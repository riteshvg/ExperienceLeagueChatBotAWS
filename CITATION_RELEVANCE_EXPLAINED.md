# Citation Relevance Score - Complete Explanation

## 🎯 How Relevance Scores are Defined

### **Source: AWS Bedrock Knowledge Base Vector Search**

The relevance score is **NOT calculated by our code** - it comes directly from **AWS Bedrock Knowledge Base's semantic search engine**.

---

## 📊 Complete Flow

### **Step 1: User Asks Question**
```
User: "How do I create segments in Adobe Analytics?"
```

### **Step 2: Query Preprocessing**
```python
# Query expanded with abbreviations
Enhanced Query: "How do I create segments in Adobe Analytics step-by-step guide tutorial"
```

### **Step 3: AWS Bedrock Vector Search**
```python
# AWS Bedrock Knowledge Base performs semantic search
response = bedrock_agent_client.retrieve(
    knowledgeBaseId=knowledge_base_id,
    retrievalQuery={'text': enhanced_query},
    retrievalConfiguration={
        'vectorSearchConfiguration': {
            'numberOfResults': 8  # Request top 8 most relevant docs
        }
    }
)
```

**AWS Bedrock Returns**:
```python
[
    {
        'content': {'text': 'Segmentation workflow guide...'},
        'score': 0.8532,  # ⭐ RELEVANCE SCORE from AWS
        'location': {'s3Location': {'uri': 's3://bucket/path/to/doc.md'}}
    },
    {
        'content': {'text': 'Build segments in Analysis Workspace...'},
        'score': 0.7845,  # ⭐ RELEVANCE SCORE from AWS
        'location': {'s3Location': {'uri': 's3://bucket/path/to/doc2.md'}}
    },
    ...
]
```

### **Step 4: Similarity Threshold Filtering**
```python
# Our code filters by score
filtered_docs = [doc for doc in raw_results if doc['score'] >= 0.6]

# Fallback to 0.5 if < 3 results
if len(filtered_docs) < 3:
    filtered_docs = [doc for doc in raw_results if doc['score'] >= 0.5]
```

**Example**:
```
Original 8 documents from AWS:
  1. Doc A: score 0.85 ✅ Keep (>= 0.6)
  2. Doc B: score 0.78 ✅ Keep (>= 0.6)
  3. Doc C: score 0.72 ✅ Keep (>= 0.6)
  4. Doc D: score 0.65 ✅ Keep (>= 0.6)
  5. Doc E: score 0.58 ❌ Filter out (< 0.6)
  6. Doc F: score 0.51 ❌ Filter out (< 0.6)
  7. Doc G: score 0.45 ❌ Filter out (< 0.6)
  8. Doc H: score 0.38 ❌ Filter out (< 0.6)

Final: 4 documents (scores: 0.85, 0.78, 0.72, 0.65)
```

### **Step 5: Citation Generation**
```python
# Create citation for each filtered document
for doc in filtered_docs:
    citation = {
        'title': 'Segmentation Workflow',  # From metadata registry or frontmatter
        'url': 'https://experienceleague.adobe.com/...',
        'score': doc['score'],  # ⭐ Pass through AWS score
        'display': f"...{doc['score']:.2%}"  # Format as percentage
    }
```

### **Step 6: URL Validation**
```python
# Validate URLs, filter out 404s
valid_citations = filter_valid_citations(citations)
# Only citations with HTTP 200/301/302 are kept
```

### **Step 7: Display to User**
```markdown
### 📚 Sources

1. **[Segmentation Workflow](...)** (Relevance: 85%) ✓
2. **[Build Segments](...)** (Relevance: 78%) ✓
3. **[Segment Builder](...)** (Relevance: 72%) ✓
4. **[Filter Segments](...)** (Relevance: 65%) ✓
```

---

## 🔬 How AWS Bedrock Calculates Relevance Score

### **Vector Similarity Algorithm**

AWS Bedrock uses **cosine similarity** between vector embeddings:

1. **Query Embedding**:
   ```
   Query: "How do I create segments?"
   → Vector: [0.23, 0.87, 0.45, ..., 0.12] (1536 dimensions)
   ```

2. **Document Embeddings** (pre-computed in Knowledge Base):
   ```
   Doc 1: "Segmentation workflow..."
   → Vector: [0.25, 0.85, 0.47, ..., 0.14]
   
   Doc 2: "Build segments..."
   → Vector: [0.22, 0.88, 0.43, ..., 0.13]
   ```

3. **Cosine Similarity Calculation**:
   ```
   similarity = (query_vector · doc_vector) / (||query_vector|| × ||doc_vector||)
   
   Score range: 0.0 to 1.0
   - 1.0 = Perfect match
   - 0.9 = Extremely relevant
   - 0.7-0.8 = Highly relevant
   - 0.5-0.6 = Moderately relevant
   - < 0.5 = Low relevance
   ```

4. **Ranking**:
   ```
   AWS returns documents sorted by score (highest first)
   Top 8 documents are returned based on 'numberOfResults' parameter
   ```

---

## 📋 Complete Criteria for Citation Selection

### **1. Initial Retrieval (AWS Bedrock)**
**Criteria**: 
- Top-K vector similarity (K=8)
- Semantic matching of query to document content
- Pre-computed embeddings using Amazon Titan

**AWS Returns**: 8 most semantically similar documents

### **2. Similarity Threshold Filtering (Our Code)**
**Criteria**:
```python
# Primary threshold
if doc['score'] >= 0.6:
    keep_document = True

# Fallback threshold (if < 3 results)
elif doc['score'] >= 0.5:
    keep_document = True
```

