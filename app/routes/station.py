from fastapi import APIRouter, Header, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import json
import time
import hashlib
import hmac
import os
from pathlib import Path
from datetime import datetime

from app.config import (
    OPERATOR_ID, SIG_SECRET, DATA_SECRET, DATA_SECRET_IV, OPERATOR_SECRET
)
from app.services.crypto import aes_encrypt, aes_decrypt, hmac_md5_sign
from app.models.database import get_db
from app.models.order import PushRecord
from app.models.station_connector import StationConnectorMapping

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent.parent.resolve()
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


def write_push_log(interface: str, direction: str, request_data: dict = None,
                   response_data: dict = None, result: str = None, error_msg: str = None):
    try:
        date_str = datetime.now().strftime('%Y-%m-%d')
        log_file = LOG_DIR / f"push_{date_str}.log"
        log_entry = {
            "time": datetime.now().isoformat(),
            "interface": interface,
            "direction": direction,
            "result": result,
            "error": error_msg,
            "request": request_data,
            "response": response_data
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"日志写入失败: {e}")


_token_store: dict = {}


def verify_sig(operator_id: str, enc_data: str, timestamp: str,
               seq: str, sig: str) -> bool:
    sign_str = f"{operator_id}{enc_data}{timestamp}{seq}"
    expected = hmac_md5_sign(sign_str, SIG_SECRET)
    return sig.upper() == expected.upper()


def verify_token(token: str) -> bool:
    if token not in _token_store:
        return False
    if time.time() > _token_store[token].get("expire_at", 0):
        del _token_store[token]
        return False
    return True


def decrypt_data(enc_data: str) -> dict:
    return json.loads(aes_decrypt(enc_data, DATA_SECRET, DATA_SECRET_IV))


def get_field(body: dict, *keys) -> Optional[any]:
    for key in keys:
        if key in body:
            return body[key]
    return None


def build_enc_response(ret: int, msg: str, data: dict) -> dict:
    enc_data = aes_encrypt(json.dumps(data, ensure_ascii=False), DATA_SECRET, DATA_SECRET_IV)
    sig = hmac_md5_sign(f"{ret}{msg}{enc_data}", SIG_SECRET)
    return {
        "ret": ret,
        "msg": msg,
        "data": enc_data,
        "sig": sig
    }


def build_plain_response(ret: int, msg: str, data: dict = None) -> dict:
    body = data or {}
    sig = hmac_md5_sign(f"{ret}{msg}", SIG_SECRET)
    return {
        "ret": ret,
        "msg": msg,
        "data": body,
        "sig": sig
    }


async def _parse_body(req: Request) -> dict:
    raw = await req.body()
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


