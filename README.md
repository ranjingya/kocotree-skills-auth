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
  "api_key": "kk_abc123...",
  "short_id": "kk_abc12...3xyz",
  "name": "my-app",
  "created_at": "2026-06-08T10:00:00+00:00",
  "expires_at": "2026-09-06T10:00:00+00:00"
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
  -d '{"short_id": "kk_abc12...3xyz"}'
```

## 配置

环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `KKTREE_DB_PATH` | `keys.db` | SQLite 数据库文件路径 |
| `KKTREE_RATE_LIMIT` | `60` | 每个窗口期最大请求数 |
| `KKTREE_RATE_WINDOW` | `60` | 限速窗口时长（秒） |
