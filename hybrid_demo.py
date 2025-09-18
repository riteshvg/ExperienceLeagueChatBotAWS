"""
Demo Streamlit app for hybrid model architecture.
Demonstrates Gemini and Claude integration with comparison features.
"""

import streamlit as st
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

from src.models.model_provider import ModelProvider
from src.config.hybrid_config import HybridConfigManager
from src.routing.query_router import QueryRouter
from src.ui.comparison_ui import ComparisonUI

# Authentication functions
def check_authentication():
    """Check if user is authenticated."""
    # Check if already authenticated
    if st.session_state.get('authenticated', False):
        return True
    
    # Show authentication form
    st.markdown("### 🔐 Authentication Required")
    st.markdown("Please enter the password to access the Hybrid AI Model Demo.")
    
    # Create a form for password input
    with st.form("auth_form"):
        password = st.text_input("Password", type="password", placeholder="Enter password")
        submit_button = st.form_submit_button("🔓 Access Demo")
        
        if submit_button:
            # Check password (you can change this to your preferred password)
            demo_password = os.getenv("DEMO_PASSWORD", "demo123")  # Default password
            if password == demo_password:
                st.session_state.authenticated = True
                st.success("✅ Access granted! Loading demo...")
                st.rerun()
            else:
                st.error("❌ Invalid password. Please try again.")
    
    return False

def logout_user():
    """Logout from demo."""
    if 'authenticated' in st.session_state:
        del st.session_state.authenticated
    st.success("👋 Logged out successfully!")
    st.rerun()

