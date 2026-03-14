# 🧪 Advanced Test Questions for Chatbot

This document contains comprehensive test questions to evaluate the chatbot's advanced capabilities across different complexity levels, use cases, and Adobe products.

## 📊 Test Categories

### 1. Simple Questions (Should use Haiku model)
### 2. Complex Questions (Should use Sonnet model)
### 3. Very Complex Questions (Should use Opus model)
### 4. Troubleshooting Scenarios
### 5. Implementation & Best Practices
### 6. Integration Questions
### 7. Edge Cases & Advanced Features

---

## 🟢 Simple Questions (Basic Information)

These should trigger **Haiku** model for fast, cost-effective responses.

1. **What is Adobe Analytics?**
2. **How do I create a segment in Adobe Analytics?**
3. **What is the difference between eVars and props?**
4. **How do I set up conversion tracking?**
5. **What is Customer Journey Analytics?**
6. **How do I create a calculated metric?**
7. **What is a virtual report suite?**
8. **How do I use Analysis Workspace?**
9. **What is Adobe Experience Platform?**
10. **How do I create a dashboard in Adobe Analytics?**

---

## 🟡 Complex Questions (Detailed Analysis)

These should trigger **Sonnet** model for balanced performance.

### Adobe Analytics

11. **How do I implement Adobe Analytics tracking for a single-page application (SPA) using the Web SDK, and what are the best practices for handling page views and events?**
12. **What are the differences between server-side and client-side data collection in Adobe Analytics, and when should I use each approach?**
13. **How do I set up cross-domain tracking in Adobe Analytics, and what are the common pitfalls to avoid?**
14. **Explain how to create and use data classifications in Adobe Analytics, including the process for setting up marketing channel classifications.**
15. **What is the processing order of Adobe Analytics rules, and how does it affect data accuracy in reports?**
16. **How do I implement Adobe Analytics for mobile apps using the Mobile SDK, including offline tracking and lifecycle metrics?**
17. **What are the best practices for implementing Adobe Analytics in a privacy-compliant way, including GDPR and CCPA considerations?**
18. **How do I use Data Warehouse and Data Feeds to export raw data from Adobe Analytics?**
19. **Explain the difference between visits and visitors, and how sessionization works in Adobe Analytics.**
20. **How do I troubleshoot data discrepancies between Adobe Analytics and other analytics tools?**

### Customer Journey Analytics (CJA)

21. **How do I create a connection in Customer Journey Analytics that combines data from multiple channels, and what are the data requirements?**
22. **What is identity stitching in Customer Journey Analytics, and how does it differ from Adobe Analytics visitor identification?**
23. **How do I analyze cross-channel customer journeys in CJA, including attribution across touchpoints?**
24. **Explain how to use the CJA Workspace to create cross-channel analysis and what capabilities it offers over traditional Analytics Workspace.**
25. **How do I set up data views in Customer Journey Analytics, and what are the key configuration options?**
26. **What are the differences between Adobe Analytics and Customer Journey Analytics, and when should I use each?**
27. **How do I implement CJA for analyzing customer journeys across web, mobile app, and offline channels?**
28. **Explain how to use calculated metrics and dimensions in CJA for advanced analysis.**
29. **How do I create audiences in CJA and activate them through Adobe Experience Platform?**
30. **What are the data governance considerations when setting up CJA connections?**

### Adobe Experience Platform (AEP)

31. **How do I create and configure XDM schemas in Adobe Experience Platform for different data types?**
32. **What is the Real-Time Customer Profile in AEP, and how does it differ from traditional customer databases?**
33. **How do I ingest data into Adobe Experience Platform using batch and streaming ingestion?**
34. **Explain how to use Query Service in AEP to analyze data in the data lake.**
35. **How do I create segments in Adobe Experience Platform and activate them to destinations?**
36. **What are sandboxes in AEP, and how do I use them for development and testing?**
37. **How do I set up data governance and privacy labels in Adobe Experience Platform?**
38. **Explain the difference between datasets and data streams in AEP.**
39. **How do I connect Adobe Analytics data to Adobe Experience Platform?**
40. **What are the best practices for data modeling in Adobe Experience Platform?**

---

## 🔴 Very Complex Questions (Advanced Scenarios)

These should trigger **Opus** model for maximum capability.

### Multi-Product Integration

41. **Design a complete data architecture that integrates Adobe Analytics, Customer Journey Analytics, and Adobe Experience Platform to provide a unified view of customer journeys across web, mobile, email, and offline channels, including data flow, identity resolution, and activation strategies.**

