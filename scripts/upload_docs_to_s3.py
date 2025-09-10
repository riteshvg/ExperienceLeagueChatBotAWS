#!/usr/bin/env python3
"""
Upload Adobe Documentation to S3

This script uploads Adobe Analytics and Customer Journey Analytics documentation
from GitHub repositories to the S3 bucket for use with Bedrock Knowledge Base.
"""

import os
import sys
import json
import logging
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import boto3
from botocore.exceptions import ClientError
import requests
from git import Repo

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings


class DocumentUploader:
    """Handles uploading Adobe documentation to S3."""
    
    def __init__(self):
        """Initialize the document uploader."""
        self.setup_logging()
        self.load_configuration()
        self.initialize_aws_clients()
        
    def setup_logging(self):
        """Configure logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def load_configuration(self):
        """Load configuration from settings."""
        try:
            settings = get_settings()
            self.bucket_name = settings.aws_s3_bucket
            self.region = settings.aws_default_region
            self.logger.info(f"Configuration loaded - Bucket: {self.bucket_name}, Region: {self.region}")
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
            
    def initialize_aws_clients(self):
        """Initialize AWS clients."""
        try:
            self.s3_client = boto3.client('s3', region_name=self.region)
            self.logger.info("AWS S3 client initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize AWS clients: {e}")
            raise
    
    def clone_repository(self, repo_url: str, target_dir: Path) -> bool:
        """
        Clone a Git repository to a local directory.
        
        Args:
            repo_url: Git repository URL
            target_dir: Target directory for cloning
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if target_dir.exists():
                self.logger.info(f"Repository already exists at {target_dir}, pulling latest changes...")
                repo = Repo(target_dir)
                repo.remotes.origin.pull()
            else:
                self.logger.info(f"Cloning repository: {repo_url}")
                Repo.clone_from(repo_url, target_dir)
            
            self.logger.info(f"Repository cloned successfully to {target_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clone repository {repo_url}: {e}")
            return False
    
    def upload_directory_to_s3(self, local_dir: Path, s3_prefix: str) -> bool:
        """
        Upload a directory to S3.
        
        Args:
            local_dir: Local directory to upload
            s3_prefix: S3 prefix (folder path)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            uploaded_count = 0
            total_files = 0
            
            # Count total files first
            for file_path in local_dir.rglob('*'):
                if file_path.is_file() and self.is_document_file(file_path):
                    total_files += 1
            
            self.logger.info(f"Found {total_files} document files to upload")
            
            # Upload files
            for file_path in local_dir.rglob('*'):
                if file_path.is_file() and self.is_document_file(file_path):
                    relative_path = file_path.relative_to(local_dir)
                    s3_key = f"{s3_prefix}/{relative_path}".replace('\\', '/')
                    
                    try:
                        self.s3_client.upload_file(
                            str(file_path),
                            self.bucket_name,
                            s3_key,
                            ExtraArgs={'ContentType': self.get_content_type(file_path)}
                        )
                        uploaded_count += 1
                        self.logger.info(f"Uploaded: {s3_key} ({uploaded_count}/{total_files})")
                        
                    except Exception as e:
                        self.logger.error(f"Failed to upload {file_path}: {e}")
            
            self.logger.info(f"Upload completed: {uploaded_count}/{total_files} files uploaded")
            return uploaded_count > 0
            
        except Exception as e:
            self.logger.error(f"Failed to upload directory {local_dir}: {e}")
            return False
    
    def is_document_file(self, file_path: Path) -> bool:
        """
        Check if a file is a document file that should be uploaded.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if it's a document file, False otherwise
        """
        # Document file extensions
        doc_extensions = {'.md', '.txt', '.rst', '.pdf', '.html', '.htm', '.json', '.yaml', '.yml'}
        
        # Skip certain directories and files
        skip_patterns = {
            '.git', '__pycache__', '.DS_Store', 'node_modules', 
            '.gitignore', 'README.md', 'LICENSE', 'CHANGELOG.md'
        }
        
        # Check extension
        if file_path.suffix.lower() not in doc_extensions:
            return False
        
        # Check if file should be skipped
        if any(pattern in str(file_path) for pattern in skip_patterns):
            return False
        
        # Skip very large files (>10MB)
        if file_path.stat().st_size > 10 * 1024 * 1024:
            return False
        
        return True
    
    def get_content_type(self, file_path: Path) -> str:
        """
        Get the appropriate content type for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Content type string
        """
        content_types = {
            '.md': 'text/markdown',
            '.txt': 'text/plain',
            '.rst': 'text/x-rst',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.json': 'application/json',
            '.yaml': 'text/yaml',
            '.yml': 'text/yaml',
            '.pdf': 'application/pdf'
        }
        
        return content_types.get(file_path.suffix.lower(), 'text/plain')
    
    def upload_adobe_docs(self) -> bool:
        """Upload Adobe Analytics documentation."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Clone Adobe Analytics API docs
                adobe_analytics_dir = temp_path / "adobe-analytics-apis"
                if not self.clone_repository(
                    "https://github.com/AdobeDocs/analytics-2.0-apis.git",
                    adobe_analytics_dir
                ):
                    return False
                
                # Upload API docs to S3
                if not self.upload_directory_to_s3(
                    adobe_analytics_dir,
                    "adobe-docs/analytics-apis"
                ):
                    return False
                
                # Clone main Adobe Analytics user documentation
                adobe_user_docs_dir = temp_path / "adobe-analytics-user"
                if not self.clone_repository(
                    "https://github.com/AdobeDocs/analytics.en.git",
                    adobe_user_docs_dir
                ):
                    return False
                
                # Upload user docs to S3
                return self.upload_directory_to_s3(
                    adobe_user_docs_dir,
                    "adobe-docs/adobe-analytics"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to upload Adobe Analytics docs: {e}")
            return False
    
    def upload_cja_docs(self) -> bool:
        """Upload Customer Journey Analytics documentation."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Clone English CJA docs
                cja_dir = temp_path / "customer-journey-analytics"
                if not self.clone_repository(
                    "https://github.com/AdobeDocs/customer-journey-analytics-learn.en.git",
                    cja_dir
                ):
                    self.logger.error("Failed to clone CJA repository")
                    return False
                
                # Upload to S3
                if not self.upload_directory_to_s3(
                    cja_dir,
                    "adobe-docs/customer-journey-analytics"
                ):
                    return False
                
                self.logger.info("✅ Customer Journey Analytics docs uploaded successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to upload CJA docs: {e}")
            return False
    
    def upload_analytics_apis_docs(self) -> bool:
        """Upload Analytics APIs documentation."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Clone Analytics APIs docs
                apis_dir = temp_path / "analytics-apis"
                if not self.clone_repository(
                    "https://github.com/AdobeDocs/analytics-2.0-apis.git",
                    apis_dir
                ):
                    return False
                
                # Upload to S3
                return self.upload_directory_to_s3(
                    apis_dir,
                    "adobe-docs/analytics-apis"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to upload Analytics APIs docs: {e}")
            return False
    
    def list_uploaded_docs(self) -> bool:
        """List uploaded documents in S3."""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix="adobe-docs/"
            )
            
            if 'Contents' in response:
                self.logger.info(f"Found {len(response['Contents'])} documents in S3:")
                for obj in response['Contents'][:10]:  # Show first 10
                    self.logger.info(f"  - {obj['Key']}")
                if len(response['Contents']) > 10:
                    self.logger.info(f"  ... and {len(response['Contents']) - 10} more files")
            else:
                self.logger.info("No documents found in S3")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to list documents: {e}")
            return False
    
    def run_upload(self) -> bool:
        """Run the complete document upload process."""
        self.logger.info("Starting Adobe documentation upload...")
        
        try:
            # Upload different documentation sources
            success_count = 0
            total_sources = 3
            
            # Upload Adobe Analytics docs
            if self.upload_adobe_docs():
                success_count += 1
                self.logger.info("✅ Adobe Analytics docs uploaded successfully")
            else:
                self.logger.error("❌ Failed to upload Adobe Analytics docs")
            
            # Upload CJA docs
            if self.upload_cja_docs():
                success_count += 1
                self.logger.info("✅ Customer Journey Analytics docs uploaded successfully")
            else:
                self.logger.error("❌ Failed to upload CJA docs")
            
            # Upload Analytics APIs docs
            if self.upload_analytics_apis_docs():
                success_count += 1
                self.logger.info("✅ Analytics APIs docs uploaded successfully")
            else:
                self.logger.error("❌ Failed to upload Analytics APIs docs")
            
            # List uploaded documents
            self.list_uploaded_docs()
            
            self.logger.info(f"Upload completed: {success_count}/{total_sources} sources uploaded successfully")
            
            if success_count > 0:
                self.logger.info("🎉 Document upload completed successfully!")
                self.logger.info("Next steps:")
                self.logger.info("1. Enable Bedrock models in AWS console")
                self.logger.info("2. Create Bedrock Knowledge Base with S3 data source")
                self.logger.info("3. Test the complete RAG pipeline")
                return True
            else:
                self.logger.error("❌ No documents were uploaded successfully")
                return False
                
        except Exception as e:
            self.logger.error(f"Upload process failed: {e}")
            return False


def main():
    """Main function."""
    try:
        uploader = DocumentUploader()
        success = uploader.run_upload()
        
        if success:
            print("\n✅ Document upload completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Document upload failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n❌ Upload interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
