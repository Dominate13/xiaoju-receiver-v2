import json
from datetime import datetime
from typing import Dict, Any, Optional


class OrderMapper:
    """订单数据映射器 - 将推送数据映射为氚云表单字段"""
    
    # 氚云表单字段映射
    FIELD_MAP = {
        # 订单标识
        "StartChargeSeq": "StartChargeSeq",      # 订单号
        "OutStartChargeSeq": "OutStartChargeSeq",  # 外部订单号
        
        # 设备信息
        "ConnectorID": "ConnectorID",           # 充电枪ID
        "ConnectorName": "ConnectorName",       # 充电枪名称
        "StationID": "StationID",               # 电站ID
        "StationName": "StationName",           # 电站名称
        "PortNo": "PortNo",                     # 端口号
        
        # 时间信息
        "StartTime": "StartTime",               # 开始时间
        "EndTime": "EndTime",                   # 结束时间
        
        # 电量与费用
        "TotalPower": "TotalPower",             # 总充电量
        "TotalElecMoney": "TotalElecMoney",     # 电费
        "TotalSeviceMoney": "TotalSeviceMoney",  # 服务费
        "TotalMoney": "TotalMoney",             # 总费用
        
        # 充电明细
        "StopReason": "StopReason",             # 停止原因
        "SumPeriod": "SumPeriod",               # 充电时段数
        "ChargeDetails": "ChargeDetails",       # 充电明细JSON
        
        # 用户信息
        "UserID": "UserID",                     # 用户ID
        "UserName": "UserName",                 # 用户名
        "UserTel": "UserTel",                   # 手机号
        "CardNo": "CardNo",                     # 卡号
        "PlateNumber": "PlateNumber",          # 车牌号
        
        # SOC
        "StartSOC": "StartSOC",                 # 开始SOC
        "EndSOC": "EndSOC",                     # 结束SOC
        
        # 电气参数
        "StartVolt": "StartVolt",               # 开始电压
        "StartCurrent": "StartCurrent",         # 开始电流
        "EndVolt": "EndVolt",                   # 结束电压
        "EndCurrent": "EndCurrent",             # 结束电流
        
        # 支付信息
        "PayType": "PayType",                   # 支付类型
        "PayStatus": "PayStatus",               # 支付状态
        
        # VIN
        "Vin": "Vin",                           # 车架号
        
        # 接收时间（本地添加）
        "ReceivedAt": "ReceivedAt",             # 接收时间
    }
    
    @classmethod
    def map_to_biz_object(cls, record) -> Dict[str, Any]:
        """
        将PushRecord映射为氚云业务对象
        
        Args:
            record: PushRecord模型实例
        
        Returns:
            氚云业务对象字典
        """
        biz_object = {}
        
        # 基础字段直接映射（不含需要特殊处理的字段）
        simple_fields = [
            "start_charge_seq", "out_start_charge_seq",
            "connector_id",
            "station_id", "port_no",
            "total_power", "total_elec_money", "total_money",
            "stop_reason", "sum_period",
            "user_id", "user_name", "user_tel", "card_no",
            "start_soc", "end_soc",
            "start_volt", "start_current", "end_volt", "end_current",
            "pay_type", "pay_status", "vin"
        ]
        
        for field in simple_fields:
            value = getattr(record, field, None)
            if value is not None:
                camel_field = cls._to_camel(field)
                biz_object[camel_field] = value
        
        # connector_name 特殊处理：氚云字段为 ConnectorName（首字母大写）
        if record.connector_name:
            biz_object["ConnectorName"] = record.connector_name
        
        # total_svc_money 特殊处理：氚云字段为 TotalSeviceMoney（首字母大写，注意拼写）
        if record.total_svc_money is not None:
            biz_object["TotalSeviceMoney"] = record.total_svc_money
        
        # 车牌号特殊处理：映射为 PlateNumber
        if record.plate_no:
            biz_object["PlateNumber"] = record.plate_no
        
        # station_name 特殊处理：氚云字段为 StationName（首字母大写）
        if record.station_name:
            biz_object["StationName"] = record.station_name
        
        # 时间字段特殊处理
        if record.start_time:
            biz_object["StartTime"] = record.start_time.strftime("%Y-%m-%d %H:%M:%S")
        if record.end_time:
            biz_object["EndTime"] = record.end_time.strftime("%Y-%m-%d %H:%M:%S")
        if record.received_at:
            biz_object["ReceivedAt"] = record.received_at.strftime("%Y-%m-%d %H:%M:%S")
        
        # 充电明细
        if record.charge_details:
            if isinstance(record.charge_details, str):
                biz_object["ChargeDetails"] = record.charge_details
            else:
                biz_object["ChargeDetails"] = json.dumps(record.charge_details, ensure_ascii=False)
        
        return biz_object
    
    @staticmethod
    def _to_camel(snake_str: str) -> str:
        """下划线转大驼峰"""
        components = snake_str.split("_")
        return components[0] + "".join(x.title() for x in components[1:])
    
    @classmethod
    def parse_push_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析推送数据，统一字段名
        
        Args:
            data: 原始推送数据（可能有多种字段名格式）
        
        Returns:
            统一格式的字典
        """
        result = {}
        
        # 订单标识
        result["start_charge_seq"] = data.get("StartChargeSeq") or data.get("startChargeSeq")
        result["out_start_charge_seq"] = data.get("OutStartChargeSeq") or data.get("outStartChargeSeq")
        
        # 设备信息
        result["connector_id"] = data.get("ConnectorID") or data.get("connectorID")
        result["connector_name"] = data.get("ConnectorName") or data.get("connectorName")
        result["station_id"] = data.get("StationID") or data.get("stationID")
        result["station_name"] = data.get("StationName") or data.get("stationName")
        result["port_no"] = data.get("PortNo") or data.get("portNo")
        
        # 时间信息
        result["start_time"] = cls._parse_datetime(data.get("StartTime") or data.get("startTime"))
        result["end_time"] = cls._parse_datetime(data.get("EndTime") or data.get("endTime"))
        
        # 电量与费用
        result["total_power"] = cls._parse_float(data.get("TotalPower") or data.get("totalPower"))
        result["total_elec_money"] = cls._parse_float(data.get("TotalElecMoney") or data.get("totalElecMoney"))
        # 注意：小桔拼写是 TotalSeviceMoney（大写S）
        result["total_svc_money"] = cls._parse_float(
            data.get("TotalSeviceMoney") or data.get("totalSeviceMoney") or data.get("TotalSvcMoney")
        )
        result["total_money"] = cls._parse_float(data.get("TotalMoney") or data.get("totalMoney"))
        
        # 充电明细
        result["stop_reason"] = cls._parse_int(data.get("StopReason") or data.get("stopReason"))
        result["sum_period"] = cls._parse_int(data.get("SumPeriod") or data.get("sumPeriod"))
        result["charge_details"] = cls._parse_json(data.get("ChargeDetails") or data.get("chargeDetails"))
        
        # 用户信息
        result["user_id"] = data.get("UserID") or data.get("userID") or data.get("userId")
        result["user_name"] = data.get("UserName") or data.get("userName")
        result["user_tel"] = data.get("UserTel") or data.get("userTel")
        result["card_no"] = data.get("CardNo") or data.get("cardNo")
        # 车牌：加密大驼峰 PlateNumber，明文小驼峰 plateNo / plateNumber
        result["plate_no"] = data.get("PlateNumber") or data.get("plateNumber") or data.get("PlateNo") or data.get("plateNo")
        
        # SOC
        result["start_soc"] = cls._parse_float(data.get("StartSOC") or data.get("startSOC"))
        result["end_soc"] = cls._parse_float(data.get("EndSOC") or data.get("endSOC"))
        
        # 电气参数
        result["start_volt"] = cls._parse_float(data.get("StartVolt") or data.get("startVolt"))
        result["start_current"] = cls._parse_float(data.get("StartCurrent") or data.get("startCurrent"))
        result["end_volt"] = cls._parse_float(data.get("EndVolt") or data.get("endVolt"))
        result["end_current"] = cls._parse_float(data.get("EndCurrent") or data.get("endCurrent"))
        
        # 支付信息
        result["pay_type"] = cls._parse_int(data.get("PayType") or data.get("payType"))
        result["pay_status"] = cls._parse_int(data.get("PayStatus") or data.get("payStatus"))
        
        # VIN
        result["vin"] = data.get("Vin") or data.get("vin")
        
        return result
    
    @staticmethod
    def _parse_datetime(value) -> Optional[datetime]:
        """解析日期时间"""
        if not value:
            return None
        try:
            if isinstance(value, datetime):
                return value
            # 尝试多种格式
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d %H:%M:%S"]:
                try:
                    return datetime.strptime(str(value), fmt)
                except ValueError:
                    continue
            return None
        except Exception:
            return None
    
    @staticmethod
    def _parse_float(value) -> Optional[float]:
        """解析浮点数"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _parse_int(value) -> Optional[int]:
        """解析整数"""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _parse_json(value) -> Optional[str]:
        """解析JSON（返回字符串）"""
        if value is None:
            return None
        if isinstance(value, str):
            try:
                json.loads(value)
                return value
            except json.JSONDecodeError:
                return None
        else:
            try:
                return json.dumps(value, ensure_ascii=False)
            except Exception:
                return None
