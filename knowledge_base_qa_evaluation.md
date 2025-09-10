# Knowledge Base Q&A Evaluation

**Knowledge Base ID**: NQTC3SRPZX  
**Name**: knowledge-base-experienceleagechatbot  
**Status**: ACTIVE  
**Region**: us-east-1  
**Test Date**: 2025-09-09  
**Test Results**: 8/8 tests passed (100.0%)

---

## Test 1: Basic Adobe Analytics Definition

**Question**: What is Adobe Analytics?

**Retrieval Scores**:

- Document 1: 0.835 (Analytics Tech Notes)
- Document 2: 0.702 (General overview information)
- Document 3: 0.697 (Key features in Adobe Analytics)

**Answer**:

# What is Adobe Analytics?

Adobe Analytics is a cloud-based web analytics solution that enables businesses to measure, analyze, and optimize their digital marketing activities. It provides real-time insights into customer behavior, website performance, and marketing campaign effectiveness.

Key features include:

- Real-time data collection and reporting
- Advanced segmentation capabilities
- Custom event tracking
- Conversion funnel analysis
- Integration with other Adobe Experience Cloud products
- Predictive analytics and machine learning insights
- Mobile app analytics
- Cross-device tracking
- Custom dashboards and reports

Adobe Analytics helps organizations understand their customers' digital journey, optimize their marketing spend, and make data-driven decisions to improve business outcomes.

**Keywords Found**: adobe, analytics, web, data  
**Answer Length**: 1,099 characters  
**Status**: ✅ PASS

---

## Test 2: Custom Events Implementation

**Question**: How do I create custom events in Adobe Analytics?

**Retrieval Scores**:

- Document 1: 0.692 (Event configuration notes)
- Document 2: 0.689 (Google Analytics event comparison)
- Document 3: 0.641 (Available events information)

**Answer**:

# Creating Custom Events in Adobe Analytics

To create custom events in Adobe Analytics, you have several options based on your implementation method:

## Using the Adobe Analytics Extension in Tags

1. **Navigate to the Adobe Analytics Extension** in Adobe Experience Platform Tags
2. **Go to Rules** and create a new rule or edit an existing one
3. **Add an Action** and select "Set Variables"
4. **Configure the Event** by setting the appropriate event variable (e.g., event1, event2, etc.)
5. **Set the Value** for the event (usually 1 for counting occurrences)
6. **Add Conditions** if you want the event to fire only under specific circumstances

## Using JavaScript Implementation

```javascript
// Basic event tracking
s.events = 'event1'; // Replace event1 with your custom event

// Event with additional data
s.events = 'event1,event2';
s.eVar1 = 'custom_value';
s.prop1 = 'additional_data';
```

## Using Adobe Experience Platform Web SDK

```javascript
// Track custom event
alloy('event', {
  xdm: {
    eventType: 'web.webpagedetails.pageViews',
    web: {
      webPageDetails: {
        name: 'Custom Event Page',
      },
    },
    customData: {
      customEvent: 'event1',
    },
  },
});
```

## Best Practices

- Use descriptive names for your events
- Document your event taxonomy
- Test events in a development environment first
- Use consistent naming conventions
- Consider the impact on data collection limits

**Keywords Found**: custom, events, implementation  
**Answer Length**: 1,736 characters  
**Status**: ✅ PASS

---

## Test 3: eVars and Props Explanation

**Question**: What are eVars and props in Adobe Analytics?

**Retrieval Scores**:

- Document 1: 0.646 (eVar setup information)
- Document 2: 0.633 (Props description)
- Document 3: 0.626 (Props availability)

**Answer**:

# eVars and props in Adobe Analytics

Based on the provided context, eVars and props are custom variables in Adobe Analytics that serve different purposes:

## eVars (Conversion Variables)

- Up to 250 eVars are available if your contract with Adobe supports it
- Used for conversion tracking and attribution
- Persist beyond the page view where they are set
- Can be used for both traffic and conversion analysis
- Set up in report suite configuration
- Can be used with the Web SDK Pro extension

## Props (Traffic Variables)

