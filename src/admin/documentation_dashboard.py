"""
Documentation Dashboard for Admin Panel

This module provides the Streamlit UI for the documentation management dashboard.
"""

import streamlit as st
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DocumentationDashboard:
    """Documentation management dashboard UI."""
    
    def __init__(self, doc_manager):
        """
        Initialize documentation dashboard.
        
        Args:
            doc_manager: DocumentationManager instance
        """
        self.doc_manager = doc_manager
    
    def render_dashboard(self):
        """Render the main documentation dashboard."""
        st.header("📚 Documentation Management Dashboard")
        st.markdown("Monitor and manage documentation updates for all Adobe solutions.")
        
        # Refresh button
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("🔄 Refresh Status", type="primary"):
                st.rerun()
        
        with col2:
            if st.button("🚀 Auto-Update All Stale", type="secondary"):
                self._handle_auto_update_all()
        
        with col3:
            if st.button("📊 View Statistics", type="secondary"):
                self._show_statistics()
        
        st.markdown("---")
        
        # Documentation freshness status
        with st.spinner("Checking documentation freshness..."):
            freshness_status = self.doc_manager.check_documentation_freshness()
        
        # Render status cards
        self._render_status_cards(freshness_status)
        
        # Detailed status table
        st.markdown("---")
        st.subheader("📋 Detailed Status")
        self._render_detailed_table(freshness_status)
        
        # Auto-update recommendations
        self._render_recommendations(freshness_status)
    
    def _render_status_cards(self, freshness_status: Dict):
        """Render status cards for each documentation source."""
        st.subheader("📊 Documentation Status")
        
        # Create columns for status cards
        cols = st.columns(len(freshness_status))
        
        for idx, (source_key, status) in enumerate(freshness_status.items()):
            with cols[idx]:
                self._render_status_card(source_key, status)
    
    def _render_status_card(self, source_key: str, status: Dict):
        """Render a single status card."""
        display_name = status.get('display_name', source_key)
        status_type = status.get('status', 'unknown')
        
        # Color coding
        if status_type == 'current':
            color = "🟢"
            bg_color = "#d4edda"
        elif status_type == 'stale':
            color = "🟡"
            bg_color = "#fff3cd"
        else:
            color = "🔴"
            bg_color = "#f8d7da"
        
        # Card HTML
        st.markdown(f"""
        <div style="background-color: {bg_color}; padding: 15px; border-radius: 10px; margin-bottom: 10px;">
            <h3>{color} {display_name}</h3>
            <p><strong>Status:</strong> {status_type.upper()}</p>
            <p><strong>Days Behind:</strong> {status.get('days_behind', 'N/A')}</p>
            <p><strong>Last Update:</strong> {self._format_date(status.get('s3_last_upload'))}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Update button for stale docs
        if status.get('needs_update'):
            if st.button(f"Update {display_name}", key=f"update_{source_key}"):
                self._handle_update_source(source_key)
    
    def _render_detailed_table(self, freshness_status: Dict):
        """Render detailed status table."""
        import pandas as pd
        
        table_data = []
        for source_key, status in freshness_status.items():
            table_data.append({
                'Documentation Source': status.get('display_name', source_key),
                'Status': status.get('status', 'unknown').upper(),
                'GitHub Last Commit': self._format_date(status.get('github_last_commit')),
                'S3 Last Upload': self._format_date(status.get('s3_last_upload')),
                'Days Behind': status.get('days_behind', 'N/A'),
                'Update Frequency': f"{status.get('update_frequency_days', 'N/A')} days",
                'Needs Update': '✅ Yes' if status.get('needs_update') else '❌ No'
            })
        
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    def _render_recommendations(self, freshness_status: Dict):
        """Render update recommendations."""
        stale_sources = [
            (key, status) for key, status in freshness_status.items()
            if status.get('needs_update')
        ]
        
        if stale_sources:
            st.markdown("---")
            st.subheader("⚠️ Update Recommendations")
            
            for source_key, status in stale_sources:
                st.warning(
                    f"**{status['display_name']}** is {status.get('days_behind', 'unknown')} days behind. "
                    f"Last updated: {self._format_date(status.get('s3_last_upload'))}"
                )
            
            st.info("💡 Click 'Auto-Update All Stale' to update all outdated documentation sources.")
        else:
            st.success("✅ All documentation sources are up to date!")
    
    def _handle_update_source(self, source_key: str):
        """Handle update for a specific source."""
        with st.spinner(f"Updating {source_key}..."):
            success, message = self.doc_manager.trigger_documentation_update(source_key)
            
            if success:
                st.success(f"✅ {message}")
                st.info("🔄 Refreshing status...")
                st.rerun()
            else:
                st.error(f"❌ {message}")
    
    def _handle_auto_update_all(self):
        """Handle auto-update for all stale sources."""
        with st.spinner("Auto-updating all stale documentation..."):
            results = self.doc_manager.auto_update_stale_docs()
        
        st.markdown("---")
        st.subheader("📊 Auto-Update Results")
        
        for source_key, result in results.items():
            if result['success'] is None:
                st.info(f"**{result['display_name']}**: {result['message']}")
            elif result['success']:
                st.success(f"✅ **{result['display_name']}**: {result['message']}")
            else:
                st.error(f"❌ **{result['display_name']}**: {result['message']}")
        
        st.info("🔄 Refreshing status in 3 seconds...")
        import time
        time.sleep(3)
        st.rerun()
    
    def _show_statistics(self):
        """Show documentation statistics."""
        with st.spinner("Loading statistics..."):
            stats = self.doc_manager.get_documentation_stats()
        
        st.markdown("---")
        st.subheader("📊 Documentation Statistics")
        
        if 'error' in stats:
            st.error(f"Error loading statistics: {stats['error']}")
        else:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Files", f"{stats['total_files']:,}")
            
            with col2:
                st.metric("Total Size", f"{stats['total_size_mb']} MB")
            
            with col3:
                st.metric("Knowledge Base ID", stats['knowledge_base_id'])
            
            with col4:
                st.metric("Bucket", stats['bucket_name'])
            
            # Additional info
            st.markdown("### 📁 Storage Details")
            st.write(f"**Region**: {stats['region']}")
            st.write(f"**Bucket**: `{stats['bucket_name']}`")
            st.write(f"**Knowledge Base**: `{stats['knowledge_base_id']}`")
    
    def _format_date(self, date_str: Optional[str]) -> str:
        """Format date string for display."""
        if not date_str:
            return "N/A"
        
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        except Exception:
            return date_str
    
    def render_update_history(self):
        """Render update history."""
        st.subheader("📜 Update History")
        
        # This would show recent update history
        # For now, show a placeholder
        st.info("Update history feature coming soon. This will show recent documentation updates and ingestion jobs.")
        
        # Show recent ingestion jobs
        st.markdown("### Recent Ingestion Jobs")
        st.info("Recent ingestion job monitoring coming soon.")

