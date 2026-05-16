#!/usr/bin/env python3
"""数据库初始化脚本"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.database import init_db, engine, Base
from app.models.order import PushRecord
from app.models.station_connector import StationConnectorMapping

def main():
    print("正在初始化数据库...")
    
    # 创建表
    Base.metadata.create_all(bind=engine)
    
    print("数据库表创建成功！")
    print("已创建的表:", engine.table_names() if hasattr(engine, 'table_names') else "无法获取")

if __name__ == "__main__":
    main()
