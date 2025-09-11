-- PostgreSQL Migration Script
-- Convert MySQL schema to PostgreSQL for Railway deployment

-- Create database (Railway will handle this)
-- CREATE DATABASE chatbot_analytics;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (for future user management)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT,
    ip_address INET,
    CONSTRAINT users_session_id_unique UNIQUE (session_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_session_id ON users(session_id);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- Query sessions table
CREATE TABLE IF NOT EXISTS query_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    session_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    total_queries INTEGER DEFAULT 0,
    total_feedback_positive INTEGER DEFAULT 0,
    total_feedback_negative INTEGER DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES users(session_id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_query_sessions_session_id ON query_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_query_sessions_created_at ON query_sessions(created_at);

-- User queries table
CREATE TABLE IF NOT EXISTS user_queries (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    query_session_id INTEGER,
    query_text TEXT NOT NULL,
    query_length INTEGER,
    query_complexity VARCHAR(20) DEFAULT 'simple' CHECK (query_complexity IN ('simple', 'complex', 'extremely_complex')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_time_ms INTEGER,
    status VARCHAR(20) DEFAULT 'success' CHECK (status IN ('success', 'error', 'timeout')),
    error_message TEXT,
    FOREIGN KEY (session_id) REFERENCES users(session_id) ON DELETE CASCADE,
    FOREIGN KEY (query_session_id) REFERENCES query_sessions(id) ON DELETE SET NULL
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_user_queries_session_id ON user_queries(session_id);
CREATE INDEX IF NOT EXISTS idx_user_queries_created_at ON user_queries(created_at);
CREATE INDEX IF NOT EXISTS idx_user_queries_complexity ON user_queries(query_complexity);
CREATE INDEX IF NOT EXISTS idx_user_queries_status ON user_queries(status);
CREATE INDEX IF NOT EXISTS idx_user_queries_text_search ON user_queries USING gin(to_tsvector('english', query_text));

-- AI responses table
CREATE TABLE IF NOT EXISTS ai_responses (
    id SERIAL PRIMARY KEY,
    query_id INTEGER NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    model_id VARCHAR(255) NOT NULL,
    response_text TEXT NOT NULL,
    response_length INTEGER,
    tokens_used INTEGER,
    estimated_cost DECIMAL(10, 6),
    documents_retrieved INTEGER DEFAULT 0,
    relevance_score DECIMAL(3, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (query_id) REFERENCES user_queries(id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_ai_responses_query_id ON ai_responses(query_id);
CREATE INDEX IF NOT EXISTS idx_ai_responses_model_used ON ai_responses(model_used);
CREATE INDEX IF NOT EXISTS idx_ai_responses_created_at ON ai_responses(created_at);

-- User feedback table
CREATE TABLE IF NOT EXISTS user_feedback (
    id SERIAL PRIMARY KEY,
    query_id INTEGER NOT NULL,
    response_id INTEGER NOT NULL,
    feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('positive', 'negative', 'neutral')),
    feedback_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    additional_notes TEXT,
    FOREIGN KEY (query_id) REFERENCES user_queries(id) ON DELETE CASCADE,
    FOREIGN KEY (response_id) REFERENCES ai_responses(id) ON DELETE CASCADE,
    CONSTRAINT unique_query_response_feedback UNIQUE (query_id, response_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_user_feedback_query_id ON user_feedback(query_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_type ON user_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_user_feedback_timestamp ON user_feedback(feedback_timestamp);

-- Query categories table (for future categorization)
CREATE TABLE IF NOT EXISTS query_categories (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Query categorization mapping
CREATE TABLE IF NOT EXISTS query_categorization (
    id SERIAL PRIMARY KEY,
    query_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    confidence_score DECIMAL(3, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (query_id) REFERENCES user_queries(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES query_categories(id) ON DELETE CASCADE,
    CONSTRAINT unique_query_category UNIQUE (query_id, category_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_query_categorization_query_id ON query_categorization(query_id);
CREATE INDEX IF NOT EXISTS idx_query_categorization_category_id ON query_categorization(category_id);

-- Analytics summary table (for performance optimization)
CREATE TABLE IF NOT EXISTS analytics_summary (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    total_queries INTEGER DEFAULT 0,
    successful_queries INTEGER DEFAULT 0,
    failed_queries INTEGER DEFAULT 0,
    avg_processing_time_ms DECIMAL(10, 2),
    total_tokens_used BIGINT DEFAULT 0,
    total_cost DECIMAL(10, 6) DEFAULT 0,
    positive_feedback_count INTEGER DEFAULT 0,
    negative_feedback_count INTEGER DEFAULT 0,
    most_used_model VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_analytics_date UNIQUE (date)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_analytics_summary_date ON analytics_summary(date);

-- Insert default query categories
INSERT INTO query_categories (category_name, description) VALUES
('adobe_analytics', 'Questions about Adobe Analytics features and functionality'),
('customer_journey_analytics', 'Questions about Customer Journey Analytics'),
('implementation', 'Questions about implementation and setup'),
('troubleshooting', 'Questions about debugging and problem-solving'),
('best_practices', 'Questions about best practices and recommendations'),
('comparisons', 'Questions comparing different tools or approaches'),
('general', 'General questions not fitting other categories')
ON CONFLICT (category_name) DO NOTHING;

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

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for analytics_summary
CREATE TRIGGER update_analytics_summary_updated_at 
    BEFORE UPDATE ON analytics_summary 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