@router.post("/api/query_token")
async def query_token(req: Request):
    body = await _parse_body(req)
    interface = "query_token"

    operator_id = get_field(body, "operatorID", "OperatorID", "operator_id")
    operator_secret = get_field(body, "operatorSecret", "OperatorSecret", "operator_secret")

    if operator_secret is not None:
        if operator_id and operator_secret == OPERATOR_SECRET and operator_id == OPERATOR_ID:
            token = hashlib.sha256(
                f"{OPERATOR_ID}{operator_secret}{int(time.time())}".encode()
            ).hexdigest()
            expire_in = 7200
            expire_at = int(time.time()) + expire_in
            _token_store[token] = {"OperatorID": OPERATOR_ID, "expire_at": expire_at}
            response = build_enc_response(0, "成功", {
                "operatorID": OPERATOR_ID,
                "succStat": 0,
                "accessToken": token,
                "tokenAvailableTime": expire_in,
                "failReason": 0
            })
            write_push_log(interface, "query_in", request_data=body, response_data=response, result="success")
            return response
        elif operator_id != OPERATOR_ID:
            response = build_enc_response(4004, "无此运营商", {
                "operatorID": operator_id or "",
                "succStat": 1,
                "accessToken": "",
                "tokenAvailableTime": 0,
                "failReason": 1
            })
            write_push_log(interface, "query_in", request_data=body, response_data=response, result="failed", error_msg="无此运营商")
            return response
        else:
            response = build_enc_response(4004, "秘钥错误", {
                "operatorID": operator_id or "",
                "succStat": 1,
                "accessToken": "",
                "tokenAvailableTime": 0,
                "failReason": 2
            })
            write_push_log(interface, "query_in", request_data=body, response_data=response, result="failed", error_msg="秘钥错误")
            return response

    enc_data = get_field(body, "data", "Data") or ""
    operator_id = operator_id or get_field(body, "operatorID", "OperatorID")
    ts = get_field(body, "timeStamp", "TimeStamp", "timestamp")
    s = get_field(body, "sig", "Sig")

    if not enc_data:
        response = build_enc_response(4003, "缺少 data 字段", {})
        write_push_log(interface, "query_in", request_data=body, response_data=response, result="failed", error_msg="缺少 data 字段")
        return response

    if not verify_sig(operator_id, enc_data, ts, get_field(body, "seq", "Seq"), s):
        response = build_enc_response(4001, "签名错误", {})
        write_push_log(interface, "query_in", request_data=body, response_data=response, result="failed", error_msg="签名错误")
        return response

    try:
        inner = decrypt_data(enc_data)
    except Exception:
        response = build_enc_response(4001, "数据解密失败", {})
        write_push_log(interface, "query_in", request_data=body, response_data=response, result="failed", error_msg="数据解密失败")
        return response

    inner_secret = get_field(inner, "operatorSecret", "OperatorSecret", "operator_secret")
    inner_id = get_field(inner, "operatorID", "OperatorID", "operator_id")

    if inner_id != OPERATOR_ID:
        response = build_enc_response(4004, "无此运营商", {
            "operatorID": inner_id or "",
            "succStat": 1,
            "accessToken": "",
            "tokenAvailableTime": 0,
            "failReason": 1
        })
        write_push_log(interface, "query_in", request_data=body, response_data=response, result="failed", error_msg="无此运营商")
        return response

    if inner_secret != OPERATOR_SECRET:
        response = build_enc_response(4004, "秘钥错误", {
            "operatorID": inner_id or "",
            "succStat": 1,
            "accessToken": "",
            "tokenAvailableTime": 0,
            "failReason": 2
        })
        write_push_log(interface, "query_in", request_data=body, response_data=response, result="failed", error_msg="秘钥错误")
        return response

    token = hashlib.sha256(
        f"{OPERATOR_ID}{inner_secret}{ts}{time.time()}".encode()
    ).hexdigest()
    expire_in = 7200
    expire_at = int(time.time()) + expire_in
    _token_store[token] = {"OperatorID": OPERATOR_ID, "expire_at": expire_at}

    response = build_enc_response(0, "成功", {
        "operatorID": OPERATOR_ID,
        "succStat": 0,
        "accessToken": token,
        "tokenAvailableTime": expire_in,
        "failReason": 0
    })
    write_push_log(interface, "query_in", request_data=body, response_data=response, result="success")
    return response


