#!/usr/bin/env python3
"""
Manually test analytics functionality.
"""

import os
import sys
import psycopg2
from pathlib import Path
from datetime import datetime

def test_analytics_manually():
    """Test analytics functionality manually."""
    print("🧪 Manual Analytics Test")
    print("=" * 50)
    
    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found")
        print("🔧 Please set DATABASE_URL environment variable")
        return False
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test session
        session_id = f"manual-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        print(f"📝 Testing with session: {session_id}")
        
        # 1. Insert user query
        print("\n1️⃣ Inserting user query...")
        cursor.execute("""
            INSERT INTO user_queries (query_text, session_id, query_complexity, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, ("How do I set up Adobe Analytics?", session_id, "medium", datetime.now()))
        
        query_id = cursor.fetchone()[0]
        print(f"✅ Query inserted - ID: {query_id}")
        
        # 2. Insert AI response
        print("\n2️⃣ Inserting AI response...")
        cursor.execute("""
            INSERT INTO ai_responses (query_id, response_text, model_used, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (query_id, "To set up Adobe Analytics, you need to...", "claude-3-haiku", datetime.now()))
        
        response_id = cursor.fetchone()[0]
        print(f"✅ Response inserted - ID: {response_id}")
        
        # 3. Insert user feedback
        print("\n3️⃣ Inserting user feedback...")
        cursor.execute("""
            INSERT INTO user_feedback (query_id, response_id, feedback_type, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (query_id, response_id, "positive", datetime.now()))
        
        feedback_id = cursor.fetchone()[0]
        print(f"✅ Feedback inserted - ID: {feedback_id}")
        
        # 4. Verify data
        print("\n4️⃣ Verifying data...")
        cursor.execute("""
            SELECT 
                q.id as query_id,
                q.query_text,
                q.session_id,
                q.query_complexity,
                q.created_at as query_time,
                r.response_text,
                r.model_used,
                r.created_at as response_time,
                f.feedback_type,
                f.created_at as feedback_time
            FROM user_queries q
            LEFT JOIN ai_responses r ON q.id = r.query_id
            LEFT JOIN user_feedback f ON q.id = f.query_id
            WHERE q.session_id = %s
        """, (session_id,))
        
        result = cursor.fetchone()
        if result:
            print("✅ Data verification successful:")
            print(f"   Query ID: {result[0]}")
            print(f"   Query: {result[1]}")
            print(f"   Session: {result[2]}")
            print(f"   Complexity: {result[3]}")
            print(f"   Query Time: {result[4]}")
            print(f"   Response: {result[5]}")
            print(f"   Model: {result[6]}")
            print(f"   Response Time: {result[7]}")
            print(f"   Feedback: {result[8]}")
            print(f"   Feedback Time: {result[9]}")
        
        # 5. Test analytics summary
        print("\n5️⃣ Testing analytics summary...")
        cursor.execute("""
            SELECT 
                COUNT(q.id) as total_queries,
                COUNT(r.id) as total_responses,
                COUNT(f.id) as total_feedback,
                COUNT(CASE WHEN f.feedback_type = 'positive' THEN 1 END) as positive_feedback,
                COUNT(CASE WHEN f.feedback_type = 'negative' THEN 1 END) as negative_feedback
            FROM user_queries q
            LEFT JOIN ai_responses r ON q.id = r.query_id
            LEFT JOIN user_feedback f ON q.id = f.query_id
        """)
        
        summary = cursor.fetchone()
        print("✅ Analytics summary:")
        print(f"   Total Queries: {summary[0]}")
        print(f"   Total Responses: {summary[1]}")
        print(f"   Total Feedback: {summary[2]}")
        print(f"   Positive Feedback: {summary[3]}")
        print(f"   Negative Feedback: {summary[4]}")
        
        # 6. Test recent queries
        print("\n6️⃣ Testing recent queries...")
        cursor.execute("""
            SELECT 
                q.query_text,
                q.created_at,
                r.model_used,
                f.feedback_type
            FROM user_queries q
            LEFT JOIN ai_responses r ON q.id = r.query_id
            LEFT JOIN user_feedback f ON q.id = f.query_id
            ORDER BY q.created_at DESC
            LIMIT 5
        """)
        
        recent = cursor.fetchall()
        print("✅ Recent queries:")
        for i, (query, created_at, model, feedback) in enumerate(recent, 1):
            print(f"   {i}. {query[:50]}...")
            print(f"      Time: {created_at}")
            print(f"      Model: {model or 'N/A'}")
            print(f"      Feedback: {feedback or 'N/A'}")
            print()
        
        # 7. Clean up test data
        print("\n7️⃣ Cleaning up test data...")
        cursor.execute("DELETE FROM user_queries WHERE session_id = %s", (session_id,))
        conn.commit()
        print("✅ Test data cleaned up")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Manual analytics test completed successfully!")
        print("✅ Database is working correctly")
        print("✅ Analytics can be inserted and retrieved")
        print("✅ If queries still don't appear in the app, check:")
        print("   1. Railway logs for errors")
        print("   2. App is using latest code")
        print("   3. Analytics service is initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Manual analytics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function."""
    print("🧪 Manual Analytics Test Tool")
    print("=" * 60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = test_analytics_manually()
    
    if success:
        print("\n✅ All tests passed!")
        print("🔧 If queries still don't appear in the app:")
        print("   1. Check Railway logs for runtime errors")
        print("   2. Verify app is using latest deployed code")
        print("   3. Check if analytics_available is True in session state")
        return 0
    else:
        print("\n❌ Tests failed!")
        print("🔧 Check database connection and table structure")
        return 1

if __name__ == "__main__":
    exit(main())
