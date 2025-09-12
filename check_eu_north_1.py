#!/usr/bin/env python3
"""
Check OpenSearch resources specifically in eu-north-1 region.
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime

def check_eu_north_1():
    """Check OpenSearch resources in eu-north-1 region."""
    region = 'eu-north-1'
    print(f"🔍 Checking OpenSearch resources in {region}")
    print("=" * 60)
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
    
    total_resources = 0
    
    # Check OpenSearch domains
    print("1️⃣ Checking OpenSearch Domains")
    print("-" * 40)
    try:
        opensearch_client = boto3.client('opensearch', region_name=region)
        response = opensearch_client.list_domain_names()
        domains = response.get('DomainNames', [])
        
        if domains:
            print(f"❌ Found {len(domains)} OpenSearch domains in {region}:")
            for domain in domains:
                domain_name = domain['DomainName']
                try:
                    domain_info = opensearch_client.describe_domain(DomainName=domain_name)
                    domain_status = domain_info['DomainStatus']
                    
                    print(f"   📊 Domain: {domain_name}")
                    print(f"      - Status: {domain_status['Processing']}")
                    print(f"      - Created: {domain_status.get('Created', 'Unknown')}")
                    print(f"      - Deleted: {domain_status.get('Deleted', False)}")
                    print(f"      - Endpoint: {domain_status.get('Endpoint', 'N/A')}")
                    print(f"      - Engine Version: {domain_status.get('EngineVersion', 'N/A')}")
                    print(f"      - Instance Type: {domain_status.get('ElasticsearchClusterConfig', {}).get('InstanceType', 'N/A')}")
                    print(f"      - Instance Count: {domain_status.get('ElasticsearchClusterConfig', {}).get('InstanceCount', 'N/A')}")
                    
                    # Check if domain is being deleted
                    if domain_status.get('Processing') == 'Deleting':
                        print(f"      ⏳ Status: DELETING (in progress)")
                    elif domain_status.get('Deleted'):
                        print(f"      ✅ Status: DELETED")
                    else:
                        print(f"      ⚠️  Status: ACTIVE (not deleted)")
                        total_resources += 1
                        
                except ClientError as e:
                    print(f"      ❌ Error getting domain details: {e}")
                    total_resources += 1
        else:
            print(f"✅ No OpenSearch domains found in {region}")
            
    except ClientError as e:
        if e.response['Error']['Code'] == 'UnauthorizedOperation':
            print(f"⚠️  No permissions to check OpenSearch domains in {region}")
        else:
            print(f"❌ Error checking OpenSearch domains in {region}: {e}")
    except Exception as e:
        print(f"❌ Unexpected error checking OpenSearch domains in {region}: {e}")
    
    print()
    
    # Check OpenSearch Serverless collections
    print("2️⃣ Checking OpenSearch Serverless Collections")
    print("-" * 40)
    try:
        opensearch_client = boto3.client('opensearchserverless', region_name=region)
        response = opensearch_client.list_collections()
        collections = response.get('collectionSummaries', [])
        
        if collections:
            print(f"❌ Found {len(collections)} OpenSearch Serverless collections in {region}:")
            for collection in collections:
                collection_name = collection['name']
                collection_id = collection['id']
                collection_status = collection['status']
                collection_type = collection.get('type', 'Unknown')
                
                print(f"   📊 Collection: {collection_name}")
                print(f"      - ID: {collection_id}")
                print(f"      - Status: {collection_status}")
                print(f"      - Type: {collection_type}")
                print(f"      - Created: {collection.get('createdDate', 'Unknown')}")
                
                if collection_status == 'DELETING':
                    print(f"      ⏳ Status: DELETING (in progress)")
                elif collection_status == 'DELETED':
                    print(f"      ✅ Status: DELETED")
                else:
                    print(f"      ⚠️  Status: ACTIVE (not deleted)")
                    total_resources += 1
        else:
            print(f"✅ No OpenSearch Serverless collections found in {region}")
            
    except ClientError as e:
        if e.response['Error']['Code'] == 'UnauthorizedOperation':
            print(f"⚠️  No permissions to check OpenSearch Serverless in {region}")
        else:
            print(f"❌ Error checking OpenSearch Serverless in {region}: {e}")
    except Exception as e:
        print(f"❌ Unexpected error checking OpenSearch Serverless in {region}: {e}")
    
    print()
    
    # Check OpenSearch Serverless VPC endpoints
    print("3️⃣ Checking OpenSearch Serverless VPC Endpoints")
    print("-" * 40)
    try:
        opensearch_client = boto3.client('opensearchserverless', region_name=region)
        response = opensearch_client.list_vpc_endpoints()
        vpc_endpoints = response.get('vpcEndpointSummaries', [])
        
        if vpc_endpoints:
            print(f"❌ Found {len(vpc_endpoints)} OpenSearch Serverless VPC endpoints in {region}:")
            for endpoint in vpc_endpoints:
                endpoint_name = endpoint['name']
                endpoint_id = endpoint['id']
                endpoint_status = endpoint['status']
                
                print(f"   📊 VPC Endpoint: {endpoint_name}")
                print(f"      - ID: {endpoint_id}")
                print(f"      - Status: {endpoint_status}")
                print(f"      - Created: {endpoint.get('createdDate', 'Unknown')}")
                
                if endpoint_status == 'DELETING':
                    print(f"      ⏳ Status: DELETING (in progress)")
                elif endpoint_status == 'DELETED':
                    print(f"      ✅ Status: DELETED")
                else:
                    print(f"      ⚠️  Status: ACTIVE (not deleted)")
                    total_resources += 1
        else:
            print(f"✅ No OpenSearch Serverless VPC endpoints found in {region}")
            
    except ClientError as e:
        if e.response['Error']['Code'] == 'UnauthorizedOperation':
            print(f"⚠️  No permissions to check OpenSearch Serverless VPC endpoints in {region}")
        else:
            print(f"❌ Error checking OpenSearch Serverless VPC endpoints in {region}: {e}")
    except Exception as e:
        print(f"❌ Unexpected error checking OpenSearch Serverless VPC endpoints in {region}: {e}")
    
    print()
    
    # Check CloudFormation stacks
    print("4️⃣ Checking CloudFormation Stacks")
    print("-" * 40)
    try:
        cf_client = boto3.client('cloudformation', region_name=region)
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
                # Get stack resources
                resources = cf_client.list_stack_resources(StackName=stack_name)
                
                # Check if stack contains OpenSearch resources
                has_opensearch = False
                for resource in resources.get('StackResourceSummaries', []):
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
            print(f"❌ Found {len(opensearch_stacks)} CloudFormation stacks with OpenSearch resources in {region}:")
            for stack in opensearch_stacks:
                print(f"   📊 Stack: {stack['name']}")
                print(f"      - Status: {stack['status']}")
                print(f"      - Created: {stack['created']}")
                total_resources += 1
        else:
            print(f"✅ No CloudFormation stacks with OpenSearch resources found in {region}")
            
    except ClientError as e:
        if e.response['Error']['Code'] == 'AccessDenied':
            print(f"⚠️  No permissions to check CloudFormation in {region}")
        else:
            print(f"❌ Error checking CloudFormation in {region}: {e}")
    except Exception as e:
        print(f"❌ Unexpected error checking CloudFormation in {region}: {e}")
    
    print()
    
    # Summary
    print("📊 SUMMARY FOR eu-north-1")
    print("=" * 60)
    print(f"Total OpenSearch resources found: {total_resources}")
    print()
    
    if total_resources == 0:
        print("🎉 SUCCESS: No OpenSearch resources found in eu-north-1!")
        print("✅ Your OpenSearch cleanup is complete for this region.")
        return 0
    else:
        print("⚠️  WARNING: OpenSearch resources still exist in eu-north-1!")
        print("🔧 You may need to delete these resources manually.")
        print("\nTo delete resources manually:")
        print("1. Go to AWS Console → OpenSearch Service")
        print("2. Select eu-north-1 region")
        print("3. Delete any remaining domains/collections")
        return 1

if __name__ == "__main__":
    exit(check_eu_north_1())