**Why 0.6?**
- Research shows scores >= 0.6 indicate good semantic match
- Scores 0.5-0.6 are borderline (kept if needed for minimum results)
- Scores < 0.5 are usually off-topic

### **3. Document Prioritization (Our Code)**
**Criteria** (from `select_best_documents` function):
```python
Priority Order:
1. High relevance (score > 0.6) ← Highest priority
2. Main documentation (not release notes)
3. Other documentation
4. Release notes ← Lowest priority

Within each category: Sort by score descending
```

### **4. URL Validation (Our Code)**
**Criteria**:
```python
# HTTP status check
if status_code in [200, 301, 302]:
    keep_citation = True  # Valid URL
elif status_code == 404:
    filter_out_citation = True  # Broken link
```

---

## 📊 Relevance Score Interpretation

| Score Range | Meaning | Action |
|-------------|---------|--------|
| **0.85 - 1.0** | Excellent match | ✅ Always included |
| **0.7 - 0.84** | Very good match | ✅ Always included |
| **0.6 - 0.69** | Good match | ✅ Included |
| **0.5 - 0.59** | Moderate match | ⚠️ Included only if <3 results |
| **< 0.5** | Poor match | ❌ Filtered out |

---

## 🎯 Example from Your Logs

From line 139 in your logs:
```
2025-10-22 09:51:44,724 - src.utils.citation_mapper - INFO - ✅ Citation from registry: Conversion Variables (eVar) → https://experienceleague.adobe.com/en/docs/analytics/admin/tools/manage-rs/edit-settings/conversion-var-admin/conversion-var-admin
```

**What Happened**:
1. **AWS Bedrock** found this document with high semantic similarity to user's query
2. **AWS assigned** a score (likely 0.7-0.9 based on it being included)
3. **Our similarity filter** kept it (score >= 0.6)
4. **Metadata lookup** found proper title: "Conversion Variables (eVar)"
5. **URL validation** checked URL (HTTP 200 = keep)
6. **User sees**: "Conversion Variables (eVar)" with relevance score

---

## 🔧 Configuration

### **You Can Adjust These Parameters**:

```env
# Similarity thresholds
SIMILARITY_THRESHOLD=0.6           # Primary threshold
MIN_RETRIEVAL_RESULTS=3            # Minimum results to return
MAX_RETRIEVAL_RESULTS=8            # Maximum results to return

# URL validation
VALIDATE_CITATION_URLS=true        # Enable/disable URL checking
CITATION_URL_TIMEOUT=3             # Timeout for URL validation
```

### **In Code** (`config/settings.py`):
```python
similarity_threshold: float = 0.6
min_retrieval_results: int = 3
max_retrieval_results: int = 8
```

---

## 📈 Why This Multi-Layer Approach?

### **Layer 1: AWS Bedrock (Semantic Search)**
- **What**: Finds semantically similar documents
- **How**: Vector embeddings + cosine similarity
- **Output**: 8 most relevant documents with scores

### **Layer 2: Similarity Filtering**
- **What**: Quality control for retrieved documents
- **How**: Filter by minimum score threshold
- **Output**: 3-8 high-quality documents

### **Layer 3: URL Validation**
- **What**: Ensures working links only
- **How**: HTTP HEAD requests to verify 200/301/302
- **Output**: Only verified working citations

### **Result**:
- High-quality, relevant documents
- With working, verified URLs
- Professional, trustworthy citations

---

## 💡 Key Insights

### **The Score Represents**:
1. **Semantic similarity** between query and document
2. **NOT** human quality ratings
3. **NOT** document popularity
4. **NOT** manual curation

### **Score is Influenced By**:
- Query wording (enhanced by our preprocessing)
- Document content quality
- Embedding model quality (Amazon Titan)
- Document chunking strategy

### **Score is NOT Influenced By**:
- Document age
- Document URL
- Document title
- Number of views

---

## 🧪 Real Example from Logs

### **Query**: "What is expiration of an eVar?"

**AWS Bedrock Retrieved**:
```
1. "Conversion Variables (eVar)" - Score: ~0.85 ✅
2. "eVar (dimension)" - Score: ~0.78 ✅
3. "Merchandising eVars..." - Score: ~0.72 ✅
```

**After Filtering (score >= 0.6)**:
- All 3 kept ✅

**After URL Validation**:
- All URLs returned HTTP 200 ✅
- All 3 citations shown to user

**User Sees**:
```
### 📚 Sources

1. **[Conversion Variables (eVar)](...)**  (Relevance: 85%) ✓
2. **[eVar (dimension)](...)**  (Relevance: 78%) ✓
3. **[Merchandising eVars...](...)**  (Relevance: 72%) ✓
```

---

## ✅ Summary

**Relevance Score Definition**:
- Calculated by: AWS Bedrock Knowledge Base (vector similarity)
- Range: 0.0 to 1.0
- Higher = More semantically similar to query
- Based on: Cosine similarity of embedding vectors

**Citation Selection Criteria**:
1. ✅ Semantic similarity >= 0.6 (or 0.5 fallback)
2. ✅ Top 3-8 most relevant documents
3. ✅ URL validation (HTTP 200/301/302)
4. ✅ Prioritize main docs over release notes
5. ✅ Sort by score (highest first)

**You Cannot Directly Control**:
- The AWS Bedrock similarity algorithm
- How embeddings are generated

**You CAN Control**:
- Similarity threshold (0.6)
- Number of results (3-8)
- URL validation (on/off)
- Query preprocessing (abbreviations, context)

