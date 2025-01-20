# app/services/margin_service.py

from anthropic import Anthropic
from app.models import TempProduct, PriceUpdate
from app.extensions import db
import json

class MarginService:
    def __init__(self):
        self.client = Anthropic(api_key=current_app.config['CLAUDE_API_KEY'])  # Get from config
        
    def get_ai_suggestions(self, categories, location):
        """Get AI-suggested margins based on location"""
        try:
            prompt = f"""
            As a retail pricing expert, suggest profit margins for these product categories:
            {', '.join(categories)}
            
            Location: {location}
            
            Consider these factors:
            1. Local purchasing power in {location}
            2. Competition and market dynamics
            3. Standard industry margins for each category
            4. Typical product turnover rates
            5. Local price sensitivity
            
            Return only a JSON object with category names as keys and suggested margin percentages as values.
            Example format:
            {{
                "category1": 25.5,
                "category2": 30.0
            }}
            """

            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Log response for debugging
            current_app.logger.info("AI Margin Response:")
            current_app.logger.info(response.content[0].text)
            
            # Extract JSON part from response
            content = response.content[0].text
            json_str = content[content.find('{'):content.rfind('}')+1]
            margins = json.loads(json_str)
            
            # Validate margins
            validated_margins = self._validate_margins(margins)
            
            # Log validated margins
            current_app.logger.info("Validated margins:")
            current_app.logger.info(validated_margins)
            
            return validated_margins
            
        except json.JSONDecodeError as e:
            current_app.logger.error(f"JSON parsing error: {str(e)}")
            current_app.logger.error(f"Response content: {response.content[0].text}")
            raise ValueError("Failed to parse AI response")
        except Exception as e:
            current_app.logger.error(f"Error getting AI suggestions: {str(e)}")
            raise ValueError(f"Failed to get AI suggestions: {str(e)}")

    def calculate_prices(self, invoice_id, margins):
        """Calculate and save prices based on margins"""
        try:
            # Validate margins
            if not margins:
                raise ValueError("No margins provided")
            
            # Get products
            temp_products = TempProduct.query.filter_by(invoice_id=invoice_id).all()
            if not temp_products:
                raise ValueError("No products found for this invoice")
            
            # Create price updates
            updates = []
            for product in temp_products:
                if product.category not in margins:
                    current_app.logger.warning(f"No margin specified for category {product.category}, using default 30%")
                
                margin = margins.get(product.category, 30.0) / 100
                selling_price = product.cost_price * (1 + margin)
                
                update = PriceUpdate(
                    invoice_id=invoice_id,
                    temp_product_id=product.id,
                    old_cost_price=product.cost_price,
                    new_cost_price=product.cost_price,
                    new_selling_price=round(selling_price, 2),
                    new_margin=margin * 100,
                    status='pending'
                )
                updates.append(update)
                
                # Update temp product as well
                product.margin = margin * 100
                product.selling_price = selling_price
            
            # Save everything to database
            db.session.bulk_save_objects(updates)
            db.session.commit()
            
            task_id = self._create_staff_task(invoice_id, updates)
            
            return {
                'status': 'success',
                'task_id': task_id
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error calculating prices: {str(e)}")
            raise ValueError(f"Failed to calculate prices: {str(e)}")

    def _validate_margins(self, margins):
        """Validate and clean margin values"""
        validated = {}
        for category, margin in margins.items():
            # Ensure margin is a number
            try:
                margin_value = float(margin)
            except (TypeError, ValueError):
                margin_value = 30.0  # Default margin
                
            # Ensure margin is within reasonable bounds (0-100%)
            margin_value = max(0, min(100, margin_value))
            
            validated[category] = margin_value
            
        return validated

    def _create_staff_task(self, invoice_id, updates):
        """Create a task for staff to update price tags"""
        # Implementation for creating staff task
        # This would create a record in your task tracking system
        pass