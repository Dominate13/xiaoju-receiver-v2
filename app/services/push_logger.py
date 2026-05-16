import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from logging.handlers import RotatingFileHandler
import os


class PushLogger:
    """简化日志服务 - 只记录关键事件"""
    
    def __init__(self, log_dir: str = None):
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "logs")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志文件名（按日期）
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.log_file = self.log_dir / f"service_{self.today}.log"
        
        # 清理过期日志（保留30天）
        self._cleanup_old_logs(30)
    
    def _cleanup_old_logs(self, days: int = 30):
        """清理超过指定天数的日志文件"""
        try:
            cutoff = datetime.now() - timedelta(days=days)
            for log_file in self.log_dir.glob("service_*.log"):
                if log_file.stat().st_mtime < cutoff.timestamp():
                    log_file.unlink()
        except Exception:
            pass
    
    def _get_logger(self):
        """获取当日logger实例"""
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self.today:
            # 新的一天，重置logger
            self.today = today
            self.log_file = self.log_dir / f"service_{self.today}.log"

        logger = logging.getLogger(f"push_{self.today}")
        # 防止重复添加 handler（跨天切换或重复调用时）
        if not logger.handlers:
            handler = logging.FileHandler(self.log_file, encoding="utf-8")
            formatter = logging.Formatter("%(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            # 禁止传播到根 logger，避免日志重复
            logger.propagate = False

        return logger
    
    def _write(self, level: str, msg: str, **details):
        """写入日志"""
        entry = {
            "time": datetime.now().isoformat(),
            "level": level,
            "msg": msg,
            "details": details
        }
        try:
            self._get_logger().info(json.dumps(entry, ensure_ascii=False))
        except Exception:
            pass
    
    def info(self, msg: str, **details):
        """信息级别"""
        self._write("INFO", msg, **details)
    
    def warning(self, msg: str, **details):
        """警告级别"""
        self._write("WARNING", msg, **details)
    
    def error(self, msg: str, **details):
        """错误级别"""
        self._write("ERROR", msg, **details)
    
    def critical(self, msg: str, **details):
        """严重错误级别"""
        self._write("CRITICAL", msg, **details)
    
    # === 业务事件快捷方法 ===
    
    def service_started(self, port: int):
        """服务启动"""
        self.info("服务启动", port=port)
    
    def service_stopped(self):
        """服务停止"""
        self.info("服务停止")
    
    def push_received(self, seq: str, interface: str):
        """推送接收"""
        self.info("推送接收", seq=seq, interface=interface)
    
    def push_success(self, seq: str):
        """推送处理成功"""
        self.info("推送处理成功", seq=seq)
    
    def push_failed(self, seq: str, error: str):
        """推送处理失败"""
        self.warning("推送处理失败", seq=seq, error=error)
    
    def sync_success(self, seq: str, cost_ms: int = None):
        """同步成功"""
        self.info("同步成功", seq=seq, cost_ms=cost_ms)
    
    def sync_failed(self, seq: str, error: str):
        """同步失败"""
        self.error("同步失败", seq=seq, error=error)
    
    def sync_skipped(self, seq: str, reason: str):
        """同步跳过"""
        self.warning("同步跳过", seq=seq, reason=reason)
    
    def health_check_failed(self, consecutive_failures: int):
        """健康检查失败"""
        self.error("健康检查失败", consecutive_failures=consecutive_failures)
    
    def service_restarted(self):
        """服务重启"""
        self.warning("服务已自动重启")


# 全局单例
_logger = None

def get_logger() -> PushLogger:
    """获取全局日志实例"""
    global _logger
    if _logger is None:
        _logger = PushLogger()
    return _logger
