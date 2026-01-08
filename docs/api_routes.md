# API 路由定义

所有路由均以 `/api` 为前缀。

## 1. 小说管理 (`/app/api/novel_routes.py`)  (url_prefix: `/api/novels`)

- **`POST /api/novels`**

  - 功能: 创建一本新小说。
  - 请求体: `{ "title": "小说标题", "author": "作者" }`
  - 响应: `{ "id": 1, "title": "小说标题", "author": "作者" }`
- **`GET /api/novels`**

  - 功能: 获取小说列表。
  - 响应: `[{ "id": 1, "title": "小说标题", "author": "作者" }, ...]`
- **`DELETE /api/novels/<int:novel_id>`**

  - 功能: 删除小说（数据库级联删除相关数据）。
  - 响应: `{ "message": "Novel deleted successfully" }` 或错误信息。

## 1.5 小说整体分析与模式挖掘 (`/app/api/novel_routes.py`)

- **`GET /api/novels/<int:novel_id>/density`**

  - 功能: 计算小说的设定密度（设定项数 / 字数），返回实体数、属性数、关系数、总字数与密度值。
  - 示例响应: `{ "novel_id": 1, "density": 0.000123, "entities_count": 50, "properties_count": 120, "relationships_count": 200, "word_count": 300000 }`
  - 使用场景: 可用于**密度比较**（不同小说或同一小说的不同时间点），前端或分析脚本可对多个小说的 density 值做横向对比来判断设定浓度。

- **`GET /api/novels/<int:novel_id>/frequent_patterns`**

  - 功能: 挖掘小说当前（或最新章节）知识图谱的频繁子图模式（使用 FP-Growth 思路实现）。
  - 可选参数: `count` (int, 默认 5) — 返回模式数量上限。
  - 响应: 模式数组，每项包含 `support`, `node_types`, `nodes`, `edges`, `examples`, `pattern_type` 等字段，适合前端可视化呈现典型交互模式（例如：常见的主体-关系-客体三元组）。

> 说明：`density` 与 `frequent_patterns` 均在 `novel_routes.py` 中实现，返回的数据便于前端做横向对比与可视化分析。

## 2. 章节与导入（`/app/api/chapter_routes.py` 与 `/app/api/novel_routes`）

- **`POST /api/novels/<int:novel_id>/chapters/batch`**

  - 功能: 批量导入章节。
  - 请求体: `[{ "number": 1, "title": "第一章", "content": "..." }, ...]`
  - 响应: `{ "success_count": N, "errors": [...] }`
- **`POST /api/novels/<int:novel_id>/import_next`**

  - 功能: 自动从本地小说文件导入下一个未导入章节（用于逐章导入场景）。
  - 响应: 成功时返回新导入章节号和提示。
- **`POST /api/novels/<int:novel_id>/chapters/batch_delete`**

  - 功能（当前实现）: 删除从 `start_chapter` 到最新已提取章节的**设定**（并返回提示）。请求体示例: `{ "start_chapter": 5 }`。
  - 注意: 源代码中存在两个同路径的路由定义（先是用于删除章节、后是删除设定的实现），后定义会覆盖前定义，导致行为与早期文档不一致。请在使用时注意该路由当前的实际行为或在代码中修复该重复定义。
- **`POST /api/novels/<int:novel_id>/chapters/delete_latest`**

  - 功能: 删除最新一章并删除从该章开始的设定（章节 + 该章之后的设定）。
  - 响应: `{ "message": "Chapter X and its settings have been deleted." }`
- **`GET /api/novels/<int:novel_id>/chapters`**

  - 功能: 列出章节摘要（id, number, title）并返回 `latest_extracted_chapter`。
  - 响应: `{ "chapters": [...], "latest_extracted_chapter": N }`
- **`GET /api/novels/<int:novel_id>/chapters/<int:chapter_num>/content`**

  - 功能: 返回章节内容和可能的冲突检测结果。
  - 响应: `{ "content": "...", "conflict_result": {...} }`
- **`POST /api/novels/<int:novel_id>/chapters/<int:chapter_num>/detect_conflicts`**

  - 功能: 使用 AI 检测章节与已有设定的冲突并保存结果。
  - 响应: `{ "conflicts": [ { "original_text": "...", "conflicting_setting": "...", "start_chapter": 1, "description": "..." }, ... ] }`
- **`POST /api/novels/<int:novel_id>/chapters/<int:chapter_num>/chat`**

  - 功能: 基于该章节上下文与已有设定，进行 AI 问答。
  - 请求体: `{ "query": "问题文本" }`
  - 响应: `{ "response": "AI 的回答文本" }`

## 3. 设定提取与管理 (`/app/api/setting_routes.py`)

- **`POST /api/novels/<int:novel_id>/chapters/<int:chapter_number>/extract`**

  - 功能: 对指定章节执行一次增量设定提取与数据库更新。
  - 响应: `{ "message": "Settings for chapter X extracted successfully." }`
- **`POST /api/novels/<int:novel_id>/extract_batch`**

  - 功能: 同步批量提取指定区间内的设定（注意：可能为阻塞操作）。
  - 请求体: `{ "start": 1, "end": 10 }`
  - 响应: `{ "message": "Batch extraction completed...", "successful_chapters": [...], "errors": [...] }`
- **`POST /api/novels/<int:novel_id>/extract_to_chapter`**

  - 功能: 从第一个未提取章节开始，自动提取直到指定章号（会尝试自动导入缺失章节）。
  - 请求体: `{ "end_chapter": 20 }`
- **`GET /api/novels/<int:novel_id>/chapters/<int:chapter_number>/settings`**

  - 功能: 获取某章结束时的完整设定（entities, relationships, properties）。
- **`GET /api/novels/<int:novel_id>/chapters/<int:chapter_number>/changes`**

  - 功能: 获取该章发生的增量变化（新增实体、新增属性、新增关系、失效项等）。

## 4. 搜索与建议 (`/app/api/search_routes.py`) (url_prefix: `/api/search`)

- **`GET /api/search/entity_history`**

  - 参数: `novel_id`, `entity_name`, `start_chapter`, `end_chapter`。
  - 功能: 获取实体在指定章节区间内的历史变更（创建、属性变更）。
- **`GET /api/search/suggest`**

  - 参数: `novel_id`, `query`。
  - 功能: 基于模糊匹配返回实体名称建议，用于前端自动补全。

## 5. 知识图谱与可视化 (`/app/api/visualization_routes.py`)

- **`GET /api/novels/<int:novel_id>/chapters/<int:chapter_number>/knowledge_graph`**

  - 参数: `n` (int, optional): 使用最近 n 章的数据来构建图，默认 `n=1`。
  - 功能: 返回 `nodes` 与 `links` 用于前端展示知识图谱（节点带有 `start_chapter` 用于高亮/过滤）。
- **`GET /api/novels/<int:novel_id>/chapters/<int:chapter_number>/knowledge_graph/shortest_path`**

  - 参数: `source_id`/`source_name`, `target_id`/`target_name`, `n`。
  - 功能: 返回两实体之间的最短路径 `{"path_nodes": [...], "path_links": [...]}`；实现使用 BFS 在无向邻接表中查找最短连接。
  - 错误/边界: 若未指定合法的 source/target，返回 400 错误；若找不到路径，返回空路径并带提示消息（200）。

> 说明：知识图谱相关接口返回的数据结构已便于 ECharts / vis.js 等前端库直接渲染；`shortest_path` 对外提供了便捷的关系追溯功能。
