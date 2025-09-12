#!/usr/bin/env python3
"""
Update app.py to add streaming functionality
"""

import re

def update_app_for_streaming():
    """Update app.py to include streaming functionality."""
    
    # Read the current app.py file
    with open('app.py', 'r') as file:
        content = file.read()
    
    # Add import for streaming functions at the top
    import_addition = """
# Import streaming functionality
from streaming_app_functions import render_streaming_chat_interface, process_query_with_streaming
"""
    
    # Find the imports section and add the streaming import
    content = re.sub(
        r'(from src\.integrations\.streamlit_analytics_simple import.*?\n)',
        r'\1' + import_addition,
        content
    )
    
    # Replace the main page rendering with streaming version
    content = re.sub(
        r'def render_main_page\(settings, aws_clients, aws_error, kb_status, kb_error, smart_router, analytics_service=None\):.*?(?=def render_admin_page)',
        '''def render_main_page(settings, aws_clients, aws_error, kb_status, kb_error, smart_router, analytics_service=None):
    """Render the main page with streaming chat interface."""
    # Use the new streaming chat interface
    render_streaming_chat_interface()
    
    # Render chat history sidebar
    render_chat_history_sidebar()
    
    # Render feedback section
    render_feedback_section(analytics_service)
''',
        content,
        flags=re.DOTALL
    )
    
    # Write the updated content back
    with open('app.py', 'w') as file:
        file.write(content)
    
    print("✅ App updated for streaming functionality!")

def main():
    """Main function to update app.py."""
    print("🚀 Updating app.py for streaming responses...")
    update_app_for_streaming()
    print("✅ Streaming functionality added to app.py!")

if __name__ == "__main__":
    main()
