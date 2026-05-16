# 部署文档

## 环境要求

### Python 版本

- 推荐版本：Python 3.12+
- 最低版本：Python 3.10

### 依赖组件

- FastAPI >= 0.109.0
- SQLAlchemy >= 2.0.0
- httpx >= 0.26.0

## 部署方式

### 方式一：直接运行

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python init_db.py

# 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8100
```

### 方式二：使用 Windows 脚本

```batch
deploy\start_service.bat
```

## 配置说明

### 必需配置

```env
# 小桔充电密钥
XJ_OPERATOR_ID=your_operator_id
XJ_DATA_SECRET=your_aes_key
XJ_DATA_SECRET_IV=your_aes_iv
XJ_SIG_SECRET=your_hmac_secret

# 氦云配置
H3YUN_ENGINE_CODE=your_engine_code
H3YUN_ENGINE_SECRET=your_engine_secret
H3YUN_SCHEMA_CODE=your_schema_code
```

### 可选配置

```env
# 服务端口（默认8100）
SERVICE_PORT=8100

# 同步配置
SYNC_INTERVAL_SECONDS=30
SYNC_BATCH_SIZE=10
SYNC_MAX_RETRY=3

# 钉钉告警
DINGTALK_WEBHOOK=
DINGTALK_SECRET=
```

## 生产环境部署

### 使用 Windows 服务管理器

将服务注册为 Windows 任务计划程序，实现开机自启：

1. 打开「任务计划程序」
2. 创建基本任务 → 命名为 `xiaoju-receiver-v2`
3. 触发器：计算机启动时
4. 操作：启动程序
   - 程序：`python`
   - 参数：`-m uvicorn app.main:app --host 0.0.0.0 --port 8100`
   - 起始位置：`C:\path\to\xiaoju-receiver-v2`
5. 勾选「不管用户是否登录都要运行」

## 数据库迁移

### 初始化数据库

```bash
python init_db.py
```

### 执行迁移

```bash
python migrate_db.py
```

## 日志管理

### 日志位置

- 推送日志：`logs\push_YYYY-MM-DD.log`
- 服务日志：`logs\service_YYYY-MM-DD.log`

### 日志清理

系统每天凌晨 2:00 自动清理 10 天前的日志。

### 手动清理

```bash
# 清理7天前的日志
python -c "from app.services.log_cleanup import cleanup_old_logs; cleanup_old_logs(7)"
```

## 监控

### 健康检查

```bash
curl http://localhost:8100/health
```

### 查看日志

```bash
# 实时查看服务日志
tail -f logs/service_$(date +%Y-%m-%d).log

# 查看推送日志
tail -f logs/push_$(date +%Y-%m-%d).log
```

## 故障排查

### 服务无法启动

1. 检查端口是否被占用：`netstat -an | findstr 8100`
2. 检查配置文件是否正确
3. 查看服务日志

### 推送接收失败

1. 检查小桔密钥配置
2. 检查网络连通性
3. 查看推送日志

### 同步失败

1. 检查氦云配置
2. 检查网络连通性
3. 查看同步错误信息

## 安全建议

1. 修改默认后台密码
2. 限制管理后台访问 IP
3. 使用 HTTPS
4. 定期备份数据库
5. 定期轮换密钥
