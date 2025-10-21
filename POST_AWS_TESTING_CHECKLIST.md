# Post-AWS Restoration Testing Checklist

## ⏳ To Be Completed When AWS Bedrock Service is Restored

---

## 🧪 LIVE QUERY TESTS

### Test 1: Adobe Analytics - Segments
- [ ] Query: "How do I create a segment in Adobe Analytics?"
- [ ] Verify citations appear at bottom of response
- [ ] Click Experience League link
- [ ] Verify link works (not 404)
- [ ] Check URL pattern: `/en/docs/analytics/components/segmentation/...`
- [ ] Click GitHub link to verify backup works

**Expected Citation**:
```
1. **[Segment Workflow](https://experienceleague.adobe.com/en/docs/analytics/components/segmentation/seg-workflow)** (Relevance: XX%) • [View on GitHub →]
```

---

### Test 2: Customer Journey Analytics - Data Views
- [ ] Query: "What is a data view in CJA?"
- [ ] Verify CJA citations appear
- [ ] Click Experience League link
- [ ] Verify link works (not 404)
- [ ] Check URL pattern: `/en/docs/analytics-platform/...`
- [ ] Verify no broken 'cja-' prefix issues

**Expected Citation**:
```
1. **[Data Views](https://experienceleague.adobe.com/en/docs/analytics-platform/data-views/...)** (Relevance: XX%) • [View on GitHub →]
```

---

### Test 3: Adobe Experience Platform - Connectors
- [ ] Query: "How do I set up a source connector in AEP?"
- [ ] Verify AEP citations appear
- [ ] Click Experience League link
- [ ] Verify link works (not 404)
- [ ] Check URL pattern: `/en/docs/experience-platform/sources/connectors/...`

**Expected Citation**:
```
1. **[Analytics Connector](https://experienceleague.adobe.com/en/docs/experience-platform/sources/connectors/adobe-applications/analytics)** (Relevance: XX%) • [View on GitHub →]
```

---

### Test 4: Multi-Topic Query
- [ ] Query: "Explain eVars vs props in Adobe Analytics"
- [ ] Verify multiple citations appear
- [ ] All citations numbered correctly (1, 2, 3...)
- [ ] No duplicate URLs
- [ ] All links clickable
- [ ] All links work (not 404)
- [ ] Relevance scores shown

**Expected Citations**:
```
1. **[eVar](https://experienceleague.adobe.com/en/docs/analytics/components/dimensions/evar)** (Relevance: XX%)
2. **[Props](https://experienceleague.adobe.com/en/docs/analytics/components/dimensions/props)** (Relevance: XX%)
```

---

### Test 5: Cross-Product Query
- [ ] Query: "What's the difference between Adobe Analytics and Customer Journey Analytics?"
- [ ] Verify citations from both products
- [ ] AA citations use `/analytics/...` pattern
- [ ] CJA citations use `/analytics-platform/...` pattern
- [ ] All links work

---

## 🔍 URL VERIFICATION TESTS

### Manual URL Tests:

#### Adobe Analytics (Already Verified ✅):
```bash
curl -I "https://experienceleague.adobe.com/en/docs/analytics/components/dimensions/evar"
# Expected: HTTP 200 ✅

curl -I "https://experienceleague.adobe.com/en/docs/analytics/admin/admin-console/permissions/product-profile"
# Expected: HTTP 200 ✅
```

#### Customer Journey Analytics (Need to Test):
```bash
curl -I "https://experienceleague.adobe.com/en/docs/analytics-platform/data-views/create-dataview"
# Expected: HTTP 200 or 301 redirect

curl -I "https://experienceleague.adobe.com/en/docs/analytics-platform/connections/overview"
# Expected: HTTP 200 or 301 redirect
```

#### Adobe Experience Platform (Need to Test):
```bash
curl -I "https://experienceleague.adobe.com/en/docs/experience-platform/sources/connectors/adobe-applications/analytics"
# Expected: HTTP 200 or 301 redirect
```

---

## 📋 CITATION DISPLAY VERIFICATION

### Check These Elements in UI:

- [ ] Citations appear after response
- [ ] Horizontal line separator before citations
- [ ] "📚 Sources" heading displayed
- [ ] Numbered list (1., 2., 3...)
- [ ] Clickable Experience League links (blue)
- [ ] Clickable GitHub links (gray)
- [ ] Relevance percentages shown
- [ ] No broken formatting
- [ ] Mobile-responsive display

---

## 🐛 ERROR CHECKING

### Application Logs:
- [ ] Check for citation-related INFO messages
- [ ] No ERROR messages for citation generation
- [ ] No WARNING messages (except expected fallbacks)
- [ ] Logging shows successful URL generation

**Expected Log Output**:
```
INFO - Adobe Analytics mapping: ... → https://experienceleague.adobe.com/...
INFO - Generated citation: Segment Workflow → https://experienceleague.adobe.com/...
INFO - Added 3 citations to response
```

### Console Output:
- [ ] No JavaScript errors
- [ ] No 404 errors when clicking links
- [ ] No broken image icons
- [ ] Streamlit renders markdown correctly

---

## 📊 QUALITY CHECKS

### Citation Accuracy:
- [ ] Titles match document content
- [ ] URLs point to correct pages
- [ ] Relevance scores make sense (high scores for good matches)
- [ ] No duplicate citations

### User Experience:
- [ ] Citations don't clutter the response
- [ ] Visual separation is clear
- [ ] Links are obviously clickable
- [ ] GitHub backup provides value

---

## 🔧 IF ISSUES FOUND

### If URLs Return 404:

1. **Document the URL**:
   ```
   Failed URL: https://experienceleague.adobe.com/...
   Expected page: [description]
   Path in S3: ...
   ```

2. **Check GitHub**:
   - Does the GitHub link work?
   - Is the file in a different location?

3. **Test Alternative Patterns**:
   ```bash
   # Try with /using/ prefix
   https://experienceleague.adobe.com/en/docs/analytics-platform/using/...
   
   # Try without /en/
   https://experienceleague.adobe.com/docs/analytics-platform/...
   
   # Try with .html
   https://experienceleague.adobe.com/docs/analytics-platform/....html
   ```

4. **Update Mapping**:
   - Modify `src/utils/citation_mapper.py`
   - Update the appropriate `_map_*_url()` function
   - Rerun tests
   - Commit fix

---

## ✅ SUCCESS CRITERIA

All tests pass when:
- [ ] All citations display correctly
- [ ] All Experience League links work (HTTP 200)
- [ ] All GitHub links work
- [ ] No 404 errors
- [ ] Titles are readable
- [ ] Relevance scores shown
- [ ] Works for AA, CJA, AEP queries
- [ ] No application errors
- [ ] Logs show successful generation

---

## 📝 TESTING NOTES

**Document Your Findings**:
- Working URLs (✅)
- Broken URLs (❌) with details
- Suggested fixes
- Pattern observations

**Share Results**:
- Screenshot of working citations
- List of any 404 URLs
- Curl test outputs
- Log file excerpts

---

## 🚀 AFTER TESTING

Once all tests pass:
1. Mark all checklist items complete
2. Document any fixes made
3. Update this checklist with results
4. Consider merging to main branch
5. Deploy to production

---

**This checklist will be ready when AWS Bedrock service is restored!**

