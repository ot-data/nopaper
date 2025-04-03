# import os
# import re
# import boto3
# from functools import lru_cache
# from typing import Dict, List, Any

# class EnhancedBedrockRetriever:
#     def __init__(self, config: Dict[str, Any]):
#         self.config = config
#         self.kb_id = config["aws"]["s3_kb_id"]
#         self.region = config["aws"]["region"]
#         self.access_key = config["aws"]["access_key"]
#         self.secret_key = config["aws"]["secret_key"]
#         self.num_results = config["retrieval"].get("num_results", 5)
#         self.min_score = config["retrieval"].get("min_score", 0.5)
        
#         self.session = boto3.Session(
#             aws_access_key_id=self.access_key,
#             aws_secret_access_key=self.secret_key,
#             region_name=self.region
#         )
#         self.bedrock_client = self.session.client("bedrock-agent-runtime")
#         self.s3_client = self.session.client("s3")
        
#         self.synonyms = {
#             "lpu": ["lovely professional university", "lpu university", "lovely university"],
#             "fee": ["fees", "tuition", "cost", "payment"],
#             "admission": ["admissions", "enrollment", "joining", "application"],
#             "course": ["program", "degree", "curriculum", "study"],
#         }

#     def preprocess_query(self, query: str) -> str:
#         processed = query.lower().strip()
#         acronyms = {
#             "lpu": "LPU",
#             "cse": "computer science engineering",
#             "ece": "electronics and communication engineering",
#             "ai": "artificial intelligence",
#             "ml": "machine learning"
#         }
#         for acronym, full_form in acronyms.items():
#             pattern = r'\b' + re.escape(acronym) + r'\b'
#             processed = re.sub(pattern, full_form, processed)
#         processed = re.sub(r'\s+', ' ', processed)
#         processed = re.sub(r'[^\w\s]', '', processed)
#         return processed

#     def expand_query(self, query: str) -> List[str]:
#         query_terms = query.split()
#         expanded_queries = [query]
#         for i, term in enumerate(query_terms):
#             if term in self.synonyms:
#                 for synonym in self.synonyms[term]:
#                     new_query = query_terms.copy()
#                     new_query[i] = synonym
#                     expanded_queries.append(" ".join(new_query))
#         return expanded_queries[:3]

#     @lru_cache(maxsize=32)
#     def cached_retrieve(self, query: str) -> Dict:
#         try:
#             response = self.bedrock_client.retrieve(
#                 knowledgeBaseId=self.kb_id,
#                 retrievalQuery={"text": query},
#                 retrievalConfiguration={
#                     "vectorSearchConfiguration": {
#                         "numberOfResults": self.num_results * 2
#                     }
#                 }
#             )
#             return response
#         except Exception as e:
#             return {"error": str(e), "retrievalResults": []}

#     def retrieve(self, query: str, advanced: bool = True) -> Dict:
#         processed_query = self.preprocess_query(query)
#         if advanced:
#             query_variations = self.expand_query(processed_query)
#             all_results = []
#             seen_texts = set()
#             for query_var in query_variations:
#                 response = self.cached_retrieve(query_var)
#                 if "error" in response:
#                     continue
#                 for result in response["retrievalResults"]:
#                     content = result["content"]["text"]
#                     if hash(content) not in seen_texts:
#                         seen_texts.add(hash(content))
#                         all_results.append(result)
#             return {"retrievalResults": all_results[:self.num_results]}
#         return self.cached_retrieve(processed_query)

#     def get_presigned_url(self, s3_uri: str) -> str:
#         if s3_uri.startswith('s3://'):
#             bucket = s3_uri.split('/')[2]
#             key = '/'.join(s3_uri.split('/')[3:])
#             try:
#                 url = self.s3_client.generate_presigned_url(
#                     'get_object',
#                     Params={'Bucket': bucket, 'Key': key},
#                     ExpiresIn=3600
#                 )
#                 return url
#             except Exception as e:
#                 return f"Error generating URL: {str(e)}"
#         return s3_uri

#     def format_as_link(self, source_url: str) -> str:
#         if source_url == 'Source URL not available':
#             return source_url
#         # elif source_url.startswith('s3://'):
#         #     presigned_url = self.get_presigned_url(source_url)
#             # return f"[View Document]({presigned_url})"
#         elif source_url.startswith(('http://', 'https://')):
#             return f"[View Document]({source_url})"
#         else:
#             return source_url

#     def get_specific_source_urls(self, response: Dict, indices: List[int] = None) -> str:
#         if "error" in response:
#             return ""
        
#         results = response.get("retrievalResults", [])
#         if not results:
#             return ""
        
#         formatted_urls = []
#         for i, result in enumerate(results, 1):
#             if indices and i not in indices:
#                 continue
                
#             location = result.get('location', {})
#             s3_location = location.get('s3Location', {})
#             source_url = s3_location.get('uri', 'Source URL not available')
            
#             if source_url != 'Source URL not available':
#                 markdown_link = self.format_as_link(source_url)
#                 formatted_urls.append(f"- Source {i}: {markdown_link}")
        
#         return "\n".join(formatted_urls)

