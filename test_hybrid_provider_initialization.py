#!/usr/bin/env python3
"""
Test script to verify hybrid model provider initialization in auto-retraining page.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.models.model_provider import ModelProvider
from src.config.hybrid_config import HybridConfigManager
from src.routing.query_router import QueryRouter
from src.ui.comparison_ui import ComparisonUI
from config.settings import Settings

def test_hybrid_provider_initialization():
    """Test hybrid model provider initialization."""
    print("🧪 TESTING: Hybrid Model Provider Initialization")
    print("=" * 60)
    
    # Test 1: Check API keys availability
    print("1. 📋 Checking API Keys Availability")
    print("-" * 40)
    
    try:
        settings = Settings()
        google_available = bool(settings.google_api_key)
        aws_available = bool(settings.aws_access_key_id and settings.aws_secret_access_key)
        at_least_one_available = google_available or aws_available
        
        print(f"   Google API Key: {'✅ Available' if google_available else '❌ Not Available'}")
        print(f"   AWS Access Key: {'✅ Available' if settings.aws_access_key_id else '❌ Not Available'}")
        print(f"   AWS Secret Key: {'✅ Available' if settings.aws_secret_access_key else '❌ Not Available'}")
        print(f"   At Least One Available: {'✅ Yes' if at_least_one_available else '❌ No'}")
        
        if not at_least_one_available:
            print("\n❌ No API keys available. Please set GOOGLE_API_KEY or AWS credentials.")
            return False
            
    except Exception as e:
        print(f"❌ Error checking settings: {e}")
        return False
    
    # Test 2: Initialize config manager
    print("\n2. ⚙️ Initializing Config Manager")
    print("-" * 40)
    
    try:
        config_manager = HybridConfigManager()
        print("   ✅ Config manager initialized successfully")
        
        # Validate API keys through config manager
        validation = config_manager.validate_api_keys()
        print(f"   Google Available: {'✅' if validation['google_available'] else '❌'}")
        print(f"   AWS Available: {'✅' if validation['aws_available'] else '❌'}")
        print(f"   At Least One: {'✅' if validation['at_least_one_available'] else '❌'}")
        
    except Exception as e:
        print(f"   ❌ Error initializing config manager: {e}")
        return False
    
    # Test 3: Initialize model provider
    print("\n3. 🤖 Initializing Model Provider")
    print("-" * 40)
    
    try:
        model_provider = ModelProvider()
        print("   ✅ Model provider initialized successfully")
        
        # Check available models
        available_models = model_provider.get_available_models()
        print(f"   Available Models: {', '.join(available_models)}")
        
    except Exception as e:
        print(f"   ❌ Error initializing model provider: {e}")
        return False
    
    # Test 4: Initialize query router
    print("\n4. 🧭 Initializing Query Router")
    print("-" * 40)
    
    try:
        query_router = QueryRouter(config_manager)
        print("   ✅ Query router initialized successfully")
        
    except Exception as e:
        print(f"   ❌ Error initializing query router: {e}")
        return False
    
    # Test 5: Initialize comparison UI
    print("\n5. 🎨 Initializing Comparison UI")
    print("-" * 40)
    
    try:
        comparison_ui = ComparisonUI(model_provider, query_router)
        print("   ✅ Comparison UI initialized successfully")
        
    except Exception as e:
        print(f"   ❌ Error initializing comparison UI: {e}")
        return False
    
    # Test 6: Test dual response generation capability
    print("\n6. 🚀 Testing Dual Response Generation Capability")
    print("-" * 40)
    
    try:
        # Test if the model provider has the required method
        if hasattr(model_provider, 'query_both_models_with_kb'):
            print("   ✅ query_both_models_with_kb method available")
        else:
            print("   ❌ query_both_models_with_kb method not available")
            return False
        
        if hasattr(model_provider, 'query_both_models'):
            print("   ✅ query_both_models method available")
        else:
            print("   ❌ query_both_models method not available")
            return False
        
        print("   ✅ Dual response generation capability confirmed")
        
    except Exception as e:
        print(f"   ❌ Error testing dual response capability: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - Hybrid Model Provider Ready!")
    print("=" * 60)
    
    print("\n🚀 Ready to test in Streamlit:")
    print("   1. Go to http://localhost:8509")
    print("   2. Navigate to '🚀 Auto-Retraining'")
    print("   3. Click '🚀 Initialize Hybrid Model Provider'")
    print("   4. Enter a query and click 'Generate Dual Response'")
    print("   5. Review the generated responses and provide feedback")
    
    return True

if __name__ == "__main__":
    success = test_hybrid_provider_initialization()
    if not success:
        print("\n❌ Some tests failed. Please check your configuration.")
        sys.exit(1)




