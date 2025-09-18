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
            st.session_state.debug_panel_expanded = True
    
    def add_debug_entry(self, query: str, status: str, duration: float = None, 
                       tokens: int = None, cost: float = None, model: str = None,
                       error: str = None, step_info: str = None, source_urls: List[str] = None):
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
            'step_info': step_info,
            'source_urls': source_urls or []
        }
        
        st.session_state.debug_history.append(entry)
        
        # Update counters
        if status == 'completed':
            st.session_state.success_count += 1
        elif status == 'error':
            st.session_state.error_count += 1
        
        # Store last model used
        if model:
            st.session_state.last_model_used = model
        
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
        """Render current session status section (sidebar optimized)"""
        st.markdown("**📊 Current Status**")
        
        # Compact status display
        current_query = st.session_state.get('query_input', 'No query')
        processing_state = "Processing" if st.session_state.get('processing_query', False) else "Idle"
        current_step = st.session_state.get('processing_step', 0)
        total_messages = len(st.session_state.get('chat_history', []))
        last_model = st.session_state.get('last_model_used', 'Not set')
        
        # Status in compact format
        st.write(f"**Query:** {current_query[:25]}{'...' if len(current_query) > 25 else ''}")
        st.write(f"**State:** {processing_state} | **Step:** {current_step}")
        st.write(f"**Messages:** {total_messages}")
        st.write(f"**Last Model:** {last_model}")
        
        # Processing step details
        if st.session_state.get('processing_query', False):
            st.info(f"🔄 Step {current_step}/5")
        
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
        """Render performance metrics dashboard (sidebar optimized)"""
        st.markdown("**⚡ Performance**")
        
        # Compact metrics display
        avg_response_time = 0
        if st.session_state.get('response_times'):
            avg_response_time = sum(st.session_state.response_times) / len(st.session_state.response_times)
        
        total_tokens = st.session_state.get('total_tokens_used', 0)
        session_cost = st.session_state.get('session_cost', 0)
        
        success_rate = 0
        total_queries = st.session_state.get('total_queries', 0)
        if total_queries > 0:
            success_rate = (st.session_state.get('success_count', 0) / total_queries) * 100
        
        # Compact format
        st.write(f"**Avg Time:** {avg_response_time:.2f}s")
        st.write(f"**Tokens:** {total_tokens:,}")
        st.write(f"**Cost:** ${session_cost:.4f}")
        st.write(f"**Success:** {success_rate:.1f}%")
        
        # Current processing duration
        if st.session_state.get('current_step_start'):
            current_duration = time.time() - st.session_state.current_step_start
            st.info(f"⏱️ Current step duration: {current_duration:.2f}s")
    
    def render_query_history(self):
        """Render enhanced query history (sidebar optimized)"""
        st.markdown("**📝 Query History**")
        
        if not st.session_state.get('debug_history'):
            st.info("No queries yet")
            return
        
        # Show last 5 entries in compact format
        recent_history = st.session_state.debug_history[-5:]
        
        for entry in reversed(recent_history):
            # Compact entry display
            status_emoji = "✅" if entry['status'] == 'completed' else "❌" if entry['status'] == 'error' else "🔄"
            duration = f"{entry['duration']:.1f}s" if entry['duration'] else "N/A"
            tokens = f"{entry['tokens']:,}" if entry['tokens'] else "N/A"
            model = entry.get('model', 'Unknown')
            
            st.write(f"{status_emoji} **#{entry['id']}** {entry['timestamp']}")
            st.write(f"   {entry['query'][:40]}{'...' if len(entry['query']) > 40 else ''}")
            st.write(f"   Time: {duration} | Tokens: {tokens} | Model: {model}")
            
            # Show source URLs if available
            if entry.get('source_urls'):
                with st.expander(f"📚 Sources for Query #{entry['id']}", expanded=False):
                    self.render_source_urls(entry['source_urls'])
            
            if entry['error']:
                st.error(f"   Error: {entry['error'][:50]}{'...' if len(entry['error']) > 50 else ''}")
    
    def render_session_variables(self):
        """Render organized session variables (sidebar optimized)"""
        st.markdown("**🔧 Session Variables**")
        
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
    
    def _convert_s3_uri_to_experience_league_url(self, s3_uri: str) -> str:
        """Convert S3 URI to proper Adobe Experience League URL."""
        if not s3_uri or not s3_uri.startswith('s3://'):
            return s3_uri
        
        # Extract the path after the bucket name
        # s3://bucket-name/adobe-docs/path/to/file.md
        parts = s3_uri.split('/')
        if len(parts) < 4:
            return s3_uri
        
        # Get the path after 'adobe-docs'
        adobe_docs_index = -1
        for i, part in enumerate(parts):
            if part == 'adobe-docs':
                adobe_docs_index = i
                break
        
        if adobe_docs_index == -1 or adobe_docs_index + 1 >= len(parts):
            return s3_uri
        
        # Get the relative path after adobe-docs
        relative_path = '/'.join(parts[adobe_docs_index + 1:])
        
        # Remove file extension
        if relative_path.endswith('.md'):
            relative_path = relative_path[:-3]
        elif relative_path.endswith('.txt'):
            relative_path = relative_path[:-4]
        
        # Map S3 paths to Experience League URLs based on actual Adobe structure
        if relative_path.startswith('adobe-analytics/'):
            # adobe-analytics/path → analytics/path
            exp_league_path = relative_path.replace('adobe-analytics/', 'analytics/')
            # Use /en/docs/ structure for main pages
            if exp_league_path.count('/') <= 1:
                return f"https://experienceleague.adobe.com/en/docs/{exp_league_path}"
            else:
                return f"https://experienceleague.adobe.com/en/docs/{exp_league_path}"
        
        elif relative_path.startswith('customer-journey-analytics/'):
            # customer-journey-analytics/path → customer-journey-analytics/path
            # Use the correct CJA URL structure
            if relative_path.count('/') <= 1:
                return f"https://experienceleague.adobe.com/en/docs/{relative_path}"
            else:
                return f"https://experienceleague.adobe.com/en/docs/{relative_path}"
        
        elif relative_path.startswith('experience-platform/'):
            # experience-platform/path → real-time-customer-data-platform/path
            # Map to Real-Time CDP as it's the main AEP documentation
            aep_path = relative_path.replace('experience-platform/', 'real-time-customer-data-platform/')
            if aep_path.count('/') <= 1:
                return f"https://experienceleague.adobe.com/en/docs/{aep_path}"
            else:
                return f"https://experienceleague.adobe.com/en/docs/{aep_path}"
        
        elif relative_path.startswith('analytics-apis/'):
            # analytics-apis/path → analytics/apis/path
            exp_league_path = relative_path.replace('analytics-apis/', 'analytics/apis/')
            return f"https://experienceleague.adobe.com/en/docs/{exp_league_path}"
        
        elif relative_path.startswith('cja-apis/'):
            # cja-apis/path → customer-journey-analytics/apis/path
            exp_league_path = relative_path.replace('cja-apis/', 'customer-journey-analytics/apis/')
            return f"https://experienceleague.adobe.com/en/docs/{exp_league_path}"
        
        else:
            # Default fallback - try to map to a reasonable URL
            # For unknown paths, try to construct a reasonable URL
            if '/' not in relative_path:
                return f"https://experienceleague.adobe.com/en/docs/{relative_path}"
            else:
                return f"https://experienceleague.adobe.com/en/docs/{relative_path}"
    
    def render_source_urls(self, source_urls: List[str]):
        """Render clickable source URLs"""
        if not source_urls:
            return
        
        st.markdown("**📚 Source Documents:**")
        
        for i, url in enumerate(source_urls, 1):
            # Convert S3 URI to Experience League URL
            if url.startswith('s3://'):
                exp_league_url = self._convert_s3_uri_to_experience_league_url(url)
                # Extract filename from S3 URI for display name
                filename = url.split('/')[-1]
                if filename.endswith('.md'):
                    filename = filename[:-3]
                elif filename.endswith('.txt'):
                    filename = filename[:-4]
                display_name = filename.replace('_', ' ').replace('-', ' ').title()
                st.markdown(f"{i}. [{display_name}]({exp_league_url})")
            else:
                # If it's already a web URL, use it directly
                st.markdown(f"{i}. [Source {i}]({url})")
    
    def render_debug_controls(self):
        """Render debug control buttons (sidebar optimized)"""
        st.markdown("**🎛️ Debug Controls**")
        
        # Compact controls
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Refresh", help="Refresh debug info"):
                st.rerun()
        
        with col2:
            if st.button("🗑️ Clear", help="Clear debug history"):
                st.session_state.debug_history = []
                st.session_state.query_count = 0
                st.session_state.total_queries = 0
                st.session_state.response_times = []
                st.session_state.success_count = 0
                st.session_state.error_count = 0
                st.session_state.session_cost = 0.0
                st.session_state.cost_by_model = {}
                st.session_state.total_tokens_used = 0
                st.success("Cleared!")
                st.rerun()
        
        # Export button
        if st.button("📊 Export Data", help="Download debug data"):
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
        """Main function to render the complete debug panel under query input"""
        if not st.session_state.get('debug_mode', False):
            return
        
        # Render debug panel directly under query input
        st.markdown("---")
        with st.expander("🔍 Debug Panel", expanded=True):
            # Debug panel toggle (optional - for collapsing)
            col1, col2 = st.columns([1, 2])
            with col1:
                if st.button("🔍 Toggle", help="Show/hide detailed debug information"):
                    st.session_state.debug_panel_expanded = not st.session_state.get('debug_panel_expanded', True)
            
            with col2:
                if st.session_state.get('debug_panel_expanded', True):
                    st.success("Details ON")
                else:
                    st.info("Details OFF")
            
            # Always show basic debug info
            self.render_current_status()
            
            # Show detailed sections only if expanded
            if st.session_state.get('debug_panel_expanded', True):
                st.markdown("---")
                self.render_performance_metrics()
                st.markdown("---")
                self.render_query_history()
                st.markdown("---")
                self.render_session_variables()
                st.markdown("---")
                self.render_debug_controls()
    
    def render_debug_panel_content_only(self):
        """Render only the debug panel content without column layout"""
        if not st.session_state.get('debug_mode', False):
            return
        
        st.markdown("---")
        st.markdown("## 🔍 Debug Panel")
        
        # Debug panel toggle (optional - for collapsing)
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("🔍 Toggle", help="Show/hide detailed debug information"):
                st.session_state.debug_panel_expanded = not st.session_state.get('debug_panel_expanded', True)
        
        with col2:
            if st.session_state.get('debug_panel_expanded', True):
                st.success("Details ON")
            else:
                st.info("Details OFF")
        
        # Always show basic debug info
        self.render_current_status()
        
        # Show detailed sections only if expanded
        if st.session_state.get('debug_panel_expanded', True):
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
