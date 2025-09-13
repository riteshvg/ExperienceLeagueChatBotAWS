#!/usr/bin/env python3
"""
Comprehensive CLS Analysis Test for app.py
Identifies all potential CLS-causing elements.
"""

import sys
import os
sys.path.insert(0, '.')

def analyze_cls_causes():
    """Analyze all potential CLS causes in app.py."""
    print("🔍 Comprehensive CLS Analysis")
    print("=" * 50)
    
    try:
        with open('app.py', 'r') as f:
            content = f.read()
        
        # Find all potential CLS-causing elements
        cls_patterns = [
            ('st.success(', 'Success messages'),
            ('st.warning(', 'Warning messages'),
            ('st.error(', 'Error messages'),
            ('st.info(', 'Info messages'),
            ('st.expander(', 'Expandable sections'),
            ('st.metric(', 'Metric displays'),
            ('st.progress(', 'Progress bars'),
            ('st.empty(', 'Dynamic placeholders'),
            ('st.spinner(', 'Loading spinners'),
            ('st.columns(', 'Column layouts'),
            ('st.container(', 'Container elements'),
            ('st.rerun(', 'Page reruns'),
            ('if st.session_state', 'Session state conditionals'),
            ('if st.button', 'Button conditionals'),
            ('if submit_button', 'Submit button conditionals')
        ]
        
        # Analyze render_main_page_minimal function
        print("\n📋 Analyzing render_main_page_minimal function...")
        start = content.find('def render_main_page_minimal():')
        if start != -1:
            next_def = content.find('\ndef ', start + 1)
            if next_def == -1:
                next_def = len(content)
            function_content = content[start:next_def]
            
            found_elements = []
            for pattern, description in cls_patterns:
                if pattern in function_content:
                    lines = function_content.split('\n')
                    for i, line in enumerate(lines):
                        if pattern in line:
                            found_elements.append(f"  Line {i+1}: {description} - {line.strip()}")
            
            if found_elements:
                print(f"❌ Found {len(found_elements)} potential CLS elements:")
                for element in found_elements:
                    print(element)
            else:
                print("✅ No potential CLS elements found")
        
        # Analyze process_query_with_full_initialization function
        print("\n📋 Analyzing process_query_with_full_initialization function...")
        start = content.find('def process_query_with_full_initialization(')
        if start != -1:
            next_def = content.find('\ndef ', start + 1)
            if next_def == -1:
                next_def = len(content)
            function_content = content[start:next_def]
            
            found_elements = []
            for pattern, description in cls_patterns:
                if pattern in function_content:
                    lines = function_content.split('\n')
                    for i, line in enumerate(lines):
                        if pattern in line:
                            found_elements.append(f"  Line {i+1}: {description} - {line.strip()}")
            
            if found_elements:
                print(f"❌ Found {len(found_elements)} potential CLS elements:")
                for element in found_elements:
                    print(element)
            else:
                print("✅ No potential CLS elements found")
        
        # Compare with optimized app
        print("\n📋 Comparing with optimized app...")
        try:
            with open('src/performance/complete_optimized_app.py', 'r') as f:
                opt_content = f.read()
            
            # Find render_optimized_chat_interface function
            start = opt_content.find('def render_optimized_chat_interface(')
            if start != -1:
                next_def = opt_content.find('\ndef ', start + 1)
                if next_def == -1:
                    next_def = len(opt_content)
                function_content = opt_content[start:next_def]
                
                found_elements = []
                for pattern, description in cls_patterns:
                    if pattern in function_content:
                        lines = function_content.split('\n')
                        for i, line in enumerate(lines):
                            if pattern in line:
                                found_elements.append(f"  Line {i+1}: {description} - {line.strip()}")
                
                if found_elements:
                    print(f"❌ Optimized app has {len(found_elements)} potential CLS elements:")
                    for element in found_elements:
                        print(element)
                else:
                    print("✅ Optimized app has no potential CLS elements")
        except FileNotFoundError:
            print("❌ Optimized app file not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return False

def main():
    """Run comprehensive CLS analysis."""
    success = analyze_cls_causes()
    
    if success:
        print("\n🎯 CLS Analysis Complete!")
        print("Check the results above to identify CLS-causing elements.")
    else:
        print("\n❌ CLS Analysis Failed!")

if __name__ == "__main__":
    main()
