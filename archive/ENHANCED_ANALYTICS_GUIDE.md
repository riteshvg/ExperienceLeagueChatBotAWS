# Enhanced Analytics System Guide

## 🎯 **What's New**

Your analytics system has been enhanced with:
- **⏱️ Query Timing**: Track how long each query takes to process
- **🤖 Model Tracking**: See which AI model was used for each response
- **📊 Better Reactions**: Proper "positive", "negative", "none" values instead of single characters
- **📈 Enhanced Metrics**: Average query time, model usage statistics

## 🔧 **Updated Table Structure**

Your `query_analytics` table now includes:

```sql
CREATE TABLE query_analytics (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    userid VARCHAR(100) DEFAULT 'anonymous',
    date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reaction VARCHAR(20) DEFAULT 'none',  -- 'positive', 'negative', or 'none'
    query_time_seconds DECIMAL(10,3) DEFAULT NULL,  -- Time taken to process query
    model_used VARCHAR(50) DEFAULT NULL,  -- Which AI model was used
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🚀 **How to Update Your Table**

### **Option 1: Use the Update Script (Recommended)**

1. **Run the update script**:
   ```bash
   python update_table_schema.py
   ```

2. **The script will**:
   - ✅ Add new columns (`query_time_seconds`, `model_used`, `created_at`)
   - ✅ Update existing columns to proper sizes
   - ✅ Add performance indexes
   - ✅ Test the new schema

### **Option 2: Manual SQL Commands**

If you prefer to run SQL commands manually:

```sql
-- Add new columns
ALTER TABLE query_analytics ADD COLUMN query_time_seconds DECIMAL(10,3) DEFAULT NULL;
ALTER TABLE query_analytics ADD COLUMN model_used VARCHAR(50) DEFAULT NULL;
ALTER TABLE query_analytics ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Update existing columns
ALTER TABLE query_analytics ALTER COLUMN reaction TYPE VARCHAR(20);
ALTER TABLE query_analytics ALTER COLUMN userid TYPE VARCHAR(100);
ALTER TABLE query_analytics ALTER COLUMN query TYPE TEXT;

-- Add indexes for performance
CREATE INDEX idx_query_analytics_date_time ON query_analytics(date_time);
CREATE INDEX idx_query_analytics_userid ON query_analytics(userid);
CREATE INDEX idx_query_analytics_model ON query_analytics(model_used);
CREATE INDEX idx_query_analytics_reaction ON query_analytics(reaction);
```

## 📊 **New Analytics Features**

### **Enhanced Dashboard Metrics**
- **Total Queries**: Count of all queries
- **Total Feedback**: Count of queries with feedback
- **Positive/Negative Feedback**: Proper reaction tracking
- **Average Query Time**: How long queries take on average
- **Models Used**: Number of different AI models used

### **Query History Table**
Now shows:
- **ID**: Unique query identifier
- **Query**: The user's question
- **User ID**: Who asked the question
- **Date & Time**: When it was asked
- **Reaction**: User feedback (positive/negative/none)
- **Query Time**: How long it took to process
- **Model Used**: Which AI model responded

### **Reaction System**
- **Default**: `"none"` - No feedback given yet
- **Positive**: `"positive"` - User clicked thumbs up
- **Negative**: `"negative"` - User clicked thumbs down
- **Automatic**: Set to `"none"` when query is first stored

## 🔍 **How to Verify the Update**

### **1. Check Table Schema**
```sql
SELECT column_name, data_type, character_maximum_length 
FROM information_schema.columns 
WHERE table_name = 'query_analytics'
ORDER BY ordinal_position;
```

### **2. Test Insert**
```sql
INSERT INTO query_analytics (query, userid, reaction, query_time_seconds, model_used)
VALUES ('Test query', 'test_user', 'positive', 2.5, 'claude-3-haiku')
RETURNING id;
```

### **3. Check Data**
```sql
SELECT * FROM query_analytics ORDER BY id DESC LIMIT 5;
```

## 🎯 **What Happens Now**

### **When Users Ask Questions**
1. ✅ Query is stored with timing information
2. ✅ Model used is recorded
3. ✅ Reaction defaults to "none"
4. ✅ Success message shows ID, time, and model

### **When Users Give Feedback**
1. ✅ Reaction is updated to "positive" or "negative"
2. ✅ Analytics dashboard shows proper feedback counts
3. ✅ Satisfaction rate is calculated correctly

### **In Admin Dashboard**
1. ✅ Enhanced metrics with timing and model info
2. ✅ Query history shows all new fields
3. ✅ Export includes timing and model data
4. ✅ Better analytics for performance monitoring

## 🚨 **Important Notes**

- **Backward Compatible**: Existing data will work fine
- **No Data Loss**: All existing queries are preserved
- **Performance**: New indexes improve query speed
- **Flexible**: New columns allow NULL values for existing records

## 🔧 **Troubleshooting**

### **If Update Fails**
1. Check your `DATABASE_URL` environment variable
2. Ensure you have proper database permissions
3. Try running individual ALTER TABLE commands
4. Check Railway logs for specific errors

### **If Analytics Don't Work**
1. Verify the table schema was updated correctly
2. Check that new columns exist
3. Test with the verification script
4. Check application logs for errors

## 🎉 **Ready to Go!**

Once you've updated your table schema:
1. ✅ Deploy the updated application
2. ✅ Test with a few queries
3. ✅ Check the Admin Dashboard
4. ✅ Verify timing and model tracking works

Your enhanced analytics system is now ready to provide detailed insights into user queries, response times, and model performance! 🚀
