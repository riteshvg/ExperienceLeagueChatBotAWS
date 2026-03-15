#!/usr/bin/env python3
"""Test AWS connection using .env file"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Add project paths
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / 'src'))

# Test loading settings
try:
    from config.settings import Settings
    settings = Settings()
    
    print('📋 Application Configuration:')
    print('=' * 50)
    print(f'AWS Access Key ID: {settings.aws_access_key_id[:10] if settings.aws_access_key_id else "Not set"}...')
    print(f'AWS Region: {settings.aws_default_region}')
    print(f'Bedrock Model: {settings.bedrock_model_id}')
    print(f'Bedrock Region: {settings.bedrock_region}')
    print(f'Knowledge Base ID: {settings.bedrock_knowledge_base_id or "Not set"}')
    print(f'Database URL: {settings.database_url}')
    
    # Test AWS client initialization
    from src.utils.aws_utils import get_sts_client, get_bedrock_client, get_bedrock_agent_client
    
    print('\n🔧 Testing AWS Client Initialization:')
    print('=' * 50)
    
    sts_client = get_sts_client(settings.aws_default_region)
    identity = sts_client.get_caller_identity()
    print(f'✅ STS Client: Working (Account: {identity.get("Account")})')
    
    bedrock_client = get_bedrock_client(settings.bedrock_region)
    print(f'✅ Bedrock Client: Initialized')
    
    bedrock_agent_client = get_bedrock_agent_client(settings.bedrock_region)
    print(f'✅ Bedrock Agent Client: Initialized')
    
    print('\n✅ All AWS clients initialized successfully!')
    print('\n🚀 The application is ready to connect to AWS services!')
    
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

