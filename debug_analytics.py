#!/usr/bin/env python3
"""
Debug analytics service initialization and tracking
"""

import os
import sys

# Add project root and src to path
sys.path.append('.')
sys.path.append('src')

def debug_analytics_initialization():
    """Debug analytics service initialization."""
    print("🔍 Debugging Analytics Service Initialization...")
    print("=" * 60)
    
    # Check environment variables
    database_url = os.getenv('DATABASE_URL')
    print(f"✅ DATABASE_URL: {database_url[:50] if database_url else 'Not set'}...")
    
    # Try to import and initialize analytics service
    try:
        from src.integrations.streamlit_analytics_simple import initialize_analytics_service
        print("✅ Analytics service module imported successfully")
        
        # Initialize service
        analytics_service = initialize_analytics_service()
        print(f"🔍 Analytics service initialized: {analytics_service is not None}")
        
        if analytics_service:
            print("✅ Analytics service created successfully")
            
            # Test health check
            health_ok = analytics_service.analytics_service.health_check()
            print(f"📊 Health check result: {health_ok}")
            
            if health_ok:
                # Test query tracking
                print("🔍 Testing query tracking...")
                from datetime import datetime
                
                query_id = analytics_service.track_query(
                    session_id="debug_session",
                    query_text="Debug test query",
                    query_complexity="simple",
                    query_time_seconds=1.0,
                    model_used="claude-3-haiku"
                )
                
                print(f"🔍 Query tracking result: {query_id}")
                
                if query_id:
                    print("✅ Query tracking successful!")
                    
                    # Test response tracking
                    response_id = analytics_service.track_response(
                        query_id=query_id,
                        response_text="Debug test response",
                        model_used="claude-3-haiku"
                    )
                    
                    print(f"🔍 Response tracking result: {response_id}")
                    
                    if response_id:
                        print("✅ Response tracking successful!")
                        return True
                    else:
                        print("❌ Response tracking failed")
                        return False
                else:
                    print("❌ Query tracking failed")
                    return False
            else:
                print("❌ Health check failed")
                return False
        else:
            print("❌ Analytics service initialization returned None")
            return False
            
    except Exception as e:
        print(f"❌ Error during analytics test: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = debug_analytics_initialization()
    print(f"\n📊 Debug Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
