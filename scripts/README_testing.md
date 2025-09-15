# Knowledge Base Testing Scripts

This directory contains scripts to programmatically test your Knowledge Base with questions across all data sources.

## Scripts Available

### 1. `test_knowledge_base_questions.py` - Comprehensive Testing

**Full-featured test suite with detailed evaluation and reporting.**

**Features:**

- Tests all 5 categories (Analytics, CJA, AEP, Analytics+AEP, Analytics+CJA)
- 10 total test questions (2 per category)
- Keyword matching and relevance scoring
- Detailed logging and progress tracking
- JSON results export
- Pass/fail evaluation with 60% threshold

**Usage:**

```bash
# Basic test
python3 scripts/test_knowledge_base_questions.py --kb-id NQTC3SRPZX

# Save results to file
python3 scripts/test_knowledge_base_questions.py --kb-id NQTC3SRPZX --save-results

# Custom output file
python3 scripts/test_knowledge_base_questions.py --kb-id NQTC3SRPZX --save-results --output-file my_test_results.json

# Different region
python3 scripts/test_knowledge_base_questions.py --kb-id NQTC3SRPZX --region us-west-2
```

### 2. `quick_test_questions.py` - Quick Testing

**Simple script for quick verification with 5 key questions.**

**Features:**

- 5 essential test questions (1 per category)
- Simple pass/fail evaluation
- Quick summary and category breakdown
- JSON results export
- Fast execution

**Usage:**

```bash
# Quick test
python3 scripts/quick_test_questions.py --kb-id NQTC3SRPZX

# Different region
python3 scripts/quick_test_questions.py --kb-id NQTC3SRPZX --region us-west-2
```

## Test Questions by Category

### Analytics

- "How do I set up Adobe Analytics tracking on my website?"
- "What are the different types of variables in Adobe Analytics and how do I use them?"

### Customer Journey Analytics (CJA)

- "How do I create a connection in Customer Journey Analytics?"
- "What is the difference between Adobe Analytics and Customer Journey Analytics?"

### Adobe Experience Platform (AEP)

- "How do I create a schema in Adobe Experience Platform?"
- "What are datasets in AEP and how do I create them?"

### Analytics + AEP Integration

- "How do I connect Adobe Analytics data to Adobe Experience Platform for customer journey analysis?"
- "What is the best way to send Analytics data to AEP for real-time personalization?"

### Analytics + CJA Integration

- "How do I use Adobe Analytics data in Customer Journey Analytics for cross-device analysis?"
- "What's the process to migrate from Adobe Analytics to Customer Journey Analytics?"

## Expected Results

### ✅ Good Results

- **Score ≥ 0.6**: Test passes
- **Found keywords**: Expected product-specific terms are present
- **High relevance**: Retrieved documents are highly relevant
- **Multiple documents**: 3-5 relevant documents found

### ❌ Issues to Investigate

- **Score < 0.6**: Test fails
- **Missing keywords**: Expected terms not found in results
- **Low relevance**: Retrieved documents are not relevant
- **No results**: Knowledge Base returns empty results

## Understanding the Scores

### Scoring Algorithm

- **Keyword Score (60%)**: Percentage of expected keywords found
- **Relevance Score (40%)**: Average relevance score of retrieved documents
- **Total Score**: Weighted combination of both scores

### Thresholds

- **Pass**: Score ≥ 0.6 (60%)
- **Fail**: Score < 0.6 (60%)

## Troubleshooting

### Common Issues

1. **"No results found"**

   - Check if Knowledge Base is ACTIVE
   - Verify data sources are AVAILABLE
   - Check if ingestion jobs completed successfully

2. **"Missing expected keywords"**

   - Verify documents were properly ingested
   - Check if content contains expected terminology
   - Consider if question phrasing needs adjustment

3. **"Low relevance scores"**

   - Check if question is too specific or vague
   - Verify document quality and content
   - Consider adjusting retrieval configuration

4. **"Query failed"**
   - Check AWS credentials and permissions
   - Verify Knowledge Base ID is correct
   - Check AWS region configuration

### Debug Steps

1. **Check Knowledge Base status:**

   ```bash
   aws bedrock-agent get-knowledge-base --knowledge-base-id NQTC3SRPZX
   ```

2. **Check data sources:**

   ```bash
   aws bedrock-agent list-data-sources --knowledge-base-id NQTC3SRPZX
   ```

3. **Check ingestion jobs:**
   ```bash
   aws bedrock-agent list-ingestion-jobs --knowledge-base-id NQTC3SRPZX
   ```

## Output Files

### Comprehensive Test Results

- **File**: `test_results/knowledge_base_test_results_YYYYMMDD_HHMMSS.json`
- **Content**: Detailed results with evaluation scores, keyword analysis, and category breakdown

### Quick Test Results

- **File**: `quick_test_results_YYYYMMDD_HHMMSS.json`
- **Content**: Summary results with pass/fail status and category breakdown

## Best Practices

1. **Run tests regularly** to ensure Knowledge Base quality
2. **Use both scripts** - comprehensive for thorough testing, quick for daily checks
3. **Monitor trends** in test scores over time
4. **Investigate failures** promptly to maintain quality
5. **Update test questions** as your knowledge base evolves

## Integration with CI/CD

These scripts can be integrated into your CI/CD pipeline:

```bash
# Example CI/CD step
python3 scripts/quick_test_questions.py --kb-id $KB_ID
if [ $? -eq 0 ]; then
    echo "Knowledge Base tests passed"
else
    echo "Knowledge Base tests failed"
    exit 1
fi
```
