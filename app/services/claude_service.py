import anthropic
from flask import current_app
from .prompts import create_extraction_prompt, create_pricing_prompt

def extract_invoice_data(file_path):
    """Extract product data from invoice file"""
    with open(file_path, 'r') as f:
        text = f.read()
    service = ClaudeService()
    return service.extract_invoice_data(text)

class ClaudeService:
    def __init__(self):
        self.client = anthropic.Client(api_key=current_app.config['CLAUDE_API_KEY'])

    def extract_invoice_data(self, text):
        """Extract product data from invoice text"""
        prompt = create_extraction_prompt(text)
        
        response = self.client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content

    def get_margin_suggestions(self, location, categories):
        """Get margin suggestions based on location and categories"""
        prompt = create_pricing_prompt(location, categories)
        
        response = self.client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content