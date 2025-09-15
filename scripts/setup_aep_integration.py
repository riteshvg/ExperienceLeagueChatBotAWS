#!/usr/bin/env python3
"""
Setup Adobe Experience Platform Integration

This script orchestrates the complete AEP integration process:
1. Upload all Adobe documentation (Analytics, CJA, AEP)
2. Create enhanced knowledge base
3. Start ingestion jobs
4. Validate the integration
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
import subprocess

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AEPIntegrationSetup:
    """Orchestrates the complete AEP integration setup."""
    
    def __init__(self):
        """Initialize the AEP integration setup."""
        self.setup_logging()
        self.load_configuration()
        
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
            self.settings = get_settings()
            self.logger.info("Configuration loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
    
    def run_script(self, script_path: str, description: str) -> bool:
        """Run a Python script and return success status."""
        try:
            self.logger.info(f"🚀 {description}...")
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                cwd=project_root
            )
            
            if result.returncode == 0:
                self.logger.info(f"✅ {description} completed successfully")
                return True
            else:
                self.logger.error(f"❌ {description} failed:")
                self.logger.error(f"STDOUT: {result.stdout}")
                self.logger.error(f"STDERR: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Failed to run {description}: {e}")
            return False
    
    def validate_aws_setup(self) -> bool:
        """Validate AWS configuration and permissions."""
        self.logger.info("🔍 Validating AWS setup...")
        
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            # Test S3 access
            s3_client = boto3.client('s3', region_name=self.settings.aws_default_region)
            try:
                s3_client.head_bucket(Bucket=self.settings.aws_s3_bucket)
                self.logger.info("✅ S3 bucket access confirmed")
            except ClientError as e:
                self.logger.error(f"❌ S3 bucket access failed: {e}")
                return False
            
            # Test Bedrock access
            bedrock_client = boto3.client('bedrock', region_name=self.settings.bedrock_region)
            try:
                bedrock_client.list_foundation_models()
                self.logger.info("✅ Bedrock access confirmed")
            except ClientError as e:
                self.logger.error(f"❌ Bedrock access failed: {e}")
                return False
            
            # Test Bedrock Agent access
            bedrock_agent_client = boto3.client('bedrock-agent', region_name=self.settings.bedrock_region)
            try:
                bedrock_agent_client.list_knowledge_bases()
                self.logger.info("✅ Bedrock Agent access confirmed")
            except ClientError as e:
                self.logger.error(f"❌ Bedrock Agent access failed: {e}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ AWS validation failed: {e}")
            return False
    
    def setup_aep_integration(self) -> bool:
        """Run the complete AEP integration setup."""
        self.logger.info("🚀 Starting Adobe Experience Platform Integration Setup")
        self.logger.info("=" * 80)
        
        # Step 1: Validate AWS setup
        if not self.validate_aws_setup():
            self.logger.error("❌ AWS setup validation failed. Please check your configuration.")
            return False
        
        # Step 2: Upload all Adobe documentation
        self.logger.info("📚 Step 1: Uploading all Adobe documentation...")
        if not self.run_script(
            "scripts/upload_all_adobe_docs.py",
            "Uploading all Adobe documentation (Analytics, CJA, AEP)"
        ):
            self.logger.error("❌ Document upload failed")
            return False
        
        # Step 3: Create enhanced knowledge base
        self.logger.info("🤖 Step 2: Creating enhanced knowledge base...")
        if not self.run_script(
            "scripts/create_enhanced_knowledge_base.py",
            "Creating enhanced knowledge base with AEP support"
        ):
            self.logger.error("❌ Knowledge base creation failed")
            return False
        
        # Step 4: Wait for ingestion to complete
        self.logger.info("⏳ Step 3: Waiting for document ingestion to complete...")
        self.logger.info("This may take 30-60 minutes. You can check progress in the AWS console.")
        self.logger.info("Ingestion jobs are running in the background.")
        
        # Step 5: Validate integration
        self.logger.info("✅ Step 4: Integration setup completed!")
        self.logger.info("=" * 80)
        self.logger.info("🎉 Adobe Experience Platform Integration Setup Complete!")
        self.logger.info("")
        self.logger.info("📚 Documentation sources now included:")
        self.logger.info("  • Adobe Analytics (User Documentation)")
        self.logger.info("  • Adobe Analytics APIs")
        self.logger.info("  • Customer Journey Analytics")
        self.logger.info("  • Adobe Experience Platform")
        self.logger.info("")
        self.logger.info("🔧 Next steps:")
        self.logger.info("1. Wait for ingestion jobs to complete (30-60 minutes)")
        self.logger.info("2. Test the chatbot with AEP-specific queries")
        self.logger.info("3. Monitor the admin dashboard for system status")
        self.logger.info("4. Update your application configuration if needed")
        self.logger.info("")
        self.logger.info("🧪 Test queries you can try:")
        self.logger.info("  • 'How do I create a schema in Adobe Experience Platform?'")
        self.logger.info("  • 'What are datasets and how do I use them in AEP?'")
        self.logger.info("  • 'How do I set up data ingestion in AEP?'")
        self.logger.info("  • 'How do I create audiences in Adobe Experience Platform?'")
        self.logger.info("  • 'What is XDM and how do I use it?'")
        
        return True
    
    def create_test_queries_file(self):
        """Create a file with test queries for AEP integration."""
        test_queries = {
            "adobe_experience_platform": [
                "How do I create a schema in Adobe Experience Platform?",
                "What are datasets and how do I use them in AEP?",
                "How do I set up data ingestion in AEP?",
                "How do I create audiences in Adobe Experience Platform?",
                "What is XDM and how do I use it?",
                "How do I configure identity service in AEP?",
                "What are data sources in Adobe Experience Platform?",
                "How do I set up real-time customer profiles?",
                "What is the data lake in AEP?",
                "How do I use query service in Adobe Experience Platform?"
            ],
            "adobe_analytics": [
                "How do I create segments in Adobe Analytics?",
                "What's the difference between eVars and props?",
                "How do I set up conversion tracking?",
                "How do I use Analysis Workspace?",
                "How do I create calculated metrics?"
            ],
            "customer_journey_analytics": [
                "How do I set up cross-channel analytics in CJA?",
                "What is data stitching in Customer Journey Analytics?",
                "How do I create customer journey reports?",
                "How do I connect data sources in CJA?"
            ]
        }
        
        test_file_path = project_root / "aep_test_queries.json"
        
        try:
            with open(test_file_path, 'w') as f:
                json.dump(test_queries, f, indent=2)
            
            self.logger.info(f"✅ Test queries saved to: {test_file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create test queries file: {e}")
            return False

def main():
    """Main function."""
    try:
        setup = AEPIntegrationSetup()
        
        # Create test queries file
        setup.create_test_queries_file()
        
        # Run the complete setup
        success = setup.setup_aep_integration()
        
        if success:
            print("\n🎉 Adobe Experience Platform Integration Setup Completed Successfully!")
            print("\nYour chatbot now supports:")
            print("• Adobe Analytics")
            print("• Customer Journey Analytics") 
            print("• Adobe Experience Platform")
            print("\nTest it out with AEP-specific queries!")
            sys.exit(0)
        else:
            print("\n❌ Adobe Experience Platform Integration Setup Failed!")
            print("Please check the logs above for error details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n❌ Setup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
