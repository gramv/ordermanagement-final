# app/routes/pricing.py

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
from app.services.price_service import PriceCalculationService
from app.extensions import db
from app.models import Invoice, Category, Product

bp = Blueprint('pricing', __name__)

@bp.route('/invoice/<int:invoice_id>/categories')
@login_required
def get_invoice_categories(invoice_id):
    """Get categorized summary of invoice items"""
    service = PriceCalculationService()
    categories = service.get_invoice_summary(invoice_id)
    
    return jsonify({
        'categories': categories
    })

@bp.route('/invoice/<int:invoice_id>/calculate-manual', methods=['POST'])
@login_required
def calculate_manual_prices(invoice_id):
    """Calculate prices using manually set margins"""
    category_margins = request.json.get('margins', {})
    
    service = PriceCalculationService()
    price_updates = service.calculate_prices_manual(invoice_id, category_margins)
    
    return jsonify({
        'price_updates': price_updates
    })

@bp.route('/invoice/<int:invoice_id>/suggest-margins', methods=['POST'])
@login_required
def suggest_margins(invoice_id):
    """Get AI-suggested margins based on location"""
    location = request.json.get('location')
    if not location:
        return jsonify({'error': 'Location is required'}), 400
        
    service = PriceCalculationService()
    suggested_margins = service.suggest_margins(invoice_id, location)
    
    return jsonify(suggested_margins)