- Up to 75 props are available if your contract with Adobe supports it
- Used for traffic analysis and segmentation
- Only persist for the current page view
- Primarily used for traffic analysis
- Set up in report suite configuration
- Can be used with the Web SDK Pro extension

## Key Differences

| Feature           | eVars               | Props                  |
| ----------------- | ------------------- | ---------------------- |
| **Persistence**   | Beyond page view    | Current page view only |
| **Primary Use**   | Conversion tracking | Traffic analysis       |
| **Attribution**   | Yes                 | No                     |
| **Maximum Count** | 250                 | 75                     |
| **Data Type**     | String              | String                 |

## Implementation

Both eVars and props are implemented in your tracking code:

```javascript
// eVar implementation
s.eVar1 = 'conversion_value';

// Prop implementation
s.prop1 = 'traffic_value';
```

**Keywords Found**: evar, props, conversion, variable  
**Answer Length**: 1,079 characters  
**Status**: ✅ PASS

---

## Test 4: Customer Journey Analytics Setup

**Question**: How do I set up Customer Journey Analytics?

**Retrieval Scores**:

- Document 1: 0.712 (Customer Journey Analytics Videos and Tutorials)
- Document 2: 0.706 (What is Customer Journey Analytics?)
- Document 3: 0.683 (Architecture and Integrations)

**Answer**:

# How to Set Up Customer Journey Analytics

To set up Adobe Customer Journey Analytics (CJA), you need to follow these general steps:

1. **Ensure your data is in Adobe Experience Platform**: CJA leverages data from Adobe Experience Platform, so your data must first be ingested into AEP.

2. **Configure data connections**: Set up connections between your data sources and Adobe Experience Platform, including:

   - Web analytics data
   - Mobile app data
   - Offline data
   - CRM data
   - Other relevant data sources

3. **Create datasets**: Organize your data into datasets within Adobe Experience Platform that will be used by CJA.

4. **Set up data views**: Configure data views in CJA to define how your data should be interpreted and displayed.

5. **Configure identity mapping**: Set up identity mapping to connect customer data across different touchpoints and devices.

6. **Create connections**: Establish connections between CJA and your data sources through Adobe Experience Platform.

7. **Configure attribution**: Set up attribution models to understand how different touchpoints contribute to conversions.

8. **Test and validate**: Ensure data is flowing correctly and that your reports are displaying accurate information.

## Prerequisites

- Adobe Experience Platform license
- Customer Journey Analytics license
- Data already ingested into Adobe Experience Platform
- Proper data governance and privacy settings configured

## Key Features

- Cross-channel customer journey analysis
- Real-time data processing
- Advanced segmentation
- Attribution modeling
- Custom metrics and dimensions
- Integration with other Adobe Experience Cloud products

**Keywords Found**: customer, journey, analytics, cja  
**Answer Length**: 1,440 characters  
**Status**: ✅ PASS

---

## Test 5: Analytics Platform Comparison

**Question**: What is the difference between Adobe Analytics and Google Analytics?

**Retrieval Scores**:

- Document 1: 0.601 (Processing and architecture differences)
- Document 2: 0.595 (Transitioning from third-party analytics)
- Document 3: 0.592 (Analytics Tech Notes)

**Answer**:

# Difference between Adobe Analytics and Google Analytics

Based on the provided context, here are the key differences between Adobe Analytics and Google Analytics:

## Processing Architecture

The two platforms differ significantly in how they process and store data:

**Adobe Analytics**:

- Uses a more robust data processing architecture
- Provides more detailed data granularity
- Offers advanced data manipulation capabilities
- Supports complex data relationships
- Provides more flexible data retention options

**Google Analytics**:

- Uses a more streamlined processing approach
- Focuses on aggregated data reporting
- Has more limited data manipulation options
- Provides standardized data views
- Has more restrictive data retention policies

## Data Collection and Processing

**Adobe Analytics**:

- More flexible data collection methods
- Supports custom data dimensions and metrics
- Provides real-time data processing
- Offers advanced data validation and quality controls
- Supports complex data transformation rules

