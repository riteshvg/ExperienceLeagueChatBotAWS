# Adobe Experience League Chatbot

An intelligent Retrieval-Augmented Generation (RAG) chatbot powered by AWS Bedrock, designed to help users interact with Adobe Analytics and Customer Journey Analytics documentation through natural language queries.

## 🚀 Features

- **🤖 Smart AI Routing**: Automatically selects optimal AWS Bedrock models (Claude 3 Haiku, Sonnet, Opus) based on query complexity
- **📚 Knowledge Base Integration**: AWS Bedrock Knowledge Base with Adobe documentation
- **💰 Real-time Cost Tracking**: Monitor AWS usage and optimize costs
- **🎨 Modern UI**: React frontend with Material-UI
- **🔧 FastAPI Backend**: High-performance API with WebSocket support
- **📊 Example Questions**: Pre-built queries for common Adobe Analytics topics
- **🛡️ Error Handling**: Robust fallback mechanisms and error recovery
- **⚡ High Performance**: Optimized for speed and cost-effectiveness

## 🏗️ Architecture

- **Frontend**: React + TypeScript + Material-UI (Vite)
- **Backend**: FastAPI + Python
- **AI/LLM**: AWS Bedrock (Claude 3 models)
- **Knowledge Base**: AWS Bedrock Knowledge Base
- **Storage**: AWS S3
- **Deployment**: Railway

## 📁 Project Structure

```
ExperienceLeagueChatBotAWS/
├── backend/              # FastAPI backend
│   ├── app/             # Application code
│   ├── requirements.txt # Production dependencies
│   └── requirements-dev.txt # Development dependencies
├── frontend/            # React frontend
│   ├── src/            # Source code
│   └── dist/           # Build output
├── config/             # Configuration
├── scripts/            # Utility scripts
└── start.sh            # Railway startup script
```

## 🔧 Configuration

Set the following environment variables:

- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `AWS_DEFAULT_REGION` - AWS region (default: us-east-1)
- `AWS_S3_BUCKET` - S3 bucket for documents
- `BEDROCK_KNOWLEDGE_BASE_ID` - Bedrock Knowledge Base ID
- `BEDROCK_MODEL_ID` - Bedrock model ID
- `BEDROCK_REGION` - Bedrock region

## 📄 License

This project is licensed under the MIT License.