42. **How do I implement a comprehensive attribution model that combines Adobe Analytics data with Customer Journey Analytics to analyze the full customer journey from first touch to conversion, accounting for cross-device and cross-channel interactions?**

43. **Explain how to build a real-time personalization system using Adobe Experience Platform, Adobe Analytics, and Adobe Target, including data collection, profile building, segment creation, and content delivery.**

44. **What is the complete implementation strategy for migrating from traditional Adobe Analytics implementation to the Web SDK, including data mapping, validation, parallel tracking, and cutover planning?**

45. **How do I set up a data governance framework across Adobe Analytics, CJA, and AEP that ensures data quality, privacy compliance (GDPR, CCPA), and proper data classification and usage policies?**

### Advanced Analytics

46. **How do I create a custom attribution model in Adobe Analytics that weights different touchpoints based on business rules, and how does this compare to using CJA for attribution analysis?**

47. **Explain how to implement server-side tracking for Adobe Analytics using the Web SDK, including edge network configuration, data validation, and error handling strategies.**

48. **How do I build a comprehensive analytics implementation that tracks user behavior across multiple domains, mobile apps, and offline touchpoints, with proper identity stitching and cross-device analysis?**

49. **What are the advanced techniques for optimizing Adobe Analytics data collection to reduce latency, improve data quality, and minimize costs while maintaining comprehensive tracking?**

50. **How do I implement a data quality monitoring system for Adobe Analytics that detects anomalies, validates data accuracy, and provides alerts for data issues?**

### Implementation & Architecture

51. **Design and implement a privacy-first analytics solution using Adobe Analytics that supports consent management, data minimization, and user rights (GDPR deletion requests, opt-out) while maintaining data accuracy.**

52. **How do I create a scalable Adobe Analytics implementation for a large e-commerce platform with multiple brands, international sites, and complex business rules?**

53. **Explain how to implement Adobe Analytics for a media/streaming platform that needs to track video consumption, ad views, subscription events, and user engagement across web, mobile, and connected TV devices.**

54. **How do I set up a data pipeline that combines Adobe Analytics data with external data sources (CRM, marketing automation) in Adobe Experience Platform for advanced analysis and activation?**

55. **What is the complete strategy for implementing Adobe Analytics in a headless commerce architecture, including API-based tracking, server-side rendering considerations, and real-time data validation?**

---

## 🔧 Troubleshooting Scenarios

56. **Why is my Adobe Analytics data showing zero visitors even though I can see hits being sent?**
57. **How do I troubleshoot data discrepancies between Adobe Analytics and Google Analytics?**
58. **Why are my conversion events not firing in Adobe Analytics, and how do I debug this?**
59. **How do I fix cross-domain tracking issues where visitor counts are inflated?**
60. **Why is my Adobe Analytics data delayed, and what are the typical processing times?**
61. **How do I troubleshoot missing data in Customer Journey Analytics connections?**
62. **Why are my segments not working correctly in Adobe Analytics, and how do I validate them?**
63. **How do I debug Adobe Analytics implementation issues using browser developer tools?**
64. **Why is my data retention period shorter than expected in Adobe Analytics?**
65. **How do I troubleshoot issues with Adobe Experience Platform data ingestion failures?**

---

## 💼 Business & Strategy Questions

66. **What are the key metrics I should track for an e-commerce business in Adobe Analytics?**
67. **How do I measure the ROI of my marketing campaigns using Adobe Analytics?**
68. **What is the best way to analyze customer lifetime value using Adobe Analytics and CJA?**
69. **How do I create executive dashboards in Adobe Analytics that show business KPIs?**
70. **What are the best practices for setting up analytics for a B2B SaaS company?**
71. **How do I measure the effectiveness of my content marketing using Adobe Analytics?**
72. **What metrics should I track for a mobile app in Adobe Analytics?**
73. **How do I analyze user engagement and retention using Adobe Analytics?**
74. **What is the best approach to measure multi-touch attribution for my marketing channels?**
75. **How do I create a comprehensive analytics strategy that aligns with business objectives?**

---

## 🔗 Integration Questions

