# 小说设定增量提取系统 (Novel Setting Extraction System)

这是一个基于大语言模型 (LLM) 的长篇小说世界观设定自动提取与版本管理系统。它能够逐章分析小说内容，自动提取实体（角色、地点、组织等）、属性及关系，并支持**增量更新**和**历史回滚**，构建随剧情演变的动态知识图谱。

## 🚀 核心特性

* **增量提取 (Incremental Extraction)**:
  * 系统不会每次都重新分析全文。它读取上一章的设定状态作为上下文，仅分析新章节带来的变化（新增、修改、失效）。
  * 极大降低 Token 消耗，同时保证设定的连贯性。
* **版本控制与回滚 (Version Control & Rollback)**:
  * 数据库记录了每个设定（实体/属性/关系）的生命周期 (`start_chapter_id`, `end_chapter_id`)。
  * 支持删除最新章节，系统会自动回滚该章节产生的所有设定变更，恢复到上一章的状态。
* **实体历史追踪**:
  * 支持查询特定实体在指定章节范围内的演变历史。
* **自动化处理**:
  * 内置小说切分工具，支持 GB2312/UTF-8 编码自动检测，自动识别“第X章”格式进行切分。
* **AI 集成**:
  * 后端对接 **智谱 AI (ZhipuAI)** 的 **GLM-4.5-Flash** 模型，提供高性价比的文本分析能力。
  * 精心设计的 Prompt 工程，确保输出严格的 JSON 格式数据。
* **整体分析与模式挖掘**: 小说整体分析功能。
  * **设定密度 (`GET /api/novels/<id>/density`)**: 统计实体/属性/关系总数并按总字数归一化，便于对比小说或章节（用于密度比较）。
  * **频繁子图模式 (`GET /api/novels/<id>/frequent_patterns?count=K`)**: 基于 FP-Growth 思路，挖掘常见的关系模式（示例：人物—从属—组织）。
* **知识图谱增强分析**: **最短路径查询** 接口（`GET /api/novels/<id>/chapters/<num>/knowledge_graph/shortest_path`），可查询两实体之间的最短连接路径，适用于关系追溯与编辑帮助。

## 🛠️ 技术栈

* **后端**: Python, Flask
* **数据库**: SQLite (轻量级，无需配置，支持事务)
* **AI 模型**: ZhipuAI GLM-4.5-Flash
* **前端**: HTML, JavaScript (原生 Fetch API)
* **工具库**: `requests`, `chardet`

## 📂 项目结构

```text
/系统
|-- run.py                      # Flask 服务启动入口
|-- config.py                   # 配置文件
|-- schema.sql                  # 数据库初始化脚本
|-- novel_system.db             # SQLite 数据库文件 (自动生成)
|-- 《从零开始》.txt             # 示例小说文件
|
|-- /app
|   |-- __init__.py             # App 工厂
|   |-- /api                    # API 路由层
|   |   |-- novel_routes.py     # 小说增删改查
|   |   |-- chapter_routes.py   # 章节管理
|   |   |-- setting_routes.py   # 设定提取核心接口
|   |   |-- search_routes.py    # 搜索与历史查询接口
|   |   |-- visualization_routes.py # 知识图谱数据接口
|   |
|   |-- /services               # 业务逻辑层
|   |   |-- db_service.py       # 数据库操作封装
|   |   |-- ai_service.py       # 智谱 AI 对接实现
|   |   |-- setting_service.py  # 核心：增量提取与回滚算法
|   |   |-- novel_service.py    # 小说管理逻辑
|   |   |-- chapter_service.py  # 章节管理逻辑
|   |
|   |-- /templates              # 前端页面
|       |-- index.html          # 首页
|       |-- novel.html          # 详情与操作页
|       |-- search.html         # 搜索页
|
|-- /utils
|   |-- novel_splitter.py       # 小说自动切分工具
|
|-- /docs                       # 项目文档
    |-- ai_prompts.md           # AI Prompt 设计
    |-- api_routes.md           # API 接口文档
    |-- database_design.md      # 数据库设计文档
    |-- ...
```

## ⚡ 快速开始

### 1. 环境准备

确保已安装 Python 3.8+。安装所需依赖：

```bash
pip install flask requests zhipuai chardet
```

### 2. 配置 API Key

打开 `app/services/ai_service.py`，填入您的智谱 AI API Key：

```python
class AIService:
    def __init__(self):
        self.api_key = "YOUR_API_KEY_HERE" 
        # ...
```

### 3. 启动服务

在项目根目录下运行：

```bash
python run.py
```

服务将启动在 `http://127.0.0.1:5000`。
