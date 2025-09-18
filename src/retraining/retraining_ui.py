"""
Retraining UI for hybrid model feedback data.
Provides interface for data preparation and retraining management.
"""

import streamlit as st
import json
import pandas as pd
from typing import Dict, Any
from pathlib import Path
from .retraining_processor import RetrainingProcessor

class RetrainingUI:
    """UI components for model retraining management."""
    
    def __init__(self):
        """Initialize retraining UI."""
        self.processor = RetrainingProcessor()
    
    def render_retraining_interface(self):
        """Render the main retraining interface."""
        st.header("🔄 Model Retraining")
        st.markdown("Prepare feedback data for model retraining and improvement")
        
        # Check if feedback data exists
        feedback_file = Path("./feedback_data/feedback.json")
        if not feedback_file.exists():
            st.warning("No feedback data found. Please collect some feedback first.")
            return
        
        # Data preparation section
        st.subheader("📊 Data Preparation")
        
        col1, col2 = st.columns(2)
        
        with col1:
            min_rating = st.slider(
                "Minimum Rating:",
                min_value=1,
                max_value=5,
                value=4,
                help="Only include feedback with this rating or higher"
            )
        
        with col2:
            min_quality = st.slider(
                "Minimum Quality Score:",
                min_value=1,
                max_value=5,
                value=4,
                help="Only include feedback with this quality score or higher"
            )
        
        if st.button("🔍 Analyze Feedback Data", type="primary"):
            with st.spinner("Analyzing feedback data..."):
                trends = self.processor.analyze_feedback_trends()
                
                if "error" in trends:
                    st.error(trends["error"])
                else:
                    # Display analysis
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Feedback", trends["total_feedback"])
                    
                    with col2:
                        st.metric("Average Rating", f"{trends['average_rating']:.2f}/5")
                    
                    with col3:
                        gemini_count = trends["model_preferences"].get("gemini", 0)
                        st.metric("Gemini Selections", gemini_count)
                    
                    with col4:
                        claude_count = trends["model_preferences"].get("claude", 0)
                        st.metric("Claude Selections", claude_count)
                    
                    # Quality scores
                    if "quality_scores" in trends:
                        st.subheader("📈 Quality Score Analysis")
                        quality_df = st.dataframe(
                            pd.DataFrame(trends["quality_scores"]).T,
                            use_container_width=True
                        )
        
        st.markdown("---")
        
        # Training data preparation
        st.subheader("🎯 Prepare Training Data")
        
        if st.button("📦 Prepare Training Data", type="primary"):
            with st.spinner("Preparing training data..."):
                training_data = self.processor.prepare_training_data(
                    min_rating=min_rating,
                    min_quality=min_quality
                )
                
                if training_data:
                    st.success("✅ Training data prepared successfully!")
                    
                    # Show summary
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Gemini Examples", len(training_data.get("gemini", [])))
                    
                    with col2:
                        st.metric("Claude Examples", len(training_data.get("claude", [])))
                    
                    with col3:
                        st.metric("Preference Pairs", len(training_data.get("preference_data", [])))
                    
                    # Show sample data
                    with st.expander("Sample Training Data", expanded=False):
                        st.json(training_data["metadata"])
                        
                        if training_data.get("gemini"):
                            st.write("**Sample Gemini Training Example:**")
                            st.json(training_data["gemini"][0])
                        
                        if training_data.get("claude"):
                            st.write("**Sample Claude Training Example:**")
                            st.json(training_data["claude"][0])
                else:
                    st.error("❌ Failed to prepare training data")
        
        st.markdown("---")
        
        # Retraining scripts
        st.subheader("🚀 Generate Retraining Scripts")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🤖 Generate Claude Script"):
                with st.spinner("Generating Claude retraining script..."):
                    script_path = self.processor.generate_retraining_script('claude')
                    st.success(f"✅ Claude retraining script generated: {script_path}")
                    
                    # Show script content
                    with open(script_path, 'r') as f:
                        script_content = f.read()
                    
                    st.code(script_content, language='python')
        
        with col2:
            if st.button("🤖 Generate Gemini Script"):
                with st.spinner("Generating Gemini retraining script..."):
                    script_path = self.processor.generate_retraining_script('gemini')
                    st.success(f"✅ Gemini retraining script generated: {script_path}")
                    
                    # Show script content
                    with open(script_path, 'r') as f:
                        script_content = f.read()
                    
                    st.code(script_content, language='python')
        
        st.markdown("---")
        
        # Evaluation dataset
        st.subheader("📊 Create Evaluation Dataset")
        
        test_ratio = st.slider(
            "Test Data Ratio:",
            min_value=0.1,
            max_value=0.5,
            value=0.2,
            step=0.1,
            help="Percentage of data to use for testing"
        )
        
        if st.button("📊 Create Evaluation Dataset"):
            with st.spinner("Creating evaluation dataset..."):
                eval_data = self.processor.create_evaluation_dataset(test_ratio=test_ratio)
                
                if eval_data:
                    st.success("✅ Evaluation dataset created!")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Training Examples", eval_data["metadata"]["train_count"])
                    
                    with col2:
                        st.metric("Test Examples", eval_data["metadata"]["test_count"])
                    
                    # Show sample test data
                    with st.expander("Sample Test Data", expanded=False):
                        if eval_data["test"]:
                            st.json(eval_data["test"][0])
                else:
                    st.error("❌ Failed to create evaluation dataset")
        
        st.markdown("---")
        
        # Retraining instructions
        st.subheader("📋 Retraining Instructions")
        
        with st.expander("How to Use the Generated Scripts", expanded=True):
            st.markdown("""
            ### Claude Retraining (AWS Bedrock)
            
            1. **Upload Training Data to S3:**
               ```bash
               aws s3 cp ./feedback_data/training_data/claude_training_*.jsonl s3://your-bucket/training-data.jsonl
               ```
            
            2. **Set up IAM Role:**
               - Create a role with Bedrock model customization permissions
               - Update the role ARN in the script
            
            3. **Run the Script:**
               ```bash
               python retrain_claude_*.py
               ```
            
            4. **Monitor Progress:**
               - Check AWS Bedrock console for job status
               - Training typically takes 2-6 hours
            
            ### Gemini Retraining (Google AI Platform)
            
            1. **Set up Google Cloud:**
               ```bash
               gcloud auth login
               gcloud config set project YOUR_PROJECT_ID
               ```
            
            2. **Upload Training Data:**
               ```bash
               gsutil cp ./feedback_data/training_data/gemini_training_*.jsonl gs://your-bucket/training-data.jsonl
               ```
            
            3. **Run the Script:**
               ```bash
               python retrain_gemini_*.py
               ```
            
            ### Custom Retraining
            
            For custom retraining approaches:
            
            1. **Use the prepared JSONL files** in your preferred framework
            2. **Implement your own training loop** using the feedback data
            3. **Consider using Hugging Face Transformers** for open-source models
            4. **Use the preference data** for RLHF-style training
            """)
        
        # Best practices
        with st.expander("Best Practices", expanded=False):
            st.markdown("""
            ### Data Quality
            - Start with at least 100-500 high-quality examples
            - Filter out low-quality feedback (rating < 4)
            - Ensure diverse query types and response patterns
            
            ### Training Strategy
            - Use a small learning rate (1e-5 to 1e-6)
            - Train for 3-5 epochs maximum
            - Use early stopping to prevent overfitting
            - Validate on held-out test data
            
            ### Evaluation
            - Compare retrained model with original
            - Use A/B testing for gradual rollout
            - Monitor user satisfaction metrics
            - Collect new feedback on retrained models
            
            ### Iteration
            - Retrain regularly with new feedback
            - Track performance improvements
            - Identify areas for further improvement
            - Maintain model versioning
            """)
