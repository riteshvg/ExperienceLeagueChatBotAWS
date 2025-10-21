# Complex Technical Test Queries

This document contains complex technical questions to thoroughly test the optimized RAG chatbot with streaming responses.

---

## 1. Multi-Step Configuration Questions

### Question 1.1
```
"How do I set up a data source connector in Adobe Experience Platform, including authentication and field mapping?"
```

### Question 1.2
```
"What are the steps to configure a report suite in Adobe Analytics, including traffic variables and custom events?"
```

### Question 1.3
```
"Walk me through setting up a destination in Adobe Experience Platform, from data source to audience activation."
```

---

## 2. Architecture & Best Practices

### Question 2.1
```
"What is the difference between batch and streaming segmentation in Adobe Experience Platform, and when should I use each?"
```

### Question 2.2
```
"Explain the XDM schema architecture and how it relates to data ingestion in Adobe Experience Platform."
```

### Question 2.3
```
"How does the identity graph work in Adobe Experience Platform, and what are the best practices for identity stitching?"
```

---

## 3. Advanced Feature Questions

### Question 3.1
```
"How do I create a calculated metric in Adobe Analytics that combines multiple events and applies specific filters?"
```

### Question 3.2
```
"Explain how to use Query Service in Adobe Experience Platform to analyze customer journey data across multiple datasets."
```

### Question 3.3
```
"What is the difference between profile merge rules and identity namespaces in Adobe Experience Platform?"
```

---

## 4. Troubleshooting & Error Handling

### Question 4.1
```
"What should I do if my data source ingestion is failing in Adobe Experience Platform?"
```

### Question 4.2
```
"How do I debug audience activation issues in Adobe Experience Platform destinations?"
```

### Question 4.3
```
"What are common reasons for calculated metrics to return incorrect values in Adobe Analytics?"
```

---

## 5. Integration & API Questions

### Question 5.1
```
"How do I use the Adobe Analytics 2.0 API to retrieve real-time report data?"
```

### Question 5.2
```
"Explain how to integrate Adobe Experience Platform with third-party marketing automation tools like Marketo."
```

### Question 5.3
```
"What are the steps to implement server-side forwarding from Adobe Analytics to Adobe Experience Platform?"
```

---

## 6. Data Governance & Privacy

### Question 6.1
```
"How do I implement consent management in Adobe Experience Platform using IAB TCF 2.0?"
```

### Question 6.2
```
"Explain the data retention policies in Adobe Experience Platform and how to configure them."
```

### Question 6.3
```
"What are the best practices for handling PII data in Adobe Experience Platform?"
```

---

## 7. Performance & Optimization

### Question 7.1
```
"How can I optimize query performance in Adobe Experience Platform Query Service?"
```

### Question 7.2
```
"What are the best practices for reducing data latency in Adobe Experience Platform?"
```

### Question 7.3
```
"How do I monitor and optimize the performance of my Adobe Analytics implementation?"
```

---

## 8. Cross-Product Questions

### Question 8.1
```
"How do I use Adobe Analytics data in Adobe Experience Platform for real-time customer profiles?"
```

### Question 8.2
```
"Explain the workflow for creating segments in Adobe Analytics and activating them through Adobe Experience Platform."
```

### Question 8.3
```
"What is the relationship between Adobe Analytics, Customer Journey Analytics, and Adobe Experience Platform?"
```

---

## 9. Edge Cases & Scenarios

### Question 9.1
```
"How do I handle duplicate events in Adobe Experience Platform data ingestion?"
```

### Question 9.2
```
"What happens when a visitor has multiple identity namespaces in Adobe Experience Platform?"
```

### Question 9.3
```
"How do I migrate from Adobe Audience Manager to Adobe Experience Platform Real-time CDP?"
```

---

## 10. Advanced Analytics

### Question 10.1
```
"Explain how to use Attribution AI in Adobe Experience Platform to measure marketing effectiveness."
```

### Question 10.2
```
"How do I create a lookalike audience in Adobe Experience Platform Real-time CDP?"
```

### Question 10.3
```
"What is the difference between batch and streaming segmentation, and how do I choose between them?"
```

---

## Testing Strategy

### Test Each Category:
1. ✅ Multi-step configuration (tests procedural knowledge)
2. ✅ Architecture questions (tests deep understanding)
3. ✅ Advanced features (tests specialized knowledge)
4. ✅ Troubleshooting (tests practical application)
5. ✅ Integration (tests cross-system knowledge)
6. ✅ Data governance (tests compliance knowledge)
7. ✅ Performance (tests optimization knowledge)
8. ✅ Cross-product (tests ecosystem knowledge)
9. ✅ Edge cases (tests boundary conditions)
10. ✅ Advanced analytics (tests AI/ML features)

---

## What to Validate

### ✅ Factual Accuracy
- Answers should reference specific Adobe documentation
- Technical terms should be correct
- Steps should be accurate

### ✅ Consistency
- Run same query 2-3 times
- Should get similar (not identical) but consistent answers

### ✅ Completeness
- Complex questions should get comprehensive answers
- Should not miss critical steps or information

### ✅ Reduced Hallucinations
- No made-up features or capabilities
- No incorrect API endpoints or parameters
- No fictional workflows

### ✅ Context Awareness
- Should understand multi-part questions
- Should provide relevant examples
- Should explain relationships between concepts

### ✅ Streaming Behavior
- Answers should appear progressively
- No long waits before seeing text
- Smooth, continuous display

---

## Validation Checklist

After testing, note:
- [ ] Which queries worked well?
- [ ] Which queries had issues?
- [ ] Any hallucinations detected?
- [ ] Any missing information?
- [ ] Response quality compared to before optimization
- [ ] Streaming performance and smoothness
- [ ] Perceived speed improvement

---

## Quick Start Test Queries

**Start with these for initial validation:**

1. **Basic**: "What is Adobe Analytics?"
2. **Technical**: "How do I create a report suite?"
3. **Multi-step**: "Walk me through setting up Adobe Experience Platform data sources"
4. **Complex**: "Explain the complete workflow for segmentation in Customer Journey Analytics"
5. **Integration**: "How do I integrate Adobe Analytics with Adobe Experience Platform?"

---

## Notes

- All queries are designed to test the optimized RAG system
- Temperature: 0.15 (factual accuracy)
- Top-K: 8 (optimal retrieval)
- Streaming: Enabled (real-time display)
- Expected improvements: 60-70% reduction in hallucinations

---

**Created**: October 19, 2025  
**Purpose**: Comprehensive testing of optimized RAG chatbot  
**Status**: Ready for validation

