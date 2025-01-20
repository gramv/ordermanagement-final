# app/routes/staff.py

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.models import PriceUpdate, TempProduct
from app.extensions import db

bp = Blueprint('staff', __name__, url_prefix='/staff')

@bp.route('/tasks')
@login_required
def task_list():
    """Show list of price update tasks"""
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    
    # Query price updates
    query = PriceUpdate.query.filter_by(status='pending')
    
    # Apply filters
    if search:
        query = query.join(TempProduct).filter(
            TempProduct.name.ilike(f'%{search}%')
        )
    if category:
        query = query.join(TempProduct).filter(
            TempProduct.category == category
        )
    
    tasks = query.all()
    
    # Get unique categories
    categories = db.session.query(TempProduct.category).distinct().all()
    
    return render_template('staff/tasks.html',
                         tasks=tasks,
                         categories=categories)

@bp.route('/tasks/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    """Mark a price update as completed"""
    try:
        update = PriceUpdate.query.get_or_404(task_id)
        update.status = 'completed'
        update.completed_by_id = current_user.id
        update.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/tasks/<int:task_id>')
@login_required
def get_task_details(task_id):
    """Get task details for label printing"""
    try:
        update = PriceUpdate.query.get_or_404(task_id)
        return jsonify({
            'product_name': update.temp_product.name,
            'category': update.temp_product.category,
            'new_price': update.new_selling_price,
            'old_price': update.old_selling_price
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500