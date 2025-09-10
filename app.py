import streamlit as st
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Load environment variables
load_dotenv()

# Import configuration
from config.settings import Settings

# Import AWS utilities
from src.utils.aws_utils import get_s3_client, get_sts_client, get_bedrock_agent_client
from src.utils.bedrock_client import BedrockClient

# Basic app configuration
st.set_page_config(
    page_title="Adobe Experience League Chatbot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_configuration():
    """Load and validate configuration settings."""
    try:
        settings = Settings()
        return settings, None
    except Exception as e:
        return None, str(e)

def initialize_aws_clients(settings):
    """Initialize AWS clients and test connectivity."""
    try:
        # Initialize S3 client
        s3_client = get_s3_client(settings.aws_default_region)
        
        # Initialize STS client for identity verification
        sts_client = get_sts_client(settings.aws_default_region)
        
        # Initialize Bedrock client
        bedrock_client = BedrockClient(
            model_id=settings.bedrock_model_id,
            region=settings.bedrock_region
        )
        
        # Initialize Bedrock Agent Runtime client for Knowledge Base
        bedrock_agent_client = get_bedrock_agent_client(settings.bedrock_region)
        
        # Test AWS connectivity
        identity = sts_client.get_caller_identity()
        account_id = identity.get('Account', 'Unknown')
        user_arn = identity.get('Arn', 'Unknown')
        
        # Test S3 bucket access
        try:
            s3_client.head_bucket(Bucket=settings.aws_s3_bucket)
            s3_status = "✅ Accessible"
        except Exception as e:
            s3_status = f"❌ Error: {str(e)[:50]}..."
        
        return {
            's3_client': s3_client,
            'sts_client': sts_client,
            'bedrock_client': bedrock_client,
            'bedrock_agent_client': bedrock_agent_client,
            'account_id': account_id,
            'user_arn': user_arn,
            's3_status': s3_status
        }, None
        
    except Exception as e:
        return None, str(e)

def retrieve_documents_from_kb(query: str, knowledge_base_id: str, bedrock_agent_client, max_results: int = 3):
    """Retrieve relevant documents from Knowledge Base."""
    try:
        response = bedrock_agent_client.retrieve(
            knowledgeBaseId=knowledge_base_id,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': max_results
                }
            }
        )
        return response.get('retrievalResults', []), None
    except Exception as e:
        return [], str(e)

def generate_answer_from_kb(query: str, knowledge_base_id: str, model_id: str, bedrock_agent_client):
    """Generate answer using Knowledge Base."""
    try:
        response = bedrock_agent_client.retrieve_and_generate(
            input={
                'text': query
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': knowledge_base_id,
                    'modelArn': model_id
                }
            }
        )
        return response.get('output', {}).get('text', ''), None
    except Exception as e:
        return '', str(e)

def test_knowledge_base_connection(knowledge_base_id: str, bedrock_agent_client):
    """Test Knowledge Base connection with a simple query."""
    try:
        # Test with a simple query
        test_query = "What is Adobe Analytics?"
        documents, error = retrieve_documents_from_kb(test_query, knowledge_base_id, bedrock_agent_client, max_results=1)
        
        if error:
            return False, f"Retrieval error: {error}"
        
        if not documents:
            return False, "No documents retrieved"
        
        return True, f"Successfully retrieved {len(documents)} document(s)"
        
    except Exception as e:
        return False, str(e)

