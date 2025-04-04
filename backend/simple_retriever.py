import os
import re
from typing import Dict, List, Any, Tuple

class SimpleRetriever:
    def __init__(self, config: Dict):
        self.config = config

    def retrieve(self, query: str, advanced: bool = True) -> Dict:
        # Simplified retriever that returns sample results
        return {
            "retrievalResults": [
                {
                    "content": {"text": "LPU offers a comprehensive admission process for various programs. The admission process typically involves an entrance exam, followed by counseling and document verification."},
                    "score": 0.95,
                    "location": {"type": "WEB", "webLocation": {"url": "https://www.lpu.in/admission/"}}
                },
                {
                    "content": {"text": "For undergraduate engineering programs, students need to appear for LPUNEST (LPU National Entrance and Scholarship Test) or have a valid JEE Main score."},
                    "score": 0.92,
                    "location": {"type": "WEB", "webLocation": {"url": "https://www.lpu.in/admission/engineering.php"}}
                },
                {
                    "content": {"text": "International students can apply through the International Students Office and may have different admission requirements."},
                    "score": 0.88,
                    "location": {"type": "WEB", "webLocation": {"url": "https://www.lpu.in/international/"}}
                }
            ]
        }

    def format_retrieval_results(self, response: Dict) -> Tuple[str, str]:
        # Format the retrieval results
        if "retrievalResults" not in response or not response["retrievalResults"]:
            return "No content available.", ""

        formatted_content = []
        reference_links = []

        for i, result in enumerate(response["retrievalResults"], 1):
            content = result["content"]["text"]
            score = result.get("score", "N/A")
            location = result.get("location", {})

            if location.get("type") == "WEB":
                url = location.get("webLocation", {}).get("url", None)
                if url:
                    reference_links.append(f"- [Source {i}]({url})")

            formatted_content.append(f"SOURCE {i} [Score: {score}]:\n{content}\n")

        return "\n".join(formatted_content), "\n".join(reference_links)

    def get_specific_source_urls(self, response: Dict) -> str:
        # Format reference links
        if "retrievalResults" not in response or not response["retrievalResults"]:
            return ""

        reference_links = []

        for i, result in enumerate(response["retrievalResults"], 1):
            location = result.get("location", {})
            content = result.get("content", {}).get("text", "")

            # Create a descriptive title based on content
            title = self._generate_title_from_content(content, i)

            if location.get("type") == "WEB":
                url = location.get("webLocation", {}).get("url", None)
                if url:
                    reference_links.append(f"- [{title}]({url})")

        return "\n".join(reference_links)

    def _generate_title_from_content(self, content: str, index: int) -> str:
        """Generate a descriptive title from content"""
        # Extract keywords from content
        if "admission" in content.lower():
            return "LPU Admission Information"
        elif "engineering" in content.lower():
            return "LPU Engineering Programs"
        elif "international" in content.lower():
            return "LPU International Student Resources"
        elif "scholarship" in content.lower():
            return "LPU Scholarship Details"
        elif "placement" in content.lower():
            return "LPU Placement Information"
        elif "hostel" in content.lower() or "accommodation" in content.lower():
            return "LPU Campus Accommodation"
        else:
            return f"LPU Information Resource {index}"
