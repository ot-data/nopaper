from typing import Dict, Optional
import yaml
from pathlib import Path

class InstitutionManager:
    def __init__(self, config_path: str = "institutions_config.yaml"):
        self.config = self._load_config(config_path)
        self.institutions = self.config["institutions"]
        self.prompt_templates = self.config["prompt_templates"]
        
    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get_institution_config(self, institution_id: str) -> Optional[Dict]:
        return self.institutions.get(institution_id)
    
    def get_prompt_template(self, institution_id: str) -> str:
        institution = self.get_institution_config(institution_id)
        if not institution:
            raise ValueError(f"Institution {institution_id} not found")
        return self.prompt_templates[institution["prompt_template"]]
    
    def get_kb_id(self, institution_id: str) -> str:
        institution = self.get_institution_config(institution_id)
        if not institution:
            raise ValueError(f"Institution {institution_id} not found")
        return institution["kb_id"]