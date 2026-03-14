#!/usr/bin/env python3
"""
Update Knowledge Base with Latest Experience League Articles

This script:
1. Fetches latest articles from Experience League (GitHub repos)
2. Uploads them to S3
3. Triggers Knowledge Base sync/ingestion job
4. Monitors ingestion progress
"""

import os
import sys
import json
import logging
import tempfile
import shutil
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
import requests
from git import Repo

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import Settings
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KnowledgeBaseUpdater:
    """Updates Knowledge Base with latest Experience League articles."""
    
    def __init__(self):
        """Initialize the updater."""
        self.settings = Settings()
        self.bucket_name = self.settings.aws_s3_bucket
        self.region = self.settings.aws_default_region
        self.kb_id = self.settings.bedrock_knowledge_base_id
        
        # Initialize AWS clients first (needed for bucket lookup)
        self.s3_client = boto3.client('s3', region_name=self.region)
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=self.region)
        
        # If bucket name not in settings, try to find it from Knowledge Base
        if not self.bucket_name:
            logger.warning("⚠️  S3 bucket name not in settings, attempting to find from Knowledge Base...")
            self.bucket_name = self._find_bucket_from_kb()
        
        if not self.bucket_name:
            raise ValueError("S3 bucket name is required. Set AWS_S3_BUCKET in .env file or configure in Knowledge Base.")
        
        logger.info(f"Initialized - Bucket: {self.bucket_name}, KB ID: {self.kb_id}")
    
    def _find_bucket_from_kb(self) -> Optional[str]:
        """Try to find S3 bucket from Knowledge Base data sources."""
        try:
            if not self.kb_id:
                return None
            
            response = self.bedrock_agent_client.list_data_sources(
                knowledgeBaseId=self.kb_id
            )
            
            for ds in response.get('dataSourceSummaries', []):
                # Get detailed data source info
                try:
                    ds_detail = self.bedrock_agent_client.get_data_source(
                        knowledgeBaseId=self.kb_id,
                        dataSourceId=ds['dataSourceId']
                    )
                    config = ds_detail['dataSource'].get('dataSourceConfiguration', {})
                    if config.get('type') == 'S3':
                        s3_config = config.get('s3Configuration', {})
                        bucket_arn = s3_config.get('bucketArn', '')
                        if bucket_arn:
                            # Extract bucket name from ARN: arn:aws:s3:::bucket-name
                            bucket_name = bucket_arn.split(':')[-1]
                            logger.info(f"Found bucket from Knowledge Base: {bucket_name}")
                            return bucket_name
                except Exception as e:
                    logger.debug(f"Could not get details for data source {ds['dataSourceId']}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not find bucket from KB: {e}")
            return None
    
    def get_data_source_id(self) -> Optional[str]:
        """Get the data source ID for the Knowledge Base."""
        try:
            response = self.bedrock_agent_client.list_data_sources(
                knowledgeBaseId=self.kb_id
            )
            
            data_sources = response.get('dataSourceSummaries', [])
            if data_sources:
                # Return the first active data source
                for ds in data_sources:
                    if ds.get('status') == 'ACTIVE':
                        logger.info(f"Found data source: {ds['name']} (ID: {ds['dataSourceId']})")
                        return ds['dataSourceId']
                # If no active, return first one
                if data_sources:
                    return data_sources[0]['dataSourceId']
            
            logger.error("No data sources found for Knowledge Base")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get data source ID: {e}")
            return None
    
    def clone_or_update_repo(self, repo_url: str, target_dir: Path) -> bool:
        """Clone or update a Git repository."""
        try:
            if target_dir.exists():
                logger.info(f"Updating existing repository: {target_dir.name}")
                repo = Repo(target_dir)
                repo.remotes.origin.pull()
                logger.info(f"✅ Repository updated: {target_dir.name}")
            else:
                logger.info(f"Cloning repository: {repo_url}")
                Repo.clone_from(repo_url, target_dir, depth=1)
                logger.info(f"✅ Repository cloned: {target_dir.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clone/update repository {repo_url}: {e}")
            return False
    
    def is_document_file(self, file_path: Path) -> bool:
        """Check if a file should be uploaded."""
        doc_extensions = {'.md', '.txt', '.rst', '.html', '.htm', '.json'}
        skip_patterns = {
            '.git', '__pycache__', '.DS_Store', 'node_modules',
            '.gitignore', 'LICENSE', 'CHANGELOG.md', 'package.json'
        }
        
        if file_path.suffix.lower() not in doc_extensions:
            return False
        
        if any(pattern in str(file_path) for pattern in skip_patterns):
            return False
        
        # Skip very large files
        try:
            if file_path.stat().st_size > 10 * 1024 * 1024:  # 10MB
                return False
        except:
            return False
        
        return True
    
    def get_content_type(self, file_path: Path) -> str:
        """Get content type for file."""
        content_types = {
            '.md': 'text/markdown',
            '.txt': 'text/plain',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.json': 'application/json',
        }
        return content_types.get(file_path.suffix.lower(), 'text/plain') or 'text/plain'
    
    def upload_directory_to_s3(self, local_dir: Path, s3_prefix: str) -> int:
        """Upload directory to S3 and return count of uploaded files."""
        uploaded_count = 0
        total_files = 0
        
        # Count files first
        for file_path in local_dir.rglob('*'):
            if file_path.is_file() and self.is_document_file(file_path):
                total_files += 1
        
        logger.info(f"Found {total_files} document files to upload")
        
        # Upload files
        for file_path in local_dir.rglob('*'):
            if file_path.is_file() and self.is_document_file(file_path):
                relative_path = file_path.relative_to(local_dir)
                s3_key = f"{s3_prefix}/{relative_path}".replace('\\', '/')
                
                try:
                    content_type = self.get_content_type(file_path)
                    self.s3_client.upload_file(
                        str(file_path),
                        self.bucket_name,
                        s3_key,
                        ExtraArgs={'ContentType': content_type}
                    )
                    uploaded_count += 1
                    if uploaded_count % 50 == 0:
                        logger.info(f"Uploaded {uploaded_count}/{total_files} files...")
                        
                except Exception as e:
                    logger.error(f"Failed to upload {file_path}: {e}")
        
        logger.info(f"✅ Upload completed: {uploaded_count}/{total_files} files")
        return uploaded_count
    
    def update_adobe_documentation(self) -> bool:
        """Update all Adobe documentation from GitHub repositories."""
        logger.info("📚 Updating Adobe documentation from Experience League...")
        logger.info("=" * 80)
        
        # Experience League GitHub repositories
        repos = {
            "adobe-analytics": {
                "url": "https://github.com/AdobeDocs/analytics.en.git",
                "s3_prefix": "adobe-docs/adobe-analytics"
            },
            "customer-journey-analytics": {
                "url": "https://github.com/AdobeDocs/customer-journey-analytics-learn.en.git",
                "s3_prefix": "adobe-docs/customer-journey-analytics"
            },
            "analytics-apis": {
                "url": "https://github.com/AdobeDocs/analytics-2.0-apis.git",
                "s3_prefix": "adobe-docs/analytics-apis"
            },
            "experience-platform": {
                "url": "https://github.com/AdobeDocs/experience-platform.en.git",
                "s3_prefix": "adobe-docs/experience-platform"
            }
        }
        
        total_uploaded = 0
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                for repo_name, repo_info in repos.items():
                    logger.info(f"\n📦 Processing {repo_name}...")
                    repo_dir = temp_path / repo_name
                    
                    # Clone or update repository
                    if not self.clone_or_update_repo(repo_info["url"], repo_dir):
                        logger.warning(f"⚠️  Skipping {repo_name} due to clone error")
                        continue
                    
                    # Upload to S3
                    uploaded = self.upload_directory_to_s3(repo_dir, repo_info["s3_prefix"])
                    total_uploaded += uploaded
                    
                    logger.info(f"✅ {repo_name}: {uploaded} files uploaded")
                
                logger.info(f"\n📊 Total files uploaded: {total_uploaded}")
                return total_uploaded > 0
                
        except Exception as e:
            logger.error(f"Failed to update documentation: {e}")
            return False
    
    def start_sync_job(self, data_source_id: str) -> Optional[str]:
        """Start a sync job for the data source."""
        try:
            logger.info("🔄 Starting Knowledge Base sync job...")
            
            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=data_source_id,
                description=f"Sync job started at {datetime.now().isoformat()}"
            )
            
            job_id = response['ingestionJob']['ingestionJobId']
            logger.info(f"✅ Sync job started: {job_id}")
            logger.info(f"   Status: {response['ingestionJob']['status']}")
            
            return job_id
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConflictException':
                logger.warning("⚠️  A sync job is already in progress")
                return None
            else:
                logger.error(f"Failed to start sync job: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to start sync job: {e}")
            return None
    
    def monitor_ingestion_job(self, data_source_id: str, job_id: str, max_wait_minutes: int = 60):
        """Monitor ingestion job progress."""
        logger.info(f"⏳ Monitoring ingestion job: {job_id}")
        logger.info(f"   Max wait time: {max_wait_minutes} minutes")
        logger.info("=" * 80)
        
        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60
        
        while True:
            try:
                response = self.bedrock_agent_client.get_ingestion_job(
                    knowledgeBaseId=self.kb_id,
                    dataSourceId=data_source_id,
                    ingestionJobId=job_id
                )
                
                job = response['ingestionJob']
                status = job['status']
                elapsed = int(time.time() - start_time)
                
                logger.info(f"[{elapsed}s] Status: {status}")
                
                if 'statistics' in job:
                    stats = job['statistics']
                    logger.info(f"   Documents Scanned: {stats.get('numberOfDocumentsScanned', 0)}")
                    logger.info(f"   New Documents: {stats.get('numberOfDocumentsIndexed', 0)}")
                    logger.info(f"   Modified Documents: {stats.get('numberOfModifiedDocumentsIndexed', 0)}")
                    logger.info(f"   Failed: {stats.get('numberOfDocumentsFailed', 0)}")
                
                if status == 'COMPLETE':
                    logger.info("✅ Ingestion job completed successfully!")
                    return True
                elif status == 'FAILED':
                    logger.error("❌ Ingestion job failed!")
                    if 'failureReasons' in job:
                        for reason in job['failureReasons']:
                            logger.error(f"   Reason: {reason}")
                    return False
                elif elapsed > max_wait_seconds:
                    logger.warning(f"⏰ Max wait time ({max_wait_minutes} min) reached. Job still running.")
                    logger.info("   You can check status later using:")
                    logger.info(f"   python scripts/check_ingestion_status.py --kb-id {self.kb_id} --data-source-id {data_source_id} --job-id {job_id}")
                    return None
                
                time.sleep(30)  # Check every 30 seconds
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Monitoring stopped by user")
                return None
            except Exception as e:
                logger.error(f"Error checking job status: {e}")
                time.sleep(30)
    
    def run_update(self, monitor: bool = True) -> bool:
        """Run the complete update process."""
        logger.info("🚀 Starting Knowledge Base Update Process")
        logger.info("=" * 80)
        
        # Step 1: Validate Knowledge Base
        if not self.kb_id:
            logger.error("❌ Knowledge Base ID not configured in .env file")
            return False
        
        # Step 2: Get data source ID
        data_source_id = self.get_data_source_id()
        if not data_source_id:
            logger.error("❌ Could not find data source for Knowledge Base")
            return False
        
        # Step 3: Update documentation
        logger.info("\n📚 Step 1: Updating documentation from Experience League...")
        if not self.update_adobe_documentation():
            logger.error("❌ Failed to update documentation")
            return False
        
        # Step 4: Start sync job
        logger.info("\n🔄 Step 2: Starting Knowledge Base sync job...")
        job_id = self.start_sync_job(data_source_id)
        
        if not job_id:
            logger.warning("⚠️  Could not start new sync job (may already be running)")
            logger.info("   Check existing jobs in AWS console")
            return True  # Still consider it success if docs were uploaded
        
        # Step 5: Monitor job (optional)
        if monitor:
            logger.info("\n⏳ Step 3: Monitoring ingestion progress...")
            self.monitor_ingestion_job(data_source_id, job_id)
        else:
            logger.info(f"\n✅ Sync job started: {job_id}")
            logger.info("   Monitor progress in AWS console or run:")
            logger.info(f"   python scripts/check_ingestion_status.py --kb-id {self.kb_id} --data-source-id {data_source_id} --job-id {job_id} --monitor")
        
        logger.info("\n" + "=" * 80)
        logger.info("🎉 Knowledge Base update process completed!")
        logger.info(f"📋 Knowledge Base ID: {self.kb_id}")
        if job_id:
            logger.info(f"📋 Sync Job ID: {job_id}")
        
        return True


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Update Knowledge Base with latest Experience League articles'
    )
    parser.add_argument(
        '--no-monitor',
        action='store_true',
        help='Do not monitor ingestion job (start and exit)'
    )
    parser.add_argument(
        '--max-wait',
        type=int,
        default=60,
        help='Maximum wait time for ingestion in minutes (default: 60)'
    )
    
    args = parser.parse_args()
    
    try:
        updater = KnowledgeBaseUpdater()
        success = updater.run_update(monitor=not args.no_monitor)
        
        if success:
            print("\n✅ Knowledge Base update completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Knowledge Base update failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n❌ Update interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

