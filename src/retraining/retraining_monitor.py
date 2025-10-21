"""
Retraining monitoring dashboard for real-time tracking of model retraining jobs.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime
import json
import os

class RetrainingMonitor:
    """Real-time monitoring dashboard for retraining jobs."""
    
    def __init__(self):
        """Initialize retraining monitor."""
        pass
    
    def render_cloud_credentials_status(self, pipeline):
        """Render cloud credentials and connectivity status."""
        st.subheader("☁️ Cloud Credentials Status")
        
        creds_status = pipeline.get_cloud_credentials_status()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### AWS Configuration")
            aws_status = creds_status['aws']
            
            if aws_status['available']:
                st.success("✅ AWS Bedrock Available")
                st.info(f"**Region:** {aws_status['region']}")
                st.info(f"**S3 Bucket:** {aws_status['bucket']}")
                
                if aws_status['s3_available']:
                    st.success("✅ S3 Client Available")
                else:
                    st.error("❌ S3 Client Not Available")
            else:
                st.error("❌ AWS Not Available")
                st.warning("Check AWS credentials in environment variables")
        
        with col2:
            st.markdown("### GCP Configuration")
            gcp_status = creds_status['gcp']
            
            if gcp_status['available']:
                st.success("✅ Google Cloud Available")
                st.info(f"**Project ID:** {gcp_status['project_id']}")
                st.info(f"**GCS Bucket:** {gcp_status['bucket']}")
                
                if gcp_status['gcs_available']:
                    st.success("✅ GCS Client Available")
                else:
                    st.error("❌ GCS Client Not Available")
            else:
                st.error("❌ GCP Not Available")
                st.warning("Check GCP credentials in environment variables")
    
    def render_retraining_jobs_table(self, pipeline):
        """Render table of retraining jobs."""
        st.subheader("🔄 Retraining Jobs History")
        
        history = pipeline.get_retraining_history()
        
        if not history:
            st.info("No retraining jobs found. Submit feedback to trigger retraining.")
            return
        
        # Convert to DataFrame for better display
        df_data = []
        for job in history:
            df_data.append({
                'Job Name': job.get('job_name', 'N/A'),
                'Model Type': job.get('model_type', 'N/A').title(),
                'Status': job.get('status', 'N/A').title(),
                'Training Examples': job.get('training_examples', 0),
                'Started': job.get('timestamp', 'N/A'),
                'S3 Location': job.get('s3_location', 'N/A'),
                'GCS Location': job.get('gcs_location', 'N/A'),
                'Job ARN': job.get('job_arn', 'N/A'),
                'Model Resource': job.get('model_resource_name', 'N/A')
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
        
        # Show job details in expandable sections
        for i, job in enumerate(history):
            with st.expander(f"Job {i+1}: {job.get('job_name', 'Unknown')}", expanded=False):
                st.json(job)
    
    def render_training_data_history(self, pipeline):
        """Render training data upload history."""
        st.subheader("📊 Training Data History")
        
        data_history = pipeline.get_training_data_history()
        
        if not data_history:
            st.info("No training data uploads found.")
            return
        
        # Convert to DataFrame
        df_data = []
        for data in data_history:
            df_data.append({
                'Model Type': data.get('model_type', 'N/A').title(),
                'Training Examples': data.get('training_examples', 0),
                'S3 Location': data.get('s3_location', 'N/A'),
                'GCS Location': data.get('gcs_location', 'N/A'),
                'Upload Time': data.get('timestamp', 'N/A')
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
    
    def render_local_training_data(self, pipeline):
        """Render locally saved training data files."""
        st.subheader("💾 Local Training Data Files")
        
        local_path = pipeline.config.get('local_data_path', './training_data')
        
        if not os.path.exists(local_path):
            st.info("No local training data directory found.")
            return
        
        # List files in training data directory
        files = [f for f in os.listdir(local_path) if f.endswith('.jsonl')]
        
        if not files:
            st.info("No training data files found locally.")
            return
        
        st.info(f"Found {len(files)} training data files in {local_path}")
        
        for file in files:
            file_path = os.path.join(local_path, file)
            file_size = os.path.getsize(file_path)
            
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"📄 {file}")
            
            with col2:
                st.write(f"{file_size:,} bytes")
            
            with col3:
                if st.button(f"View", key=f"view_{file}"):
                    with open(file_path, 'r') as f:
                        content = f.read()
                    st.text_area(f"Content of {file}", content, height=200)
    
    def render_real_time_metrics(self, pipeline):
        """Render real-time metrics and statistics."""
        st.subheader("📈 Real-Time Metrics")
        
        status = pipeline.get_pipeline_status()
        history = pipeline.get_retraining_history()
        data_history = pipeline.get_training_data_history()
        
        # Calculate metrics
        total_jobs = len(history)
        claude_jobs = len([j for j in history if j.get('model_type') == 'claude'])
        gemini_jobs = len([j for j in history if j.get('model_type') == 'gemini'])
        total_training_examples = sum([j.get('training_examples', 0) for j in history])
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Jobs", total_jobs)
        
        with col2:
            st.metric("Claude Jobs", claude_jobs)
        
        with col3:
            st.metric("Gemini Jobs", gemini_jobs)
        
        with col4:
            st.metric("Total Examples", total_training_examples)
        
        # Pipeline status
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Queue Size", f"{status['queue_size']}/{status['retraining_threshold']}")
        
        with col2:
            st.metric("AWS Available", "✅" if status['aws_available'] else "❌")
        
        # Show recent activity
        if history:
            st.subheader("🕒 Recent Activity")
            recent_jobs = sorted(history, key=lambda x: x.get('timestamp', ''), reverse=True)[:3]
            
            for job in recent_jobs:
                st.write(f"• **{job.get('model_type', 'Unknown').title()}** job: {job.get('job_name', 'Unknown')} - {job.get('status', 'Unknown')}")
    
    def render_monitoring_dashboard(self, pipeline):
        """Render the complete monitoring dashboard."""
        st.title("🔍 Retraining Monitor")
        st.markdown("Real-time monitoring of model retraining jobs and data")
        st.markdown("---")
        
        # Cloud credentials status
        self.render_cloud_credentials_status(pipeline)
        st.markdown("---")
        
        # Real-time metrics
        self.render_real_time_metrics(pipeline)
        st.markdown("---")
        
        # Retraining jobs table
        self.render_retraining_jobs_table(pipeline)
        st.markdown("---")
        
        # Training data history
        self.render_training_data_history(pipeline)
        st.markdown("---")
        
        # Local training data files
        self.render_local_training_data(pipeline)




