#!/usr/bin/env python3
"""
Check Knowledge Base Ingestion Status
"""

import boto3
import time
import sys
from datetime import datetime

def check_ingestion_status(kb_id, data_source_id, job_id=None):
    """Check the status of ingestion jobs for a data source."""
    
    bedrock_agent = boto3.client('bedrock-agent')
    
    try:
        # Get data source details
        data_source = bedrock_agent.get_data_source(
            knowledgeBaseId=kb_id,
            dataSourceId=data_source_id
        )
        
        print(f"📊 Data Source: {data_source['dataSource']['name']}")
        print(f"📊 Status: {data_source['dataSource']['status']}")
        print(f"📊 Updated: {data_source['dataSource']['updatedAt']}")
        print()
        
        # List ingestion jobs
        response = bedrock_agent.list_ingestion_jobs(
            knowledgeBaseId=kb_id,
            dataSourceId=data_source_id,
            maxResults=10
        )
        
        if not response['ingestionJobSummaries']:
            print("❌ No ingestion jobs found")
            return
        
        print("🔄 Ingestion Jobs:")
        print("=" * 80)
        
        for job in response['ingestionJobSummaries']:
            job_id = job['ingestionJobId']
            status = job['status']
            started_at = job['startedAt']
            
            print(f"📋 Job ID: {job_id}")
            print(f"📋 Status: {status}")
            print(f"📋 Started: {started_at}")
            
            if 'statistics' in job:
                stats = job['statistics']
                print(f"📋 Documents Scanned: {stats.get('numberOfDocumentsScanned', 0)}")
                print(f"📋 New Documents Indexed: {stats.get('numberOfDocumentsIndexed', 0)}")
                print(f"📋 Modified Documents: {stats.get('numberOfModifiedDocumentsIndexed', 0)}")
                print(f"📋 Documents Failed: {stats.get('numberOfDocumentsFailed', 0)}")
                print(f"📋 Documents Deleted: {stats.get('numberOfDocumentsDeleted', 0)}")
            
            print(f"📋 Last Updated: {job['updatedAt']}")
            print("-" * 80)
            
            # Get detailed job info if job_id is specified
            if job_id and job['ingestionJobId'] == job_id:
                try:
                    job_details = bedrock_agent.get_ingestion_job(
                        knowledgeBaseId=kb_id,
                        dataSourceId=data_source_id,
                        ingestionJobId=job_id
                    )
                    
                    print(f"🔍 Detailed Job Information:")
                    print(f"   Status: {job_details['ingestionJob']['status']}")
                    print(f"   Started: {job_details['ingestionJob']['startedAt']}")
                    if 'endedAt' in job_details['ingestionJob']:
                        print(f"   Ended: {job_details['ingestionJob']['endedAt']}")
                    
                    if 'failureReasons' in job_details['ingestionJob']:
                        print(f"   Failure Reasons: {job_details['ingestionJob']['failureReasons']}")
                    
                except Exception as e:
                    print(f"   Error getting job details: {e}")
        
        return response['ingestionJobSummaries']
        
    except Exception as e:
        print(f"❌ Error checking ingestion status: {e}")
        return None

def monitor_ingestion(kb_id, data_source_id, job_id, check_interval=60):
    """Monitor ingestion job progress."""
    
    print(f"🔄 Monitoring ingestion job: {job_id}")
    print(f"⏰ Check interval: {check_interval} seconds")
    print("=" * 80)
    
    while True:
        try:
            jobs = check_ingestion_status(kb_id, data_source_id, job_id)
            
            if jobs:
                job = next((j for j in jobs if j['ingestionJobId'] == job_id), None)
                if job:
                    status = job['status']
                    print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Status: {status}")
                    
                    if status in ['COMPLETE', 'FAILED']:
                        print(f"✅ Ingestion job {status.lower()}!")
                        break
                    elif status == 'IN_PROGRESS':
                        print("⏳ Job still in progress...")
                    else:
                        print(f"ℹ️  Job status: {status}")
            
            print(f"\n⏰ Waiting {check_interval} seconds before next check...")
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
            break
        except Exception as e:
            print(f"❌ Error during monitoring: {e}")
            break

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check Knowledge Base ingestion status')
    parser.add_argument('--kb-id', required=True, help='Knowledge Base ID')
    parser.add_argument('--data-source-id', required=True, help='Data Source ID')
    parser.add_argument('--job-id', help='Specific Job ID to monitor')
    parser.add_argument('--monitor', action='store_true', help='Monitor job progress')
    parser.add_argument('--interval', type=int, default=60, help='Check interval in seconds')
    
    args = parser.parse_args()
    
    if args.monitor and args.job_id:
        monitor_ingestion(args.kb_id, args.data_source_id, args.job_id, args.interval)
    else:
        check_ingestion_status(args.kb_id, args.data_source_id, args.job_id)

if __name__ == "__main__":
    main()
