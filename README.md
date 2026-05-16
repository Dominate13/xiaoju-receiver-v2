# xiaoju-receiver-v2

> 小桔充电数据集成中间件 | FastAPI + SQLite + 氚云 OpenAPI

[English](#english) | [中文](#中文)

---

## 中文

### 项目简介

xiaoju-receiver-v2 是一个轻量级的充电运营数据集成中间件，负责接收小桔充电平台的加密订单推送，完成数据解密、验签、存储，并同步至氚云（H3YUN）业务系统。

目的是将订单数据传回公司内部 OA，如要对接其他业务系统可在此基础上做二次开发。

> **备注**：小桔平台推送的订单数据不含场站信息。为关联场站和充电枪，项目增加了「映射管理」页面，通过手动设置场站与充电枪编号的对应关系来补全场站名称和枪别名。
> 需注意：推送数据中的枪编号与充电桩上设置的枪号不同，需根据建站时申请的资产码核对确认。

> **项目状态**：已在生产环境稳定运行超过一周，接收数据正常、同步稳定。

### 核心特性

- **安全可靠**：AES-128-CBC 数据加密 + HMAC-SHA256 签名验签
- **幂等防重**：本地 + 云端双重幂等检查，避免重复同步
- **异步同步**：定时任务 + 失败重试机制，保障数据一致性
- **后台管理**：Web 管理界面，支持订单查询、状态监控、手动重试
- **健康检查**：/health 接口监控服务状态

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     外部系统                                  │
│  ┌──────────────┐                      ┌──────────────┐   │
│  │  小桔充电平台  │                      │    氚云平台    │   │
│  └──────┬───────┘                      └──────┬───────┘   │
└─────────┼─────────────────────────────────────┼───────────┘
          │ POST /api/push                      │ HTTP API
          ▼                                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI 应用层                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │ PushReceiver│  │   Admin     │  │    SyncAdmin    │    │
│  │   Router   │  │   Router    │  │     Router      │    │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘    │
│         │                │                    │              │
│         ▼                ▼                    ▼              │
│  ┌─────────────┐  ┌─────────────────────────────────────┐  │
│  │PushHandler  │  │            SyncWorker               │  │
│  │(解密/验签)  │  │         (定时同步任务)                │  │
│  └──────┬──────┘  └──────────────────┬──────────────────┘  │
│         │                             │                     │
│         ▼                             ▼                     │
│  ┌─────────────┐              ┌─────────────┐              │
│  │ CryptoUtil  │              │ H3yunClient │              │
│  │(AES/HMAC)  │              │(OpenAPI)    │              │
│  └─────────────┘              └─────────────┘              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   SQLite DB     │
                    │  (本地数据缓冲)  │
                    └─────────────────┘
```

### 技术栈

| 组件 | 技术选型 |
|------|----------|
| Web 框架 | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 |
| 数据库 | SQLite (开发) / PostgreSQL (生产) |
| HTTP 客户端 | httpx (异步) |
| 加密 | pycryptodome |
| 模板引擎 | Jinja2 |
| 定时任务 | schedule |

### 快速开始

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

#### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入实际配置
```

#### 3. 初始化数据库

```bash
python init_db.py
```

#### 4. 启动服务

```bash
# 开发模式
python -m uvicorn app.main:app --reload --port 8100

# 生产模式
python -m uvicorn app.main:app --host 0.0.0.0 --port 8100
```

#### 5. 访问管理后台

- 地址：http://localhost:8100/admin
- 默认账号：`admin` / `123456`

### 配置说明

| 配置项 | 说明 | 必填 |
|--------|------|------|
| `XJ_OPERATOR_ID` | 小桔运营商 ID | ✓ |
| `XJ_DATA_SECRET` | AES 加密密钥（32字符）| ✓ |
| `XJ_DATA_SECRET_IV` | AES 初始化向量（16字符）| ✓ |
| `XJ_SIG_SECRET` | HMAC 签名密钥 | ✓ |
| `H3YUN_ENGINE_CODE` | 氚云引擎编码 | ✓ |
| `H3YUN_ENGINE_SECRET` | 氚云引擎密钥 | ✓ |
| `H3YUN_SCHEMA_CODE` | 氚云表单编码 | ✓ |

### API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/push` | POST | 接收小桔充电订单推送 |
| `/api/push/test` | GET | 测试推送接口 |
| `/health` | GET | 健康检查 |
| `/admin` | GET | 后台管理首页 |
| `/admin/orders` | GET | 订单列表查询 |
| `/admin/sync/status` | GET | 同步状态 |
| `/admin/sync/retry` | POST | 重试失败记录 |

### 注意事项

- **密钥说明**：小桔开放平台密钥需联系平台方申请；氚云密钥从开发后台获取

---
### 项目截图

<img width="1200" height="973" alt="管理后台1" src="https://github.com/user-attachments/assets/f3fb222c-9898-4fc9-a7fc-7180017a59e7" />

<img width="1200" height="963" alt="订单查询1" src="https://github.com/user-attachments/assets/640b1a65-b47e-4d37-bde3-919cfd7d2f7e" />

<img width="1200" height="946" alt="映射管理1" src="https://github.com/user-attachments/assets/91562323-9c5a-4a12-9b78-3f2b35e84d89" />

> 截图说明：管理后台可查看运行状态与同步状态；订单查询支持按条件筛选；映射管理用于关联充电枪与场站。

---

### Roadmap

#### Planned: Dynamic Mapping Engine
- [ ] 支持映射规则的热更新，无需重启服务
- [ ] 提供映射规则的导入/导出功能（Excel/JSON）
- [ ] 添加映射冲突检测和告警机制
- [ ] 考虑引入规则引擎（如 JSONLogic）提升灵活性

#### Planned: Schema Optimization
- [ ] 精简数据库 schema，移除历史兼容字段
- [ ] 引入数据版本管理，支持 schema migration
- [ ] 考虑 PostgreSQL 迁移，支撑更大规模数据
- [ ] 添加字段级数据质量监控

#### Future Enhancements
- [ ] **多平台支持**：扩展支持特来电、星星充电等平台
- [ ] **消息队列**：引入 Redis/RabbitMQ 解耦，提升并发能力
- [ ] **监控告警**：完善 Prometheus + Grafana 监控体系
- [ ] **单元测试**：补充关键模块测试，CI/CD 集成
- [ ] **监控告警**：完善服务监控和异常告警机制
- [ ] **多场站支持**：扩展支持多充电场站统一管理

### 项目结构

```
xiaoju-receiver-v2/
├── app/
│   ├── main.py              # 应用入口
│   ├── config.py            # 配置管理
│   ├── models/              # 数据模型
│   ├── routes/              # API 路由
│   └── services/           # 核心服务
│       ├── crypto.py       # 加解密工具
│       ├── h3yun_client.py # 氚云客户端
│       └── sync_worker.py  # 同步工作器
├── deploy/                  # 部署脚本
├── docs/                    # 文档
├── static/                  # 静态资源
├── .env.example            # 配置示例
├── requirements.txt         # 依赖清单
└── LICENSE                 # MIT 协议
```

### License

MIT License - 详见 [LICENSE](LICENSE) 文件

### 开发说明

本项目由 **WorkBuddy + Trae** 协同开发，代码和方案均仅供学习参考。
如需用于生产环境，请根据实际情况调整配置和部署方式。

---

## English

### Introduction

xiaoju-receiver-v2 is a lightweight middleware for EV charging data integration. It receives encrypted order push notifications from Xiaoju Charging platform, decrypts and validates them, stores locally, and syncs to H3YUN (a business process management platform).

> **Note**: The push data from Xiaoju platform does not include station information. A "Mapping Management" page is added to manually associate charging guns with stations. Note that the gun ID in push data differs from the physical gun number on the charger — verify using the asset code from station setup.

> **Project Status**: Stable in production for over 1 week, with normal data reception and reliable sync.

### Key Features

- **Security**: AES-128-CBC encryption + HMAC-SHA256 signature verification
- **Idempotency**: Local + cloud dual idempotency checks
- **Async Sync**: Scheduled tasks + retry mechanism
- **Admin UI**: Web-based management interface
- **Health Check**: /health endpoint for monitoring

### Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
python init_db.py
python -m uvicorn app.main:app --reload --port 8100
```

### License

MIT License - see [LICENSE](LICENSE)

### Development

This project was developed collaboratively using **WorkBuddy + Trae**. Code and designs are for learning reference only. If using in production, please adjust configurations and deployment accordingly.
