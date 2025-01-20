# app/routes/price_review.py

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app.models import Invoice, InvoiceItem, Product, PriceHistory
from app import db
from datetime import datetime

bp = Blueprint('price_review', __name__)

@bp.route('/invoice/<int:invoice_id>/price-changes', methods=['GET'])
@login_required
def get_price_changes(invoice_id):
    """Get all price changes for review"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    price_changes = []
    for item in invoice.items:
        if item.product:  # Only include items matched to products
            # Calculate the new price based on category margin
            category_margin = item.product.category.default_margin if item.product.category else 0
            new_price = item.cost_price * (1 + category_margin/100)
            
            price_changes.append({
                'id': item.id,
                'name': item.product.name,
                'category': item.product.category.name if item.product.category else 'Uncategorized',
                'current_price': item.product.selling_price,
                'new_price': round(new_price, 2),
                'cost_price': item.cost_price,
                'margin': category_margin
            })
    
    return jsonify(price_changes)

@bp.route('/invoice/<int:invoice_id>/confirm-prices', methods=['POST'])
@login_required
def confirm_prices(invoice_id):
    """Confirm and apply all price changes"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        
        # Begin transaction
        for item in invoice.items:
            if item.product and item.is_matched:
                # Get the current product
                product = item.product
                
                # Create price history record
                history = PriceHistory(
                    product_id=product.id,
                    cost_price=item.cost_price,
                    selling_price=product.selling_price,
                    margin=product.margin,
                    invoice_id=invoice_id,
                    effective_date=datetime.utcnow(),
                    change_type='invoice',
                    change_reason=f'Price update from invoice {invoice.invoice_number}'
                )
                db.session.add(history)
                
                # Update product prices
                category_margin = product.category.default_margin if product.category else 0
                product.cost_price = item.cost_price
                product.selling_price = item.cost_price * (1 + category_margin/100)
                product.margin = category_margin
                product.last_price_update = datetime.utcnow()
                
                # Update invoice item status
                item.status = 'pending_update'  # This will make it appear in staff's update list
                
        # Update invoice status
        invoice.status = 'prices_set'
        invoice.processed_by_id = current_user.id
        invoice.processed_date = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Prices confirmed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error confirming prices: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/invoice/<int:invoice_id>/summary', methods=['GET'])
@login_required
def get_summary(invoice_id):
    """Get summary statistics for price changes"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    total_items = len(invoice.items)
    increases = 0
    decreases = 0
    no_change = 0
    
    for item in invoice.items:
        if item.product:
            category_margin = item.product.category.default_margin if item.product.category else 0
            new_price = item.cost_price * (1 + category_margin/100)
            
            if new_price > item.product.selling_price:
                increases += 1
            elif new_price < item.product.selling_price:
                decreases += 1
            else:
                no_change += 1
    
    return jsonify({
        'total_items': total_items,
        'increases': increases,
        'decreases': decreases,
        'no_change': no_change
    })