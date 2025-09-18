"""
Side-by-side comparison UI component for hybrid model architecture.
Provides interface for comparing Gemini and Claude responses.
"""

import streamlit as st
import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd
from ..feedback.feedback_ui import FeedbackUI

class ComparisonUI:
    """Side-by-side comparison UI for model testing."""
    
    def __init__(self, model_provider, query_router):
        """Initialize comparison UI."""
        self.model_provider = model_provider
        self.query_router = query_router
        self.knowledge_base_id = None
        self.aws_clients = None
        self.feedback_ui = FeedbackUI()
        
        # Initialize session state for comparison data
        if 'comparison_history' not in st.session_state:
            st.session_state.comparison_history = []
        
        if 'current_comparison' not in st.session_state:
            st.session_state.current_comparison = None
        
        if 'test_queries' not in st.session_state:
            st.session_state.test_queries = self._get_default_test_queries()
    
    def _generate_source_links(self, query: str) -> List[Dict[str, str]]:
        """Generate relevant Adobe Experience League source links based on query content."""
        query_lower = query.lower()
        
        links = []
        
        # Adobe Analytics links
        if any(keyword in query_lower for keyword in ['analytics', 'aa', 'adobe analytics']):
            links.append({
                'name': 'Adobe Analytics Documentation',
                'url': 'https://experienceleague.adobe.com/en/docs/analytics',
                'type': 'documentation'
            })
        
        # Customer Journey Analytics links
        if any(keyword in query_lower for keyword in ['cja', 'customer journey', 'journey analytics']):
            links.append({
                'name': 'Customer Journey Analytics Documentation',
                'url': 'https://experienceleague.adobe.com/en/docs/customer-journey-analytics',
                'type': 'documentation'
            })
        
        # Adobe Experience Platform links
        if any(keyword in query_lower for keyword in ['aep', 'experience platform', 'platform']):
            links.append({
                'name': 'Real-Time Customer Data Platform Documentation',
                'url': 'https://experienceleague.adobe.com/en/docs/real-time-customer-data-platform',
                'type': 'documentation'
            })
        
        # Mobile SDK links
        if any(keyword in query_lower for keyword in ['mobile', 'sdk', 'app']):
            links.append({
                'name': 'Mobile SDK Documentation',
                'url': 'https://experienceleague.adobe.com/en/docs/mobile',
                'type': 'documentation'
            })
        
        # Identity links
        if any(keyword in query_lower for keyword in ['identity', 'id', 'stitching']):
            links.append({
                'name': 'Identity Service Documentation',
                'url': 'https://experienceleague.adobe.com/en/docs/real-time-customer-data-platform/identity',
                'type': 'documentation'
            })
        
        # Data Collection links
        if any(keyword in query_lower for keyword in ['data collection', 'collection', 'ingestion']):
            links.append({
                'name': 'Data Collection Documentation',
                'url': 'https://experienceleague.adobe.com/en/docs/real-time-customer-data-platform/edge',
                'type': 'documentation'
            })
        
        return links
    
    def _clean_adobe_dnl_text(self, text: str) -> str:
        """Clean Adobe DNL (Display Name Language) markup from text."""
        import re
        
        # Remove [!DNL ...] markup and replace with just the text
        text = re.sub(r'\[!DNL\s+([^\]]+)\]', r'\1', text)
        
        # Remove other common Adobe markup patterns
        text = re.sub(r'\[!UICONTROL\s+([^\]]+)\]', r'\1', text)
        text = re.sub(r'\[!BADGE\s+([^\]]+)\]', r'\1', text)
        text = re.sub(r'\[!NOTE\]', 'Note:', text)
        text = re.sub(r'\[!WARNING\]', 'Warning:', text)
        text = re.sub(r'\[!TIP\]', 'Tip:', text)
        
        return text

    def _convert_s3_uri_to_experience_league_url(self, s3_uri: str) -> str:
        """Convert S3 URI to proper Adobe Experience League URL."""
        if not s3_uri or not s3_uri.startswith('s3://'):
            return s3_uri
        
        # Extract the path after the bucket name
        # s3://bucket-name/adobe-docs/path/to/file.md
        parts = s3_uri.split('/')
        if len(parts) < 4:
            return s3_uri
        
        # Get the path after 'adobe-docs'
        adobe_docs_index = -1
        for i, part in enumerate(parts):
            if part == 'adobe-docs':
                adobe_docs_index = i
                break
        
        if adobe_docs_index == -1 or adobe_docs_index + 1 >= len(parts):
            return s3_uri
        
        # Get the relative path after adobe-docs
        relative_path = '/'.join(parts[adobe_docs_index + 1:])
        
        # Remove file extension
        if relative_path.endswith('.md'):
            relative_path = relative_path[:-3]
        elif relative_path.endswith('.txt'):
            relative_path = relative_path[:-4]
        
        # Map S3 paths to Experience League URLs based on actual Adobe structure
        if relative_path.startswith('adobe-analytics/'):
            # adobe-analytics/path → analytics/path
            exp_league_path = relative_path.replace('adobe-analytics/', 'analytics/')
            # Use /en/docs/ structure for main pages
            if exp_league_path.count('/') <= 1:
                return f"https://experienceleague.adobe.com/en/docs/{exp_league_path}"
            else:
                return f"https://experienceleague.adobe.com/en/docs/{exp_league_path}"
        
        elif relative_path.startswith('customer-journey-analytics/'):
            # customer-journey-analytics/path → customer-journey-analytics/path
            # Use the correct CJA URL structure
            if relative_path.count('/') <= 1:
                return f"https://experienceleague.adobe.com/en/docs/{relative_path}"
            else:
                return f"https://experienceleague.adobe.com/en/docs/{relative_path}"
        
        elif relative_path.startswith('experience-platform/'):
            # experience-platform/path → real-time-customer-data-platform/path
            # Map to Real-Time CDP as it's the main AEP documentation
            aep_path = relative_path.replace('experience-platform/', 'real-time-customer-data-platform/')
            if aep_path.count('/') <= 1:
                return f"https://experienceleague.adobe.com/en/docs/{aep_path}"
            else:
                return f"https://experienceleague.adobe.com/en/docs/{aep_path}"
        
        elif relative_path.startswith('analytics-apis/'):
            # analytics-apis/path → analytics/apis/path
            exp_league_path = relative_path.replace('analytics-apis/', 'analytics/apis/')
            return f"https://experienceleague.adobe.com/en/docs/{exp_league_path}"
        
        elif relative_path.startswith('cja-apis/'):
            # cja-apis/path → customer-journey-analytics/apis/path
            exp_league_path = relative_path.replace('cja-apis/', 'customer-journey-analytics/apis/')
            return f"https://experienceleague.adobe.com/en/docs/{exp_league_path}"
        
        else:
            # Default fallback - try to map to a reasonable URL
            # For unknown paths, try to construct a reasonable URL
            if '/' not in relative_path:
                return f"https://experienceleague.adobe.com/en/docs/{relative_path}"
            else:
                return f"https://experienceleague.adobe.com/en/docs/{relative_path}"
    
    def _extract_knowledge_base_sources(self, result: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract source URLs from knowledge base documents if available."""
        source_urls = []
        
        # Check if the result has knowledge base sources
        if result.get('used_knowledge_base', False):
            # Try to extract from documents if available
            documents = result.get('documents', [])
            for doc in documents:
                location = doc.get('location', {})
                s3_uri = location.get('s3Location', {}).get('uri', '')
                if s3_uri:
                    # Convert S3 URI to Experience League URL
                    exp_league_url = self._convert_s3_uri_to_experience_league_url(s3_uri)
                    
                    # Create a readable display name
                    filename = s3_uri.split('/')[-1]
                    if filename.endswith('.md'):
                        filename = filename[:-3]
                    elif filename.endswith('.txt'):
                        filename = filename[:-4]
                    
                    display_name = filename.replace('_', ' ').replace('-', ' ').title()
                    
                    source_urls.append({
                        'name': display_name,
                        'url': exp_league_url,
                        'type': 'knowledge_base'
                    })
        
        return source_urls
    
    def _render_source_links(self, sources: List[Dict[str, str]], model_name: str):
        """Render source links for a model response."""
        if not sources:
            return
        
        st.markdown(f"**📚 Sources for {model_name}:**")
        
        for i, source in enumerate(sources, 1):
            if source['type'] == 'knowledge_base':
                st.markdown(f"{i}. [{source['name']}]({source['url']}) *(Knowledge Base)*")
            else:
                st.markdown(f"{i}. [{source['name']}]({source['url']})")
        
        st.markdown("---")
    
    def _get_default_test_queries(self) -> List[Dict[str, Any]]:
        """Get default test queries for Adobe Experience League."""
        return [
            {
                'query': 'What is Adobe Analytics and how does it work?',
                'category': 'basic_facts',
                'complexity': 'simple',
                'expected_model': 'claude'
            },
            {
                'query': 'How do I create a calculated metric in Adobe Analytics?',
                'category': 'implementation',
                'complexity': 'medium',
                'expected_model': 'claude'
            },
            {
                'query': 'Compare different attribution models in Adobe Analytics and explain their use cases for e-commerce businesses.',
                'category': 'complex_analysis',
                'complexity': 'complex',
                'expected_model': 'gemini'
            },
            {
                'query': 'Show me JavaScript code for implementing custom event tracking in Adobe Analytics with proper error handling.',
                'category': 'code_examples',
                'complexity': 'medium',
                'expected_model': 'claude'
            },
            {
                'query': 'Why isn\'t my Adobe Analytics tracking code working and how can I debug data collection issues?',
                'category': 'troubleshooting',
                'complexity': 'medium',
                'expected_model': 'claude'
            }
        ]
    
    def render_comparison_interface(self):
        """Render the main comparison interface."""
        st.title("🔄 Model Comparison Interface")
        st.markdown("Compare responses from Gemini and Claude models side-by-side")
        
        # Query input section
        self._render_query_input_section()
        
        # Comparison results
        if st.session_state.current_comparison:
            self._render_comparison_results()
        
        # Test suite section
        with st.expander("🧪 Test Suite", expanded=False):
            self._render_test_suite()
        
        # History section
        with st.expander("📊 Comparison History", expanded=False):
            self._render_comparison_history()
    
    def _render_query_input_section(self):
        """Render query input and options."""
        st.subheader("📝 Query Input")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            query = st.text_area(
                "Enter your query:",
                placeholder="e.g., What is Adobe Analytics and how does it work?",
                height=100,
                key="comparison_query"
            )
        
        with col2:
            complexity = st.selectbox(
                "Complexity Level:",
                ["auto", "simple", "medium", "complex"],
                index=0
            )
            
            context_length = st.slider(
                "Context Length:",
                min_value=0,
                max_value=100000,
                value=0,
                step=1000,
                help="Estimated context length in characters"
            )
        
        # Submit buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🚀 Compare Both Models", type="primary"):
                if query:
                    self._run_comparison(query, complexity, context_length)
                else:
                    st.error("Please enter a query")
        
        with col2:
            if st.button("🎯 Use Smart Routing"):
                if query:
                    self._run_smart_routing(query, complexity, context_length)
                else:
                    st.error("Please enter a query")
        
        with col3:
            if st.button("🧪 Run Test Suite"):
                self._run_test_suite()
    
    def _run_comparison(self, query: str, complexity: str, context_length: int):
        """Run comparison between both models."""
        st.session_state.processing_comparison = True
        
        with st.spinner("Running comparison..."):
            start_time = time.time()
            
            # Query both models with knowledge base if available
            if hasattr(self, 'knowledge_base_id') and self.knowledge_base_id and hasattr(self, 'aws_clients') and self.aws_clients:
                result = self.model_provider.query_both_models_with_kb(
                    query=query,
                    knowledge_base_id=self.knowledge_base_id,
                    aws_clients=self.aws_clients,
                    temperature=0.1,
                    max_tokens={'gemini': 4096, 'claude': 4096}
                )
            else:
                result = self.model_provider.query_both_models(
                    prompt=query,
                    context=f"Context length: {context_length} characters" if context_length > 0 else None
                )
            
            total_time = time.time() - start_time
            
            if result['success']:
                # Store comparison result
                comparison_data = {
                    'timestamp': datetime.now().isoformat(),
                    'query': query,
                    'complexity': complexity,
                    'context_length': context_length,
                    'total_time': total_time,
                    'results': result['results'],
                    'comparison': result['comparison']
                }
                
                st.session_state.current_comparison = comparison_data
                st.session_state.comparison_history.append(comparison_data)
                
                st.success("Comparison completed successfully!")
            else:
                st.error("Comparison failed. Please try again.")
        
        st.session_state.processing_comparison = False
        st.rerun()
    
    def _run_smart_routing(self, query: str, complexity: str, context_length: int):
        """Run query with smart routing."""
        st.session_state.processing_routing = True
        
        with st.spinner("Analyzing query and selecting best model..."):
            # Get routing decision
            decision = self.query_router.determine_best_model(query, context_length)
            
            # Query the recommended model
            if decision.recommended_model == 'gemini':
                result = self.model_provider.query_gemini(query)
            else:
                result = self.model_provider.query_claude_bedrock(query)
            
            if result['success']:
                st.success(f"Query completed using {decision.recommended_model.upper()}")
                st.info(f"**Reasoning:** {decision.reasoning}")
                
                # Display result
                st.subheader(f"🤖 {decision.recommended_model.upper()} Response")
                st.write(result['response'])
                
                # Display metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Response Time", f"{result['response_time']:.2f}s")
                with col2:
                    st.metric("Cost", f"${result['cost']:.4f}")
                with col3:
                    st.metric("Tokens", f"{result['total_tokens']:,}")
            else:
                st.error(f"Query failed: {result['error']}")
        
        st.session_state.processing_routing = False
    
    def _run_test_suite(self):
        """Run the test suite."""
        st.session_state.running_test_suite = True
        
        with st.spinner("Running test suite..."):
            test_results = []
            
            for i, test_query in enumerate(st.session_state.test_queries):
                with st.expander(f"Test {i+1}: {test_query['query'][:50]}...", expanded=False):
                    st.write(f"**Category:** {test_query['category']}")
                    st.write(f"**Expected Complexity:** {test_query['complexity']}")
                    st.write(f"**Expected Model:** {test_query['expected_model']}")
                    
                    # Run comparison with knowledge base if available
                    if hasattr(self, 'knowledge_base_id') and self.knowledge_base_id and hasattr(self, 'aws_clients') and self.aws_clients:
                        result = self.model_provider.query_both_models_with_kb(
                            query=test_query['query'],
                            knowledge_base_id=self.knowledge_base_id,
                            aws_clients=self.aws_clients,
                            temperature=0.1,
                            max_tokens={'gemini': 4096, 'claude': 4096}
                        )
                    else:
                        result = self.model_provider.query_both_models(
                            prompt=test_query['query']
                        )
                    
                    if result['success']:
                        test_results.append({
                            'test_id': i+1,
                            'query': test_query['query'],
                            'category': test_query['category'],
                            'expected_model': test_query['expected_model'],
                            'results': result['results'],
                            'comparison': result['comparison']
                        })
                        
                        # Display results
                        col1, col2 = st.columns(2)
                        
        with col1:
            st.subheader("🤖 Gemini")
            if 'gemini' in result['results'] and result['results']['gemini']['success']:
                gemini_result = result['results']['gemini']
                # Clean Adobe DNL markup from response
                cleaned_response = self._clean_adobe_dnl_text(gemini_result['response'])
                st.write(cleaned_response[:200] + "...")
                st.metric("Time", f"{gemini_result['response_time']:.2f}s")
                st.metric("Cost", f"${gemini_result['cost']:.4f}")
                
                # Source links for Gemini in test
                gemini_sources = []
                kb_sources = self._extract_knowledge_base_sources(gemini_result)
                gemini_sources.extend(kb_sources)
                doc_sources = self._generate_source_links(test_query['query'])
                gemini_sources.extend(doc_sources)
                
                if gemini_sources:
                    self._render_source_links(gemini_sources, "Gemini")
            else:
                st.error("Gemini failed")
                        
        with col2:
            st.subheader("🤖 Claude")
            if 'claude' in result['results'] and result['results']['claude']['success']:
                claude_result = result['results']['claude']
                # Clean Adobe DNL markup from response
                cleaned_response = self._clean_adobe_dnl_text(claude_result['response'])
                st.write(cleaned_response[:200] + "...")
                st.metric("Time", f"{claude_result['response_time']:.2f}s")
                st.metric("Cost", f"${claude_result['cost']:.4f}")
                
                # Source links for Claude in test
                claude_sources = []
                kb_sources = self._extract_knowledge_base_sources(claude_result)
                claude_sources.extend(kb_sources)
                doc_sources = self._generate_source_links(test_query['query'])
                claude_sources.extend(doc_sources)
                
                if claude_sources:
                    self._render_source_links(claude_sources, "Claude")
            else:
                st.error("Claude failed")
            
            # Store test results
            st.session_state.test_suite_results = test_results
            st.success(f"Test suite completed! {len(test_results)} tests run.")
        
        st.session_state.running_test_suite = False
        st.rerun()
    
    def _render_comparison_results(self):
        """Render comparison results."""
        if not st.session_state.current_comparison:
            return
        
        comparison = st.session_state.current_comparison
        results = comparison['results']
        
        st.subheader("📊 Comparison Results")
        
        # Query info
        st.write(f"**Query:** {comparison['query']}")
        st.write(f"**Total Time:** {comparison['total_time']:.2f}s")
        
        # Model responses
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🤖 Gemini 2.0 Flash")
            if 'gemini' in results and results['gemini']['success']:
                gemini_result = results['gemini']
                # Clean Adobe DNL markup from response
                cleaned_response = self._clean_adobe_dnl_text(gemini_result['response'])
                st.write(cleaned_response)
                
                # Metrics
                col1_1, col1_2, col1_3 = st.columns(3)
                with col1_1:
                    st.metric("⏱️ Time", f"{gemini_result['response_time']:.2f}s")
                with col1_2:
                    st.metric("💰 Cost", f"${gemini_result['cost']:.4f}")
                with col1_3:
                    st.metric("🔤 Tokens", f"{gemini_result['total_tokens']:,}")
                
                # Source links for Gemini
                gemini_sources = []
                # Add knowledge base sources if available
                kb_sources = self._extract_knowledge_base_sources(gemini_result)
                gemini_sources.extend(kb_sources)
                # Add general documentation links
                doc_sources = self._generate_source_links(comparison['query'])
                gemini_sources.extend(doc_sources)
                
                if gemini_sources:
                    self._render_source_links(gemini_sources, "Gemini 2.0 Flash")
            else:
                st.error("Gemini failed to respond")
        
        with col2:
            st.subheader("🤖 Claude 3.5 Sonnet")
            if 'claude' in results and results['claude']['success']:
                claude_result = results['claude']
                # Clean Adobe DNL markup from response
                cleaned_response = self._clean_adobe_dnl_text(claude_result['response'])
                st.write(cleaned_response)
                
                # Metrics
                col2_1, col2_2, col2_3 = st.columns(3)
                with col2_1:
                    st.metric("⏱️ Time", f"{claude_result['response_time']:.2f}s")
                with col2_2:
                    st.metric("💰 Cost", f"${claude_result['cost']:.4f}")
                with col2_3:
                    st.metric("🔤 Tokens", f"{claude_result['total_tokens']:,}")
                
                # Source links for Claude
                claude_sources = []
                # Add knowledge base sources if available
                kb_sources = self._extract_knowledge_base_sources(claude_result)
                claude_sources.extend(kb_sources)
                # Add general documentation links
                doc_sources = self._generate_source_links(comparison['query'])
                claude_sources.extend(doc_sources)
                
                if claude_sources:
                    self._render_source_links(claude_sources, "Claude 3.5 Sonnet")
            else:
                st.error("Claude failed to respond")
        
        # Comparison analysis
        if 'comparison' in comparison:
            comp = comparison['comparison']
            
            st.subheader("📈 Comparison Analysis")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if 'winner' in comp and 'speed' in comp['winner']:
                    st.metric("🏆 Speed Winner", comp['winner']['speed'].title())
                    if 'speed_difference' in comp['winner']:
                        st.caption(f"Difference: {comp['winner']['speed_difference']:.2f}s")
            
            with col2:
                if 'winner' in comp and 'cost' in comp['winner']:
                    st.metric("💰 Cost Winner", comp['winner']['cost'].title())
                    if 'cost_difference_percentage' in comp['winner']:
                        st.caption(f"Difference: {comp['winner']['cost_difference_percentage']:.1f}%")
            
            with col3:
                if comp.get('both_successful', False):
                    st.metric("✅ Success Rate", "100%")
                else:
                    st.metric("❌ Success Rate", "Partial")
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Save to History"):
                st.success("Saved to comparison history!")
        
        with col2:
            if st.button("📊 Export Results"):
                self._export_comparison_results(comparison)
        
        with col3:
            if st.button("🔄 Run Again"):
                st.rerun()
        
        # Feedback collection
        if 'gemini' in results and 'claude' in results and results['gemini']['success'] and results['claude']['success']:
            st.markdown("---")
            st.subheader("📝 Rate the Responses")
            st.markdown("Help us improve the models by rating the responses:")
            
            # Get responses for feedback
            gemini_response = results['gemini']['response']
            claude_response = results['claude']['response']
            
            # Render feedback form
            feedback_id = self.feedback_ui.render_feedback_form(
                query=comparison['query'],
                gemini_response=gemini_response,
                claude_response=claude_response
            )
            
            if feedback_id:
                st.session_state.last_feedback_id = feedback_id
    
    def _render_test_suite(self):
        """Render test suite interface."""
        st.subheader("🧪 Test Suite Management")
        
        # Test queries management
        st.write("**Test Queries:**")
        for i, test_query in enumerate(st.session_state.test_queries):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.write(f"{i+1}. {test_query['query']}")
            
            with col2:
                if st.button("Run", key=f"run_test_{i}"):
                    self._run_single_test(test_query)
            
            with col3:
                if st.button("Remove", key=f"remove_test_{i}"):
                    st.session_state.test_queries.pop(i)
                    st.rerun()
        
        # Add new test query
        with st.expander("➕ Add New Test Query", expanded=False):
            new_query = st.text_input("Query:")
            new_category = st.selectbox("Category:", ["basic_facts", "implementation", "complex_analysis", "code_examples", "troubleshooting"])
            new_complexity = st.selectbox("Complexity:", ["simple", "medium", "complex"])
            new_expected_model = st.selectbox("Expected Model:", ["gemini", "claude", "auto"])
            
            if st.button("Add Test Query"):
                if new_query:
                    st.session_state.test_queries.append({
                        'query': new_query,
                        'category': new_category,
                        'complexity': new_complexity,
                        'expected_model': new_expected_model
                    })
                    st.success("Test query added!")
                    st.rerun()
        
        # Test suite results
        if 'test_suite_results' in st.session_state:
            st.subheader("📊 Test Suite Results")
            
            # Summary metrics
            results = st.session_state.test_suite_results
            total_tests = len(results)
            successful_tests = sum(1 for r in results if r['results'])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Tests", total_tests)
            with col2:
                st.metric("Successful", successful_tests)
            with col3:
                st.metric("Success Rate", f"{successful_tests/total_tests*100:.1f}%" if total_tests > 0 else "0%")
            
            # Detailed results
            if st.button("📊 Show Detailed Results"):
                self._render_detailed_test_results(results)
    
    def _render_comparison_history(self):
        """Render comparison history."""
        if not st.session_state.comparison_history:
            st.info("No comparison history yet. Run some comparisons to see results here.")
            return
        
        st.subheader("📊 Comparison History")
        
        # Summary table
        history_data = []
        for i, comparison in enumerate(st.session_state.comparison_history):
            history_data.append({
                'Index': i+1,
                'Query': comparison['query'][:50] + "..." if len(comparison['query']) > 50 else comparison['query'],
                'Timestamp': comparison['timestamp'][:19],
                'Total Time': f"{comparison['total_time']:.2f}s",
                'Both Successful': comparison['comparison'].get('both_successful', False)
            })
        
        df = pd.DataFrame(history_data)
        st.dataframe(df, use_container_width=True)
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Export History"):
                self._export_comparison_history()
        
        with col2:
            if st.button("🗑️ Clear History"):
                st.session_state.comparison_history = []
                st.success("History cleared!")
                st.rerun()
        
        with col3:
            if st.button("📈 Show Analytics"):
                self._render_history_analytics()
    
    def _export_comparison_results(self, comparison: Dict[str, Any]):
        """Export comparison results."""
        export_data = {
            'timestamp': comparison['timestamp'],
            'query': comparison['query'],
            'results': comparison['results'],
            'comparison': comparison['comparison']
        }
        
        st.download_button(
            label="📥 Download Results",
            data=json.dumps(export_data, indent=2),
            file_name=f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    def _export_comparison_history(self):
        """Export comparison history."""
        st.download_button(
            label="📥 Download History",
            data=json.dumps(st.session_state.comparison_history, indent=2),
            file_name=f"comparison_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    def _render_history_analytics(self):
        """Render analytics from comparison history."""
        if not st.session_state.comparison_history:
            return
        
        st.subheader("📈 Comparison Analytics")
        
        # Calculate metrics
        total_comparisons = len(st.session_state.comparison_history)
        successful_comparisons = sum(1 for c in st.session_state.comparison_history if c['comparison'].get('both_successful', False))
        
        # Average times
        gemini_times = []
        claude_times = []
        
        for comparison in st.session_state.comparison_history:
            results = comparison['results']
            if 'gemini' in results and results['gemini']['success']:
                gemini_times.append(results['gemini']['response_time'])
            if 'claude' in results and results['claude']['success']:
                claude_times.append(results['claude']['response_time'])
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Comparisons", total_comparisons)
        
        with col2:
            st.metric("Success Rate", f"{successful_comparisons/total_comparisons*100:.1f}%")
        
        with col3:
            if gemini_times:
                st.metric("Avg Gemini Time", f"{sum(gemini_times)/len(gemini_times):.2f}s")
        
        with col4:
            if claude_times:
                st.metric("Avg Claude Time", f"{sum(claude_times)/len(claude_times):.2f}s")
        
        # Performance comparison chart
        if gemini_times and claude_times:
            st.subheader("📊 Performance Comparison")
            
            chart_data = pd.DataFrame({
                'Gemini': gemini_times,
                'Claude': claude_times
            })
            
            st.line_chart(chart_data)
