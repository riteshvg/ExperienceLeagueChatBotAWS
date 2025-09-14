# 🚀 Performance Comparison Tool

A side-by-side comparison tool to test and compare the performance of the main app vs the complete optimized app.

## 🎯 Features

- **Side-by-side comparison** of both app versions
- **Real-time timing** with millisecond precision
- **Performance metrics** including speed improvement calculations
- **Response quality comparison** (length, success rate)
- **Performance history** tracking
- **Model usage tracking** (which model each version uses)

## 🚀 How to Run

```bash
streamlit run performance_comparison.py
```

## 📊 What You'll See

### 1. **Query Input**

- Enter a question that will be processed by both versions simultaneously
- Both apps will process the same query in parallel

### 2. **Real-time Results**

- **Main App (Optimized)**: Shows results from the merged main app
- **Complete Optimized App**: Shows results from the standalone optimized app
- **Timing**: Precise timing for each version
- **Success/Failure**: Status of each query

### 3. **Performance Metrics**

- **Response Time**: How long each version took
- **Speed Improvement**: Which version is faster and by how much
- **Time Difference**: Absolute difference in response times
- **Model Used**: Which AI model each version selected

### 4. **Performance Analysis**

- **Winner**: Which version performed better
- **Response Quality**: Length and content comparison
- **Historical Data**: Track performance over multiple queries

## 🔍 What to Test

### **Query Examples:**

1. **Simple**: "How do I implement Adobe Analytics?"
2. **Complex**: "What are the best practices for Adobe Analytics implementation with data privacy considerations?"
3. **Technical**: "How do I set up custom events in Adobe Analytics using the Web SDK?"
4. **Troubleshooting**: "Why is my Adobe Analytics data not showing up in reports?"

### **Expected Results:**

- **First Query**: Both versions should take 8-15 seconds
- **Repeated Query**: Main app should be faster due to caching
- **Performance Dashboard**: Check the "🚀 Performance" tab in main app admin

## 📈 Performance Insights

### **Main App Advantages:**

- ✅ **Caching**: Repeated queries are much faster
- ✅ **Integration**: Full admin dashboard and analytics
- ✅ **Production Ready**: All features integrated

### **Complete Optimized App Advantages:**

- ✅ **Clean Code**: No legacy code conflicts
- ✅ **Focused**: Built specifically for performance
- ✅ **Standalone**: Independent of main app structure

## 🛠️ Troubleshooting

### **If Import Errors Occur:**

1. Check that both `app.py` and `src/performance/complete_optimized_app.py` exist
2. Ensure all dependencies are installed
3. Verify AWS configuration is set up

### **If Queries Fail:**

1. Check AWS credentials and region settings
2. Verify Knowledge Base ID is correct
3. Ensure Bedrock models are enabled

### **If Timing Seems Off:**

1. First query will always be slower (cold start)
2. Subsequent queries should be faster due to caching
3. Network latency can affect results

## 📊 Interpreting Results

### **Speed Comparison:**

- **1.0x**: Same speed
- **2.0x**: One version is twice as fast
- **0.5x**: One version is half as fast (2x slower)

### **Response Quality:**

- **Length**: Longer responses may be more detailed
- **Success Rate**: Both should have high success rates
- **Model Selection**: May differ based on query complexity

## 🎯 Best Practices

1. **Test Multiple Queries**: Try different types of questions
2. **Repeat Queries**: Test caching performance
3. **Check Admin Dashboard**: Use the Performance tab in main app
4. **Monitor Trends**: Look for consistent performance patterns
5. **Document Findings**: Note which version works better for your use case

## 🔧 Technical Details

- **Threading**: Both queries run in parallel for fair comparison
- **Caching**: Main app uses intelligent caching, optimized app doesn't
- **Error Handling**: Both versions have robust error handling
- **Metrics**: Detailed performance tracking and analysis
- **UI**: Clean, responsive interface for easy comparison

---

**Happy Testing! 🚀**
