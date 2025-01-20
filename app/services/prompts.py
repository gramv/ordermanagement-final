def create_extraction_prompt(text):
    return f"""
    Analyze this invoice and extract:
    1. Product details in exact format as they appear
    2. Quantities
    3. Unit prices
    4. Any product codes/identifiers

    Format your response as JSON:
    {{
        "products": [
            {{
                "name": "exact product name from invoice",
                "quantity": number,
                "unit_price": number,
                "product_code": "code if available",
                "original_text": "complete text as appears in invoice"
            }}
        ]
    }}

    Invoice text:
    {text}
    """

def create_pricing_prompt(location, categories):
    return f"""
    Analyze these product categories for a store in {location} and suggest profit margins.
    Current categories and their default margins:
    {categories}

    Consider:
    - Local market conditions in {location}
    - Typical retail margins
    - Competition levels
    - Type of products
    
    Return JSON format:
    {{
        "category_name": {{
            "suggested_margin": percentage,
            "reasoning": "explanation"
        }}
    }}
    """ 