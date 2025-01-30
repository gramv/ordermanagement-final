import base64
import json
import os
from openai import OpenAI
from flask import current_app
from app.models import Invoice, TempProduct, Category, ProcessingProgress
from app.extensions import db

class EnhancedInvoiceProcessor:
    def __init__(self):
        self.logger = current_app.logger

    def _create_progress_record(self, invoice_id):
        """Create initial progress record"""
        try:
            progress = ProcessingProgress(
                invoice_id=invoice_id,
                progress=0,
                current_step='Started',
                detailed_status='Starting invoice processing...',
                step_number=1,
                total_steps=4
            )
            db.session.add(progress)
            db.session.commit()
            return progress
        except Exception as e:
            self.logger.error(f"Error creating progress record: {str(e)}")
            raise

    def _update_progress(self, progress_record, stage, message, percentage):
        """Update progress record"""
        try:
            progress_record.current_step = stage
            progress_record.detailed_status = message
            progress_record.progress = percentage
            db.session.commit()
        except Exception as e:
            self.logger.error(f"Error updating progress: {str(e)}")

    def process_invoice(self, invoice_id, file_path):
        """
        Comprehensive invoice processing workflow
        Stages:
        0-25%: Initial setup and file upload
        25-50%: Text extraction
        50-75%: Product categorization
        75-100%: Saving products
        """
        try:
            # Stage 0-25%: Initial setup
            invoice = Invoice.query.get_or_404(invoice_id)
            progress_record = self._create_progress_record(invoice_id)
            self.logger.info(f"Processing invoice {invoice_id} from {file_path}")

            # Stage 25-50%: Text Extraction
            try:
                extracted_products = self._extract_text(file_path)
                self._update_progress(progress_record, 50, "Text extracted successfully")
                self.logger.info(f"Extracted {len(extracted_products)} products")
            except Exception as extract_error:
                self.logger.error(f"Text extraction failed: {str(extract_error)}")
                self._update_progress(progress_record, 25, f"Text extraction error: {str(extract_error)}")
                raise

            # Stage 50-75%: Categorization
            try:
                categorized_products = self._categorize_products(extracted_products)
                self._update_progress(progress_record, 75, "Products categorized")
                self.logger.info(f"Categorized {len(categorized_products)} products")
            except Exception as categorize_error:
                self.logger.error(f"Product categorization failed: {str(categorize_error)}")
                self._update_progress(progress_record, 50, f"Categorization error: {str(categorize_error)}")
                raise

            # Stage 75-100%: Save Products
            try:
                self._save_products(invoice, categorized_products)
                self._update_progress(progress_record, 100, "Invoice processing complete")
                self.logger.info(f"Successfully processed invoice {invoice_id}")
            except Exception as save_error:
                self.logger.error(f"Product saving failed: {str(save_error)}")
                self._update_progress(progress_record, 75, f"Saving error: {str(save_error)}")
                raise

            return categorized_products

        except Exception as e:
            self.logger.critical(f"Comprehensive invoice processing failed: {str(e)}")
            # Ensure progress is updated even in failure scenarios
            if 'progress_record' in locals():
                self._update_progress(progress_record, 0, f"Processing failed: {str(e)}")
            raise

    def _extract_text(self, file_path):
        """Extract text from invoice using GPT-4 turbo"""
        try:
            # Validate file exists and is readable
            if not os.path.exists(file_path):
                raise ValueError(f"File not found: {file_path}")
            
            # Read and encode the image
            with open(file_path, 'rb') as file:
                file_bytes = file.read()
                if len(file_bytes) == 0:
                    raise ValueError("Empty file")
                file_b64 = base64.b64encode(file_bytes).decode('utf-8')

            # Create OpenAI client
            client = OpenAI(api_key=current_app.config['OPENAI_API_KEY'])
            
            response = client.chat.completions.create(
                model="gpt-4-turbo",  # Use vision model
                messages=[
                    {
                        "role": "system",
                        "content": """Extract only these fields from the invoice:
                        1. Product name (exactly as written)
                        2. Quantity (as number)
                        3. Unit price (as decimal)

                        Return ONLY JSON in this exact format:
                        {
                            "products": [
                                {
                                    "name": "Product name",
                                    "quantity": 10,
                                    "price": 5.99
                                }
                            ]
                        }
                        
                        If no products are found, return an empty list."""
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract the products from this invoice."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{file_b64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000,
                response_format={"type": "json_object"}  # Force JSON response
            )

            content = response.choices[0].message.content
            
            # Clean up response - remove any markdown or code blocks
            content = content.replace('```json', '').replace('```', '').strip()
            
            try:
                data = json.loads(content)
                products = data.get('products', [])
                
                # Detailed validation
                validated_products = []
                for idx, product in enumerate(products, 1):
                    try:
                        validated_product = {
                            'name': str(product.get('name', f'Unknown Product {idx}')).strip(),
                            'quantity': max(1, int(float(product.get('quantity', 1)))),
                            'price': max(0, float(product.get('price', 0)))
                        }
                        validated_products.append(validated_product)
                    except (ValueError, TypeError) as val_err:
                        self.logger.warning(f"Validation error for product {idx}: {val_err}")
                
                # Log extraction details
                self.logger.info(f"Extracted {len(validated_products)} products from invoice")
                
                if not validated_products:
                    self.logger.warning("No valid products found in extracted data")
                
                return validated_products
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse GPT response: {str(e)}")
                self.logger.error(f"Response content that failed to parse: {content}")
                raise ValueError("Failed to parse invoice")
                
        except Exception as e:
            self.logger.error(f"Comprehensive error extracting text: {str(e)}")
            raise

    def _categorize_products(self, products):
        """Categorize products using GPT matching to DB categories"""
        try:
            # Get categories from DB
            categories = Category.query.all()
            category_names = [cat.name for cat in categories]
            categories_str = ', '.join(category_names)
            
            # Prepare product list for GPT
            product_list = '\n'.join([f"- {p['name']}" for p in products])
            
            # Create OpenAI client
            client = OpenAI(api_key=current_app.config['OPENAI_API_KEY'])
            
            # Get categorization from GPT
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a product categorization expert.
                        Categorize each product into exactly one of these categories: {categories_str}
                        
                        Rules:
                        1. Only use categories from the provided list
                        2. Be consistent with similar products
                        3. Return JSON with product indices and categories
                        4. If unsure, use closest match
                        
                        Example response:
                        {{
                            "categorized_products": [
                                {{"index": 0, "name": "Product Name", "category": "Category Name"}}
                            ]
                        }}"""
                    },
                    {
                        "role": "user",
                        "content": f"Categorize these products:\n{product_list}"
                    }
                ],
                response_format={ "type": "json_object" }
            )
            
            # Parse categorization
            result = json.loads(response.choices[0].message.content)
            categorized = result.get('categorized_products', [])
            
            # Map categories back to products
            categorized_products = []
            for i, product in enumerate(products):
                # Find category for this product
                cat_info = next(
                    (cat for cat in categorized if cat['index'] == i),
                    {'category': 'Uncategorized'}
                )
                
                # Add category to product
                product['category_name'] = cat_info['category']
                categorized_products.append(product)
            
            return categorized_products
            
        except Exception as e:
            self.logger.error(f"Error categorizing products: {str(e)}")
            # Return products with default category
            return [dict(p, category_name='Uncategorized') for p in products]

    def _save_products(self, invoice, products):
        """Save categorized products to database"""
        try:
            # Clear existing temp products
            TempProduct.query.filter_by(invoice_id=invoice.id).delete()
            
            # Save new temp products with categories
            for product in products:
                temp_product = TempProduct(
                    invoice_id=invoice.id,
                    name=product['name'],
                    quantity=product['quantity'],
                    cost_price=product['price'],
                    category_name=product['category_name']
                )
                db.session.add(temp_product)

            db.session.commit()

        except Exception as e:
            self.logger.error(f"Error saving products: {str(e)}")
            db.session.rollback()
            raise

# Alias for backwards compatibility
InvoiceProcessor = EnhancedInvoiceProcessor
