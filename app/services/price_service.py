# app/services/price_service.py
from app.extensions import db
from app.models import TempProduct, Product, PriceUpdate
from anthropic import Anthropic
import os

class PriceCalculationService:  # Changed class name
    def __init__(self):
        self.client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

    def get_invoice_summary(self, invoice_id):  # Added this method to match route expectations
        return self.get_categories_summary(invoice_id)

    def get_categories_summary(self, invoice_id):
        """Get summary of categories and their products"""
        products = TempProduct.query.filter_by(invoice_id=invoice_id).all()
        categories = {}
        
        for product in products:
            if product.category not in categories:
                categories[product.category] = {
                    'count': 0,
                    'total_cost': 0,
                    'products': []
                }
            
            categories[product.category]['count'] += 1
            categories[product.category]['total_cost'] += product.cost_price
            categories[product.category]['products'].append({
                'name': product.name,
                'quantity': product.quantity,
                'cost_price': product.cost_price
            })
        
        return categories

    def suggest_margins(self, invoice_id, location):
        """Get AI-suggested margins based on location"""
        categories = self.get_categories_summary(invoice_id)
        
        prompt = f"""
        Please suggest profit margins for different product categories in a {location} location.
        Consider factors like:
        - Competition in the area
        - Standard industry margins
        - Product type and turnover
        
        Categories:
        {list(categories.keys())}
        
        Please format your response as JSON with category names as keys and 
        suggested margin percentages as values.
        """

        try:
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            return response.content[0].text
        except Exception as e:
            current_app.logger.error(f"Error suggesting margins: {str(e)}")
            return {}

    def calculate_prices_manual(self, invoice_id, margins):  # Added this method to match route expectations
        """Calculate prices using manually set margins"""
        return self.calculate_prices(invoice_id, margins)

    def calculate_prices(self, invoice_id, margins):
        """Calculate selling prices based on margins"""
        products = TempProduct.query.filter_by(invoice_id=invoice_id).all()
        price_updates = []
        
        for product in products:
            margin = margins.get(product.category, 0.3)  # Default 30% margin
            selling_price = product.cost_price * (1 + margin)
            
            price_update = PriceUpdate(
                product_id=product.id,
                invoice_id=invoice_id,
                old_cost_price=product.cost_price,
                new_cost_price=product.cost_price,
                new_selling_price=selling_price,
                new_margin=margin * 100,
                status='pending'
            )
            price_updates.append(price_update)
            
        db.session.add_all(price_updates)
        db.session.commit()
        
        return price_updates

    def create_staff_tasks(self, invoice_id):
        """Create update tasks for staff"""
        updates = PriceUpdate.query.filter_by(
            invoice_id=invoice_id,
            status='pending'
        ).all()
        
        # Group by category for easier handling
        tasks = {}
        for update in updates:
            category = update.product.category.name
            if category not in tasks:
                tasks[category] = []
            tasks[category].append({
                'product_id': update.product_id,
                'product_name': update.product.name,
                'old_price': update.old_selling_price,
                'new_price': update.new_selling_price,
                'status': 'pending'
            })
            
        return tasks