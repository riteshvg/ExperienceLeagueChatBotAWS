#!/usr/bin/env python3
"""
Simple OpenSearch cleanup check for key regions.
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime

def check_region(region_name):
    """Check OpenSearch resources in a specific region."""
    print(f"🔍 Checking region: {region_name}")
    print("-" * 40)
    
    total_resources = 0
    
    # Check OpenSearch domains
    try:
        opensearch_client = boto3.client('opensearch', region_name=region_name)
        domains = opensearch_client.list_domain_names()
        
        if domains['DomainNames']:
            print(f"❌ Found {len(domains['DomainNames'])} OpenSearch domains:")
            for domain in domains['DomainNames']:
                domain_name = domain['DomainName']
                try:
                    domain_info = opensearch_client.describe_domain(DomainName=domain_name)
                    status = domain_info['DomainStatus']['Processing']
                    print(f"   - {domain_name} (Status: {status})")
                    total_resources += 1
                except ClientError as e:
                    print(f"   - {domain_name} (Error: {e})")
        else:
            print("✅ No OpenSearch domains found")
    except ClientError as e:
        print(f"⚠️  Cannot check OpenSearch domains: {e}")
    except Exception as e:
        print(f"❌ Error checking OpenSearch domains: {e}")
    
    # Check OpenSearch Serverless collections
    try:
        opensearch_client = boto3.client('opensearchserverless', region_name=region_name)
        collections = opensearch_client.list_collections()
        
        if collections['collectionSummaries']:
            print(f"❌ Found {len(collections['collectionSummaries'])} OpenSearch Serverless collections:")
            for collection in collections['collectionSummaries']:
                print(f"   - {collection['name']} (Status: {collection['status']})")
                total_resources += 1
        else:
            print("✅ No OpenSearch Serverless collections found")
    except ClientError as e:
        print(f"⚠️  Cannot check OpenSearch Serverless: {e}")
    except Exception as e:
        print(f"❌ Error checking OpenSearch Serverless: {e}")
    
    print()
    return total_resources

def check_costs():
    """Check OpenSearch costs."""
    try:
        ce_client = boto3.client('ce', region_name='us-east-1')
        
        # Get costs for current month
        from datetime import datetime
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        
        response = ce_client.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity='MONTHLY',
            Metrics=['BlendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )
        
        opensearch_costs = []
        for result in response.get('ResultsByTime', []):
            for group in result.get('Groups', []):
                service = group['Keys'][0]
                cost = float(group['Metrics']['BlendedCost']['Amount'])
                
                if 'OpenSearch' in service or 'Elasticsearch' in service:
                    opensearch_costs.append({'service': service, 'cost': cost})
        
        if opensearch_costs:
            print("💰 OpenSearch Costs (Current Month):")
            total_cost = 0
            for cost_info in opensearch_costs:
                print(f"   - {cost_info['service']}: ${cost_info['cost']:.2f}")
                total_cost += cost_info['cost']
            print(f"   Total: ${total_cost:.2f}")
            return total_cost
        else:
            print("✅ No OpenSearch costs found for current month")
            return 0
            
    except Exception as e:
        print(f"❌ Error checking costs: {e}")
        return 0

def main():
    """Main function."""
    print("🔍 OpenSearch Cleanup Analysis")
    print("=" * 50)
    print(f"Analysis started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test AWS credentials
    try:
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()
        print(f"✅ AWS Identity: {identity.get('Arn', 'Unknown')}")
        print()
    except Exception as e:
        print(f"❌ AWS credentials error: {e}")
        return 1
    
    # Check key regions
    regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'eu-north-1']
    total_resources = 0
    
    for region in regions:
        total_resources += check_region(region)
    
    # Check costs
    print("💰 Cost Analysis")
    print("-" * 40)
    total_cost = check_costs()
    print()
    
    # Summary
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"Total OpenSearch resources found: {total_resources}")
    print(f"OpenSearch costs this month: ${total_cost:.2f}")
    print()
    
    if total_resources == 0:
        print("🎉 SUCCESS: No OpenSearch resources found!")
        print("✅ Your OpenSearch cleanup is complete.")
        return 0
    else:
        print("⚠️  WARNING: OpenSearch resources still exist!")
        print("🔧 You may need to delete these resources manually.")
        return 1

if __name__ == "__main__":
    exit(main())
