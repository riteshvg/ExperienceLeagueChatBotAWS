"""
Simple test page for Documentation Management Dashboard
Run this with: streamlit run test_doc_dashboard.py
"""

import streamlit as st
from src.admin.documentation_manager import DocumentationManager
from src.admin.documentation_dashboard import DocumentationDashboard
from config.settings import get_settings

st.set_page_config(page_title="Documentation Management Test", layout="wide")

st.title("📚 Documentation Management Dashboard - Test Page")
st.markdown("This is a standalone test page to verify the dashboard works.")

# Load settings
settings = get_settings()

st.success("✅ Settings loaded successfully")
st.info(f"**KB ID:** {settings.bedrock_knowledge_base_id}")
st.info(f"**Region:** {settings.bedrock_region}")
st.info(f"**Bucket:** {settings.aws_s3_bucket}")

# Initialize manager
with st.spinner("Initializing Documentation Manager..."):
    try:
        doc_manager = DocumentationManager(
            kb_id=settings.bedrock_knowledge_base_id,
            region=settings.bedrock_region
        )
        st.success("✅ DocumentationManager initialized")
    except Exception as e:
        st.error(f"❌ Error initializing manager: {e}")
        import traceback
        st.code(traceback.format_exc())
        st.stop()

# Initialize dashboard
with st.spinner("Initializing Documentation Dashboard..."):
    try:
        doc_dashboard = DocumentationDashboard(doc_manager)
        st.success("✅ DocumentationDashboard initialized")
    except Exception as e:
        st.error(f"❌ Error initializing dashboard: {e}")
        import traceback
        st.code(traceback.format_exc())
        st.stop()

st.markdown("---")

# Render dashboard
st.header("📊 Dashboard Content")
try:
    doc_dashboard.render_dashboard()
    st.success("✅ Dashboard rendered successfully!")
except Exception as e:
    st.error(f"❌ Error rendering dashboard: {e}")
    import traceback
    st.code(traceback.format_exc())

