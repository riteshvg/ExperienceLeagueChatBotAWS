#!/usr/bin/env python3
"""
Update Bedrock Configuration

This script updates the .env file with the latest Bedrock model configuration.
"""

import os
import sys
from pathlib import Path

def update_env_file():
    """Update the .env file with latest Bedrock configuration."""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ .env file not found!")
        return False
    
    # Read current .env file
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # New Bedrock configuration
    new_config = [
        "\n",
        "# =============================================================================\n",
        "# AWS Bedrock Configuration (Primary AI Provider)\n",
        "# =============================================================================\n",
        "BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0\n",
        "BEDROCK_REGION=us-east-1\n",
        "BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1\n",
        "\n"
    ]
    
    # Check if Bedrock config already exists
    bedrock_exists = any('BEDROCK_MODEL_ID' in line for line in lines)
    
    if bedrock_exists:
        print("🔄 Updating existing Bedrock configuration...")
        # Update existing lines
        updated_lines = []
        for line in lines:
            if line.startswith('BEDROCK_MODEL_ID'):
                updated_lines.append('BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0\n')
            elif line.startswith('BEDROCK_REGION'):
                updated_lines.append('BEDROCK_REGION=us-east-1\n')
            elif line.startswith('BEDROCK_EMBEDDING_MODEL_ID'):
                updated_lines.append('BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1\n')
            else:
                updated_lines.append(line)
        
        # Write updated content
        with open(env_file, 'w') as f:
            f.writelines(updated_lines)
    else:
        print("➕ Adding new Bedrock configuration...")
        # Add new configuration
        with open(env_file, 'a') as f:
            f.writelines(new_config)
    
    print("✅ Bedrock configuration updated successfully!")
    print("\n📋 New Configuration:")
    print("   - Text Model: anthropic.claude-3-5-sonnet-20241022-v2:0")
    print("   - Region: us-east-1")
    print("   - Embedding Model: amazon.titan-embed-text-v1")
    
    return True

def main():
    """Main function."""
    try:
        success = update_env_file()
        
        if success:
            print("\n🎉 Configuration update completed!")
            print("\nNext steps:")
            print("1. Test the updated configuration")
            print("2. Create Bedrock Knowledge Base")
            print("3. Test the complete RAG pipeline")
            sys.exit(0)
        else:
            print("\n❌ Configuration update failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error updating configuration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
