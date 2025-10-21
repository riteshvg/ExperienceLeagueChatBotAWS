"""
Auto-retraining UI for single-click model improvement.
Provides interface for pipeline management and monitoring.
"""

import streamlit as st
from typing import Dict, Any
from datetime import datetime
import asyncio
from .status_monitor import StatusMonitor
from .retraining_monitor import RetrainingMonitor


class AutoRetrainingUI:
    """UI components for auto-retraining pipeline."""

    def __init__(self):
        """Initialize auto-retraining UI."""
        self.status_monitor = StatusMonitor()
        self.retraining_monitor = RetrainingMonitor()

    def render_auto_retraining_dashboard(self):
        """Render the auto-retraining dashboard."""
        st.header("🚀 Auto-Retraining Pipeline")
        st.markdown("Automated model improvement based on user feedback")
        
        # Add tabs for different views
        tab1, tab2, tab3 = st.tabs(["📊 Pipeline Status", "🔍 Monitoring", "⚙️ Configuration"])
        
        with tab1:
            self._render_pipeline_status_tab()
        
        with tab2:
            self._render_monitoring_tab()
        
        with tab3:
            self._render_configuration_tab()
    
    def _render_pipeline_status_tab(self):
        """Render the pipeline status tab."""
        if st.session_state.get('auto_retraining_pipeline'):
            pipeline = st.session_state.auto_retraining_pipeline
            
            # Get live status with real-time updates
            status_summary = self.status_monitor.render_live_status(pipeline)
            
            # Render status alerts
            self.status_monitor.render_status_alert(status_summary)
            
            # Render progress indicators
            self.status_monitor.render_progress_indicators(status_summary)
            
            # Render feedback history
            self.status_monitor.render_feedback_history(pipeline)
    
    def _render_monitoring_tab(self):
        """Render the monitoring tab."""
        if st.session_state.get('auto_retraining_pipeline'):
            pipeline = st.session_state.auto_retraining_pipeline
            self.retraining_monitor.render_monitoring_dashboard(pipeline)
        else:
            st.error("Auto-retraining pipeline not initialized.")
    
    def _render_configuration_tab(self):
        """Render the configuration tab."""
        if st.session_state.get('auto_retraining_pipeline'):
            pipeline = st.session_state.auto_retraining_pipeline
            
            # Detailed status information
            with st.expander("📊 Detailed Status", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Queue Size:** {status_summary['queue_size']} items")
                    st.write(f"**Threshold:** {status_summary['threshold']} items")
                    st.write(f"**Quality Threshold:** {pipeline.quality_threshold}/5")
                
                with col2:
                    st.write(f"**Cooldown Period:** {pipeline.retraining_cooldown/3600:.1f} hours")
                    if status_summary['last_retraining']:
                        last_time = datetime.fromtimestamp(status_summary['last_retraining'])
                        st.write(f"**Last Retraining:** {last_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    else:
                        st.write("**Last Retraining:** Never")
                
                # Show last update time
                st.write(f"**Last Update:** {status_summary['timestamp']}")

            # Configuration
            with st.expander("⚙️ Pipeline Configuration", expanded=False):
                new_threshold = st.number_input(
                    "Retraining Threshold",
                    min_value=1,
                    max_value=100,
                    value=status_summary['threshold'],
                    help="Minimum number of feedback items to trigger retraining"
                )

                new_quality = st.number_input(
                    "Quality Threshold",
                    min_value=1,
                    max_value=5,
                    value=pipeline.quality_threshold,
                    help="Minimum quality score to include in training"
                )

                new_cooldown = st.number_input(
                    "Cooldown Period (hours)",
                    min_value=0.01,
                    max_value=24.0,
                    value=pipeline.retraining_cooldown / 3600,
                    help="Minimum time between retraining jobs"
                )

                if st.button("Update Configuration"):
                    pipeline.update_config({
                        'retraining_threshold': new_threshold,
                        'quality_threshold': new_quality,
                        'retraining_cooldown': new_cooldown * 3600
                    })
                    st.success("Configuration updated!")
                    st.rerun()

            # Manual controls
            col1, col2 = st.columns(2)

            with col1:
                if st.button("🔄 Force Retraining", disabled=status_summary['queue_size'] < 1):
                    if status_summary['queue_size'] >= 1:
                        # Force retraining
                        asyncio.run(pipeline._trigger_auto_retraining())
                        st.success("Retraining triggered!")
                        st.rerun()
                    else:
                        st.warning("Need at least 1 feedback item to force retraining")

            with col2:
                if st.button("🗑️ Reset Pipeline"):
                    pipeline.reset_pipeline()
                    st.success("Pipeline reset!")
                    st.rerun()

        else:
            st.warning("Auto-retraining pipeline not initialized. Please check configuration.")

    def render_feedback_submission_with_auto_retraining(self, feedback_data: Dict[str, Any]):
        """Render feedback submission with auto-retraining integration."""
        st.subheader("📝 Submit Feedback")

        with st.form("feedback_form"):
            query = st.text_area("Query", value=feedback_data.get('query', ''), disabled=True)

            col1, col2 = st.columns(2)
            with col1:
                gemini_response = st.text_area("Gemini Response", value=feedback_data.get('gemini_response', ''), disabled=True)
            with col2:
                claude_response = st.text_area("Claude Response", value=feedback_data.get('claude_response', ''), disabled=True)

            selected_model = st.selectbox(
                "Which response do you prefer?",
                ["gemini", "claude", "both"],
                index=0
            )

            user_rating = st.slider("Overall Rating", 1, 5, 4)

            st.subheader("Response Quality")
            col1, col2 = st.columns(2)
            with col1:
                accuracy = st.slider("Accuracy", 1, 5, 4)
                relevance = st.slider("Relevance", 1, 5, 4)
            with col2:
                clarity = st.slider("Clarity", 1, 5, 4)
                completeness = st.slider("Completeness", 1, 5, 4)

            submit_button = st.form_submit_button("🚀 Submit Feedback & Trigger Auto-Retraining", type="primary")

            if submit_button:
                # Prepare feedback data
                feedback = {
                    'query': query,
                    'gemini_response': gemini_response,
                    'claude_response': claude_response,
                    'selected_model': selected_model,
                    'user_rating': user_rating,
                    'response_quality': {
                        'accuracy': accuracy,
                        'relevance': relevance,
                        'clarity': clarity,
                        'completeness': completeness
                    },
                    'timestamp': datetime.now().isoformat()
                }

                # Process feedback through auto-retraining pipeline
                if st.session_state.get('auto_retraining_pipeline'):
                    pipeline = st.session_state.auto_retraining_pipeline
                    result = asyncio.run(pipeline.process_feedback_async(feedback))

                    if result['status'] == 'queued':
                        st.success(f"✅ {result['message']}")
                    elif result['status'] == 'retraining_started':
                        st.success(f"🚀 {result['message']}")
                        st.info(f"Training data size: {result['training_data_size']} examples")
                    else:
                        st.error(f"❌ {result['message']}")
                else:
                    st.error("Auto-retraining pipeline not initialized")