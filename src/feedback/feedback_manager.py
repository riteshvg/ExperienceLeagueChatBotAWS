"""
Feedback management system for hybrid model evaluation and retraining.
Captures user feedback on model responses and prepares data for retraining.
"""

import json
import csv
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import pandas as pd

class FeedbackManager:
    """Manages user feedback collection and retraining data preparation."""
    
    def __init__(self, feedback_dir: str = "./feedback_data"):
        """Initialize feedback manager."""
        self.feedback_dir = Path(feedback_dir)
        self.feedback_dir.mkdir(exist_ok=True)
        
        # Initialize feedback storage
        self.feedback_file = self.feedback_dir / "feedback.json"
        self.retraining_file = self.feedback_dir / "retraining_data.json"
        self.csv_file = self.feedback_dir / "feedback_export.csv"
        
        # Load existing feedback
        self.feedback_data = self._load_feedback()
    
    def _load_feedback(self) -> List[Dict[str, Any]]:
        """Load existing feedback data."""
        if self.feedback_file.exists():
            try:
                with open(self.feedback_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return []
        return []
    
    def _save_feedback(self):
        """Save feedback data to file."""
        with open(self.feedback_file, 'w') as f:
            json.dump(self.feedback_data, f, indent=2)
    
    def submit_feedback(
        self,
        query: str,
        gemini_response: str,
        claude_response: str,
        selected_model: str,
        user_rating: int,
        user_comments: str = "",
        response_quality: Dict[str, int] = None,
        additional_notes: str = ""
    ) -> str:
        """
        Submit user feedback for a model comparison.
        
        Args:
            query: Original user query
            gemini_response: Gemini model response
            claude_response: Claude model response
            selected_model: Which model was selected ('gemini' or 'claude')
            user_rating: Overall rating (1-5)
            user_comments: User's comments about the responses
            response_quality: Detailed quality ratings
            additional_notes: Additional notes
            
        Returns:
            Feedback ID
        """
        feedback_id = f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.feedback_data)}"
        
        feedback_entry = {
            "feedback_id": feedback_id,
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "gemini_response": gemini_response,
            "claude_response": claude_response,
            "selected_model": selected_model,
            "user_rating": user_rating,
            "user_comments": user_comments,
            "response_quality": response_quality or {},
            "additional_notes": additional_notes,
            "retraining_ready": False
        }
        
        self.feedback_data.append(feedback_entry)
        self._save_feedback()
        
        return feedback_id
    
    def get_feedback_summary(self) -> Dict[str, Any]:
        """Get summary of all feedback data."""
        if not self.feedback_data:
            return {
                "total_feedback": 0,
                "average_rating": 0,
                "model_preferences": {},
                "recent_feedback": []
            }
        
        total_feedback = len(self.feedback_data)
        average_rating = sum(f.get('user_rating', 0) for f in self.feedback_data) / total_feedback
        
        # Model preferences
        model_preferences = {}
        for feedback in self.feedback_data:
            model = feedback.get('selected_model', 'unknown')
            model_preferences[model] = model_preferences.get(model, 0) + 1
        
        # Recent feedback (last 10)
        recent_feedback = sorted(
            self.feedback_data, 
            key=lambda x: x.get('timestamp', ''), 
            reverse=True
        )[:10]
        
        return {
            "total_feedback": total_feedback,
            "average_rating": round(average_rating, 2),
            "model_preferences": model_preferences,
            "recent_feedback": recent_feedback
        }
    
    def prepare_retraining_data(self, feedback_ids: List[str] = None) -> Dict[str, Any]:
        """
        Prepare feedback data for model retraining.
        
        Args:
            feedback_ids: Specific feedback IDs to include (None for all)
            
        Returns:
            Retraining data in format suitable for fine-tuning
        """
        if feedback_ids:
            selected_feedback = [f for f in self.feedback_data if f['feedback_id'] in feedback_ids]
        else:
            selected_feedback = self.feedback_data
        
        retraining_data = {
            "training_examples": [],
            "preference_data": [],
            "quality_metrics": [],
            "metadata": {
                "total_examples": len(selected_feedback),
                "generated_at": datetime.now().isoformat(),
                "source": "hybrid_demo_feedback"
            }
        }
        
        for feedback in selected_feedback:
            # Create training examples
            query = feedback['query']
            selected_model = feedback['selected_model']
            rating = feedback['user_rating']
            
            # Positive example (chosen response)
            chosen_response = feedback[f'{selected_model}_response']
            retraining_data["training_examples"].append({
                "query": query,
                "response": chosen_response,
                "model": selected_model,
                "rating": rating,
                "feedback_id": feedback['feedback_id']
            })
            
            # Preference data (if both responses available)
            if feedback['gemini_response'] and feedback['claude_response']:
                retraining_data["preference_data"].append({
                    "query": query,
                    "preferred_response": chosen_response,
                    "preferred_model": selected_model,
                    "alternative_response": feedback[f'{"claude" if selected_model == "gemini" else "gemini"}_response'],
                    "alternative_model": "claude" if selected_model == "gemini" else "gemini",
                    "preference_strength": rating / 5.0,  # Normalize to 0-1
                    "feedback_id": feedback['feedback_id']
                })
            
            # Quality metrics
            if feedback.get('response_quality'):
                retraining_data["quality_metrics"].append({
                    "feedback_id": feedback['feedback_id'],
                    "query": query,
                    "model": selected_model,
                    "quality_scores": feedback['response_quality'],
                    "overall_rating": rating
                })
        
        # Save retraining data
        with open(self.retraining_file, 'w') as f:
            json.dump(retraining_data, f, indent=2)
        
        return retraining_data
    
    def export_to_csv(self) -> str:
        """Export feedback data to CSV for analysis."""
        if not self.feedback_data:
            return ""
        
        # Prepare data for CSV
        csv_data = []
        for feedback in self.feedback_data:
            csv_data.append({
                "feedback_id": feedback['feedback_id'],
                "timestamp": feedback['timestamp'],
                "query": feedback['query'],
                "selected_model": feedback['selected_model'],
                "user_rating": feedback['user_rating'],
                "user_comments": feedback['user_comments'],
                "gemini_response_length": len(feedback.get('gemini_response', '')),
                "claude_response_length": len(feedback.get('claude_response', '')),
                "additional_notes": feedback.get('additional_notes', '')
            })
        
        # Write to CSV
        df = pd.DataFrame(csv_data)
        df.to_csv(self.csv_file, index=False)
        
        return str(self.csv_file)
    
    def get_model_performance_analysis(self) -> Dict[str, Any]:
        """Analyze model performance based on feedback."""
        if not self.feedback_data:
            return {"error": "No feedback data available"}
        
        # Group by model
        gemini_feedback = [f for f in self.feedback_data if f['selected_model'] == 'gemini']
        claude_feedback = [f for f in self.feedback_data if f['selected_model'] == 'claude']
        
        analysis = {
            "gemini": {
                "total_selections": len(gemini_feedback),
                "average_rating": sum(f['user_rating'] for f in gemini_feedback) / len(gemini_feedback) if gemini_feedback else 0,
                "rating_distribution": {}
            },
            "claude": {
                "total_selections": len(claude_feedback),
                "average_rating": sum(f['user_rating'] for f in claude_feedback) / len(claude_feedback) if claude_feedback else 0,
                "rating_distribution": {}
            }
        }
        
        # Rating distributions
        for model_data in [gemini_feedback, claude_feedback]:
            model_name = "gemini" if model_data == gemini_feedback else "claude"
            for rating in range(1, 6):
                count = sum(1 for f in model_data if f['user_rating'] == rating)
                analysis[model_name]["rating_distribution"][str(rating)] = count
        
        return analysis
    
    def clear_feedback(self, confirm: bool = False):
        """Clear all feedback data (use with caution)."""
        if confirm:
            self.feedback_data = []
            self._save_feedback()
            return True
        return False
