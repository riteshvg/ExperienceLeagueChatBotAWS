-- Query Analytics Database Schema
-- This schema stores user queries, responses, and feedback for analysis

-- Create database (if not exists)
CREATE DATABASE IF NOT EXISTS chatbot_analytics;

USE chatbot_analytics;

-- Users table (for future user management)
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    user_agent TEXT,
    ip_address VARCHAR(45),
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at)
);

-- Query sessions table
CREATE TABLE IF NOT EXISTS query_sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(255) NOT NULL,
    session_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    total_queries INT DEFAULT 0,
    total_feedback_positive INT DEFAULT 0,
    total_feedback_negative INT DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES users(session_id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at)
);

-- User queries table
CREATE TABLE IF NOT EXISTS user_queries (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(255) NOT NULL,
    query_session_id INT,
    query_text TEXT NOT NULL,
    query_length INT,
    query_complexity ENUM('simple', 'complex', 'extremely_complex') DEFAULT 'simple',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_time_ms INT,
    status ENUM('success', 'error', 'timeout') DEFAULT 'success',
    error_message TEXT NULL,
    FOREIGN KEY (session_id) REFERENCES users(session_id) ON DELETE CASCADE,
    FOREIGN KEY (query_session_id) REFERENCES query_sessions(id) ON DELETE SET NULL,
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at),
    INDEX idx_query_complexity (query_complexity),
    INDEX idx_status (status),
    FULLTEXT idx_query_text (query_text)
);

-- AI responses table
CREATE TABLE IF NOT EXISTS ai_responses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    query_id INT NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    model_id VARCHAR(255) NOT NULL,
    response_text TEXT NOT NULL,
    response_length INT,
    tokens_used INT,
    estimated_cost DECIMAL(10, 6),
    documents_retrieved INT DEFAULT 0,
    relevance_score DECIMAL(3, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (query_id) REFERENCES user_queries(id) ON DELETE CASCADE,
    INDEX idx_query_id (query_id),
    INDEX idx_model_used (model_used),
    INDEX idx_created_at (created_at)
);

-- User feedback table
CREATE TABLE IF NOT EXISTS user_feedback (
    id INT PRIMARY KEY AUTO_INCREMENT,
    query_id INT NOT NULL,
    response_id INT NOT NULL,
    feedback_type ENUM('positive', 'negative', 'neutral') NOT NULL,
    feedback_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    additional_notes TEXT NULL,
    FOREIGN KEY (query_id) REFERENCES user_queries(id) ON DELETE CASCADE,
    FOREIGN KEY (response_id) REFERENCES ai_responses(id) ON DELETE CASCADE,
    UNIQUE KEY unique_query_response_feedback (query_id, response_id),
    INDEX idx_query_id (query_id),
    INDEX idx_feedback_type (feedback_type),
    INDEX idx_feedback_timestamp (feedback_timestamp)
);

-- Query categories table (for future categorization)
CREATE TABLE IF NOT EXISTS query_categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    category_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Query categorization mapping
CREATE TABLE IF NOT EXISTS query_categorization (
    id INT PRIMARY KEY AUTO_INCREMENT,
    query_id INT NOT NULL,
    category_id INT NOT NULL,
    confidence_score DECIMAL(3, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (query_id) REFERENCES user_queries(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES query_categories(id) ON DELETE CASCADE,
    UNIQUE KEY unique_query_category (query_id, category_id),
    INDEX idx_query_id (query_id),
    INDEX idx_category_id (category_id)
);

-- Analytics summary table (for performance optimization)
CREATE TABLE IF NOT EXISTS analytics_summary (
    id INT PRIMARY KEY AUTO_INCREMENT,
    date DATE NOT NULL,
    total_queries INT DEFAULT 0,
    successful_queries INT DEFAULT 0,
    failed_queries INT DEFAULT 0,
    avg_processing_time_ms DECIMAL(10, 2),
    total_tokens_used BIGINT DEFAULT 0,
    total_cost DECIMAL(10, 6) DEFAULT 0,
    positive_feedback_count INT DEFAULT 0,
    negative_feedback_count INT DEFAULT 0,
    most_used_model VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_date (date),
    INDEX idx_date (date)
);

-- Insert default query categories
INSERT IGNORE INTO query_categories (category_name, description) VALUES
('adobe_analytics', 'Questions about Adobe Analytics features and functionality'),
('customer_journey_analytics', 'Questions about Customer Journey Analytics'),
('implementation', 'Questions about implementation and setup'),
('troubleshooting', 'Questions about debugging and problem-solving'),
('best_practices', 'Questions about best practices and recommendations'),
('comparisons', 'Questions comparing different tools or approaches'),
('general', 'General questions not fitting other categories');

-- Create views for common analytics queries
CREATE OR REPLACE VIEW query_analytics_view AS
SELECT 
    uq.id,
    uq.session_id,
    uq.query_text,
    uq.query_complexity,
    uq.created_at,
    uq.processing_time_ms,
    uq.status,
    ar.model_used,
    ar.tokens_used,
    ar.estimated_cost,
    ar.documents_retrieved,
    uf.feedback_type,
    uf.feedback_timestamp,
    qs.session_name
FROM user_queries uq
LEFT JOIN ai_responses ar ON uq.id = ar.query_id
LEFT JOIN user_feedback uf ON uq.id = uf.query_id
LEFT JOIN query_sessions qs ON uq.query_session_id = qs.id
ORDER BY uq.created_at DESC;

-- Create view for daily analytics
CREATE OR REPLACE VIEW daily_analytics_view AS
SELECT 
    DATE(uq.created_at) as date,
    COUNT(*) as total_queries,
    SUM(CASE WHEN uq.status = 'success' THEN 1 ELSE 0 END) as successful_queries,
    SUM(CASE WHEN uq.status = 'error' THEN 1 ELSE 0 END) as failed_queries,
    AVG(uq.processing_time_ms) as avg_processing_time_ms,
    SUM(ar.tokens_used) as total_tokens_used,
    SUM(ar.estimated_cost) as total_cost,
    SUM(CASE WHEN uf.feedback_type = 'positive' THEN 1 ELSE 0 END) as positive_feedback,
    SUM(CASE WHEN uf.feedback_type = 'negative' THEN 1 ELSE 0 END) as negative_feedback,
    ar.model_used as most_used_model
FROM user_queries uq
LEFT JOIN ai_responses ar ON uq.id = ar.query_id
LEFT JOIN user_feedback uf ON uq.id = uf.query_id
GROUP BY DATE(uq.created_at), ar.model_used
ORDER BY date DESC;
