# Model Retraining Implementation Guide

## Overview
This guide explains how to use the feedback data collected from the hybrid demo to retrain and improve the AI models.

## Data Formats Generated

### 1. Preference Learning Data
The system generates data suitable for Reinforcement Learning from Human Feedback (RLHF):

```json
{
  "training_examples": [
    {
      "query": "How do I set up Adobe Analytics tracking?",
      "response": "To set up Adobe Analytics tracking...",
      "model": "claude",
      "rating": 4,
      "feedback_id": "feedback_20250118_054123_001"
    }
  ],
  "preference_data": [
    {
      "query": "What is Adobe Analytics?",
      "preferred_response": "Claude's response...",
      "preferred_model": "claude",
      "alternative_response": "Gemini's response...",
      "alternative_model": "gemini",
      "preference_strength": 0.8,
      "feedback_id": "feedback_20250118_054123_002"
    }
  ]
}
```

## Retraining Approaches

### 1. Fine-tuning with Quality Scores

#### For Claude (AWS Bedrock)
```python
# Prepare training data
training_data = []
for example in feedback_data['training_examples']:
    if example['model'] == 'claude' and example['rating'] >= 4:
        training_data.append({
            "prompt": f"Question: {example['query']}\n\nAnswer:",
            "completion": example['response']
        })

# Use AWS Bedrock fine-tuning
import boto3
bedrock = boto3.client('bedrock')

# Create fine-tuning job
response = bedrock.create_model_customization_job(
    jobName='claude-feedback-finetune',
    customModelName='claude-analytics-expert',
    baseModelIdentifier='anthropic.claude-3-5-sonnet-20240620-v1:0',
    trainingDataConfig={
        's3Uri': 's3://your-bucket/training-data.jsonl'
    },
    validationDataConfig={
        's3Uri': 's3://your-bucket/validation-data.jsonl'
    }
)
```

#### For Gemini (Google AI)
```python
# Prepare training data for Gemini
import google.generativeai as genai

# Convert feedback to Gemini format
gemini_training_data = []
for example in feedback_data['training_examples']:
    if example['model'] == 'gemini' and example['rating'] >= 4:
        gemini_training_data.append({
            "input_text": f"Question: {example['query']}",
            "output_text": example['response']
        })

# Use Google's fine-tuning API
# Note: Gemini fine-tuning may require Google Cloud Platform setup
```

### 2. Preference Learning (RLHF)

#### Using Hugging Face TRL
```python
from trl import PPOTrainer, PPOConfig
from transformers import AutoTokenizer, AutoModelForCausalLM

# Load base model
model_name = "microsoft/DialoGPT-medium"  # or your preferred base model
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Prepare preference data
preference_dataset = []
for pref in feedback_data['preference_data']:
    preference_dataset.append({
        "prompt": pref['query'],
        "chosen": pref['preferred_response'],
        "rejected": pref['alternative_response']
    })

# Configure PPO training
ppo_config = PPOConfig(
    model_name=model_name,
    learning_rate=1e-5,
    batch_size=4,
    mini_batch_size=1,
    ppo_epochs=4
)

# Train with preferences
ppo_trainer = PPOTrainer(ppo_config, model, tokenizer)
ppo_trainer.train(preference_dataset)
```

### 3. Custom Retraining Pipeline

#### Step 1: Data Preprocessing
```python
def preprocess_feedback_data(feedback_file):
    """Convert feedback data to training format."""
    with open(feedback_file, 'r') as f:
        feedback_data = json.load(f)
    
    # Filter high-quality examples
    high_quality = [
        ex for ex in feedback_data['training_examples'] 
        if ex['rating'] >= 4 and ex['response_quality']['accuracy'] >= 4
    ]
    
    # Create training pairs
    training_pairs = []
    for example in high_quality:
        training_pairs.append({
            "input": f"Question: {example['query']}\n\nAnswer:",
            "output": example['response'],
            "metadata": {
                "model": example['model'],
                "rating": example['rating'],
                "quality_scores": example.get('response_quality', {})
            }
        })
    
    return training_pairs
```

