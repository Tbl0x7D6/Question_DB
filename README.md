# CPHOS Question Bank V1

这是一个面向 CPHOS 内部题目整理、统计与检索的轻量题库源码仓。当前版本按“LaTeX-first + 服务器 SQLite”设计：源码仓只保存 schema、脚本、API、样例与文档；生产环境中的 LaTeX 题库、xlsx 统计工作簿、题图、原始资料和运行日志都放在你们自己的服务器上。

## 核心设计
- `papers` 以试卷主 LaTeX 文件为核心索引，记录届数、类型、主 LaTeX 路径、可选 PDF 路径和题目索引。
- `questions` 不再直接保存题干字符串，而是保存题目 LaTeX 文件路径、答案 LaTeX 文件路径、卷内顺序索引和检索文本索引。
- `score_workbooks` 把 xlsx 统计表直接写入 SQLite 的 BLOB 字段，同时保存文件名、sheet 列表和哈希，保证原始统计表可追溯。
- `question_stats` 继续保存按题聚合后的统计量，并通过 `source_workbook_id` 关联回原始 xlsx。

## 仓库结构
- `question_bank/`: 核心 Python 包，包含 schema、导入、统计、导出、难度评分、workbook 存储和查询仓储。
- `scripts/`: 命令行脚本入口。
- `api/`: FastAPI 应用。
- `samples/demo_bundle/`: 样例 bundle，演示 LaTeX 题目与 xlsx workbook 的入库方式。
- `assets/`: 样例图片或开发环境静态资源。
- `docs/`: 字段字典、录入规范、维护手册、部署说明、FAQ。
- `tests/`: 围绕样例库的测试。

## 配置方式
生产路径不写死在仓库中，通过环境变量注入：

- `QUESTION_BANK_DB_PATH`: 服务器上 SQLite 文件路径。
- `QUESTION_BANK_ASSETS_DIR`: 服务器上题图资产根目录。
- `QUESTION_BANK_RAW_DIR`: 服务器上原始资料目录。
- `QUESTION_BANK_EXPORTS_DIR`: 导出目录。

本地未设置这些变量时，项目会回退到仓库内的样例路径，便于开发和测试。

## 快速开始
1. 初始化本地样例数据库

```bash
python scripts/init_db.py
```

2. 校验并导入样例 bundle

```bash
python scripts/validate_bundle.py samples/demo_bundle
python scripts/import_bundle.py samples/demo_bundle --commit
```

3. 导入样例成绩统计并关联样例 workbook

```bash
python scripts/import_stats.py samples/demo_bundle/stats/raw_scores.csv --stats-source sample_scores --stats-version demo-v1 --source-workbook-id WB-CPHOS-18-DEMO-INDEX
python scripts/calculate_difficulty.py --method-version demo-baseline
```

4. 导出内部版与半公开版数据

```bash
python scripts/export_data.py --format jsonl
python scripts/export_data.py --format csv --public
```

5. 执行质量检查

```bash
python scripts/check_data_quality.py
```

## API 启动
当前仓库未附带 FastAPI 依赖。若要启动 API，请先安装依赖：

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload
```

可用接口：
- `/health`
- `/papers`
- `/questions`
- `/questions/{question_id}`
- `/score-workbooks`
- `/score-workbooks/{workbook_id}`
- `/search`

## 样例内容
项目自带 3 道示例题和 1 份示例 xlsx 工作簿：
- 理论题：滑块-斜面动力学
- 实验题：单摆测重力加速度
- 实验题：加热电阻的能量评估
- 统计工作簿：`demo_score_index.xlsx`

这些样例仅用于本地开发验证，不代表生产库位置或生产部署方式。