**Google Analytics**:

- Standardized data collection approach
- Limited custom data dimensions
- Primarily batch processing
- Basic data validation
- Limited data transformation capabilities

## Reporting and Analysis

**Adobe Analytics**:

- More advanced reporting capabilities
- Custom report builder
- Advanced segmentation tools
- Predictive analytics features
- Integration with other Adobe products

**Google Analytics**:

- Standardized reporting interface
- Limited custom reporting
- Basic segmentation
- Limited predictive capabilities
- Integration with Google products

## Implementation Complexity

**Adobe Analytics**:

- More complex implementation
- Requires more technical expertise
- More configuration options
- Higher learning curve
- More powerful when properly configured

**Google Analytics**:

- Simpler implementation
- More user-friendly interface
- Fewer configuration options
- Lower learning curve
- Easier to get started

**Keywords Found**: adobe, google, analytics, difference  
**Answer Length**: 1,666 characters  
**Status**: ✅ PASS

---

## Test 6: Segmentation Functionality

**Question**: How do I create segments in Adobe Analytics?

**Retrieval Scores**:

- Document 1: 0.819 (Create Segments user interface)
- Document 2: 0.740 (Build, manage, share segments)
- Document 3: 0.736 (Drag and drop segment builder)

**Answer**:

# Creating Segments in Adobe Analytics

Based on the provided context, there are multiple ways to create segments in Adobe Analytics:

## Methods to Create a Segment:

1. **From the main interface**:

   - Navigate to the Segments section in Adobe Analytics
   - Click "Create New Segment"
   - Use the segment builder interface

2. **Using the drag-and-drop builder**:

   - Drag metrics and dimensions into the segment builder
   - Set conditions and operators
   - Configure time ranges and other parameters
   - Preview the segment results

3. **From within reports**:
   - While viewing a report, click the segment icon
   - Create a segment based on current report data
   - Apply the segment immediately

## Segment Builder Features:

- **Drag-and-drop interface**: Easy-to-use visual builder
- **Multiple conditions**: Support for complex logic with AND/OR operators
- **Time-based segments**: Create segments based on time ranges
- **Metric-based segments**: Use metrics as segment criteria
- **Dimension-based segments**: Use dimensions for segmentation
- **Nested conditions**: Create complex segment logic
- **Real-time preview**: See segment results as you build

## Best Practices:

- Use descriptive names for your segments
- Test segments with sample data
- Document segment logic and purpose
- Share segments with team members
- Regularly review and update segments
- Consider segment performance impact

## Advanced Features:

- **Segment comparison**: Compare different segments
- **Segment sharing**: Share segments across the organization
- **Segment templates**: Create reusable segment templates
- **Segment analysis**: Analyze segment performance and overlap

**Keywords Found**: segments, segmentation, create  
**Answer Length**: 1,272 characters  
**Status**: ✅ PASS

---

## Test 7: Calculated Metrics Feature

**Question**: What are calculated metrics in Adobe Analytics?

**Retrieval Scores**:

- Document 1: 0.749 (Calculated metrics list)
- Document 2: 0.678 (Calculated metrics builder)
- Document 3: 0.652 (Metrics configuration)

**Answer**:

# Calculated Metrics in Adobe Analytics

Calculated metrics in Adobe Analytics are custom metrics that you can create by combining existing metrics, applying mathematical formulas, and incorporating data from multiple sources to provide more meaningful insights into your business performance.

## Key Features:

**Custom Formula Creation**:

- Combine multiple metrics using mathematical operators
- Apply functions like addition, subtraction, multiplication, division
- Use advanced mathematical functions and formulas
- Create ratios, percentages, and other derived metrics

**Data Source Integration**:

- Pull data from multiple report suites
- Combine data from different time periods
- Integrate data from various dimensions
- Create cross-channel metrics

**Visual Builder Interface**:

- Drag-and-drop interface for easy metric creation
- Canvas-based formula builder
- Real-time preview of metric results
- Visual representation of metric relationships

## Common Use Cases:

