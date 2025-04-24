from typing import Dict, Optional, Any
import os
import logging
from institution_settings import institution_settings

logger = logging.getLogger(__name__)

class InstitutionManager:
    def __init__(self):
        """Initialize the institution manager using Pydantic settings."""
        self.institutions = institution_settings.institutions
        self.prompt_templates = institution_settings.prompt_templates
        self.default_institution_id = institution_settings.default_institution_id

        logger.info(f"Initialized InstitutionManager with default institution: {self.default_institution_id}")
        logger.info(f"Available institutions: {list(self.institutions.keys())}")

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
        template_name = institution.prompt_template
        return getattr(self.prompt_templates, template_name)

    def get_processed_prompt(self, institution_id: Optional[str] = None) -> str:
        """Get a prompt with all placeholders replaced with institution values."""
        institution = self.get_institution_config(institution_id)
        template = self.get_prompt_template(institution_id)

        placeholders = {
            "{{INSTITUTION_NAME}}": institution.name,
            "{{INSTITUTION_SHORT_NAME}}": institution.short_name,
            "{{ROLE}}": institution.role,
            "{{WEBSITE}}": institution.website,
            "{{ADMISSIONS_URL}}": institution.admissions_url,
            "{{PROGRAMS_URL}}": institution.programs_url
        }

        processed_template = template
        for placeholder, value in placeholders.items():
            processed_template = processed_template.replace(placeholder, value)

        return processed_template