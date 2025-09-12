-- PostgreSQL Table Creation Script for Query Analytics
-- Run this in your Railway PostgreSQL service console

-- User queries table
CREATE TABLE IF NOT EXISTS user_queries (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    session_id VARCHAR(255),
    query_complexity VARCHAR(50) DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI responses table
CREATE TABLE IF NOT EXISTS ai_responses (
    id SERIAL PRIMARY KEY,
    query_id INTEGER REFERENCES user_queries(id) ON DELETE CASCADE,
    response_text TEXT NOT NULL,
    model_used VARCHAR(100),
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User feedback table
CREATE TABLE IF NOT EXISTS user_feedback (
    id SERIAL PRIMARY KEY,
    query_id INTEGER REFERENCES user_queries(id) ON DELETE CASCADE,
    response_id INTEGER REFERENCES ai_responses(id) ON DELETE CASCADE,
    feedback_type VARCHAR(50) NOT NULL,
    feedback_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Query sessions table
CREATE TABLE IF NOT EXISTS query_sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255),
    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_end TIMESTAMP,
    total_queries INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_queries_session_id ON user_queries(session_id);
CREATE INDEX IF NOT EXISTS idx_user_queries_created_at ON user_queries(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_responses_query_id ON ai_responses(query_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_query_id ON user_feedback(query_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_response_id ON user_feedback(response_id);

-- Verify tables were created
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
AND table_name IN ('user_queries', 'ai_responses', 'user_feedback', 'query_sessions')
ORDER BY table_name;

-- Show table structure
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public'
AND table_name IN ('user_queries', 'ai_responses', 'user_feedback', 'query_sessions')
ORDER BY table_name, ordinal_position;