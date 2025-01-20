# app/routes/price_setting.py

from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required
from app.models import Invoice, Category, InvoiceItem
from app import db
import anthropic
from app.services.price_service import PriceService

bp = Blueprint('pricing', __name__)

@bp.route('/invoice/<int:invoice_id>/pricing')
@login_required
def pricing_page(invoice_id):
    """Show the price setting interface"""
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template('invoice/price_setting.html', invoice_id=invoice_id)

@bp.route('/invoice/<int:invoice_id>/categories')
@login_required
def get_categories(invoice_id):
    """Get categorized items from invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Group items by category
    categories = {}
    for item in invoice.items:
        if item.product and item.product.category:
            category_name = item.product.category.name
            if category_name not in categories:
                categories[category_name] = {
                    'items': [],
                    'current_margin': item.product.category.default_margin
                }
            
            categories[category_name]['items'].append({
                'name': item.product.name,
                'cost_price': item.cost_price,
                'current_price': item.product.selling_price
            })
    
    return jsonify(categories)

@bp.route('/invoice/<int:invoice_id>/suggest-margins', methods=['POST'])
@login_required
def suggest_margins(invoice_id):
    """Get AI-suggested margins based on location"""
    location = request.json.get('location')
    if not location:
        return jsonify({'error': 'Location is required'}), 400
    
    invoice = Invoice.query.get_or_404(invoice_id)
    
    try:
        price_service = PriceService()
        suggestions = price_service.get_margin_suggestions(location, invoice.id)
        return jsonify(suggestions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/invoice/<int:invoice_id>/calculate-prices', methods=['POST'])
@login_required
def calculate_prices(invoice_id):
    """Calculate prices based on provided margins"""
    margins = request.json.get('margins', {})
    if not margins:
        return jsonify({'error': 'Margins are required'}), 400
    
    try:
        price_service = PriceService()
        calculations = price_service.calculate_prices(invoice_id, margins)
        return jsonify(calculations)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/invoice/<int:invoice_id>/review')
@login_required
def review_prices(invoice_id):
    """Show price review page"""
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template('invoice/review.html', invoice=invoice)