class SmartRouter:
    """Smart router for selecting appropriate Bedrock models based on query analysis."""
    
    def __init__(self):
        self.models = {
            "haiku": "us.anthropic.claude-3-haiku-20240307-v1:0",
            "sonnet": "us.anthropic.claude-3-7-sonnet-20250219-v1:0", 
            "opus": "us.anthropic.claude-3-opus-20240229-v1:0"
        }
        
        # Query complexity indicators
        self.simple_keywords = ["what", "define", "explain", "how to", "tutorial", "guide"]
        self.complex_keywords = ["analyze", "compare", "difference", "troubleshoot", "debug", "optimize", "implement"]
        self.creative_keywords = ["best", "recommend", "suggest", "trends", "future", "strategy", "design"]
        
        # Knowledge Base relevance thresholds
        self.high_relevance_threshold = 0.7
        self.medium_relevance_threshold = 0.3
    
    def analyze_query_complexity(self, query: str) -> str:
        """Analyze query complexity based on keywords and structure."""
        query_lower = query.lower()
        word_count = len(query.split())
        
        # Check for creative/open-ended queries
        if any(keyword in query_lower for keyword in self.creative_keywords):
            return "extremely_complex"
        
        # Check for analytical queries
        if any(keyword in query_lower for keyword in self.complex_keywords):
            return "complex"
        
        # Check query length and structure
        if word_count < 5:
            return "simple"
        elif word_count > 15:
            return "complex"
        elif "?" in query and word_count > 8:
            return "complex"
        else:
            return "simple"
    
    def check_kb_relevance(self, query: str, documents: list) -> float:
        """Check Knowledge Base relevance based on retrieved documents."""
        if not documents:
            return 0.0
        
        # Calculate average relevance score
        scores = [doc.get('score', 0) for doc in documents]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        return avg_score
    
    def select_model(self, query: str, documents: list = None) -> dict:
        """Select appropriate model based on query analysis."""
        complexity = self.analyze_query_complexity(query)
        relevance = self.check_kb_relevance(query, documents or [])
        
        # Model selection logic with fallback for unavailable models
        if relevance < self.medium_relevance_threshold:
            # Low KB relevance - prefer Opus, fallback to Sonnet
            selected_model = "opus"
            reasoning = f"Low KB relevance ({relevance:.2f}) - using Opus for general knowledge"
        elif complexity == "simple":
            # Simple queries - use fast, cost-effective model
            selected_model = "haiku"
            reasoning = f"Simple query - using Haiku for fast response"
        elif complexity == "complex":
            # Complex queries - use balanced model
            selected_model = "sonnet"
            reasoning = f"Complex query - using Sonnet for detailed analysis"
        else:  # extremely_complex
            # Extremely complex queries - prefer Opus, fallback to Sonnet
            selected_model = "opus"
            reasoning = f"Extremely complex query - using Opus for maximum capability"
        
        return {
            "model": selected_model,
            "model_id": self.models[selected_model],
            "complexity": complexity,
            "relevance": relevance,
            "reasoning": reasoning
        }
    
    def select_available_model(self, query: str, documents: list = None, available_models: list = None) -> dict:
        """Select appropriate model with fallback to available models."""
        if available_models is None:
            available_models = ["haiku", "sonnet"]  # Default available models
        
        # Get initial selection
        selection = self.select_model(query, documents)
        
        # Check if selected model is available, fallback if not
        if selection["model"] not in available_models:
            if "sonnet" in available_models:
                selection["model"] = "sonnet"
                selection["model_id"] = self.models["sonnet"]
                selection["reasoning"] += " (fallback to Sonnet - Opus not available)"
            elif "haiku" in available_models:
                selection["model"] = "haiku"
                selection["model_id"] = self.models["haiku"]
                selection["reasoning"] += " (fallback to Haiku - preferred model not available)"
        
        return selection
    
    def get_model_info(self, model_name: str) -> dict:
        """Get information about a specific model."""
        model_info = {
            "haiku": {
                "name": "Claude 3 Haiku",
                "description": "Fast, cost-effective for simple queries",
                "cost_per_1m_tokens": "$1.50",
                "use_cases": ["Definitions", "Simple how-to", "Quick answers"]
            },
            "sonnet": {
                "name": "Claude 3.7 Sonnet", 
                "description": "Balanced performance for complex queries",
                "cost_per_1m_tokens": "$18.00",
                "use_cases": ["Analysis", "Comparisons", "Detailed explanations"]
            },
            "opus": {
                "name": "Claude 3 Opus",
                "description": "Most capable for creative and complex tasks",
                "cost_per_1m_tokens": "$75.00", 
                "use_cases": ["Creative tasks", "Open-ended questions", "General knowledge"]
            }
        }
        return model_info.get(model_name, {})

