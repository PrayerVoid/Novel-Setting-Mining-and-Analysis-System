# 模块接口定义 (Interface Definitions)

本文档详细定义了系统各核心模块（Service层）的接口，包括输入参数、输出结果及功能备注。开发时请严格遵守此规范，以便于模块组装。

## 1. 数据库服务 (`app/services/db_service.py`)

负责底层的数据库连接与操作。

### `get_db_connection`

- **输入**: 无
- **输出**: `sqlite3.Connection` 对象
- **备注**: 获取数据库连接，通常在其他函数内部调用或通过上下文管理器使用。

### `execute_query`

- **输入**:
  - `query` (str): SQL 查询语句 (SELECT)。
  - `params` (tuple, optional): SQL 参数，默认为空元组。
- **输出**: `List[Dict[str, Any]]`
  - 返回查询结果列表，每一项是一个字典，键为列名，值为数据。
- **备注**: 用于执行读操作。

### `execute_commit`

- **输入**:
  - `query` (str): SQL 执行语句 (INSERT, UPDATE, DELETE)。
  - `params` (tuple, optional): SQL 参数。
- **输出**: `int`
  - 对于 INSERT，返回新插入行的 ID (`lastrowid`)。
  - 对于 UPDATE/DELETE，返回受影响的行数 (`rowcount`)。
- **备注**: 用于执行写操作，自动提交事务。

### `execute_transaction`

- **输入**:
  - `operations` (List[Dict]): 操作列表。每个操作是一个字典，包含：
    - `query` (str): SQL 语句。
    - `params` (tuple): 参数。
- **输出**: `bool`
  - 成功返回 `True`，失败回滚并返回 `False` (或抛出异常)。
- **备注**: 用于批量执行需要原子性的操作（如批量导入章节、更新设定）。

---

## 2. AI 服务 (`app/services/ai_service.py`)

负责与 LLM（本项目使用智谱 ZhipuAI 客户端示例）进行交互，包含三类主要接口：

### `extract_settings_from_text(chapter_content: str, existing_settings: Dict) -> Dict`

- 输入:
  - `chapter_content` (str): 当前章节原文。
  - `existing_settings` (Dict): 上一章节的有效设定（`entities`, `relationships`, `properties`）。
- 输出(示例):
  - 返回 JSON 格式的字典，典型键名为：
    - `new_settings`: 包含 `entities`（name/type/properties 列表）和 `relationships`（subject/object/relation 列表）。
    - `invalidated_settings`: 包含要失效的设置（如 relationship 或 property 指定项）。
  - 例如：
    {
    "new_settings": { "entities": [...], "relationships": [...] },
    "invalidated_settings": [ {"type": "property", "entity": "X", "key": "age"}, ... ]
    }
- 备注:
  - 返回的 JSON 必须严格可解析；代码层会直接使用 `json.loads()` 解析并根据 `new_settings` 和 `invalidated_settings` 生成数据库操作。

### `detect_conflicts(previous_settings: Dict, chapter_content: str) -> Dict`

- 功能: 使用 AI 检测章节与已有设定之间的明显逻辑冲突。
- 输出格式: `{ "conflicts": [ { "original_text": "...", "conflicting_setting": "...", "start_chapter": 1, "description": "..." }, ... ] }`。

### `chat_with_context(previous_settings: Dict, chapter_content: str, user_query: str) -> str`

- 功能: 基于已有设定与章节内容，返回 AI 的自然语言回答（字符串）。

> ✅ 说明：文档已与 `ai_service.py` 的实际实现对齐 —— **没有** `unchanged_settings` 字段返回，冲突检测返回 `conflicts` 列表，而非布尔 `has_conflict` 字段。

## 3. 小说服务 (`app/services/novel_service.py`)

负责小说元数据的管理。

### `create_novel`

- **输入**:
  - `title` (str): 小说标题。
  - `author` (str): 作者名。
  - `description` (str, optional): 简介。
- **输出**: `Dict`
  - 创建成功的小说对象，包含 `id`, `title`, `author` 等。
- **备注**: 对应 `POST /novels`。

### `get_all_novels`

- **输入**: 无
- **输出**: `List[Dict]`
  - 所有小说的列表。
- **备注**: 对应 `GET /novels`。

### `get_novel_details`

- **输入**:
  - `novel_id` (int): 小说ID。
- **输出**: `Dict`
  - 指定小说的详细信息，若不存在返回 None。
- **备注**: 用于内部查询或详情页。

### `delete_novel`

- **输入**:
  - `novel_id` (int): 小说ID。
- **输出**: `bool`
  - 删除成功返回 True。
- **备注**: 级联删除该小说下的所有章节和设定。

---

## 小说整体分析接口

### `get_novel_density` (NovelService)

- **输入**:
  - `novel_id` (int): 小说ID。
- **输出**: `Dict`，示例:
  - `{ "novel_id": 1, "density": 0.000123, "entities_count": 50, "properties_count": 120, "relationships_count": 200, "word_count": 300000 }`
