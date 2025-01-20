# app/services/invoice_processor.py
import base64
from anthropic import Anthropic
from app.models import Invoice, TempProduct, Category
from app.extensions import db
import json
from flask import current_app, url_for
from datetime import datetime

class InvoiceProcessor:
    def __init__(self):
        self.client = Anthropic(api_key=current_app.config['CLAUDE_API_KEY'])

    def _extract_products(self, file_path):
        """Extract products from invoice using Claude"""
        try:
            system_prompt = """You are a precise invoice parser. 
            Always return complete, valid JSON. Never truncate the response. 
            If there are too many items, return the first 20 items only."""
            
            with open(file_path, 'rb') as file:
                file_content = file.read()
                file_b64 = base64.b64encode(file_content).decode('utf-8')

            message = self.client.beta.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Extract only the product details from this invoice.
                                    Limit to maximum 20 products if there are more.
                                    For each product, extract:
                                    - Exact product name
                                    - Quantity (as a number)
                                    - Price (as a number)
                                    
                                    Return ONLY a valid JSON array of products in this EXACT format, nothing else:
                                    {
                                        "products": [
                                            {
                                                "name": "product name",
                                                "quantity": number,
                                                "price": number
                                            }
                                        ]
                                    }"""
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": file_b64
                            }
                        }
                    ]
                }]
            )

            # Get the response text and clean it
            content = message.content[0].text.strip()
            
            # Log the full response for debugging
            current_app.logger.info("Claude Response:")
            current_app.logger.info(content)

            # Try to find and parse JSON
            try:
                # Find the first { and last }
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                
                if json_start == -1 or json_end == -1:
                    raise ValueError("No JSON object found in response")
                
                json_str = content[json_start:json_end]
                
                # Try to parse the JSON
                try:
                    result = json.loads(json_str)
                    if 'products' not in result:
                        raise ValueError("No products array in response")
                        
                    # Validate each product has required fields
                    for product in result['products']:
                        if not all(key in product for key in ['name', 'quantity', 'price']):
                            raise ValueError("Product missing required fields")
                    
                    return result['products']
                    
                except json.JSONDecodeError as e:
                    # Try to clean up the JSON string
                    json_str = json_str.replace('\n', ' ').replace('\r', '')
                    result = json.loads(json_str)
                    return result['products']
                    
            except Exception as e:
                current_app.logger.error(f"JSON parsing error: {str(e)}")
                current_app.logger.error(f"Attempted to parse: {json_str if 'json_str' in locals() else 'No JSON found'}")
                raise ValueError(f"Failed to parse response as JSON: {str(e)}")

        except Exception as e:
            current_app.logger.error(f"Error in extracting products: {str(e)}")
            raise ValueError(f"Failed to extract products: {str(e)}")

    def _match_categories(self, products):
        """Match products with existing categories"""
        try:
            categories = Category.query.all()
            category_names = [cat.name for cat in categories]
            
            message = self.client.beta.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": f"""You must categorize these products using ONLY the EXACT categories from this list: {', '.join(category_names)}

                                Rules:
                                1. You MUST use categories EXACTLY as provided without any modifications
                                2. For perfumes and fragrances, use 'Deodorants & Perfumes' category
                                3. For cleaning solutions and alcohols, use 'First Aid' or 'Cleaning Tools' as appropriate
                                4. NEVER create new categories or modify existing ones
                                
                                Available categories: {', '.join(category_names)}
                                
                                Products to categorize:
                                {json.dumps(products, indent=2)}
                                
                                Return ONLY valid JSON in this exact format:
                                {{
                                    "categorized_products": [
                                        {{
                                            "name": "product name exactly as given",
                                            "category": "exact category from the list",
                                            "quantity": same number as input,
                                            "price": same number as input
                                        }}
                                    ]
                                }}"""
                }]
            )

            # Get and clean response
            content = message.content[0].text.strip()
            
            # Log for debugging
            current_app.logger.info("Category Matching Response:")
            current_app.logger.info(content)

            # Extract JSON
            json_str = content[content.find('{'):content.rfind('}')+1]
            result = json.loads(json_str)
            
            # Validate categories
            if 'categorized_products' not in result:
                raise ValueError("No categorized_products array in response")
            
            # Validate each product
            for product in result['categorized_products']:
                if not all(key in product for key in ['name', 'category', 'quantity', 'price']):
                    raise ValueError("Product missing required fields")
                if product['category'] not in category_names:
                    raise ValueError(f"Invalid category: {product['category']}. Must be one of: {category_names}")
            
            return result['categorized_products']

        except Exception as e:
            current_app.logger.error(f"Error in matching categories: {str(e)}")
            current_app.logger.error(f"Categories available: {category_names}")
            raise ValueError(f"Failed to categorize products: {str(e)}")

    def _store_results(self, invoice_id, categorized_products):
        """Store processed products in TempProduct table"""
        try:
            for product in categorized_products:
                temp_product = TempProduct(
                    name=product['name'],
                    category=product['category'],
                    quantity=product['quantity'],
                    cost_price=product['price'],  # Changed from price to cost_price
                    invoice_id=invoice_id,
                    status='pending'
                )
                db.session.add(temp_product)
            
            db.session.commit()
            current_app.logger.info(f"Stored {len(categorized_products)} products for invoice {invoice_id}")
        
        except Exception as e:
            current_app.logger.error(f"Error storing results: {str(e)}")
            db.session.rollback()
            raise

    def process_invoice(self, invoice_id, file_path):
        """Process invoice and create temporary products"""
        try:
            # Get raw products from invoice
            products = self._extract_products(file_path)
            
            # Match categories
            categorized_products = self._match_categories(products)
            
            # Store results
            self._store_results(invoice_id, categorized_products)
            
            # Update invoice status
            invoice = Invoice.query.get(invoice_id)
            invoice.status = 'processed'
            db.session.commit()
            
            # Return with _external=True for absolute URL
            return {
                'status': 'success',
                'redirect': url_for('invoice.pricing_method', invoice_id=invoice_id, _external=True)
            }
                
        except Exception as e:
            current_app.logger.error(f"Error processing invoice {invoice_id}: {str(e)}")
            db.session.rollback()
            raise