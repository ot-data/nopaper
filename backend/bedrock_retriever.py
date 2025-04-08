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
            # Remove the filters parameter since customer_id is undefined
            response = self.bedrock_client.retrieve(
                knowledgeBaseId=self.kb_id,
                retrievalQuery={
                    "text": query
                    # Removed filters with undefined customer_id
                },
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": self.num_results
                    }
                }
            )
            return response
        except Exception as e:
            print(f"Bedrock retrieval error: {str(e)}")
            return {"error": str(e), "retrievalResults": []}

    def retrieve(self, query: str, advanced: bool = True, debug: bool = True) -> Dict:
        processed_query = self.preprocess_query(query)
        print(f"Processed query: '{processed_query}'")

        if advanced:
            query_variations = self.expand_query(processed_query)
            print(f"Query variations: {query_variations}")

            all_results = []
            seen_texts = set()

            for query_var in query_variations:
                print(f"Retrieving for query variation: '{query_var}'")
                response = self.cached_retrieve(query_var)

                if "error" in response:
                    print(f"Error in response for '{query_var}': {response.get('error')}")
                    continue

                # Debug: Print the full response structure if debug mode is on
                if debug:
                    import json
                    try:
                        # Convert to dict and back to JSON for pretty printing
                        response_dict = {k: v for k, v in response.items() if k != 'retrievalResults'}
                        response_dict['retrievalResults'] = f"[{len(response.get('retrievalResults', []))} results]"
                        print(f"Response structure for '{query_var}': {json.dumps(response_dict, indent=2)}")

                        # Print the structure of the first result if available
                        if response.get('retrievalResults'):
                            first_result = response['retrievalResults'][0]
                            first_result_dict = {k: (v if k != 'content' else '[content text]') for k, v in first_result.items()}
                            print(f"First result structure: {json.dumps(first_result_dict, indent=2)}")
                    except Exception as e:
                        print(f"Error printing response structure: {str(e)}")

                # Process results
                for result in response.get("retrievalResults", []):
                    try:
                        content = result.get("content", {}).get("text", "")
                        if hash(content) not in seen_texts:
                            seen_texts.add(hash(content))
                            all_results.append(result)
                    except Exception as e:
                        print(f"Error processing result: {str(e)}")

            print(f"Total unique results after processing: {len(all_results)}")
            return {"retrievalResults": all_results[:self.num_results]}

        # Non-advanced mode
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

    def get_specific_source_urls(self, response: Dict, indices: List[int] = None, institution_domain: str = None, institution_website: str = None) -> str:
        if "error" in response:
            print(f"Error in response: {response.get('error')}")
            return ""

        results = response.get("retrievalResults", [])
        if not results:
            print("No retrieval results found")
            return ""

        print(f"Processing {len(results)} retrieval results for reference links")
        formatted_urls = []
        seen_urls = set()

        # Default to LPU domain if none provided
        if not institution_domain:
            institution_domain = "lpu.in"
        print(f"Using institution domain: {institution_domain}")

        # Use the provided institution website or try to construct one
        if institution_website:
            print(f"Using institution website: {institution_website}")
        else:
            # Construct a default website URL if not provided
            institution_website = f"https://www.{institution_domain}"
            print(f"No institution website provided, using default: {institution_website}")

        # First pass: collect all URLs from all results
        all_urls = []
        for i, result in enumerate(results, 1):
            if indices and i not in indices:
                continue

            # Collect all URLs from this result
            result_urls = []

            # Check all metadata fields for URLs
            metadata = result.get('metadata', {})
            for key, value in metadata.items():
                if isinstance(value, str) and (value.startswith('http://') or value.startswith('https://')):
                    result_urls.append((value, metadata.get('title', '')))
                    print(f"Result {i} - Found URL in metadata[{key}]: {value}")

            # Check document metadata
            document_metadata = result.get('documentMetadata', {})
            for key, value in document_metadata.items():
                if isinstance(value, str) and (value.startswith('http://') or value.startswith('https://')):
                    result_urls.append((value, document_metadata.get('title', '')))
                    print(f"Result {i} - Found URL in documentMetadata[{key}]: {value}")

            # Check location
            location = result.get('location', {})
            location_type = location.get('type', '')

            if location_type == 'WEB':
                web_location = location.get('webLocation', {})
                web_url = web_location.get('url', '')
                if web_url:
                    result_urls.append((web_url, metadata.get('title', '')))
                    print(f"Result {i} - Found URL in webLocation: {web_url}")

            # Extract URLs from content
            content = result.get('content', {}).get('text', '')
            import re
            url_pattern = r'https?://[\w.-]+(?:\.[\w.-]+)+[\w\-._~:/?#[\]@!$&\'()*+,;=]+'
            content_urls = re.findall(url_pattern, content)

            # Look for URLs that might be from the institution's domain
            for url in content_urls:
                try:
                    from urllib.parse import urlparse
                    parsed_url = urlparse(url)
                    domain = parsed_url.netloc.lower()
                    if institution_domain.lower() in domain:
                        result_urls.append((url, ''))
                        print(f"Result {i} - Found relevant URL in content: {url}")
                except Exception as e:
                    print(f"Result {i} - Error parsing content URL: {str(e)}")

            # Add all URLs from this result to the master list
            all_urls.extend([(url, title, i) for url, title in result_urls])

        # Second pass: filter and format the URLs
        for url, title, result_index in all_urls:
            if url and url not in seen_urls:
                # Verify it's from the institution's domain
                is_valid = False
                if url.startswith('http://') or url.startswith('https://'):
                    try:
                        from urllib.parse import urlparse
                        parsed_url = urlparse(url)
                        domain = parsed_url.netloc.lower()

                        # Remove 'www.' prefix if present for comparison
                        if domain.startswith('www.'):
                            domain = domain[4:]

                        # Normalize institution domain for comparison
                        norm_institution_domain = institution_domain.lower()
                        if norm_institution_domain.startswith('www.'):
                            norm_institution_domain = norm_institution_domain[4:]

                        # Domain validation - check if the URL's domain matches or is a subdomain
                        # of the institution domain
                        is_valid = (
                            domain == norm_institution_domain or
                            domain.endswith('.' + norm_institution_domain) or
                            (len(norm_institution_domain) > 4 and norm_institution_domain in domain)
                        )

                        print(f"URL validation: domain={domain}, institution_domain={norm_institution_domain}, is_valid={is_valid}")
                    except Exception as e:
                        print(f"Error validating URL {url}: {str(e)}")
                        is_valid = False

                if is_valid:
                    seen_urls.add(url)

                    # Get a meaningful title
                    if not title:
                        # Try to extract title from URL path
                        try:
                            from urllib.parse import urlparse
                            parsed_url = urlparse(url)
                            path = parsed_url.path
                            if path and path != '/':
                                # Use the last part of the path as title
                                path_parts = path.strip('/').split('/')
                                title = path_parts[-1].replace('-', ' ').replace('_', ' ').title()
                            else:
                                title = f"Reference {len(formatted_urls) + 1}"
                        except Exception as e:
                            print(f"Error extracting title from URL: {str(e)}")
                            title = f"Reference {len(formatted_urls) + 1}"

                    formatted_urls.append(f"- [{title}]({url})")
                    print(f"Added reference: {title} -> {url}")

        if not formatted_urls:
            print("No valid reference URLs found after filtering")
        else:
            print(f"Found {len(formatted_urls)} valid reference URLs")

        return "\n".join(formatted_urls)


    def format_retrieval_results(self, response: Dict) -> (str, str):
        if "error" in response:
            print(f"Error in format_retrieval_results: {response.get('error')}")
            return f"Retrieval Error: {response['error']}", ""

        results = response.get("retrievalResults", [])
        if not results:
            print("No retrieval results found in format_retrieval_results")
            return "No relevant content found in knowledge base.", ""

        print(f"Formatting {len(results)} retrieval results")
        formatted_content = []
        reference_links = []
        seen_sources = set()

        # First pass: extract all URLs from the results
        all_urls = []
        for i, result in enumerate(results, 1):
            # Extract content
            content = result.get("content", {}).get("text", "")
            score = result.get("score", "N/A")

            # Log the structure of the result for debugging
            print(f"Result {i} structure: {list(result.keys())}")

            # Extract source URL from all possible locations
            source_urls = []

            # Check metadata
            metadata = result.get('metadata', {})
            if metadata:
                for key, value in metadata.items():
                    if isinstance(value, str) and (value.startswith('http://') or value.startswith('https://')):
                        source_urls.append(value)
                        print(f"Result {i} - Found URL in metadata[{key}]: {value}")

            # Check document metadata
            document_metadata = result.get('documentMetadata', {})
            if document_metadata:
                for key, value in document_metadata.items():
                    if isinstance(value, str) and (value.startswith('http://') or value.startswith('https://')):
                        source_urls.append(value)
                        print(f"Result {i} - Found URL in documentMetadata[{key}]: {value}")

            # Check location
            location = result.get("location", {})
            location_type = location.get("type", "")
            print(f"Result {i} - Location type: {location_type}")

            if location_type == "WEB":
                web_location = location.get("webLocation", {})
                web_url = web_location.get("url", "")
                if web_url:
                    source_urls.append(web_url)
                    print(f"Result {i} - Web location URL: {web_url}")

            # Extract URLs from content text
            import re
            url_pattern = r'https?://[\w.-]+(?:\.[\w.-]+)+[\w\-._~:/?#[\]@!$&\'()*+,;=]+'
            content_urls = re.findall(url_pattern, content)
            if content_urls:
                for url in content_urls:
                    source_urls.append(url)
                    print(f"Result {i} - Found URL in content: {url}")

            # Add all found URLs to the master list
            all_urls.extend([(url, metadata.get('title', ''), i) for url in source_urls])

            # Format content
            formatted_content.append(f"SOURCE {i} [Score: {score}]")

        # Second pass: filter and format the URLs
        for url, title, result_index in all_urls:
            if url and url not in seen_sources:
                # Use a meaningful title or generate one
                if not title:
                    title = f"Reference {len(reference_links) + 1}"

                # Try to extract a better title from the URL if it's a web URL
                if url.startswith('http'):
                    try:
                        from urllib.parse import urlparse
                        parsed_url = urlparse(url)
                        path = parsed_url.path
                        if path and path != '/':
                            # Use the last part of the path as title
                            path_parts = path.strip('/').split('/')
                            url_title = path_parts[-1].replace('-', ' ').replace('_', ' ').title()
                            if url_title:
                                title = url_title
                    except Exception as e:
                        print(f"Error extracting title from URL: {str(e)}")

                reference_links.append(f"- [{title}]({url})")
                seen_sources.add(url)
                print(f"Added reference link: {title} -> {url}")

        if not formatted_content:
            print("No formatted content generated")
            return "No relevant content with available sources found in knowledge base.", ""

        print(f"Returning {len(formatted_content)} formatted content items and {len(reference_links)} reference links")
        return "\n".join(formatted_content), "\n".join(reference_links)




    def get_relevant_context(self, query: str) -> str:
        response = self.retrieve(query, advanced=True)
        return self.format_retrieval_results(response)
