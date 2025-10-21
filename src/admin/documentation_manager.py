"""
Documentation Manager for Admin Panel

This module manages documentation updates, monitors freshness,
and triggers automatic updates when documentation is stale.
"""

import os
import sys
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import boto3
from botocore.exceptions import ClientError

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


class DocumentationManager:
    """Manages documentation updates and freshness monitoring."""
    
    # Documentation sources configuration
    DOC_SOURCES = {
        "adobe-experience-platform": {
            "repo_url": "https://github.com/AdobeDocs/experience-platform.en.git",
            "repo_path": ".cache/repos/adobe-experience-platform",
            "s3_prefix": "adobe-docs/experience-platform",
            "update_frequency_days": 7,  # Weekly updates
            "display_name": "Adobe Experience Platform",
            "data_source_id": "U2ZFV61LQS"  # AEP data source
        },
        "adobe-analytics": {
            "repo_url": "https://github.com/AdobeDocs/analytics.en.git",
            "repo_path": ".cache/repos/adobe-analytics",
            "s3_prefix": "adobe-docs/adobe-analytics",
            "update_frequency_days": 30,  # Monthly updates
            "display_name": "Adobe Analytics",
            "data_source_id": None  # Part of main data source
        },
        "customer-journey-analytics": {
            "repo_url": "https://github.com/AdobeDocs/customer-journey-analytics-learn.en.git",
            "repo_path": ".cache/repos/customer-journey-analytics",
            "s3_prefix": "adobe-docs/customer-journey-analytics",
            "update_frequency_days": 30,  # Monthly updates
            "display_name": "Customer Journey Analytics",
            "data_source_id": None  # Part of main data source
        },
        "analytics-apis": {
            "repo_url": "https://github.com/AdobeDocs/analytics-2.0-apis.git",
            "repo_path": ".cache/repos/analytics-apis",
            "s3_prefix": "adobe-docs/analytics-apis",
            "update_frequency_days": 30,  # Monthly updates
            "display_name": "Analytics 2.0 APIs",
            "data_source_id": None  # Part of main data source
        }
    }
    
    def __init__(self, kb_id: str, region: str = "us-east-1"):
        """
        Initialize Documentation Manager.
        
        Args:
            kb_id: Knowledge Base ID
            region: AWS region
        """
        self.kb_id = kb_id
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=region)
        
        # Load settings
        from config.settings import get_settings
        settings = get_settings()
        self.bucket_name = settings.aws_s3_bucket
        
        # Create cache directory
        self.cache_dir = project_root / ".cache" / "repos"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_repo_last_commit_date(self, repo_path: Path) -> Optional[datetime]:
        """
        Get the last commit date from a Git repository.
        
        Args:
            repo_path: Path to the Git repository
            
        Returns:
            Last commit date or None if error
        """
        try:
            if not repo_path.exists():
                return None
            
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%ci'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.stdout:
                commit_date_str = result.stdout.strip()
                # Parse format: 2025-10-17 16:25:27 -0700
                commit_date = datetime.strptime(commit_date_str[:19], '%Y-%m-%d %H:%M:%S')
                return commit_date
            
            return None
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting commit date for {repo_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting commit date: {e}")
            return None
    
    def get_s3_last_upload_date(self, s3_prefix: str) -> Optional[datetime]:
        """
        Get the last upload date from S3.
        
        Args:
            s3_prefix: S3 prefix to check
            
        Returns:
            Last upload date or None if error
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=s3_prefix,
                MaxKeys=1000
            )
            
            if 'Contents' not in response:
                return None
            
            # Get the most recent file
            latest_file = max(response['Contents'], key=lambda x: x['LastModified'])
            return latest_file['LastModified'].replace(tzinfo=None)
            
        except Exception as e:
            logger.error(f"Error getting S3 upload date for {s3_prefix}: {e}")
            return None
    
    def check_documentation_freshness(self) -> Dict[str, Dict]:
        """
        Check freshness of all documentation sources.
        
        Returns:
            Dictionary with freshness status for each source
        """
        freshness_status = {}
        
        for source_key, config in self.DOC_SOURCES.items():
            try:
                # Get repo path
                repo_path_str = str(config['repo_path'])
                repo_path = self.cache_dir / repo_path_str.split('/')[-1]
                
                # Get last commit date from GitHub
                github_date = self.get_repo_last_commit_date(repo_path)
                
                # Get last upload date from S3
                s3_prefix = str(config['s3_prefix'])
                s3_date = self.get_s3_last_upload_date(s3_prefix)
                
                # Calculate days behind
                days_behind = None
                if github_date and s3_date:
                    days_behind = (github_date - s3_date).days
                
                # Determine if update is needed
                needs_update = False
                update_freq = int(config['update_frequency_days'])
                if days_behind is not None:
                    needs_update = days_behind > update_freq
                elif s3_date:
                    # If we can't get GitHub date, check if S3 is old
                    days_since_s3 = (datetime.now() - s3_date).days
                    needs_update = days_since_s3 > update_freq
                
                freshness_status[source_key] = {
                    'display_name': str(config['display_name']),
                    'github_last_commit': github_date.isoformat() if github_date else None,
                    's3_last_upload': s3_date.isoformat() if s3_date else None,
                    'days_behind': days_behind,
                    'needs_update': needs_update,
                    'update_frequency_days': int(config['update_frequency_days']),
                    'status': 'current' if not needs_update else 'stale'
                }
                
            except Exception as e:
                logger.error(f"Error checking freshness for {source_key}: {e}")
                freshness_status[source_key] = {
                    'display_name': str(config['display_name']),
                    'error': str(e),
                    'status': 'error'
                }
        
        return freshness_status
    
    def trigger_documentation_update(self, source_key: str) -> Tuple[bool, str]:
        """
        Trigger documentation update for a specific source.
        
        Args:
            source_key: Key of the documentation source to update
            
        Returns:
            Tuple of (success, message)
        """
        if source_key not in self.DOC_SOURCES:
            return False, f"Unknown source: {source_key}"
        
        config = self.DOC_SOURCES[source_key]
        
        try:
            # Import the upload script
            from scripts.upload_docs_to_s3 import DocumentUploader
            
            uploader = DocumentUploader()
            
            # Update specific source
            if source_key == "adobe-experience-platform":
                # Use the AEP upload script
                from scripts.upload_aep_docs import AEPDocumentUploader
                aep_uploader = AEPDocumentUploader()
                success = aep_uploader.upload_documents()
            elif source_key == "adobe-analytics":
                success = uploader.upload_adobe_docs()
            elif source_key == "customer-journey-analytics":
                success = uploader.upload_cja_docs()
            elif source_key == "analytics-apis":
                success = uploader.upload_adobe_docs()  # Analytics APIs are part of Adobe docs
            else:
                return False, f"Update not implemented for {source_key}"
            
            if success:
                # Trigger ingestion if needed
                ingestion_job_id = self.trigger_ingestion_job(source_key)
                
                return True, f"Update started successfully. Ingestion job: {ingestion_job_id}"
            else:
                return False, "Update failed"
                
        except Exception as e:
            logger.error(f"Error triggering update for {source_key}: {e}")
            return False, f"Error: {str(e)}"
    
    def trigger_ingestion_job(self, source_key: str) -> Optional[str]:
        """
        Trigger ingestion job for a specific source.
        
        Args:
            source_key: Key of the documentation source
            
        Returns:
            Ingestion job ID or None
        """
        try:
            config = self.DOC_SOURCES[source_key]
            data_source_id = config.get('data_source_id')
            
            if not data_source_id:
                # Use main data source for analytics docs
                data_source_id = "U2ZFV61LQS"
            
            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=data_source_id
            )
            
            job_id = response['ingestionJob']['ingestionJobId']
            logger.info(f"Started ingestion job: {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Error triggering ingestion job: {e}")
            return None
    
    def get_ingestion_job_status(self, job_id: str, data_source_id: str) -> Dict:
        """
        Get status of an ingestion job.
        
        Args:
            job_id: Ingestion job ID
            data_source_id: Data source ID
            
        Returns:
            Job status dictionary
        """
        try:
            response = self.bedrock_agent_client.get_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=data_source_id,
                ingestionJobId=job_id
            )
            
            job = response['ingestionJob']
            
            return {
                'job_id': job_id,
                'status': job['status'],
                'statistics': job['statistics'],
                'started_at': job['startedAt'],
                'updated_at': job['updatedAt']
            }
            
        except Exception as e:
            logger.error(f"Error getting ingestion job status: {e}")
            return {'error': str(e)}
    
    def auto_update_stale_docs(self) -> Dict[str, Dict]:
        """
        Automatically update all stale documentation sources.
        
        Returns:
            Dictionary with update results for each source
        """
        freshness_status = self.check_documentation_freshness()
        update_results = {}
        
        for source_key, status in freshness_status.items():
            if status.get('needs_update'):
                logger.info(f"Auto-updating {source_key}...")
                success, message = self.trigger_documentation_update(source_key)
                
                update_results[source_key] = {
                    'success': success,
                    'message': message,
                    'display_name': status['display_name']
                }
            else:
                update_results[source_key] = {
                    'success': None,
                    'message': 'No update needed',
                    'display_name': status['display_name']
                }
        
        return update_results
    
    def get_documentation_stats(self) -> Dict:
        """
        Get overall documentation statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            # Get all S3 objects
            total_files = 0
            total_size = 0
            
            for config in self.DOC_SOURCES.values():
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=config['s3_prefix']
                )
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        total_files += 1
                        total_size += obj['Size']
            
            return {
                'total_files': total_files,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'knowledge_base_id': self.kb_id,
                'bucket_name': self.bucket_name,
                'region': self.region
            }
            
        except Exception as e:
            logger.error(f"Error getting documentation stats: {e}")
            return {'error': str(e)}

