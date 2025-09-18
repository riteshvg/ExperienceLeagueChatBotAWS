"""
Configuration management for hybrid model architecture.
Handles settings, preferences, and model configuration.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    """Configuration for individual models."""
    # Model preferences
    default_model: str = "auto"  # auto, gemini, claude
    cost_vs_quality_preference: float = 0.5  # 0=cost, 1=quality
    max_response_time: int = 30  # seconds
    max_cost_per_query: float = 1.0  # dollars
    
    # Context settings
    max_context_tokens: int = 100000
    context_compression_enabled: bool = True
    
    # Gemini settings
    gemini_model: str = "gemini-2.0-flash-exp"
    gemini_temperature: float = 0.1
    gemini_max_tokens: int = 8192
    
    # Claude settings
    claude_model: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    claude_temperature: float = 0.1
    claude_max_tokens: int = 4096
    claude_region: str = "us-east-1"
    
    # Testing settings
    enable_comparison_mode: bool = False
    save_all_responses: bool = True
    enable_performance_logging: bool = True
    
    # Routing settings
    auto_routing_enabled: bool = True
    complexity_threshold_simple: int = 50  # characters
    complexity_threshold_complex: int = 200  # characters
    
    # Cost thresholds
    daily_cost_limit: float = 10.0
    monthly_cost_limit: float = 100.0
    
    # Performance thresholds
    max_response_time_warning: float = 10.0  # seconds
    max_error_rate_warning: float = 0.05  # 5%
    max_consecutive_errors: int = 3

@dataclass
class UserPreferences:
    """User-specific preferences."""
    preferred_model: str = "auto"
    cost_sensitivity: float = 0.5  # 0=very cost sensitive, 1=not cost sensitive
    speed_priority: float = 0.5  # 0=very fast, 1=very thorough
    response_style: str = "balanced"  # concise, balanced, detailed
    enable_streaming: bool = True
    show_performance_metrics: bool = True
    enable_debug_mode: bool = False

class HybridConfigManager:
    """Manages configuration for hybrid model architecture."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration manager."""
        self.config_file = config_file or "hybrid_config.json"
        self.config_path = Path(self.config_file)
        
        # Load configuration
        self.model_config = self._load_model_config()
        self.user_preferences = self._load_user_preferences()
        
        logger.info("Hybrid configuration manager initialized")
    
    def _load_model_config(self) -> ModelConfig:
        """Load model configuration from file or create default."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    return ModelConfig(**data.get('model_config', {}))
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}. Using defaults.")
        
        return ModelConfig()
    
    def _load_user_preferences(self) -> UserPreferences:
        """Load user preferences from file or create default."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    return UserPreferences(**data.get('user_preferences', {}))
            except Exception as e:
                logger.warning(f"Failed to load user preferences: {e}. Using defaults.")
        
        return UserPreferences()
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            config_data = {
                'model_config': asdict(self.model_config),
                'user_preferences': asdict(self.user_preferences),
                'last_updated': str(Path().cwd())
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
    
    def update_model_config(self, **kwargs):
        """Update model configuration."""
        for key, value in kwargs.items():
            if hasattr(self.model_config, key):
                setattr(self.model_config, key, value)
                logger.info(f"Updated model config: {key} = {value}")
            else:
                logger.warning(f"Unknown model config key: {key}")
    
    def update_user_preferences(self, **kwargs):
        """Update user preferences."""
        for key, value in kwargs.items():
            if hasattr(self.user_preferences, key):
                setattr(self.user_preferences, key, value)
                logger.info(f"Updated user preference: {key} = {value}")
            else:
                logger.warning(f"Unknown user preference key: {key}")
    
    def get_api_keys(self) -> Dict[str, Optional[str]]:
        """Get API keys from environment variables."""
        return {
            'google_api_key': os.getenv('GOOGLE_API_KEY'),
            'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
            'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
            'aws_region': os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        }
    
    def validate_api_keys(self) -> Dict[str, bool]:
        """Validate that required API keys are present."""
        api_keys = self.get_api_keys()
        
        validation = {
            'google_available': api_keys['google_api_key'] is not None,
            'aws_available': all([
                api_keys['aws_access_key_id'] is not None,
                api_keys['aws_secret_access_key'] is not None
            ]),
            'at_least_one_available': False
        }
        
        validation['at_least_one_available'] = (
            validation['google_available'] or validation['aws_available']
        )
        
        return validation
    
    def get_model_selection_criteria(self) -> Dict[str, Any]:
        """Get criteria for automatic model selection."""
        return {
            'cost_vs_quality': self.model_config.cost_vs_quality_preference,
            'max_response_time': self.model_config.max_response_time,
            'max_cost_per_query': self.model_config.max_cost_per_query,
            'complexity_thresholds': {
                'simple': self.model_config.complexity_threshold_simple,
                'complex': self.model_config.complexity_threshold_complex
            },
            'user_preferences': {
                'preferred_model': self.user_preferences.preferred_model,
                'cost_sensitivity': self.user_preferences.cost_sensitivity,
                'speed_priority': self.user_preferences.speed_priority
            }
        }
    
    def get_performance_thresholds(self) -> Dict[str, float]:
        """Get performance monitoring thresholds."""
        return {
            'max_response_time': self.model_config.max_response_time_warning,
            'max_error_rate': self.model_config.max_error_rate_warning,
            'max_consecutive_errors': self.model_config.max_consecutive_errors,
            'daily_cost_limit': self.model_config.daily_cost_limit,
            'monthly_cost_limit': self.model_config.monthly_cost_limit
        }
    
    def get_model_settings(self, model: str) -> Dict[str, Any]:
        """Get settings for a specific model."""
        if model.lower() == 'gemini':
            return {
                'model_id': self.model_config.gemini_model,
                'temperature': self.model_config.gemini_temperature,
                'max_tokens': self.model_config.gemini_max_tokens,
                'streaming': self.user_preferences.enable_streaming
            }
        elif model.lower() == 'claude':
            return {
                'model_id': self.model_config.claude_model,
                'temperature': self.model_config.claude_temperature,
                'max_tokens': self.model_config.claude_max_tokens,
                'region': self.model_config.claude_region,
                'streaming': self.user_preferences.enable_streaming
            }
        else:
            raise ValueError(f"Unknown model: {model}")
    
    def export_config(self, format: str = 'json') -> str:
        """Export configuration in specified format."""
        config_data = {
            'model_config': asdict(self.model_config),
            'user_preferences': asdict(self.user_preferences),
            'api_keys_status': self.validate_api_keys(),
            'export_timestamp': str(Path().cwd())
        }
        
        if format.lower() == 'json':
            return json.dumps(config_data, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def import_config(self, config_data: Dict[str, Any]):
        """Import configuration from dictionary."""
        try:
            if 'model_config' in config_data:
                self.model_config = ModelConfig(**config_data['model_config'])
            
            if 'user_preferences' in config_data:
                self.user_preferences = UserPreferences(**config_data['user_preferences'])
            
            logger.info("Configuration imported successfully")
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            raise
    
    def reset_to_defaults(self):
        """Reset configuration to default values."""
        self.model_config = ModelConfig()
        self.user_preferences = UserPreferences()
        logger.info("Configuration reset to defaults")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration."""
        return {
            'model_config': asdict(self.model_config),
            'user_preferences': asdict(self.user_preferences),
            'api_keys_status': self.validate_api_keys(),
            'config_file': str(self.config_path),
            'config_exists': self.config_path.exists()
        }

# Global configuration manager instance
config_manager = HybridConfigManager()

def get_config() -> HybridConfigManager:
    """Get the global configuration manager instance."""
    return config_manager
