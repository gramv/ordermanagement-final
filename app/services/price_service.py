# app/services/price_service.py
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from flask import current_app
from app import db
from app.models import (TempProduct, PriceUpdate, Category, Invoice, 
                       TempPriceHistory, Task)

class EnhancedPriceService:
    def __init__(self):
        self.logger = current_app.logger

    def _round_price(self, price, rounding_method='99'):
        """
        Round price according to retail pricing conventions
        Methods:
        - '99': Round to nearest .99 (default)
        - '95': Round to nearest .95
        - 'std': Standard mathematical rounding
        """
        try:
            if rounding_method == '99':
                # Round to nearest .99
                base = Decimal(str(price)).quantize(Decimal('0'), rounding=ROUND_HALF_UP)
                return float(base - Decimal('0.01'))
            elif rounding_method == '95':
                # Round to nearest .95
                base = Decimal(str(price)).quantize(Decimal('0'), rounding=ROUND_HALF_UP)
                return float(base - Decimal('0.05'))
            else:
                # Standard rounding to 2 decimal places
                return float(Decimal(str(price)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        except Exception as e:
            self.logger.error(f"Error rounding price {price}: {str(e)}")
            return round(price, 2)

    def calculate_category_summary(self, invoice_id):
        """Generate summary statistics by category"""
        try:
            # Get all temp products for this invoice
            products = TempProduct.query.filter_by(invoice_id=invoice_id).all()
            if not products:
                raise ValueError(f"No products found for invoice {invoice_id}")

            # Initialize summary
            summary = {
                'total_products': 0,
                'total_cost': 0.0,
                'categories': {}
            }

            # Group products by category
            for product in products:
                category = product.category_name
                if category not in summary['categories']:
                    summary['categories'][category] = {
                        'product_count': 0,
                        'total_cost': 0.0,
                        'avg_margin': None,
                        'products': []
                    }

                cat_summary = summary['categories'][category]
                cat_summary['product_count'] += 1
                cat_summary['total_cost'] += product.cost_price * product.quantity
                cat_summary['products'].append({
                    'id': product.id,
                    'name': product.name,
                    'cost_price': product.cost_price,
                    'quantity': product.quantity
                })

                summary['total_products'] += 1
                summary['total_cost'] += product.cost_price * product.quantity

            # Calculate average margins from historical data
            for category in summary['categories'].keys():
                avg_margin = self._get_category_average_margin(category)
                summary['categories'][category]['avg_margin'] = avg_margin

            return summary

        except Exception as e:
            self.logger.error(f"Error calculating category summary: {str(e)}")
            raise

    def _get_category_average_margin(self, category_name):
        """Get average margin for a category from historical data"""
        try:
            category = Category.query.filter_by(name=category_name).first()
            if not category:
                return None

            # Get recent price history
            history = TempPriceHistory.query.join(TempProduct).filter(
                TempProduct.category_name == category_name
            ).order_by(
                TempPriceHistory.created_at.desc()
            ).limit(100).all()

            if not history:
                return category.default_margin

            # Calculate average margin
            total_margin = sum(h.margin for h in history)
            return round(total_margin / len(history), 2)

        except Exception as e:
            self.logger.error(f"Error getting average margin for {category_name}: {str(e)}")
            return None

    def calculate_prices(self, invoice_id, margins, rounding_method='99'):
        """Calculate selling prices based on margins"""
        try:
            invoice = Invoice.query.get_or_404(invoice_id)
            
            for product in invoice.temp_products:
                category = product.category_name
                if category in margins:
                    margin = float(margins[category])
                    product.margin = margin
                    product.calculate_selling_price()
            
            db.session.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Error calculating prices: {str(e)}")
            db.session.rollback()
            return False

    def create_tasks(self, invoice_id):
        """Create tasks for staff to update price tags"""
        try:
            invoice = Invoice.query.get_or_404(invoice_id)
            invoice.create_price_update_tasks()
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating tasks: {str(e)}")
            return False

    def get_category_summary(self, invoice_id):
        """Get summary of products by category"""
        try:
            invoice = Invoice.query.get_or_404(invoice_id)
            return invoice.category_summary
            
        except Exception as e:
            self.logger.error(f"Error getting category summary: {str(e)}")
            return None

    def get_task_progress(self, invoice_id):
        """Get progress of price update tasks"""
        try:
            tasks = Task.query.join(TempProduct).filter(
                TempProduct.invoice_id == invoice_id
            ).all()

            if not tasks:
                return {'status': 'no_tasks', 'message': 'No tasks found'}

            summary = {
                'total': len(tasks),
                'completed': sum(1 for t in tasks if t.status == 'completed'),
                'pending': sum(1 for t in tasks if t.status == 'pending'),
                'in_progress': sum(1 for t in tasks if t.status == 'in_progress'),
                'tasks': [{
                    'id': t.id,
                    'product_name': t.temp_product.name,
                    'status': t.status,
                    'completed_at': t.completed_at.isoformat() if t.completed_at else None
                } for t in tasks]
            }

            return {
                'status': 'success',
                'summary': summary
            }

        except Exception as e:
            self.logger.error(f"Error getting task progress: {str(e)}")
            raise