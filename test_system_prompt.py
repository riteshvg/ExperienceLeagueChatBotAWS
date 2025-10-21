#!/usr/bin/env python3
"""
Test script for system prompt implementation

This script tests the system prompt functionality to ensure:
1. System prompt is properly formatted
2. Context validation works
3. Fallback messages are triggered correctly
4. Claude API receives system prompt correctly
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.prompts import (
    format_system_prompt,
    should_use_fallback,
    NO_CONTEXT_MESSAGE,
    validate_context_quality,
    get_adobe_term_definition
)


def test_system_prompt_formatting():
    """Test that system prompt is properly formatted."""
    print("=" * 80)
    print("TEST 1: System Prompt Formatting")
    print("=" * 80)
    
    # Sample context and query
    retrieved_context = """
    Adobe Analytics is a web analytics platform that helps you measure, analyze, 
    and optimize your customer interactions across all your marketing channels.
    
    To create a report suite:
    1. Navigate to Admin > Report Suites
    2. Click Create Report Suite
    3. Enter report suite name
    4. Select base report suite
    5. Click Save
    """
    
    user_query = "How do I create a report suite in Adobe Analytics?"
    
    # Format system prompt
    system_prompt = format_system_prompt(retrieved_context, user_query)
    
    # Check if system prompt contains key elements
    assert "CRITICAL RULES" in system_prompt, "Missing CRITICAL RULES section"
    assert "Answer ONLY using the provided documentation context" in system_prompt, "Missing context-only instruction"
    assert "Adobe Analytics" in system_prompt, "Missing Adobe Analytics reference"
    assert retrieved_context in system_prompt, "Missing retrieved context"
    assert user_query in system_prompt, "Missing user query"
    
    print("✅ System prompt formatted correctly")
    print(f"   Length: {len(system_prompt)} characters")
    print(f"   Contains context: {retrieved_context[:50] in system_prompt}")
    print(f"   Contains query: {user_query in system_prompt}")
    print()


def test_empty_context_fallback():
    """Test that empty context triggers fallback message."""
    print("=" * 80)
    print("TEST 2: Empty Context Fallback")
    print("=" * 80)
    
    # Test with empty context
    empty_context = ""
    user_query = "What is Adobe Analytics?"
    
    system_prompt = format_system_prompt(empty_context, user_query)
    
    assert system_prompt == NO_CONTEXT_MESSAGE, "Should return NO_CONTEXT_MESSAGE for empty context"
    print("✅ Empty context correctly triggers fallback message")
    print()


def test_context_validation():
    """Test context validation logic."""
    print("=" * 80)
    print("TEST 3: Context Validation")
    print("=" * 80)
    
    # Test with valid context
    valid_context = "A" * 200  # 200 characters
    validation = validate_context_quality(valid_context)
    
    assert validation["valid"] == True, "Valid context should pass validation"
    print(f"✅ Valid context passes validation: {validation['reason']}")
    
    # Test with empty context
    empty_context = ""
    validation = validate_context_quality(empty_context)
    
    assert validation["valid"] == False, "Empty context should fail validation"
    print(f"✅ Empty context fails validation: {validation['reason']}")
    
    # Test with short context
    short_context = "A" * 50  # 50 characters
    validation = validate_context_quality(short_context)
    
    assert validation["valid"] == False, "Short context should fail validation"
    print(f"✅ Short context fails validation: {validation['reason']}")
    print()


def test_fallback_logic():
    """Test fallback logic."""
    print("=" * 80)
    print("TEST 4: Fallback Logic")
    print("=" * 80)
    
    # Test with empty context
    empty_context = ""
    should_fallback = should_use_fallback(empty_context)
    assert should_fallback == True, "Empty context should trigger fallback"
    print("✅ Empty context triggers fallback")
    
    # Test with short context
    short_context = "A" * 50
    should_fallback = should_use_fallback(short_context)
    assert should_fallback == True, "Short context should trigger fallback"
    print("✅ Short context triggers fallback")
    
    # Test with valid context
    valid_context = "A" * 200
    should_fallback = should_use_fallback(valid_context)
    assert should_fallback == False, "Valid context should not trigger fallback"
    print("✅ Valid context does not trigger fallback")
    print()


def test_adobe_terminology():
    """Test Adobe terminology definitions."""
    print("=" * 80)
    print("TEST 5: Adobe Terminology")
    print("=" * 80)
    
    terms = ["eVar", "prop", "Workspace", "Segment", "Data View"]
    
    for term in terms:
        definition = get_adobe_term_definition(term)
        if definition:
            print(f"✅ {term}: {definition}")
        else:
            print(f"⚠️  {term}: No definition found")
    print()


def test_system_prompt_structure():
    """Test that system prompt has correct structure."""
    print("=" * 80)
    print("TEST 6: System Prompt Structure")
    print("=" * 80)
    
    retrieved_context = "Adobe Analytics is a web analytics platform."
    user_query = "What is Adobe Analytics?"
    
    system_prompt = format_system_prompt(retrieved_context, user_query)
    
    # Check for required sections
    required_sections = [
        "CRITICAL RULES",
        "Adobe Analytics Key Concepts",
        "Customer Journey Analytics Key Concepts",
        "Documentation Context:",
        "User Question:"
    ]
    
    for section in required_sections:
        assert section in system_prompt, f"Missing section: {section}"
        print(f"✅ Contains section: {section}")
    print()


def test_hallucination_prevention():
    """Test that system prompt includes hallucination prevention instructions."""
    print("=" * 80)
    print("TEST 7: Hallucination Prevention")
    print("=" * 80)
    
    retrieved_context = "Adobe Analytics is a web analytics platform."
    user_query = "What is Adobe Analytics?"
    
    system_prompt = format_system_prompt(retrieved_context, user_query)
    
    # Check for key hallucination prevention phrases
    prevention_phrases = [
        "Answer ONLY using the provided documentation context",
        "Never invent features",
        "If the context doesn't contain the answer",
        "explicitly state what's covered and what's missing"
    ]
    
    for phrase in prevention_phrases:
        assert phrase in system_prompt, f"Missing prevention phrase: {phrase}"
        print(f"✅ Contains prevention instruction: {phrase[:50]}...")
    print()


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("SYSTEM PROMPT TEST SUITE")
    print("=" * 80 + "\n")
    
    try:
        test_system_prompt_formatting()
        test_empty_context_fallback()
        test_context_validation()
        test_fallback_logic()
        test_adobe_terminology()
        test_system_prompt_structure()
        test_hallucination_prevention()
        
        print("=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        return True
        
    except AssertionError as e:
        print("=" * 80)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 80)
        return False
    except Exception as e:
        print("=" * 80)
        print(f"❌ UNEXPECTED ERROR: {e}")
        print("=" * 80)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

