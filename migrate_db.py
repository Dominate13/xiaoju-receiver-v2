#!/usr/bin/env python3
"""数据库迁移脚本 - 备份旧数据并创建新数据库"""
import os
import sys
import shutil
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.database import engine, Base, SessionLocal
from app.models.order import PushRecord
from app.models.station_connector import StationConnectorMapping

def backup_database():
    """备份旧数据库"""
    backup_name = f"data/xiaoju_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    if os.path.exists("data/xiaoju.db"):
        shutil.copy2("data/xiaoju.db", backup_name)
        print(f"已备份数据库到: {backup_name}")
        return backup_name
    return None

def create_new_database():
    """创建新数据库表"""
    print("正在创建新数据库表...")
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("新数据库表创建成功！")
    
    # 检查创建的表
    inspector = engine.dialect.inspector(engine)
    tables = inspector.get_table_names()
    print(f"已创建的表: {tables}")

def restore_data(backup_path):
    """从备份恢复数据"""
    if not backup_path or not os.path.exists(backup_path):
        print("没有备份文件可恢复")
        return
    
    print("正在从备份恢复数据...")
    
    # 使用SQLite直接操作
    import sqlite3
    
    # 连接旧数据库
    old_conn = sqlite3.connect(backup_path)
    old_cursor = old_conn.cursor()
    
    # 连接新数据库
    new_conn = sqlite3.connect("data/xiaoju.db")
    new_cursor = new_conn.cursor()
    
    # 恢复 push_record 表数据
    try:
        old_cursor.execute("SELECT * FROM push_record")
        rows = old_cursor.fetchall()
        if rows:
            # 获取列名
            old_cursor.execute("PRAGMA table_info(push_record)")
            columns = [col[1] for col in old_cursor.fetchall()]
            placeholders = ",".join("?" * len(columns))
            new_cursor.executemany(f"INSERT INTO push_record ({','.join(columns)}) VALUES ({placeholders})", rows)
            new_conn.commit()
            print(f"已恢复 {len(rows)} 条 push_record 记录")
    except Exception as e:
        print(f"恢复 push_record 失败: {e}")
    
    # 恢复 station_connector_mapping 表数据（如果存在）
    try:
        old_cursor.execute("SELECT * FROM station_connector_mapping")
        rows = old_cursor.fetchall()
        if rows:
            old_cursor.execute("PRAGMA table_info(station_connector_mapping)")
            columns = [col[1] for col in old_cursor.fetchall()]
            placeholders = ",".join("?" * len(columns))
            new_cursor.executemany(f"INSERT INTO station_connector_mapping ({','.join(columns)}) VALUES ({placeholders})", rows)
            new_conn.commit()
            print(f"已恢复 {len(rows)} 条 station_connector_mapping 记录")
    except Exception as e:
        print(f"恢复 station_connector_mapping 失败: {e}")
    
    old_conn.close()
    new_conn.close()
    print("数据恢复完成！")

def main():
    print("===== 数据库迁移开始 =====")
    
    # 1. 备份旧数据库
    backup_path = backup_database()
    
    # 2. 删除旧数据库
    if os.path.exists("data/xiaoju.db"):
        os.remove("data/xiaoju.db")
        print("已删除旧数据库")
    
    # 3. 创建新数据库
    create_new_database()
    
    # 4. 恢复数据
    restore_data(backup_path)
    
    print("===== 数据库迁移完成 =====")

if __name__ == "__main__":
    main()