@router.post("/api/query_stations_info")
async def query_stations_info(
    authorization: str = Header(None),
    req: Request = None
):
    interface = "query_stations_info"
    
    if not authorization or not authorization.startswith("Bearer "):
        response = build_enc_response(4002, "Token错误", {})
        write_push_log(interface, "query_in", response_data=response, result="failed", error_msg="Token错误")
        return response
    if not verify_token(authorization[7:]):
        response = build_enc_response(4002, "Token无效或已过期", {})
        write_push_log(interface, "query_in", response_data=response, result="failed", error_msg="Token无效或已过期")
        return response

    body = await _parse_body(req)
    enc_data = get_field(body, "data", "Data") or ""
    operator_id = get_field(body, "operatorID", "OperatorID")
    ts = get_field(body, "timeStamp", "TimeStamp", "timestamp")
    s = get_field(body, "sig", "Sig")

    if not verify_sig(operator_id, enc_data, ts, get_field(body, "seq", "Seq"), s):
        response = build_enc_response(4001, "签名错误", {})
        write_push_log(interface, "query_in", request_data=body, response_data=response, result="failed", error_msg="签名错误")
        return response

    try:
        inner = decrypt_data(enc_data)
    except Exception:
        response = build_enc_response(4001, "数据解密失败", {})
        write_push_log(interface, "query_in", request_data=body, response_data=response, result="failed", error_msg="数据解密失败")
        return response

    response = build_enc_response(0, "成功", {
        "pageNo": get_field(inner, "pageNo", "PageNo") or 1,
        "pageCount": 0,
        "itemSize": 0,
        "stationInfos": []
    })
    write_push_log(interface, "query_in", request_data=body, response_data=response, result="success")
    return response


@router.post("/api/query_station_status")
async def query_station_status(
    authorization: str = Header(None),
    req: Request = None,
    db: Session = Depends(get_db)
):
    interface = "query_station_status"
    
    if not authorization or not authorization.startswith("Bearer "):
        response = build_enc_response(4002, "Token错误", {})
        write_push_log(interface, "query_in", response_data=response, result="failed", error_msg="Token错误")
        return response
    if not verify_token(authorization[7:]):
        response = build_enc_response(4002, "Token无效或已过期", {})
        write_push_log(interface, "query_in", response_data=response, result="failed", error_msg="Token无效或已过期")
        return response

    body = await _parse_body(req)
    enc_data = get_field(body, "data", "Data") or ""
    operator_id = get_field(body, "operatorID", "OperatorID")
    ts = get_field(body, "timeStamp", "TimeStamp", "timestamp")
    s = get_field(body, "sig", "Sig")

    if not verify_sig(operator_id, enc_data, ts, get_field(body, "seq", "Seq"), s):
        response = build_enc_response(4001, "签名错误", {})
        write_push_log(interface, "query_in", request_data=body, response_data=response, result="failed", error_msg="签名错误")
        return response

    try:
        inner = decrypt_data(enc_data)
    except Exception:
        response = build_enc_response(4001, "数据解密失败", {})
        write_push_log(interface, "query_in", request_data=body, response_data=response, result="failed", error_msg="数据解密失败")
        return response

    station_ids = get_field(inner, "stationIDs", "StationIDs") or []
    status_list = []
    for sid in station_ids[:50]:
        status_list.append({
            "stationID": sid,
            "connectorStatusInfos": [
                {
                    "connectorID": f"{sid}_01",
                    "status": 1,
                    "parkStatus": 10,
                    "lockStatus": 10
                }
            ]
        })

    response = build_enc_response(0, "成功", {
        "stationStatusInfos": status_list
    })
    write_push_log(interface, "query_in", 
                   request_data={"_raw": body, "_decrypted": inner}, 
                   response_data=response, result="success")
    return response
@router.post("/api/query_station_stats")
async def query_station_stats(
    authorization: str = Header(None),
    req: Request = None
):
    interface = "query_station_stats"
    
    if not authorization or not authorization.startswith("Bearer "):
        response = build_enc_response(4002, "Token错误", {})
        write_push_log(interface, "query_in", response_data=response, result="failed", error_msg="Token错误")
        return response
    if not verify_token(authorization[7:]):
        response = build_enc_response(4002, "Token无效或已过期", {})
        write_push_log(interface, "query_in", response_data=response, result="failed", error_msg="Token无效或已过期")
        return response

    body = await _parse_body(req)
    enc_data = get_field(body, "data", "Data") or ""
    operator_id = get_field(body, "operatorID", "OperatorID")
    ts = get_field(body, "timeStamp", "TimeStamp", "timestamp")
    s = get_field(body, "sig", "Sig")

    if not verify_sig(operator_id, enc_data, ts, get_field(body, "seq", "Seq"), s):
        response = build_enc_response(4001, "签名错误", {})
        write_push_log(interface, "query_in", request_data=body, response_data=response, result="failed", error_msg="签名错误")
        return response

    try:
        decrypt_data(enc_data)
    except Exception:
        response = build_enc_response(4001, "数据解密失败", {})
        write_push_log(interface, "query_in", request_data=body, response_data=response, result="failed", error_msg="数据解密失败")
        return response

    response = build_enc_response(0, "成功", {"stationStats": []})
    write_push_log(interface, "query_in", request_data=body, response_data=response, result="success")
    return response


