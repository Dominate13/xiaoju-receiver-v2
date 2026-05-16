from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import logging

DATABASE_URL = "sqlite:///./data/xiaoju.db"

logger = logging.getLogger(__name__)

def cleanup_old_logs(days_to_keep: int = 10):
    """
    清理指定天数前的日志记录
    
    Args:
        days_to_keep: 保留最近多少天的日志，默认10天
    """
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        result = db.execute(text("SELECT COUNT(*) FROM push_records WHERE received_at < :cutoff"), {"cutoff": cutoff_date})
        count_before = result.scalar()
        
        result2 = db.execute(text("DELETE FROM push_records WHERE received_at < :cutoff"), {"cutoff": cutoff_date})
        deleted_count = result2.rowcount
        
        db.commit()
        
        if deleted_count > 0:
            logger.info(f"已清理 {deleted_count} 条 {days_to_keep} 天前的日志记录")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 已清理 {deleted_count} 条 {days_to_keep} 天前的日志记录")
        else:
            logger.info(f"没有需要清理的日志（保留最近 {days_to_keep} 天）")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 没有需要清理的日志（保留最近 {days_to_keep} 天）")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"清理日志失败: {e}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 清理日志失败: {e}")
        db.rollback()
        return 0
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_old_logs(10)