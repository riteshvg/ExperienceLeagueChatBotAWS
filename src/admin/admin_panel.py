"""
Admin Panel for Adobe Analytics RAG Chatbot
Separated from main app.py for better performance and maintainability
"""

import streamlit as st
import time
from datetime import datetime, timedelta

# Database query components removed - no longer needed


def render_admin_page(settings, aws_clients, aws_error, kb_status, kb_error, smart_router, model_test_results, analytics_service=None, tagging_service=None):
    """Render the admin page with all technical details."""
    # Add logout button at the top
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("🔧 Admin Dashboard")
        st.markdown("**System Configuration, Status, and Analytics**")
    with col2:
        if st.button("🚪 Logout", type="secondary", help="Logout from admin panel"):
            if 'admin_authenticated' in st.session_state:
                del st.session_state.admin_authenticated
            st.success("👋 Logged out successfully!")
            st.rerun()
    
    st.markdown("---")
    
    # Create tabs for different admin sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 System Status", 
        "⚙️ Settings", 
        "📊 Query Analytics",
        "🔍 Database Query"
    ])
    
    with tab1:
        st.header("📊 System Status Overview")
        
        # Overall system status
        current_haiku_only_mode = st.session_state.get('haiku_only_mode', smart_router.haiku_only_mode if smart_router else False)
        if not aws_error and kb_status and smart_router:
            if current_haiku_only_mode:
                st.success("🚀 **System Status: READY** - All components operational (HAIKU-ONLY MODE ACTIVE)")
            else:
                st.success("🚀 **System Status: READY** - All components operational (SMART ROUTING MODE)")
        elif not aws_error and smart_router:
            if current_haiku_only_mode:
                st.info("🔧 **System Status: PARTIAL** - Knowledge Base testing in progress (HAIKU-ONLY MODE ACTIVE)")
            else:
                st.info("🔧 **System Status: PARTIAL** - Knowledge Base testing in progress (SMART ROUTING MODE)")
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
        
        # Account Information section (merged from AWS Details tab)
        st.markdown("---")
        st.subheader("🏢 Account Information")
        
        if aws_error:
            st.error(f"❌ **AWS Error:** {aws_error}")
        elif aws_clients:
            st.success("✅ **AWS clients initialized successfully**")
            
            # Account details in organized sections
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Account ID:** `{aws_clients['account_id']}`")
                st.write(f"**User ARN:** `{aws_clients['user_arn']}`")
                st.write(f"**Region:** `{settings.aws_default_region}`")
            
            with col2:
                st.write(f"**S3 Bucket:** `{aws_clients['s3_status']}`")
                st.write("**Bedrock Client:** ✅ Initialized")
                st.write("**STS Client:** ✅ Initialized")
        else:
            st.warning("⚠️ AWS clients not initialized")
    
    with tab2:
        st.header("⚙️ Settings & Configuration")
        
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
            
            # Debug mode toggle
            st.markdown("---")
            st.subheader("🔧 Debug Settings")
            debug_mode = st.checkbox(
                "Enable Debug Mode", 
                value=st.session_state.get('debug_mode', False),
                help="Show debug information in the main chat interface"
            )
            st.session_state.debug_mode = debug_mode
            
            if debug_mode:
                st.info("🔍 Debug mode enabled - Debug information will be shown in the main chat interface")
            else:
                st.info("🔍 Debug mode disabled - Clean interface without debug information")
            
            # Enable Haiku Only Mode (merged from Performance tab)
            st.markdown("---")
            st.subheader("🤖 Model Configuration")
            
            if smart_router:
                st.success("✅ **Smart Router: Initialized**")
                
                # Haiku-only mode indicator
                if smart_router.haiku_only_mode:
                    st.warning("⚠️ **HAIKU-ONLY MODE ACTIVE** - All queries will use Claude 3 Haiku for cost optimization (92% cost reduction)")
                    st.info("💡 This mode is enabled for one week testing. Monitor response quality and user feedback.")
                else:
                    st.info("ℹ️ **Normal Mode** - Smart routing based on query complexity and context")
                
                # Mode toggle section
                st.markdown("---")
                st.subheader("🔄 Dynamic Mode Control")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write("**Switch between modes based on your cost management needs:**")
                    st.write("• **Smart Routing**: Optimal quality with balanced costs")
                    st.write("• **Haiku-Only**: Maximum cost savings with good quality")
                
                with col2:
                    # Toggle button for Haiku-only mode
                    current_mode = smart_router.haiku_only_mode
                    new_mode = st.toggle(
                        "Enable Haiku-Only Mode",
                        value=current_mode,
                        help="Toggle to enable/disable Haiku-only mode for cost optimization"
                    )
                    
                    # Update mode if changed
                    if new_mode != current_mode:
                        smart_router.haiku_only_mode = new_mode
                        st.session_state.haiku_only_mode = new_mode
                        st.rerun()
                
                # Mode change confirmation
                if new_mode != current_mode:
                    if new_mode:
                        st.success("🔄 **Switched to Haiku-Only Mode** - All queries will now use Claude 3 Haiku")
                    else:
                        st.success("🔄 **Switched to Smart Routing Mode** - Models will be selected based on query analysis")
                
                # Cost impact analysis
                st.markdown("---")
                st.subheader("💰 Cost Impact Analysis")
                
                cost_col1, cost_col2 = st.columns(2)
                
                with cost_col1:
                    st.write("**Current Mode Cost (per 1M tokens):**")
                    if smart_router.haiku_only_mode:
                        st.metric("Haiku Only", "$1.50", "92% savings vs Sonnet")
                        st.caption("• Input: $0.25 per 1M tokens")
                        st.caption("• Output: $1.25 per 1M tokens")
                    else:
                        st.metric("Smart Routing", "Variable", "Optimized selection")
                        st.caption("• Haiku: $1.50 per 1M tokens")
                        st.caption("• Sonnet: $18.00 per 1M tokens")
                        st.caption("• Opus: $75.00 per 1M tokens")
                
                with cost_col2:
                    st.write("**Estimated Monthly Savings:**")
                    if smart_router.haiku_only_mode:
                        st.metric("Cost Reduction", "80-90%", "vs Smart Routing")
                        st.caption("• Typical usage: $15-30/month")
                        st.caption("• High usage: $50-100/month")
                    else:
                        st.metric("Balanced Cost", "Optimized", "Quality + Efficiency")
                        st.caption("• Typical usage: $50-150/month")
                        st.caption("• High usage: $200-400/month")
            else:
                st.warning("⚠️ Smart Router not initialized")
    
    with tab3:
        st.header("📊 Query Analytics Dashboard")
        
        # Check if analytics service is available
        if st.session_state.get('analytics_available', False):
            st.success("✅ **Analytics Service: Available**")
            
            # Render the analytics dashboard
            try:
                analytics_service.render_analytics_dashboard()
            except Exception as e:
                st.error(f"❌ **Analytics Dashboard Error:** {str(e)}")
                st.info("💡 **Troubleshooting:** Check database connection and configuration")
        else:
            st.warning("⚠️ **Analytics Service: Not Available**")
            st.info("""
            **To enable query analytics:**
            1. Set up a database (PostgreSQL, MySQL, or SQLite)
            2. Configure database connection in environment variables
            3. Run database migration script
            4. Restart the application
            
            **For local testing with SQLite:**
            ```bash
            export USE_SQLITE=true
            export SQLITE_DATABASE=analytics.db
            ```
            """)
            
            # Show database configuration status
            st.subheader("🔧 Database Configuration Status")
            try:
                from src.utils.database_config import get_database_info
                db_info = get_database_info()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Database Type:** {db_info.get('type', 'Unknown')}")
                    st.write(f"**Host:** {db_info.get('host', 'Unknown')}")
                    st.write(f"**Port:** {db_info.get('port', 'Unknown')}")
                
                with col2:
                    st.write(f"**Database:** {db_info.get('database', 'Unknown')}")
                    st.write(f"**Username:** {db_info.get('username', 'Unknown')}")
                    st.write(f"**Railway:** {db_info.get('is_railway', False)}")
                
            except Exception as e:
                st.error(f"Database configuration error: {e}")
        
        # Add tagging analytics section
        st.markdown("---")
        st.subheader("🏷️ Tagging Analytics")
        
        if tagging_service and st.session_state.get('tagging_available', False):
            st.success("✅ **Tagging Service: Available**")
            
            # Render tagging analytics
            try:
                tagging_service.render_analytics_dashboard()
            except Exception as e:
                st.error(f"❌ **Tagging Analytics Error:** {str(e)}")
                st.info("💡 **Troubleshooting:** Check tagging service configuration")
        else:
            st.warning("⚠️ **Tagging Service: Not Available**")
            st.info("""
            **To enable tagging analytics:**
            1. Ensure tagging service is properly initialized
            2. Check that all tagging dependencies are installed
            3. Verify database connection for tagging data
            4. Restart the application
            """)
    
    with tab4:
        st.header("🔍 Database Query Interface")
        
        # GitHub Documentation Management
        st.markdown("---")
        st.subheader("📚 GitHub Documentation Management")
        
        # Define the four repositories used
        repositories = {
            "Adobe Analytics APIs": {
                "url": "https://github.com/AdobeDocs/analytics-2.0-apis.git",
                "description": "Adobe Analytics 2.0 APIs documentation",
                "added_date": "2024-09-01"  # This should be updated when actually added
            },
            "Adobe Analytics User Docs": {
                "url": "https://github.com/AdobeDocs/analytics.en.git", 
                "description": "Adobe Analytics user documentation",
                "added_date": "2024-09-01"
            },
            "Customer Journey Analytics": {
                "url": "https://github.com/AdobeDocs/customer-journey-analytics-learn.en.git",
                "description": "Customer Journey Analytics learning documentation", 
                "added_date": "2024-09-01"
            },
            "Analytics APIs Docs": {
                "url": "https://github.com/AdobeDocs/analytics-2.0-apis.git",
                "description": "Analytics APIs comprehensive documentation",
                "added_date": "2024-09-01"
            }
        }
        
        # Button to fetch repository details
        if st.button("🔄 Fetch Repository Details", help="Get latest information about the GitHub repositories"):
            with st.spinner("Fetching repository information..."):
                try:
                    import requests
                    
                    st.success("✅ Repository details fetched successfully!")
                    
                    # Display repository information
                    for repo_name, repo_info in repositories.items():
                        with st.expander(f"📖 {repo_name}", expanded=True):
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.write(f"**Description:** {repo_info['description']}")
                                st.write(f"**Repository URL:** {repo_info['url']}")
                                st.write(f"**Added to Application:** {repo_info['added_date']}")
                            
                            with col2:
                                # Calculate days since added
                                added_date = datetime.strptime(repo_info['added_date'], "%Y-%m-%d")
                                days_since_added = (datetime.now() - added_date).days
                                st.metric("Days Since Added", days_since_added)
                                
                                # Try to get last commit info (simplified)
                                try:
                                    # Extract repo path from URL
                                    repo_path = repo_info['url'].replace('https://github.com/', '').replace('.git', '')
                                    api_url = f"https://api.github.com/repos/{repo_path}"
                                    
                                    response = requests.get(api_url, timeout=10)
                                    if response.status_code == 200:
                                        repo_data = response.json()
                                        last_updated = repo_data.get('updated_at', '')
                                        if last_updated:
                                            last_update_date = datetime.strptime(last_updated[:10], "%Y-%m-%d")
                                            days_since_update = (datetime.now() - last_update_date).days
                                            st.metric("Days Since Last Update", days_since_update)
                                            st.caption(f"Last updated: {last_updated[:10]}")
                                        else:
                                            st.info("Last update info unavailable")
                                    else:
                                        st.warning("Could not fetch update info")
                                except Exception as e:
                                    st.warning(f"Update info unavailable: {str(e)[:50]}...")
                    
                    # Summary
                    st.markdown("### 📊 Summary")
                    total_repos = len(repositories)
                    avg_days_since_added = sum([
                        (datetime.now() - datetime.strptime(repo['added_date'], "%Y-%m-%d")).days 
                        for repo in repositories.values()
                    ]) / total_repos
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Repositories", total_repos)
                    with col2:
                        st.metric("Avg Days Since Added", f"{avg_days_since_added:.0f}")
                    with col3:
                        st.metric("Status", "Active")
                        
                except Exception as e:
                    st.error(f"❌ Error fetching repository details: {str(e)}")
                    st.info("💡 **Troubleshooting:** Check internet connection and GitHub API access")
        
        # Static repository information (always visible)
        st.markdown("### 📋 Repository Overview")
        
        for repo_name, repo_info in repositories.items():
            with st.expander(f"📖 {repo_name}", expanded=False):
                st.write(f"**Description:** {repo_info['description']}")
                st.write(f"**Repository URL:** {repo_info['url']}")
                st.write(f"**Added to Application:** {repo_info['added_date']}")
                
                # Calculate days since added
                added_date = datetime.strptime(repo_info['added_date'], "%Y-%m-%d")
                days_since_added = (datetime.now() - added_date).days
                st.write(f"**Days Since Added:** {days_since_added} days")
        
        # Tagging analytics removed for now
    


