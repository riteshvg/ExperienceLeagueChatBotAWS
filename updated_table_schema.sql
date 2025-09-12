-- Updated query_analytics table schema
-- This includes time tracking and model information

CREATE TABLE IF NOT EXISTS query_analytics (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    userid VARCHAR(100) DEFAULT 'anonymous',
    date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reaction VARCHAR(20) DEFAULT 'none',  -- 'positive', 'negative', or 'none'
    query_time_seconds DECIMAL(10,3) DEFAULT NULL,  -- Time taken to process query
    model_used VARCHAR(50) DEFAULT NULL,  -- Which AI model was used
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_query_analytics_date_time ON query_analytics(date_time);
CREATE INDEX IF NOT EXISTS idx_query_analytics_userid ON query_analytics(userid);
CREATE INDEX IF NOT EXISTS idx_query_analytics_model ON query_analytics(model_used);
CREATE INDEX IF NOT EXISTS idx_query_analytics_reaction ON query_analytics(reaction);
