from fastapi import APIRouter, Depends, HTTPException, Request, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from datetime import datetime

from app.models.database import get_db
from app.models.station_connector import Station, Connector, StationConnectorMapping
from app.config import ADMIN_USERNAME, ADMIN_PASSWORD

router = APIRouter()
security = HTTPBasic()

templates = None

def set_templates(tpl):
    global templates
    templates = tpl


def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
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


@router.get("/", response_class=HTMLResponse)
async def station_mapping_page(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(verify_auth)
):
    try:
        stations = db.query(Station).order_by(Station.name).all()
        return templates.TemplateResponse(request, "admin/station_mapping.html", {
            "stations": stations,
            "message": request.query_params.get("message")
        })
    except Exception as e:
        import traceback
        return HTMLResponse(f"<h1>服务器错误</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>", status_code=500)


@router.post("/station/add")
async def add_station(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(verify_auth)
):
    try:
        form_data = await request.form()
        name = form_data.get("station_name")
        description = form_data.get("station_description", "")
        
        if not name:
            raise HTTPException(status_code=400, detail="充电站名称不能为空")
        
        existing = db.query(Station).filter(Station.name == name).first()
        if existing:
            raise HTTPException(status_code=400, detail="该充电站名称已存在")
        
        station = Station(name=name, description=description)
        db.add(station)
        db.commit()
        db.refresh(station)
        
        return templates.TemplateResponse(request, "admin/station_mapping.html", {
            "stations": db.query(Station).order_by(Station.name).all(),
            "message": f"充电站 '{name}' 添加成功"
        })
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return HTMLResponse(f"<h1>服务器错误</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>", status_code=500)


@router.post("/station/edit/{station_id}")
async def edit_station(
    request: Request,
    station_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_auth)
):
    try:
        station = db.query(Station).filter(Station.id == station_id).first()
        if not station:
            raise HTTPException(status_code=404, detail="充电站不存在")
        
        form_data = await request.form()
        name = form_data.get("station_name")
        description = form_data.get("station_description", "")
        
        if not name:
            raise HTTPException(status_code=400, detail="充电站名称不能为空")
        
        existing = db.query(Station).filter(Station.name == name, Station.id != station_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="该充电站名称已存在")
        
        station.name = name
        station.description = description
        db.commit()
        
        return templates.TemplateResponse(request, "admin/station_mapping.html", {
            "stations": db.query(Station).order_by(Station.name).all(),
            "message": f"充电站 '{name}' 修改成功"
        })
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return HTMLResponse(f"<h1>服务器错误</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>", status_code=500)


@router.post("/station/delete/{station_id}")
async def delete_station(
    request: Request,
    station_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_auth)
):
    try:
        station = db.query(Station).filter(Station.id == station_id).first()
        if not station:
            raise HTTPException(status_code=404, detail="充电站不存在")
        
        connectors = db.query(Connector).filter(Connector.station_id == station_id).all()
        for connector in connectors:
            db.delete(connector)
        
        db.delete(station)
        db.commit()
        
        return templates.TemplateResponse(request, "admin/station_mapping.html", {
            "stations": db.query(Station).order_by(Station.name).all(),
            "message": f"充电站 '{station.name}' 及其 {len(connectors)} 个充电枪已删除"
        })
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return HTMLResponse(f"<h1>服务器错误</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>", status_code=500)


@router.post("/connector/add/{station_id}")
async def add_connector(
    request: Request,
    station_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_auth)
):
    try:
        station = db.query(Station).filter(Station.id == station_id).first()
        if not station:
            raise HTTPException(status_code=404, detail="充电站不存在")
        
        form_data = await request.form()
        code = form_data.get("connector_code")
        name = form_data.get("connector_name", "")
        
        if not code:
            raise HTTPException(status_code=400, detail="充电枪编码不能为空")
        
        existing = db.query(Connector).filter(Connector.code == code).first()
        if existing:
            raise HTTPException(status_code=400, detail="该充电枪编码已存在")
        
        connector = Connector(station_id=station_id, code=code, name=name)
        db.add(connector)
        db.commit()
        db.refresh(connector)
        
        return templates.TemplateResponse(request, "admin/station_mapping.html", {
            "stations": db.query(Station).order_by(Station.name).all(),
            "message": f"充电枪 '{code}' 添加成功"
        })
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return HTMLResponse(f"<h1>服务器错误</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>", status_code=500)


