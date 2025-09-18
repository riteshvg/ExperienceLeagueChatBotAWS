# 🔄 Hybrid AI Model Architecture

A comprehensive system for integrating and comparing Google Gemini and AWS Bedrock Claude models in a unified Streamlit application.

## 🎯 Overview

This hybrid model architecture provides:
- **Unified API interface** for both Gemini and Claude models
- **Intelligent query routing** based on query characteristics
- **Side-by-side comparison** capabilities
- **Performance tracking** and cost monitoring
- **Test suite management** for systematic evaluation
- **Configuration management** with user preferences

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI Layer                      │
├─────────────────────────────────────────────────────────────┤
│  Comparison UI  │  Smart Routing  │  Test Suite  │ Analytics │
├─────────────────────────────────────────────────────────────┤
│                    Query Router                            │
│  (Complexity Analysis │ Model Selection │ Cost Optimization) │
├─────────────────────────────────────────────────────────────┤
│                    Model Provider                          │
│  (Unified Interface │ Error Handling │ Performance Tracking) │
├─────────────────────────────────────────────────────────────┤
│  Gemini Client  │  Claude Client  │  Cost Tracker  │ Monitor │
├─────────────────────────────────────────────────────────────┤
│  Google API     │  AWS Bedrock    │  Local Storage │ Logging │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Installation

```bash
# Install additional dependencies
pip install -r requirements-hybrid.txt

# Or install individually
pip install google-generativeai tiktoken
```

### 2. Configuration

Set up your API keys:

```bash
# Google Gemini API Key
export GOOGLE_API_KEY="your_google_api_key_here"

# AWS Credentials (for Claude via Bedrock)
export AWS_ACCESS_KEY_ID="your_aws_access_key"
export AWS_SECRET_ACCESS_KEY="your_aws_secret_key"
export AWS_DEFAULT_REGION="us-east-1"
```

Or add to your `.env` file:
```env
GOOGLE_API_KEY=your_google_api_key_here
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1
```

### 3. Run the Demo

```bash
# Run the hybrid model demo
streamlit run hybrid_demo.py

# Or run the integration test
python test_hybrid_integration.py
```

## 📁 Project Structure

```
src/
├── models/
│   ├── __init__.py
│   ├── model_provider.py      # Unified model interface
│   ├── gemini_client.py       # Google Gemini client
│   ├── claude_bedrock_client.py # AWS Bedrock Claude client
│   ├── cost_tracker.py        # Cost and usage tracking
│   └── performance_monitor.py # Performance monitoring
├── config/
│   └── hybrid_config.py       # Configuration management
├── routing/
│   └── query_router.py        # Intelligent query routing
└── ui/
    └── comparison_ui.py       # Side-by-side comparison UI

# Demo and test files
hybrid_demo.py                 # Main demo application
test_hybrid_integration.py     # Integration tests
test_hybrid_models.py          # Model provider tests
requirements-hybrid.txt        # Additional dependencies
```

## 🔧 Core Components

### 1. Model Provider (`src/models/model_provider.py`)

Unified interface for both Gemini and Claude models:

```python
from src.models.model_provider import ModelProvider

# Initialize provider
provider = ModelProvider()

# Query individual models
gemini_result = provider.query_gemini("What is Adobe Analytics?")
claude_result = provider.query_claude_bedrock("What is Adobe Analytics?")

# Query both models simultaneously
both_result = provider.query_both_models("What is Adobe Analytics?")

# Get usage statistics
stats = provider.get_usage_stats()
```

### 2. Query Router (`src/routing/query_router.py`)

Intelligent routing based on query characteristics:

```python
from src.routing.query_router import QueryRouter

# Initialize router
router = QueryRouter()

# Analyze query
analysis = router.analyze_query("What is Adobe Analytics?")
print(f"Complexity: {analysis.complexity}")
print(f"Query Type: {analysis.query_type}")

# Get routing decision
decision = router.determine_best_model("What is Adobe Analytics?")
print(f"Recommended: {decision.recommended_model}")
print(f"Reasoning: {decision.reasoning}")
```

### 3. Configuration Manager (`src/config/hybrid_config.py`)

Centralized configuration management:

```python
from src.config.hybrid_config import HybridConfigManager

# Initialize config manager
config = HybridConfigManager()

# Update settings
config.update_user_preferences(
    preferred_model="auto",
    cost_sensitivity=0.5
)

# Save configuration
config.save_config()
```

### 4. Comparison UI (`src/ui/comparison_ui.py`)

Side-by-side comparison interface:

```python
from src.ui.comparison_ui import ComparisonUI

# Initialize comparison UI
comparison_ui = ComparisonUI(model_provider, query_router)

# Render comparison interface
comparison_ui.render_comparison_interface()
```

## 🎛️ Features

### 1. Model Comparison

- **Side-by-side responses** from both models
- **Performance metrics** (response time, cost, tokens)
- **Quality comparison** with rating system
- **Export functionality** for test results