def main():
    """Main Streamlit app for hybrid model demo."""
    st.set_page_config(
        page_title="Hybrid AI Model Demo",
        page_icon="🔄",
        layout="wide"
    )
    
    # Check authentication
    if not check_authentication():
        return
    
    # Header with logout button
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("🔄 Hybrid AI Model Architecture Demo")
        st.markdown("**Compare Google Gemini and AWS Bedrock Claude models side-by-side**")
    with col2:
        if st.button("🚪 Logout", type="secondary", help="Logout from demo"):
            logout_user()
    
    # Initialize session state
    if 'model_provider' not in st.session_state:
        st.session_state.model_provider = None
    if 'config_manager' not in st.session_state:
        st.session_state.config_manager = None
    if 'query_router' not in st.session_state:
        st.session_state.query_router = None
    if 'comparison_ui' not in st.session_state:
        st.session_state.comparison_ui = None
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key status
        st.subheader("🔑 API Keys")
        config_manager = HybridConfigManager()
        api_status = config_manager.validate_api_keys()
        
        # Debug information
        with st.expander("🔍 Debug Info", expanded=False):
            google_key = os.getenv('GOOGLE_API_KEY')
            aws_key = os.getenv('AWS_ACCESS_KEY_ID')
            st.write(f"Google API Key: {'✅ Set' if google_key else '❌ Not set'}")
            st.write(f"AWS Access Key: {'✅ Set' if aws_key else '❌ Not set'}")
            if google_key:
                st.write(f"Google Key (first 10 chars): {google_key[:10]}...")
            if aws_key:
                st.write(f"AWS Key (first 10 chars): {aws_key[:10]}...")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Google", "✅" if api_status['google_available'] else "❌")
        with col2:
            st.metric("AWS", "✅" if api_status['aws_available'] else "❌")
        
        if not api_status['at_least_one_available']:
            st.error("No API keys found. Please set GOOGLE_API_KEY or AWS credentials.")
            st.info("Set environment variables or add to .env file")
            return
        
        # Initialize components
        if st.button("🚀 Initialize Models"):
            with st.spinner("Initializing models..."):
                try:
                    # Initialize model provider
                    model_provider = ModelProvider()
                    st.session_state.model_provider = model_provider
                    
                    # Initialize query router
                    query_router = QueryRouter(config_manager)
                    st.session_state.query_router = query_router
                    
                    # Initialize comparison UI
                    comparison_ui = ComparisonUI(model_provider, query_router)
                    st.session_state.comparison_ui = comparison_ui
                    
                    st.session_state.config_manager = config_manager
                    
                    st.success("Models initialized successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Initialization failed: {e}")
        
        # Model status
        if st.session_state.model_provider:
            st.subheader("🤖 Model Status")
            available_models = st.session_state.model_provider.get_available_models()
            for model in available_models:
                st.success(f"✅ {model.title()}")
        
        # Configuration settings
        if st.session_state.config_manager:
            st.subheader("⚙️ Settings")
            
            # Model preference
            preferred_model = st.selectbox(
                "Preferred Model:",
                ["auto", "gemini", "claude"],
                index=0,
                key="preferred_model_selectbox"
            )
            
            # Cost vs Quality preference
            cost_vs_quality = st.slider(
                "Cost vs Quality:",
                min_value=0.0,
                max_value=1.0,
                value=0.5,
                help="0 = Cost sensitive, 1 = Quality focused",
                key="cost_vs_quality_slider"
            )
            
            # Update configuration
            if st.button("💾 Save Settings"):
                st.session_state.config_manager.update_user_preferences(
                    preferred_model=preferred_model,
                    cost_sensitivity=1.0 - cost_vs_quality
                )
                st.session_state.config_manager.save_config()
                st.success("Settings saved!")
        
        # Model Links Section
        st.subheader("🔗 Model Links")
        
        # Google Gemini links
        with st.expander("🤖 Google Gemini", expanded=False):
            st.markdown("")
            st.markdown("**[Google AI Studio](https://makersuite.google.com/app/apikey)** - Get API key")
            st.markdown("**[Gemini Documentation](https://ai.google.dev/docs)** - Official docs")
            st.markdown("**[Gemini API Reference](https://ai.google.dev/api/rest)** - API reference")
            st.markdown("**[Gemini Pricing](https://ai.google.dev/pricing)** - Cost information")
        
        # AWS Bedrock Claude links
        with st.expander("🤖 AWS Bedrock Claude", expanded=False):
            st.markdown("")
            st.markdown("**[AWS Bedrock Console](https://console.aws.amazon.com/bedrock/)** - Access Bedrock")
            st.markdown("**[Claude Documentation](https://docs.anthropic.com/claude)** - Official docs")
            st.markdown("**[Bedrock API Reference](https://docs.aws.amazon.com/bedrock/)** - API docs")
            st.markdown("**[Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)** - Cost information")
        
        # Adobe Experience League links
        with st.expander("📚 Adobe Experience League", expanded=False):
            st.markdown("")
            st.markdown("**[Adobe Analytics](https://experienceleague.adobe.com/docs/analytics/)** - Analytics docs")
            st.markdown("**[Customer Journey Analytics](https://experienceleague.adobe.com/docs/analytics-platform/)** - CJA docs")
            st.markdown("**[Adobe Experience Platform](https://experienceleague.adobe.com/docs/experience-platform/)** - AEP docs")
            st.markdown("**[Mobile SDK](https://experienceleague.adobe.com/docs/mobile/)** - Mobile docs")
    
    # Main content
    if not st.session_state.model_provider:
        st.info("👆 Please initialize the models using the sidebar to get started.")
        
        # Show setup instructions
        with st.expander("📋 Setup Instructions", expanded=True):
            st.markdown("""
            ### Prerequisites
            
            1. **Google API Key** (for Gemini):
               - Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
               - Set environment variable: `GOOGLE_API_KEY=your_key_here`
            
            2. **AWS Credentials** (for Claude):
               - Configure AWS credentials for Bedrock access
               - Set environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
               - Or use AWS CLI: `aws configure`
            
            3. **Install Dependencies**:
               ```bash
               pip install google-generativeai tiktoken
               ```
            
            ### Features
            
            - **Side-by-side comparison** of Gemini and Claude responses
            - **Smart routing** based on query characteristics
            - **Performance tracking** with cost and speed metrics
            - **Test suite** for systematic model evaluation
            - **Configuration management** with user preferences
            """)
        
        return
    
    # Main interface
    tab1, tab2, tab3, tab4 = st.tabs(["🔄 Compare Models", "🧭 Smart Routing", "🧪 Test Suite", "📊 Analytics"])
    
    with tab1:
        st.session_state.comparison_ui.render_comparison_interface()
    
    with tab2:
        render_smart_routing_interface()
    
    with tab3:
        render_test_suite_interface()
    
    with tab4:
        render_analytics_interface()

