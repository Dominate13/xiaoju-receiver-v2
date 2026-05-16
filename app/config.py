import os
from dotenv import load_dotenv

# 加载 .env 文件
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
load_dotenv(env_path)

# 服务配置
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8100"))

# 小桔密钥
OPERATOR_ID = os.getenv("XJ_OPERATOR_ID")
OPERATOR_SECRET = os.getenv("XJ_OPERATOR_SECRET")
DATA_SECRET = os.getenv("XJ_DATA_SECRET")
DATA_SECRET_IV = os.getenv("XJ_DATA_SECRET_IV")
SIG_SECRET = os.getenv("XJ_SIG_SECRET")

# 数据库
DB_URL = os.getenv("DB_URL", "sqlite:///./data/xiaoju.db")

# 后台管理认证
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456")

# 氚云 OpenAPI 配置
H3YUN_ENGINE_CODE = os.getenv("H3YUN_ENGINE_CODE")
H3YUN_ENGINE_SECRET = os.getenv("H3YUN_ENGINE_SECRET")
H3YUN_SCHEMA_CODE = os.getenv("H3YUN_SCHEMA_CODE", "ChargeOrderForm")

# 同步任务配置
SYNC_INTERVAL_SECONDS = int(os.getenv("SYNC_INTERVAL_SECONDS", "30"))
SYNC_BATCH_SIZE = int(os.getenv("SYNC_BATCH_SIZE", "10"))
SYNC_MAX_RETRY = int(os.getenv("SYNC_MAX_RETRY", "3"))

# 钉钉告警配置
DINGTALK_WEBHOOK = os.getenv("DINGTALK_WEBHOOK")
DINGTALK_SECRET = os.getenv("DINGTALK_SECRET")

# 健康检查配置
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))
HEALTH_CHECK_THRESHOLD = int(os.getenv("HEALTH_CHECK_THRESHOLD", "3"))


def validate_config() -> list:
    """验证配置完整性，返回错误列表（空列表表示通过）"""
    errors = []

    # 检查端口范围
    if not (1 <= SERVICE_PORT <= 65535):
        errors.append(f"SERVICE_PORT 端口值无效: {SERVICE_PORT}")

    # 检查同步间隔
    if SYNC_INTERVAL_SECONDS < 5:
        errors.append(f"SYNC_INTERVAL_SECONDS 建议不小于5秒: {SYNC_INTERVAL_SECONDS}")

    # 检查数据库URL
    if not DB_URL:
        errors.append("DB_URL 未配置")

    return errors
