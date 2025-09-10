#!/usr/bin/env python3
"""
Interactive .env Setup Script

This script helps you set up your .env file step by step with guided prompts.
"""

import os
import secrets
import sys
from pathlib import Path


def print_header():
    """Print the setup header."""
    print("=" * 60)
    print("🔧 Adobe Analytics RAG - Environment Setup")
    print("=" * 60)
    print("This script will help you configure your .env file step by step.")
    print("You can skip any section by pressing Enter.")
    print()


def get_input(prompt, default="", required=False, secret=False):
    """Get user input with validation."""
    while True:
        if secret:
            import getpass
            value = getpass.getpass(f"{prompt} [{default}]: ").strip()
        else:
            value = input(f"{prompt} [{default}]: ").strip()
        
        if not value:
            value = default
            
        if required and not value:
            print("❌ This field is required. Please enter a value.")
            continue
            
        return value


def generate_secret_key():
    """Generate a secure secret key."""
    return secrets.token_urlsafe(32)


def setup_basic_config():
    """Setup basic application configuration."""
    print("\n📋 Step 1: Basic Application Configuration")
    print("-" * 40)
    
    config = {}
    config['ENVIRONMENT'] = get_input("Environment (development/production)", "development")
    config['LOG_LEVEL'] = get_input("Log level (DEBUG/INFO/WARNING/ERROR)", "INFO")
    config['DEBUG'] = get_input("Enable debug mode (true/false)", "false")
    config['SECRET_KEY'] = generate_secret_key()
    
    print(f"✅ Generated secret key: {config['SECRET_KEY'][:8]}...")
    return config


def setup_aws_config():
    """Setup AWS configuration."""
    print("\n☁️ Step 2: AWS Configuration")
    print("-" * 40)
    print("You can use either AWS access keys or AWS profile.")
    print("For development: Use access keys")
    print("For production: Use AWS profile (recommended)")
    
    use_profile = get_input("Use AWS profile instead of access keys? (y/n)", "n").lower() == 'y'
    
    config = {}
    if use_profile:
        config['AWS_PROFILE'] = get_input("AWS profile name", "adobe-rag")
        print("ℹ️  Make sure to run 'aws configure --profile adobe-rag' first")
    else:
        config['AWS_ACCESS_KEY_ID'] = get_input("AWS Access Key ID", required=True, secret=True)
        config['AWS_SECRET_ACCESS_KEY'] = get_input("AWS Secret Access Key", required=True, secret=True)
    
    config['AWS_DEFAULT_REGION'] = get_input("AWS Region", "us-east-1")
    config['AWS_S3_BUCKET'] = get_input("S3 Bucket Name", f"adobe-analytics-rag-docs-{secrets.token_hex(4)}")
    
    return config


def setup_adobe_config():
    """Setup Adobe Analytics configuration."""
    print("\n🎨 Step 3: Adobe Analytics API Configuration")
    print("-" * 40)
    print("Get these from Adobe Developer Console: https://developer.adobe.com/")
    print("1. Create a new project")
    print("2. Choose 'API' → 'Adobe Analytics API'")
    print("3. Generate keypair and download private key")
    
    config = {}
    config['ADOBE_CLIENT_ID'] = get_input("Adobe Client ID", required=True)
    config['ADOBE_CLIENT_SECRET'] = get_input("Adobe Client Secret", required=True, secret=True)
    config['ADOBE_ORGANIZATION_ID'] = get_input("Adobe Organization ID", required=True)
    config['ADOBE_TECHNICAL_ACCOUNT_ID'] = get_input("Adobe Technical Account ID", required=True)
    config['ADOBE_PRIVATE_KEY_PATH'] = get_input("Path to private key file", "./adobe_private_key.pem")
    
    return config


def setup_ai_config():
    """Setup AI/LLM configuration."""
    print("\n🤖 Step 4: AI/LLM Configuration")
    print("-" * 40)
    print("Choose your AI provider:")
    print("1. OpenAI (recommended)")
    print("2. Azure OpenAI")
    
    provider = get_input("Choose provider (1/2)", "1")
    
    config = {}
    if provider == "1":
        config['OPENAI_API_KEY'] = get_input("OpenAI API Key", required=True, secret=True)
        print("ℹ️  Get your API key from: https://platform.openai.com/api-keys")
    else:
        config['AZURE_OPENAI_ENDPOINT'] = get_input("Azure OpenAI Endpoint", required=True)
        config['AZURE_OPENAI_API_KEY'] = get_input("Azure OpenAI API Key", required=True, secret=True)
        config['AZURE_OPENAI_API_VERSION'] = get_input("Azure OpenAI API Version", "2024-02-15-preview")
        config['AZURE_OPENAI_DEPLOYMENT_NAME'] = get_input("Azure OpenAI Deployment Name", required=True)
    
    return config


