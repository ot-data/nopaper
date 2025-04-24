"""
Test script for special query handling with dynamic function calling.
"""
import asyncio
import sys
import os
import re
import pytest
from typing import Dict, Any, Optional, List, Tuple

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from backend.function_registry import FunctionRegistry
from backend.memory import ConversationMemory

# Test queries
EXACT_MATCH_QUERIES = [
    "i want to raise a query",
    "can i raise a query",
    "can i raise a ticket",
    "can i connect to someone",
    "can i speak to the counsellor",
    "How can I track my application status?"
]

PATTERN_MATCH_QUERIES = [
    "I'd like to raise a ticket please",
    "I need to submit a query",
    "Can I file a complaint?",
    "I want to talk to someone from support",
    "Is there anyone I can speak with?",
    "How do I check my application status?",
    "Where can I see the status of my admission?",
    "I need to know how my application is progressing"
]

NON_MATCHING_QUERIES = [
    "What is the fee structure?",
    "Tell me about the computer science program",
    "When is the application deadline?",
    "What are the hostel facilities?",
    "Do you offer scholarships?"
]

# Create a fresh function registry for testing
function_registry = FunctionRegistry()

# Register the handler function
@function_registry.register
async def handle_special_query(
    query: str,
    memory: Optional[ConversationMemory] = None,
    **kwargs
) -> Dict[str, Any]:
    """Handle all special queries with the standard RAISE_QUERY response."""
    if memory:
        memory.add_interaction(query, "{{RAISE_QUERY}}")
    return {"responses": [{"type": "response", "content": "{{RAISE_QUERY}}"}]}

# Register special queries
function_registry.register_special_queries(
    function_name="handle_special_query",
    queries=EXACT_MATCH_QUERIES
)

# Register patterns for variations of special queries
function_registry.register_special_patterns(
    function_name="handle_special_query",
    patterns=[
        # Patterns for raising a query/ticket
        r"(raise|submit|create|open|file|log)\s+(a\s+)?(query|ticket|issue|concern|complaint|problem)",
        # Patterns for connecting with someone
        r"(connect|speak|talk|chat|communicate)\s+(to|with)\s+(a\s+)?(someone|counsellor|counselor|advisor|person|representative|agent|staff|support)",
        r"(need|want)\s+(to\s+)?(speak|talk|connect|chat|communicate)",
        r"is there (someone|anyone) i can (talk|speak|chat) (to|with)",
        # Patterns for tracking application status
        r"(track|check|know|see|find out|get)\s+(my\s+)?(application|admission)\s+(status|progress|update)",
        r"(how|where)\s+(can|do|could|would|should|might)\s+(i|we)\s+(track|check|see|find|know)\s+(my|the)\s+(application|admission)",
        r"(where|how)\s+can\s+i\s+see\s+(the\s+)?(status|progress)\s+of\s+my\s+(application|admission)",
        r"(need|want)\s+to\s+(know|see|check)\s+(how|if)\s+my\s+(application|admission)\s+(is\s+)?(progressing|going|doing)"
    ]
)

@pytest.mark.parametrize("query", EXACT_MATCH_QUERIES + PATTERN_MATCH_QUERIES)
@pytest.mark.asyncio
async def test_matching_query(query: str) -> None:
    """Test that matching queries return the correct response."""
    # Check if the query matches a special query handler
    match_result = function_registry.find_special_query_handler(query)

    # Assert that the query matches a handler
    assert match_result is not None, f"Query '{query}' did not match any handler"

    func_name, arguments = match_result

    # Call the handler function directly
    memory = ConversationMemory(max_history=5)
    arguments["memory"] = memory

    # Call the handler function directly
    handler_func = function_registry.functions[func_name]["function"]
    result = await handler_func(**arguments)

    # Check that the response is correct
    assert "responses" in result, f"Expected 'responses' in result, got {result}"
    assert len(result["responses"]) > 0, f"Expected non-empty responses, got {result['responses']}"

    response = result["responses"][0]
    assert response["type"] == "response", f"Expected response type 'response', got '{response['type']}'"
    assert response["content"] == "{{RAISE_QUERY}}", f"Expected content '{{RAISE_QUERY}}', got '{response['content']}'"

@pytest.mark.parametrize("query", NON_MATCHING_QUERIES)
@pytest.mark.asyncio
async def test_non_matching_query(query: str) -> None:
    """Test that non-matching queries don't match any handler."""
    # Check if the query matches a special query handler
    match_result = function_registry.find_special_query_handler(query)

    # Assert that the query doesn't match any handler
    assert match_result is None, f"Query '{query}' unexpectedly matched handler {match_result[0]}"

if __name__ == "__main__":
    print("This test file is now designed to be run with pytest.")
    print("Run with: python -m pytest tests/unit/backend/test_special_queries.py -v")