### 2. Smart Routing

- **Automatic model selection** based on query characteristics
- **Complexity analysis** (simple, medium, complex)
- **Query type classification** (factual, analytical, code, troubleshooting)
- **Cost vs quality optimization**

### 3. Test Suite

- **Predefined test categories** for Adobe Experience League
- **Batch testing** capabilities
- **Performance benchmarking**
- **Result analysis** and comparison

### 4. Analytics Dashboard

- **Usage statistics** and cost tracking
- **Performance monitoring** with health status
- **Model comparison** metrics
- **Export capabilities** for data analysis

## 🧪 Testing

### Run Integration Tests

```bash
# Test complete integration
python test_hybrid_integration.py

# Test individual components
python test_hybrid_models.py
```

### Test Categories

The system includes predefined test categories:

1. **Basic Facts** - Simple factual questions
2. **Implementation** - How-to and technical questions
3. **Complex Analysis** - Multi-faceted analytical questions
4. **Code Examples** - Programming and implementation questions
5. **Troubleshooting** - Debugging and problem-solving questions

## 📊 Performance Monitoring

### Cost Tracking

- **Real-time cost calculation** per query
- **Daily/monthly cost limits** with alerts
- **Cost comparison** between models
- **Token usage tracking**

### Performance Metrics

- **Response time monitoring** with averages and percentiles
- **Success rate tracking** with error analysis
- **Health status monitoring** with alerts
- **Consecutive error tracking**

## ⚙️ Configuration Options

### Model Settings

```python
# Gemini configuration
gemini_model = "gemini-2.0-flash-exp"
gemini_temperature = 0.1
gemini_max_tokens = 8192

# Claude configuration
claude_model = "anthropic.claude-3-5-sonnet-20241022-v2:0"
claude_temperature = 0.1
claude_max_tokens = 4096
```

### Routing Rules

```python
# Complexity thresholds
complexity_threshold_simple = 50    # characters
complexity_threshold_complex = 200  # characters

# Cost vs quality preference (0.0 = cost, 1.0 = quality)
cost_vs_quality_preference = 0.5

# Response time limits
max_response_time = 30  # seconds
```

### User Preferences

```python
# User-specific settings
preferred_model = "auto"           # auto, gemini, claude
cost_sensitivity = 0.5             # 0.0 = very sensitive, 1.0 = not sensitive
speed_priority = 0.5               # 0.0 = very fast, 1.0 = very thorough
response_style = "balanced"        # concise, balanced, detailed
```

## 🔒 Security

### API Key Management

- **Environment variable** configuration
- **Secure credential storage** with validation
- **API key rotation** support
- **Usage monitoring** and alerts

### Error Handling

- **Graceful degradation** when models are unavailable
- **Fallback mechanisms** for failed requests
- **Comprehensive error logging**
- **User-friendly error messages**

## 📈 Usage Examples

### Basic Usage

```python
from src.models.model_provider import ModelProvider

# Initialize
provider = ModelProvider()

# Simple query
result = provider.query_gemini("What is Adobe Analytics?")
print(result['response'])

# Compare both models
comparison = provider.query_both_models("What is Adobe Analytics?")
print(f"Gemini: {comparison['results']['gemini']['response']}")
print(f"Claude: {comparison['results']['claude']['response']}")
```

### Advanced Usage

```python
from src.routing.query_router import QueryRouter
from src.config.hybrid_config import HybridConfigManager

# Initialize components
config = HybridConfigManager()
router = QueryRouter(config)
provider = ModelProvider()

# Smart routing
decision = router.determine_best_model("Complex analytical query")
if decision.recommended_model == 'gemini':
    result = provider.query_gemini("Complex analytical query")
else:
    result = provider.query_claude_bedrock("Complex analytical query")
```

## 🚀 Production Deployment

### Environment Setup

1. **Set environment variables** for API keys
2. **Configure AWS credentials** for Bedrock access
3. **Install dependencies** from requirements-hybrid.txt
4. **Run the application** with `streamlit run hybrid_demo.py`

### Monitoring

- **Health checks** for both model APIs
- **Performance monitoring** with alerts
- **Cost tracking** with daily/monthly limits
- **Error rate monitoring** with automatic fallbacks

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**
3. **Add tests** for new functionality
4. **Submit a pull request**

## 📄 License

This project is part of the Adobe Experience League Chatbot and follows the same licensing terms.

## 🆘 Support

For issues and questions:
1. **Check the documentation** in this README
2. **Run the integration tests** to verify setup
3. **Check API key configuration** and credentials
4. **Review error logs** for detailed error information

## 🔮 Future Enhancements

- **Additional model support** (GPT-4, PaLM, etc.)
- **Advanced routing algorithms** with machine learning
- **Custom model fine-tuning** capabilities
- **Real-time performance optimization**
- **Advanced analytics** and reporting
- **API rate limiting** and quota management
