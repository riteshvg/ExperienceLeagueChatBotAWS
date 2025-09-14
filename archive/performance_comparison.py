"""
Performance Comparison Tool
Compare main app vs complete optimized app side by side
"""

import streamlit as st
import time
import threading
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "src"))

# Import both applications
try:
    from app import (
        get_cached_settings, get_cached_aws_clients, process_query_optimized,
        SmartRouter, retrieve_documents_from_kb, invoke_bedrock_model
    )
    from src.performance.complete_optimized_app import (
        OptimizedStreamlitApp, process_query_with_smart_routing as opt_process_query
    )
    IMPORTS_SUCCESSFUL = True
except Exception as e:
    st.error(f"❌ Import error: {e}")
    IMPORTS_SUCCESSFUL = False

# Performance tracking
class PerformanceTracker:
    def __init__(self):
        self.results = {}
        self.lock = threading.Lock()
    
    def start_timer(self, test_id: str) -> str:
        """Start timing a test"""
        timer_id = f"{test_id}_{int(time.time() * 1000)}"
        with self.lock:
            self.results[timer_id] = {
                'test_id': test_id,
                'start_time': time.time(),
                'end_time': None,
                'duration': None,
                'success': False,
                'error': None,
                'response_length': 0,
                'model_used': None
            }
        return timer_id
    
    def end_timer(self, timer_id: str, success: bool = True, error: str = None, 
                  response_length: int = 0, model_used: str = None):
        """End timing a test"""
        with self.lock:
            if timer_id in self.results:
                self.results[timer_id].update({
                    'end_time': time.time(),
                    'success': success,
                    'error': error,
                    'response_length': response_length,
                    'model_used': model_used
                })
                self.results[timer_id]['duration'] = (
                    self.results[timer_id]['end_time'] - self.results[timer_id]['start_time']
                )
    
    def get_results(self, test_id: str) -> Dict[str, Any]:
        """Get results for a specific test"""
        with self.lock:
            test_results = {k: v for k, v in self.results.items() if v['test_id'] == test_id}
            return test_results
    
    def get_latest_result(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest result for a test"""
        results = self.get_results(test_id)
        if results:
            return max(results.values(), key=lambda x: x['start_time'])
        return None

# Global performance tracker
perf_tracker = PerformanceTracker()

def process_main_app_query(query: str, settings, aws_clients, smart_router) -> Tuple[bool, str, float, str]:
    """Process query using main app optimized function"""
    try:
        timer_id = perf_tracker.start_timer("main_app")
        
        result = process_query_optimized(
            query,
            settings.bedrock_knowledge_base_id,
            smart_router,
            aws_clients
        )
        
        success = result.get("success", False)
        answer = result.get("answer", "")
        model_used = result.get("model_used", "unknown")
        
        perf_tracker.end_timer(
            timer_id, 
            success=success, 
            error=result.get("error"),
            response_length=len(answer),
            model_used=model_used
        )
        
        return success, answer, perf_tracker.get_latest_result("main_app")['duration'], model_used
        
    except Exception as e:
        perf_tracker.end_timer(timer_id, success=False, error=str(e))
        return False, f"Error: {str(e)}", 0, "error"

def process_optimized_app_query(query: str, settings, aws_clients, smart_router) -> Tuple[bool, str, float, str]:
    """Process query using complete optimized app"""
    try:
        timer_id = perf_tracker.start_timer("optimized_app")
        
        result = opt_process_query(
            query,
            settings.bedrock_knowledge_base_id,
            smart_router,
            aws_clients
        )
        
        success = result.get("success", False)
        answer = result.get("answer", "")
        model_used = result.get("model_used", "unknown")
        
        perf_tracker.end_timer(
            timer_id, 
            success=success, 
            error=result.get("error"),
            response_length=len(answer),
            model_used=model_used
        )
        
        return success, answer, perf_tracker.get_latest_result("optimized_app")['duration'], model_used
        
    except Exception as e:
        perf_tracker.end_timer(timer_id, success=False, error=str(e))
        return False, f"Error: {str(e)}", 0, "error"

def render_comparison_interface():
    """Render the side-by-side comparison interface"""
    st.title("🚀 Performance Comparison Tool")
    st.markdown("**Compare Main App vs Complete Optimized App**")
    st.markdown("---")
    
    if not IMPORTS_SUCCESSFUL:
        st.error("❌ Failed to import required modules. Please check the file structure.")
        return
    
    # Initialize components
    if 'settings' not in st.session_state:
        st.session_state.settings = get_cached_settings()
    
    if 'aws_clients' not in st.session_state and st.session_state.settings:
        st.session_state.aws_clients = get_cached_aws_clients(st.session_state.settings)
    
    if 'smart_router' not in st.session_state:
        st.session_state.smart_router = SmartRouter(haiku_only_mode=False)
    
    # Check if components are ready
    if not st.session_state.settings:
        st.error("❌ Settings not loaded. Please check your configuration.")
        return
    
    if not st.session_state.aws_clients:
        st.error("❌ AWS clients not loaded. Please check your AWS configuration.")
        return
    
    # Query input
    st.subheader("❓ Enter Query for Comparison")
    
    with st.form("comparison_form"):
        query = st.text_area(
            "Enter your question:",
            placeholder="e.g., How do I implement Adobe Analytics on my website?",
            height=100,
            help="This query will be processed by both versions simultaneously"
        )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            submit_button = st.form_submit_button("🚀 Run Comparison", use_container_width=True)
        
        with col2:
            clear_button = st.form_submit_button("🗑️ Clear Results", use_container_width=True)
        
        with col3:
            history_button = st.form_submit_button("📊 View History", use_container_width=True)
    
    # Handle form submission
    if submit_button and query:
        run_comparison(query)
    
    if clear_button:
        if 'comparison_results' in st.session_state:
            del st.session_state.comparison_results
        st.rerun()
    
    if history_button:
        show_performance_history()

def run_comparison(query: str):
    """Run the performance comparison"""
    st.subheader("🔄 Running Comparison...")
    
    # Create columns for side-by-side results
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📱 Main App (Optimized)")
        with st.spinner("Processing with main app..."):
            main_success, main_answer, main_duration, main_model = process_main_app_query(
                query, 
                st.session_state.settings, 
                st.session_state.aws_clients, 
                st.session_state.smart_router
            )
    
    with col2:
        st.markdown("### 🚀 Complete Optimized App")
        with st.spinner("Processing with optimized app..."):
            opt_success, opt_answer, opt_duration, opt_model = process_optimized_app_query(
                query, 
                st.session_state.settings, 
                st.session_state.aws_clients, 
                st.session_state.smart_router
            )
    
    # Display results
    display_comparison_results(
        main_success, main_answer, main_duration, main_model,
        opt_success, opt_answer, opt_duration, opt_model,
        query
    )

def display_comparison_results(main_success, main_answer, main_duration, main_model,
                              opt_success, opt_answer, opt_duration, opt_model, query):
    """Display the comparison results"""
    
    # Store results in session state
    st.session_state.comparison_results = {
        'query': query,
        'timestamp': datetime.now(),
        'main_app': {
            'success': main_success,
            'answer': main_answer,
            'duration': main_duration,
            'model': main_model
        },
        'optimized_app': {
            'success': opt_success,
            'answer': opt_answer,
            'duration': opt_duration,
            'model': opt_model
        }
    }
    
    # Results summary
    st.subheader("📊 Comparison Results")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Main App Time", 
            f"{main_duration:.2f}s" if main_duration else "Error",
            help="Time taken by main app"
        )
    
    with col2:
        st.metric(
            "Optimized App Time", 
            f"{opt_duration:.2f}s" if opt_duration else "Error",
            help="Time taken by optimized app"
        )
    
    with col3:
        if main_duration and opt_duration:
            speedup = main_duration / opt_duration if opt_duration > 0 else 0
            st.metric(
                "Speed Improvement", 
                f"{speedup:.1f}x" if speedup > 1 else f"{1/speedup:.1f}x slower",
                help="Performance comparison"
            )
        else:
            st.metric("Speed Improvement", "N/A")
    
    with col4:
        if main_duration and opt_duration:
            time_diff = abs(main_duration - opt_duration)
            st.metric(
                "Time Difference", 
                f"{time_diff:.2f}s",
                help="Absolute time difference"
            )
        else:
            st.metric("Time Difference", "N/A")
    
    # Detailed results
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📱 Main App Results")
        if main_success:
            st.success("✅ Success")
            st.info(f"**Model:** {main_model}")
            st.info(f"**Duration:** {main_duration:.3f} seconds")
            st.markdown("**Response:**")
            st.text_area("Main App Response", main_answer, height=200, key="main_response", label_visibility="collapsed")
        else:
            st.error("❌ Failed")
            st.error(f"**Error:** {main_answer}")
    
    with col2:
        st.markdown("### 🚀 Optimized App Results")
        if opt_success:
            st.success("✅ Success")
            st.info(f"**Model:** {opt_model}")
            st.info(f"**Duration:** {opt_duration:.3f} seconds")
            st.markdown("**Response:**")
            st.text_area("Optimized App Response", opt_answer, height=200, key="opt_response", label_visibility="collapsed")
        else:
            st.error("❌ Failed")
            st.error(f"**Error:** {opt_answer}")
    
    # Performance analysis
    if main_success and opt_success:
        st.subheader("📈 Performance Analysis")
        
        if main_duration < opt_duration:
            st.success(f"🏆 **Main App is faster by {opt_duration - main_duration:.2f} seconds**")
        elif opt_duration < main_duration:
            st.success(f"🏆 **Optimized App is faster by {main_duration - opt_duration:.2f} seconds**")
        else:
            st.info("🤝 **Both apps performed equally**")
        
        # Response quality comparison
        if len(main_answer) > 0 and len(opt_answer) > 0:
            st.markdown("**Response Quality:**")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Main App Response Length", f"{len(main_answer)} chars")
            with col2:
                st.metric("Optimized App Response Length", f"{len(opt_answer)} chars")

def show_performance_history():
    """Show performance history"""
    st.subheader("📊 Performance History")
    
    if 'comparison_results' not in st.session_state:
        st.info("No comparison results available yet.")
        return
    
    results = st.session_state.comparison_results
    
    st.markdown(f"**Last Query:** {results['query']}")
    st.markdown(f"**Timestamp:** {results['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create a simple history table
    import pandas as pd
    
    history_data = {
        'App Version': ['Main App', 'Optimized App'],
        'Success': [results['main_app']['success'], results['optimized_app']['success']],
        'Duration (s)': [results['main_app']['duration'], results['optimized_app']['duration']],
        'Model': [results['main_app']['model'], results['optimized_app']['model']],
        'Response Length': [len(results['main_app']['answer']), len(results['optimized_app']['answer'])]
    }
    
    df = pd.DataFrame(history_data)
    st.dataframe(df, use_container_width=True)

def main():
    """Main function"""
    st.set_page_config(
        page_title="Performance Comparison",
        page_icon="🚀",
        layout="wide"
    )
    
    # Sidebar
    st.sidebar.title("🚀 Performance Comparison")
    st.sidebar.markdown("**Compare Main App vs Complete Optimized App**")
    
    # System status
    st.sidebar.subheader("🔧 System Status")
    
    if IMPORTS_SUCCESSFUL:
        st.sidebar.success("✅ Imports successful")
    else:
        st.sidebar.error("❌ Import failed")
    
    # Performance tracker stats
    st.sidebar.subheader("📊 Performance Stats")
    
    main_results = perf_tracker.get_results("main_app")
    opt_results = perf_tracker.get_results("optimized_app")
    
    if main_results:
        latest_main = perf_tracker.get_latest_result("main_app")
        st.sidebar.metric("Main App Tests", len(main_results))
        if latest_main:
            st.sidebar.metric("Latest Main App Time", f"{latest_main['duration']:.2f}s")
    
    if opt_results:
        latest_opt = perf_tracker.get_latest_result("optimized_app")
        st.sidebar.metric("Optimized App Tests", len(opt_results))
        if latest_opt:
            st.sidebar.metric("Latest Optimized App Time", f"{latest_opt['duration']:.2f}s")
    
    # Main interface
    render_comparison_interface()

if __name__ == "__main__":
    main()