- **功能说明**: 计算并返回小说的设定密度（(实体+属性+关系) / 总字数），便于用于横向或纵向密度比较与排名。

### `get_frequent_patterns` (NovelService)

- **输入**:
  - `novel_id` (int): 小说ID。
  - `count` (int, optional): 返回模式的最大数量，默认 5。
- **输出**: `List[Dict]`，每项包含 `support`, `node_types`, `nodes`, `edges`, `examples`, `pattern_type`。
- **功能说明**: 使用 FP-Growth 思路挖掘频繁子图模式，返回便于可视化的子图结构与示例。

---

## 可视化 / 图分析接口（Visualization）

### `get_shortest_path`

- **输入**:
  - `novel_id` (int): 小说ID。
  - `chapter_number` (int): 目标章节版本号。
  - `source_id`/`source_name`, `target_id`/`target_name` (任选): 要查询的起点与终点实体。
  - `n` (int, optional): 与知识图谱查询一致的范围参数（最近 n 章），默认 1。
- **输出**: `Dict`：`{ "path_nodes": [id,...], "path_links": [ {"source":...,"target":...,"value":...}, ... ] }`。
- **功能说明**: 将关系视为无向边构建邻接表并使用 BFS 寻找最短路径，返回路径节点与边（保留原始关系方向与名称，如果不存在直接边则使用占位项）。

> 备注：当前实现依赖实体名到 ID 的一对一映射（实体在命名上最好唯一），否则路径解析/映射可能出现歧义。

---

## 4. 章节服务 (`app/services/chapter_service.py`)

负责章节内容的增删改查。

### `batch_import_chapters`

- **输入**:
  - `novel_id` (int): 小说ID。
  - `chapters_data` (List[Dict]): 章节列表，每项包含 `number`, `title`, `content`。
- **输出**: `Dict`
  - 包含 `success_count` (int) 和 `errors` (List[str])。
- **备注**: 批量插入章节，需处理章节号重复的情况。

### `get_chapter_content`

- **输入**:
  - `novel_id` (int): 小说ID。
  - `chapter_number` (int): 章节号。
- **输出**: `Dict`
  - 包含 `id`, `title`, `content`, `number`。
- **备注**: 用于提取设定时获取文本。

### `get_latest_chapter`

- **输入**:
  - `novel_id` (int): 小说ID。
- **输出**: `Dict`
  - 该小说最新一章的信息。
- **备注**: 用于确定回滚操作的目标。

### `delete_chapter_and_rollback`

- **输入**:
  - `novel_id` (int): 小说ID。
  - `chapter_number` (int): 要删除的章节号（通常是最新一章）。
- **输出**: `bool`
  - 成功返回 True。
- **备注**: **关键操作**。不仅删除章节记录，还需要调用 `setting_service` 回滚相关设定。

---

## 5. 设定服务 (`app/services/setting_service.py`)

核心业务逻辑，负责设定的提取、存储和版本管理。

### `get_settings_at_chapter`

- **输入**:
  - `novel_id` (int): 小说ID。
  - `chapter_number` (int): 目标章节号。
- **输出**: `Dict`
  - 该章节结束时的完整世界观设定。
  - 结构: `{ "entities": [...], "properties": [...], "relationships": [...] }`
- **备注**: 查询逻辑：`start_chapter <= N` 且 `(end_chapter IS NULL OR end_chapter >= N)`。

### `extract_and_update_settings`

- **输入**:
  - `novel_id` (int): 小说ID。
  - `chapter_number` (int): 当前需要提取的章节号。
- **输出**: `Dict`
  - 提取结果摘要，如 `{ "added": 5, "updated": 2, "invalidated": 1 }`。
- **备注**: **核心流程**。
  1. 调用 `get_settings_at_chapter(novel_id, chapter_number - 1)` 获取旧设定。
  2. 调用 `chapter_service.get_chapter_content` 获取新文本。
  3. 调用 `ai_service.extract_settings` 获取变更。
  4. 调用 `db_service.execute_transaction` 更新数据库（插入新设定，更新旧设定的 `end_chapter_id`）。

### `rollback_settings`

- **输入**:
  - `novel_id` (int): 小说ID。
  - `target_chapter_number` (int): 回滚到的目标章节号（即删除 target_chapter_number + 1 及其之后的设定）。
- **输出**: `bool`
- **备注**:
  1. 删除 `start_chapter > target_chapter_number` 的所有记录。
  2. 将 `end_chapter > target_chapter_number` 的记录的 `end_chapter_id` 重置为 NULL (或恢复为之前的值，如果支持多级回滚)。
     *简化版逻辑*: 仅支持回滚最新一章。即删除 `start_chapter == deleted_chapter` 的记录，将 `end_chapter == deleted_chapter - 1` 的记录重置为 NULL。

### `get_entity_evolution`

- **输入**:
  - `entity_name` (str): 实体名称。
  - `novel_id` (int): 小说ID。
- **输出**: `List[Dict]`
  - 该实体随章节变化的属性列表。
- **备注**: 用于展示实体演变历史。