def invoke_bedrock_model(model_id: str, query: str, bedrock_client, context: str = "") -> tuple:
    """Invoke Bedrock model with proper request format based on model type."""
    try:
        # Use the BedrockClient's generate_text method instead of direct invoke_model
        prompt = f"{context}\n\nQuery: {query}" if context else query
        
        # Create a temporary BedrockClient with the specific model_id
        from src.utils.bedrock_client import BedrockClient
        temp_client = BedrockClient(model_id=model_id, region=bedrock_client.region)
        
        # Generate text using the appropriate method
        answer = temp_client.generate_text(
            prompt=prompt,
            max_tokens=1000,
            temperature=0.7,
            top_p=0.9
        )
        
        return answer, None
            
    except Exception as e:
        # If the selected model fails, try fallback to Haiku
        if "AccessDeniedException" in str(e) or "don't have access" in str(e).lower():
            try:
                print(f"⚠️ Model {model_id} not accessible, falling back to Haiku...")
                fallback_client = BedrockClient(model_id="us.anthropic.claude-3-haiku-20240307-v1:0", region=bedrock_client.region)
                answer = fallback_client.generate_text(
                    prompt=prompt,
                    max_tokens=1000,
                    temperature=0.7,
                    top_p=0.9
                )
                return answer, None
            except Exception as fallback_error:
                return "", f"Primary model failed: {str(e)}. Fallback also failed: {str(fallback_error)}"
        else:
            return "", str(e)

def process_query_with_smart_routing(query: str, knowledge_base_id: str, smart_router, aws_clients) -> dict:
    """Process query using smart routing and return comprehensive results."""
    try:
        # Step 1: Retrieve documents from Knowledge Base
        documents, retrieval_error = retrieve_documents_from_kb(
            query, 
            knowledge_base_id, 
            aws_clients['bedrock_agent_client']
        )
        
        if retrieval_error:
            return {
                "success": False,
                "error": f"Retrieval error: {retrieval_error}",
                "documents": [],
                "routing_decision": None,
                "answer": "",
                "model_used": None
            }
        
        # Step 2: Smart routing - select appropriate model with fallback
        # Use available models (Haiku and Sonnet are confirmed working)
        available_models = ["haiku", "sonnet"]
        routing_decision = smart_router.select_available_model(query, documents, available_models)
        
        # Step 3: Prepare context from retrieved documents
        context = ""
        if documents:
            context_parts = []
            for i, doc in enumerate(documents[:3], 1):  # Use top 3 documents
                content = doc.get('content', {}).get('text', '')
                if content:
                    context_parts.append(f"Document {i}: {content[:500]}...")
            context = "\n\n".join(context_parts)
        
        # Step 4: Invoke selected model
        answer, generation_error = invoke_bedrock_model(
            routing_decision['model_id'],
            query,
            aws_clients['bedrock_client'],
            context
        )
        
        if generation_error:
            return {
                "success": False,
                "error": f"Generation error: {generation_error}",
                "documents": documents,
                "routing_decision": routing_decision,
                "answer": "",
                "model_used": routing_decision['model']
            }
        
        return {
            "success": True,
            "error": None,
            "documents": documents,
            "routing_decision": routing_decision,
            "answer": answer,
            "model_used": routing_decision['model']
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Processing error: {str(e)}",
            "documents": [],
            "routing_decision": None,
            "answer": "",
            "model_used": None
        }

def test_model_invocation(model_id: str, test_query: str, bedrock_client) -> tuple:
    """Test model invocation with a simple query."""
    try:
        answer, error = invoke_bedrock_model(model_id, test_query, bedrock_client, "")
        
        if error:
            return False, f"Model invocation error: {error}"
        
        if not answer or len(answer.strip()) < 10:
            return False, "Model returned empty or very short response"
        
        return True, f"Model responded successfully (length: {len(answer)} chars)"
        
    except Exception as e:
        return False, str(e)

