# AWS Infrastructure Setup Script

This script automates the setup of AWS infrastructure required for the Adobe Analytics RAG system.

## Features

- **S3 Bucket Creation**: Creates a dedicated S3 bucket for Adobe documentation storage
- **Folder Structure**: Sets up organized folder structure for different Adobe services
- **IAM Roles & Policies**: Creates necessary IAM roles for S3 and Bedrock access
- **Bucket Policies**: Configures bucket policies for Bedrock Knowledge Base access
- **Lifecycle Policies**: Implements cost optimization through intelligent data archiving
- **Idempotent**: Safe to run multiple times without creating duplicate resources
- **Error Handling**: Comprehensive error handling and logging

## Prerequisites

1. **AWS CLI configured** with appropriate permissions
2. **Python 3.7+** installed
3. **Virtual environment** set up (see Setup section below)
4. **AWS permissions** for:
   - S3 bucket creation and management
   - IAM role and policy creation
   - Bedrock service access

## Setup

### 1. Initial Project Setup

First, run the main setup script to create the virtual environment and install dependencies:

```bash
# Run the main setup script
bash scripts/setup.sh

# Activate the virtual environment
source venv/bin/activate
```

### 2. Verify Dependencies

Ensure boto3 is installed:

```bash
pip list | grep boto3
```

## Usage

### Basic Usage

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run the AWS setup script
python scripts/setup_aws_infrastructure.py
```

### With Environment Variables

```bash
# Activate virtual environment
source venv/bin/activate

# Set environment variables
export AWS_REGION=us-west-2
export S3_BUCKET_NAME=my-adobe-docs-bucket
export BEDROCK_KNOWLEDGE_BASE_ROLE_NAME=MyBedrockRole
export S3_ACCESS_ROLE_NAME=MyS3Role

# Run the script
python scripts/setup_aws_infrastructure.py
```

## Environment Variables

| Variable                           | Default                             | Description                      |
| ---------------------------------- | ----------------------------------- | -------------------------------- |
| `AWS_REGION`                       | `us-east-1`                         | AWS region for resource creation |
| `S3_BUCKET_NAME`                   | `adobe-analytics-rag-docs-{random}` | Name for the S3 bucket           |
| `BEDROCK_KNOWLEDGE_BASE_ROLE_NAME` | `AdobeAnalyticsRAGBedrockRole`      | IAM role name for Bedrock        |
| `S3_ACCESS_ROLE_NAME`              | `AdobeAnalyticsRAGS3Role`           | IAM role name for S3 access      |

## Created Resources

### S3 Bucket

- **Name**: As specified or auto-generated
- **Versioning**: Enabled
- **Public Access**: Blocked
- **Lifecycle Policies**: Configured for cost optimization

### Folder Structure

```
adobe-docs/
├── adobe-analytics/
├── customer-journey-analytics/
├── analytics-apis/
└── cja-apis/
```

### IAM Roles

1. **S3 Access Role**: For general S3 operations
2. **Bedrock Role**: For Bedrock Knowledge Base operations

### Lifecycle Policies

- **30 days**: Move to Standard-IA
- **90 days**: Move to Glacier
- **365 days**: Move to Deep Archive
- **Version management**: Automatic cleanup of old versions

## Output

The script provides:

- Real-time logging to console and `aws_setup.log`
- Detailed summary of created resources
- Next steps for using the infrastructure

## Error Handling

The script includes comprehensive error handling for:

- AWS credential issues
- Permission errors
- Resource conflicts
- Network connectivity issues
- Invalid configurations

## Logging

Logs are written to:

- Console output (INFO level and above)
- `aws_setup.log` file (all levels)

## Next Steps

After running the script:

1. **Upload Documentation**: Place your Adobe documentation files in the appropriate S3 folders
2. **Create Knowledge Base**: Use the Bedrock console to create a Knowledge Base with the S3 data source
3. **Configure RAG Application**: Update your RAG application to use the Knowledge Base

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure your AWS credentials have sufficient permissions
2. **Bucket Name Conflicts**: Use a unique bucket name or let the script generate one
3. **Region Issues**: Ensure the specified region supports all required services
4. **Role Creation Fails**: Check IAM permissions and role name conflicts

### Verification

The script includes built-in verification to ensure all resources are created correctly. Check the output for any warnings or errors.

## Security Notes

- All S3 buckets are created with public access blocked
- IAM roles follow the principle of least privilege
- Bucket policies are scoped to specific roles
- No sensitive data is logged or exposed
