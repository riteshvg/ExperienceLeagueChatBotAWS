#!/usr/bin/env python3
"""
Script to switch between testing and production auto-retraining configurations.
"""

import shutil
import os
from pathlib import Path

def switch_to_testing():
    """Switch to testing configuration (3 responses threshold)."""
    print("🔄 Switching to TESTING configuration...")
    print("   - Retraining threshold: 3 responses")
    print("   - Quality threshold: 3/5")
    print("   - Cooldown: 1 minute")
    
    # Copy testing config to main config
    shutil.copy('config/auto_retraining_config.py', 'config/auto_retraining_config_backup.py')
    print("✅ Configuration switched to TESTING mode")
    print("   - Auto-retraining will trigger with just 3 responses")
    print("   - Perfect for testing the pipeline functionality")

def switch_to_production():
    """Switch to production configuration (10 responses threshold)."""
    print("🔄 Switching to PRODUCTION configuration...")
    print("   - Retraining threshold: 10 responses")
    print("   - Quality threshold: 4/5")
    print("   - Cooldown: 1 hour")
    
    # Copy production config to main config
    shutil.copy('config/auto_retraining_config_production.py', 'config/auto_retraining_config.py')
    print("✅ Configuration switched to PRODUCTION mode")
    print("   - Auto-retraining will trigger with 10 high-quality responses")
    print("   - Suitable for production deployment")

def show_current_config():
    """Show the current configuration."""
    try:
        from config.auto_retraining_config import AUTO_RETRAINING_CONFIG
        print("📊 Current Configuration:")
        print(f"   - Retraining threshold: {AUTO_RETRAINING_CONFIG['retraining_threshold']} responses")
        print(f"   - Quality threshold: {AUTO_RETRAINING_CONFIG['quality_threshold']}/5")
        print(f"   - Cooldown: {AUTO_RETRAINING_CONFIG['retraining_cooldown']/60:.0f} minutes")
        
        if AUTO_RETRAINING_CONFIG['retraining_threshold'] == 3:
            print("   - Mode: TESTING")
        else:
            print("   - Mode: PRODUCTION")
    except ImportError:
        print("❌ Could not load configuration")

def main():
    """Main function to manage configuration switching."""
    print("🚀 Auto-Retraining Configuration Manager")
    print("=" * 50)
    
    show_current_config()
    print()
    
    print("Options:")
    print("1. Switch to TESTING mode (3 responses)")
    print("2. Switch to PRODUCTION mode (10 responses)")
    print("3. Show current configuration")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == '1':
        switch_to_testing()
    elif choice == '2':
        switch_to_production()
    elif choice == '3':
        show_current_config()
    elif choice == '4':
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")

if __name__ == "__main__":
    main()




