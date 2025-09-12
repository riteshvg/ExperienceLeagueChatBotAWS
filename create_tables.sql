-- Database schema for Adobe Analytics RAG Chatbot
-- Run this script to create all required tables

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

-- Insert some sample data for testing
INSERT INTO user_queries (query_text, session_id, query_complexity) VALUES 
('What is Adobe Analytics?', 'test-session-1', 'simple'),
('How do I set up custom events?', 'test-session-1', 'medium'),
('Explain data retention policies', 'test-session-1', 'complex')
ON CONFLICT DO NOTHING;

-- Update the updated_at column trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for user_queries table
DROP TRIGGER IF EXISTS update_user_queries_updated_at ON user_queries;
CREATE TRIGGER update_user_queries_updated_at
    BEFORE UPDATE ON user_queries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