def render_admin_page(settings, aws_clients, aws_error, kb_status, kb_error, smart_router, model_test_results):
    """Render the admin page with all technical details."""
    st.title("🔧 Admin Dashboard")
    st.markdown("**System Configuration, Status, and Analytics**")
    st.markdown("---")
    
    # Create tabs for different admin sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 System Status", 
        "⚙️ Configuration", 
        "🔗 AWS Details", 
        "🧠 Smart Router", 
        "📈 Analytics"
    ])
    
    with tab1:
        st.header("📊 System Status Overview")
        
        # Overall system status
        if not aws_error and kb_status and smart_router:
            st.success("🚀 **System Status: READY** - All components operational")
        elif not aws_error and smart_router:
            st.info("🔧 **System Status: PARTIAL** - Knowledge Base testing in progress")
        else:
            st.warning("⚠️ **System Status: SETUP** - System setup in progress")
        
        # Component status grid
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if aws_error:
                st.error("❌ **AWS**\nConnection Failed")
            elif aws_clients:
                st.success("✅ **AWS**\nConnected")
            else:
                st.warning("⚠️ **AWS**\nNot Initialized")
        
        with col2:
            if kb_error:
                st.error("❌ **Knowledge Base**\nError")
            elif kb_status:
                st.success("✅ **Knowledge Base**\nReady")
            else:
                st.info("ℹ️ **Knowledge Base**\nPending")
        
        with col3:
            if smart_router:
                st.success("✅ **Smart Router**\nInitialized")
            else:
                st.warning("⚠️ **Smart Router**\nNot Initialized")
        
        with col4:
            if model_test_results:
                tested_models = sum(1 for result in model_test_results.values() if result["success"])
                total_models = len(model_test_results)
                st.success(f"✅ **Models**\n{tested_models}/{total_models} Working")
            else:
                st.info("ℹ️ **Models**\nTesting Pending")
    
    with tab2:
        st.header("⚙️ Configuration Settings")
        
        if aws_error:
            st.error(f"❌ **Configuration Error:** {aws_error}")
        else:
            st.success("✅ **Configuration loaded successfully**")
            
            # Configuration details in a nice format
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🔧 Core Settings")
                st.write(f"**AWS Region:** `{settings.aws_default_region}`")
                st.write(f"**S3 Bucket:** `{settings.aws_s3_bucket}`")
                st.write(f"**Bedrock Model:** `{settings.bedrock_model_id}`")
                st.write(f"**Knowledge Base ID:** `{settings.bedrock_knowledge_base_id}`")
            
            with col2:
                st.subheader("🔑 Authentication")
                st.write(f"**AWS Access Key:** `{settings.aws_access_key_id[:8]}...`")
                st.write(f"**AWS Secret Key:** `{settings.aws_secret_access_key[:8]}...`")
                st.write(f"**Bedrock Region:** `{settings.bedrock_region}`")
                st.write(f"**Embedding Model:** `{settings.bedrock_embedding_model_id}`")
    
    with tab3:
        st.header("🔗 AWS Connection Details")
        
        if aws_error:
            st.error(f"❌ **AWS Error:** {aws_error}")
        elif aws_clients:
            st.success("✅ **AWS clients initialized successfully**")
            
            # AWS details in organized sections
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🏢 Account Information")
                st.write(f"**Account ID:** `{aws_clients['account_id']}`")
                st.write(f"**User ARN:** `{aws_clients['user_arn']}`")
                st.write(f"**Region:** `{settings.aws_default_region}`")
            
            with col2:
                st.subheader("🪣 S3 Status")
                st.write(f"**Bucket:** `{aws_clients['s3_status']}`")
                st.write("**Bedrock Client:** ✅ Initialized")
                st.write("**STS Client:** ✅ Initialized")
            
            # AWS Cost Information
            st.markdown("---")
            st.subheader("💰 AWS Cost Breakdown")
            
            # Cost information in expandable sections
            cost_col1, cost_col2, cost_col3 = st.columns(3)
            
            with cost_col1:
                with st.expander("🤖 **Bedrock Costs**", expanded=True):
                    st.write("**Claude 3 Haiku:**")
                    st.write("• Input: $0.25 per 1M tokens")
                    st.write("• Output: $1.25 per 1M tokens")
                    st.write("• **Best for:** Simple queries, high volume")
                    
                    st.write("**Claude 3 Sonnet:**")
                    st.write("• Input: $3.00 per 1M tokens")
                    st.write("• Output: $15.00 per 1M tokens")
                    st.write("• **Best for:** Complex analysis, balanced performance")
                    
                    st.write("**Claude 3 Opus:**")
                    st.write("• Input: $15.00 per 1M tokens")
                    st.write("• Output: $75.00 per 1M tokens")
                    st.write("• **Best for:** Creative tasks, maximum capability")
                    
                    st.write("**Titan Embeddings v2:**")
                    st.write("• Cost: $0.02 per 1M tokens")
                    st.write("• **Used for:** Document embeddings")
            
            with cost_col2:
                with st.expander("🪣 **S3 Storage Costs**", expanded=True):
                    st.write("**Standard Storage:**")
                    st.write("• First 50 TB: $0.023 per GB/month")
                    st.write("• Next 450 TB: $0.022 per GB/month")
                    st.write("• Over 500 TB: $0.021 per GB/month")
                    
                    st.write("**Standard-IA Storage:**")
                    st.write("• First 50 TB: $0.0125 per GB/month")
                    st.write("• **Used for:** Infrequently accessed docs")
                    
                    st.write("**Glacier Storage:**")
                    st.write("• $0.004 per GB/month")
                    st.write("• **Used for:** Long-term archival")
                    
                    st.write("**Data Transfer:**")
                    st.write("• Out to Internet: $0.09 per GB")
                    st.write("• **Note:** Bedrock access is free")
            
            with cost_col3:
                with st.expander("🧠 **Knowledge Base Costs**", expanded=True):
                    st.write("**Vector Store (Pinecone):**")
                    st.write("• $0.0001 per 1K vectors/month")
                    st.write("• **Estimated:** ~$5-20/month for typical usage")
                    
                    st.write("**Data Source Sync:**")
                    st.write("• $0.10 per 1K documents")
                    st.write("• **One-time cost** per sync")
                    
                    st.write("**Query Processing:**")
                    st.write("• $0.10 per 1K queries")
                    st.write("• **Per query cost**")
                    
                    st.write("**Embedding Generation:**")
                    st.write("• Uses Titan v2: $0.02 per 1M tokens")
                    st.write("• **Included in** document processing")
            
            # Cost estimation section
            st.markdown("---")
            st.subheader("📊 **Monthly Cost Estimation**")
            
            est_col1, est_col2, est_col3 = st.columns(3)
            
            with est_col1:
                st.metric("**Low Usage**", "$15-30", "~100 queries/month")
                st.caption("• Mostly Haiku model\n• Small document set\n• Basic S3 storage")
            
            with est_col2:
                st.metric("**Medium Usage**", "$50-100", "~500 queries/month")
                st.caption("• Mix of Haiku/Sonnet\n• Regular document updates\n• Standard S3 + IA")
            
            with est_col3:
                st.metric("**High Usage**", "$150-300", "~2000 queries/month")
                st.caption("• All models used\n• Large document corpus\n• Full S3 lifecycle")
            
            # Cost optimization tips
            with st.expander("💡 **Cost Optimization Tips**", expanded=False):
                st.write("**Model Selection:**")
                st.write("• Use Haiku for simple questions (10x cheaper than Opus)")
                st.write("• Use Sonnet for complex analysis (5x cheaper than Opus)")
                st.write("• Use Opus only for creative tasks")
                
                st.write("**Storage Optimization:**")
                st.write("• Enable S3 lifecycle policies (moves old docs to IA/Glacier)")
                st.write("• Compress documents before upload")
                st.write("• Regular cleanup of unused documents")
                
                st.write("**Query Optimization:**")
                st.write("• Use specific, focused questions")
                st.write("• Leverage example questions for common queries")
                st.write("• Monitor usage in AWS Cost Explorer")
                
                st.write("**Smart Routing Benefits:**")
                st.write("• Automatically selects cost-effective models")
                st.write("• Reduces unnecessary Opus usage")
                st.write("• Optimizes based on query complexity")
        else:
            st.warning("⚠️ AWS clients not initialized")
    
    with tab4:
        st.header("🧠 Smart Router Configuration")
        
        if smart_router:
            st.success("✅ **Smart Router: Initialized**")
            
            # Available models
            st.subheader("🤖 Available Models")
            for model_name, model_id in smart_router.models.items():
                model_info = smart_router.get_model_info(model_name)
                with st.expander(f"**{model_name.title()}** - {model_info.get('name', model_id)}"):
                    st.write(f"**Model ID:** `{model_id}`")
                    st.write(f"**Description:** {model_info.get('description', 'N/A')}")
                    st.write(f"**Cost:** {model_info.get('cost_per_1m_tokens', 'N/A')}")
                    st.write(f"**Max Tokens:** {model_info.get('max_tokens', 'N/A')}")
            
            # Routing logic
            st.subheader("🎯 Routing Logic")
            st.write("**Query Complexity Analysis:**")
            st.write("• **Simple queries** → Haiku (fast, cost-effective)")
            st.write("• **Complex queries** → Sonnet (balanced performance)")
            st.write("• **Low KB relevance** → Opus (general knowledge)")
            st.write("• **Creative queries** → Opus (maximum capability)")
            
            st.write("**Relevance Thresholds:**")
            st.write(f"• **High relevance:** ≥ {smart_router.high_relevance_threshold}")
            st.write(f"• **Medium relevance:** ≥ {smart_router.medium_relevance_threshold}")
            st.write(f"• **Low relevance:** < {smart_router.medium_relevance_threshold}")
        else:
            st.warning("⚠️ Smart Router not initialized")
    
    with tab5:
        st.header("📈 Analytics & Cost Tracking")
        
        if model_test_results:
            st.success("✅ **Model Testing: Completed**")
            
            # Model test results in a table format
            st.subheader("🧪 Test Results")
            for model_name, result in model_test_results.items():
                if result["success"]:
                    st.success(f"✅ **{model_name.title()}:** {result['message']}")
                else:
                    st.error(f"❌ **{model_name.title()}:** {result['message']}")
            
            # Summary statistics
            st.subheader("📊 Summary Statistics")
            successful_models = sum(1 for result in model_test_results.values() if result["success"])
            total_models = len(model_test_results)
            success_rate = (successful_models / total_models) * 100 if total_models > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Models", total_models)
            with col2:
                st.metric("Successful", successful_models)
            with col3:
                st.metric("Success Rate", f"{success_rate:.1f}%")
        else:
            st.info("ℹ️ Model testing pending...")
        
        # Cost tracking section
        st.markdown("---")
        st.subheader("💰 **Cost Tracking & Usage Analytics**")
        
        # Initialize session state for cost tracking
        if 'query_count' not in st.session_state:
            st.session_state.query_count = 0
        if 'total_tokens_used' not in st.session_state:
            st.session_state.total_tokens_used = 0
        if 'cost_by_model' not in st.session_state:
            st.session_state.cost_by_model = {'haiku': 0, 'sonnet': 0, 'opus': 0}
        
        # Cost tracking metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Queries Processed", st.session_state.query_count)
        
        with col2:
            st.metric("Total Tokens Used", f"{st.session_state.total_tokens_used:,}")
        
        with col3:
            total_cost = sum(st.session_state.cost_by_model.values())
            st.metric("Estimated Cost", f"${total_cost:.4f}")
        
        with col4:
            if st.session_state.query_count > 0:
                avg_cost = total_cost / st.session_state.query_count
                st.metric("Avg Cost/Query", f"${avg_cost:.4f}")
            else:
                st.metric("Avg Cost/Query", "$0.0000")
        
        # Model usage breakdown
        st.subheader("🤖 **Model Usage Breakdown**")
        
        if st.session_state.query_count > 0:
            usage_col1, usage_col2 = st.columns(2)
            
            with usage_col1:
                st.write("**Cost by Model:**")
                for model, cost in st.session_state.cost_by_model.items():
                    if cost > 0:
                        percentage = (cost / total_cost) * 100 if total_cost > 0 else 0
                        st.write(f"• **{model.title()}:** ${cost:.4f} ({percentage:.1f}%)")
            
            with usage_col2:
                # Create a simple bar chart for model usage
                try:
                    import pandas as pd
                    
                    model_data = {
                        'Model': list(st.session_state.cost_by_model.keys()),
                        'Cost': list(st.session_state.cost_by_model.values())
                    }
                    df = pd.DataFrame(model_data)
                    df = df[df['Cost'] > 0]  # Only show models with usage
                    
                    if not df.empty:
                        st.bar_chart(df.set_index('Model'))
                    else:
                        st.info("No model usage data yet")
                except ImportError:
                    # Fallback if pandas is not available
                    st.write("**Model Usage Chart:**")
                    for model, cost in st.session_state.cost_by_model.items():
                        if cost > 0:
                            st.write(f"• **{model.title()}:** ${cost:.4f}")
        else:
            st.info("No queries processed yet. Start asking questions to see cost analytics!")
        
        # Cost optimization recommendations
        st.subheader("💡 **Cost Optimization Recommendations**")
        
        if st.session_state.query_count > 0:
            # Analyze usage patterns and provide recommendations
            recommendations = []
            
            if st.session_state.cost_by_model.get('opus', 0) > 0:
                opus_percentage = (st.session_state.cost_by_model['opus'] / total_cost) * 100
                if opus_percentage > 30:
                    recommendations.append(f"⚠️ High Opus usage ({opus_percentage:.1f}%) - Consider using Sonnet for complex queries")
            
            if st.session_state.cost_by_model.get('haiku', 0) == 0:
                recommendations.append("💡 No Haiku usage - Consider using Haiku for simple questions to reduce costs")
            
            if st.session_state.query_count < 10:
                recommendations.append("📊 Limited data - More queries needed for accurate cost analysis")
            
            if recommendations:
                for rec in recommendations:
                    st.write(rec)
            else:
                st.success("✅ Good cost optimization! Your model usage is well-balanced.")
        else:
            st.info("Start using the system to get personalized cost optimization recommendations!")
        
        # Reset button for cost tracking
        if st.button("🔄 Reset Cost Tracking", help="Reset all cost tracking data"):
            st.session_state.query_count = 0
            st.session_state.total_tokens_used = 0
            st.session_state.cost_by_model = {'haiku': 0, 'sonnet': 0, 'opus': 0}
            st.rerun()

