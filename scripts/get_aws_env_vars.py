#!/usr/bin/env python3
"""
Retrieve environment variables from AWS services.

This script can retrieve environment variables from:
1. AWS Secrets Manager
2. AWS Systems Manager Parameter Store
3. AWS CLI configuration files
4. EC2 instance metadata (if running on EC2)
"""

import os
import sys
import json
import boto3
from pathlib import Path
from typing import Dict, Optional, List
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError


def print_header():
    """Print script header."""
    print("🔐 AWS Environment Variables Retriever")
    print("=" * 50)
    print()


def get_aws_cli_credentials(profile: Optional[str] = None) -> Dict[str, str]:
    """Get AWS credentials from AWS CLI configuration files."""
    print("📋 Checking AWS CLI configuration...")
    
    aws_dir = Path.home() / '.aws'
    credentials_file = aws_dir / 'credentials'
    config_file = aws_dir / 'config'
    
    env_vars = {}
    
    if not credentials_file.exists():
        print("   ⚠️  No AWS credentials file found")
        return env_vars
    
    try:
        import configparser
        config = configparser.ConfigParser()
        config.read(credentials_file)
        
        # Use default profile or specified profile
        profile_name = profile or 'default'
        
        if profile_name in config:
            access_key = config[profile_name].get('aws_access_key_id')
            secret_key = config[profile_name].get('aws_secret_access_key')
            
            if access_key:
                env_vars['AWS_ACCESS_KEY_ID'] = access_key
                print(f"   ✅ Found AWS_ACCESS_KEY_ID in profile '{profile_name}'")
            if secret_key:
                env_vars['AWS_SECRET_ACCESS_KEY'] = secret_key
                print(f"   ✅ Found AWS_SECRET_ACCESS_KEY in profile '{profile_name}'")
        else:
            print(f"   ⚠️  Profile '{profile_name}' not found in credentials file")
            
    except Exception as e:
        print(f"   ❌ Error reading credentials file: {e}")
    
    # Get region from config file
    if config_file.exists():
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read(config_file)
            
            profile_name = profile or 'default'
            section_name = f'profile {profile_name}' if profile_name != 'default' else 'default'
            
            if section_name in config:
                region = config[section_name].get('region')
                if region:
                    env_vars['AWS_DEFAULT_REGION'] = region
                    print(f"   ✅ Found AWS_DEFAULT_REGION: {region}")
        except Exception as e:
            print(f"   ⚠️  Error reading config file: {e}")
    
    return env_vars


def get_secret_from_secrets_manager(secret_name: str, region: str = "us-east-1") -> Optional[Dict]:
    """Get secret from AWS Secrets Manager."""
    try:
        client = boto3.client('secretsmanager', region_name=region)
        
        response = client.get_secret_value(SecretId=secret_name)
        
        # Parse the secret string (usually JSON)
        secret_string = response.get('SecretString', '')
        if secret_string:
            try:
                return json.loads(secret_string)
            except json.JSONDecodeError:
                # If not JSON, return as plain text
                return {'SECRET_VALUE': secret_string}
        
        return None
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            print(f"   ❌ Secret '{secret_name}' not found")
        elif error_code == 'AccessDeniedException':
            print(f"   ❌ Access denied to secret '{secret_name}'")
        else:
            print(f"   ❌ Error retrieving secret: {e}")
        return None
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return None


def get_parameter_from_ssm(parameter_name: str, region: str = "us-east-1", decrypt: bool = True) -> Optional[str]:
    """Get parameter from AWS Systems Manager Parameter Store."""
    try:
        client = boto3.client('ssm', region_name=region)
        
        response = client.get_parameter(
            Name=parameter_name,
            WithDecryption=decrypt
        )
        
        return response['Parameter']['Value']
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ParameterNotFound':
            print(f"   ❌ Parameter '{parameter_name}' not found")
        elif error_code == 'AccessDeniedException':
            print(f"   ❌ Access denied to parameter '{parameter_name}'")
        else:
            print(f"   ❌ Error retrieving parameter: {e}")
        return None
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return None


