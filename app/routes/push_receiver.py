import json
import logging
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.services.push_handler import PushHandler
from app.config import DATA_SECRET, DATA_SECRET_IV, SIG_SECRET

router = APIRouter()
logger = logging.getLogger("push_receiver")


@router.post("/push")
async def receive_push(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    接收小桔充电推送
    
    小桔会定期推送充电订单数据，包括：
    - 充电开始/结束通知
    - 充电过程明细
    - 支付结果等
    """
    try:
        # 获取原始请求体
        body = await request.body()
        body_str = body.decode("utf-8")
        
        # 尝试解析JSON
        try:
            payload = json.loads(body_str)
        except json.JSONDecodeError:
            payload = {"raw": body_str}
        
        # 处理推送
        handler = PushHandler(db)
        result = handler.handle_push(
            payload,
            DATA_SECRET,
            DATA_SECRET_IV,
            SIG_SECRET
        )
        
        return result
        
    except Exception as e:
        logger.error("推送处理异常", exc_info=True, error=str(e))
        return {
            "code": 1,
            "msg": "处理异常，请查看日志"
        }


@router.get("/push/test")
async def test_push():
    """测试接口"""
    return {"code": 0, "msg": "接口正常"}
