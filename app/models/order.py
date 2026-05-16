from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime
from app.models.database import Base


class PushRecord(Base):
    """推送记录表"""
    __tablename__ = "push_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 订单标识
    start_charge_seq = Column(String(64), unique=True, index=True, nullable=False)
    out_start_charge_seq = Column(String(64), index=True)
    
    # 设备信息
    connector_id = Column(String(32))
    connector_name = Column(String(128))
    station_id = Column(String(32))
    station_name = Column(String(128))
    port_no = Column(String(16))
    
    # 时间信息
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    received_at = Column(DateTime, default=datetime.now, nullable=False)
    
    # 电量与费用
    total_power = Column(Float)
    total_elec_money = Column(Float)
    total_svc_money = Column(Float)
    total_money = Column(Float)
    
    # 充电明细
    stop_reason = Column(Integer)
    sum_period = Column(Integer)
    charge_details = Column(Text)
    
    # 用户信息
    user_id = Column(String(32))
    user_name = Column(String(64))
    user_tel = Column(String(20))
    card_no = Column(String(32))
    plate_no = Column(String(32))
    
    # 电气参数
    start_soc = Column(Float)
    end_soc = Column(Float)
    start_volt = Column(Float)
    start_current = Column(Float)
    end_volt = Column(Float)
    end_current = Column(Float)
    
    # 支付信息
    pay_type = Column(Integer)
    pay_status = Column(Integer)
    
    # VIN
    vin = Column(String(32))
    
    # 验签状态
    sig_valid = Column(Integer, default=1)
    
    # 同步状态
    sync_status = Column(String(20), default="pending_sync", index=True)
    sync_at = Column(DateTime)
    sync_error = Column(Text)
    push_count = Column(Integer, default=1)
    
    # 原始数据
    raw_data = Column(Text)
    raw_payload = Column(Text)
    decrypted_data = Column(Text)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "start_charge_seq": self.start_charge_seq,
            "out_start_charge_seq": self.out_start_charge_seq,
            "connector_id": self.connector_id,
            "connector_name": self.connector_name,
            "station_id": self.station_id,
            "station_name": self.station_name,
            "port_no": self.port_no,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "total_power": self.total_power,
            "total_elec_money": self.total_elec_money,
            "total_svc_money": self.total_svc_money,
            "total_money": self.total_money,
            "stop_reason": self.stop_reason,
            "sum_period": self.sum_period,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "user_tel": self._mask_phone(self.user_tel) if self.user_tel else None,
            "card_no": self.card_no,
            "plate_no": self.plate_no,
            "start_soc": self.start_soc,
            "end_soc": self.end_soc,
            "vin": self.vin,
            "sig_valid": bool(self.sig_valid),
            "sync_status": self.sync_status,
            "sync_at": self.sync_at.isoformat() if self.sync_at else None,
            "sync_error": self.sync_error,
            "push_count": self.push_count
        }
    
    @staticmethod
    def _mask_phone(phone):
        """手机号脱敏"""
        if len(phone) >= 7:
            return phone[:3] + "****" + phone[-4:]
        return phone
