# Admin API

管理员接口用于查看软删除数据、恢复软删除记录、执行最终垃圾回收，以及用户管理。

说明：

- 所有 `/admin/*` 接口需要 `admin` 角色的 JWT access token
- 通过 `Authorization: Bearer <token>` 头传递认证信息
- `deleted_by` 返回执行删除操作的用户 UUID（鉴权上线前创建的记录该字段为 `null`）

## Endpoints

### `GET /admin/questions`

按条件分页查询题目，支持查看活跃、已删除或全部记录。

支持的 query 参数：

- `state`
  - `active` | `deleted` | `all`
  - 默认 `all`
- `paper_id`
- `category`
- `tag`
- `score_min`
- `score_max`
- `difficulty_tag`
- `difficulty_min`
- `difficulty_max`
- `q`
- `limit`（默认 20，最大 100）
- `offset`（默认 0）

响应格式（分页包裹）：

```json
{
  "items": [ ... ],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

`items` 中每个元素在普通题目摘要字段之外追加：

- `deleted_at`
- `deleted_by`
- `is_deleted`

### `GET /admin/questions/{question_id}`

返回单个题目的完整详情，不区分是否已软删除。

返回值会在普通题目详情字段之外追加：

- `deleted_at`
- `deleted_by`
- `is_deleted`

### `POST /admin/questions/{question_id}/restore`

恢复一个已软删除的题目。

- 如果题目不存在，返回 `404`
- 如果题目未被软删除，返回 `409`

成功时返回恢复后的管理员题目详情。

### `GET /admin/papers`

按条件分页查询试卷，支持查看活跃、已删除或全部记录。

支持的 query 参数：

- `state`
  - `active` | `deleted` | `all`
  - 默认 `all`
- `question_id`
- `category`
- `tag`
- `q`
- `limit`（默认 20，最大 100）
- `offset`（默认 0）

响应格式（分页包裹）：

```json
{
  "items": [ ... ],
  "total": 12,
  "limit": 20,
  "offset": 0
}
```

`items` 中每个元素在普通试卷摘要字段之外追加：

- `deleted_at`
- `deleted_by`
- `is_deleted`

### `GET /admin/papers/{paper_id}`

返回单个试卷的完整详情，不区分是否已软删除。

返回值会在普通试卷详情字段之外追加：

- `deleted_at`
- `deleted_by`
- `is_deleted`

### `POST /admin/papers/{paper_id}/restore`

恢复一个已软删除的试卷。

- 如果试卷不存在，返回 `404`
- 如果试卷未被软删除，返回 `409`
- 如果试卷引用了已删除题目，或这些题目当前不再满足试卷创建约束，返回 `409`

成功时返回恢复后的管理员试卷详情。

### `POST /admin/garbage-collections/preview`

预演垃圾回收，但不会真正提交删除。

请求体：

```json
{}
```

返回值：

```json
{
  "dry_run": true,
  "deleted_questions": 13,
  "deleted_papers": 4,
  "deleted_objects": 45,
  "freed_bytes": 1711558
}
```

语义：

- 会统计当前所有可安全硬删除的软删除题目
- 会统计当前所有软删除试卷
- 会统计这些硬删除后会变成无引用的 `objects`，以及已经存在的孤儿 `objects`
- 整个流程在事务里回滚，因此只提供精确预览，不会改数据

### `POST /admin/garbage-collections/run`

真正执行垃圾回收。

请求体与返回值格式和 `preview` 相同，只是 `dry_run = false`。

执行顺序：

1. 硬删除已软删除试卷
2. 硬删除不再被未删除试卷引用的已软删除题目
3. 删除所有无任何引用的 `objects`

---

## 用户管理

### `GET /admin/users`

分页列出所有用户。

支持的 query 参数：

- `limit`（默认 20，最大 100）
- `offset`（默认 0）

响应格式（分页包裹）：

```json
{
  "items": [
    {
      "user_id": "...",
      "username": "admin",
      "display_name": "Administrator",
      "role": "admin",
      "is_active": true,
      "created_at": "2025-01-01T00:00:00.000Z",
      "updated_at": "2025-01-01T00:00:00.000Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

### `POST /admin/users`

创建新用户。

请求体：

```json
{
  "username": "alice",
  "password": "secure-password",
  "display_name": "Alice",
  "role": "editor"
}
```

- `username`: 必填，唯一
- `password`: 必填，至少 6 个字符
- `display_name`: 可选，默认空字符串
- `role`: 可选，默认 `viewer`，可选值 `viewer` / `editor` / `admin`

成功返回用户信息（同列表中的 item 格式）。

错误：

- `400`: 参数校验失败
- `409`: 用户名已存在

### `PATCH /admin/users/{user_id}`

更新用户信息。至少提供一个字段。

请求体（均为可选）：

```json
{
  "display_name": "New Name",
  "role": "admin",
  "is_active": false
}
```

错误：

- `400`: 无可更新字段 / 角色值无效 / 尝试停用自己
- `404`: 用户不存在

### `DELETE /admin/users/{user_id}`

停用用户（软删除），同时撤销其所有 refresh token。

- 不允许停用自己
- 返回 `{ "message": "user deactivated" }`

错误：

- `400`: 尝试删除自己
- `404`: 用户不存在
