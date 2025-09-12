#!/usr/bin/env python3
"""
Check CloudFormation stacks for OpenSearch resources.
"""

import boto3
from botocore.exceptions import ClientError

def check_cloudformation_stacks():
    """Check CloudFormation stacks for OpenSearch resources."""
    print("🔍 Checking CloudFormation Stacks for OpenSearch Resources")
    print("=" * 60)
    
    regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'eu-north-1']
    total_stacks = 0
    
    for region in regions:
        print(f"\n🌍 Region: {region}")
        print("-" * 40)
        
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
                    # Get stack resources
                    resources = cf_client.list_stack_resources(StackName=stack_name)
                    
                    # Check for OpenSearch resources
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
                        
                except ClientError as e:
                    # Skip stacks we can't access
                    continue
            
            if opensearch_stacks:
                print(f"❌ Found {len(opensearch_stacks)} stacks with OpenSearch resources:")
                for stack in opensearch_stacks:
                    print(f"   - {stack['name']} (Status: {stack['status']})")
                    print(f"     Created: {stack['created']}")
                total_stacks += len(opensearch_stacks)
            else:
                print("✅ No CloudFormation stacks with OpenSearch resources found")
                
        except ClientError as e:
            print(f"⚠️  Cannot check CloudFormation in {region}: {e}")
        except Exception as e:
            print(f"❌ Error checking CloudFormation in {region}: {e}")
    
    print(f"\n📊 SUMMARY")
    print("=" * 60)
    print(f"Total CloudFormation stacks with OpenSearch resources: {total_stacks}")
    
    if total_stacks == 0:
        print("🎉 SUCCESS: No CloudFormation stacks with OpenSearch resources found!")
        return 0
    else:
        print("⚠️  WARNING: CloudFormation stacks with OpenSearch resources found!")
        print("🔧 You may need to delete these stacks manually.")
        return 1

if __name__ == "__main__":
    exit(check_cloudformation_stacks())
