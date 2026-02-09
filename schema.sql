-- FindItFast – Full Database Schema
-- Run once against a fresh MySQL database to create all required tables.

CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(255) NOT NULL,
    student_id    VARCHAR(100) NOT NULL UNIQUE,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    profile_photo VARCHAR(255) DEFAULT NULL,
    role          VARCHAR(50)  NOT NULL DEFAULT 'user',
    active        TINYINT(1)   NOT NULL DEFAULT 1,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lost_items (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT          NOT NULL,
    name          VARCHAR(255) NOT NULL,
    category      VARCHAR(100) DEFAULT NULL,
    description   TEXT         DEFAULT NULL,
    color         VARCHAR(100) DEFAULT NULL,
    brand         VARCHAR(100) DEFAULT NULL,
    shape         VARCHAR(100) DEFAULT NULL,
    material      VARCHAR(100) DEFAULT NULL,
    last_seen     VARCHAR(255) DEFAULT NULL,
    last_seen_at  DATE         DEFAULT NULL,
    status        VARCHAR(50)  NOT NULL DEFAULT 'pending',
    photo         VARCHAR(255) DEFAULT NULL,
    embedding     LONGTEXT     DEFAULT NULL,
    reported_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS found_items (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT          NOT NULL,
    name          VARCHAR(255) NOT NULL,
    category      VARCHAR(100) DEFAULT NULL,
    description   TEXT         DEFAULT NULL,
    color         VARCHAR(100) DEFAULT NULL,
    brand         VARCHAR(100) DEFAULT NULL,
    shape         VARCHAR(100) DEFAULT NULL,
    material      VARCHAR(100) DEFAULT NULL,
    where_found   VARCHAR(255) DEFAULT NULL,
    found_at      DATE         DEFAULT NULL,
    status        VARCHAR(50)  NOT NULL DEFAULT 'pending',
    photo         VARCHAR(255) DEFAULT NULL,
    embedding     LONGTEXT     DEFAULT NULL,
    reported_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS matches (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    lost_item_id   INT          NOT NULL,
    found_item_id  INT          NOT NULL,
    score          FLOAT        NOT NULL DEFAULT 0,
    created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lost_item_id)  REFERENCES lost_items(id)  ON DELETE CASCADE,
    FOREIGN KEY (found_item_id) REFERENCES found_items(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS claims (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    match_id       INT          DEFAULT NULL,
    lost_item_id   INT          DEFAULT NULL,
    found_item_id  INT          DEFAULT NULL,
    user_id        INT          NOT NULL,
    status         VARCHAR(50)  NOT NULL DEFAULT 'Pending',
    justification  TEXT         DEFAULT NULL,
    created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (match_id)      REFERENCES matches(id)     ON DELETE SET NULL,
    FOREIGN KEY (lost_item_id)  REFERENCES lost_items(id)  ON DELETE SET NULL,
    FOREIGN KEY (found_item_id) REFERENCES found_items(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id)       REFERENCES users(id)       ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS notifications (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT          NOT NULL,
    type          VARCHAR(100) NOT NULL,
    title         VARCHAR(255) NOT NULL,
    message       TEXT         DEFAULT NULL,
    related_id    INT          DEFAULT NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at       DATETIME     DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS suggestions (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT          NOT NULL,
    message       TEXT         NOT NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
