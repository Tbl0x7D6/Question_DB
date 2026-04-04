# Admin API

管理员接口用于查看软删除数据、恢复软删除记录，以及执行最终垃圾回收。

说明：

- 当前没有接账号系统，这组接口默认不鉴权
- `deleted_by` 目前只是占位字段，现阶段固定返回 `null`
- 普通 `/questions`、`/papers` 接口默认只返回 `deleted_at IS NULL` 的活跃记录

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
