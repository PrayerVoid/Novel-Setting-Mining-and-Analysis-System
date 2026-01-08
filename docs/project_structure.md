# 项目结构

```
系统（项目根目录）
|
|-- app/
|   |-- api/
|   |   |-- __init__.py
|   |   |-- novel_routes.py         # 小说管理路由（/api/novels）
|   |   |-- chapter_routes.py       # 章节管理、导入、检测相关路由（/api/novels）
|   |   |-- setting_routes.py       # 设定提取、批量提取、回滚等路由（/api/novels）
|   |   |-- visualization_routes.py # 可视化（知识图谱）路由（/api/novels），包含 `knowledge_graph` 导出与 `knowledge_graph/shortest_path` 最短路径查询

|   |   |-- search_routes.py        # 搜索与建议接口（/api/search）
|   |
|   |-- services/
|   |   |-- __init__.py
|   |   |-- novel_service.py        # 小说相关业务逻辑
|   |   |-- chapter_service.py      # 章节导入/删除/查询逻辑
|   |   |-- setting_service.py      # 设定提取、回滚、范围查询等核心逻辑
|   |   |-- ai_service.py           # 与 AI 模型（智谱等）交互的逻辑
|   |   |-- db_service.py           # SQLite 数据库交互与事务封装
|   |
|   |-- templates/
|   |   |-- index.html
|   |   |-- novel.html
|   |   |-- search.html
|   |
|   |-- __init__.py                 # Flask app 工厂（create_app），注册蓝图并初始化 DB
|
|-- run.py                          # 启动脚本
|-- requirements.txt                # 项目依赖
|-- schema.sql                      # 数据库初始化脚本（用于创建表）
|-- novel_system.db                 # 运行时生成的 SQLite 数据库（位于项目根）
|-- docs/                           # 项目文档（本文档所在）
|-- utils/                          # 工具函数（如小说分章）
```

## 结构说明

- **`/app`**: Flask 应用核心代码。
  - **`/app/api`**: 按职责划分的蓝图（Blueprints），当前注册的蓝图及其前缀为：
    - `novels` (url_prefix=`/api/novels`)：小说与章节、设定相关接口。
    - `search` (url_prefix=`/api/search`)：搜索与建议接口。
  - **`/app/services`**: 业务逻辑层：数据库操作、AI 调用、设定增量提取和版本控制等均在此实现。
  - **`/app/templates`**: 简单的前端模板（`index.html`, `novel.html`, `search.html`）。
- `run.py`: 本项目的启动入口，调用 `create_app()` 并运行 Flask 开发服务器。
- `schema.sql`: 数据库建表脚本（见 `database_design.md`）。
- `novel_system.db`: 运行时产生的 SQLite 数据库文件（`app.services.db_service.DB_PATH`）。