@router.post("/api/notification_charge_order_info")
async def notification_charge_order(req: Request, db: Session = Depends(get_db)):
    body = await _parse_body(req)
    interface = "notification_charge_order_info"

    start_charge_seq = get_field(body, "startChargeSeq", "StartChargeSeq")
    connector_id = get_field(body, "connectorID", "ConnectorID")

    if start_charge_seq:
        response = build_plain_response(0, "", {
            "startChargeSeq": start_charge_seq,
            "connectorID": connector_id or "",
            "confirmResult": 0
        })
        _save_order_to_db(db, body, body, True)
        write_push_log(
            interface, "push_in",
            request_data={"_mode": "plain", "_raw": body, "_decrypted": body},
            response_data=response, result="success"
        )
        return response

    enc_data = get_field(body, "data", "Data") or ""
    operator_id = get_field(body, "operatorID", "OperatorID")
    ts = get_field(body, "timeStamp", "TimeStamp", "timestamp")
    s = get_field(body, "sig", "Sig")

    sig_ok = verify_sig(operator_id, enc_data, ts, get_field(body, "seq", "Seq"), s)
    if not sig_ok:
        response = build_plain_response(4001, "签名错误", {})
        write_push_log(
            interface, "push_in",
            request_data={"_mode": "encrypted", "_raw": body, "_decrypted": None},
            response_data=response, result="failed", error_msg="签名错误"
        )
        return response

    try:
        order_data = decrypt_data(enc_data)
    except Exception as e:
        response = build_plain_response(4001, "数据解密失败", {})
        write_push_log(
            interface, "push_in",
            request_data={"_mode": "encrypted", "_raw": body, "_decrypted": None},
            response_data=response, result="failed", error_msg=str(e)
        )
        return response

    _save_order_to_db(db, order_data, body, sig_ok)

    response = build_plain_response(0, "", {
        "startChargeSeq": get_field(order_data, "startChargeSeq", "StartChargeSeq") or "",
        "connectorID": get_field(order_data, "connectorID", "ConnectorID") or "",
        "confirmResult": 0
    })
    write_push_log(
        interface, "push_in",
        request_data={"_mode": "encrypted", "_raw": body, "_decrypted": order_data},
        response_data=response, result="success"
    )
    return response


def _parse_datetime(time_str):
    """解析时间字符串为 datetime 对象"""
    if not time_str:
        return None
    try:
        from datetime import datetime
        formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d %H:%M:%S"]
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue
        return None
    except Exception:
        return None


