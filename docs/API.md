# API 文档

## 基础信息

- 基础路径：`http://localhost:8100`
- 数据格式：JSON
- 编码：UTF-8

## 接口列表

### 1. 推送接收接口

#### POST /api/push

接收小桔充电平台的订单推送。

**请求头**：
```
Content-Type: application/json
```

**请求体**：
```json
{
  "InterfaceName": "ChargeOrderNotify",
  "EncryptedData": "base64_encrypted_string",
  "Signature": "hmac_signature",
  "timestamp": 1699999999
}
```

**响应**：
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "seq": "ORDER123456789",
    "id": 123
  }
}
```

**错误码**：
| code | 说明 |
|------|------|
| 0 | 成功 |
| 1001 | 签名验证失败 |
| 1002 | 解密失败 |
| 1003 | 数据格式错误 |
| 1004 | 服务器内部错误 |

#### GET /api/push/test

测试推送接口是否正常。

**响应**：
```json
{
  "status": "ok",
  "message": "push endpoint is ready"
}
```

---

### 2. 场站接口

#### GET /stations

获取所有充电站列表。

**响应**：
```json
{
  "code": 0,
  "data": [
    {
      "id": 1,
      "name": "充电站A",
      "description": "描述"
    }
  ]
}
```

#### POST /stations

创建充电站。

**请求体**：
```json
{
  "name": "新充电站",
  "description": "描述"
}
```

#### GET /connectors

获取所有充电枪列表。

**响应**：
```json
{
  "code": 0,
  "data": [
    {
      "id": 1,
      "station_id": 1,
      "code": "C001",
      "name": "1号枪"
    }
  ]
}
```

#### POST /connectors

创建充电枪。

**请求体**：
```json
{
  "station_id": 1,
  "code": "C001",
  "name": "1号枪"
}
```

---

### 3. 后台管理接口

#### GET /admin

后台管理首页。

**响应**：HTML 页面

#### GET /admin/orders

查询订单列表。

**查询参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码（默认1） |
| page_size | int | 每页数量（默认20） |
| status | string | 同步状态筛选 |
| start_date | string | 开始日期 |
| end_date | string | 结束日期 |
| keyword | string | 关键词搜索 |

**响应**：
```json
{
  "code": 0,
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

#### GET /admin/orders/{id}

获取订单详情。

**响应**：
```json
{
  "code": 0,
  "data": {
    "id": 1,
    "start_charge_seq": "ORDER123456789",
    "station_name": "充电站A",
    "connector_name": "1号枪",
    "total_power": 50.5,
    "total_money": 35.5,
    "sync_status": "synced",
    "...": "..."
  }
}
```

#### DELETE /admin/orders/{id}

删除订单。

**响应**：
```json
{
  "code": 0,
  "msg": "删除成功"
}
```

---

### 4. 同步管理接口

#### GET /admin/sync/status

获取同步任务状态。

**响应**：
```json
{
  "code": 0,
  "data": {
    "running": true,
    "last_sync": "2024-01-01 12:00:00",
    "pending_count": 5,
    "failed_count": 2,
    "synced_count": 100
  }
}
```

#### POST /admin/sync/run

手动触发同步。

**响应**：
```json
{
  "code": 0,
  "msg": "同步任务已触发"
}
```

#### POST /admin/sync/retry

重试失败的同步记录。

**请求体**：
```json
{
  "ids": [1, 2, 3]
}
```

**响应**：
```json
{
  "code": 0,
  "msg": "重试任务已触发",
  "data": {
    "count": 3
  }
}
```

---

### 5. 映射管理接口

#### GET /admin/station_mapping

映射管理页面。

**响应**：HTML 页面

---

### 6. 健康检查

#### GET /health

服务健康检查。

**响应**：
```json
{
  "status": "healthy",
  "database": "ok",
  "sync_worker": "running"
}
```

**状态值**：
| 状态 | 说明 |
|------|------|
| healthy | 服务正常 |
| unhealthy | 服务异常 |

---

### 7. 根路径

#### GET /

服务信息。

**响应**：
```json
{
  "message": "小桔充电推送接收服务运行中",
  "version": "2.0.0"
}
```
