# app/routes/pricing.py

from flask import Blueprint, jsonify, request, current_app, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.models import Invoice, TempProduct, Category, MarginSuggestion, Task
from app.services.price_service import EnhancedPriceService
from app.services.claude_service import ClaudeService
from app.extensions import db
from app.utils.error_handling import APIError, handle_database_error, log_api_call
from datetime import datetime

bp = Blueprint('pricing', __name__)

@bp.route('/invoice/<int:invoice_id>/pricing')
@login_required
def pricing(invoice_id):
    """Show pricing page"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        mode = request.args.get('mode', 'manual')
        
        service = EnhancedPriceService()
        categories = service.calculate_category_summary(invoice_id)
        
        return render_template(
            'invoice/pricing.html',
            invoice=invoice,
            categories=categories['categories'],
            mode=mode
        )
    except Exception as e:
        current_app.logger.error(f"Error loading pricing page: {str(e)}")
        return redirect(url_for('invoice.manage'))

@bp.route('/api/invoice/<int:invoice_id>/categories')
@login_required
@log_api_call
def get_categories(invoice_id):
    """Get categorized summary of invoice products"""
    try:
        service = EnhancedPriceService()
        summary = service.calculate_category_summary(invoice_id)
        
        return jsonify({
            'status': 'success',
            'categories': summary['categories']
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting categories: {str(e)}")
        raise APIError("Failed to get category summary")

@bp.route('/api/invoice/<int:invoice_id>/calculate-prices', methods=['POST'])
@login_required
@log_api_call
@handle_database_error
def calculate_prices(invoice_id):
    """Calculate prices for a category with given margin"""
    try:
        data = request.get_json()
        if not data:
            raise APIError("No data provided")
            
        category = data.get('category')
        margin = data.get('margin')
        
        if not category or margin is None:
            raise APIError("Category and margin are required")
            
        service = EnhancedPriceService()
        result = service.calculate_prices(
            invoice_id,
            {category: float(margin)}
        )
        
        # Extract category calculations
        category_summary = result['summary']['by_category'].get(category, {})
        calculations = {
            'avg_selling_price': category_summary.get('total_selling', 0) / category_summary.get('count', 1),
            'total_revenue': category_summary.get('total_selling', 0),
            'profit': category_summary.get('total_selling', 0) - category_summary.get('total_cost', 0)
        }
        
        return jsonify({
            'status': 'success',
            'calculations': calculations
        })
        
    except Exception as e:
        current_app.logger.error(f"Error calculating prices: {str(e)}")
        raise APIError("Failed to calculate prices")

@bp.route('/api/invoice/<int:invoice_id>/suggest-margins', methods=['POST'])
@login_required
@log_api_call
@handle_database_error
def suggest_margins(invoice_id):
    """Get AI-suggested margins based on location"""
    try:
        data = request.get_json()
        if not data:
            raise APIError("No data provided")
            
        location = data.get('location')
        area_type = data.get('areaType')
        
        if not location or not area_type:
            raise APIError("Location and area type are required")
            
        # Update invoice with location info
        invoice = Invoice.query.get_or_404(invoice_id)
        invoice.location = location
        invoice.area_type = area_type
        
        # Get margin suggestions from Claude
        claude = ClaudeService()
        suggestions = claude.get_margin_suggestions(location, area_type)
        
        # Calculate summary with suggested margins
        service = EnhancedPriceService()
        result = service.calculate_prices(invoice_id, suggestions)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'margins': suggestions,
            'summary': {
                'total_products': result['summary']['total_products'],
                'total_cost': result['summary']['total_cost'],
                'expected_revenue': result['summary']['total_selling']
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting margin suggestions: {str(e)}")
        raise APIError("Failed to get margin suggestions")

@bp.route('/api/invoice/<int:invoice_id>/save-prices', methods=['POST'])
@login_required
@log_api_call
@handle_database_error
def save_prices(invoice_id):
    """Save calculated prices and create staff tasks"""
    try:
        data = request.get_json()
        if not data:
            raise APIError("No data provided")
            
        margins = data.get('margins')
        
        if not margins:
            raise APIError("Margins are required")
            
        # Save final prices
        service = EnhancedPriceService()
        result = service.calculate_prices(invoice_id, margins)
        
        # Create staff tasks
        tasks = service.create_tasks(invoice_id)
        
        # Update invoice status
        invoice = Invoice.query.get_or_404(invoice_id)
        invoice.status = 'prices_set'
        invoice.processed_date = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'redirect': url_for('invoice.review', invoice_id=invoice_id)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error saving prices: {str(e)}")
        raise APIError("Failed to save prices")

@bp.route('/api/invoice/<int:invoice_id>/price-tasks')
@login_required
@log_api_call
def get_price_tasks(invoice_id):
    """Get status of price update tasks"""
    try:
        service = EnhancedPriceService()
        result = service.get_task_progress(invoice_id)
        
        return jsonify({
            'status': 'success',
            'tasks': result['summary']['tasks']
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting price tasks: {str(e)}")
        raise APIError("Failed to get price tasks")