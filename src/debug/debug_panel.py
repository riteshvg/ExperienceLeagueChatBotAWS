"""
Enhanced Debug Panel for Streamlit Chatbot Application

This module provides a comprehensive debug panel with organized information,
performance metrics, and user-friendly controls.
"""

import streamlit as st
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

class DebugPanel:
    """Enhanced debug panel with organized sections and performance tracking"""
    
    def __init__(self):
        self.initialize_session_variables()
    
    def initialize_session_variables(self):
        """Initialize debug-related session variables if they don't exist"""
        if 'debug_history' not in st.session_state:
            st.session_state.debug_history = []
        
        if 'query_count' not in st.session_state:
            st.session_state.query_count = 0
        
        if 'total_queries' not in st.session_state:
            st.session_state.total_queries = 0
        
        if 'response_times' not in st.session_state:
            st.session_state.response_times = []
        
        if 'success_count' not in st.session_state:
            st.session_state.success_count = 0
        
        if 'error_count' not in st.session_state:
            st.session_state.error_count = 0
        
        if 'session_cost' not in st.session_state:
            st.session_state.session_cost = 0.0
        
        if 'cost_by_model' not in st.session_state:
            st.session_state.cost_by_model = {}
        
        if 'total_tokens_used' not in st.session_state:
            st.session_state.total_tokens_used = 0
        
        if 'current_step_start' not in st.session_state:
            st.session_state.current_step_start = None
        
        if 'debug_panel_expanded' not in st.session_state:
            st.session_state.debug_panel_expanded = False
    
    def add_debug_entry(self, query: str, status: str, duration: float = None, 
                       tokens: int = None, cost: float = None, model: str = None,
                       error: str = None, step_info: str = None):
        """Add a new debug entry to the history"""
        entry = {
            'id': len(st.session_state.debug_history) + 1,
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'query': query[:60] + "..." if len(query) > 60 else query,
            'status': status,
            'duration': duration,
            'tokens': tokens,
            'cost': cost,
            'model': model,
            'error': error,
            'step_info': step_info
        }
        
        st.session_state.debug_history.append(entry)
        
        # Update counters
        if status == 'completed':
            st.session_state.success_count += 1
        elif status == 'error':
            st.session_state.error_count += 1
        
        # Update performance metrics
        if duration:
            st.session_state.response_times.append(duration)
        
        if tokens:
            st.session_state.total_tokens_used += tokens
        
        if cost:
            st.session_state.session_cost += cost
        
        if model and cost:
            if model not in st.session_state.cost_by_model:
                st.session_state.cost_by_model[model] = 0
            st.session_state.cost_by_model[model] += cost
    
    def render_current_status(self):
        """Render current session status section"""
        st.subheader("📊 Current Session Status")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            current_query = st.session_state.get('query_input', 'No query')
            st.metric(
                "Current Query",
                current_query[:30] + "..." if len(current_query) > 30 else current_query
            )
        
        with col2:
            processing_state = "Processing" if st.session_state.get('processing_query', False) else "Idle"
            st.metric("Processing State", processing_state)
        
        with col3:
            current_step = st.session_state.get('processing_step', 0)
            st.metric("Current Step", f"Step {current_step}")
        
        with col4:
            total_messages = len(st.session_state.get('chat_history', []))
            st.metric("Total Messages", total_messages)
        
        # Processing step details
        if st.session_state.get('processing_query', False):
            st.info(f"🔄 Currently processing: {st.session_state.get('processing_step', 0)}/5 steps")
        
        # Session activity summary
        st.write("**Session Activity Summary:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"• Total Queries: {st.session_state.get('total_queries', 0)}")
        with col2:
            st.write(f"• Successful: {st.session_state.get('success_count', 0)}")
        with col3:
            st.write(f"• Failed: {st.session_state.get('error_count', 0)}")
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        response_times = st.session_state.get('response_times', [])
        if not response_times:
            return {"message": "No performance data available"}
        
        stats = {
            'complexity_distribution': {
                'simple': st.session_state.get('success_count', 0),
                'medium': 0,
                'complex': 0
            },
            'detection_times': {
                'avg_ms': sum(response_times) / len(response_times) * 1000,
                'min_ms': min(response_times) * 1000,
                'max_ms': max(response_times) * 1000,
                'count': len(response_times)
            }
        }
        
        return stats

    def render_performance_metrics(self):
        """Render performance metrics dashboard"""
        st.subheader("⚡ Performance Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_response_time = 0
            if st.session_state.get('response_times'):
                avg_response_time = sum(st.session_state.response_times) / len(st.session_state.response_times)
            st.metric(
                "Avg Response Time",
                f"{avg_response_time:.2f}s",
                delta=None
            )
        
        with col2:
            total_tokens = st.session_state.get('total_tokens_used', 0)
            st.metric(
                "Total Tokens",
                f"{total_tokens:,}",
                delta=None
            )
        
        with col3:
            session_cost = st.session_state.get('session_cost', 0)
            st.metric(
                "Session Cost",
                f"${session_cost:.4f}",
                delta=None
            )
        
        with col4:
            success_rate = 0
            total_queries = st.session_state.get('total_queries', 0)
            if total_queries > 0:
                success_rate = (st.session_state.get('success_count', 0) / total_queries) * 100
            st.metric(
                "Success Rate",
                f"{success_rate:.1f}%",
                delta=None
            )
        
        # Current processing duration
        if st.session_state.get('current_step_start'):
            current_duration = time.time() - st.session_state.current_step_start
            st.info(f"⏱️ Current step duration: {current_duration:.2f}s")
    
    def render_query_history(self):
        """Render enhanced query history"""
        st.subheader("📝 Query History")
        
        if not st.session_state.get('debug_history'):
            st.info("No queries processed yet.")
            return
        
        # Show last 10 entries
        recent_history = st.session_state.debug_history[-10:]
        
        for entry in reversed(recent_history):
            with st.expander(f"Query #{entry['id']} - {entry['timestamp']}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Query:** {entry['query']}")
                    st.write(f"**Status:** {self._get_status_badge(entry['status'])}")
                    if entry['step_info']:
                        st.write(f"**Step Info:** {entry['step_info']}")
                
                with col2:
                    if entry['duration']:
                        st.write(f"**Duration:** {entry['duration']:.2f}s")
                    if entry['tokens']:
                        st.write(f"**Tokens:** {entry['tokens']:,}")
                    if entry['cost']:
                        st.write(f"**Cost:** ${entry['cost']:.4f}")
                    if entry['model']:
                        st.write(f"**Model:** {entry['model']}")
                
                if entry['error']:
                    st.error(f"**Error:** {entry['error']}")
    
    def render_session_variables(self):
        """Render organized session variables"""
        st.subheader("🔧 Session Variables")
        
        # Group variables by category
        core_session = {
            'session_id': st.session_state.get('current_session_id', 'Not set'),
            'processing_step': st.session_state.get('processing_step', 0),
            'query_input': st.session_state.get('query_input', 'Not set'),
            'processing_query': st.session_state.get('processing_query', False)
        }
        
        history_analytics = {
            'chat_history_count': len(st.session_state.get('chat_history', [])),
            'debug_history_count': len(st.session_state.get('debug_history', [])),
            'query_count': st.session_state.get('query_count', 0),
            'total_queries': st.session_state.get('total_queries', 0)
        }
        
        performance = {
            'response_times_count': len(st.session_state.get('response_times', [])),
            'success_count': st.session_state.get('success_count', 0),
            'error_count': st.session_state.get('error_count', 0),
            'session_cost': st.session_state.get('session_cost', 0),
            'total_tokens_used': st.session_state.get('total_tokens_used', 0)
        }
        
        ui_state = {
            'debug_mode': st.session_state.get('debug_mode', False),
            'query_enhancement_enabled': st.session_state.get('query_enhancement_enabled', False),
            'debug_panel_expanded': st.session_state.get('debug_panel_expanded', False)
        }
        
        # Display each category
        categories = [
            ("Core Session", core_session),
            ("History & Analytics", history_analytics),
            ("Performance", performance),
            ("UI State", ui_state)
        ]
        
        for category_name, variables in categories:
            with st.expander(f"📁 {category_name}", expanded=False):
                for key, value in variables.items():
                    st.write(f"**{key}:** {value}")
    
    def render_debug_controls(self):
        """Render debug control buttons"""
        st.subheader("🎛️ Debug Controls")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔄 Refresh Debug Info"):
                st.rerun()
        
        with col2:
            if st.button("🗑️ Clear Debug History"):
                st.session_state.debug_history = []
                st.session_state.query_count = 0
                st.session_state.total_queries = 0
                st.session_state.response_times = []
                st.session_state.success_count = 0
                st.session_state.error_count = 0
                st.session_state.session_cost = 0.0
                st.session_state.cost_by_model = {}
                st.session_state.total_tokens_used = 0
                st.success("Debug history cleared!")
                st.rerun()
        
        with col3:
            view_mode = st.selectbox(
                "View Mode",
                ["Summary", "Full Details"],
                index=0
            )
            st.session_state.debug_view_mode = view_mode
        
        with col4:
            if st.button("📊 Export Debug Data"):
                self.export_debug_data()
    
    def export_debug_data(self):
        """Export debug data as JSON"""
        debug_data = {
            'session_info': {
                'session_id': st.session_state.get('current_session_id', 'unknown'),
                'total_queries': st.session_state.get('total_queries', 0),
                'success_count': st.session_state.get('success_count', 0),
                'error_count': st.session_state.get('error_count', 0),
                'session_cost': st.session_state.get('session_cost', 0),
                'total_tokens_used': st.session_state.get('total_tokens_used', 0)
            },
            'performance_metrics': {
                'avg_response_time': sum(st.session_state.get('response_times', [])) / len(st.session_state.get('response_times', [])) if st.session_state.get('response_times') else 0,
                'response_times': st.session_state.get('response_times', []),
                'cost_by_model': st.session_state.get('cost_by_model', {})
            },
            'query_history': st.session_state.get('debug_history', []),
            'export_timestamp': datetime.now().isoformat()
        }
        
        st.download_button(
            label="📥 Download Debug Data",
            data=json.dumps(debug_data, indent=2),
            file_name=f"debug_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    def _get_status_badge(self, status: str) -> str:
        """Get status badge with color coding"""
        badges = {
            'completed': '✅ Completed',
            'processing': '⏳ Processing',
            'error': '❌ Error',
            'idle': '🔵 Idle'
        }
        return badges.get(status, f"❓ {status}")
    
    def render_debug_panel(self):
        """Main function to render the complete debug panel"""
        if not st.session_state.get('debug_mode', False):
            return
        
        # Debug panel toggle
        if st.button("🔍 Toggle Debug Panel"):
            st.session_state.debug_panel_expanded = not st.session_state.debug_panel_expanded
        
        if not st.session_state.get('debug_panel_expanded', False):
            st.info("🔍 Debug mode is active. Click 'Toggle Debug Panel' to view details.")
            return
        
        st.markdown("---")
        st.markdown("## 🔍 Debug Panel")
        
        # Render all sections
        self.render_current_status()
        st.markdown("---")
        
        self.render_performance_metrics()
        st.markdown("---")
        
        self.render_query_history()
        st.markdown("---")
        
        self.render_session_variables()
        st.markdown("---")
        
        self.render_debug_controls()
        st.markdown("---")

# Global instance
debug_panel = DebugPanel()
