"""
Handler functions for special queries.
"""
from typing import Dict, Any, Optional, List
from memory import ConversationMemory
from function_registry import function_registry

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
def register_special_queries():
    """Register special queries with their handler function."""

    # Register exact special queries
    function_registry.register_special_queries(
        function_name="handle_special_query",
        queries=[
            # Queries for raising a ticket or connecting with a counselor
            "i want to raise a query",
            "can i raise a query",
            "can i raise a ticket",
            "can i connect to someone",
            "can i speak to the counsellor",
            # Queries for tracking application status
            "How can I track my application status?"
        ]
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
