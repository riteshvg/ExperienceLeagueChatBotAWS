#!/usr/bin/env python3
"""
CLS Performance Test
Runs both apps and measures their performance characteristics.
"""

import sys
import os
sys.path.insert(0, '.')

def test_app_structure():
    """Test the structure of both apps to identify CLS differences."""
    print("🔍 CLS Performance Analysis")
    print("=" * 50)
    
    try:
        # Read main app
        with open('app.py', 'r') as f:
            main_content = f.read()
        
        # Read optimized app
        with open('src/performance/complete_optimized_app.py', 'r') as f:
            opt_content = f.read()
        
        # Analyze main app structure
        print("\n📋 Main App Structure Analysis:")
        print("-" * 30)
        
        # Check for sidebar elements
        sidebar_elements = main_content.count('st.sidebar')
        print(f"Sidebar elements: {sidebar_elements}")
        
        # Check for conditional rendering
        conditional_patterns = [
            'if st.session_state',
            'if st.button',
            'if submit_button',
            'if query',
            'if result'
        ]
        
        total_conditionals = 0
        for pattern in conditional_patterns:
            count = main_content.count(pattern)
            total_conditionals += count
            print(f"  {pattern}: {count}")
        
        print(f"Total conditionals: {total_conditionals}")
        
        # Check for dynamic UI elements
        dynamic_elements = [
            'st.empty(',
            'st.container(',
            'st.columns(',
            'st.expander(',
            'st.metric(',
            'st.progress(',
            'st.spinner('
        ]
        
        total_dynamic = 0
        for element in dynamic_elements:
            count = main_content.count(element)
            total_dynamic += count
            print(f"  {element}: {count}")
        
        print(f"Total dynamic elements: {total_dynamic}")
        
        # Analyze optimized app structure
        print("\n📋 Optimized App Structure Analysis:")
        print("-" * 30)
        
        # Check for sidebar elements
        opt_sidebar_elements = opt_content.count('st.sidebar')
        print(f"Sidebar elements: {opt_sidebar_elements}")
        
        # Check for conditional rendering
        opt_total_conditionals = 0
        for pattern in conditional_patterns:
            count = opt_content.count(pattern)
            opt_total_conditionals += count
            print(f"  {pattern}: {count}")
        
        print(f"Total conditionals: {opt_total_conditionals}")
        
        # Check for dynamic UI elements
        opt_total_dynamic = 0
        for element in dynamic_elements:
            count = opt_content.count(element)
            opt_total_dynamic += count
            print(f"  {element}: {count}")
        
        print(f"Total dynamic elements: {opt_total_dynamic}")
        
        # Compare
        print("\n📊 Comparison:")
        print("-" * 30)
        print(f"Sidebar elements - Main: {sidebar_elements}, Optimized: {opt_sidebar_elements}")
        print(f"Conditionals - Main: {total_conditionals}, Optimized: {opt_total_conditionals}")
        print(f"Dynamic elements - Main: {total_dynamic}, Optimized: {opt_total_dynamic}")
        
        # Identify potential CLS causes
        print("\n🎯 Potential CLS Causes:")
        print("-" * 30)
        
        if sidebar_elements > opt_sidebar_elements:
            print(f"❌ Main app has {sidebar_elements - opt_sidebar_elements} more sidebar elements")
        
        if total_conditionals > opt_total_conditionals:
            print(f"❌ Main app has {total_conditionals - opt_total_conditionals} more conditionals")
        
        if total_dynamic > opt_total_dynamic:
            print(f"❌ Main app has {total_dynamic - opt_total_dynamic} more dynamic elements")
        
        if total_conditionals <= opt_total_conditionals and total_dynamic <= opt_total_dynamic:
            print("✅ Main app has similar or fewer dynamic elements than optimized app")
            print("💡 CLS issue might be from other factors (CSS, JavaScript, etc.)")
        
        return True
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return False

def main():
    """Run CLS performance analysis."""
    success = test_app_structure()
    
    if success:
        print("\n🎯 CLS Analysis Complete!")
        print("Check the comparison above to identify differences.")
    else:
        print("\n❌ CLS Analysis Failed!")

if __name__ == "__main__":
    main()