76. **How do I integrate Adobe Analytics with Salesforce to track marketing campaign performance?**
77. **How do I connect Adobe Analytics data to Google BigQuery for advanced analysis?**
78. **How do I integrate Adobe Analytics with marketing automation platforms like Marketo or HubSpot?**
79. **How do I set up Adobe Analytics to work with Adobe Target for personalization?**
80. **How do I integrate Customer Journey Analytics with Adobe Campaign for cross-channel marketing?**
81. **How do I connect Adobe Experience Platform to external data warehouses?**
82. **How do I integrate Adobe Analytics with social media platforms for campaign tracking?**
83. **How do I set up Adobe Analytics to track email campaign performance?**
84. **How do I integrate Adobe Analytics with CRM systems for customer analysis?**
85. **How do I connect Adobe Analytics to business intelligence tools like Tableau or Power BI?**

---

## 🎯 Advanced Features & Edge Cases

86. **How do I use Adobe Analytics Data Feeds to build custom reporting solutions?**
87. **What are the advanced features of Analysis Workspace, and how do I use them effectively?**
88. **How do I implement custom event tracking for complex user interactions?**
89. **How do I use Adobe Analytics APIs to automate report generation and data extraction?**
90. **What are the advanced segmentation techniques in Adobe Analytics, including sequential segments and container logic?**
91. **How do I implement data layer architecture for Adobe Analytics in a complex website?**
92. **What are the best practices for handling bot traffic and data quality in Adobe Analytics?**
93. **How do I use Adobe Analytics for A/B testing and experimentation analysis?**
94. **How do I implement Adobe Analytics for tracking offline-to-online customer journeys?**
95. **What are the advanced features of Customer Journey Analytics for analyzing customer behavior?**

---

## 🧪 Model Selection Test Questions

These questions are designed to test the smart routing system:

### Should Use Haiku (Simple)
- "What is Adobe Analytics?"
- "How do I create a segment?"

### Should Use Sonnet (Complex)
- "How do I implement cross-domain tracking with proper visitor identification?"
- "Explain the differences between Adobe Analytics and Customer Journey Analytics."

### Should Use Opus (Very Complex)
- "Design a complete data architecture integrating Analytics, CJA, and AEP for unified customer journey analysis."
- "How do I implement a privacy-compliant analytics solution with GDPR support?"

---

## 📝 Testing Checklist

Use this checklist when testing:

- [ ] **Simple questions** return fast responses (Haiku)
- [ ] **Complex questions** get detailed answers (Sonnet)
- [ ] **Very complex questions** get comprehensive responses (Opus)
- [ ] **Troubleshooting questions** provide actionable solutions
- [ ] **Integration questions** explain step-by-step processes
- [ ] **Business questions** provide strategic insights
- [ ] **Edge cases** are handled gracefully
- [ ] **Knowledge Base** retrieves relevant documents
- [ ] **Citations** are provided for answers
- [ ] **Follow-up questions** work correctly

---

## 🚀 Quick Test Script

Run these in sequence to test different capabilities:

```bash
# Simple question
"What is Adobe Analytics?"

# Complex question  
"How do I implement cross-domain tracking in Adobe Analytics?"

# Very complex question
"Design a complete data architecture integrating Adobe Analytics, CJA, and AEP."

# Troubleshooting
"Why is my Adobe Analytics data showing zero visitors?"

# Integration
"How do I integrate Adobe Analytics with Salesforce?"
```

---

## 📊 Expected Model Usage

Based on query complexity analysis:

- **Haiku**: Questions 1-10, 56-60 (simple, factual)
- **Sonnet**: Questions 11-40, 61-75 (moderate complexity, detailed)
- **Opus**: Questions 41-55, 76-95 (very complex, strategic, multi-step)

---

## 💡 Tips for Testing

1. **Start Simple**: Test basic questions first to ensure core functionality works
2. **Progressive Complexity**: Gradually increase question complexity
3. **Test Edge Cases**: Try unusual or boundary questions
4. **Verify Citations**: Check that answers reference source documents
5. **Test Follow-ups**: Ask related follow-up questions
6. **Check Model Selection**: Verify the right model is chosen for each question
7. **Test Error Handling**: Try invalid or irrelevant questions
8. **Performance**: Note response times for different complexity levels

---

## 🎯 Success Criteria

A successful test should show:

✅ **Correct Model Selection**: Right model for query complexity  
✅ **Accurate Answers**: Answers are factually correct  
✅ **Relevant Sources**: Documents cited are relevant  
✅ **Complete Responses**: Answers address the full question  
✅ **Actionable Guidance**: Troubleshooting questions provide solutions  
✅ **Fast Responses**: Simple questions answered quickly  
✅ **Comprehensive Answers**: Complex questions get detailed responses  

---

**Happy Testing! 🚀**

