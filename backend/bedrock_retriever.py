import os
import re
import boto3
from functools import lru_cache
from typing import Dict, List, Any

class EnhancedBedrockRetriever:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Get AWS configuration from config
        self.kb_id = config["aws"]["s3_kb_id"]
        self.region = config["aws"]["region"]
        self.access_key = config["aws"]["access_key"]
        self.secret_key = config["aws"]["secret_key"]

        # Get retrieval configuration
        self.num_results = config["retrieval"]["num_results"]
        self.min_score = config["retrieval"]["min_score"]

        self.session = boto3.Session(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region
        )
        self.bedrock_client = self.session.client("bedrock-agent-runtime")
        self.s3_client = self.session.client("s3")

        self.synonyms = {
            "lpu": ["lovely professional university", "lpu university", "lovely university"],
            "fee": ["fees", "tuition", "cost", "payment"],
            "admission": ["admissions", "enrollment", "joining", "application"],
            "course": ["program", "degree", "curriculum", "study"],
        }

    def preprocess_query(self, query: str) -> str:
        processed = query.lower().strip()
        acronyms = {
            "lpu": "LPU",
            "cse": "computer science engineering",
            "ece": "electronics and communication engineering",
            "ai": "artificial intelligence",
            "ml": "machine learning"
        }
        for acronym, full_form in acronyms.items():
            pattern = r'\b' + re.escape(acronym) + r'\b'
            processed = re.sub(pattern, full_form, processed)
        processed = re.sub(r'\s+', ' ', processed)
        processed = re.sub(r'[^\w\s]', '', processed)
        return processed

    def expand_query(self, query: str) -> List[str]:
        query_terms = query.split()
        expanded_queries = [query]
        for i, term in enumerate(query_terms):
            if term in self.synonyms:
                for synonym in self.synonyms[term]:
                    new_query = query_terms.copy()
                    new_query[i] = synonym
                    expanded_queries.append(" ".join(new_query))
        return expanded_queries[:3]

    @lru_cache(maxsize=32)
    def cached_retrieve(self, query: str) -> Dict:
        try:
            response = self.bedrock_client.retrieve(
                knowledgeBaseId=self.kb_id,
                retrievalQuery={
                    "text": query,
                    "filters": {
                        "customer_id": customer_id
                }
                },
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": self.num_results
                    }
                }
            )
            return response
        except Exception as e:
            return {"error": str(e), "retrievalResults": []}

    def retrieve(self, query: str, advanced: bool = True) -> Dict:
        processed_query = self.preprocess_query(query)
        if advanced:
            query_variations = self.expand_query(processed_query)
            all_results = []
            seen_texts = set()
            for query_var in query_variations:
                response = self.cached_retrieve(query_var)
                if "error" in response:
                    continue
                for result in response["retrievalResults"]:
                    content = result["content"]["text"]
                    if hash(content) not in seen_texts:
                        seen_texts.add(hash(content))
                        all_results.append(result)
            return {"retrievalResults": all_results[:self.num_results]}
        return self.cached_retrieve(processed_query)

    def get_presigned_url(self, s3_uri: str) -> str:
        if s3_uri.startswith('s3://'):
            bucket = s3_uri.split('/')[2]
            key = '/'.join(s3_uri.split('/')[3:])
            try:
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': key},
                    ExpiresIn=3600
                )
                return url
            except Exception as e:
                return f"Error generating URL: {str(e)}"
        return s3_uri

    def format_as_link(self, source_url: str) -> str:
        if source_url == 'Source URL not available':
            return source_url
        elif source_url.startswith(('http://', 'https://')):
            return f"[View Document]({source_url})"
        elif source_url.startswith('s3://'):
            presigned_url = self.get_presigned_url(source_url)
            return f"[View Document]({presigned_url})"
        else:
            return source_url

    def get_specific_source_urls(self, response: Dict, indices: List[int] = None, institution_domain: str = None) -> str:
        if "error" in response:
            return ""

        results = response.get("retrievalResults", [])
        if not results:
            return ""

        formatted_urls = []
        seen_urls = set()

        # Default to LPU domain if none provided
        if not institution_domain:
            institution_domain = "lpu.in"

        for i, result in enumerate(results, 1):
            if indices and i not in indices:
                continue

            # Get source URL from metadata if available
            metadata = result.get('metadata', {})
            source_url = metadata.get('source_url', '')

            # If not in metadata, try to get from S3 location
            if not source_url:
                location = result.get('location', {})
                s3_location = location.get('s3Location', {})
                source_url = s3_location.get('uri', '')

            # Only include if it's a valid URL and from the institution's domain
            if source_url and source_url not in seen_urls:
                # Strictly verify it's from the institution's domain
                is_valid = False

                # Check if it's an HTTP/HTTPS URL from the institution's domain
                if source_url.startswith('http://') or source_url.startswith('https://'):
                    try:
                        from urllib.parse import urlparse
                        parsed_url = urlparse(source_url)
                        domain = parsed_url.netloc
                        # Check if the domain is or ends with the institution domain
                        is_valid = domain == institution_domain or domain.endswith('.' + institution_domain)
                    except:
                        is_valid = False

                if is_valid:
                    seen_urls.add(source_url)
                    title = metadata.get('title', f"Reference {len(formatted_urls) + 1}")
                    formatted_urls.append(f"- [{title}]({source_url})")

        return "\n".join(formatted_urls)


    def format_retrieval_results(self, response: Dict) -> (str, str):
        if "error" in response:
            return f"Retrieval Error: {response['error']}", ""

        results = response.get("retrievalResults", [])
        if not results:
            return "No relevant content found in knowledge base.", ""

        formatted_content = []
        reference_links = []
        seen_sources = set()

        for i, result in enumerate(results, 1):
            content = result["content"]["text"]
            score = result.get("score", "N/A")
            location = result.get("location", {})
            source_url = None

            if location.get("type") == "WEB":
                source_url = location.get("webLocation", {}).get("url", None)

            if source_url and source_url not in seen_sources:
                reference_links.append(f"- [View Document]({source_url})")
                seen_sources.add(source_url)



            formatted_content.append(
                f"SOURCE {i} [Score: {score}]"
            )

        if not formatted_content:
            return "No relevant content with available sources found in knowledge base.", ""

        return "\n".join(formatted_content), "\n".join(reference_links)




    def get_relevant_context(self, query: str) -> str:
        response = self.retrieve(query, advanced=True)
        return self.format_retrieval_results(response)
