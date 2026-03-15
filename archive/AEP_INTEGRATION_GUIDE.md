# 🏗️ Adobe Experience Platform (AEP) Integration Guide

This guide explains how to integrate Adobe Experience Platform documentation into your Adobe Analytics RAG chatbot, expanding its capabilities to answer questions about AEP, Analytics, and Customer Journey Analytics.

## 📋 Overview

The enhanced chatbot now supports three major Adobe Experience Cloud products:

- **Adobe Analytics** - Web analytics and reporting
- **Customer Journey Analytics (CJA)** - Cross-channel customer journey analysis
- **Adobe Experience Platform (AEP)** - Data management and customer experience orchestration

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

Run the complete integration setup:

```bash
python scripts/integrate_aep_with_existing_kb.py
```

This will:

1. Upload AEP documentation to S3
2. Add AEP as a new data source to your existing knowledge base
3. Start document ingestion job
4. Validate the integration

### Option 2: Manual Setup

If you prefer to run each step manually:

```bash
# Step 1: Upload AEP documentation
python scripts/upload_aep_docs.py

# Step 2: Add AEP data source to existing KB
python scripts/add_aep_to_existing_kb.py

# Step 3: Wait for ingestion to complete (10-30 minutes)
# Check status in AWS Bedrock console
```

## 📚 Documentation Sources

The integration includes documentation from these GitHub repositories:

| Source                         | Repository                                                                                              | Description                     |
| ------------------------------ | ------------------------------------------------------------------------------------------------------- | ------------------------------- |
| **Adobe Analytics**            | [analytics.en](https://github.com/AdobeDocs/analytics.en)                                               | User documentation and guides   |
| **Analytics APIs**             | [analytics-2.0-apis](https://github.com/AdobeDocs/analytics-2.0-apis)                                   | API reference and examples      |
| **Customer Journey Analytics** | [customer-journey-analytics-learn.en](https://github.com/AdobeDocs/customer-journey-analytics-learn.en) | CJA learning materials          |
| **Adobe Experience Platform**  | [experience-platform.en](https://github.com/AdobeDocs/experience-platform.en)                           | AEP comprehensive documentation |

## 🧪 Test Queries

After setup, test the integration with these sample queries:

### Adobe Experience Platform Queries

```
• How do I create a schema in Adobe Experience Platform?
• What are datasets and how do I use them in AEP?
• How do I set up data ingestion in AEP?
• How do I create audiences in Adobe Experience Platform?
• What is XDM and how do I use it?
• How do I configure identity service in AEP?
• What are data sources in Adobe Experience Platform?
• How do I set up real-time customer profiles?
• What is the data lake in AEP?
• How do I use query service in Adobe Experience Platform?
```

### Adobe Analytics Queries

```
• How do I create segments in Adobe Analytics?
• What's the difference between eVars and props?
• How do I set up conversion tracking?
• How do I use Analysis Workspace?
• How do I create calculated metrics?
```

### Customer Journey Analytics Queries

```
• How do I set up cross-channel analytics in CJA?
• What is data stitching in Customer Journey Analytics?
• How do I create customer journey reports?
• How do I connect data sources in CJA?
```

## 🔧 Technical Details

### Knowledge Base Configuration

Your existing knowledge base will be extended with:

- **Existing KB**: `knowledge-base-experienceleagechatbot` (your current setup)
- **Storage**: Amazon OpenSearch Serverless (your existing setup)
- **Embedding Model**: Amazon Titan Embeddings (your existing setup)
- **Chunking**: Fixed-size chunks (1000 tokens, 20% overlap)

### Data Sources

Your existing knowledge base will have these data sources:

1. **adobe-analytics-docs** - Main Analytics documentation (existing)
2. **adobe-analytics-apis** - Analytics API documentation (existing)
3. **customer-journey-analytics-docs** - CJA documentation (existing)
4. **adobe-experience-platform-docs** - AEP documentation (newly added)

### Query Processing

The chatbot automatically:

1. **Analyzes query complexity** to select the best AI model
2. **Checks relevance** to Adobe products (Analytics, AEP, CJA)
3. **Retrieves relevant documents** from the knowledge base
4. **Generates contextual responses** using AWS Bedrock

## 📊 Monitoring and Analytics

### Admin Dashboard

Monitor the integration through the admin dashboard:

- **System Status** - Overall health and component status
- **Query Analytics** - Usage patterns and performance metrics
- **Cost Tracking** - AWS usage and costs by service

### Debug Mode

Enable debug mode in the admin panel to see:

- Query processing details
- Document retrieval information
- Model selection reasoning
- Response generation metrics

## 🔄 Updating Documentation

To update the documentation with latest changes:

```bash
# Re-run the upload script to get latest changes
python scripts/upload_all_adobe_docs.py

# Re-run ingestion jobs to process new documents
# (This can be done through AWS console or by re-running the setup)
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. AWS Permissions

```
Error: Access Denied
Solution: Ensure your AWS credentials have the required permissions for S3, Bedrock, and Bedrock Agent services
```

#### 2. Knowledge Base Creation Fails

```
Error: ConflictException
Solution: The knowledge base may already exist. Check AWS console or use the existing one
```

#### 3. Ingestion Jobs Stuck

```
Issue: Ingestion jobs not completing
Solution: Check AWS Bedrock console for job status and error messages
```

#### 4. No AEP Responses

```
Issue: Chatbot not answering AEP questions
Solution: Verify AEP documentation was uploaded and ingested successfully
```

### Debug Steps

1. **Check S3 bucket** - Verify documents are uploaded
2. **Check knowledge base** - Ensure all data sources are created
3. **Check ingestion jobs** - Verify all jobs completed successfully
4. **Test with debug mode** - Enable debug mode to see processing details
5. **Check logs** - Review application logs for errors

## 📈 Performance Considerations

### Cost Optimization

- **Smart Routing** - Automatically selects the most cost-effective model
- **Haiku-Only Mode** - Use Claude 3 Haiku for 92% cost reduction
- **Caching** - Responses are cached to reduce API calls

### Response Quality

- **Model Selection** - Complex queries use more capable models
- **Context Retrieval** - Relevant documents provide accurate context
- **Relevance Filtering** - Only processes Adobe-related queries

## 🔐 Security

### Data Protection

- **Input Validation** - All queries are validated and sanitized
- **No PII Storage** - No personal data is stored or logged
- **Secure Transmission** - All data transmitted over HTTPS

### Access Control

- **Admin Authentication** - Secure admin panel access
- **Session Management** - Secure session handling
- **Audit Logging** - All actions are logged for security

## 📞 Support

### Getting Help

- **GitHub Issues** - Report bugs or request features
- **Documentation** - Check this guide and other docs
- **Admin Dashboard** - Monitor system status and health

### Contributing

- **Documentation Updates** - Help improve this guide
- **Feature Requests** - Suggest new capabilities
- **Bug Reports** - Help identify and fix issues

## 🎯 Next Steps

After successful integration:

1. **Test thoroughly** - Try various AEP, Analytics, and CJA queries
2. **Monitor usage** - Use the admin dashboard to track performance
3. **Optimize costs** - Adjust model selection based on usage patterns
4. **Gather feedback** - Collect user feedback to improve responses
5. **Expand coverage** - Consider adding more Adobe products

---

**🎉 Congratulations!** Your chatbot now supports the complete Adobe Experience Cloud ecosystem, providing comprehensive answers about Analytics, Customer Journey Analytics, and Adobe Experience Platform.
