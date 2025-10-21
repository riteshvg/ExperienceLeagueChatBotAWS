"""
Real-time status monitoring for auto-retraining pipeline.
Provides live updates and progress tracking.
"""

import streamlit as st
import time
from datetime import datetime
from typing import Dict, Any

class StatusMonitor:
    """Real-time status monitoring for auto-retraining pipeline."""
    
    def __init__(self):
        """Initialize status monitor."""
        self.last_update = None
        self.update_interval = 2  # seconds
    
    def should_update(self) -> bool:
        """Check if status should be updated."""
        if self.last_update is None:
            return True
        
        return time.time() - self.last_update > self.update_interval
    
    def render_live_status(self, pipeline) -> Dict[str, Any]:
        """Render live status with real-time updates."""
        if not pipeline:
            return {}
        
        # Get current status
        status = pipeline.get_pipeline_status()
        
        # Update timestamp
        self.last_update = time.time()
        
        # Create status summary
        status_summary = {
            'status': status['status'],
            'queue_size': status['queue_size'],
            'threshold': status['retraining_threshold'],
            'progress': min(status['queue_size'] / status['retraining_threshold'], 1.0),
            'last_retraining': status['last_retraining'],
            'cooldown_remaining': status['cooldown_remaining'],
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
        
        return status_summary
    
    def render_status_alert(self, status_summary: Dict[str, Any]):
        """Render status alerts and notifications."""
        if not status_summary:
            return
        
        # Status-based alerts
        if status_summary['status'] == 'retraining':
            st.success("🚀 **Retraining in Progress!** Models are being updated with your feedback.")
        
        elif status_summary['progress'] >= 1.0:
            st.info("⚡ **Queue Full!** Ready to trigger retraining on next high-quality feedback.")
        
        elif status_summary['progress'] >= 0.8:
            st.info("📈 **Almost Ready!** Just a few more feedback items needed.")
        
        elif status_summary['cooldown_remaining'] > 0:
            st.warning(f"⏳ **Cooldown Active** - {status_summary['cooldown_remaining']:.0f}s remaining before next retraining.")
        
        # Recent activity indicator
        if status_summary['last_retraining']:
            last_time = datetime.fromtimestamp(status_summary['last_retraining'])
            time_diff = datetime.now() - last_time
            if time_diff.total_seconds() < 300:  # 5 minutes
                st.info(f"🕒 **Recent Activity** - Last retraining: {last_time.strftime('%H:%M:%S')}")
    
    def render_feedback_history(self, pipeline) -> None:
        """Render recent feedback history."""
        if not pipeline or not hasattr(pipeline, 'feedback_queue'):
            return
        
        if pipeline.feedback_queue:
            st.subheader("📝 Recent Feedback")
            
            # Show last 5 feedback items
            for i, feedback in enumerate(pipeline.feedback_queue[-5:], 1):
                with st.expander(f"Feedback #{len(pipeline.feedback_queue) - 5 + i}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Query:** {feedback.get('query', 'N/A')}")
                        st.write(f"**Selected Model:** {feedback.get('selected_model', 'N/A')}")
                        st.write(f"**Quality Scores:** "
                               f"Accuracy={feedback.get('response_quality', {}).get('accuracy', 'N/A')}, "
                               f"Relevance={feedback.get('response_quality', {}).get('relevance', 'N/A')}")
                    
                    with col2:
                        rating = feedback.get('user_rating', 0)
                        st.write(f"**Rating:** {'⭐' * rating} ({rating}/5)")
                        
                        # Quality indicator
                        if rating >= 4:
                            st.success("High Quality")
                        elif rating >= 3:
                            st.warning("Medium Quality")
                        else:
                            st.error("Low Quality")
    
    def render_progress_indicators(self, status_summary: Dict[str, Any]):
        """Render progress indicators and metrics."""
        if not status_summary:
            return
        
        # Progress bar with enhanced styling
        progress = status_summary['progress']
        
        if progress >= 1.0:
            st.progress(progress, text="🚀 Ready for retraining!")
        elif progress >= 0.8:
            st.progress(progress, text="⚡ Almost ready for retraining")
        elif progress >= 0.5:
            st.progress(progress, text="📈 Building feedback queue")
        else:
            st.progress(progress, text="📝 Collecting feedback")
        
        # Metrics with visual indicators
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status_emoji = ("🟢" if status_summary['status'] == 'idle'
                          else "🟡" if status_summary['status'] == 'retraining'
                          else "🔴")
            st.metric("Status", f"{status_emoji} {status_summary['status'].title()}")
        
        with col2:
            queue_ratio = status_summary['queue_size'] / status_summary['threshold']
            if queue_ratio >= 1.0:
                st.metric("Queue", f"🚀 {status_summary['queue_size']}/{status_summary['threshold']}", delta="Ready!")
            elif queue_ratio >= 0.8:
                st.metric("Queue", f"⚡ {status_summary['queue_size']}/{status_summary['threshold']}", delta="Almost ready")
            else:
                st.metric("Queue", f"📝 {status_summary['queue_size']}/{status_summary['threshold']}")
        
        with col3:
            if status_summary['last_retraining']:
                last_time = datetime.fromtimestamp(status_summary['last_retraining'])
                st.metric("Last Training", f"🕒 {last_time.strftime('%H:%M')}")
            else:
                st.metric("Last Training", "❌ Never")
        
        with col4:
            if status_summary['cooldown_remaining'] > 0:
                st.metric("Cooldown", f"⏳ {status_summary['cooldown_remaining']:.0f}s")
            else:
                st.metric("Cooldown", "✅ Ready")