def get_parameters_by_path_ssm(path: str, region: str = "us-east-1", decrypt: bool = True) -> Dict[str, str]:
    """Get multiple parameters from SSM Parameter Store by path."""
    env_vars = {}
    
    try:
        client = boto3.client('ssm', region_name=region)
        
        paginator = client.get_paginator('get_parameters_by_path')
        page_iterator = paginator.paginate(
            Path=path,
            Recursive=True,
            WithDecryption=decrypt
        )
        
        for page in page_iterator:
            for param in page.get('Parameters', []):
                # Extract parameter name (remove path prefix)
                param_name = param['Name'].replace(path, '').lstrip('/')
                # Convert to environment variable format
                env_var_name = param_name.replace('/', '_').upper()
                env_vars[env_var_name] = param['Value']
                print(f"   ✅ Found parameter: {env_var_name}")
        
        return env_vars
        
    except ClientError as e:
        print(f"   ❌ Error retrieving parameters from path '{path}': {e}")
        return env_vars
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return env_vars


def get_ec2_metadata() -> Dict[str, str]:
    """Get metadata from EC2 instance (if running on EC2)."""
    env_vars = {}
    
    try:
        import requests
        
        # Try to get instance metadata
        metadata_url = "http://169.254.169.254/latest/meta-data/"
        
        # Check if we're on EC2
        response = requests.get(metadata_url, timeout=2)
        if response.status_code == 200:
            print("   ✅ Running on EC2 instance")
            
            # Get region
            identity_url = "http://169.254.169.254/latest/dynamic/instance-identity/document"
            identity = requests.get(identity_url, timeout=2).json()
            if 'region' in identity:
                env_vars['AWS_DEFAULT_REGION'] = identity['region']
                print(f"   ✅ Found region from EC2 metadata: {identity['region']}")
            
            return env_vars
        else:
            print("   ℹ️  Not running on EC2 instance")
            return env_vars
            
    except Exception:
        print("   ℹ️  Not running on EC2 instance")
        return env_vars


def test_aws_connection() -> bool:
    """Test AWS credentials by calling STS."""
    try:
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()
        print(f"   ✅ AWS credentials valid")
        print(f"      Account ID: {identity.get('Account')}")
        print(f"      ARN: {identity.get('Arn')}")
        return True
    except NoCredentialsError:
        print("   ❌ No AWS credentials found")
        return False
    except Exception as e:
        print(f"   ❌ Error testing credentials: {e}")
        return False


def save_to_env_file(env_vars: Dict[str, str], env_file: str = '.env', append: bool = True):
    """Save environment variables to .env file."""
    env_path = Path(env_file)
    
    # Read existing content if appending
    existing_content = []
    if append and env_path.exists():
        with open(env_path, 'r') as f:
            existing_content = f.readlines()
    
    # Remove existing entries for variables we're adding
    existing_vars = {var.split('=')[0] for var in existing_content if '=' in var}
    
    # Write back existing vars (excluding ones we're updating)
    new_content = []
    for line in existing_content:
        var_name = line.split('=')[0].strip() if '=' in line else None
        if var_name and var_name not in env_vars:
            new_content.append(line)
    
    # Add new/updated variables
    for var_name, var_value in env_vars.items():
        new_content.append(f"{var_name}={var_value}\n")
    
    # Write to file
    with open(env_path, 'w') as f:
        f.writelines(new_content)
    
    print(f"\n✅ Saved {len(env_vars)} environment variables to {env_file}")


