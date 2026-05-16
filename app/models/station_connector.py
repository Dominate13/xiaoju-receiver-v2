from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base


class Station(Base):
    """充电站表"""
    __tablename__ = "station"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="充电站名称")
    description = Column(String(500), comment="充电站描述")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    connectors = relationship("Connector", back_populates="station")


class Connector(Base):
    """充电枪表"""
    __tablename__ = "connector"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(Integer, ForeignKey("station.id"), nullable=False, comment="所属充电站ID")
    code = Column(String(50), nullable=False, unique=True, comment="充电枪编码")
    name = Column(String(100), comment="充电枪名称")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    station = relationship("Station", back_populates="connectors")


class StationConnectorMapping(Base):
    """充电站-充电枪映射表（旧表，兼容使用）"""
    __tablename__ = "station_connector_mapping"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    station_name = Column(String(100), nullable=False, comment="场站名称")
    connector_code = Column(String(50), nullable=False, unique=True, comment="充电枪编码")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