def display_aws_cost_data(cost_data):
    """Display AWS cost data in a formatted way."""
    try:
        results = cost_data.get('ResultsByTime', [])
        
        if not results:
            st.info("No cost data available for the selected period.")
            return
        
        # Calculate total costs
        total_cost = 0
        service_costs = {}
        
        for result in results:
            time_period = result.get('TimePeriod', {})
            groups = result.get('Groups', [])
            
            for group in groups:
                service = group.get('Keys', ['Unknown'])[0]
                metrics = group.get('Metrics', {})
                cost = float(metrics.get('BlendedCost', {}).get('Amount', 0))
                
                if service not in service_costs:
                    service_costs[service] = 0
                service_costs[service] += cost
                total_cost += cost
        
        # Display total cost
        st.metric("Total AWS Cost", f"${total_cost:.2f}")
        
        # Display service breakdown
        if service_costs:
            st.write("**Cost by Service:**")
            for service, cost in sorted(service_costs.items(), key=lambda x: x[1], reverse=True):
                percentage = (cost / total_cost) * 100 if total_cost > 0 else 0
                st.write(f"• **{service}:** ${cost:.2f} ({percentage:.1f}%)")
        
        # Create a simple chart if pandas is available
        try:
            import pandas as pd
            df = pd.DataFrame(list(service_costs.items()), columns=['Service', 'Cost'])
            df = df[df['Cost'] > 0]  # Only show services with costs
            if not df.empty:
                st.bar_chart(df.set_index('Service'))
        except ImportError:
            st.info("Install pandas for cost visualization charts")
            
    except Exception as e:
        st.error(f"Error displaying cost data: {str(e)}")


