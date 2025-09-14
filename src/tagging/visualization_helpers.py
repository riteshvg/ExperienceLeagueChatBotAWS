"""
Data Visualization Helpers for Tagging Analytics

This module provides visualization utilities for the tagging analytics system,
including chart generation and data formatting for Streamlit integration.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

# Optional imports for visualization
try:
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    # Create dummy classes for when plotly is not available
    class go:
        class Figure:
            def __init__(self, *args, **kwargs):
                pass
        class Bar:
            def __init__(self, *args, **kwargs):
                pass
        class Pie:
            def __init__(self, *args, **kwargs):
                pass
        class Scatter:
            def __init__(self, *args, **kwargs):
                pass
        class Heatmap:
            def __init__(self, *args, **kwargs):
                pass
        class Indicator:
            def __init__(self, *args, **kwargs):
                pass
    
    class pd:
        @staticmethod
        def DataFrame(data=None):
            return data or []
    
    def make_subplots(*args, **kwargs):
        return go.Figure()

logger = logging.getLogger(__name__)

class TaggingVisualization:
    """Visualization helpers for tagging analytics."""
    
    def __init__(self):
        """Initialize visualization helpers."""
        self.logger = logging.getLogger(__name__)
    
    def create_trending_topics_chart(self, trending_data: List[Dict[str, Any]], 
                                   title: str = "Trending Topics") -> go.Figure:
        """
        Create a bar chart for trending topics.
        
        Args:
            trending_data: List of trending topic data
            title: Chart title
            
        Returns:
            Plotly figure object
        """
        try:
            if not PLOTLY_AVAILABLE:
                self.logger.warning("Plotly not available, returning empty chart")
                return self._create_empty_chart("Plotly not available for visualization")
            
            if not trending_data:
                return self._create_empty_chart("No trending data available")
            
            # Prepare data
            topics = [item['topic'] for item in trending_data]
            counts = [item['count'] for item in trending_data]
            growth_rates = [item['growth_rate'] for item in trending_data]
            
            # Create bar chart
            fig = go.Figure(data=[
                go.Bar(
                    x=topics,
                    y=counts,
                    text=[f"{rate:.1f}%" for rate in growth_rates],
                    textposition='auto',
                    marker_color=['green' if rate > 0 else 'red' for rate in growth_rates]
                )
            ])
            
            fig.update_layout(
                title=title,
                xaxis_title="Topics",
                yaxis_title="Question Count",
                xaxis_tickangle=-45,
                height=400
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating trending topics chart: {e}")
            return self._create_error_chart(str(e))
    
    def create_product_correlation_heatmap(self, correlation_data: List[Dict[str, Any]], 
                                         title: str = "Product Correlations") -> go.Figure:
        """
        Create a heatmap for product correlations.
        
        Args:
            correlation_data: List of product correlation data
            title: Chart title
            
        Returns:
            Plotly figure object
        """
        try:
            if not PLOTLY_AVAILABLE:
                self.logger.warning("Plotly not available, returning empty chart")
                return self._create_empty_chart("Plotly not available for visualization")
            
            if not correlation_data:
                return self._create_empty_chart("No correlation data available")
            
            # Prepare data for heatmap
            products = set()
            for item in correlation_data:
                products.add(item['product1'])
                products.add(item['product2'])
            
            products = sorted(list(products))
            correlation_matrix = [[0.0 for _ in products] for _ in products]
            
            # Fill correlation matrix
            for item in correlation_data:
                i = products.index(item['product1'])
                j = products.index(item['product2'])
                correlation_matrix[i][j] = item['correlation_score']
                correlation_matrix[j][i] = item['correlation_score']
            
            # Create heatmap
            fig = go.Figure(data=go.Heatmap(
                z=correlation_matrix,
                x=products,
                y=products,
                colorscale='Blues',
                showscale=True
            ))
            
            fig.update_layout(
                title=title,
                xaxis_title="Products",
                yaxis_title="Products",
                height=500
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating correlation heatmap: {e}")
            return self._create_error_chart(str(e))
    
    def create_confidence_distribution_chart(self, accuracy_data: Dict[str, Any], 
                                           title: str = "Confidence Distribution") -> go.Figure:
        """
        Create a pie chart for confidence distribution.
        
        Args:
            accuracy_data: Tagging accuracy data
            title: Chart title
            
        Returns:
            Plotly figure object
        """
        try:
            labels = ['High Confidence', 'Medium Confidence', 'Low Confidence']
            values = [
                accuracy_data.get('high_confidence_count', 0),
                accuracy_data.get('medium_confidence_count', 0),
                accuracy_data.get('low_confidence_count', 0)
            ]
            colors = ['#2E8B57', '#FFD700', '#DC143C']
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                marker_colors=colors,
                textinfo='label+percent',
                textposition='auto'
            )])
            
            fig.update_layout(
                title=title,
                height=400
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating confidence distribution chart: {e}")
            return self._create_error_chart(str(e))
    
    def create_time_series_chart(self, time_series_data: Dict[str, List[Dict[str, Any]]], 
                               title: str = "Question Volume Over Time") -> go.Figure:
        """
        Create a time series chart for question volume.
        
        Args:
            time_series_data: Time series data
            title: Chart title
            
        Returns:
            Plotly figure object
        """
        try:
            question_volume = time_series_data.get('question_volume', [])
            if not question_volume:
                return self._create_empty_chart("No time series data available")
            
            # Prepare data
            times = [item['time'] for item in question_volume]
            counts = [item['count'] for item in question_volume]
            
            fig = go.Figure(data=[
                go.Scatter(
                    x=times,
                    y=counts,
                    mode='lines+markers',
                    name='Question Volume',
                    line=dict(color='#1f77b4', width=2)
                )
            ])
            
            fig.update_layout(
                title=title,
                xaxis_title="Time",
                yaxis_title="Question Count",
                height=400
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating time series chart: {e}")
            return self._create_error_chart(str(e))
    
    def create_user_segmentation_chart(self, user_behavior_data: Dict[str, Any], 
                                     title: str = "User Segmentation") -> go.Figure:
        """
        Create a pie chart for user segmentation.
        
        Args:
            user_behavior_data: User behavior analysis data
            title: Chart title
            
        Returns:
            Plotly figure object
        """
        try:
            segmentation = user_behavior_data.get('segmentation', {})
            if not segmentation:
                return self._create_empty_chart("No user segmentation data available")
            
            labels = ['Power Users', 'Active Users', 'Casual Users']
            values = [
                segmentation.get('power_users', 0),
                segmentation.get('active_users', 0),
                segmentation.get('casual_users', 0)
            ]
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                marker_colors=colors,
                textinfo='label+percent+value',
                textposition='auto'
            )])
            
            fig.update_layout(
                title=title,
                height=400
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating user segmentation chart: {e}")
            return self._create_error_chart(str(e))
    
    def create_performance_metrics_dashboard(self, performance_data: Dict[str, Any]) -> go.Figure:
        """
        Create a dashboard with multiple performance metrics.
        
        Args:
            performance_data: Performance metrics data
            
        Returns:
            Plotly figure object
        """
        try:
            # Create subplots
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Success Rate', 'Error Rate', 'Bedrock Usage', 'Cost per Question'),
                specs=[[{"type": "indicator"}, {"type": "indicator"}],
                       [{"type": "indicator"}, {"type": "indicator"}]]
            )
            
            # Success rate gauge
            fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=performance_data.get('success_rate', 0) * 100,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Success Rate (%)"},
                gauge={'axis': {'range': [None, 100]},
                       'bar': {'color': "darkblue"},
                       'steps': [{'range': [0, 50], 'color': "lightgray"},
                                {'range': [50, 80], 'color': "yellow"},
                                {'range': [80, 100], 'color': "green"}]}
            ), row=1, col=1)
            
            # Error rate gauge
            fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=performance_data.get('error_rate', 0) * 100,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Error Rate (%)"},
                gauge={'axis': {'range': [None, 100]},
                       'bar': {'color': "darkred"},
                       'steps': [{'range': [0, 20], 'color': "green"},
                                {'range': [20, 50], 'color': "yellow"},
                                {'range': [50, 100], 'color': "red"}]}
            ), row=1, col=2)
            
            # Bedrock usage gauge
            fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=performance_data.get('bedrock_usage_rate', 0) * 100,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Bedrock Usage (%)"},
                gauge={'axis': {'range': [None, 100]},
                       'bar': {'color': "purple"}}
            ), row=2, col=1)
            
            # Cost per question
            fig.add_trace(go.Indicator(
                mode="number",
                value=performance_data.get('cost_per_question', 0),
                title={'text': "Cost per Question ($)"},
                number={'prefix': "$", 'valueformat': ".4f"}
            ), row=2, col=2)
            
            fig.update_layout(height=600, title_text="Performance Metrics Dashboard")
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating performance dashboard: {e}")
            return self._create_error_chart(str(e))
    
    def create_analytics_summary_table(self, analytics_data: Dict[str, Any]) -> pd.DataFrame:
        """
        Create a summary table for analytics data.
        
        Args:
            analytics_data: Complete analytics data
            
        Returns:
            Pandas DataFrame with summary information
        """
        try:
            summary_data = []
            
            # Trending topics summary
            trending_topics = analytics_data.get('trending_topics', [])
            if trending_topics:
                top_topic = max(trending_topics, key=lambda x: x['growth_rate'])
                summary_data.append({
                    'Metric': 'Top Trending Topic',
                    'Value': f"{top_topic['topic']} (+{top_topic['growth_rate']:.1f}%)",
                    'Category': 'Trends'
                })
            
            # Accuracy summary
            accuracy = analytics_data.get('tagging_accuracy', {})
            if accuracy:
                summary_data.append({
                    'Metric': 'Tagging Accuracy',
                    'Value': f"{accuracy.get('accuracy_rate', 0):.1%}",
                    'Category': 'Quality'
                })
                summary_data.append({
                    'Metric': 'Average Confidence',
                    'Value': f"{accuracy.get('avg_confidence', 0):.3f}",
                    'Category': 'Quality'
                })
            
            # Performance summary
            performance = analytics_data.get('performance_metrics', {})
            if performance:
                summary_data.append({
                    'Metric': 'Success Rate',
                    'Value': f"{performance.get('success_rate', 0):.1%}",
                    'Category': 'Performance'
                })
                summary_data.append({
                    'Metric': 'Cost per Question',
                    'Value': f"${performance.get('cost_per_question', 0):.4f}",
                    'Category': 'Performance'
                })
            
            # User behavior summary
            user_behavior = analytics_data.get('user_behavior', {})
            if user_behavior:
                summary_data.append({
                    'Metric': 'Total Users',
                    'Value': f"{user_behavior.get('segmentation', {}).get('total_users', 0)}",
                    'Category': 'Users'
                })
                summary_data.append({
                    'Metric': 'Avg Questions per User',
                    'Value': f"{user_behavior.get('avg_questions_per_user', 0):.1f}",
                    'Category': 'Users'
                })
            
            return pd.DataFrame(summary_data)
            
        except Exception as e:
            self.logger.error(f"Error creating analytics summary table: {e}")
            return pd.DataFrame()
    
    def _create_empty_chart(self, message: str) -> go.Figure:
        """Create an empty chart with a message."""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            xaxis={'visible': False},
            yaxis={'visible': False},
            height=400
        )
        return fig
    
    def _create_error_chart(self, error_message: str) -> go.Figure:
        """Create an error chart with error message."""
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error: {error_message}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="red")
        )
        fig.update_layout(
            xaxis={'visible': False},
            yaxis={'visible': False},
            height=400
        )
        return fig

# Example usage
if __name__ == "__main__":
    # Test visualization helpers
    viz = TaggingVisualization()
    
    # Sample data
    trending_data = [
        {"topic": "adobe_analytics", "count": 25, "growth_rate": 15.5},
        {"topic": "implementation", "count": 20, "growth_rate": 8.2},
        {"topic": "troubleshooting", "count": 18, "growth_rate": -5.1}
    ]
    
    accuracy_data = {
        "high_confidence_count": 45,
        "medium_confidence_count": 30,
        "low_confidence_count": 25
    }
    
    # Test charts
    print("Testing visualization helpers...")
    
    # Trending topics chart
    fig1 = viz.create_trending_topics_chart(trending_data)
    print("✅ Trending topics chart created")
    
    # Confidence distribution chart
    fig2 = viz.create_confidence_distribution_chart(accuracy_data)
    print("✅ Confidence distribution chart created")
    
    print("✅ Visualization helpers test completed")
