#!/usr/bin/env python3
"""
Comprehensive OpenSearch Service cleanup analysis.
Checks for any remaining OpenSearch resources across all regions.
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import json
from datetime import datetime

def get_all_regions():
    """Get all available AWS regions."""
    try:
        ec2_client = boto3.client('ec2', region_name='us-east-1')
        regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
        return regions
    except Exception as e:
        print(f"❌ Error getting regions: {e}")
        # Fallback to common regions
        return ['us-east-1', 'us-west-2', 'eu-west-1', 'eu-north-1', 'ap-southeast-1']

def check_opensearch_domains(region):
    """Check for OpenSearch domains in a specific region."""
    try:
        opensearch_client = boto3.client('opensearch', region_name=region)
        
        # List all domains
        response = opensearch_client.list_domain_names()
        domains = response.get('DomainNames', [])
        
        if domains:
            print(f"🔍 Region {region}: Found {len(domains)} OpenSearch domains")
            for domain in domains:
                domain_name = domain['DomainName']
                try:
                    # Get domain details
                    domain_info = opensearch_client.describe_domain(DomainName=domain_name)
                    domain_status = domain_info['DomainStatus']
                    
                    print(f"   📊 Domain: {domain_name}")
                    print(f"      - Status: {domain_status['Processing']}")
                    print(f"      - Created: {domain_status.get('Created', 'Unknown')}")
                    print(f"      - Deleted: {domain_status.get('Deleted', False)}")
                    print(f"      - Endpoint: {domain_status.get('Endpoint', 'N/A')}")
                    
                    # Check if domain is being deleted
                    if domain_status.get('Processing') == 'Deleting':
                        print(f"      ⏳ Status: DELETING (in progress)")
                    elif domain_status.get('Deleted'):
                        print(f"      ✅ Status: DELETED")
                    else:
                        print(f"      ⚠️  Status: ACTIVE (not deleted)")
                        
                except ClientError as e:
                    print(f"      ❌ Error getting domain details: {e}")
        else:
            print(f"✅ Region {region}: No OpenSearch domains found")
            
        return len(domains)
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'UnauthorizedOperation':
            print(f"⚠️  Region {region}: No permissions to check OpenSearch")
        else:
            print(f"❌ Region {region}: Error checking OpenSearch - {e}")
        return 0
    except Exception as e:
        print(f"❌ Region {region}: Unexpected error - {e}")
        return 0

def check_opensearch_serverless_collections(region):
    """Check for OpenSearch Serverless collections in a specific region."""
    try:
        opensearch_client = boto3.client('opensearchserverless', region_name=region)
        
        # List collections
        response = opensearch_client.list_collections()
        collections = response.get('collectionSummaries', [])
        
        if collections:
            print(f"🔍 Region {region}: Found {len(collections)} OpenSearch Serverless collections")
            for collection in collections:
                collection_name = collection['name']
                collection_id = collection['id']
                collection_status = collection['status']
                
                print(f"   📊 Collection: {collection_name}")
                print(f"      - ID: {collection_id}")
                print(f"      - Status: {collection_status}")
                print(f"      - Type: {collection.get('type', 'Unknown')}")
                
                if collection_status == 'DELETING':
                    print(f"      ⏳ Status: DELETING (in progress)")
                elif collection_status == 'DELETED':
                    print(f"      ✅ Status: DELETED")
                else:
                    print(f"      ⚠️  Status: ACTIVE (not deleted)")
        else:
            print(f"✅ Region {region}: No OpenSearch Serverless collections found")
            
        return len(collections)
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'UnauthorizedOperation':
            print(f"⚠️  Region {region}: No permissions to check OpenSearch Serverless")
        else:
            print(f"❌ Region {region}: Error checking OpenSearch Serverless - {e}")
        return 0
    except Exception as e:
        print(f"❌ Region {region}: Unexpected error - {e}")
        return 0

def check_opensearch_serverless_vpc_endpoints(region):
    """Check for OpenSearch Serverless VPC endpoints in a specific region."""
    try:
        opensearch_client = boto3.client('opensearchserverless', region_name=region)
        
        # List VPC endpoints
        response = opensearch_client.list_vpc_endpoints()
        vpc_endpoints = response.get('vpcEndpointSummaries', [])
        
        if vpc_endpoints:
            print(f"🔍 Region {region}: Found {len(vpc_endpoints)} OpenSearch Serverless VPC endpoints")
            for endpoint in vpc_endpoints:
                endpoint_name = endpoint['name']
                endpoint_id = endpoint['id']
                endpoint_status = endpoint['status']
                
                print(f"   📊 VPC Endpoint: {endpoint_name}")
                print(f"      - ID: {endpoint_id}")
                print(f"      - Status: {endpoint_status}")
                
                if endpoint_status == 'DELETING':
                    print(f"      ⏳ Status: DELETING (in progress)")
                elif endpoint_status == 'DELETED':
                    print(f"      ✅ Status: DELETED")
                else:
                    print(f"      ⚠️  Status: ACTIVE (not deleted)")
        else:
            print(f"✅ Region {region}: No OpenSearch Serverless VPC endpoints found")
            
        return len(vpc_endpoints)
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'UnauthorizedOperation':
            print(f"⚠️  Region {region}: No permissions to check OpenSearch Serverless VPC endpoints")
        else:
            print(f"❌ Region {region}: Error checking OpenSearch Serverless VPC endpoints - {e}")
        return 0
    except Exception as e:
        print(f"❌ Region {region}: Unexpected error - {e}")
        return 0

def check_cloudformation_stacks(region):
    """Check for CloudFormation stacks that might contain OpenSearch resources."""
    try:
        cf_client = boto3.client('cloudformation', region_name=region)
        
        # List all stacks
        response = cf_client.list_stacks()
        stacks = response.get('StackSummaries', [])
        
        opensearch_stacks = []
        for stack in stacks:
            stack_name = stack['StackName']
            stack_status = stack['StackStatus']
            
            # Skip deleted stacks
            if 'DELETE' in stack_status:
                continue
                
            try:
                # Get stack details
                stack_details = cf_client.describe_stacks(StackName=stack_name)
                stack_resources = cf_client.list_stack_resources(StackName=stack_name)
                
                # Check if stack contains OpenSearch resources
                has_opensearch = False
                for resource in stack_resources.get('StackResourceSummaries', []):
                    resource_type = resource['ResourceType']
                    if 'OpenSearch' in resource_type or 'Elasticsearch' in resource_type:
                        has_opensearch = True
                        break
                
                if has_opensearch:
                    opensearch_stacks.append({
                        'name': stack_name,
                        'status': stack_status,
                        'created': stack.get('CreationTime', 'Unknown')
                    })
                    
            except ClientError:
                # Skip stacks we can't access
                continue
        
        if opensearch_stacks:
            print(f"🔍 Region {region}: Found {len(opensearch_stacks)} CloudFormation stacks with OpenSearch resources")
            for stack in opensearch_stacks:
                print(f"   📊 Stack: {stack['name']}")
                print(f"      - Status: {stack['status']}")
                print(f"      - Created: {stack['created']}")
        else:
            print(f"✅ Region {region}: No CloudFormation stacks with OpenSearch resources found")
            
        return len(opensearch_stacks)
        
    except ClientError as e:
        print(f"❌ Region {region}: Error checking CloudFormation - {e}")
        return 0
    except Exception as e:
        print(f"❌ Region {region}: Unexpected error - {e}")
        return 0

def check_costs():
    """Check for recent OpenSearch costs."""
    try:
        ce_client = boto3.client('ce', region_name='us-east-1')
        
        # Get costs for the last 7 days
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now().replace(day=1)).strftime('%Y-%m-%d')  # First day of current month
        
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='MONTHLY',
            Metrics=['BlendedCost'],
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }
            ]
        )
        
        opensearch_costs = []
        for result in response.get('ResultsByTime', []):
            for group in result.get('Groups', []):
                service = group['Keys'][0]
                cost = float(group['Metrics']['BlendedCost']['Amount'])
                
                if 'OpenSearch' in service or 'Elasticsearch' in service:
                    opensearch_costs.append({
                        'service': service,
                        'cost': cost
                    })
        
        if opensearch_costs:
            print(f"💰 OpenSearch Costs (Current Month):")
            total_cost = 0
            for cost_info in opensearch_costs:
                print(f"   - {cost_info['service']}: ${cost_info['cost']:.2f}")
                total_cost += cost_info['cost']
            print(f"   Total: ${total_cost:.2f}")
        else:
            print("✅ No OpenSearch costs found for current month")
            
        return opensearch_costs
        
    except ClientError as e:
        print(f"❌ Error checking costs: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error checking costs: {e}")
        return []

def main():
    """Main analysis function."""
    print("🔍 OpenSearch Service Cleanup Analysis")
    print("=" * 60)
    print(f"Analysis started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Test AWS credentials
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()
        print(f"✅ AWS Identity: {identity.get('Arn', 'Unknown')}")
        print()
    except NoCredentialsError:
        print("❌ No AWS credentials found. Please configure your credentials.")
        return 1
    except Exception as e:
        print(f"❌ Error with AWS credentials: {e}")
        return 1
    
    # Get all regions
    regions = get_all_regions()
    print(f"🌍 Checking {len(regions)} AWS regions...")
    print()
    
    total_domains = 0
    total_collections = 0
    total_vpc_endpoints = 0
    total_stacks = 0
    
    # Check each region
    for region in regions:
        print(f"🔍 Checking region: {region}")
        print("-" * 40)
        
        # Check OpenSearch domains
        domains = check_opensearch_domains(region)
        total_domains += domains
        
        # Check OpenSearch Serverless collections
        collections = check_opensearch_serverless_collections(region)
        total_collections += collections
        
        # Check OpenSearch Serverless VPC endpoints
        vpc_endpoints = check_opensearch_serverless_vpc_endpoints(region)
        total_vpc_endpoints += vpc_endpoints
        
        # Check CloudFormation stacks
        stacks = check_cloudformation_stacks(region)
        total_stacks += stacks
        
        print()
    
    # Check costs
    print("💰 Cost Analysis")
    print("-" * 40)
    costs = check_costs()
    print()
    
    # Summary
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Total OpenSearch domains: {total_domains}")
    print(f"Total OpenSearch Serverless collections: {total_collections}")
    print(f"Total OpenSearch Serverless VPC endpoints: {total_vpc_endpoints}")
    print(f"Total CloudFormation stacks with OpenSearch: {total_stacks}")
    print(f"OpenSearch costs this month: ${sum(c['cost'] for c in costs):.2f}")
    print()
    
    if total_domains == 0 and total_collections == 0 and total_vpc_endpoints == 0 and total_stacks == 0:
        print("🎉 SUCCESS: No OpenSearch resources found!")
        print("✅ Your OpenSearch cleanup is complete.")
        return 0
    else:
        print("⚠️  WARNING: OpenSearch resources still exist!")
        print("🔧 You may need to delete these resources manually.")
        return 1

if __name__ == "__main__":
    exit(main())