def display_bedrock_cost_data(cost_data):
    """Display Bedrock-specific cost data."""
    try:
        results = cost_data.get('ResultsByTime', [])
        
        if not results:
            st.info("No Bedrock cost data available for the selected period.")
            return
        
        total_cost = 0
        usage_costs = {}
        
        for result in results:
            groups = result.get('Groups', [])
            
            for group in groups:
                usage_type = group.get('Keys', ['Unknown'])[0]
                metrics = group.get('Metrics', {})
                cost = float(metrics.get('BlendedCost', {}).get('Amount', 0))
                
                if usage_type not in usage_costs:
                    usage_costs[usage_type] = 0
                usage_costs[usage_type] += cost
                total_cost += cost
        
        # Display total Bedrock cost
        st.metric("Total Bedrock Cost", f"${total_cost:.2f}")
        
        # Display usage type breakdown
        if usage_costs:
            st.write("**Cost by Usage Type:**")
            for usage_type, cost in sorted(usage_costs.items(), key=lambda x: x[1], reverse=True):
                percentage = (cost / total_cost) * 100 if total_cost > 0 else 0
                st.write(f"• **{usage_type}:** ${cost:.2f} ({percentage:.1f}%)")
        
    except Exception as e:
        st.error(f"Error displaying Bedrock cost data: {str(e)}")