#### Step 2: Model Training
```python
def train_model_with_feedback(training_data, base_model):
    """Train model using feedback data."""
    # This is a simplified example - actual implementation would depend on your chosen framework
    
    # Prepare data
    X = [pair['input'] for pair in training_data]
    y = [pair['output'] for pair in training_data]
    
    # Tokenize
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForCausalLM.from_pretrained(base_model)
    
    # Fine-tune (simplified)
    for epoch in range(3):
        for input_text, output_text in zip(X, y):
            # Training step here
            # This would involve actual model training code
            pass
    
    return model
```

## Implementation Steps

### 1. Collect Sufficient Data
- Aim for at least 100-500 high-quality feedback examples
- Ensure diverse query types and response patterns
- Include both positive and negative examples

### 2. Data Quality Filtering
```python
def filter_high_quality_data(feedback_data):
    """Filter data based on quality criteria."""
    filtered = []
    for example in feedback_data['training_examples']:
        # Only include high-quality examples
        if (example['rating'] >= 4 and 
            example['response_quality']['accuracy'] >= 4 and
            example['response_quality']['relevance'] >= 4):
            filtered.append(example)
    return filtered
```

### 3. Split Data
```python
def split_training_data(data, train_ratio=0.8):
    """Split data into training and validation sets."""
    import random
    random.shuffle(data)
    split_idx = int(len(data) * train_ratio)
    return data[:split_idx], data[split_idx:]
```

### 4. Model Evaluation
```python
def evaluate_retrained_model(model, test_data):
    """Evaluate the retrained model."""
    scores = []
    for example in test_data:
        # Generate response
        response = model.generate(example['query'])
        
        # Compare with ground truth (if available)
        # Calculate metrics like BLEU, ROUGE, etc.
        score = calculate_similarity(response, example['expected_response'])
        scores.append(score)
    
    return sum(scores) / len(scores)
```

## Integration with Hybrid Demo

### 1. Automated Retraining Trigger
```python
def check_retraining_threshold():
    """Check if enough feedback has been collected for retraining."""
    feedback_summary = feedback_manager.get_feedback_summary()
    
    if feedback_summary['total_feedback'] >= 100:
        return True
    return False

def trigger_retraining():
    """Trigger retraining process."""
    if check_retraining_threshold():
        # Prepare data
        retraining_data = feedback_manager.prepare_retraining_data()
        
        # Start retraining job
        start_retraining_job(retraining_data)
        
        # Notify user
        st.success("Retraining process started!")
```

### 2. A/B Testing
```python
def setup_ab_testing():
    """Set up A/B testing between original and retrained models."""
    # Route some queries to retrained model
    # Compare performance metrics
    # Gradually increase traffic to retrained model
    pass
```

## Monitoring and Iteration

### 1. Performance Tracking
- Monitor response quality metrics
- Track user satisfaction scores
- Compare before/after retraining performance

### 2. Continuous Learning
- Collect new feedback on retrained models
- Identify areas for further improvement
- Iterate on training data and methods

## Best Practices

1. **Start Small**: Begin with 100-200 high-quality examples
2. **Iterative Improvement**: Retrain regularly with new feedback
3. **A/B Testing**: Compare retrained models with originals
4. **Quality Control**: Filter out low-quality feedback
5. **Diverse Data**: Ensure training data covers various query types
6. **Monitoring**: Track performance metrics continuously

## Tools and Frameworks

- **Hugging Face Transformers**: For open-source model fine-tuning
- **AWS Bedrock**: For Claude model customization
- **Google AI Platform**: For Gemini model fine-tuning
- **Weights & Biases**: For experiment tracking
- **MLflow**: For model versioning and deployment
