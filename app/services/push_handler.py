import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.order import PushRecord
from app.services.crypto import CryptoUtil
from app.services.order_mapper import OrderMapper
from app.services.push_logger import get_logger


class PushHandler:
    """推送处理器"""
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = get_logger()
    
    def handle_push(
        self,
        payload: Dict[str, Any],
        data_secret: str = None,
        data_secret_iv: str = None,
        sig_secret: str = None
    ) -> Dict[str, Any]:
        """
        处理推送
        
        Args:
            payload: 推送数据
            data_secret: AES密钥
            data_secret_iv: AES IV
            sig_secret: HMAC密钥
        
        Returns:
            处理结果
        """
        try:
            # 获取接口名称
            interface = payload.get("InterfaceName") or payload.get("interfaceName", "unknown")
            
            # 解密数据（如果加密）
            decrypted_data = self._decrypt_payload(payload, data_secret, data_secret_iv)
            
            if decrypted_data is None:
                # 尝试直接使用payload作为数据
                decrypted_data = payload
            
            # 验签
            sig_valid = self._verify_signature(payload, sig_secret)
            
            # 获取订单号
            seq = decrypted_data.get("StartChargeSeq") or decrypted_data.get("startChargeSeq")
            
            if seq:
                self.logger.push_received(seq, interface)
            else:
                self.logger.warning("推送缺少订单号", interface=interface)
            
            # 存储记录
            record = self._save_record(decrypted_data, seq, payload, sig_valid)
            
            if record:
                self.logger.push_success(seq)
                return {
                    "code": 0,
                    "msg": "success",
                    "data": {"seq": seq, "id": record.id}
                }
            else:
                self.logger.push_failed(seq, "存储失败")
                return {
                    "code": 1,
                    "msg": "存储失败"
                }
                
        except Exception as e:
            self.logger.error("推送处理异常", error=str(e))
            return {
                "code": 1,
                "msg": f"处理异常: {str(e)}"
            }
    
    def _decrypt_payload(
        self,
        payload: Dict[str, Any],
        data_secret: str,
        data_secret_iv: str
    ) -> Optional[Dict[str, Any]]:
        """解密推送数据"""
        if not data_secret or not data_secret_iv:
            return None
        
        try:
            # 尝试多种加密数据字段名
            encrypted = (
                payload.get("EncryptedData") or
                payload.get("encryptedData") or
                payload.get("data")
            )
            
            if encrypted:
                decrypted = CryptoUtil.aes_decrypt(encrypted, data_secret, data_secret_iv)
                if decrypted:
                    return decrypted
        except Exception:
            pass
        
        return None
    
    def _verify_signature(self, payload: Dict[str, Any], sig_secret: str) -> bool:
        """验签"""
        if not sig_secret:
            return True  # 未配置密钥，跳过验签

        try:
            # 尝试多种签名字段名
            signature = (
                payload.get("Signature") or
                payload.get("signature") or
                payload.get("Sig")
            )

            data = (
                payload.get("Data") or
                payload.get("data")
            )

            if not signature or not data:
                self.logger.warning("验签字段缺失", has_sig=bool(signature), has_data=bool(data))
                return False

            data_str = json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
            verified = CryptoUtil.hmac_verify(data_str, signature, sig_secret)
            if not verified:
                self.logger.warning("验签失败")
            return verified
        except Exception as e:
            self.logger.error("验签异常", error=str(e))
            return False
    
    def _save_record(
        self,
        data: Dict[str, Any],
        seq: str,
        raw_payload: Dict[str, Any],
        sig_valid: bool
    ) -> Optional[PushRecord]:
        """保存推送记录"""
        if not seq:
            return None

        order_status = data.get("StartChargeSeqStat") or data.get("startChargeSeqStat")
        if order_status:
            try:
                if int(order_status) != 2:
                    self.logger.info(f"跳过非完成状态订单: {seq}, 状态: {order_status}")
                    return None
            except ValueError:
                pass
        
        try:
            # 检查是否已存在
            existing = self.db.query(PushRecord).filter(
                PushRecord.start_charge_seq == seq
            ).first()
            
            if existing:
                # 更新已有记录
                self._update_record(existing, data)
                existing.push_count += 1
                self.db.commit()
                return existing
            
            # 创建新记录
            record = PushRecord()
            self._update_record(record, data)
            record.start_charge_seq = seq
            record.received_at = datetime.now()
            record.sig_valid = 1 if sig_valid else 0
            record.sync_status = "pending_sync"
            record.push_count = 1
            record.raw_data = json.dumps(raw_payload, ensure_ascii=False)
            
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            
            return record
            
        except Exception as e:
            self.db.rollback()
            self.logger.error("保存记录失败", seq=seq, error=str(e))
            return None
    
    def _update_record(self, record: PushRecord, data: Dict[str, Any]):
        """更新记录字段"""
        parsed = OrderMapper.parse_push_data(data)
        
        for key, value in parsed.items():
            if value is not None and hasattr(record, key):
                setattr(record, key, value)
