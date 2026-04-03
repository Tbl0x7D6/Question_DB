# Ops API

## Endpoints

题目和试卷的批量打包下载接口见：

- [Questions API](/home/be/Question_DB/src/api/questions/API.md)
- [Papers API](/home/be/Question_DB/src/api/papers/API.md)
- [Admin API](/home/be/Question_DB/src/api/admin/API.md)

### `POST /exports/run`

导出题目数据。

说明：

- 只导出未软删除题目

请求体：

```json
{
  "format": "jsonl",
  "public": false,
  "output_path": "exports/question_bank_internal.jsonl"
}
```

### `POST /quality-checks/run`

运行数据质量检查，并把结果写到指定文件。

说明：

- 只检查未软删除题目和未软删除试卷

请求体：

```json
{
  "output_path": "exports/quality_report.json"
}
```
