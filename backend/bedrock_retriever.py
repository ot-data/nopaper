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
        self.auth_method = config["aws"].get("auth_method", "credentials")

        # Get retrieval configuration
        self.num_results = config["retrieval"]["num_results"]
        self.min_score = config["retrieval"]["min_score"]

        # Create session based on authentication method
        if self.auth_method.lower() == "iam_role":
            # Use IAM role authentication (default credential provider chain)
            self.session = boto3.Session(region_name=self.region)
            print(f"Using IAM role authentication for AWS services")
        else:
            # Use explicit credentials
            self.access_key = config["aws"].get("access_key")
            self.secret_key = config["aws"].get("secret_key")

            if not self.access_key or not self.secret_key:
                print(f"Warning: Missing AWS credentials but auth_method is '{self.auth_method}'. Falling back to IAM role.")
                self.session = boto3.Session(region_name=self.region)
            else:
                self.session = boto3.Session(
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region
                )
                print(f"Using credential-based authentication for AWS services")

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
        """Retrieve from Bedrock knowledge base with caching."""
        import logging
        import boto3
        from botocore.exceptions import ClientError, BotoCoreError

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
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            logging.error(f"AWS Bedrock ClientError: {error_code} - {error_msg}")

            if error_code == "ThrottlingException":
                return {"error": "AWS service is currently busy. Please try again shortly.", "retrievalResults": []}
            elif error_code == "AccessDeniedException":
                return {"error": "Access denied to AWS Bedrock. Check credentials and permissions.", "retrievalResults": []}
            else:
                return {"error": f"AWS error: {error_msg}", "retrievalResults": []}
        except BotoCoreError as e:
            logging.error(f"AWS BotoCoreError: {str(e)}")
            return {"error": f"AWS connection error: {str(e)}", "retrievalResults": []}
        except Exception as e:
            logging.error(f"Unexpected error in Bedrock retrieval: {str(e)}")
            return {"error": f"Retrieval error: {str(e)}", "retrievalResults": []}

    def retrieve(self, query: str, advanced: bool = True, debug: bool = True) -> Dict:
        """Retrieve content from knowledge base, with optional query expansion."""
        import logging
        import json

        # Setup logging if not already configured
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        try:
            # Preprocess the query
            processed_query = self.preprocess_query(query)
            logging.info(f"Processed query: '{processed_query}'")

            if advanced:
                # Use query expansion for advanced mode
                query_variations = self.expand_query(processed_query)
                logging.info(f"Query variations: {query_variations}")

                all_results = []
                seen_texts = set()
                error_count = 0

                for query_var in query_variations:
                    try:
                        logging.info(f"Retrieving for query variation: '{query_var}'")
                        response = self.cached_retrieve(query_var)

                        if "error" in response:
                            error_count += 1
                            logging.warning(f"Error in response for '{query_var}': {response.get('error')}")
                            continue

                        # Debug: Print the full response structure if debug mode is on
                        if debug:
                            try:
                                # Convert to dict and back to JSON for pretty printing
                                response_dict = {k: v for k, v in response.items() if k != 'retrievalResults'}
                                response_dict['retrievalResults'] = f"[{len(response.get('retrievalResults', []))} results]"
                                logging.info(f"Response structure for '{query_var}': {json.dumps(response_dict, indent=2)}")

                                # Print the structure of the first result if available
                                if response.get('retrievalResults'):
                                    first_result = response['retrievalResults'][0]
                                    first_result_dict = {k: (v if k != 'content' else '[content text]') for k, v in first_result.items()}
                                    logging.info(f"First result structure: {json.dumps(first_result_dict, indent=2)}")
                            except Exception as e:
                                logging.error(f"Error printing response structure: {str(e)}")

                        # Process results
                        for result in response.get("retrievalResults", []):
                            try:
                                content = result.get("content", {}).get("text", "")
                                content_hash = hash(content)
                                if content_hash not in seen_texts:
                                    seen_texts.add(content_hash)
                                    all_results.append(result)
                            except Exception as e:
                                logging.error(f"Error processing result: {str(e)}")
                    except Exception as e:
                        error_count += 1
                        logging.error(f"Error processing query variation '{query_var}': {str(e)}")

                # Check if all queries failed
                if error_count == len(query_variations):
                    logging.error("All query variations failed")
                    return {"error": "All retrieval attempts failed", "retrievalResults": []}

                logging.info(f"Total unique results after processing: {len(all_results)}")
                return {"retrievalResults": all_results[:self.num_results]}

            # Non-advanced mode - just use the processed query directly
            return self.cached_retrieve(processed_query)

        except Exception as e:
            logging.error(f"Unexpected error in retrieve method: {str(e)}")
            return {"error": f"Retrieval processing error: {str(e)}", "retrievalResults": []}

    def get_presigned_url(self, s3_uri: str) -> str:
        """Generate a presigned URL for an S3 URI."""
        import logging
        import boto3
        from botocore.exceptions import ClientError, BotoCoreError

        if not s3_uri.startswith('s3://'):
            return s3_uri

        try:
            # Parse the S3 URI
            parts = s3_uri.split('/')
            if len(parts) < 4:
                logging.error(f"Invalid S3 URI format: {s3_uri}")
                return s3_uri

            bucket = parts[2]
            key = '/'.join(parts[3:])

            # Generate the presigned URL
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=3600
            )
            logging.info(f"Generated presigned URL for {s3_uri}")
            return url

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            logging.error(f"AWS S3 ClientError: {error_code} - {error_msg}")
            return f"Error accessing document: {error_msg}"

        except BotoCoreError as e:
            logging.error(f"AWS S3 BotoCoreError: {str(e)}")
            return f"Error connecting to document storage: {str(e)}"

        except Exception as e:
            logging.error(f"Unexpected error generating presigned URL for {s3_uri}: {str(e)}")
            return f"Error generating URL: {str(e)}"

    def format_as_link(self, source_url: str) -> str:
        """Format a source URL as a markdown link."""
        import logging

        if not source_url or source_url == 'Source URL not available':
            return "Source URL not available"

        try:
            if source_url.startswith(('http://', 'https://')):
                # For web URLs, create a direct link
                return f"[View Document]({source_url})"
            elif source_url.startswith('s3://'):
                # For S3 URIs, generate a presigned URL
                presigned_url = self.get_presigned_url(source_url)
                return f"[View Document]({presigned_url})"
            else:
                # For other formats, return as is
                logging.warning(f"Unknown URL format: {source_url}")
                return source_url
        except Exception as e:
            logging.error(f"Error formatting link for {source_url}: {str(e)}")
            return source_url

    def extract_urls_from_result(self, result: Dict, result_index: int, institution_domain: str) -> List[tuple]:
        """Extract URLs from a single result, prioritizing structured metadata fields.
        Only extracts web links (http/https URLs).
        """
        import logging
        from urllib.parse import urlparse

        result_urls = []

        try:
            # 1. First priority: Check location (most reliable structured field)
            location = result.get('location', {})
            location_type = location.get('type', '')

            if location_type == 'WEB':
                web_location = location.get('webLocation', {})
                web_url = web_location.get('url', '')
                if web_url and (web_url.startswith('http://') or web_url.startswith('https://')):
                    metadata = result.get('metadata', {})
                    result_urls.append((web_url, metadata.get('title', ''), 'webLocation'))
                    logging.info(f"Result {result_index} - Found URL in webLocation: {web_url}")

            # 2. Second priority: Check document metadata
            document_metadata = result.get('documentMetadata', {})
            for key, value in document_metadata.items():
                if isinstance(value, str) and (value.startswith('http://') or value.startswith('https://')):
                    # Validate URL format
                    try:
                        parsed_url = urlparse(value)
                        if parsed_url.netloc:  # Ensure it has a domain
                            result_urls.append((value, document_metadata.get('title', ''), f'documentMetadata[{key}]'))
                            logging.info(f"Result {result_index} - Found URL in documentMetadata[{key}]: {value}")
                    except Exception:
                        logging.warning(f"Result {result_index} - Invalid URL in documentMetadata[{key}]: {value}")

            # 3. Third priority: Check all metadata fields
            metadata = result.get('metadata', {})
            for key, value in metadata.items():
                if isinstance(value, str) and (value.startswith('http://') or value.startswith('https://')):
                    # Validate URL format
                    try:
                        parsed_url = urlparse(value)
                        if parsed_url.netloc:  # Ensure it has a domain
                            result_urls.append((value, metadata.get('title', ''), f'metadata[{key}]'))
                            logging.info(f"Result {result_index} - Found URL in metadata[{key}]: {value}")
                    except Exception:
                        logging.warning(f"Result {result_index} - Invalid URL in metadata[{key}]: {value}")

            # 4. Last resort: Extract URLs from content using regex
            # Only if we haven't found any URLs from structured fields
            if not result_urls:
                content = result.get('content', {}).get('text', '')
                import re
                url_pattern = r'https?://[\w.-]+(?:\.[\w.-]+)+[\w\-._~:/?#[\]@!$&\'()*+,;=]+'
                content_urls = re.findall(url_pattern, content)

                # Filter for institution domain URLs only - strict matching
                for url in content_urls:
                    try:
                        parsed_url = urlparse(url)
                        domain = parsed_url.netloc.lower()

                        # Remove 'www.' prefix if present
                        if domain.startswith('www.'):
                            domain = domain[4:]

                        # Normalize institution domain
                        norm_institution_domain = institution_domain.lower()
                        if norm_institution_domain.startswith('www.'):
                            norm_institution_domain = norm_institution_domain[4:]

                        # Strict domain validation - only exact match or subdomains
                        if (domain == norm_institution_domain or domain.endswith('.' + norm_institution_domain)) and parsed_url.netloc:
                            result_urls.append((url, '', 'content'))
                            logging.info(f"Result {result_index} - Found relevant URL in content: {url}")
                        else:
                            logging.info(f"Result {result_index} - URL {url} rejected: domain {domain} doesn't match {norm_institution_domain}")
                    except Exception as e:
                        logging.warning(f"Result {result_index} - Error parsing content URL: {str(e)}")

            return result_urls

        except Exception as e:
            logging.error(f"Error extracting URLs from result {result_index}: {str(e)}")
            return []

    def validate_url_domain(self, url: str, institution_domain: str) -> bool:
        """Validate if a URL belongs to the specified institution domain and is a web link."""
        import logging
        from urllib.parse import urlparse

        try:
            # If no institution domain is provided, we can't validate
            if not institution_domain:
                logging.warning(f"No institution domain provided for URL validation: {url}")
                return False

            # Ensure it's a web URL (http or https)
            if not (url.startswith('http://') or url.startswith('https://')):
                logging.info(f"URL {url} rejected: not a web URL")
                return False

            # Validate URL format
            parsed_url = urlparse(url)
            if not parsed_url.netloc:
                logging.info(f"URL {url} rejected: invalid URL format")
                return False

            domain = parsed_url.netloc.lower()

            # Remove 'www.' prefix if present for comparison
            if domain.startswith('www.'):
                domain = domain[4:]

            # Normalize institution domain for comparison
            norm_institution_domain = institution_domain.lower()
            if norm_institution_domain.startswith('www.'):
                norm_institution_domain = norm_institution_domain[4:]

            # Strict domain validation - only accept exact domain match or subdomains
            # This prevents including URLs from unrelated websites
            is_valid = (
                domain == norm_institution_domain or  # Exact match
                domain.endswith('.' + norm_institution_domain)  # Subdomain
            )

            logging.info(f"URL validation: domain={domain}, institution_domain={norm_institution_domain}, is_valid={is_valid}")
            return is_valid

        except Exception as e:
            logging.error(f"Error validating URL {url}: {str(e)}")
            return False

    def extract_title_from_url(self, url: str, default_title: str = "") -> str:
        """Extract a meaningful title from a URL path."""
        import logging
        from urllib.parse import urlparse

        if not url.startswith(('http://', 'https://')):
            return default_title or "Unknown Reference"

        try:
            parsed_url = urlparse(url)
            path = parsed_url.path

            if path and path != '/':
                # Use the last part of the path as title
                path_parts = path.strip('/').split('/')
                title = path_parts[-1].replace('-', ' ').replace('_', ' ').title()
                return title if title else default_title or "Unknown Reference"
            else:
                return default_title or parsed_url.netloc

        except Exception as e:
            logging.warning(f"Error extracting title from URL {url}: {str(e)}")
            return default_title or "Unknown Reference"

    def get_specific_source_urls(self, response: Dict, indices: List[int] = None, institution_domain: str = None, institution_website: str = None) -> str:
        """Extract and format source URLs from retrieval results, prioritizing structured metadata."""
        import logging

        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        # Error handling for response
        if "error" in response:
            logging.error(f"Error in response: {response.get('error')}")
            return ""

        results = response.get("retrievalResults", [])
        if not results:
            logging.warning("No retrieval results found")
            return ""

        logging.info(f"Processing {len(results)} retrieval results for reference links")
        formatted_urls = []
        seen_urls = set()

        # Default to LPU domain if none provided
        if not institution_domain:
            institution_domain = "lpu.in"
        logging.info(f"Using institution domain: {institution_domain}")

        # Use the provided institution website or try to construct one
        if institution_website:
            logging.info(f"Using institution website: {institution_website}")
        else:
            # Construct a default website URL if not provided
            institution_website = f"https://www.{institution_domain}"
            logging.info(f"No institution website provided, using default: {institution_website}")

        # First pass: collect all URLs from all results
        all_urls = []
        for i, result in enumerate(results, 1):
            if indices and i not in indices:
                continue

            # Extract URLs from this result using our helper method
            result_urls = self.extract_urls_from_result(result, i, institution_domain)

            # Add all URLs from this result to the master list
            all_urls.extend([(url, title, source, i) for url, title, source in result_urls])

        # Second pass: filter and format the URLs
        for url, title, source, result_index in all_urls:
            if url and url not in seen_urls:
                # Verify it's from the institution's domain
                is_valid = self.validate_url_domain(url, institution_domain)

                if is_valid:
                    seen_urls.add(url)

                    # Get a meaningful title
                    if not title:
                        title = self.extract_title_from_url(url, f"Reference {len(formatted_urls) + 1}")

                    formatted_urls.append(f"- [{title}]({url})")
                    logging.info(f"Added reference: {title} -> {url} (from {source})")

        if not formatted_urls:
            logging.warning("No valid reference URLs found after filtering")
            # Return an empty string instead of a placeholder
            return ""
        else:
            logging.info(f"Found {len(formatted_urls)} valid reference URLs")
            return "\n".join(formatted_urls)


    def format_retrieval_results(self, response: Dict) -> (str, str):
        """Format retrieval results into content and reference links."""
        import logging

        # Setup logging if not already configured
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        # Error handling for response
        if "error" in response:
            error_msg = response.get('error')
            logging.error(f"Error in format_retrieval_results: {error_msg}")
            return f"Retrieval Error: {error_msg}", ""

        results = response.get("retrievalResults", [])
        if not results:
            logging.warning("No retrieval results found in format_retrieval_results")
            return "No relevant content found in knowledge base.", ""

        logging.info(f"Formatting {len(results)} retrieval results")
        formatted_content = []
        reference_links = []
        seen_sources = set()

        try:
            # First pass: extract content and URLs from the results
            all_urls = []
            for i, result in enumerate(results, 1):
                try:
                    # Extract content and score
                    content = result.get("content", {}).get("text", "")
                    score = result.get("score", "N/A")

                    # Log the structure of the result for debugging
                    logging.info(f"Result {i} structure: {list(result.keys())}")

                    # Extract URLs using our helper method
                    # We use an empty domain here since we're not filtering by institution
                    result_urls = self.extract_urls_from_result(result, i, "")

                    # Add all found URLs to the master list
                    all_urls.extend([(url, title, source, i) for url, title, source in result_urls])

                    # Format content
                    formatted_content.append(f"SOURCE {i} [Score: {score}]")

                except Exception as e:
                    logging.error(f"Error processing result {i}: {str(e)}")
                    # Continue with next result instead of failing completely
                    continue

            # Second pass: filter and format the URLs
            for url, title, source, result_index in all_urls:
                if url and url not in seen_sources:
                    try:
                        # Get a meaningful title if not provided
                        if not title:
                            title = self.extract_title_from_url(url, f"Reference {len(reference_links) + 1}")

                        reference_links.append(f"- [{title}]({url})")
                        seen_sources.add(url)
                        logging.info(f"Added reference link: {title} -> {url} (from {source})")
                    except Exception as e:
                        logging.error(f"Error formatting URL {url}: {str(e)}")
                        # Continue with next URL
                        continue

            if not formatted_content:
                logging.warning("No formatted content generated")
                return "No relevant content with available sources found in knowledge base.", ""

            # Only return reference links if they exist and are not empty
            final_reference_links = "\n".join(reference_links) if reference_links else ""

            logging.info(f"Returning {len(formatted_content)} formatted content items and {len(reference_links)} reference links")
            return "\n".join(formatted_content), final_reference_links

        except Exception as e:
            logging.error(f"Unexpected error in format_retrieval_results: {str(e)}")
            return "Error formatting retrieval results.", ""




    def get_relevant_context(self, query: str) -> tuple:
        """Get relevant context for a query from the knowledge base.

        Args:
            query: The user query to retrieve context for

        Returns:
            A tuple of (formatted_content, reference_links)
        """
        import logging

        try:
            # Retrieve content from knowledge base
            logging.info(f"Retrieving context for query: '{query}'")
            response = self.retrieve(query, advanced=True)

            # Check for errors in the response
            if "error" in response:
                error_msg = response.get("error")
                logging.error(f"Error retrieving context: {error_msg}")
                return f"Error retrieving information: {error_msg}", ""

            # Format the retrieval results
            return self.format_retrieval_results(response)

        except Exception as e:
            logging.error(f"Unexpected error in get_relevant_context: {str(e)}")
            return "Error retrieving relevant context.", ""
