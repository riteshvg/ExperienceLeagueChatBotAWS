#!/usr/bin/env python3
"""
AWS Credentials Setup Helper

This script helps you set up AWS credentials in multiple ways.
"""

import os
import sys
from pathlib import Path


def print_header():
    """Print the setup header."""
    print("🔑 AWS Credentials Setup Helper")
    print("=" * 40)
    print("This script will help you configure AWS credentials.")
    print()


def check_existing_credentials():
    """Check if AWS credentials already exist."""
    print("🔍 Checking existing AWS credentials...")
    
    # Check environment variables
    env_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_PROFILE']
    env_found = [var for var in env_vars if os.getenv(var)]
    
    if env_found:
        print(f"✅ Found environment variables: {', '.join(env_found)}")
        return True
    
    # Check AWS credentials file
    aws_dir = Path.home() / '.aws'
    credentials_file = aws_dir / 'credentials'
    config_file = aws_dir / 'config'
    
    if credentials_file.exists():
        print(f"✅ Found AWS credentials file: {credentials_file}")
        return True
    
    if config_file.exists():
        print(f"✅ Found AWS config file: {config_file}")
        return True
    
    print("❌ No AWS credentials found")
    return False


def setup_environment_variables():
    """Set up AWS credentials as environment variables."""
    print("\n🔧 Setting up environment variables...")
    
    access_key = input("Enter your AWS Access Key ID: ").strip()
    secret_key = input("Enter your AWS Secret Access Key: ").strip()
    region = input("Enter AWS Region (default: us-east-1): ").strip() or "us-east-1"
    
    if not access_key or not secret_key:
        print("❌ Access key and secret key are required")
        return False
    
    # Create .env file or update existing one
    env_path = Path('.env')
    env_content = []
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            env_content = f.readlines()
    
    # Update or add AWS credentials
    aws_vars = {
        'AWS_ACCESS_KEY_ID': access_key,
        'AWS_SECRET_ACCESS_KEY': secret_key,
        'AWS_DEFAULT_REGION': region
    }
    
    # Remove existing AWS vars
    env_content = [line for line in env_content 
                   if not any(line.startswith(f"{var}=") for var in aws_vars.keys())]
    
    # Add new AWS vars
    for var, value in aws_vars.items():
        env_content.append(f"{var}={value}\n")
    
    # Write back to .env
    with open(env_path, 'w') as f:
        f.writelines(env_content)
    
    print("✅ AWS credentials added to .env file")
    return True


def setup_aws_cli():
    """Set up AWS CLI configuration."""
    print("\n🔧 Setting up AWS CLI...")
    
    try:
        import subprocess
        
        # Check if AWS CLI is installed
        result = subprocess.run(['aws', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ AWS CLI not found. Installing...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'awscli'])
        
        print("✅ AWS CLI is ready")
        print("\nNow run: aws configure")
        print("Enter your credentials when prompted:")
        print("  - AWS Access Key ID")
        print("  - AWS Secret Access Key")
        print("  - Default region (e.g., us-east-1)")
        print("  - Default output format (json)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up AWS CLI: {e}")
        return False


def setup_aws_profile():
    """Set up AWS profile configuration."""
    print("\n🔧 Setting up AWS profile...")
    
    profile_name = input("Enter profile name (default: adobe-rag): ").strip() or "adobe-rag"
    
    try:
        import subprocess
        
        # Run aws configure with profile
        cmd = ['aws', 'configure', '--profile', profile_name]
        print(f"Running: {' '.join(cmd)}")
        print("Enter your credentials when prompted...")
        
        result = subprocess.run(cmd)
        if result.returncode == 0:
            print(f"✅ AWS profile '{profile_name}' configured successfully")
            
            # Update .env file to use profile
            env_path = Path('.env')
            if env_path.exists():
                with open(env_path, 'r') as f:
                    content = f.read()
                
                # Remove access key lines and add profile
                lines = content.split('\n')
                lines = [line for line in lines 
                        if not line.startswith(('AWS_ACCESS_KEY_ID=', 'AWS_SECRET_ACCESS_KEY='))]
                
                if f"AWS_PROFILE={profile_name}" not in content:
                    lines.append(f"AWS_PROFILE={profile_name}")
                
                with open(env_path, 'w') as f:
                    f.write('\n'.join(lines))
                
                print("✅ Updated .env file to use AWS profile")
            
            return True
        else:
            print("❌ Failed to configure AWS profile")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up AWS profile: {e}")
        return False


def test_credentials():
    """Test AWS credentials."""
    print("\n🧪 Testing AWS credentials...")
    
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        
        # Try to create a client
        try:
            s3_client = boto3.client('s3')
            sts_client = boto3.client('sts')
            
            # Test credentials
            identity = sts_client.get_caller_identity()
            print("✅ AWS credentials are valid!")
            print(f"   Account ID: {identity['Account']}")
            print(f"   User ARN: {identity['Arn']}")
            return True
            
        except NoCredentialsError:
            print("❌ No AWS credentials found")
            return False
        except ClientError as e:
            print(f"❌ AWS credentials invalid: {e}")
            return False
            
    except ImportError:
        print("❌ boto3 not installed. Run: pip install boto3")
        return False


def print_instructions():
    """Print detailed instructions for getting AWS credentials."""
    print("\n📋 How to Get AWS Credentials")
    print("=" * 40)
    print("1. Go to AWS IAM Console: https://console.aws.amazon.com/iam/")
    print("2. Click 'Users' → 'Create user'")
    print("3. Username: adobe-analytics-rag")
    print("4. Select 'Programmatic access'")
    print("5. Attach these policies:")
    print("   - AmazonS3FullAccess")
    print("   - AmazonBedrockFullAccess")
    print("   - IAMFullAccess")
    print("6. Create access key")
    print("7. Download CSV or copy keys immediately")
    print("\n⚠️  Keep your credentials secure!")
    print("   - Never commit them to version control")
    print("   - Rotate them regularly")
    print("   - Use IAM roles when possible")


def main():
    """Main setup function."""
    print_header()
    
    # Check existing credentials
    if check_existing_credentials():
        print("\n✅ AWS credentials already configured!")
        if test_credentials():
            print("🎉 Your AWS setup is working correctly!")
            return
        else:
            print("⚠️  Credentials found but not working. Let's fix this.")
    
    print("\nChoose setup method:")
    print("1. Environment variables (for .env file)")
    print("2. AWS CLI configuration")
    print("3. AWS Profile setup")
    print("4. Show instructions for getting credentials")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        if setup_environment_variables():
            test_credentials()
    elif choice == "2":
        if setup_aws_cli():
            print("\nAfter running 'aws configure', test with: python test_config.py")
    elif choice == "3":
        if setup_aws_profile():
            test_credentials()
    elif choice == "4":
        print_instructions()
    else:
        print("❌ Invalid choice")
        return
    
    print("\n📚 Next Steps:")
    print("1. Test configuration: python test_config.py")
    print("2. Run AWS infrastructure setup: python scripts/setup_aws_infrastructure.py")
    print("3. Start application: streamlit run src/app.py")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)
