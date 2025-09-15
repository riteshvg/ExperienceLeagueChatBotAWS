#!/usr/bin/env python3
"""
Integrate AEP with Existing Knowledge Base

This script integrates Adobe Experience Platform documentation with your existing
knowledge-base-experienceleagechatbot knowledge base by:
1. Uploading AEP docs to S3
2. Adding AEP as a new data source to existing KB
3. Starting ingestion job
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AEPExistingKBIntegration:
    """Integrates AEP with existing knowledge base."""
    
    def __init__(self):
        """Initialize the AEP integration."""
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
            
            # Validate required settings
            if not self.settings.bedrock_knowledge_base_id:
                raise ValueError("BEDROCK_KNOWLEDGE_BASE_ID not found in settings")
            if not self.settings.aws_s3_bucket:
                raise ValueError("AWS_S3_BUCKET not found in settings")
                
            self.logger.info(f"Using existing KB: {self.settings.bedrock_knowledge_base_id}")
            self.logger.info(f"Using S3 bucket: {self.settings.aws_s3_bucket}")
            
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
            
            # Test Bedrock Agent access
            bedrock_agent_client = boto3.client('bedrock-agent', region_name=self.settings.bedrock_region)
            try:
                # Check if our KB exists
                response = bedrock_agent_client.get_knowledge_base(
                    knowledgeBaseId=self.settings.bedrock_knowledge_base_id
                )
                kb_name = response['knowledgeBase']['name']
                self.logger.info(f"✅ Existing Knowledge Base found: {kb_name}")
            except ClientError as e:
                self.logger.error(f"❌ Knowledge Base access failed: {e}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ AWS validation failed: {e}")
            return False
    
    def integrate_aep_with_existing_kb(self) -> bool:
        """Integrate AEP with existing knowledge base."""
        self.logger.info("🚀 Integrating Adobe Experience Platform with existing Knowledge Base")
        self.logger.info("=" * 80)
        
        # Step 1: Validate AWS setup
        if not self.validate_aws_setup():
            self.logger.error("❌ AWS setup validation failed. Please check your configuration.")
            return False
        
        # Step 2: Upload AEP documentation
        self.logger.info("📚 Step 1: Uploading AEP documentation...")
        if not self.run_script(
            "scripts/upload_aep_docs.py",
            "Uploading Adobe Experience Platform documentation"
        ):
            self.logger.error("❌ AEP document upload failed")
            return False
        
        # Step 3: Add AEP data source to existing KB
        self.logger.info("🤖 Step 2: Adding AEP data source to existing Knowledge Base...")
        if not self.run_script(
            "scripts/add_aep_to_existing_kb.py",
            "Adding AEP data source to existing Knowledge Base"
        ):
            self.logger.error("❌ AEP data source addition failed")
            return False
        
        # Step 4: Wait for ingestion to complete
        self.logger.info("⏳ Step 3: AEP documents are being ingested...")
        self.logger.info("This may take 10-30 minutes. You can check progress in the AWS console.")
        self.logger.info("Ingestion job is running in the background.")
        
        # Step 5: Integration complete
        self.logger.info("✅ Step 4: AEP integration completed!")
        self.logger.info("=" * 80)
        self.logger.info("🎉 Adobe Experience Platform Integration Complete!")
        self.logger.info("")
        self.logger.info("📚 Your existing Knowledge Base now includes:")
        self.logger.info("  • Adobe Analytics (existing)")
        self.logger.info("  • Customer Journey Analytics (existing)")
        self.logger.info("  • Adobe Experience Platform (newly added)")
        self.logger.info("")
        self.logger.info("🔧 Benefits of this approach:")
        self.logger.info("  • No new infrastructure needed")
        self.logger.info("  • Uses your existing OpenSearch Serverless setup")
        self.logger.info("  • Single Knowledge Base for all queries")
        self.logger.info("  • Better query performance (no multiple KB calls)")
        self.logger.info("  • Cost-effective (no duplicate resources)")
        self.logger.info("")
        self.logger.info("🧪 Test AEP queries once ingestion completes:")
        self.logger.info("  • 'How do I create a schema in Adobe Experience Platform?'")
        self.logger.info("  • 'What are datasets and how do I use them in AEP?'")
        self.logger.info("  • 'How do I set up data ingestion in AEP?'")
        self.logger.info("  • 'What is XDM and how do I use it?'")
        
        return True

def main():
    """Main function."""
    try:
        integration = AEPExistingKBIntegration()
        success = integration.integrate_aep_with_existing_kb()
        
        if success:
            print("\n🎉 AEP Integration with Existing Knowledge Base Completed Successfully!")
            print("\nYour chatbot now supports:")
            print("• Adobe Analytics")
            print("• Customer Journey Analytics") 
            print("• Adobe Experience Platform")
            print("\nAll using your existing infrastructure - no new costs!")
            sys.exit(0)
        else:
            print("\n❌ AEP Integration Failed!")
            print("Please check the logs above for error details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n❌ Integration interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
