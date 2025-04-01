import os
import re
import yaml
import boto3
from datetime import datetime, timedelta
from typing import Dict, Optional
from dotenv import load_dotenv
load_dotenv()

script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, "config.yaml")


def replace_env_variables(config):
    """Recursively replace placeholders in the format ${VAR_NAME} with environment variables."""
    if isinstance(config, dict):
        return {k: replace_env_variables(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [replace_env_variables(i) for i in config]
    elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
        env_var = config[2:-1]
        return os.getenv(env_var, f"Missing ENV: {env_var}")
    return config

def load_config(config_path: str = config_path):
    """Load config.yaml and replace environment variable placeholders."""
    try:
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)

        # Replace placeholders with actual environment variables
        return replace_env_variables(config)

    except (FileNotFoundError, yaml.YAMLError) as e:
        raise RuntimeError(f"Error loading config: {str(e)}")

def set_aws_credentials(config):
    os.environ["AWS_ACCESS_KEY_ID"] = config["aws"]["access_key"]
    os.environ["AWS_SECRET_ACCESS_KEY"] = config["aws"]["secret_key"]
    os.environ["AWS_REGION_NAME"] = config["aws"]["region"]

def preprocess_query(query: str) -> str:
    query = query.lower().strip()
    query = re.sub(r'\s+', ' ', query)
    query = re.sub(r'[^\w\s]', '', query)
    return query

def is_memory_query(query: str) -> bool:
    processed_query = preprocess_query(query)
    memory_triggers = [
        "previous question", "last question", "what did i ask",
        "what was my question", "my previous", "earlier question"
    ]
    return any(trigger in processed_query for trigger in memory_triggers)

def is_relevant_query(query: str, config: Optional[Dict] = None) -> bool:
    processed_query = preprocess_query(query).lower()
    
    lpu_terms = [
        "lpu", "lovely professional university", "lovely professional", 
        "lpu university", "lovely university", "phagwara campus"
    ]
    education_topics = [
        "fees", "fee structure", "tuition", "payment", "cost", "installment", "scholarship",
        "financial aid", "education loan", "hidden charges", "extra fees", "refund", "discount",
        "admission", "enrollment", "application", "eligibility", "entrance exam", "criteria",
        "cutoff", "selection process", "admission test", "apply", "registration", "interview",
        "course", "program", "degree", "curriculum", "syllabus", "branch", "specialization",
        "btech", "mtech", "phd", "master", "bachelor", "undergraduate", "postgraduate", "diploma",
        "computer science", "mechanical", "civil", "electrical", "ece", "eee", "biotechnology",
        "semester", "credit", "research", "faculty", "professor", "lecturer", "teaching",
        "hostel", "accommodation", "mess", "food", "canteen", "library", "lab", "laboratory",
        "wi-fi", "internet", "facility", "gym", "sports", "auditorium", "classroom", "infrastructure",
        "placement", "internship", "job", "career", "salary", "package", "recruitment",
        "company", "corporate", "industry", "employment", "training", "skill development",
        "campus", "university", "college", "institute", "department", "school", "center of excellence",
        "ranking", "rating", "review", "reputation", "accreditation", "naac", "ugc", "aicte", "parking",
        "film and tv production", "cafeteria", "documents", "job opportunities", "international job opportunities",
        "curfew", "rules", "regulation", "visit", "compulsory", "mandatory", "first year", "students",
        "global", "abroad", "international", "exchange", "study abroad"
    ]
    
    # Explicitly LPU-related
    if any(term in processed_query for term in lpu_terms):
        return True
    
    # Education-related topics
    if any(term in processed_query for term in education_topics):
        return True
    
    education_phrases = [
        "how to apply", "when can i apply", "what courses", "which branch", 
        "how much is the", "what is the fee", "is there a hostel", "tell me about",
        "what about", "how many students", "what is the cutoff", "what are the requirements",
        "how long is the", "do you offer", "can i get", "is there any", "are there any",
        "do i need to", "is it compulsory"
    ]
    
    if any(phrase in processed_query for phrase in education_phrases):
        return True
    
    question_indicators = ["what", "how", "where", "when", "why", "is", "are", "can", "do", "tell me"]
    if any(indicator in processed_query.split() for indicator in question_indicators):
        if any(term in processed_query for term in ["study", "student", "learn", "education", "academic", "job", "career"]):
            return True
    
    return False

def get_cached_answer(question: str, cache: Dict, config: Dict) -> Optional[str]:
    if not config["cache"]["enabled"]:
        return None
    normalized_q = preprocess_query(question)
    if normalized_q in cache:
        entry = cache[normalized_q]
        expiry_seconds = config["cache"]["expiry_seconds"]
        if datetime.now() - entry["timestamp"] < timedelta(seconds=expiry_seconds):
            return entry["answer"]
    return None

def cache_answer(question: str, answer: str, cache: Dict, config: Dict):
    if config["cache"]["enabled"]:
        normalized_q = preprocess_query(question)
        cache[normalized_q] = {
            "answer": answer,
            "timestamp": datetime.now()
        }