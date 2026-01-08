# 数据库设计与脚本

## 1. 数据库结构

数据库采用 **SQLite**，包含以下五个核心表，用于支持多本小说的设定管理和生命周期追踪。

### `novels` 表
存储小说的基本信息。

| 字段名 | 类型 | 约束 | 描述 |
| --- | --- | --- | --- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 小说唯一标识符 |
| `title` | TEXT | NOT NULL | 小说标题 |
| `author` | TEXT | | 小说作者 |

### `chapters` 表
存储章节信息，并关联到具体小说。

| 字段名 | 类型 | 约束 | 描述 |
| --- | --- | --- | --- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 章节唯一标识符 |
| `novel_id` | INTEGER | NOT NULL, FOREIGN KEY | 关联的小说ID |
| `number` | INTEGER | NOT NULL | 章节号 |
| `title` | TEXT | NOT NULL | 章节标题 |
| `content` | TEXT | | 章节的原始内容 |
| `conflict_result` | TEXT | | 冲突检测结果 (JSON字符串) |

### `entities` 表
存储提取出的实体，并记录其生命周期。

| 字段名 | 类型 | 约束 | 描述 |
| --- | --- | --- | --- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 实体唯一标识符 |
| `name` | TEXT | NOT NULL | 实体名称 |
| `type` | TEXT | NOT NULL | 实体类型 (e.g., 'character') |
| `start_chapter_id` | INTEGER | NOT NULL, FOREIGN KEY | 设定开始有效的章节ID |
| `end_chapter_id` | INTEGER | | 设定失效的章节ID (NULL表示仍有效) |

### `properties` 表
存储实体的属性，并记录其生命周期。

| 字段名 | 类型 | 约束 | 描述 |
| --- | --- | --- | --- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 属性唯一标识符 |
| `entity_id` | INTEGER | NOT NULL, FOREIGN KEY | 关联的实体ID |
| `key` | TEXT | NOT NULL | 属性名 |
| `value` | TEXT | NOT NULL | 属性值 |
| `start_chapter_id` | INTEGER | NOT NULL, FOREIGN KEY | 设定开始有效的章节ID |
| `end_chapter_id` | INTEGER | | 设定失效的章节ID (NULL表示仍有效) |

### `relationships` 表
存储实体间的关系，并记录其生命周期。

| 字段名 | 类型 | 约束 | 描述 |
| --- | --- | --- | --- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 关系唯一标识符 |
| `novel_id` | INTEGER | NOT NULL, FOREIGN KEY | 小说ID |
| `subject_name` | TEXT | NOT NULL | 主体名称 |
| `object_name` | TEXT | NOT NULL | 客体名称 |
| `relation` | TEXT | NOT NULL | 关系名称 |
| `start_chapter_id` | INTEGER | NOT NULL, FOREIGN KEY | 设定开始有效的章节ID |
| `end_chapter_id` | INTEGER | | 设定失效的章节ID (NULL表示仍有效) |

## 2. 初始化脚本 (schema.sql)

```sql
-- Database schema for novel setting extractor
-- SQLite version

-- Drop tables if they exist to ensure a clean slate
DROP TABLE IF EXISTS `relationships`;
DROP TABLE IF EXISTS `properties`;
DROP TABLE IF EXISTS `entities`;
DROP TABLE IF EXISTS `chapters`;
DROP TABLE IF EXISTS `novels`;

-- Table for novels
CREATE TABLE `novels` (
    `id` INTEGER PRIMARY KEY AUTOINCREMENT,
    `title` TEXT NOT NULL,
    `author` TEXT
);

-- Table for chapters
CREATE TABLE `chapters` (
    `id` INTEGER PRIMARY KEY AUTOINCREMENT,
    `novel_id` INTEGER NOT NULL,
    `number` INTEGER NOT NULL,
    `title` TEXT NOT NULL,
    `content` TEXT,
    FOREIGN KEY (`novel_id`) REFERENCES `novels`(`id`) ON DELETE CASCADE,
    UNIQUE (`novel_id`, `number`)
);

-- Table for entities
CREATE TABLE `entities` (
    `id` INTEGER PRIMARY KEY AUTOINCREMENT,
    `novel_id` INTEGER NOT NULL,
    `name` TEXT NOT NULL,
    `type` TEXT NOT NULL,
    `start_chapter_id` INTEGER NOT NULL,
    `end_chapter_id` INTEGER,
    FOREIGN KEY (`novel_id`) REFERENCES `novels`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`start_chapter_id`) REFERENCES `chapters`(`id`),
    FOREIGN KEY (`end_chapter_id`) REFERENCES `chapters`(`id`)
);

-- Table for properties
CREATE TABLE `properties` (
    `id` INTEGER PRIMARY KEY AUTOINCREMENT,
    `entity_id` INTEGER NOT NULL,
    `key` TEXT NOT NULL,
    `value` TEXT NOT NULL,
    `start_chapter_id` INTEGER NOT NULL,
    `end_chapter_id` INTEGER,
    FOREIGN KEY (`entity_id`) REFERENCES `entities`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`start_chapter_id`) REFERENCES `chapters`(`id`),
    FOREIGN KEY (`end_chapter_id`) REFERENCES `chapters`(`id`)
);

-- Table for relationships
CREATE TABLE `relationships` (
    `id` INTEGER PRIMARY KEY AUTOINCREMENT,
    `novel_id` INTEGER NOT NULL,
    `subject_name` TEXT NOT NULL,
    `object_name` TEXT NOT NULL,
    `relation` TEXT NOT NULL,
    `start_chapter_id` INTEGER NOT NULL,
    `end_chapter_id` INTEGER,
    FOREIGN KEY (`novel_id`) REFERENCES `novels`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`start_chapter_id`) REFERENCES `chapters`(`id`),
    FOREIGN KEY (`end_chapter_id`) REFERENCES `chapters`(`id`)
);
```
