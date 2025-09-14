"""
Simple Visualization Helpers for Tagging Analytics

This module provides basic visualization utilities without external dependencies,
suitable for console output and basic data formatting.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from collections import Counter

logger = logging.getLogger(__name__)

class SimpleTaggingVisualization:
    """Simple visualization helpers for tagging analytics."""
    
    def __init__(self):
        """Initialize visualization helpers."""
        self.logger = logging.getLogger(__name__)
    
    def format_trending_topics_table(self, trending_data: List[Dict[str, Any]], 
                                   limit: int = 10) -> str:
        """
        Format trending topics as a table.
        
        Args:
            trending_data: List of trending topic data
            limit: Maximum number of topics to show
            
        Returns:
            Formatted table string
        """
        try:
            if not trending_data:
                return "No trending data available"
            
            # Sort by growth rate
            sorted_data = sorted(trending_data, key=lambda x: x.get('growth_rate', 0), reverse=True)
            
            # Create table
            table = "Trending Topics (Top {})\n".format(min(limit, len(sorted_data)))
            table += "=" * 60 + "\n"
            table += f"{'Topic':<25} {'Count':<8} {'Growth':<10} {'Confidence':<12}\n"
            table += "-" * 60 + "\n"
            
            for item in sorted_data[:limit]:
                topic = item.get('topic', 'Unknown')[:24]
                count = item.get('count', 0)
                growth = item.get('growth_rate', 0)
                confidence = item.get('confidence', 0)
                
                growth_str = f"+{growth:.1f}%" if growth > 0 else f"{growth:.1f}%"
                confidence_str = f"{confidence:.2f}"
                
                table += f"{topic:<25} {count:<8} {growth_str:<10} {confidence_str:<12}\n"
            
            return table
            
        except Exception as e:
            self.logger.error(f"Error formatting trending topics table: {e}")
            return f"Error: {e}"
    
    def format_product_correlations_table(self, correlation_data: List[Dict[str, Any]], 
                                        limit: int = 10) -> str:
        """
        Format product correlations as a table.
        
        Args:
            correlation_data: List of product correlation data
            limit: Maximum number of correlations to show
            
        Returns:
            Formatted table string
        """
        try:
            if not correlation_data:
                return "No correlation data available"
            
            # Sort by correlation score
            sorted_data = sorted(correlation_data, key=lambda x: x.get('correlation_score', 0), reverse=True)
            
            # Create table
            table = "Product Correlations (Top {})\n".format(min(limit, len(sorted_data)))
            table += "=" * 70 + "\n"
            table += f"{'Product 1':<20} {'Product 2':<20} {'Co-occur':<8} {'Score':<8} {'Confidence':<12}\n"
            table += "-" * 70 + "\n"
            
            for item in sorted_data[:limit]:
                product1 = item.get('product1', 'Unknown')[:19]
                product2 = item.get('product2', 'Unknown')[:19]
                co_occurrence = item.get('co_occurrence', 0)
                score = item.get('correlation_score', 0)
                confidence = item.get('confidence', 0)
                
                table += f"{product1:<20} {product2:<20} {co_occurrence:<8} {score:<8.3f} {confidence:<12.3f}\n"
            
            return table
            
        except Exception as e:
            self.logger.error(f"Error formatting product correlations table: {e}")
            return f"Error: {e}"
    
    def format_confidence_distribution(self, accuracy_data: Dict[str, Any]) -> str:
        """
        Format confidence distribution as a summary.
        
        Args:
            accuracy_data: Tagging accuracy data
            
        Returns:
            Formatted summary string
        """
        try:
            total = accuracy_data.get('total_questions', 0)
            high = accuracy_data.get('high_confidence_count', 0)
            medium = accuracy_data.get('medium_confidence_count', 0)
            low = accuracy_data.get('low_confidence_count', 0)
            avg_confidence = accuracy_data.get('avg_confidence', 0)
            accuracy_rate = accuracy_data.get('accuracy_rate', 0)
            
            if total == 0:
                return "No confidence data available"
            
            # Calculate percentages
            high_pct = (high / total) * 100
            medium_pct = (medium / total) * 100
            low_pct = (low / total) * 100
            
            summary = "Confidence Distribution\n"
            summary += "=" * 40 + "\n"
            summary += f"Total Questions: {total}\n"
            summary += f"High Confidence: {high} ({high_pct:.1f}%)\n"
            summary += f"Medium Confidence: {medium} ({medium_pct:.1f}%)\n"
            summary += f"Low Confidence: {low} ({low_pct:.1f}%)\n"
            summary += f"Average Confidence: {avg_confidence:.3f}\n"
            summary += f"Accuracy Rate: {accuracy_rate:.1%}\n"
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error formatting confidence distribution: {e}")
            return f"Error: {e}"
    
    def format_performance_metrics(self, performance_data: Dict[str, Any]) -> str:
        """
        Format performance metrics as a summary.
        
        Args:
            performance_data: Performance metrics data
            
        Returns:
            Formatted summary string
        """
        try:
            total_questions = performance_data.get('total_questions_processed', 0)
            success_rate = performance_data.get('success_rate', 0)
            error_rate = performance_data.get('error_rate', 0)
            bedrock_usage = performance_data.get('bedrock_usage_rate', 0)
            cost_per_question = performance_data.get('cost_per_question', 0)
            avg_processing_time = performance_data.get('avg_processing_time', 0)
            
            summary = "Performance Metrics\n"
            summary += "=" * 40 + "\n"
            summary += f"Total Questions Processed: {total_questions}\n"
            summary += f"Success Rate: {success_rate:.1%}\n"
            summary += f"Error Rate: {error_rate:.1%}\n"
            summary += f"Bedrock Usage Rate: {bedrock_usage:.1%}\n"
            summary += f"Cost per Question: ${cost_per_question:.4f}\n"
            summary += f"Avg Processing Time: {avg_processing_time:.3f}s\n"
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error formatting performance metrics: {e}")
            return f"Error: {e}"
    
    def format_user_segmentation(self, user_behavior_data: Dict[str, Any]) -> str:
        """
        Format user segmentation as a summary.
        
        Args:
            user_behavior_data: User behavior analysis data
            
        Returns:
            Formatted summary string
        """
        try:
            segmentation = user_behavior_data.get('segmentation', {})
            total_users = segmentation.get('total_users', 0)
            power_users = segmentation.get('power_users', 0)
            active_users = segmentation.get('active_users', 0)
            casual_users = segmentation.get('casual_users', 0)
            avg_questions = user_behavior_data.get('avg_questions_per_user', 0)
            avg_tenure = user_behavior_data.get('avg_tenure_days', 0)
            
            if total_users == 0:
                return "No user data available"
            
            # Calculate percentages
            power_pct = (power_users / total_users) * 100
            active_pct = (active_users / total_users) * 100
            casual_pct = (casual_users / total_users) * 100
            
            summary = "User Segmentation\n"
            summary += "=" * 40 + "\n"
            summary += f"Total Users: {total_users}\n"
            summary += f"Power Users: {power_users} ({power_pct:.1f}%)\n"
            summary += f"Active Users: {active_users} ({active_pct:.1f}%)\n"
            summary += f"Casual Users: {casual_users} ({casual_pct:.1f}%)\n"
            summary += f"Avg Questions per User: {avg_questions:.1f}\n"
            summary += f"Avg Tenure: {avg_tenure:.1f} days\n"
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error formatting user segmentation: {e}")
            return f"Error: {e}"
    
    def format_time_series_summary(self, time_series_data: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Format time series data as a summary.
        
        Args:
            time_series_data: Time series analysis data
            
        Returns:
            Formatted summary string
        """
        try:
            question_volume = time_series_data.get('question_volume', [])
            confidence_trend = time_series_data.get('confidence_trend', [])
            product_usage = time_series_data.get('product_usage', {})
            
            if not question_volume:
                return "No time series data available"
            
            # Calculate summary statistics
            total_questions = sum(item.get('count', 0) for item in question_volume)
            avg_daily = total_questions / len(question_volume) if question_volume else 0
            
            # Get latest period
            latest_period = question_volume[-1] if question_volume else {}
            latest_count = latest_period.get('count', 0)
            latest_time = latest_period.get('time', 'Unknown')
            
            # Calculate confidence trend
            avg_confidence = 0
            if confidence_trend:
                confidences = [item.get('confidence', 0) for item in confidence_trend if item.get('confidence')]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            summary = "Time Series Summary\n"
            summary += "=" * 40 + "\n"
            summary += f"Total Questions: {total_questions}\n"
            summary += f"Average Daily: {avg_daily:.1f}\n"
            summary += f"Latest Period: {latest_time} ({latest_count} questions)\n"
            summary += f"Average Confidence: {avg_confidence:.3f}\n"
            summary += f"Data Points: {len(question_volume)}\n"
            
            # Top products
            if product_usage:
                product_totals = {}
                for product, usage_data in product_usage.items():
                    product_totals[product] = sum(item.get('count', 0) for item in usage_data)
                
                top_products = sorted(product_totals.items(), key=lambda x: x[1], reverse=True)[:5]
                summary += "\nTop Products:\n"
                for product, count in top_products:
                    summary += f"  {product}: {count} questions\n"
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error formatting time series summary: {e}")
            return f"Error: {e}"
    
    def create_analytics_report(self, analytics_data: Dict[str, Any]) -> str:
        """
        Create a comprehensive analytics report.
        
        Args:
            analytics_data: Complete analytics data
            
        Returns:
            Formatted report string
        """
        try:
            report = "TAGGING ANALYTICS REPORT\n"
            report += "=" * 50 + "\n"
            report += f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
            
            # Trending topics
            trending_data = analytics_data.get('trending_topics', [])
            if trending_data:
                report += self.format_trending_topics_table(trending_data, limit=5) + "\n\n"
            
            # Product correlations
            correlation_data = analytics_data.get('product_correlations', [])
            if correlation_data:
                report += self.format_product_correlations_table(correlation_data, limit=5) + "\n\n"
            
            # Confidence distribution
            accuracy_data = analytics_data.get('tagging_accuracy', {})
            if accuracy_data:
                report += self.format_confidence_distribution(accuracy_data) + "\n\n"
            
            # Performance metrics
            performance_data = analytics_data.get('performance_metrics', {})
            if performance_data:
                report += self.format_performance_metrics(performance_data) + "\n\n"
            
            # User segmentation
            user_behavior_data = analytics_data.get('user_behavior', {})
            if user_behavior_data:
                report += self.format_user_segmentation(user_behavior_data) + "\n\n"
            
            # Time series
            time_series_data = analytics_data.get('time_series', {})
            if time_series_data:
                report += self.format_time_series_summary(time_series_data) + "\n\n"
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error creating analytics report: {e}")
            return f"Error creating report: {e}"

# Example usage
if __name__ == "__main__":
    # Test simple visualization
    viz = SimpleTaggingVisualization()
    
    # Sample data
    trending_data = [
        {"topic": "adobe_analytics", "count": 25, "growth_rate": 15.5, "confidence": 0.8},
        {"topic": "implementation", "count": 20, "growth_rate": 8.2, "confidence": 0.7},
        {"topic": "troubleshooting", "count": 18, "growth_rate": -5.1, "confidence": 0.6}
    ]
    
    accuracy_data = {
        "total_questions": 100,
        "high_confidence_count": 45,
        "medium_confidence_count": 30,
        "low_confidence_count": 25,
        "avg_confidence": 0.75,
        "accuracy_rate": 0.75
    }
    
    # Test formatting
    print("Testing Simple Visualization Helpers")
    print("=" * 50)
    
    print(viz.format_trending_topics_table(trending_data))
    print()
    print(viz.format_confidence_distribution(accuracy_data))
    
    print("✅ Simple visualization helpers test completed")
