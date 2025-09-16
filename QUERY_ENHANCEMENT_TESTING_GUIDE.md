# 🧪 Query Enhancement System Testing Guide

This guide provides comprehensive testing strategies for the Adobe Experience League RAG Query Enhancement System.

## 🚀 Quick Start Testing

### 1. **Immediate Test (No Setup Required)**

```bash
# Run the demo script to see the system in action
python3 test_enhancement_demo.py
```

### 2. **Streamlit App Testing**

```bash
# Start the Streamlit app
streamlit run app.py

# Navigate to http://localhost:8501
# Look for the "🚀 Query Enhancement" toggle in the UI
```

## 📊 Testing Categories

### **A. Unit Testing**

Test individual components in isolation:

```bash
# Run comprehensive unit tests
python3 -m pytest tests/test_query_enhancement.py -v

# Run specific test categories
python3 -m pytest tests/test_query_enhancement.py::TestAdobeQueryEnhancer::test_adobe_product_detection -v
```

### **B. Integration Testing**

Test the complete system with real queries:

```bash
# Run the integration demo
python3 test_enhancement_demo.py
```

### **C. Performance Testing**

Benchmark performance characteristics:

```bash
# Run performance tests
python3 test_query_enhancement_simple.py
```

## 🎯 Test Scenarios by Adobe Product

### **1. Adobe Analytics Testing**

Test queries that should detect and enhance Analytics-related content:

```python
# Test queries for Analytics
analytics_queries = [
    "How to track custom events?",
    "AA implementation steps",
    "analytics dashboard creation",
    "track user behavior",
    "analytics reporting setup",
    "measure conversion rates",
    "analytics data collection"
]

# Expected enhancements:
# - Should detect "Adobe Analytics"
# - Should expand "track" → "measure"
# - Should add Adobe context
```

### **2. Adobe Experience Platform Testing**

Test queries for AEP-related content:

```python
# Test queries for AEP
aep_queries = [
    "AEP data ingestion",
    "platform schema creation",
    "CDP configuration",
    "data platform setup",
    "schema management",
    "dataset creation",
    "data ingestion workflow"
]

# Expected enhancements:
# - Should detect "Adobe Experience Platform"
# - Should expand "setup" → "implement"
# - Should add platform context
```

### **3. Adobe Target Testing**

Test personalization and targeting queries:

```python
# Test queries for Target
target_queries = [
    "Target personalization",
    "AT audience targeting",
    "ab testing setup",
    "experience targeting",
    "personalization configuration",
    "audience segmentation",
    "testing campaigns"
]

# Expected enhancements:
# - Should detect "Adobe Target"
# - Should expand "setup" → "configure"
# - Should add targeting context
```

### **4. Cross-Product Testing**

Test queries that span multiple Adobe products:

```python
# Test cross-product queries
cross_product_queries = [
    "analytics and target integration",
    "AEP and analytics data flow",
    "campaign and analytics reporting",
    "AEM and analytics tracking"
]

# Expected enhancements:
# - Should detect multiple products
# - Should generate multiple enhanced queries
# - Should provide comprehensive context
```

## 🔍 Manual Testing in Streamlit UI

### **Step 1: Enable Debug Mode**

1. Go to the admin panel
2. Enable "Debug Mode"
3. Enable "Query Enhancement" toggle

### **Step 2: Test Query Enhancement Display**

1. Enter a query like "How to track custom events?"
2. Submit the query
3. Look for the "🚀 Query Enhancement" expandable section
4. Verify it shows:
   - Original query
   - Enhanced queries
   - Detected products
   - Processing time

### **Step 3: Compare Enhanced vs Non-Enhanced**

1. Toggle "Query Enhancement" OFF
2. Submit the same query
3. Note the response quality
4. Toggle "Query Enhancement" ON
5. Submit the same query again
6. Compare response quality and relevance

## 📈 Performance Testing

### **Latency Testing**

```python
# Test processing time for various query lengths
short_queries = ["AA setup", "AEP data", "Target test"]
medium_queries = ["How to setup Adobe Analytics tracking?"]
long_queries = ["How to implement comprehensive Adobe Analytics tracking for custom events in a complex e-commerce environment?"]

# Expected results:
# - All queries should process in <400ms
# - Average processing time should be <50ms
# - No significant difference between query lengths
```