def setup_rag_config():
    """Setup RAG configuration."""
    print("\n🔍 Step 5: RAG Configuration (Optional)")
    print("-" * 40)
    print("These settings control how documents are processed and stored.")
    
    config = {}
    config['CHUNK_SIZE'] = get_input("Text chunk size", "1000")
    config['CHUNK_OVERLAP'] = get_input("Chunk overlap", "200")
    config['EMBEDDING_MODEL'] = get_input("Embedding model", "sentence-transformers/all-MiniLM-L6-v2")
    config['VECTOR_STORE_PATH'] = get_input("Vector store path", "./vector_store")
    
    return config


def setup_database_config():
    """Setup database configuration."""
    print("\n🗄️ Step 6: Database Configuration")
    print("-" * 40)
    print("Choose your database:")
    print("1. SQLite (default, no setup required)")
    print("2. PostgreSQL (for production)")
    
    db_type = get_input("Choose database (1/2)", "1")
    
    config = {}
    if db_type == "1":
        config['DATABASE_URL'] = "sqlite:///./adobe_analytics_rag.db"
    else:
        host = get_input("Database host", "localhost")
        port = get_input("Database port", "5432")
        name = get_input("Database name", "adobe_analytics_rag")
        user = get_input("Database user", "postgres")
        password = get_input("Database password", required=True, secret=True)
        config['DATABASE_URL'] = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    
    return config


def write_env_file(config, env_path):
    """Write the configuration to .env file."""
    print(f"\n💾 Writing configuration to {env_path}")
    
    with open(env_path, 'w') as f:
        f.write("# =============================================================================\n")
        f.write("# Adobe Analytics RAG Chatbot - Environment Configuration\n")
        f.write("# =============================================================================\n")
        f.write("# Generated by setup_env.py\n\n")
        
        # Group configurations
        sections = {
            "AWS Configuration": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION", "AWS_S3_BUCKET", "AWS_PROFILE"],
            "Adobe Analytics API Configuration": ["ADOBE_CLIENT_ID", "ADOBE_CLIENT_SECRET", "ADOBE_ORGANIZATION_ID", "ADOBE_TECHNICAL_ACCOUNT_ID", "ADOBE_PRIVATE_KEY_PATH"],
            "AI/LLM Configuration": ["OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_API_VERSION", "AZURE_OPENAI_DEPLOYMENT_NAME"],
            "Application Configuration": ["ENVIRONMENT", "LOG_LEVEL", "DEBUG", "SECRET_KEY"],
            "Database Configuration": ["DATABASE_URL"],
            "RAG Configuration": ["CHUNK_SIZE", "CHUNK_OVERLAP", "EMBEDDING_MODEL", "VECTOR_STORE_PATH"],
        }
        
        for section_name, keys in sections.items():
            f.write(f"\n# {section_name}\n")
            for key in keys:
                if key in config and config[key]:
                    f.write(f"{key}={config[key]}\n")
            f.write("\n")
        
        # Add default configurations
        f.write("# Streamlit Configuration\n")
        f.write("STREAMLIT_SERVER_PORT=8501\n")
        f.write("STREAMLIT_SERVER_ADDRESS=0.0.0.0\n\n")
        
        f.write("# Data Pipeline Configuration\n")
        f.write("DATA_REFRESH_INTERVAL=3600\n")
        f.write("MAX_DOCUMENTS=10000\n\n")
        
        f.write("# Monitoring and Logging\n")
        f.write("ENABLE_DETAILED_LOGGING=true\n")
        f.write("LOG_FILE_PATH=./logs/adobe_analytics_rag.log\n\n")
        
        f.write("# Development/Testing Configuration\n")
        f.write("SKIP_DATA_INGESTION=false\n")
        f.write("SKIP_VECTOR_STORE_BUILD=false\n")
        f.write("USE_MOCK_DATA=false\n")
        f.write("MOCK_DATA_PATH=./data/mock_data.json\n")


def main():
    """Main setup function."""
    print_header()
    
    # Check if .env already exists
    env_path = Path(".env")
    if env_path.exists():
        overwrite = get_input("⚠️  .env file already exists. Overwrite? (y/n)", "n").lower() == 'y'
        if not overwrite:
            print("❌ Setup cancelled.")
            return
    
    # Collect all configuration
    config = {}
    config.update(setup_basic_config())
    config.update(setup_aws_config())
    config.update(setup_adobe_config())
    config.update(setup_ai_config())
    config.update(setup_rag_config())
    config.update(setup_database_config())
    
    # Write .env file
    write_env_file(config, env_path)
    
    print("\n✅ Configuration saved successfully!")
    print("\n📋 Next Steps:")
    print("1. Review your .env file: cat .env")
    print("2. Place your Adobe private key file in the project root")
    print("3. Test your configuration: python test_config.py")
    print("4. Run AWS infrastructure setup: python scripts/setup_aws_infrastructure.py")
    print("5. Start the application: streamlit run src/app.py")
    
    print("\n🔒 Security Reminder:")
    print("- Never commit .env to version control")
    print("- Keep your API keys secure")
    print("- Rotate keys regularly")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)
