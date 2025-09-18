"""
Feedback UI components for hybrid model evaluation.
Provides interfaces for rating responses and managing feedback data.
"""

import streamlit as st
from typing import Dict, Any, Optional
from .feedback_manager import FeedbackManager

class FeedbackUI:
    """UI components for feedback collection and management."""
    
    def __init__(self):
        """Initialize feedback UI."""
        self.feedback_manager = FeedbackManager()
        
        # Initialize session state
        if 'current_feedback' not in st.session_state:
            st.session_state.current_feedback = None
        if 'feedback_submitted' not in st.session_state:
            st.session_state.feedback_submitted = False
    
    def render_feedback_form(
        self, 
        query: str, 
        gemini_response: str, 
        claude_response: str,
        selected_model: str = None
    ) -> Optional[str]:
        """
        Render feedback form for model comparison.
        
        Args:
            query: Original user query
            gemini_response: Gemini model response
            claude_response: Claude model response
            selected_model: Which model was selected
            
        Returns:
            Feedback ID if submitted, None otherwise
        """
        st.markdown("---")
        st.subheader("📝 Rate the Responses")
        st.markdown("Help us improve the models by rating the responses:")
        
        # Display responses for comparison
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🤖 Gemini Response**")
            st.text_area(
                "Gemini Response",
                value=gemini_response,
                height=200,
                disabled=True,
                key="feedback_gemini_display"
            )
        
        with col2:
            st.markdown("**🤖 Claude Response**")
            st.text_area(
                "Claude Response",
                value=claude_response,
                height=200,
                disabled=True,
                key="feedback_claude_display"
            )
        
        # Feedback form
        with st.form("feedback_form"):
            st.markdown("### Your Feedback")
            
            # Overall rating
            overall_rating = st.slider(
                "Overall Quality Rating (1-5):",
                min_value=1,
                max_value=5,
                value=3,
                help="1 = Poor, 5 = Excellent",
                key="feedback_overall_rating"
            )
            
            # Model preference
            preferred_model = st.radio(
                "Which response do you prefer?",
                ["Gemini", "Claude", "Both are good", "Both are poor"],
                key="feedback_preferred_model"
            )
            
            # Detailed quality ratings
            st.markdown("**Detailed Quality Ratings:**")
            col1, col2 = st.columns(2)
            
            with col1:
                accuracy_rating = st.slider(
                    "Accuracy (1-5):",
                    min_value=1,
                    max_value=5,
                    value=3,
                    key="feedback_accuracy"
                )
                relevance_rating = st.slider(
                    "Relevance (1-5):",
                    min_value=1,
                    max_value=5,
                    value=3,
                    key="feedback_relevance"
                )
            
            with col2:
                clarity_rating = st.slider(
                    "Clarity (1-5):",
                    min_value=1,
                    max_value=5,
                    value=3,
                    key="feedback_clarity"
                )
                completeness_rating = st.slider(
                    "Completeness (1-5):",
                    min_value=1,
                    max_value=5,
                    value=3,
                    key="feedback_completeness"
                )
            
            # Comments
            user_comments = st.text_area(
                "Comments (optional):",
                placeholder="What did you like or dislike about the responses?",
                height=100,
                key="feedback_comments"
            )
            
            # Additional notes
            additional_notes = st.text_area(
                "Additional Notes (optional):",
                placeholder="Any specific suggestions for improvement?",
                height=80,
                key="feedback_notes"
            )
            
            # Submit button
            submitted = st.form_submit_button("Submit Feedback", type="primary")
            
            if submitted:
                # Determine selected model from preference
                if preferred_model == "Gemini":
                    selected_model = "gemini"
                elif preferred_model == "Claude":
                    selected_model = "claude"
                else:
                    selected_model = "both" if "good" in preferred_model else "neither"
                
                # Prepare quality ratings
                response_quality = {
                    "accuracy": accuracy_rating,
                    "relevance": relevance_rating,
                    "clarity": clarity_rating,
                    "completeness": completeness_rating
                }
                
                # Submit feedback
                feedback_id = self.feedback_manager.submit_feedback(
                    query=query,
                    gemini_response=gemini_response,
                    claude_response=claude_response,
                    selected_model=selected_model,
                    user_rating=overall_rating,
                    user_comments=user_comments,
                    response_quality=response_quality,
                    additional_notes=additional_notes
                )
                
                st.success(f"✅ Feedback submitted successfully! ID: {feedback_id}")
                st.session_state.feedback_submitted = True
                
                return feedback_id
        
        return None
    
    def render_feedback_dashboard(self):
        """Render feedback dashboard with analytics."""
        st.header("📊 Feedback Dashboard")
        
        # Get feedback summary
        summary = self.feedback_manager.get_feedback_summary()
        
        if summary["total_feedback"] == 0:
            st.info("No feedback data available yet. Submit some feedback to see analytics!")
            return
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Feedback", summary["total_feedback"])
        
        with col2:
            st.metric("Average Rating", f"{summary['average_rating']}/5")
        
        with col3:
            gemini_count = summary["model_preferences"].get("gemini", 0)
            st.metric("Gemini Selections", gemini_count)
        
        with col4:
            claude_count = summary["model_preferences"].get("claude", 0)
            st.metric("Claude Selections", claude_count)
        
        # Model performance analysis
        st.subheader("📈 Model Performance Analysis")
        analysis = self.feedback_manager.get_model_performance_analysis()
        
        if "error" not in analysis:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🤖 Gemini Performance**")
                gemini_data = analysis["gemini"]
                st.metric("Average Rating", f"{gemini_data['average_rating']:.2f}/5")
                st.metric("Total Selections", gemini_data["total_selections"])
                
                # Rating distribution
                st.markdown("**Rating Distribution:**")
                for rating, count in gemini_data["rating_distribution"].items():
                    st.write(f"⭐ {rating}: {count} feedback")
            
            with col2:
                st.markdown("**🤖 Claude Performance**")
                claude_data = analysis["claude"]
                st.metric("Average Rating", f"{claude_data['average_rating']:.2f}/5")
                st.metric("Total Selections", claude_data["total_selections"])
                
                # Rating distribution
                st.markdown("**Rating Distribution:**")
                for rating, count in claude_data["rating_distribution"].items():
                    st.write(f"⭐ {rating}: {count} feedback")
        
        # Recent feedback
        st.subheader("📝 Recent Feedback")
        recent_feedback = summary["recent_feedback"]
        
        for feedback in recent_feedback[:5]:  # Show last 5
            with st.expander(f"Feedback {feedback['feedback_id']} - Rating: {feedback['user_rating']}/5", expanded=False):
                st.write(f"**Query:** {feedback['query']}")
                st.write(f"**Selected Model:** {feedback['selected_model']}")
                st.write(f"**Rating:** {feedback['user_rating']}/5")
                if feedback.get('user_comments'):
                    st.write(f"**Comments:** {feedback['user_comments']}")
                st.write(f"**Timestamp:** {feedback['timestamp']}")
        
        # Export and retraining options
        st.subheader("🔧 Data Management")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Export to CSV"):
                csv_path = self.feedback_manager.export_to_csv()
                if csv_path:
                    st.success(f"Data exported to: {csv_path}")
                else:
                    st.error("No data to export")
        
        with col2:
            if st.button("🔄 Prepare Retraining Data"):
                retraining_data = self.feedback_manager.prepare_retraining_data()
                st.success(f"Retraining data prepared with {retraining_data['metadata']['total_examples']} examples")
                
                # Show retraining data preview
                with st.expander("Retraining Data Preview", expanded=False):
                    st.json(retraining_data["metadata"])
                    st.write(f"Training examples: {len(retraining_data['training_examples'])}")
                    st.write(f"Preference data: {len(retraining_data['preference_data'])}")
        
        with col3:
            if st.button("🗑️ Clear All Feedback", type="secondary"):
                if st.session_state.get('confirm_clear', False):
                    if self.feedback_manager.clear_feedback(confirm=True):
                        st.success("All feedback cleared!")
                        st.session_state.confirm_clear = False
                        st.rerun()
                else:
                    st.session_state.confirm_clear = True
                    st.warning("Click again to confirm clearing all feedback")
    
    def render_retraining_interface(self):
        """Render interface for preparing retraining data."""
        st.header("🔄 Model Retraining Interface")
        
        # Get feedback summary
        summary = self.feedback_manager.get_feedback_summary()
        
        if summary["total_feedback"] == 0:
            st.info("No feedback data available for retraining. Submit some feedback first!")
            return
        
        st.markdown(f"**Total feedback available:** {summary['total_feedback']}")
        
        # Feedback selection
        st.subheader("Select Feedback for Retraining")
        
        # Show feedback list with checkboxes
        selected_feedback = []
        
        for i, feedback in enumerate(summary["recent_feedback"]):
            col1, col2, col3 = st.columns([1, 4, 2])
            
            with col1:
                include = st.checkbox("Include", key=f"include_{i}", label_visibility="collapsed")
                if include:
                    selected_feedback.append(feedback['feedback_id'])
            
            with col2:
                st.write(f"**Query:** {feedback['query'][:100]}...")
                st.write(f"**Model:** {feedback['selected_model']} | **Rating:** {feedback['user_rating']}/5")
            
            with col3:
                st.write(feedback['timestamp'][:10])
        
        # Retraining options
        st.subheader("Retraining Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            retraining_format = st.selectbox(
                "Output Format:",
                ["JSON", "CSV", "JSONL"],
                help="Format for the retraining data"
            )
        
        with col2:
            include_quality_metrics = st.checkbox(
                "Include Quality Metrics",
                value=True,
                help="Include detailed quality ratings in retraining data"
            )
        
        # Generate retraining data
        if st.button("🔄 Generate Retraining Data", type="primary"):
            if selected_feedback:
                retraining_data = self.feedback_manager.prepare_retraining_data(selected_feedback)
                
                st.success(f"Retraining data generated with {len(selected_feedback)} feedback entries!")
                
                # Display retraining data
                with st.expander("Retraining Data", expanded=True):
                    st.json(retraining_data)
                
                # Download option
                st.download_button(
                    label="📥 Download Retraining Data",
                    data=json.dumps(retraining_data, indent=2),
                    file_name=f"retraining_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            else:
                st.warning("Please select at least one feedback entry for retraining.")
