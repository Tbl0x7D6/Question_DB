# FAQ

## 为什么不直接把题干正文写进数据库？
因为你们现在已经有较成熟的 CPHOS-LaTeX 组织方式。以 LaTeX 文件路径和索引作为主存，可以最大程度保留排版、结构和后续编译能力。

## 为什么既要保存 xlsx，又要保存 question_stats？
xlsx 是原始统计工作簿，保真且可追溯；`question_stats` 是便于检索、筛选和后续难度分析的结构化结果，两者用途不同。

## PDF 还有用吗？
有，但不再作为主索引。PDF 更适合作为历史来源或发布产物，主数据仍然以 LaTeX 文件和卷内题目索引为准。

## 现在的 question_id 和 paper_index 怎么分工？
`question_id` 是全局唯一标识，`paper_index` 是卷内顺序。后者取代旧设计里依赖页码定位的做法。
