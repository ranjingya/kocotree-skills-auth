# kocotree-skills-auth

基于 Flask + SQLite 的轻量 API Key 认证服务。

## Docker 部署

```bash
docker compose up -d
```

数据持久化到宿主机 `/opt/kocotree-skills-auth/data/keys.db`。

## 接口

### 创建 Key

```bash
curl -X POST http://localhost:5050/api/v1/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app", "expires_in_days": 90}'
```

响应（原始 key 仅在此响应中出现一次）：

```json
{
  "id": 1,
  "api_key": "kk_abc123...",
  "short_id": "kk_abc12...3xyz",
  "name": "my-app",
  "created_at": "2026-06-08T10:00:00+00:00",
  "expires_at": "2026-09-06T10:00:00+00:00",
  "expires_ts": 1757296800
}
```

### 验证 Key（供其他服务调用）

```bash
curl http://localhost:5050/api/v1/auth/verify \
  -H "Authorization: Bearer kk_abc123..."
```

### 列出所有 Key（需认证）

```bash
curl http://localhost:5050/api/v1/keys \
  -H "Authorization: Bearer kk_abc123..."
```

### 撤销 Key（需认证）

```bash
curl -X POST http://localhost:5050/api/v1/keys/revoke \
  -H "Authorization: Bearer kk_abc123..." \
  -H "Content-Type: application/json" \
  -d '{"id": 1}'
```

## 客户端集成

`examples/` 目录提供两个独立示例文件，供 skill 和其他后端服务复制使用。依赖 `requests` 库。

### 后端装饰器（auth_verify.py）

其他 Flask 后端服务通过 `@require_auth` 装饰器接入认证

装饰器逻辑：
- 请求无 `Authorization` → 调 auth 服务创建 key → 返回 `{code: 100, data: {api_key, ...}, msg: "key_created"}`
- 请求有 `Authorization` → 调 auth 服务校验 → 通过执行接口，不通过返回 401

环境变量 `AUTH_SERVICE_URL`，默认 `http://kocotree-skills-auth:5050`。

### Skill 客户端（auth_client.py）

Skill 通过 `AuthClient` 自动管理 key

首次请求时，后端返回 `code=100`（新创建的 key），客户端自动保存到 `~/.kocotree-skills/auth.json` 并重试。后续请求自动带上 key。

环境变量 `AUTH_KEY_PATH` 可覆盖本地存储路径。

## 配置

环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `KKTREE_DB_PATH` | `keys.db` | SQLite 数据库文件路径 |
| `KKTREE_RATE_LIMIT` | `60` | 每个窗口期最大请求数 |
| `KKTREE_RATE_WINDOW` | `60` | 限速窗口时长（秒） |
| `AUTH_SERVICE_URL` | `http://kocotree-skills-auth:5050` | auth 服务地址（后端装饰器用） |
| `AUTH_KEY_PATH` | `~/.kocotree-skills/auth.json` | 本地 key 存储路径（skill 客户端用） |
