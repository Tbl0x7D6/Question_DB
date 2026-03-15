# 录入规范

## 1. 原始文件与 LaTeX 源
- 题目和试卷主文档以 LaTeX 为准，参考 `D:\cphos\CPHOS-Latex` 的组织方式。
- `paper` 保存主 LaTeX 路径，`question` 保存题目 LaTeX 路径与答案 LaTeX 路径。
- PDF 只作为可选的编译产物或历史来源，不再作为题目定位主依据。

## 2. 建立清洗包
- 每套卷子单独建立一个 bundle。
- bundle 必须包含 `manifest.json` 与 `questions/*.json`。
- `manifest.json` 中至少要有 `paper.paper_latex_path`，可选 `score_workbooks` 列表。
- 每道题至少要有 `question_id`、`question_no`、`paper_index`、`category`、`latex_path`、`status`、`tags`、`assets`。

## 3. LaTeX 文件组织
- `latex/papers/` 放试卷主文件。
- `latex/questions/` 放题目主体文件。
- `latex/answers/` 放答案或评分标准文件。
- 如果题目和答案在同一个 `.tex` 里，也要通过 `latex_anchor` 标清逻辑索引。

## 4. 图片与资源
- 统一命名为 `paperid_questionid_scene.ext`。
- 所有图片使用相对路径记录，不写绝对路径。
- 任何录入前先计算 SHA256。

## 5. 统计工作簿与统计量
- 原始统计表优先保留为 xlsx，并写入 `score_workbooks`。
- 若需要按题查询统计量，再从 CSV 或脚本聚合写入 `question_stats`。
- 建议在导入统计量时填写 `source_workbook_id`，保证统计值和原始 xlsx 可追溯。

## 6. 导入前检查
- 先运行 `python scripts/validate_bundle.py <bundle>`。
- 再运行 `python scripts/import_bundle.py <bundle>` 做 dry-run。
- 确认无错误后，加 `--commit` 真正写库。