def render_main_page(settings, aws_clients, aws_error, kb_status, kb_error, smart_router):
    """Render the clean main page focused on user experience."""
    # Header section
    st.title("📊 Adobe Experience League Chatbot")
    st.markdown("**Intelligent RAG Assistant for Adobe Analytics Documentation**")
    st.markdown("---")
    
    # Simple status indicator
    if not aws_error and kb_status and smart_router:
        st.success("🚀 **System Ready** - Ask your question below!")
    elif not aws_error and smart_router:
        st.info("🔧 **System Loading** - Knowledge Base testing in progress...")
    else:
        st.warning("⚠️ **System Setup** - Please check admin dashboard for details")
    
    # Main content area
    st.header("💬 Ask Your Question")
    st.markdown("Ask any question about Adobe Analytics, Customer Journey Analytics, or related topics.")
    
    # Query input section
    col1, col2 = st.columns([4, 1])
    
    with col1:
        # Query input with example question support
        default_value = st.session_state.get('selected_example_question', '')
        query = st.text_input(
            "Enter your question:",
            value=default_value,
            placeholder="e.g., How do I create custom events in Adobe Analytics?",
            key="query_input",
            help="Ask any question about Adobe Analytics, Customer Journey Analytics, or related topics."
        )
        
        # Clear the selected example question after it's been used
        if st.session_state.get('selected_example_question'):
            st.session_state.selected_example_question = None
    
    with col2:
        # Submit button
        submit_button = st.button("🚀 Ask Question", type="primary", use_container_width=True)
    
    # Process query when submitted
    if submit_button:
        if not query:
            st.warning("⚠️ Please enter a question first!")
        elif aws_clients and not aws_error and kb_status and smart_router:
            # Show processing status
            with st.spinner("🤖 Processing your question with AI..."):
                # Process query with smart routing
                result = process_query_with_smart_routing(
                    query,
                    settings.bedrock_knowledge_base_id,
                    smart_router,
                    aws_clients
                )
                
                # Track cost and usage
                if result["success"]:
                    # Initialize session state for cost tracking
                    if 'query_count' not in st.session_state:
                        st.session_state.query_count = 0
                    if 'total_tokens_used' not in st.session_state:
                        st.session_state.total_tokens_used = 0
                    if 'cost_by_model' not in st.session_state:
                        st.session_state.cost_by_model = {'haiku': 0, 'sonnet': 0, 'opus': 0}
                    
                    # Increment query count
                    st.session_state.query_count += 1
                    
                    # Estimate tokens and cost (rough estimation)
                    model_used = result.get('model_used', 'haiku')
                    answer_length = len(result.get('answer', ''))
                    query_length = len(query)
                    
                    # Rough token estimation (1 token ≈ 4 characters)
                    estimated_tokens = (query_length + answer_length) // 4
                    st.session_state.total_tokens_used += estimated_tokens
                    
                    # Cost calculation based on model
                    cost_per_1k_tokens = {
                        'haiku': 0.00125,  # $1.25 per 1M tokens
                        'sonnet': 0.015,   # $15 per 1M tokens  
                        'opus': 0.075      # $75 per 1M tokens
                    }
                    
                    estimated_cost = (estimated_tokens / 1000) * cost_per_1k_tokens.get(model_used, 0.00125)
                    st.session_state.cost_by_model[model_used] += estimated_cost
            
            if not result["success"]:
                st.error(f"❌ **Error:** {result['error']}")
            else:
                # Display results
                st.success(f"✅ **Retrieved {len(result['documents'])} relevant documents**")
                
                # Display routing information
                routing_decision = result["routing_decision"]
                with st.expander("🧠 Smart Routing Decision", expanded=False):
                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        st.write(f"**Selected Model:** {routing_decision['model'].title()}")
                        st.write(f"**Complexity:** {routing_decision['complexity']}")
                    with col_r2:
                        st.write(f"**KB Relevance:** {routing_decision['relevance']:.2f}")
                        st.write(f"**Reasoning:** {routing_decision['reasoning']}")
                    
                    # Show model info
                    model_info = smart_router.get_model_info(routing_decision['model'])
                    if model_info:
                        st.write(f"**Model Details:** {model_info['name']}")
                        st.write(f"**Description:** {model_info['description']}")
                        st.write(f"**Cost:** {model_info['cost_per_1m_tokens']}")
                
                # Display answer
                st.markdown("### 💡 Answer")
                st.markdown(result["answer"])
                
                # Show source documents
                if result["documents"]:
                    with st.expander("📚 Source Documents", expanded=False):
                        for i, doc in enumerate(result["documents"], 1):
                            st.markdown(f"**Document {i}** (Score: {doc.get('score', 'N/A')})")
                            content = doc.get('content', {}).get('text', 'N/A')
                            st.markdown(f"_{content[:300]}{'...' if len(content) > 300 else ''}_")
                            st.markdown("---")
                
                # Show processing summary
                with st.expander("📊 Processing Summary", expanded=False):
                    col_s1, col_s2, col_s3 = st.columns(3)
                    with col_s1:
                        st.metric("Model Used", result['model_used'].title())
                    with col_s2:
                        st.metric("Documents Retrieved", len(result['documents']))
                    with col_s3:
                        st.metric("Answer Length", f"{len(result['answer'])} chars")
        else:
            st.error("❌ **System not ready!** Please check the admin dashboard for system status.")
    
    # Example questions section
    st.markdown("---")
    st.markdown("### 💡 Example Questions")
    
    example_cols = st.columns(3)
    example_questions = [
        "What is Adobe Analytics?",
        "How do I create custom events?",
        "Compare Adobe Analytics vs Google Analytics",
        "What are the best practices for web analytics?",
        "How to implement tracking scripts?",
        "What is Customer Journey Analytics?"
    ]
    
    # Initialize selected question in session state
    if 'selected_example_question' not in st.session_state:
        st.session_state.selected_example_question = None
    
    for i, question in enumerate(example_questions):
        with example_cols[i % 3]:
            if st.button(f"💬 {question}", key=f"example_{i}", help="Click to use this example question"):
                st.session_state.selected_example_question = question
                st.rerun()
    
    
    # Footer
    st.markdown("---")
    st.markdown("**Adobe Experience League Chatbot** - Powered by AWS Bedrock & Smart Routing")

