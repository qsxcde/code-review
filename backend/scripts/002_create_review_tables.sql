CREATE TABLE IF NOT EXISTS review_records (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    pr_url          VARCHAR(512) NOT NULL,
    pr_title        VARCHAR(512),
    owner           VARCHAR(128),
    repo            VARCHAR(128),
    pr_number       INT,
    status          ENUM('pending','running','completed','failed') DEFAULT 'pending',
    summary_json    JSON,
    result_json     JSON,
    file_count      INT DEFAULT 0,
    risk_counts     JSON,
    duration_ms     INT,
    pr_sha          VARCHAR(64),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_user_sha (user_id, pr_sha)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS feedback (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    record_id   INT NOT NULL,
    risk_index  INT NOT NULL,
    rating      ENUM('helpful','not_helpful','false_positive') NOT NULL,
    comment     TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (record_id) REFERENCES review_records(id) ON DELETE CASCADE,
    INDEX idx_record_id (record_id),
    UNIQUE KEY idx_record_risk (record_id, risk_index)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
