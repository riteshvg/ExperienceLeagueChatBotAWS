# Adobe Experience League Chatbot

An intelligent Retrieval-Augmented Generation (RAG) chatbot powered by AWS Bedrock, designed to help users interact with Adobe Analytics and Customer Journey Analytics documentation through natural language queries.

## 🚀 Features

- **🤖 Smart AI Routing**: Automatically selects optimal AWS Bedrock models (Claude 3 Haiku, Sonnet, Opus) based on query complexity
- **📚 Knowledge Base Integration**: Pinecone vector store with Adobe documentation
- **💰 Real-time Cost Tracking**: Monitor AWS usage and optimize costs
- **🎨 Clean UI**: Streamlit interface with admin dashboard
- **🔧 Comprehensive Admin Panel**: System monitoring, configuration, and analytics
- **📊 Example Questions**: Pre-built queries for common Adobe Analytics topics
- **🛡️ Error Handling**: Robust fallback mechanisms and error recovery
- **⚡ High Performance**: Optimized for speed and cost-effectiveness

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit UI  │    │   Smart Router   │    │  AWS Bedrock    │
│                 │───▶│                  │───▶│  Claude Models  │
│ • Main Chat     │    │ • Query Analysis │    │ • Haiku         │
│ • Admin Panel   │    │ • Model Selection│    │ • Sonnet        │
└─────────────────┘    └──────────────────┘    │ • Opus          │
         │                       │              └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Knowledge     │    │   AWS S3         │    │   Pinecone      │
│   Base          │    │   Storage        │    │   Vector Store  │
│                 │    │                  │    │                 │
│ • Document      │    │ • Adobe Docs     │    │ • Embeddings    │
│   Retrieval     │    │ • CJA Docs       │    │ • Similarity    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📁 Project Structure

```
adobe-analytics-rag/
├── app.py                          # Main Streamlit application
├── config/
│   └── settings.py                 # Configuration management
├── src/
│   └── utils/
│       ├── aws_utils.py           # AWS client utilities
│       ├── bedrock_client.py      # Bedrock model client
│       └── adobe_auth.py          # Adobe authentication
├── scripts/
│   ├── setup_aws_infrastructure.py # AWS setup automation
│   ├── upload_docs_to_s3.py       # Document upload scripts
│   ├── knowledge_base_guide.py    # KB creation guide
│   └── test_*.py                  # Testing utilities
├── requirements.txt               # Python dependencies
├── .env.template                 # Environment variables template
├── docker-compose.yml            # Docker development setup
└── README.md                     # This file
```

## 🛠️ Quick Start

### 1. Prerequisites

- Python 3.11+
- AWS Account with Bedrock access
- Adobe Analytics documentation (optional)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/riteshvg/ExperienceLeagueChatBotAWS.git
cd ExperienceLeagueChatBotAWS

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy environment template
cp .env.template .env

# Edit .env with your AWS credentials
nano .env
```

Required environment variables:

```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
BEDROCK_KNOWLEDGE_BASE_ID=your_kb_id
```

### 4. Run the Application

```bash
streamlit run app.py
```

Open your browser to `http://localhost:8501`

## 🔧 AWS Setup

### 1. Enable Bedrock Models

1. Go to AWS Bedrock Console
2. Navigate to "Model access" in the left sidebar
3. Enable the following models:
   - Claude 3 Haiku
   - Claude 3 Sonnet
   - Claude 3 Opus
   - Titan Embeddings v2

### 2. Create Knowledge Base

1. Go to AWS Bedrock Console
2. Navigate to "Knowledge bases"
3. Click "Create knowledge base"
4. Follow the guided setup process
5. Use Pinecone as vector store
6. Configure S3 data source

### 3. Set Up S3 Bucket

```bash
# Run the AWS infrastructure setup
python scripts/setup_aws_infrastructure.py
```

## 💰 Cost Optimization

The application includes real-time cost tracking and optimization:

- **Smart Routing**: Automatically selects cost-effective models
- **Usage Analytics**: Track tokens and costs per query
- **Cost Recommendations**: Get optimization suggestions
- **Budget Monitoring**: Set and track spending limits

### Estimated Monthly Costs

- **Low Usage** (100 queries): $15-30
- **Medium Usage** (500 queries): $50-100
- **High Usage** (2000 queries): $150-300

## 🎯 Usage

### Main Chat Interface

1. **Ask Questions**: Type your Adobe Analytics questions
2. **Use Examples**: Click pre-built example questions
3. **View Results**: Get AI-powered answers with source documents
4. **Smart Routing**: See which model was selected and why

### Admin Dashboard

1. **System Status**: Monitor all components
2. **Configuration**: View and manage settings
3. **AWS Details**: Check connections and costs
4. **Analytics**: Track usage and performance
5. **Smart Router**: View model configurations

## 🧪 Testing

```bash
# Run comprehensive tests
python test_complete_flow.py

# Test specific components
python scripts/test_knowledge_base.py
python test_model_access.py
```

## 📚 Documentation

- [AWS Setup Guide](scripts/README_aws_setup.md)
- [Environment Setup](scripts/setup_env_guide.md)
- [Knowledge Base Evaluation](knowledge_base_qa_evaluation.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/riteshvg/ExperienceLeagueChatBotAWS/issues)
- **Documentation**: Check the `scripts/` directory for detailed guides
- **AWS Support**: Refer to AWS Bedrock documentation

## 🙏 Acknowledgments

- **AWS Bedrock** for powerful AI models
- **Streamlit** for the web interface
- **Pinecone** for vector search capabilities
- **Adobe** for comprehensive documentation

---

**Built with ❤️ for the Adobe Analytics community**
