CREATE TABLE IF NOT EXISTS review_rules (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    name            VARCHAR(128) NOT NULL,
    description     VARCHAR(512),
    category        VARCHAR(32) NOT NULL DEFAULT 'custom',
    prompt_content  TEXT NOT NULL,
    file_filters    JSON,
    is_enabled      BOOLEAN DEFAULT TRUE,
    priority        INT DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_id (user_id),
    INDEX idx_user_category (user_id, category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
