# 完整实现流程

下面根据当前代码实现（`app/services`）说明核心流程与关键实现细节。

## 1. 批量导入章节 (`chapter_service.py`)

- 接收 `POST /api/novels/<novel_id>/chapters/batch`，请求体为章节数组（每项包含 `number`, `title`, `content`）。
- 将插入操作封装为事务（`db_service.execute_transaction`），批量执行 `INSERT INTO chapters ...`。
- 如果事务失败，返回错误；成功则返回 `success_count`。

## 2. 增量提取设定 (`setting_service.py`)

这是系统的核心流程：

1. 数据准备

   - 获取 `current_chapter_id`（通过 `chapters` 表用小说ID+章号定位）。
   - 通过 `get_settings_at_chapter(novel_id, chapter_number - 1)` 获取上一章的“有效”设定（entities/properties/relationships）。
   - 读取当前章节内容。
2. 与 AI 交互

   - 调用 `ai_service.extract_settings_from_text(content, old_settings)`，传入旧设定和章节文本。
   - 期望得到 JSON 字典，至少包含 `new_settings` 与 `invalidated_settings`。
3. 解析并应用到数据库

   - 基于 `new_settings`：插入新实体、插入/更新属性（若属性值变化则把旧记录的 `end_chapter_id` 更新为当前章ID 并新增新记录）。
   - 基于 `invalidated_settings`：将对应记录的 `end_chapter_id` 更新为当前章节 ID（以标记失效）。
   - 以上操作通过 `db_service.execute_transaction` 原子执行。
4. 额外行为

   - 批量提取（`extract_to_chapter` / `extract_batch`）在遇到缺失章节时会尝试调用 `chapter_service.import_from_local_file` 自动从本地小说文件导入所需章节。

## 3. 删除 / 回滚设定

- `delete_latest_chapter_and_settings(novel_id)`（POST `/.../chapters/delete_latest`）会：
  1. 查找最新章节号并删除从该章开始的设定（`setting_service.delete_settings_from_chapter`）。
  2. 删除该章节记录本身（`chapter_service.delete_chapter`）。
- `rollback_settings` 与 `batch_rollback_settings` 提供按范围回滚的能力：将在范围内 `start_chapter_id` 的设定删除，并将 `end_chapter_id` 在范围内的记录恢复为 `NULL`。

## 4. 知识图谱生成（`visualization_routes.py`）

- 支持查询最近 `n` 章内的更新（通过参数 `n`），默认 `n=1`。
- 输出结构包含 `nodes`（实体）与 `links`（关系），并在节点中额外传递 `start_chapter` 以便前端进行更灵活的高亮/过滤。
- 提供**最短路径查询**接口 `/api/novels/<novel_id>/chapters/<chapter_number>/knowledge_graph/shortest_path`：
  - 支持以 `source_id`/`target_id` 或 `source_name`/`target_name` 指定查询端点。
  - 实现细节：将关系视作无向边构建邻接表并使用 BFS 查找最短节点路径，返回 `path_nodes`（节点 ID 列表）和 `path_links`（路径上的边，保留原始方向与 relation 名称；如找不到路径则返回空结果并提示）。
- 注意：目前实现对实体名到 ID 的映射假设实体名称唯一；若存在同名实体可能导致路径解析不准确。
- 注意2：`frequent_patterns` 模块以关系三元组为事务项，基于 FP-Growth 思路（构建 FP-tree、按支持度挖掘模式、转换为图模式）输出典型子图模式，支持前端直接可视化模式示例。

## 5. 设定冲突检测

- `detect_conflicts` 调用 AI 返回的格式为 `{ "conflicts": [ ... ] }`，其中每个冲突项包含原文片段、冲突的设定描述、该设定最早出现的章节号和简要说明。
