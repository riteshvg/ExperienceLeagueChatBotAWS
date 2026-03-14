# ⚡ Quick Test Questions

Quick reference for testing chatbot capabilities.

## 🟢 Simple (Haiku) - Fast Responses

1. What is Adobe Analytics?
2. How do I create a segment?
3. What is the difference between eVars and props?
4. How do I set up conversion tracking?
5. What is Customer Journey Analytics?

## 🟡 Complex (Sonnet) - Detailed Answers

6. How do I implement cross-domain tracking in Adobe Analytics, and what are the common pitfalls?
7. What are the differences between Adobe Analytics and Customer Journey Analytics, and when should I use each?
8. How do I set up data classifications in Adobe Analytics, including marketing channel classifications?
9. How do I create a connection in Customer Journey Analytics that combines data from multiple channels?
10. How do I create and configure XDM schemas in Adobe Experience Platform?

## 🔴 Very Complex (Opus) - Comprehensive Solutions

11. Design a complete data architecture integrating Adobe Analytics, CJA, and AEP for unified customer journey analysis.
12. How do I implement a privacy-compliant analytics solution with GDPR support using Adobe Analytics?
13. What is the complete implementation strategy for migrating from traditional Adobe Analytics to Web SDK?
14. How do I build a real-time personalization system using AEP, Analytics, and Target?
15. Design a scalable Adobe Analytics implementation for a large e-commerce platform with multiple brands.

## 🔧 Troubleshooting

16. Why is my Adobe Analytics data showing zero visitors even though I can see hits being sent?
17. How do I troubleshoot data discrepancies between Adobe Analytics and Google Analytics?
18. Why are my conversion events not firing in Adobe Analytics?
19. How do I fix cross-domain tracking issues where visitor counts are inflated?
20. Why is my Adobe Analytics data delayed?

## 💼 Business Questions

21. What are the key metrics I should track for an e-commerce business?
22. How do I measure the ROI of my marketing campaigns?
23. What is the best way to analyze customer lifetime value?
24. How do I create executive dashboards showing business KPIs?
25. What metrics should I track for a mobile app?

## 🔗 Integration

26. How do I integrate Adobe Analytics with Salesforce?
27. How do I connect Adobe Analytics data to Google BigQuery?
28. How do I integrate Adobe Analytics with Marketo?
29. How do I set up Adobe Analytics to work with Adobe Target?
30. How do I integrate Customer Journey Analytics with Adobe Campaign?

---

## 🧪 Test Script

Run the automated test suite:

```bash
cd /Users/ritesh/ExperienceLeagueChatBotAWS
source venv/bin/activate
python scripts/test_advanced_capabilities.py
```

Or test individual questions via API:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Adobe Analytics?", "user_id": "test"}'
```

---

## 📊 Expected Results

- **Simple questions**: < 5 seconds, Haiku model
- **Complex questions**: 5-15 seconds, Sonnet model  
- **Very complex**: 15-30 seconds, Opus model
- **All questions**: Should retrieve 1-3 relevant documents
- **All questions**: Should provide accurate, cited answers