#     def format_retrieval_results(self, response: Dict, use_html=False) -> (str, str):
#         if "error" in response:
#             return f"Retrieval Error: {response['error']}", ""
#         results = response.get("retrievalResults", [])
#         if not results:
#             return "No relevant content found in knowledge base.", ""
        
#         formatted_content = []
#         reference_links = []

#         for i, result in enumerate(results, 1):
#             content = result["content"]["text"]
#             score = result.get("score", "N/A")
#             location = result.get('location', {})
#             source_url = None

#             if location.get('type') == 'WEB':
#                 source_url = location.get('webLocation', {}).get('url', None)
#             # elif location.get('type') == 'S3':
#             #     source_url = location.get('s3Location', {}).get('uri', None)

#             if source_url:
#                 # if source_url.startswith('s3://'):
#                 #     display_url = self.get_presigned_url(source_url)
#                 # else:
#                 display_url = source_url
                
#                 filename = os.path.basename(source_url.split("?")[0])
#                 reference_links.append(f"- [{filename}]({display_url})")
                
#                 formatted_content.append(
#                     f"SOURCE {i} [Score: {score}]:\nContent: {content}\nSource URL: {source_url}\n"
#                 )
#             else:
#                 print(f"Skipping source {i} due to missing URL")

#         if not formatted_content:
#             return "No relevant content with available sources found in knowledge base.", ""
        
#         return "\n".join(formatted_content), "\n".join(reference_links)

#     def get_relevant_context(self, query: str) -> str:
#         response = self.retrieve(query, advanced=True)
#         return self.format_retrieval_results(response)





import os
import re
import boto3
from functools import lru_cache
from typing import Dict, List, Any

class EnhancedBedrockRetriever:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.kb_id = config["aws"]["s3_kb_id"]
        self.region = config["aws"]["region"]
        self.access_key = config["aws"]["access_key"]
        self.secret_key = config["aws"]["secret_key"]
        self.num_results = 5#config["retrieval"].get("num_results", 5)
        self.min_score = 0.5#config["retrieval"].get("min_score", 0.5)
        
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

    def get_specific_source_urls(self, response: Dict, indices: List[int] = None) -> str:
        if "error" in response:
            return ""
        
        results = response.get("retrievalResults", [])
        if not results:
            return ""
        
        formatted_urls = []
        for i, result in enumerate(results, 1):
            if indices and i not in indices:
                continue
                
            location = result.get('location', {})
            s3_location = location.get('s3Location', {})
            source_url = s3_location.get('uri', 'Source URL not available')
            
            if source_url != 'Source URL not available':
                markdown_link = self.format_as_link(source_url)
                formatted_urls.append(f"- Source {i}: {markdown_link}")
        
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

            # Only allow WEB sources, ignore S3 sources
            if location.get("type") == "WEB":
                source_url = location.get("webLocation", {}).get("url", None)
            
            if source_url and source_url not in seen_sources:
                reference_links.append(f"- [View Document]({source_url})")
                seen_sources.add(source_url)

            # Fix incorrect currency representation
            # corrected_content = self.correct_currency(content)

            # formatted_content.append(
            #     f"SOURCE {i} [Score: {score}]:\nContent: {corrected_content}\n"
            # )

            formatted_content.append(
                f"SOURCE {i} [Score: {score}]"
            )

        if not formatted_content:
            return "No relevant content with available sources found in knowledge base.", ""

        return "\n".join(formatted_content), "\n".join(reference_links)


    # def format_retrieval_results(self, response: Dict) -> (str, str):
    #     if "error" in response:
    #         return f"Retrieval Error: {response['error']}", ""
        
    #     results = response.get("retrievalResults", [])
    #     if not results:
    #         return "No relevant content found in knowledge base.", ""

    #     formatted_content = []
    #     reference_links = []
    #     seen_sources = set()  # Track unique sources contributing to responses

    #     for i, result in enumerate(results, 1):
    #         content = result["content"]["text"]
    #         score = result.get("score", "N/A")
    #         location = result.get("location", {})
    #         source_url = None

    #         # Extract source URL from location type
    #         if location.get("type") == "WEB":
    #             source_url = location.get("webLocation", {}).get("url", None)
    #         elif location.get("type") == "S3":
    #             source_url = location.get("s3Location", {}).get("uri", None)

    #         if source_url:
    #             if source_url.startswith("s3://"):
    #                 display_url = self.get_presigned_url(source_url)
    #             else:
    #                 display_url = source_url
                
    #             filename = os.path.basename(source_url.split("?")[0])

    #             # Ensure unique sources only
    #             if source_url not in seen_sources:
    #                 reference_links.append(f"- [{filename}]({display_url})")
    #                 seen_sources.add(source_url)  # Avoid duplication
            
    #         formatted_content.append(
    #             f"SOURCE {i} [Score: {score}]:\nContent: {content}\n"
    #         )

    #     if not formatted_content:
    #         return "No relevant content with available sources found in knowledge base.", ""

    #     return "\n".join(formatted_content), "\n".join(reference_links)

    def get_relevant_context(self, query: str) -> str:
        response = self.retrieve(query, advanced=True)
        return self.format_retrieval_results(response)
