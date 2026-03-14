#!/usr/bin/env python3
"""
Monitor Knowledge Base Update Progress

This script monitors:
1. Update script process status
2. S3 upload progress
3. Ingestion job status
4. Overall completion status
"""

import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional
import boto3
from botocore.exceptions import ClientError

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import Settings


class KBUpdateMonitor:
    """Monitors Knowledge Base update progress."""
    
    def __init__(self):
        """Initialize monitor."""
        self.settings = Settings()
        self.kb_id = self.settings.bedrock_knowledge_base_id
        self.bucket_name = 'experienceleaguechatbot'
        self.region = self.settings.aws_default_region
        
        # Initialize AWS clients
        self.bedrock_agent = boto3.client('bedrock-agent', region_name=self.region)
        self.s3_client = boto3.client('s3', region_name=self.region)
        
        self.start_time = datetime.now()
        
    def check_update_script(self) -> Dict:
        """Check if update script is running."""
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True
            )
            
            is_running = 'update_knowledge_base_latest' in result.stdout
            process_info = {}
            
            if is_running:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'update_knowledge_base_latest' in line and 'grep' not in line:
                        parts = line.split()
                        if len(parts) >= 10:
                            process_info = {
                                'pid': parts[1],
                                'cpu': parts[2],
                                'mem': parts[3],
                                'time': parts[9]
                            }
                        break
            
            return {
                'running': is_running,
                'process_info': process_info
            }
        except Exception as e:
            return {
                'running': False,
                'error': str(e)
            }
    
    def get_data_source_info(self) -> Dict:
        """Get data source information."""
        try:
            response = self.bedrock_agent.list_data_sources(
                knowledgeBaseId=self.kb_id
            )
            
            data_sources = []
            for ds in response.get('dataSourceSummaries', []):
                ds_id = ds['dataSourceId']
                
                # Get latest ingestion job
                try:
                    jobs_response = self.bedrock_agent.list_ingestion_jobs(
                        knowledgeBaseId=self.kb_id,
                        dataSourceId=ds_id,
                        maxResults=1
                    )
                    
                    latest_job = None
                    if jobs_response.get('ingestionJobSummaries'):
                        latest_job = jobs_response['ingestionJobSummaries'][0]
                except:
                    latest_job = None
                
                data_sources.append({
                    'name': ds['name'],
                    'id': ds_id,
                    'status': ds['status'],
                    'updated_at': ds.get('updatedAt'),
                    'latest_job': latest_job
                })
            
            return {
                'success': True,
                'data_sources': data_sources
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_s3_uploads(self) -> Dict:
        """Check S3 upload status."""
        try:
            # Count files in adobe-docs prefix
            prefixes = [
                'adobe-docs/adobe-analytics/',
                'adobe-docs/customer-journey-analytics/',
                'adobe-docs/analytics-apis/',
                'adobe-docs/experience-platform/'
            ]
            
            total_files = 0
            total_size = 0
            recent_files = []
            
            for prefix in prefixes:
                try:
                    paginator = self.s3_client.get_paginator('list_objects_v2')
                    pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
                    
                    for page in pages:
                        if 'Contents' in page:
                            for obj in page['Contents']:
                                total_files += 1
                                total_size += obj['Size']
                                
                                # Check if file was modified in last hour
                                if obj['LastModified'] > datetime.now(obj['LastModified'].tzinfo) - timedelta(hours=1):
                                    recent_files.append({
                                        'key': obj['Key'],
                                        'size': obj['Size'],
                                        'modified': obj['LastModified']
                                    })
                except ClientError:
                    # Prefix might not exist yet
                    continue
            
            return {
                'success': True,
                'total_files': total_files,
                'total_size_mb': total_size / (1024 * 1024),
                'recent_files_count': len(recent_files),
                'recent_files': recent_files[:5]  # Show first 5
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_active_ingestion_jobs(self) -> list:
        """Get active ingestion jobs."""
        active_jobs = []
        
        try:
            ds_info = self.get_data_source_info()
            if not ds_info.get('success'):
                return active_jobs
            
            for ds in ds_info['data_sources']:
                ds_id = ds['id']
                
                try:
                    jobs_response = self.bedrock_agent.list_ingestion_jobs(
                        knowledgeBaseId=self.kb_id,
                        dataSourceId=ds_id,
                        maxResults=10
                    )
                    
                    for job in jobs_response.get('ingestionJobSummaries', []):
                        if job['status'] in ['IN_PROGRESS', 'STARTING']:
                            # Get detailed job info
                            try:
                                job_detail = self.bedrock_agent.get_ingestion_job(
                                    knowledgeBaseId=self.kb_id,
                                    dataSourceId=ds_id,
                                    ingestionJobId=job['ingestionJobId']
                                )
                                active_jobs.append({
                                    'data_source': ds['name'],
                                    'job_id': job['ingestionJobId'],
                                    'status': job['status'],
                                    'started_at': job['startedAt'],
                                    'details': job_detail.get('ingestionJob', {})
                                })
                            except:
                                active_jobs.append({
                                    'data_source': ds['name'],
                                    'job_id': job['ingestionJobId'],
                                    'status': job['status'],
                                    'started_at': job['startedAt']
                                })
                except Exception as e:
                    continue
        except Exception as e:
            pass
        
        return active_jobs
    
    def display_status(self):
        """Display current status."""
        elapsed = datetime.now() - self.start_time
        elapsed_str = str(elapsed).split('.')[0]  # Remove microseconds
        
        print("\n" + "=" * 80)
        print(f"📊 Knowledge Base Update Monitor")
        print(f"⏰ Elapsed Time: {elapsed_str}")
        print("=" * 80)
        
        # Check update script
        print("\n🔄 Update Script Status:")
        script_status = self.check_update_script()
        if script_status['running']:
            print("   ✅ Script is running")
            if script_status.get('process_info'):
                info = script_status['process_info']
                print(f"   📋 PID: {info.get('pid', 'N/A')}")
                print(f"   💻 CPU: {info.get('cpu', 'N/A')}%")
                print(f"   🧠 Memory: {info.get('mem', 'N/A')}%")
                print(f"   ⏱️  Runtime: {info.get('time', 'N/A')}")
        else:
            print("   ⚠️  Script is not running")
            if script_status.get('error'):
                print(f"   ❌ Error: {script_status['error']}")
        
        # Check S3 uploads
        print("\n📦 S3 Upload Status:")
        s3_status = self.check_s3_uploads()
        if s3_status.get('success'):
            print(f"   📄 Total Files: {s3_status['total_files']:,}")
            print(f"   💾 Total Size: {s3_status['total_size_mb']:.2f} MB")
            print(f"   🆕 Recent Files (last hour): {s3_status['recent_files_count']}")
            if s3_status['recent_files']:
                print("   📝 Recent uploads:")
                for f in s3_status['recent_files'][:3]:
                    size_kb = f['size'] / 1024
                    print(f"      - {f['key'].split('/')[-1]} ({size_kb:.1f} KB)")
        else:
            print(f"   ❌ Error: {s3_status.get('error', 'Unknown')}")
        
        # Check data sources
        print("\n📚 Knowledge Base Data Sources:")
        ds_info = self.get_data_source_info()
        if ds_info.get('success'):
            for ds in ds_info['data_sources']:
                print(f"   📦 {ds['name']}")
                print(f"      Status: {ds['status']}")
                
                if ds.get('latest_job'):
                    job = ds['latest_job']
                    status = job['status']
                    started = job.get('startedAt', 'N/A')
                    
                    # Calculate time since start
                    if isinstance(started, str):
                        try:
                            started_dt = datetime.fromisoformat(started.replace('Z', '+00:00'))
                            time_ago = datetime.now(started_dt.tzinfo) - started_dt
                            time_str = f"{int(time_ago.total_seconds()/60)} minutes ago"
                        except:
                            time_str = str(started)
                    else:
                        time_str = str(started)
                    
                    print(f"      Latest Job: {status} (started {time_str})")
                    
                    if 'statistics' in job:
                        stats = job['statistics']
                        print(f"      Documents: {stats.get('numberOfDocumentsScanned', 0)} scanned, "
                              f"{stats.get('numberOfDocumentsIndexed', 0)} indexed")
                else:
                    print(f"      No ingestion jobs found")
        else:
            print(f"   ❌ Error: {ds_info.get('error', 'Unknown')}")
        
        # Check active ingestion jobs
        print("\n🔄 Active Ingestion Jobs:")
        active_jobs = self.get_active_ingestion_jobs()
        if active_jobs:
            for job in active_jobs:
                print(f"   ✅ {job['data_source']}")
                print(f"      Job ID: {job['job_id']}")
                print(f"      Status: {job['status']}")
                
                if 'details' in job and 'statistics' in job['details']:
                    stats = job['details']['statistics']
                    print(f"      Progress: {stats.get('numberOfDocumentsScanned', 0)} scanned, "
                          f"{stats.get('numberOfDocumentsIndexed', 0)} indexed")
        else:
            print("   ℹ️  No active ingestion jobs")
        
        print("\n" + "=" * 80)
    
    def monitor(self, interval: int = 30, max_duration: Optional[int] = None):
        """Monitor update progress."""
        print("🚀 Starting Knowledge Base Update Monitor")
        print(f"⏱️  Check interval: {interval} seconds")
        if max_duration:
            print(f"⏰ Max duration: {max_duration} minutes")
        print("\nPress Ctrl+C to stop monitoring\n")
        
        start_time = datetime.now()
        
        try:
            while True:
                # Clear screen (optional, can be removed if you prefer)
                # print("\033[2J\033[H")  # ANSI escape codes
                
                self.display_status()
                
                # Check if max duration reached
                if max_duration:
                    elapsed_minutes = (datetime.now() - start_time).total_seconds() / 60
                    if elapsed_minutes >= max_duration:
                        print(f"\n⏰ Maximum duration ({max_duration} minutes) reached.")
                        break
                
                # Check completion conditions
                script_status = self.check_update_script()
                active_jobs = self.get_active_ingestion_jobs()
                
                # If script finished and no active jobs, check if we should wait
                if not script_status['running'] and not active_jobs:
                    print("\n✅ Update script has completed")
                    print("⏳ Waiting for ingestion jobs to start...")
                
                print(f"\n⏳ Next check in {interval} seconds... (Press Ctrl+C to stop)")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"\n❌ Monitoring error: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Monitor Knowledge Base update progress'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Check interval in seconds (default: 30)'
    )
    parser.add_argument(
        '--max-duration',
        type=int,
        help='Maximum monitoring duration in minutes'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Check status once and exit'
    )
    
    args = parser.parse_args()
    
    try:
        monitor = KBUpdateMonitor()
        
        if args.once:
            monitor.display_status()
        else:
            monitor.monitor(
                interval=args.interval,
                max_duration=args.max_duration
            )
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

