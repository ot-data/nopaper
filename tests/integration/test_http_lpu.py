import requests
import json
import time
import pytest
from tests.conftest import SERVER_URL

@pytest.mark.integration
@pytest.mark.http
@pytest.mark.skip_if_no_server
def test_query(query, personal_info, institution_id, session_id):
    # Prepare the request
    url = f"{SERVER_URL}/chat"
    data = {
        'query': query,
        'personal_info': personal_info,
        'institution_id': institution_id,
        'session_id': session_id
    }

    print(f"\nSending message with session_id: {session_id}")

    # Send the request
    response = requests.post(url, json=data)

    # Process the response
    if response.status_code == 200:
        print(f"\n\n===== QUERY: {query} =====")
        responses = response.json().get('responses', [])
        for resp in responses:
            if resp.get('type') == 'response':
                print(resp.get('content', ''), end='')
        print("\n\n[End of response]")
    else:
        print(f"\nError: {response.status_code} - {response.text}")

def main():
    institution_id = "lpu"
    # Use a fixed session ID for consistent memory across requests
    session_id = "test_session_123"

    # Personal information
    personal_info = {
        'name': 'Rahul Sharma',
        'program': 'B.Tech Computer Science',
        'current_semester': '5',
        'academic_background': 'Science',
        'location': 'Delhi',
        'career_interest': 'Artificial Intelligence',
        'industry_preference': 'Information Technology, Research'
    }

    # Test queries
    queries = [
        # First query - should be remembered
        "How can I complete the admission process?",
        # "Tell me about LPU's Computer Science program",

        # # Memory query - should return the first question
        # "What was my previous question?",

        # # Another regular query
        # "What are the career opportunities after completing B.Tech in Computer Science at LPU?",

        # # Memory query again - should return the career opportunities question
        # "What was my last question?"
    ]

    for query in queries:
        test_query(query, personal_info, institution_id, session_id)
        time.sleep(1)  # Small delay between queries

if __name__ == "__main__":
    main()
