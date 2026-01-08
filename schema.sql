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
    `conflict_result` TEXT,
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