def render_smart_routing_interface():
    """Render smart routing interface."""
    st.header("🧭 Smart Query Routing")
    st.markdown("Let the system automatically choose the best model for your query")
    
    # Initialize session state for smart routing results
    if 'smart_routing_result' not in st.session_state:
        st.session_state.smart_routing_result = None
    if 'smart_routing_query' not in st.session_state:
        st.session_state.smart_routing_query = ""
    
    # Query input
    query = st.text_area(
        "Enter your query:",
        placeholder="e.g., What is Adobe Analytics and how does it work?",
        height=100,
        key="query_text_area"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        context_length = st.slider(
            "Context Length:",
            min_value=0,
            max_value=100000,
            value=0,
            step=1000,
            help="Estimated context length in characters",
            key="context_length_slider"
        )
    
    with col2:
        if st.button("🎯 Analyze & Route", type="primary"):
            if query:
                # Store query in session state
                st.session_state.smart_routing_query = query
                
                with st.spinner("Analyzing query and selecting best model..."):
                    # Get routing decision
                    decision = st.session_state.query_router.determine_best_model(query, context_length)
                    
                    # Display analysis
                    st.subheader("🔍 Query Analysis")
                    analysis = st.session_state.query_router.analyze_query(query)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Complexity", analysis.complexity.title())
                    with col2:
                        st.metric("Query Type", analysis.query_type.title())
                    with col3:
                        st.metric("Confidence", f"{analysis.confidence:.1%}")
                    
                    # Display routing decision
                    st.subheader("🎯 Routing Decision")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Recommended Model", decision.recommended_model.title())
                        st.write(f"**Reasoning:** {decision.reasoning}")
                    
                    with col2:
                        st.metric("Estimated Cost", f"${decision.estimated_cost:.4f}")
                        st.metric("Estimated Time", f"{decision.estimated_time:.1f}s")
                    
                    # Execute query automatically
                    st.subheader("🚀 Executing Query...")
                    with st.spinner(f"Querying {decision.recommended_model}..."):
                        if decision.recommended_model == 'gemini':
                            result = st.session_state.model_provider.query_gemini(query)
                        else:
                            result = st.session_state.model_provider.query_claude_bedrock(query)
                        
                        # Store result in session state
                        st.session_state.smart_routing_result = {
                            'result': result,
                            'decision': decision,
                            'analysis': analysis,
                            'query': query
                        }
            else:
                st.error("Please enter a query")
    
    # Display results if available
    if st.session_state.smart_routing_result and st.session_state.smart_routing_query == query:
        result_data = st.session_state.smart_routing_result
        result = result_data['result']
        decision = result_data['decision']
        
        if result['success']:
            st.subheader(f"🤖 {decision.recommended_model.title()} Response")
            st.write(result['response'])
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Actual Time", f"{result['response_time']:.2f}s")
            with col2:
                st.metric("Actual Cost", f"${result['cost']:.4f}")
            with col3:
                st.metric("Tokens", f"{result['total_tokens']:,}")
                
            # Add source links
            st.markdown("---")
            st.subheader("📚 **Relevant Sources**")
            source_links = [
                {
                    'title': 'Adobe Analytics Documentation',
                    'url': 'https://experienceleague.adobe.com/docs/analytics/home.html',
                    'description': 'Complete Adobe Analytics documentation'
                },
                {
                    'title': 'Adobe Experience Platform Documentation', 
                    'url': 'https://experienceleague.adobe.com/docs/experience-platform/home.html',
                    'description': 'Complete Adobe Experience Platform documentation'
                },
                {
                    'title': 'Adobe Experience League',
                    'url': 'https://experienceleague.adobe.com/',
                    'description': 'Adobe Experience League learning hub'
                }
            ]
            
            for link in source_links:
                st.markdown(f"**[{link['title']}]({link['url']})**  \n*{link['description']}*")
                st.write("")
        else:
            st.error(f"Query failed: {result['error']}")

def render_test_suite_interface():
    """Render test suite interface."""
    st.header("🧪 Test Suite")
    st.markdown("Run systematic tests to compare model performance")
    
    # Test categories
    test_categories = {
        'Basic Facts': [
            "What is Adobe Analytics?",
            "How does Customer Journey Analytics work?",
            "What are eVars in Adobe Analytics?"
        ],
        'Implementation': [
            "How do I create a calculated metric?",
            "Show me how to implement custom event tracking",
            "What's the best way to set up cross-domain tracking?"
        ],
        'Complex Analysis': [
            "Compare different attribution models and their use cases",
            "Explain the relationship between segments, metrics, and dimensions",
            "Design a comprehensive tagging strategy for e-commerce"
        ],
        'Troubleshooting': [
            "Why isn't my tracking code working?",
            "How to debug data collection issues?",
            "What causes missing data in Adobe Analytics?"
        ]
    }
    
    # Category selection
    selected_category = st.selectbox("Select Test Category:", list(test_categories.keys()), key="test_category_selectbox")
    
    # Display test queries
    st.subheader(f"📝 {selected_category} Tests")
    test_queries = test_categories[selected_category]
    
    for i, query in enumerate(test_queries):
        with st.expander(f"Test {i+1}: {query}", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(f"Run Gemini", key=f"gemini_{i}"):
                    with st.spinner("Running Gemini..."):
                        result = st.session_state.model_provider.query_gemini(query, max_tokens=200)
                        if result['success']:
                            st.write(result['response'])
                            st.metric("Time", f"{result['response_time']:.2f}s")
                            st.metric("Cost", f"${result['cost']:.4f}")
                        else:
                            st.error(result['error'])
            
            with col2:
                if st.button(f"Run Claude", key=f"claude_{i}"):
                    with st.spinner("Running Claude..."):
                        result = st.session_state.model_provider.query_claude_bedrock(query, max_tokens=200)
                        if result['success']:
                            st.write(result['response'])
                            st.metric("Time", f"{result['response_time']:.2f}s")
                            st.metric("Cost", f"${result['cost']:.4f}")
                        else:
                            st.error(result['error'])
    
    # Run all tests
    if st.button("🚀 Run All Tests", type="primary"):
        with st.spinner("Running all tests..."):
            results = []
            for i, query in enumerate(test_queries):
                st.write(f"Running test {i+1}: {query}")
                
                # Run both models
                both_result = st.session_state.model_provider.query_both_models(query)
                if both_result['success']:
                    results.append({
                        'query': query,
                        'results': both_result['results'],
                        'comparison': both_result['comparison']
                    })
            
            st.success(f"Completed {len(results)} tests!")
            
            # Display summary
            if results:
                st.subheader("📊 Test Summary")
                
                # Calculate metrics
                gemini_times = []
                claude_times = []
                gemini_costs = []
                claude_costs = []
                
                for result in results:
                    if 'gemini' in result['results'] and result['results']['gemini']['success']:
                        gemini_times.append(result['results']['gemini']['response_time'])
                        gemini_costs.append(result['results']['gemini']['cost'])
                    
                    if 'claude' in result['results'] and result['results']['claude']['success']:
                        claude_times.append(result['results']['claude']['response_time'])
                        claude_costs.append(result['results']['claude']['cost'])
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if gemini_times:
                        st.metric("Avg Gemini Time", f"{sum(gemini_times)/len(gemini_times):.2f}s")
                
                with col2:
                    if claude_times:
                        st.metric("Avg Claude Time", f"{sum(claude_times)/len(claude_times):.2f}s")
                
                with col3:
                    if gemini_costs:
                        st.metric("Total Gemini Cost", f"${sum(gemini_costs):.4f}")
                
                with col4:
                    if claude_costs:
                        st.metric("Total Claude Cost", f"${sum(claude_costs):.4f}")

def render_analytics_interface():
    """Render analytics interface."""
    st.header("📊 Analytics Dashboard")
    st.markdown("View performance metrics and usage statistics")
    
    if not st.session_state.model_provider:
        st.info("Initialize models first to see analytics")
        return
    
    # Get usage statistics
    stats = st.session_state.model_provider.get_usage_stats()
    
    # Cost summary
    st.subheader("💰 Cost Summary")
    cost_summary = stats['cost_summary']
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Queries", cost_summary['total_queries'])
    
    with col2:
        st.metric("Total Cost", f"${cost_summary['total_cost']:.4f}")
    
    with col3:
        st.metric("Total Tokens", f"{cost_summary['total_tokens']:,}")
    
    with col4:
        st.metric("Avg Cost/Query", f"${cost_summary['avg_cost_per_query']:.4f}")
    
    # Model comparison
    st.subheader("🤖 Model Comparison")
    model_comparison = stats['model_comparison']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Gemini**")
        gemini_data = model_comparison['gemini']
        st.metric("Queries", gemini_data['total_queries'])
        st.metric("Cost", f"${gemini_data['total_cost']:.4f}")
        st.metric("Avg Cost/Query", f"${gemini_data['avg_cost_per_query']:.4f}")
        st.metric("Avg Response Time", f"{gemini_data['avg_response_time']:.2f}s")
    
    with col2:
        st.write("**Claude**")
        claude_data = model_comparison['claude']
        st.metric("Queries", claude_data['total_queries'])
        st.metric("Cost", f"${claude_data['total_cost']:.4f}")
        st.metric("Avg Cost/Query", f"${claude_data['avg_cost_per_query']:.4f}")
        st.metric("Avg Response Time", f"{claude_data['avg_response_time']:.2f}s")
    
    # Performance summary
    st.subheader("⚡ Performance Summary")
    performance_summary = stats['performance_summary']
    
    for model, data in performance_summary.items():
        if data['total_requests'] > 0:
            with st.expander(f"{model.title()} Performance", expanded=False):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Success Rate", f"{data['success_rate']:.1%}")
                    st.metric("Error Rate", f"{data['error_rate']:.1%}")
                
                with col2:
                    st.metric("Avg Response Time", f"{data['response_time_stats']['avg']:.2f}s")
                    st.metric("Min Response Time", f"{data['response_time_stats']['min']:.2f}s")
                
                with col3:
                    st.metric("Max Response Time", f"{data['response_time_stats']['max']:.2f}s")
                    st.metric("Health Status", data['health_status'])
    
    # Export data
    st.subheader("📥 Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Export Usage Data"):
            export_data = st.session_state.model_provider.export_data()
            st.download_button(
                label="Download JSON",
                data=export_data,
                file_name="usage_data.json",
                mime="application/json"
            )
    
    with col2:
        if st.button("🗑️ Reset Data"):
            st.session_state.model_provider.reset_data()
            st.success("Data reset successfully!")
            st.rerun()

if __name__ == "__main__":
    main()
