# config_llm.py
import os

class LLMClient:
    def __init__(self):
        # Para futuro uso com OpenAI ou outras LLMs
        self.api_key = os.getenv('OPENAI_API_KEY')
    
    def is_available(self):
        return bool(self.api_key)