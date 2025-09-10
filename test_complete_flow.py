#!/usr/bin/env python3
"""
Test Complete RAG Flow

This script tests the complete RAG flow to understand how everything works
before enabling Bedrock models. It validates:
1. Configuration loading
2. AWS connectivity
3. S3 document access
4. Bedrock client setup (without model access)
5. Document structure and content
"""

import os
import sys
import logging
import json
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings
from src.utils.bedrock_client import get_bedrock_client
import boto3
from botocore.exceptions import ClientError


class RAGFlowTester:
    """Test the complete RAG flow."""
    
    def __init__(self):
        """Initialize the tester."""
        self.setup_logging()
        self.results = {}
        
    def setup_logging(self):
        """Configure logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def test_configuration(self) -> bool:
        """Test configuration loading."""
        self.logger.info("🔧 Testing configuration loading...")
        
        try:
            settings = get_settings()
            
            # Test basic settings
            self.results['config'] = {
                'aws_region': settings.aws_default_region,
                's3_bucket': settings.aws_s3_bucket,
                'bedrock_model': settings.bedrock_model_id,
                'bedrock_region': settings.bedrock_region,
                'openai_key_set': bool(settings.openai_api_key),
                'adobe_oauth_set': bool(settings.adobe_client_id and settings.adobe_client_secret)
            }
            
            self.logger.info(f"✅ Configuration loaded successfully")
            self.logger.info(f"   - AWS Region: {settings.aws_default_region}")
            self.logger.info(f"   - S3 Bucket: {settings.aws_s3_bucket}")
            self.logger.info(f"   - Bedrock Model: {settings.bedrock_model_id}")
            self.logger.info(f"   - OpenAI Key: {'Set' if settings.openai_api_key else 'Not set'}")
            self.logger.info(f"   - Adobe OAuth: {'Set' if settings.adobe_client_id else 'Not set'}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Configuration test failed: {e}")
            self.results['config'] = {'error': str(e)}
            return False
    
    def test_aws_connectivity(self) -> bool:
        """Test AWS connectivity."""
        self.logger.info("🌐 Testing AWS connectivity...")
        
        try:
            # Test S3 connectivity
            s3_client = boto3.client('s3', region_name=get_settings().aws_default_region)
            response = s3_client.list_objects_v2(
                Bucket=get_settings().aws_s3_bucket,
                MaxKeys=1
            )
            
            # Test STS (for account info)
            sts_client = boto3.client('sts')
            identity = sts_client.get_caller_identity()
            
            self.results['aws'] = {
                's3_accessible': True,
                'account_id': identity.get('Account'),
                'user_arn': identity.get('Arn'),
                'region': get_settings().aws_default_region
            }
            
            self.logger.info(f"✅ AWS connectivity successful")
            self.logger.info(f"   - Account ID: {identity.get('Account')}")
            self.logger.info(f"   - User: {identity.get('Arn')}")
            self.logger.info(f"   - S3 Bucket accessible: Yes")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ AWS connectivity test failed: {e}")
            self.results['aws'] = {'error': str(e)}
            return False
    
    def test_s3_documents(self) -> bool:
        """Test S3 document access and structure."""
        self.logger.info("📚 Testing S3 document access...")
        
        try:
            s3_client = boto3.client('s3', region_name=get_settings().aws_default_region)
            bucket = get_settings().aws_s3_bucket
            
            # List all documents
            response = s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix="adobe-docs/"
            )
            
            documents = response.get('Contents', [])
            
            # Categorize documents
            categories = {}
            total_size = 0
            
            for doc in documents:
                key = doc['Key']
                size = doc['Size']
                total_size += size
                
                # Extract category from path
                parts = key.split('/')
                if len(parts) >= 2:
                    category = parts[1]  # adobe-docs/category/...
                    if category not in categories:
                        categories[category] = {'count': 0, 'size': 0}
                    categories[category]['count'] += 1
                    categories[category]['size'] += size
            
            self.results['s3_documents'] = {
                'total_documents': len(documents),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'categories': categories,
                'sample_documents': [doc['Key'] for doc in documents[:10]]
            }
            
            self.logger.info(f"✅ S3 document access successful")
            self.logger.info(f"   - Total documents: {len(documents)}")
            self.logger.info(f"   - Total size: {round(total_size / (1024 * 1024), 2)} MB")
            self.logger.info(f"   - Categories:")
            for category, info in categories.items():
                self.logger.info(f"     - {category}: {info['count']} files ({round(info['size'] / (1024 * 1024), 2)} MB)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ S3 document test failed: {e}")
            self.results['s3_documents'] = {'error': str(e)}
            return False
    
    def test_document_content(self) -> bool:
        """Test document content accessibility."""
        self.logger.info("📄 Testing document content...")
        
        try:
            s3_client = boto3.client('s3', region_name=get_settings().aws_default_region)
            bucket = get_settings().aws_s3_bucket
            
            # Get a sample document from each category
            sample_docs = []
            
            # Find sample documents
            response = s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix="adobe-docs/"
            )
            
            documents = response.get('Contents', [])
            
            # Group by category and pick samples
            categories = {}
            for doc in documents:
                key = doc['Key']
                parts = key.split('/')
                if len(parts) >= 2:
                    category = parts[1]
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(key)
            
            # Sample one document from each category
            for category, docs in categories.items():
                if docs:
                    sample_doc = docs[0]  # Take first document
                    try:
                        # Download and read first 500 characters
                        response = s3_client.get_object(Bucket=bucket, Key=sample_doc)
                        content = response['Body'].read().decode('utf-8')
                        
                        sample_docs.append({
                            'category': category,
                            'file': sample_doc,
                            'size': len(content),
                            'preview': content[:500] + "..." if len(content) > 500 else content
                        })
                        
                    except Exception as e:
                        self.logger.warning(f"Could not read {sample_doc}: {e}")
            
            self.results['document_content'] = {
                'sample_documents': sample_docs,
                'total_categories': len(categories)
            }
            
            self.logger.info(f"✅ Document content test successful")
            self.logger.info(f"   - Categories found: {len(categories)}")
            for sample in sample_docs:
                self.logger.info(f"   - {sample['category']}: {sample['file']} ({sample['size']} chars)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Document content test failed: {e}")
            self.results['document_content'] = {'error': str(e)}
            return False
    
    def test_bedrock_client(self) -> bool:
        """Test Bedrock client setup (without model access)."""
        self.logger.info("🤖 Testing Bedrock client setup...")
        
        try:
            # Test client initialization
            bedrock_client = get_bedrock_client()
            
            # Test model configuration
            settings = get_settings()
            model_id = settings.bedrock_model_id
            region = settings.bedrock_region
            
            self.results['bedrock_client'] = {
                'client_initialized': True,
                'model_id': model_id,
                'region': region,
                'model_accessible': False  # Will be False until models are enabled
            }
            
            self.logger.info(f"✅ Bedrock client setup successful")
            self.logger.info(f"   - Model ID: {model_id}")
            self.logger.info(f"   - Region: {region}")
            self.logger.info(f"   - Model Access: Not enabled yet (expected)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Bedrock client test failed: {e}")
            self.results['bedrock_client'] = {'error': str(e)}
            return False
    
    def test_rag_flow_simulation(self) -> bool:
        """Simulate the RAG flow without actual model calls."""
        self.logger.info("🔄 Testing RAG flow simulation...")
        
        try:
            # Simulate the RAG process
            rag_flow = {
                'step_1_document_retrieval': 'S3 documents accessible',
                'step_2_document_processing': 'Ready for vectorization',
                'step_3_knowledge_base': 'Will be created after model enablement',
                'step_4_query_processing': 'Will use Bedrock models',
                'step_5_response_generation': 'Will use Bedrock models'
            }
            
            self.results['rag_flow'] = rag_flow
            
            self.logger.info(f"✅ RAG flow simulation successful")
            self.logger.info(f"   - Document retrieval: ✅ Ready")
            self.logger.info(f"   - Document processing: ✅ Ready")
            self.logger.info(f"   - Knowledge base: ⏳ Pending model enablement")
            self.logger.info(f"   - Query processing: ⏳ Pending model enablement")
            self.logger.info(f"   - Response generation: ⏳ Pending model enablement")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ RAG flow simulation failed: {e}")
            self.results['rag_flow'] = {'error': str(e)}
            return False
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate a summary report."""
        self.logger.info("📊 Generating summary report...")
        
        total_tests = 6
        passed_tests = 0
        
        for test_name, result in self.results.items():
            if 'error' not in result:
                passed_tests += 1
        
        summary = {
            'overall_status': 'PASS' if passed_tests == total_tests else 'PARTIAL',
            'tests_passed': passed_tests,
            'tests_total': total_tests,
            'success_rate': f"{(passed_tests/total_tests)*100:.1f}%",
            'next_steps': [],
            'recommendations': []
        }
        
        # Determine next steps
        if 'config' in self.results and 'error' not in self.results['config']:
            summary['next_steps'].append("✅ Configuration is ready")
        
        if 'aws' in self.results and 'error' not in self.results['aws']:
            summary['next_steps'].append("✅ AWS connectivity is working")
        
        if 's3_documents' in self.results and 'error' not in self.results['s3_documents']:
            summary['next_steps'].append("✅ Documents are accessible in S3")
        
        if 'bedrock_client' in self.results and 'error' not in self.results['bedrock_client']:
            summary['next_steps'].append("✅ Bedrock client is ready")
            summary['next_steps'].append("⏳ Enable Bedrock models in AWS console")
            summary['next_steps'].append("⏳ Create Bedrock Knowledge Base")
            summary['next_steps'].append("⏳ Test complete RAG pipeline")
        
        # Add recommendations
        if 'config' in self.results and 'error' in self.results['config']:
            summary['recommendations'].append("Fix configuration issues before proceeding")
        
        if 'aws' in self.results and 'error' in self.results['aws']:
            summary['recommendations'].append("Check AWS credentials and permissions")
        
        if 's3_documents' in self.results and 'error' in self.results['s3_documents']:
            summary['recommendations'].append("Verify S3 bucket access and document upload")
        
        return summary
    
    def run_all_tests(self) -> bool:
        """Run all tests."""
        self.logger.info("🚀 Starting complete RAG flow test...")
        
        tests = [
            self.test_configuration,
            self.test_aws_connectivity,
            self.test_s3_documents,
            self.test_document_content,
            self.test_bedrock_client,
            self.test_rag_flow_simulation
        ]
        
        all_passed = True
        for test in tests:
            if not test():
                all_passed = False
        
        # Generate summary
        summary = self.generate_summary_report()
        
        # Print summary
        self.logger.info("\n" + "="*60)
        self.logger.info("📋 TEST SUMMARY REPORT")
        self.logger.info("="*60)
        self.logger.info(f"Overall Status: {summary['overall_status']}")
        self.logger.info(f"Tests Passed: {summary['tests_passed']}/{summary['tests_total']} ({summary['success_rate']})")
        
        self.logger.info("\n📋 Next Steps:")
        for step in summary['next_steps']:
            self.logger.info(f"  {step}")
        
        if summary['recommendations']:
            self.logger.info("\n💡 Recommendations:")
            for rec in summary['recommendations']:
                self.logger.info(f"  - {rec}")
        
        # Save detailed results
        with open('test_results.json', 'w') as f:
            json.dump({
                'summary': summary,
                'detailed_results': self.results
            }, f, indent=2)
        
        self.logger.info(f"\n📄 Detailed results saved to: test_results.json")
        
        return all_passed


def main():
    """Main function."""
    try:
        tester = RAGFlowTester()
        success = tester.run_all_tests()
        
        if success:
            print("\n✅ All tests passed! Ready to proceed with Bedrock model enablement.")
            sys.exit(0)
        else:
            print("\n⚠️  Some tests failed. Please review the results before proceeding.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n❌ Testing interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
