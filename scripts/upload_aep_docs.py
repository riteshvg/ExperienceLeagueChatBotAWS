#!/usr/bin/env python3
"""
Upload Adobe Experience Platform Documentation to S3

This script uploads Adobe Experience Platform documentation
from GitHub repository to the S3 bucket for use with Bedrock Knowledge Base.
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


class AEPDocumentUploader:
    """Handles uploading Adobe Experience Platform documentation to S3."""
    
    def __init__(self):
        """Initialize the AEP document uploader."""
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
        Clone or update a Git repository using incremental updates.
        
        Args:
            repo_url: Git repository URL
            target_dir: Target directory for cloning
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if target_dir.exists():
                self.logger.info(f"Repository exists at {target_dir}, pulling latest changes...")
                repo = Repo(target_dir)
                
                # Fetch latest changes
                self.logger.info("Fetching latest changes from remote...")
                repo.remotes.origin.fetch()
                
                # Pull changes
                self.logger.info("Pulling latest changes...")
                repo.remotes.origin.pull()
                
                self.logger.info(f"Repository updated successfully at {target_dir}")
            else:
                self.logger.info(f"Cloning repository (first time): {repo_url}")
                self.logger.info("Using shallow clone for faster download...")
                
                # Use shallow clone with depth 1 for faster initial clone
                Repo.clone_from(
                    repo_url, 
                    target_dir,
                    depth=1  # Only clone latest commit
                )
                
                # After shallow clone, fetch full history if needed
                self.logger.info("Fetching full repository history...")
                repo = Repo(target_dir)
                repo.remotes.origin.fetch(unshallow=True)
                
                self.logger.info(f"Repository cloned successfully at {target_dir}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clone/update repository {repo_url}: {e}")
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
            '.gitignore', 'README.md', 'LICENSE', 'CHANGELOG.md',
            'code-of-conduct.md', 'contributing.md', 'license.md',
            'linkcheckexclude.json', 'markdownlint_custom.json',
            'metadata.md', 'pipeline.opts', 'redirects.csv'
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
        
        # Focus on help directory (main documentation)
        if 'help' not in str(file_path):
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
    
    def upload_aep_docs(self) -> bool:
        """Upload Adobe Experience Platform documentation."""
        try:
            # Use persistent directory for incremental updates
            project_root = Path(__file__).parent.parent
            cache_dir = project_root / ".cache" / "repos"
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Clone/update Adobe Experience Platform docs
            aep_dir = cache_dir / "adobe-experience-platform"
            if not self.clone_repository(
                "https://github.com/AdobeDocs/experience-platform.en.git",
                aep_dir
            ):
                return False
            
            # Upload AEP docs to S3
            if not self.upload_directory_to_s3(
                aep_dir,
                "adobe-docs/experience-platform"
            ):
                return False
            
            self.logger.info("✅ Adobe Experience Platform docs uploaded successfully")
            return True
                
        except Exception as e:
            self.logger.error(f"Failed to upload AEP docs: {e}")
            return False
    
    def list_uploaded_docs(self) -> bool:
        """List uploaded documents in S3."""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix="adobe-docs/experience-platform/"
            )
            
            if 'Contents' in response:
                self.logger.info(f"Found {len(response['Contents'])} AEP documents in S3:")
                for obj in response['Contents'][:10]:  # Show first 10
                    self.logger.info(f"  - {obj['Key']}")
                if len(response['Contents']) > 10:
                    self.logger.info(f"  ... and {len(response['Contents']) - 10} more files")
            else:
                self.logger.info("No AEP documents found in S3")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to list documents: {e}")
            return False
    
    def run_upload(self) -> bool:
        """Run the complete AEP document upload process."""
        self.logger.info("Starting Adobe Experience Platform documentation upload...")
        
        try:
            # Upload AEP documentation
            if self.upload_aep_docs():
                self.logger.info("✅ Adobe Experience Platform docs uploaded successfully")
            else:
                self.logger.error("❌ Failed to upload Adobe Experience Platform docs")
                return False
            
            # List uploaded documents
            self.list_uploaded_docs()
            
            self.logger.info("🎉 AEP document upload completed successfully!")
            self.logger.info("Next steps:")
            self.logger.info("1. Update knowledge base data source to include AEP docs")
            self.logger.info("2. Re-run ingestion job to process AEP documents")
            self.logger.info("3. Test AEP queries in the chatbot")
            return True
                
        except Exception as e:
            self.logger.error(f"Upload process failed: {e}")
            return False


def main():
    """Main function."""
    try:
        uploader = AEPDocumentUploader()
        success = uploader.run_upload()
        
        if success:
            print("\n✅ AEP document upload completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ AEP document upload failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n❌ Upload interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
