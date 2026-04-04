# System API

## 错误格式

所有接口在发生业务错误时统一返回 JSON 格式：

```json
{
  "error": "错误描述"
}
```

HTTP 状态码含义：

- `400` 请求参数不合法
- `404` 资源不存在（或已软删除）
- `409` 操作冲突（如删除仍被引用的题目、恢复未被删除的记录等）
- `500` 内部错误
- `503` 服务不可用（数据库不可达）

## Endpoints

### `GET /health`

健康检查接口。会执行一次数据库连通性探测：

- 成功时返回 `200`：

```json
{
  "status": "ok",
  "service": "qb_api_rust"
}
```

- 数据库不可达时返回 `503`：

```json
{
  "error": "database is unreachable"
}
```
