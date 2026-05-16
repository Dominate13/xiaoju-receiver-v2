from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.order import PushRecord
from app.config import SYNC_INTERVAL_SECONDS, SYNC_BATCH_SIZE
from app.services.sync_worker import SyncWorker

router = APIRouter()

# 全局同步工作器实例
sync_worker: SyncWorker = None


def get_sync_worker() -> SyncWorker:
    """获取同步工作器"""
    global sync_worker
    if sync_worker is None:
        from app.models.database import SessionLocal
        sync_worker = SyncWorker(SessionLocal)
    return sync_worker


def set_sync_worker(worker: SyncWorker):
    """设置同步工作器（在main.py中调用）"""
    global sync_worker
    sync_worker = worker


@router.get("/sync/status")
async def get_sync_status(db: Session = Depends(get_db)):
    """获取同步统计数据"""
    pending_count = db.query(PushRecord)\
        .filter(PushRecord.sync_status == "pending_sync")\
        .count()
    
    synced_count = db.query(PushRecord)\
        .filter(PushRecord.sync_status == "synced")\
        .count()
    
    failed_count = db.query(PushRecord)\
        .filter(PushRecord.sync_status == "failed")\
        .count()
    
    return {
        "pending_sync": pending_count,
        "synced": synced_count,
        "failed": failed_count,
        "sync_interval_seconds": SYNC_INTERVAL_SECONDS,
        "batch_size": SYNC_BATCH_SIZE
    }


@router.post("/sync/run")
async def trigger_sync():
    """手动触发一轮同步"""
    worker = get_sync_worker()
    report = await worker.run_once()
    return {
        "success_count": report.success_count,
        "failed_count": report.failed_count,
        "skipped_count": report.skipped_count,
        "message": report.message
    }


@router.post("/sync/retry")
async def retry_failed_records():
    """重试失败记录"""
    worker = get_sync_worker()
    report = await worker.retry_failed()
    return {
        "success_count": report.success_count,
        "failed_count": report.failed_count,
        "skipped_count": report.skipped_count,
        "message": report.message
    }


@router.post("/sync/retry/{record_id}")
async def retry_single_record(
    record_id: int,
    db: Session = Depends(get_db)
):
    """重试单条失败记录"""
    record = db.query(PushRecord).filter(PushRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    if record.sync_status != "failed":
        raise HTTPException(status_code=400, detail="记录状态不是失败")
    
    worker = get_sync_worker()
    report = await worker.retry_failed([record_id])
    return {
        "success_count": report.success_count,
        "failed_count": report.failed_count,
        "skipped_count": report.skipped_count,
        "message": report.message
    }


@router.get("/sync/failed")
async def get_failed_records(db: Session = Depends(get_db), limit: int = 20):
    """获取失败记录列表"""
    records = db.query(PushRecord)\
        .filter(PushRecord.sync_status == "failed")\
        .order_by(PushRecord.sync_at.desc())\
        .limit(limit)\
        .all()
    
    return [r.to_dict() for r in records]