def main():
    """Main Streamlit application entry point."""
    # Load configuration
    settings, config_error = load_configuration()
    
    # Initialize AWS clients if configuration is loaded
    aws_clients = None
    aws_error = None
    kb_status = None
    kb_error = None
    smart_router = None
    model_test_results = None
    
    if not config_error:
        aws_clients, aws_error = initialize_aws_clients(settings)
        
        # Initialize smart router
        smart_router = SmartRouter()
        
        # Test Knowledge Base connection if AWS clients are initialized
        if aws_clients and not aws_error:
            kb_status, kb_error = test_knowledge_base_connection(
                settings.bedrock_knowledge_base_id,
                aws_clients['bedrock_agent_client']
            )
            
            # Test model invocation if KB is working
            if kb_status and smart_router:
                model_test_results = {}
                # Only test available models to avoid AccessDeniedException during startup
                available_models = ["haiku", "sonnet"]
                for model_name in available_models:
                    if model_name in smart_router.models:
                        model_id = smart_router.models[model_name]
                        try:
                            success, message = test_model_invocation(
                                model_id, 
                                "Test query", 
                                aws_clients['bedrock_client']
                            )
                            model_test_results[model_name] = {"success": success, "message": message}
                        except Exception as e:
                            model_test_results[model_name] = {"success": False, "message": f"Test failed: {str(e)}"}
                
                # Mark unavailable models as not tested
                for model_name in smart_router.models:
                    if model_name not in available_models:
                        model_test_results[model_name] = {"success": False, "message": "Not tested - model not accessible"}
    
    # Page selection
    page = st.sidebar.selectbox(
        "Navigate to:",
        ["🏠 Main Chat", "🔧 Admin Dashboard"],
        index=0
    )
    
    # Render appropriate page
    if page == "🏠 Main Chat":
        render_main_page(settings, aws_clients, aws_error, kb_status, kb_error, smart_router)
    else:  # Admin Dashboard
        render_admin_page(settings, aws_clients, aws_error, kb_status, kb_error, smart_router, model_test_results)

if __name__ == "__main__":
    main()
