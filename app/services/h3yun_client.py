import json
import httpx
from typing import Optional, Dict, Any

from app.config import H3YUN_ENGINE_CODE, H3YUN_ENGINE_SECRET


class H3yunClient:
    """氚云 OpenAPI 客户端（异步版本）"""
    
    BASE_URL = "https://www.h3yun.com/OpenApi/Invoke"
    
    def __init__(self, engine_code: str = None, engine_secret: str = None):
        self.engine_code = engine_code or H3YUN_ENGINE_CODE
        self.engine_secret = engine_secret or H3YUN_ENGINE_SECRET
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建HTTP客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self):
        """关闭HTTP客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def create_biz_object(
        self,
        schema_code: str,
        biz_object: Dict[str, Any],
        is_submit: bool = True
    ) -> Dict[str, Any]:
        """
        创建氚云业务对象（异步）
        
        Args:
            schema_code: 表单编码
            biz_object: 字段字典
            is_submit: 是否提交（true:创建生效数据，false:创建草稿）
        
        Returns:
            {"Successful": True, "ReturnData": {"BizObjectId": "..."}}
        """
        headers = {
            "EngineCode": self.engine_code,
            "EngineSecret": self.engine_secret,
            "Content-Type": "application/json"
        }
        
        payload = {
            "ActionName": "CreateBizObject",
            "SchemaCode": schema_code,
            "BizObject": json.dumps(biz_object, ensure_ascii=False),
            "IsSubmit": is_submit
        }
        
        try:
            client = await self._get_client()
            response = await client.post(
                self.BASE_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            return result
                
        except httpx.HTTPError as e:
            return {"Successful": False, "ErrorMessage": f"HTTP错误: {str(e)}"}
        except Exception as e:
            return {"Successful": False, "ErrorMessage": f"请求异常: {str(e)}"}
    
    async def check_duplicate(self, schema_code: str, start_charge_seq: str) -> bool:
        """
        查询氚云中是否已存在该订单号（异步）
        
        Args:
            schema_code: 表单编码
            start_charge_seq: 订单号
        
        Returns:
            True: 已存在，False: 不存在
        """
        headers = {
            "EngineCode": self.engine_code,
            "EngineSecret": self.engine_secret,
            "Content-Type": "application/json"
        }
        
        payload = {
            "ActionName": "LoadBizObjects",
            "SchemaCode": schema_code,
            "PageSize": 1,
            "PageIndex": 1,
            "SearchItems": json.dumps([{
                "FieldCode": "StartChargeSeq",
                "FieldValue": start_charge_seq,
                "CompareType": 1  # 等于
            }], ensure_ascii=False)
        }
        
        try:
            client = await self._get_client()
            response = await client.post(
                self.BASE_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("Successful") and result.get("ReturnData"):
                data = result["ReturnData"]
                total = data.get("Total", 0)
                return total > 0
            return False
            
        except Exception:
            # 检查失败时跳过检查（避免阻塞同步流程）
            return False
