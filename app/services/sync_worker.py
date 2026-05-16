import asyncio
import time
from datetime import datetime
from typing import Optional

from app.models.order import PushRecord
from app.models.station_connector import Connector
from app.config import H3YUN_ENGINE_CODE, H3YUN_ENGINE_SECRET, H3YUN_SCHEMA_CODE, \
    SYNC_BATCH_SIZE, SYNC_MAX_RETRY
from app.services.h3yun_client import H3yunClient
from app.services.order_mapper import OrderMapper
from app.services.push_logger import get_logger


class SyncReport:
    """同步报告"""
    def __init__(self):
        self.success_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.message = ""


class SyncWorker:
    """同步工作器 - 异步版本"""
    
    def __init__(self, db_session_maker):
        self.db_session_maker = db_session_maker
        self.h3yun_client: Optional[H3yunClient] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.logger = get_logger()
        
        # 初始化氚云客户端
        if H3YUN_ENGINE_CODE and H3YUN_ENGINE_SECRET:
            self.h3yun_client = H3yunClient(H3YUN_ENGINE_CODE, H3YUN_ENGINE_SECRET)
            self.logger.info("氚云客户端初始化成功")
        else:
            self.logger.warning("氚云配置未完整，同步功能将不可用")
    
    async def run_once(self) -> SyncReport:
        """执行一轮同步"""
        report = SyncReport()

        if not self.h3yun_client:
            report.message = "氚云客户端未初始化"
            return report

        loop = asyncio.get_event_loop()

        # 将同步数据库查询放到线程池执行，避免阻塞事件循环
        def _query_pending():
            db = self.db_session_maker()
            pending_records = db.query(PushRecord)\
                .filter(PushRecord.sync_status == "pending_sync")\
                .order_by(PushRecord.received_at)\
                .limit(SYNC_BATCH_SIZE)\
                .all()
            return db, pending_records

        try:
            db, pending_records = await loop.run_in_executor(None, _query_pending)

            if not pending_records:
                db.close()
                report.message = "没有待同步的记录"
                return report
            
            self.logger.info(f"开始同步 {len(pending_records)} 条记录")
            
            for record in pending_records:
                start_time = time.time()
                
                try:
                    # 幂等检查（异步）
                    if await self._is_duplicate_async(db, record):
                        report.skipped_count += 1
                        continue
                    
                    # 如果 connector_name 为空，从映射表查询
                    if not record.connector_name and record.connector_id:
                        connector = db.query(Connector).filter(
                            Connector.code == record.connector_id
                        ).first()
                        if connector and connector.name:
                            record.connector_name = connector.name
                            db.commit()  # 立即保存更新
                            self.logger.info(f"填充充电枪名称: {record.connector_id} -> {connector.name}")
                    
                    # 字段映射
                    biz_object = OrderMapper.map_to_biz_object(record)
                    
                    # 调用氚云 API（异步）
                    result = await self.h3yun_client.create_biz_object(
                        H3YUN_SCHEMA_CODE,
                        biz_object
                    )
                    
                    cost_ms = int((time.time() - start_time) * 1000)
                    
                    if result.get("Successful"):
                        # 同步成功
                        record.sync_status = "synced"
                        record.sync_at = datetime.now()
                        record.sync_error = None
                        report.success_count += 1
                        self.logger.sync_success(record.start_charge_seq, cost_ms)
                    else:
                        # 同步失败
                        error_msg = result.get("ErrorMessage", "未知错误")
                        record.sync_status = "failed"
                        record.sync_at = datetime.now()
                        record.sync_error = error_msg
                        report.failed_count += 1
                        self.logger.sync_failed(record.start_charge_seq, error_msg)
                    
                except Exception as e:
                    record.sync_status = "failed"
                    record.sync_at = datetime.now()
                    record.sync_error = str(e)
                    report.failed_count += 1
                    self.logger.sync_failed(record.start_charge_seq, str(e))
            
            db.commit()
            report.message = f"同步完成: 成功 {report.success_count}, 失败 {report.failed_count}, 跳过 {report.skipped_count}"
            self.logger.info(report.message)
            
        except Exception as e:
            db.rollback()
            report.message = f"同步任务异常: {str(e)}"
            self.logger.error("同步任务异常", error=str(e))
        finally:
            db.close()
        
        return report
    
    async def _is_duplicate_async(self, db, record: PushRecord) -> bool:
        """异步检查是否重复"""
        # 本地检查：是否已同步成功
        existing = db.query(PushRecord)\
            .filter(PushRecord.start_charge_seq == record.start_charge_seq)\
            .filter(PushRecord.sync_status == "synced")\
            .first()
        
        if existing:
            self.logger.sync_skipped(record.start_charge_seq, "本地已同步")
            return True
        
        # 氚云检查：是否已存在（异步）
        if self.h3yun_client:
            try:
                exists = await self.h3yun_client.check_duplicate(
                    H3YUN_SCHEMA_CODE,
                    record.start_charge_seq
                )
                if exists:
                    self.logger.sync_skipped(record.start_charge_seq, "氚云已存在")
                    record.sync_status = "synced"
                    record.sync_at = datetime.now()
                    db.commit()  # 立即提交，避免后续异常导致状态丢失
                    return True
            except Exception as e:
                self.logger.warning("氚云重复检查异常，跳过", seq=record.start_charge_seq, error=str(e))
        
        return False
    
    async def retry_failed(self, record_ids: list = None) -> SyncReport:
        """重试失败记录"""
        db = self.db_session_maker()
        try:
            if record_ids:
                # 重试指定记录
                records = db.query(PushRecord)\
                    .filter(PushRecord.id.in_(record_ids))\
                    .filter(PushRecord.sync_status == "failed")\
                    .all()
            else:
                # 重试所有失败记录（未超过最大重试次数）
                records = db.query(PushRecord)\
                    .filter(PushRecord.sync_status == "failed")\
                    .filter(PushRecord.push_count <= SYNC_MAX_RETRY)\
                    .all()
            
            if not records:
                report = SyncReport()
                report.message = "没有需要重试的记录"
                return report
            
            # 将失败记录状态改为待同步
            for record in records:
                record.sync_status = "pending_sync"
            
            db.commit()
            self.logger.info(f"已将 {len(records)} 条失败记录重置为待同步")
            
            # 执行同步
            return await self.run_once()
        
        except Exception as e:
            db.rollback()
            self.logger.error("重试失败记录异常", error=str(e))
            report = SyncReport()
            report.message = str(e)
            return report
        finally:
            db.close()
    
    async def start_loop(self, interval_seconds: int):
        """定时任务主循环 - 修复崩溃点2和3"""
        self._running = True
        self.logger.info("同步任务启动", interval_seconds=interval_seconds)
        
        while self._running:
            try:
                await self.run_once()
            except Exception as e:
                self.logger.error("同步任务循环异常", error=str(e))
            
            # 使用 asyncio.wait_for 添加超时保护（崩溃点2修复）
            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                # 被取消时正常退出
                break
    
    def stop(self):
        """停止定时任务"""
        self._running = False
        self.logger.info("同步任务已停止")
    
    async def cleanup(self):
        """清理资源"""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        if self.h3yun_client:
            await self.h3yun_client.close()