def display_s3_cost_data(cost_data):
    """Display S3-specific cost data."""
    try:
        results = cost_data.get('ResultsByTime', [])
        
        if not results:
            st.info("No S3 cost data available for the selected period.")
            return
        
        total_cost = 0
        usage_costs = {}
        
        for result in results:
            groups = result.get('Groups', [])
            
            for group in groups:
                usage_type = group.get('Keys', ['Unknown'])[0]
                metrics = group.get('Metrics', {})
                cost = float(metrics.get('BlendedCost', {}).get('Amount', 0))
                
                if usage_type not in usage_costs:
                    usage_costs[usage_type] = 0
                usage_costs[usage_type] += cost
                total_cost += cost
        
        # Display total S3 cost
        st.metric("Total S3 Cost", f"${total_cost:.2f}")
        
        # Display usage type breakdown
        if usage_costs:
            st.write("**Cost by Usage Type:**")
            for usage_type, cost in sorted(usage_costs.items(), key=lambda x: x[1], reverse=True):
                percentage = (cost / total_cost) * 100 if total_cost > 0 else 0
                st.write(f"• **{usage_type}:** ${cost:.2f} ({percentage:.1f}%)")
        
    except Exception as e:
        st.error(f"Error displaying S3 cost data: {str(e)}")