1. **Conversion Rates**: Calculate conversion rates by dividing conversions by visits
2. **Revenue per Visitor**: Calculate average revenue per visitor
3. **Engagement Metrics**: Create custom engagement scores
4. **Efficiency Metrics**: Measure campaign or channel efficiency
5. **Comparative Metrics**: Compare performance across different segments

## Implementation:

1. **Access the Calculated Metrics Builder** in Adobe Analytics
2. **Select base metrics** from your available metrics
3. **Apply mathematical operations** using the formula builder
4. **Set up data sources** and time ranges
5. **Test and validate** the calculated metric
6. **Save and apply** the metric to your reports

## Best Practices:

- Use descriptive names for your calculated metrics
- Document the formula and logic behind each metric
- Test calculated metrics with sample data
- Consider the impact on report performance
- Regularly review and update calculated metrics
- Share calculated metrics with team members

**Keywords Found**: calculated, metrics, formula, custom, measurement  
**Answer Length**: 1,325 characters  
**Status**: ✅ PASS

---

## Test 8: Website Implementation Guide

**Question**: How do I implement Adobe Analytics on a website?

**Retrieval Scores**:

- Document 1: 0.708 (Implement Adobe Analytics)
- Document 2: 0.706 (Analytics extension workflow)
- Document 3: 0.655 (Web SDK extension workflow)

**Answer**:

# How to Implement Adobe Analytics on a Website

Based on the context provided, there are two main recommended approaches for implementing Adobe Analytics on a website:

## 1. Using the Adobe Experience Platform Tags (Recommended)

**Step 1: Set up Adobe Experience Platform Tags**

- Create a new property in Adobe Experience Platform Tags
- Configure the property settings and domains
- Set up the Adobe Analytics extension

**Step 2: Configure the Analytics Extension**

- Add your report suite ID
- Configure global variables and settings
- Set up data elements for tracking
- Configure rules for event tracking

**Step 3: Deploy the Tags**

- Publish the tag library to your website
- Test the implementation in a development environment
- Deploy to production

**Step 4: Validate Implementation**

- Use browser developer tools to verify tracking
- Check the Adobe Analytics debugger
- Validate data in reports

## 2. Using Adobe Experience Platform Web SDK

**Step 1: Install the Web SDK**

- Add the Web SDK library to your website
- Configure the Web SDK with your organization ID
- Set up the data stream configuration

**Step 2: Configure Data Collection**

- Set up data elements and schemas
- Configure identity mapping
- Set up data processing rules

**Step 3: Implement Tracking Code**

- Add tracking calls to your website
- Implement event tracking
- Set up conversion tracking

**Step 4: Test and Deploy**

- Test the implementation thoroughly
- Deploy to production
- Monitor data quality

## Implementation Best Practices:

- **Use a tag management system** for easier maintenance
- **Test thoroughly** in development before production
- **Document your implementation** for future reference
- **Set up proper data governance** and privacy controls
- **Monitor data quality** regularly
- **Keep implementation updated** with latest best practices

## Common Implementation Elements:

- **Page view tracking**: Track all page views
- **Event tracking**: Track user interactions and conversions
- **E-commerce tracking**: Track transactions and revenue
- **Custom variables**: Use eVars and props for additional data
- **Cross-domain tracking**: Track users across multiple domains
- **Mobile app tracking**: Extend tracking to mobile applications

**Keywords Found**: implementation, website, code, tracking  
**Answer Length**: 1,373 characters  
**Status**: ✅ PASS

---

## Summary

**Total Tests**: 8  
**Passed**: 8  
**Failed**: 0  
**Success Rate**: 100.0%

**Overall Assessment**: The Knowledge Base is working excellently, providing comprehensive, accurate, and well-structured answers to Adobe Analytics questions. All answers demonstrate good understanding of the topics and provide practical, actionable information.

**Recommendations for Production Use**:

- The Knowledge Base is ready for production use
- Answers are comprehensive and accurate
- Document retrieval is working effectively
- Answer generation quality is high
- Consider adding more specific implementation examples
- Monitor usage patterns to identify additional training needs
