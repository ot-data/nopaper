"""
Test script for special query handling through the HTTP API.
"""
import requests
import json
import uuid
import pytest
from tests.conftest import SERVER_URL

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

@pytest.mark.integration
@pytest.mark.http
@pytest.mark.skip_if_no_server
def test_query(query: str) -> None:
    """Test a single query and print the result."""
    print(f"\nTesting query: '{query}'")

    # Generate a unique session ID
    session_id = str(uuid.uuid4())

    # Create the request payload
    payload = {
        "query": query,
        "session_id": session_id,
        "institution_id": "lpu",
        "personal_info": {}
    }

    # Send the request
    try:
        response = requests.post(f"{SERVER_URL}/chat", json=payload)
        response.raise_for_status()

        # Parse the response
        response_data = response.json()
        print(f"Response: {response_data}")

        # Check if it's a special query response
        is_special_query = False
        for resp in response_data.get("responses", []):
            if resp.get("content") == "{{RAISE_QUERY}}":
                is_special_query = True
                break

        if is_special_query:
            print("✅ Correct special query response: {{RAISE_QUERY}}")
        else:
            print("❌ Not a special query response")

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to the server: {str(e)}")
        print(f"Make sure the backend server is running on {SERVER_URL}")

def run_tests():
    """Run all tests."""
    print("\n=== Testing Exact Match Queries ===")
    for query in EXACT_MATCH_QUERIES:
        test_query(query)

    print("\n=== Testing Pattern Match Queries ===")
    for query in PATTERN_MATCH_QUERIES:
        test_query(query)

    # print("\n=== Testing Non-Matching Queries ===")
    # for query in NON_MATCHING_QUERIES:
    #     test_query(query)

if __name__ == "__main__":
    run_tests()