def _save_order_to_db(db: Session, order_data: dict, raw_payload: dict, sig_valid: bool):
    order_status = get_field(order_data, "StartChargeSeqStat", "startChargeSeqStat")
    if order_status:
        try:
            if int(order_status) != 2:
                return None
        except ValueError:
            pass

    start_charge_seq = (
        get_field(order_data, "StartChargeSeq", "startChargeSeq")
        or get_field(order_data, "OutStartChargeSeq", "outStartChargeSeq")
    )
    out_start_charge_seq = get_field(order_data, "OutStartChargeSeq", "outStartChargeSeq")

    connector_id = get_field(order_data, "ConnectorID", "connectorID")
    connector_name = get_field(order_data, "ConnectorName", "connectorName")
    station_id = get_field(order_data, "StationID", "stationID")
    port_no = get_field(order_data, "PortNo", "portNo")
    
    station_name = get_field(order_data, "StationName", "stationName")
    if not station_name and connector_id:
        from app.models.station_connector import Connector
        connector = db.query(Connector).filter(Connector.code == connector_id).first()
        if connector and connector.station:
            station_name = connector.station.name
            print(f"[DEBUG] 订单 {start_charge_seq[:20]}... 通过新表关联充电站: {station_name}")
        else:
            mapping = db.query(StationConnectorMapping).filter(
                StationConnectorMapping.connector_code == connector_id
            ).first()
            if mapping:
                station_name = mapping.station_name
                print(f"[DEBUG] 订单 {start_charge_seq[:20]}... 通过旧表关联充电站: {station_name}")
            else:
                station_name = "未关联"
                print(f"[DEBUG] 订单 {start_charge_seq[:20]}... 未找到充电站映射, connector_id={connector_id}")

    start_time = _parse_datetime(get_field(order_data, "StartTime", "startTime"))
    end_time = _parse_datetime(get_field(order_data, "EndTime", "endTime"))

    total_power = get_field(order_data, "TotalPower", "totalPower")
    if total_power is None:
        total_power = get_field(order_data, "rawTotalPower", "rawTotalPower")

    total_elec = get_field(order_data, "TotalElecMoney", "totalElecMoney", "ElecMoney", "elecMoney")
    total_svc = get_field(order_data, "TotalSeviceMoney", "totalSeviceMoney", "SeviceMoney", "seviceMoney")
    total_money = get_field(order_data, "TotalMoney", "totalMoney")

    stop_reason = get_field(order_data, "StopReason", "stopReason")
    sum_period = get_field(order_data, "SumPeriod", "sumPeriod")
    charge_details = json.dumps(get_field(order_data, "ChargeDetails", "chargeDetails") or [], ensure_ascii=False)

    user_id = get_field(order_data, "UserID", "userID")
    user_name = get_field(order_data, "UserName", "userName")
    user_tel = get_field(order_data, "UserTel", "userTel")
    card_no = get_field(order_data, "CardNo", "cardNo")
    plate_no = get_field(order_data, "plateNo") or get_field(order_data, "PlateNo") \
               or get_field(order_data, "plateNumber") or get_field(order_data, "PlateNumber")

    start_soc = get_field(order_data, "StartSOC", "startSOC")
    end_soc = get_field(order_data, "EndSOC", "endSOC")

    vin = get_field(order_data, "Vin") or get_field(order_data, "vin")

    start_volt = get_field(order_data, "StartVolt", "startVolt")
    start_current = get_field(order_data, "StartCurrent", "startCurrent")
    end_volt = get_field(order_data, "EndVolt", "endVolt")
    end_current = get_field(order_data, "EndCurrent", "endCurrent")

    pay_type = get_field(order_data, "PayType", "payType")
    pay_status = get_field(order_data, "PayStatus", "payStatus")

    existing = db.query(PushRecord).filter(PushRecord.start_charge_seq == start_charge_seq).first()
    if existing:
        existing.push_count += 1
        existing.out_start_charge_seq = out_start_charge_seq
        existing.connector_id = connector_id
        existing.connector_name = connector_name
        existing.station_id = station_id
        existing.station_name = station_name
        existing.port_no = port_no
        existing.start_time = start_time
        existing.end_time = end_time
        existing.total_power = float(total_power) if total_power is not None else None
        existing.total_elec_money = float(total_elec) if total_elec is not None else None
        existing.total_svc_money = float(total_svc) if total_svc is not None else None
        existing.total_money = float(total_money) if total_money is not None else None
        existing.stop_reason = int(stop_reason) if stop_reason is not None else None
        existing.sum_period = int(sum_period) if sum_period is not None else None
        existing.charge_details = charge_details
        existing.user_id = user_id
        existing.user_name = user_name
        existing.user_tel = user_tel
        existing.card_no = card_no
        existing.plate_no = plate_no
        existing.start_soc = float(start_soc) if start_soc is not None else None
        existing.end_soc = float(end_soc) if end_soc is not None else None
        existing.start_volt = float(start_volt) if start_volt is not None else None
        existing.start_current = float(start_current) if start_current is not None else None
        existing.end_volt = float(end_volt) if end_volt is not None else None
        existing.end_current = float(end_current) if end_current is not None else None
        existing.pay_type = int(pay_type) if pay_type is not None else None
        existing.pay_status = int(pay_status) if pay_status is not None else None
        existing.vin = vin
        existing.raw_payload = json.dumps(raw_payload, ensure_ascii=False)
        existing.decrypted_data = json.dumps(order_data, ensure_ascii=False)
        existing.sig_valid = sig_valid
        db.commit()
        db.refresh(existing)
        return existing

    record = PushRecord(
        start_charge_seq=start_charge_seq,
        out_start_charge_seq=out_start_charge_seq,
        connector_id=connector_id,
        connector_name=connector_name,
        station_id=station_id,
        station_name=station_name,
        port_no=port_no,
        start_time=start_time,
        end_time=end_time,
        total_power=float(total_power) if total_power is not None else None,
        total_elec_money=float(total_elec) if total_elec is not None else None,
        total_svc_money=float(total_svc) if total_svc is not None else None,
        total_money=float(total_money) if total_money is not None else None,
        stop_reason=int(stop_reason) if stop_reason is not None else None,
        sum_period=int(sum_period) if sum_period is not None else None,
        charge_details=charge_details,
        user_id=user_id,
        user_name=user_name,
        user_tel=user_tel,
        card_no=card_no,
        plate_no=plate_no,
        start_soc=float(start_soc) if start_soc is not None else None,
        end_soc=float(end_soc) if end_soc is not None else None,
        vin=vin,
        start_volt=float(start_volt) if start_volt is not None else None,
        start_current=float(start_current) if start_current is not None else None,
        end_volt=float(end_volt) if end_volt is not None else None,
        end_current=float(end_current) if end_current is not None else None,
        pay_type=int(pay_type) if pay_type is not None else None,
        pay_status=int(pay_status) if pay_status is not None else None,
        raw_payload=json.dumps(raw_payload, ensure_ascii=False),
        decrypted_data=json.dumps(order_data, ensure_ascii=False),
        sig_valid=sig_valid,
        sync_status="pending_sync",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/api/logs")
async def get_push_logs(limit: int = 50):
    date_str = datetime.now().strftime('%Y-%m-%d')
    log_file = LOG_DIR / f"push_{date_str}.log"

    if not log_file.exists():
        return {"logs": [], "total": 0}

    logs = []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                line = line.strip()
                if line:
                    try:
                        logs.append(json.loads(line))
                    except:
                        pass
    except Exception as e:
        return {"error": str(e)}

    return {"logs": logs, "total": len(logs)}


@router.get("/api/logs/stats")
async def get_push_stats():
    logs = []
    for log_file in LOG_DIR.glob("push_*.log"):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            logs.append(json.loads(line))
                        except:
                            pass
        except:
            pass

    stats = {
        "total": len(logs),
        "success": sum(1 for l in logs if l.get("result") == "success"),
        "failed": sum(1 for l in logs if l.get("result") == "failed"),
        "received": sum(1 for l in logs if l.get("direction") == "push_in"),
    }

    by_interface = {}
    for log in logs:
        iface = log.get("interface", "unknown")
        if iface not in by_interface:
            by_interface[iface] = {"total": 0, "success": 0, "failed": 0}
        by_interface[iface]["total"] += 1
        result = log.get("result")
        if result == "success":
            by_interface[iface]["success"] += 1
        elif result == "failed":
            by_interface[iface]["failed"] += 1

    stats["by_interface"] = by_interface
    return stats