### **Memory Testing**

```python
# Test memory usage with repeated queries
for i in range(1000):
    result = enhancer.enhance_query(f"test query {i}")

# Expected results:
# - Memory usage should remain stable
# - Cache should prevent memory leaks
# - No significant memory growth
```

## 🐛 Error Handling Testing

### **Edge Cases**

Test the system with problematic inputs:

```python
edge_cases = [
    "",  # Empty query
    "a",  # Single character
    "   ",  # Whitespace only
    "!@#$%^&*()",  # Special characters
    "123456789",  # Numbers only
    "analytics" * 100,  # Very long query
    None,  # None input
]

# Expected results:
# - Should handle all cases gracefully
# - Should return fallback responses
# - Should not crash or throw exceptions
```

### **Fallback Testing**

Test fallback behavior when enhancement fails:

```python
# Simulate enhancement failure
# (This would require mocking the enhancement function)

# Expected results:
# - Should fall back to original query
# - Should still return valid results
# - Should log the error appropriately
```

## 🎯 Success Criteria

### **Functional Requirements**

- ✅ Adobe product detection accuracy >90%
- ✅ Query enhancement generates 2-3 variations
- ✅ Processing time <400ms per query
- ✅ Graceful error handling
- ✅ Backward compatibility

### **Performance Requirements**

- ✅ Average processing time <50ms
- ✅ Memory usage stable over time
- ✅ Cache hit rate >60% for repeated queries
- ✅ No memory leaks

### **User Experience Requirements**

- ✅ UI shows enhancement details
- ✅ Toggle works correctly
- ✅ Debug information is helpful
- ✅ No performance degradation

## 🔧 Troubleshooting

### **Common Issues**

1. **Import Errors**

   ```bash
   # Solution: Ensure you're in the project root
   cd /path/to/adobe-analytics-rag
   python3 test_enhancement_demo.py
   ```

2. **Performance Issues**

   ```bash
   # Check if caching is working
   # Look for repeated query processing times
   ```

3. **UI Not Showing Enhancement Info**
   ```bash
   # Ensure debug mode is enabled
   # Check if query_enhancement_enabled is True
   ```

### **Debug Commands**

```bash
# Check if modules are importable
python3 -c "from query_enhancer import AdobeQueryEnhancer; print('✅ Import successful')"

# Test basic functionality
python3 -c "from query_enhancer import AdobeQueryEnhancer; e = AdobeQueryEnhancer(); print(e.enhance_query('test query'))"

# Check configuration
python3 -c "from config.settings import get_settings_instance; s = get_settings_instance(); print(f'Enhancement enabled: {s.query_enhancement_enabled}')"
```

## 📊 Test Results Interpretation

### **Good Results**

- Processing time <50ms average
- Product detection accuracy >90%
- Enhanced queries are relevant and diverse
- No errors or exceptions
- UI shows enhancement details correctly

### **Issues to Watch For**

- Processing time >400ms
- Product detection accuracy <80%
- Enhanced queries are irrelevant
- Memory usage growing over time
- UI not showing enhancement info

## 🚀 Next Steps After Testing

1. **If tests pass**: Deploy to production
2. **If performance issues**: Optimize caching or query processing
3. **If accuracy issues**: Refine product detection patterns
4. **If UI issues**: Check Streamlit integration

## 📝 Test Report Template

```markdown
# Query Enhancement Test Report

## Test Date: [DATE]

## Tester: [NAME]

## Environment: [DEV/STAGING/PROD]

### Functional Tests

- [ ] Product detection accuracy
- [ ] Query enhancement generation
- [ ] Error handling
- [ ] UI integration

### Performance Tests

- [ ] Processing time <400ms
- [ ] Memory usage stable
- [ ] Cache effectiveness
- [ ] Concurrent processing

### Results

- Pass Rate: X%
- Average Processing Time: Xms
- Issues Found: X
- Recommendations: [LIST]

### Status

- [ ] Ready for Production
- [ ] Needs Fixes
- [ ] Requires Further Testing
```

This comprehensive testing guide will help you validate the query enhancement system thoroughly before deploying to production!
