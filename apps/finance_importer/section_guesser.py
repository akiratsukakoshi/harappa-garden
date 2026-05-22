import subprocess
import logging
import json
import os

logger = logging.getLogger("SectionGuesser")

class SectionGuesser:
    def __init__(self, config_path="apps/finance_importer/mapping_config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.sections = self.config.get('sections', {})
        self.keyword_rules = self.config.get('keyword_rules', {})

    def _call_gemini(self, prompt):
        try:
            # Using -p flag based on help output
            # Warning: The CLI might output ANSI codes or welcome messages.
            # We strictly want the answer.
            cmd = ["gemini", "-p", prompt]
            
            # Using Popen to capture stdout
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                # Add timeout to prevent hanging (Short timeout for UX)
                stdout, stderr = process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                logger.warning("Gemini CLI timed out (skipping AI guess).")
                return None
            
            if process.returncode != 0:
                logger.error(f"Gemini CLI error: {stderr}")
                return None
            
            return stdout
        except Exception as e:
            logger.error(f"Gemini Call failed: {e}")
        return None

    def guess(self, description):
        # 1. Exact/Full Section name match
        # Check if any full section name appears in description
        for name, id_val in self.sections.items():
            if name in description:
                logger.info(f"Rule match: '{name}' in '{description}' -> {name}")
                return id_val
        
        # 2. Keywrod Rules (Shorthand match)
        for keyword, section_name in self.keyword_rules.items():
            if keyword in description:
                if section_name in self.sections:
                    logger.info(f"Keyword match: '{keyword}' in '{description}' -> {section_name}")
                    return self.sections[section_name]
        
        # 3. AI Inference
        # Prepare a concise prompt
        candidates = list(self.sections.keys())
        prompt_text = (
            f"Classify this transaction: '{description}'. "
            f"Possible categories: {candidates}. "
            "Just return the category name."
        )
        
        logger.info(f"Invoking Gemini for: {description}")
        response = self._call_gemini(prompt_text)
        
        if response:
            # Response cleaning: remove ANSI codes if any, whitespace
            import re
            clean_resp = re.sub(r'\x1b\[[0-9;]*m', '', response) # ANSI strip
            clean_resp = clean_resp.strip()
            
            # The CLI might output greeting "Hi there..."
            # We need to find if any candidate is in the output
            # Prioritize exact match from the end of the string?
            
            for candidate in candidates:
                if candidate in clean_resp:
                    # Found a candidate in the response
                    logger.info(f"AI inferred: {candidate}")
                    return self.sections[candidate]
            
            logger.warning(f"AI response did not contain valid candidate. Response: {clean_resp[:50]}...")
        
        return None