@router.post("/connector/edit/{connector_id}")
async def edit_connector(
    request: Request,
    connector_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_auth)
):
    try:
        connector = db.query(Connector).filter(Connector.id == connector_id).first()
        if not connector:
            raise HTTPException(status_code=404, detail="充电枪不存在")
        
        form_data = await request.form()
        code = form_data.get("connector_code")
        name = form_data.get("connector_name", "")
        
        if not code:
            raise HTTPException(status_code=400, detail="充电枪编码不能为空")
        
        existing = db.query(Connector).filter(Connector.code == code, Connector.id != connector_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="该充电枪编码已存在")
        
        connector.code = code
        connector.name = name
        db.commit()
        
        return templates.TemplateResponse(request, "admin/station_mapping.html", {
            "stations": db.query(Station).order_by(Station.name).all(),
            "message": f"充电枪 '{code}' 修改成功"
        })
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return HTMLResponse(f"<h1>服务器错误</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>", status_code=500)


@router.post("/connector/delete/{connector_id}")
async def delete_connector(
    request: Request,
    connector_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(verify_auth)
):
    try:
        connector = db.query(Connector).filter(Connector.id == connector_id).first()
        if not connector:
            raise HTTPException(status_code=404, detail="充电枪不存在")
        
        db.delete(connector)
        db.commit()
        
        return templates.TemplateResponse(request, "admin/station_mapping.html", {
            "stations": db.query(Station).order_by(Station.name).all(),
            "message": f"充电枪 '{connector.code}' 删除成功"
        })
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return HTMLResponse(f"<h1>服务器错误</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>", status_code=500)


@router.post("/export")
async def export_data(
    db: Session = Depends(get_db),
    username: str = Depends(verify_auth)
):
    try:
        import io
        
        output = io.StringIO()
        output.write("\ufeff")
        output.write("充电站名称,充电枪编码,充电枪名称\n")
        
        stations = db.query(Station).order_by(Station.name).all()
        for station in stations:
            for connector in station.connectors:
                connector_name = connector.name or ""
                connector_code = f"'{connector.code}"
                output.write(f"{station.name},{connector_code},{connector_name}\n")
        
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename=station_mapping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
    except Exception as e:
        import traceback
        return HTMLResponse(f"<h1>导出失败</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>", status_code=500)


@router.post("/import")
async def import_data(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    username: str = Depends(verify_auth)
):
    try:
        import csv
        contents = await file.read()
        decoded = contents.decode('utf-8')
        
        reader = csv.reader(decoded.splitlines())
        next(reader)
        
        success_count = 0
        skip_count = 0
        error_count = 0
        errors = []
        
        for row in reader:
            if len(row) < 2:
                continue
            
            station_name = row[0].strip()
            connector_code = row[1].strip()
            connector_name = row[2].strip() if len(row) > 2 else ""
            
            if not station_name or not connector_code:
                continue
            
            station = db.query(Station).filter(Station.name == station_name).first()
            if not station:
                station = Station(name=station_name)
                db.add(station)
                db.commit()
                db.refresh(station)
            
            existing_connector = db.query(Connector).filter(Connector.code == connector_code).first()
            if existing_connector:
                skip_count += 1
                errors.append(f"跳过重复充电枪: {connector_code}")
                continue
            
            connector = Connector(station_id=station.id, code=connector_code, name=connector_name)
            db.add(connector)
            success_count += 1
        
        db.commit()
        
        message = f"导入完成: 成功 {success_count} 条, 跳过 {skip_count} 条, 错误 {error_count} 条"
        if errors:
            message += "\n" + "\n".join(errors[:10])
        
        return templates.TemplateResponse(request, "admin/station_mapping.html", {
            "stations": db.query(Station).order_by(Station.name).all(),
            "message": message
        })
    except Exception as e:
        import traceback
        return HTMLResponse(f"<h1>导入失败</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>", status_code=500)


@router.get("/api/list")
async def list_mappings(
    db: Session = Depends(get_db),
    username: str = Depends(verify_auth)
):
    stations = db.query(Station).order_by(Station.name).all()
    result = []
    for station in stations:
        connectors = [{
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "created_at": c.created_at.isoformat()
        } for c in station.connectors]
        result.append({
            "id": station.id,
            "name": station.name,
            "description": station.description,
            "connector_count": len(connectors),
            "connectors": connectors
        })
    return result


def get_station_name_by_connector(db: Session, connector_code: str) -> str:
    """根据充电枪编码获取场站名称"""
    if not connector_code:
        return "未关联"
    
    try:
        connector = db.query(Connector).filter(Connector.code == connector_code).first()
        if connector and connector.station:
            return connector.station.name
        
        mapping = db.query(StationConnectorMapping).filter(
            StationConnectorMapping.connector_code == connector_code
        ).first()
        return mapping.station_name if mapping else "未关联"
    except Exception:
        return "未关联"
