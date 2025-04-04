from typing import Dict, Optional, Any
import yaml
import re
import os
from pathlib import Path

class InstitutionManager:
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Get the absolute path to the institutions_config.yaml file
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, "institutions_config.yaml")

        self.config = self._load_config(config_path)
        self.institutions = self.config["institutions"]
        self.prompt_templates = self.config["prompt_templates"]
        self.default_institution_id = os.getenv("DEFAULT_INSTITUTION_ID", "lpu")

    def _load_config(self, config_path: str) -> Dict:
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Could not find institutions_config.yaml at {config_path}. Current working directory: {os.getcwd()}")

    def get_institution_config(self, institution_id: Optional[str] = None) -> Dict:
        """Get institution configuration, falling back to default if not specified."""
        if not institution_id:
            institution_id = self.default_institution_id

        institution = self.institutions.get(institution_id)
        if not institution:
            raise ValueError(f"Institution {institution_id} not found")
        return institution

    def get_prompt_template(self, institution_id: Optional[str] = None) -> str:
        """Get the raw prompt template for an institution."""
        institution = self.get_institution_config(institution_id)
        template_name = institution["prompt_template"]
        return self.prompt_templates[template_name]

    def get_processed_prompt(self, institution_id: Optional[str] = None) -> str:
        """Get a prompt with all placeholders replaced with institution values."""
        institution = self.get_institution_config(institution_id)
        template = self.get_prompt_template(institution_id)

        # Create a dictionary of all placeholders and their values
        placeholders = {
            "{{INSTITUTION_NAME}}": institution["name"],
            "{{INSTITUTION_SHORT_NAME}}": institution["short_name"],
            "{{ROLE}}": institution["role"],
            "{{WEBSITE}}": institution["website"],
            "{{ADMISSIONS_URL}}": institution["admissions_url"],
            "{{PROGRAMS_URL}}": institution["programs_url"]
        }

        # Replace all placeholders in the template
        processed_template = template
        for placeholder, value in placeholders.items():
            processed_template = processed_template.replace(placeholder, value)

        return processed_template