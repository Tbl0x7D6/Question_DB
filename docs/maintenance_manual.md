# 维护手册

## 新增一套卷子
1. 把试卷主 LaTeX、题目 LaTeX、答案 LaTeX、图片和原始统计 xlsx 放到服务器或开发环境对应目录。
2. 运行 `scripts/register_raw_assets.py` 更新总表。
3. 按 bundle 格式整理 `manifest.json`、`questions/*.json`、`score_workbooks/*.xlsx`。
4. 运行校验和 dry-run。
5. commit 导入。
6. 如需聚合统计，再运行 `scripts/import_stats.py` 并关联 `source_workbook_id`。
7. 运行质量检查并补齐缺失项。

## 数据修复规则
- 优先修复 LaTeX 源文件、bundle 或脚本，不直接手改 SQLite。
- 如果必须手动修复，修复后要同步回 LaTeX 源或 bundle，保证可追溯。

## 备份与回滚
- 生产 SQLite 与生产 LaTeX、xlsx、assets 必须做定期备份。
- 每次大规模录入后额外导出内部 JSONL 快照。
- 回滚时优先回滚服务器上的数据库和文件备份，再回滚源码仓版本。
