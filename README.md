# kocotree-skills-auth

基于 Flask 的轻量认证服务，通过飞书 OAuth 验证企业员工身份。

## 认证流程

```
Skill 脚本（用户机器）              auth 服务（Docker）           飞书
  │                                   │                         │
  ├─ GET /auth/login ────────────────→│                         │
  │←── 返回授权 URL + state ─────────│                         │
  ├─ 浏览器打开授权 URL ──────────────────────────────────────→│
  │                                   │←── 回调 code + state ←─│
  │                                   │── 用 code 换 token ───→│
  │                                   │←── 返回 token ────────←│
  │                                   │（暂存 token，等待轮询）  │
  ├─ GET /auth/poll?state=xxx ───────→│                         │
  │←── access_token + refresh_token ─│                         │
  │                                   │                         │
  ├─ 请求其他后端（带 token）         │                         │
  │   其他后端 → GET /auth/verify ──→│── 验证 token ─────────→│
  │                      ←── 通过/拒绝│                         │
```

## Docker 部署

```bash
docker compose up -d
```

需要在 `.env` 或 `docker-compose.yaml` 中配置 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`。

## 接口

### 获取授权链接

```bash
curl http://localhost:5050/api/v1/auth/login
```

返回飞书 OAuth 授权 URL 和 state。

### 飞书回调

```
GET /api/v1/auth/redirect?code=xxx&state=xxx
```

飞书授权后自动回调到此端点，auth 服务换取 token 后暂存，等待客户端轮询。

### 轮询获取 token

```bash
curl "http://localhost:5050/api/v1/auth/poll?state=xxx"
```

客户端用 state 轮询，授权完成前返回 `code=202`，完成后返回 token 数据。

### 刷新 token

```bash
curl -X POST http://localhost:5050/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "ur-xxx"}'
```

### 验证 token（供其他服务调用）

```bash
curl http://localhost:5050/api/v1/auth/verify \
  -H "Authorization: Bearer u-xxx"
```

### 用授权码换 token（备用）

```bash
curl -X POST http://localhost:5050/api/v1/auth/callback \
  -H "Content-Type: application/json" \
  -d '{"code": "授权码"}'
```

客户端自行接收回调时使用，正常流程通过 `/auth/redirect` + `/auth/poll` 完成。

## 客户端集成

`examples/` 目录提供两个独立示例文件，供 skill 和其他后端服务复制使用。依赖 `requests` 库。

### Skill 客户端（auth_client.py）

```python
from auth_client import with_auth, get_headers

@with_auth
def fetch_data():
    return requests.get("http://other-service/api/data", headers=get_headers())

result = fetch_data()
```

首次运行自动打开浏览器飞书授权，每 5 秒轮询 auth 服务获取 token，保存到 `~/.kocotree-skills/auth.json`。后续请求自动带 token，过期自动刷新。

### 后端装饰器（auth_verify.py）

```python
from auth_verify import require_auth

@app.route("/my-api")
@require_auth
def my_api():
    return jsonify({"code": 0, "data": "hello", "msg": "ok"})
```

透传 Authorization header 到 auth 服务校验，通过则执行接口，不通过返回 401。

## 配置

### auth 服务（环境变量）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `FEISHU_APP_ID` | - | 飞书应用 ID（必填） |
| `FEISHU_APP_SECRET` | - | 飞书应用 Secret（必填） |
| `FEISHU_REDIRECT_URI` | `http://localhost:5050/api/v1/auth/redirect` | OAuth 回调地址 |
| `RATE_LIMIT` | `60` | 每个窗口期最大请求数 |
| `RATE_WINDOW` | `60` | 限速窗口时长（秒） |

### 客户端（环境变量）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AUTH_SERVICE_URL` | `http://localhost:5050` | auth 服务地址 |
| `AUTH_TOKEN_PATH` | `~/.kocotree-skills/auth.json` | 本地 token 存储路径 |
