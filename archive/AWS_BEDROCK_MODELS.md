# AWS Bedrock Models Used in the Application

## Active Models (Currently Used)

The application uses **3 AWS Bedrock models** with smart routing based on query complexity:

### 1. **Claude 3 Haiku** (Fast & Cost-Effective)
- **Model ID**: `us.anthropic.claude-3-haiku-20240307-v1:0`
- **Version**: Claude 3 Haiku v1 (Released: March 2024)
- **Use Case**: Simple, straightforward questions
- **When Used**: 
  - Short queries (< 5 words)
  - Simple factual questions
  - Basic "what is" or "how to" questions
- **Cost**: $1.25 per 1M input tokens, $5.00 per 1M output tokens
- **Performance**: Fastest response time (< 5 seconds)

### 2. **Claude 3.7 Sonnet** (Balanced Performance)
- **Model ID**: `us.anthropic.claude-3-7-sonnet-20250219-v1:0`
- **Version**: Claude 3.7 Sonnet v1 (Released: February 2025)
- **Use Case**: Complex analytical questions
- **When Used**:
  - Complex queries (5-15 words)
  - Questions requiring analysis or comparison
  - Troubleshooting or optimization questions
- **Cost**: $15.00 per 1M input tokens, $75.00 per 1M output tokens
- **Performance**: Balanced response time (5-15 seconds)

### 3. **Claude 3 Opus** (Most Capable)
- **Model ID**: `us.anthropic.claude-3-opus-20240229-v1:0`
- **Version**: Claude 3 Opus v1 (Released: February 2024)
- **Use Case**: Very complex, strategic questions
- **When Used**:
  - Extremely complex queries (> 15 words)
  - Strategic or creative questions
  - Multi-step problem solving
  - Low Knowledge Base relevance (needs general knowledge)
- **Cost**: $75.00 per 1M input tokens, $375.00 per 1M output tokens
- **Performance**: Most comprehensive responses (15-30 seconds)

## Smart Routing Logic

The `SmartRouter` class automatically selects the appropriate model based on:

1. **Query Complexity**:
   - Simple keywords: "what", "define", "explain", "how to"
   - Complex keywords: "analyze", "compare", "difference", "troubleshoot"
   - Creative keywords: "best", "recommend", "suggest", "strategy"

2. **Query Length**:
   - < 5 words → Haiku
   - 5-15 words → Sonnet
   - > 15 words → Opus

3. **Knowledge Base Relevance**:
   - High relevance (> 0.7) → Use simpler model (Haiku/Sonnet)
   - Low relevance (< 0.3) → Use Opus for general knowledge

## Fallback Mechanism

If the selected model fails or is unavailable:
- **Fallback Model**: `us.anthropic.claude-3-haiku-20240307-v1:0`
- All models fall back to Haiku as a reliable backup

## Model Configuration Location

The models are configured in:
- **Primary**: `app.py` → `SmartRouter.__init__()` (lines 438-442)
- **Backend**: Uses the same SmartRouter from `app.py`
- **Fallback**: `backend/app/services/chat_helpers.py` (lines 223, 266)

## Available Models (Not Currently Used)

The codebase also references these models but they are **not actively used** in the smart routing:

- `us.anthropic.claude-3-5-sonnet-20240620-v1:0` (Claude 3.5 Sonnet)
- `us.anthropic.claude-3-7-sonnet-20250219-v1:0` (Claude 3.7 Sonnet - **This is the one actually used**)
- `us.anthropic.claude-sonnet-4-20250514-v1:0` (Claude Sonnet 4)
- `amazon.titan-text-express-v1` (Amazon Titan)
- `amazon.titan-embed-text-v2:0` (Amazon Titan Embeddings)
- `meta.llama2-13b-chat-v1` (Meta Llama 2)
- `meta.llama3-8b-instruct-v1:0` (Meta Llama 3)

## Model Selection Summary

| Model | Model ID | Version | Use Case | Cost (per 1M tokens) |
|-------|----------|---------|----------|---------------------|
| **Haiku** | `us.anthropic.claude-3-haiku-20240307-v1:0` | v1 (Mar 2024) | Simple queries | $1.25 input / $5.00 output |
| **Sonnet** | `us.anthropic.claude-3-7-sonnet-20250219-v1:0` | v1 (Feb 2025) | Complex queries | $15.00 input / $75.00 output |
| **Opus** | `us.anthropic.claude-3-opus-20240229-v1:0` | v1 (Feb 2024) | Very complex queries | $75.00 input / $375.00 output |

## Cost Optimization

The application includes a **Haiku-only mode** for cost optimization:
- When enabled, all queries use Haiku regardless of complexity
- Provides ~92% cost reduction
- Can be toggled in the application settings

## Embedding Model

For Knowledge Base retrieval:
- **Model**: `amazon.titan-embed-text-v2:0` (Amazon Titan Embeddings v2)
- **Purpose**: Document embeddings for semantic search
- **Location**: Configured in `config/settings.py` as `bedrock_embedding_model_id`

## Notes

1. **Model Versions**: All models use the `us.` prefix, indicating they are in the US region
2. **Inference Profiles**: Models use inference profiles (indicated by `:0` suffix)
3. **Region**: Models are configured for `us-east-1` by default
4. **Latest Model**: Claude 3.7 Sonnet (Feb 2025) is the newest model being used

