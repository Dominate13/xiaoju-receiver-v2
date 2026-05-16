import asyncio
import os
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.routing import Route

import schedule

from app.config import SERVICE_PORT, SYNC_INTERVAL_SECONDS, H3YUN_ENGINE_CODE, H3YUN_ENGINE_SECRET, \
    validate_config
from app.models.database import init_db, SessionLocal
from app.routes import push_receiver, admin, sync_admin, station, station_mapping
from app.services.sync_worker import SyncWorker
from app.services.push_logger import get_logger
from app.services.log_cleanup import cleanup_old_logs

logger = get_logger()

# 同步任务引用
sync_worker: SyncWorker = None
# 日志清理线程
log_cleanup_thread: threading.Thread = None
log_cleanup_running = False


def log_cleanup_job():
    """日志清理定时任务"""
    try:
        cleanup_old_logs(10)
    except Exception as e:
        logger.error("日志清理任务异常", error=str(e))

def log_cleanup_loop():
    """日志清理线程主循环"""
    global log_cleanup_running
    while log_cleanup_running:
        schedule.run_pending()
        time.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 修复崩溃点2和3"""
    global sync_worker, log_cleanup_thread, log_cleanup_running
    
    # === 启动阶段（修复点2：添加异常保护）===
    try:
        logger.service_started(SERVICE_PORT)

        # 配置验证
        config_errors = validate_config()
        if config_errors:
            for err in config_errors:
                logger.warning(f"配置警告: {err}")

        # 初始化数据库
        init_db()
        
        # 启动日志清理定时任务（每天凌晨2点执行）
        log_cleanup_running = True
        schedule.every().day.at("02:00").do(log_cleanup_job)
        log_cleanup_thread = threading.Thread(target=log_cleanup_loop, daemon=True)
        log_cleanup_thread.start()
        logger.info("日志清理定时任务已启动（每天凌晨2:00执行）")
        
        # 只有配置了氚云密钥才启动同步任务
        if H3YUN_ENGINE_CODE and H3YUN_ENGINE_SECRET:
            # 创建同步工作器
            sync_worker = SyncWorker(SessionLocal)
            
            # 将工作器设置到路由模块
            sync_admin.set_sync_worker(sync_worker)
            
            # 启动定时任务（使用 asyncio.create_task 并添加超时保护）
            async def run_sync_loop():
                try:
                    await sync_worker.start_loop(SYNC_INTERVAL_SECONDS)
                except asyncio.CancelledError:
                    logger.info("同步任务被取消")
                except Exception as e:
                    logger.error("同步任务异常", error=str(e))
                finally:
                    if sync_worker:
                        await sync_worker.cleanup()
            
            # 创建任务但不等待完成
            task = asyncio.create_task(run_sync_loop())
            
            logger.info("氚云同步任务已启动", interval=SYNC_INTERVAL_SECONDS)
        else:
            logger.warning("氚云配置未完整，同步任务未启动")
            
    except Exception as e:
        logger.critical("启动异常", error=str(e))
        # 不阻止应用启动，只是记录错误
    
    yield  # 应用运行中
    
    # === 关闭阶段（修复点3：正确取消task）===
    try:
        logger.service_stopped()
        
        # 停止日志清理任务
        log_cleanup_running = False
        schedule.clear()
        if log_cleanup_thread and log_cleanup_thread.is_alive():
            log_cleanup_thread.join(timeout=2.0)
        logger.info("日志清理任务已停止")
        
        if sync_worker:
            # 停止同步任务
            sync_worker.stop()
            
            # 等待任务完成（带超时）
            try:
                await asyncio.wait_for(
                    sync_worker.cleanup(),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning("同步任务清理超时，强制取消")
            except asyncio.CancelledError:
                pass
        
        logger.info("服务已正常关闭")
        
    except Exception as e:
        logger.error("关闭异常", error=str(e))
    
    finally:
        # 确保资源清理
        if sync_worker and sync_worker.h3yun_client:
            await sync_worker.h3yun_client.close()


# 创建FastAPI应用
app = FastAPI(
    title="小桔充电推送接收服务",
    description="接收小桔充电订单推送，解密验签并存储，同步至氚云",
    version="2.0.0",
    lifespan=lifespan
)

# 创建模板引擎
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# 设置管理路由的模板引擎
admin.set_templates(templates)
station_mapping.set_templates(templates)


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查接口 - 检查数据库连接和同步任务状态"""
    from sqlalchemy import text
    health_info = {"status": "healthy"}

    # 检查数据库连接
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_info["database"] = "ok"
    except Exception as e:
        health_info["status"] = "unhealthy"
        health_info["database"] = f"error: {str(e)}"

    # 检查同步任务
    if sync_worker:
        health_info["sync_worker"] = "running" if sync_worker._running else "stopped"
    else:
        health_info["sync_worker"] = "not_initialized"

    return health_info


@app.get("/")
async def root():
    """首页"""
    return {
        "message": "小桔充电推送接收服务运行中",
        "version": "2.0.0"
    }


# 静态文件
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# 注册路由
app.include_router(push_receiver.router, prefix="/api", tags=["推送接收"])
app.include_router(station.router, tags=["场站接口"])
app.include_router(admin.router, prefix="/admin", tags=["后台管理"])
app.include_router(sync_admin.router, prefix="/admin", tags=["同步管理"])
app.include_router(station_mapping.router, prefix="/admin/station_mapping", tags=["映射管理"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=False
    )