def main():
    """Main function."""
    print_header()
    
    # Check command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Retrieve environment variables from AWS')
    parser.add_argument('--source', choices=['cli', 'secrets', 'ssm', 'ssm-path', 'ec2', 'all'], 
                       default='all', help='Source to retrieve from')
    parser.add_argument('--secret-name', help='Secrets Manager secret name')
    parser.add_argument('--ssm-path', help='SSM Parameter Store path (e.g., /adobe-rag/)')
    parser.add_argument('--ssm-param', help='SSM Parameter Store parameter name')
    parser.add_argument('--profile', help='AWS CLI profile name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--save', action='store_true', help='Save to .env file')
    parser.add_argument('--output', default='.env', help='Output file path')
    
    args = parser.parse_args()
    
    all_env_vars = {}
    
    # Get from AWS CLI
    if args.source in ['cli', 'all']:
        print("\n1️⃣  Retrieving from AWS CLI configuration...")
        cli_vars = get_aws_cli_credentials(args.profile)
        all_env_vars.update(cli_vars)
    
    # Get from EC2 metadata
    if args.source in ['ec2', 'all']:
        print("\n2️⃣  Checking EC2 instance metadata...")
        ec2_vars = get_ec2_metadata()
        all_env_vars.update(ec2_vars)
    
    # Test AWS connection
    if all_env_vars or args.source in ['secrets', 'ssm', 'ssm-path']:
        print("\n3️⃣  Testing AWS connection...")
        if not test_aws_connection():
            print("\n⚠️  Warning: AWS credentials may not be configured correctly")
            print("   Some operations may fail. Continuing anyway...")
    
    # Get from Secrets Manager
    if args.source in ['secrets', 'all']:
        if args.secret_name:
            print(f"\n4️⃣  Retrieving from Secrets Manager: {args.secret_name}...")
            secret_data = get_secret_from_secrets_manager(args.secret_name, args.region)
            if secret_data:
                # Convert secret keys to uppercase env var format
                for key, value in secret_data.items():
                    env_key = key.upper().replace('-', '_')
                    all_env_vars[env_key] = str(value)
                    print(f"   ✅ Retrieved: {env_key}")
        else:
            print("\n4️⃣  Secrets Manager: --secret-name not specified, skipping")
    
    # Get from SSM Parameter Store (single parameter)
    if args.source in ['ssm', 'all']:
        if args.ssm_param:
            print(f"\n5️⃣  Retrieving from SSM Parameter Store: {args.ssm_param}...")
            param_value = get_parameter_from_ssm(args.ssm_param, args.region)
            if param_value:
                # Extract env var name from parameter name
                env_key = args.ssm_param.split('/')[-1].upper().replace('-', '_')
                all_env_vars[env_key] = param_value
                print(f"   ✅ Retrieved: {env_key}")
        else:
            print("\n5️⃣  SSM Parameter Store: --ssm-param not specified, skipping")
    
    # Get from SSM Parameter Store (path)
    if args.source in ['ssm-path', 'all']:
        if args.ssm_path:
            print(f"\n6️⃣  Retrieving from SSM Parameter Store path: {args.ssm_path}...")
            ssm_vars = get_parameters_by_path_ssm(args.ssm_path, args.region)
            all_env_vars.update(ssm_vars)
        else:
            print("\n6️⃣  SSM Parameter Store path: --ssm-path not specified, skipping")
    
    # Display results
    print("\n" + "=" * 50)
    print("📊 Retrieved Environment Variables:")
    print("=" * 50)
    
    if all_env_vars:
        for var_name, var_value in sorted(all_env_vars.items()):
            # Mask sensitive values
            if 'SECRET' in var_name or 'KEY' in var_name or 'PASSWORD' in var_name:
                masked_value = var_value[:4] + '*' * (len(var_value) - 8) + var_value[-4:] if len(var_value) > 8 else '****'
                print(f"   {var_name}={masked_value}")
            else:
                print(f"   {var_name}={var_value}")
    else:
        print("   ⚠️  No environment variables retrieved")
    
    # Save to file if requested
    if args.save and all_env_vars:
        print("\n" + "=" * 50)
        save_to_env_file(all_env_vars, args.output, append=True)
    
    print("\n" + "=" * 50)
    print("✅ Done!")
    print("\n💡 Usage examples:")
    print("   # Get from AWS CLI config:")
    print("   python scripts/get_aws_env_vars.py --source cli --save")
    print("\n   # Get from Secrets Manager:")
    print("   python scripts/get_aws_env_vars.py --source secrets --secret-name adobe-rag-config --save")
    print("\n   # Get from SSM Parameter Store path:")
    print("   python scripts/get_aws_env_vars.py --source ssm-path --ssm-path /adobe-rag/ --save")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

