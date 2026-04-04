# Ops API

## Endpoints

题目和试卷的批量打包下载接口见：

- [Questions API](../questions/API.md)
- [Papers API](../papers/API.md)
- [Admin API](../admin/API.md)

### `POST /exports/run`

导出题目数据。

说明：

- 只导出未软删除题目
- `output_path` 是相对于 `QB_EXPORT_DIR` 的路径；不传时使用默认路径
- `format` 支持 `jsonl` 和 `csv`
- `public` 为 `true` 时不包含 tex 源码

请求体：

```json
{
  "format": "jsonl",
  "public": false,
  "output_path": "exports/question_bank_internal.jsonl"
}
```

成功响应：

```json
{
  "format": "jsonl",
  "public": false,
  "output_path": "/absolute/path/to/exports/question_bank_internal.jsonl",
  "exported_questions": 42
}
```

### `POST /quality-checks/run`

运行数据质量检查，并把结果写到指定文件。

说明：

- 只检查未软删除题目和未软删除试卷
- `output_path` 是相对于 `QB_EXPORT_DIR` 的路径；不传时使用默认路径

请求体：

```json
{
  "output_path": "exports/quality_report.json"
}
```

成功响应：

```json
{
  "output_path": "/absolute/path/to/exports/quality_report.json",
  "report": { ... }
}
```
