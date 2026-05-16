import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pathlib import Path
from datetime import datetime

from app.models.database import get_db
from app.models.order import PushRecord
from app.config import ADMIN_USERNAME, ADMIN_PASSWORD
from app.services.push_logger import get_logger

router = APIRouter()
security = HTTPBasic()
logger = get_logger()


def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """验证 HTTP Basic Auth 认证"""
    import secrets
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="认证失败",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def _read_service_logs(limit: int = 50):
    """读取服务日志"""
    base_dir = Path(__file__).parent.parent.parent.resolve()
    log_dir = base_dir / "logs"

    logs = []
    if log_dir.exists():
        today_str = datetime.now().strftime("%Y-%m-%d")
        log_file = log_dir / f"service_{today_str}.log"

        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines[-limit:]:
                        line = line.strip()
                        if line:
                            try:
                                logs.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
            except Exception:
                pass

    return logs


def _read_api_logs(limit: int = 200):
    """读取API调用日志（包括query_station_status等查询接口）"""
    base_dir = Path(__file__).parent.parent.parent.resolve()
    log_dir = base_dir / "logs"

    logs = []
    if log_dir.exists():
        today_str = datetime.now().strftime("%Y-%m-%d")
        log_file = log_dir / f"push_{today_str}.log"

        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines[-limit:]:
                        line = line.strip()
                        if line:
                            try:
                                logs.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
            except Exception:
                pass

    logs = logs[::-1]

    folded_logs = []
    qss_count = 0
    qss_last = None

    for log in logs:
        if log.get("interface") == "query_station_status" and log.get("direction") == "query_in":
            qss_count += 1
            qss_last = log
        else:
            folded_logs.append(log)

    if qss_last and qss_count > 0:
        qss_last["_folded_count"] = qss_count
        folded_logs.append(qss_last)

    return folded_logs


def _get_stats(db: Session) -> dict:
    """获取推送记录统计信息（复用函数）"""
    return {
        "total": db.query(PushRecord).count(),
        "pending": db.query(PushRecord).filter(PushRecord.sync_status == "pending_sync").count(),
        "synced": db.query(PushRecord).filter(PushRecord.sync_status == "synced").count(),
        "failed": db.query(PushRecord).filter(PushRecord.sync_status == "failed").count(),
    }


@router.get("/", response_class=HTMLResponse)
async def admin_index(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(verify_auth)
):
    """后台管理首页 - 推送记录列表"""
    # 获取最近推送记录
    records = db.query(PushRecord)\
        .order_by(PushRecord.received_at.desc())\
        .limit(200)\
        .all()
    
    # 获取服务日志和API日志（API日志最多显示200条）
    service_logs = _read_service_logs(limit=50)
    api_logs = _read_api_logs(limit=200)
    
    # 统计
    stats = _get_stats(db)

    _require_templates()
    return templates.TemplateResponse(request, "admin/index.html", {
        "records": [r.to_dict() for r in records],
        "service_logs": service_logs,
        "api_logs": api_logs,
        "stats": stats
    })


@router.get("/record/{record_id}", response_class=HTMLResponse)
async def admin_record_detail(
    request: Request,
    record_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_auth)
):
    """推送记录详情"""
    record = db.query(PushRecord).filter(PushRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    _require_templates()
    return templates.TemplateResponse(request, "admin/detail.html", {"record": record.to_dict()})


@router.post("/test")
async def admin_test(
    request: Request,
    payload: dict,
    db: Session = Depends(get_db),
    username: str = Depends(verify_auth)
):
    """测试推送处理"""
    from app.services.push_handler import PushHandler
    from app.config import DATA_SECRET, DATA_SECRET_IV, SIG_SECRET
    
    handler = PushHandler(db)
    result = handler.handle_push(payload, DATA_SECRET, DATA_SECRET_IV, SIG_SECRET)
    return result


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(verify_auth)
):
    """实时看板"""
    # 今日统计
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    today_stats = {
        "push_count": db.query(PushRecord).filter(PushRecord.received_at >= today_start).count(),
        "sync_success": db.query(PushRecord)
            .filter(PushRecord.sync_status == "synced")
            .filter(PushRecord.sync_at >= today_start)
            .count(),
        "sync_failed": db.query(PushRecord)
            .filter(PushRecord.sync_status == "failed")
            .filter(PushRecord.sync_at >= today_start)
            .count(),
    }
    
    # 总览统计
    total_stats = _get_stats(db)
    
    # 最近日志（API日志最多显示200条）
    service_logs = _read_service_logs(limit=50)
    api_logs = _read_api_logs(limit=200)

    _require_templates()
    return templates.TemplateResponse(request, "admin/dashboard.html", {
        "today_stats": today_stats,
        "total_stats": total_stats,
        "service_logs": service_logs,
        "api_logs": api_logs
    })


@router.get("/retry", response_class=HTMLResponse)
async def admin_retry(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(verify_auth)
):
    """一键重试页面"""
    # 获取失败记录
    failed_records = db.query(PushRecord)\
        .filter(PushRecord.sync_status == "failed")\
        .order_by(PushRecord.sync_at.desc())\
        .limit(100)\
        .all()
    
    _require_templates()
    return templates.TemplateResponse(request, "admin/retry.html", {
        "failed_records": [r.to_dict() for r in failed_records]
    })


@router.get("/query", response_class=HTMLResponse)
async def admin_query(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(verify_auth)
):
    """订单查询页面"""
    _require_templates()
    return templates.TemplateResponse(request, "admin/query.html", {})


@router.get("/stats", response_class=HTMLResponse)
async def admin_stats(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(verify_auth)
):
    """统计报表页面"""
    # 过去30天的同步统计
    from datetime import timedelta
    days = 30
    start_date = datetime.now() - timedelta(days=days)
    
    # 按日期分组统计
    records = db.query(PushRecord)\
        .filter(PushRecord.sync_at >= start_date)\
        .filter(PushRecord.sync_at.isnot(None))\
        .all()
    
    # 聚合
    daily_stats = {}
    for r in records:
        date_key = r.sync_at.strftime("%Y-%m-%d")
        if date_key not in daily_stats:
            daily_stats[date_key] = {"success": 0, "failed": 0}
        if r.sync_status == "synced":
            daily_stats[date_key]["success"] += 1
        elif r.sync_status == "failed":
            daily_stats[date_key]["failed"] += 1
    
    # 失败原因统计
    error_stats = {}
    failed_records = db.query(PushRecord)\
        .filter(PushRecord.sync_status == "failed")\
        .filter(PushRecord.sync_error.isnot(None))\
        .all()
    
    for r in failed_records:
        error_key = r.sync_error[:50] if r.sync_error else "未知错误"
        error_stats[error_key] = error_stats.get(error_key, 0) + 1

    _require_templates()
    return templates.TemplateResponse(request, "admin/stats.html", {
        "daily_stats": json.dumps(daily_stats),
        "error_stats": json.dumps(error_stats)
    })


# 模板引擎实例（在main.py中通过set_templates注入）
templates = None

def set_templates(tpl):
    global templates
    templates = tpl


def _require_templates():
    """确保模板引擎已初始化，否则返回明确错误"""
    if templates is None:
        from fastapi.responses import JSONResponse
        raise HTTPException(status_code=503, detail="模板引擎未初始化，请稍后重试")
