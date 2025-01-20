# app/routes/invoice.py

from flask import Blueprint, jsonify, request, render_template, current_app, url_for, flash, redirect
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from app.models import Invoice, TempProduct, Wholesaler, Category
from app.services.invoice_processor import InvoiceProcessor
from app.services.margin_service import MarginService
from app.services.cloudinary_service import CloudinaryService
from app.extensions import db

bp = Blueprint('invoice', __name__, url_prefix='/invoice')

@bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_invoice():
    """Handle invoice upload and initial processing"""
    if not current_user.role == 'owner':
        return jsonify({'error': 'Access denied'}), 403

    if request.method == 'GET':
        wholesalers = Wholesaler.query.all()
        return render_template('invoice/upload.html', wholesalers=wholesalers)

    try:
        file = request.files.get('file')
        wholesaler_id = request.form.get('wholesaler_id')
        invoice_date = request.form.get('invoice_date')
        
        if not file or not wholesaler_id or not invoice_date:
            raise ValueError("File, wholesaler, and invoice date are required")

        # Create upload folder if it doesn't exist
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)

        # Save file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Debug log
        current_app.logger.info(f"File saved at: {filepath}")
        current_app.logger.info(f"File exists: {os.path.exists(filepath)}")
        
        # Create invoice record first to get ID
        invoice = Invoice(
            wholesaler_id=wholesaler_id,
            status='uploaded',
            processed_by_id=current_user.id,
            invoice_date=datetime.strptime(invoice_date, '%Y-%m-%d').date(),
            upload_date=datetime.utcnow(),
            file_path=filepath  # Save the filepath
        )
        db.session.add(invoice)
        db.session.commit()

        try:
            # Upload to Cloudinary
            cloudinary_service = CloudinaryService()
            cloudinary_result = cloudinary_service.upload_invoice(filepath, invoice.id)
            
            # Update invoice with Cloudinary details
            invoice.cloudinary_public_id = cloudinary_result['public_id']
            invoice.cloudinary_url = cloudinary_result['secure_url']
            db.session.commit()

            # Start processing
            processor = InvoiceProcessor()
            result = processor.process_invoice(invoice.id, filepath)  # Pass both arguments

            if result:
                return jsonify({
                    'status': 'success',
                    'redirect': url_for('invoice.processing', invoice_id=invoice.id)
                })

            # Clean up temporary file
            if os.path.exists(filepath):
                os.remove(filepath)
                current_app.logger.info(f"Temporary file removed: {filepath}")

            return jsonify({
                'status': 'success',
                'invoice_id': invoice.id,
                'redirect': url_for('invoice.processing', invoice_id=invoice.id)
            })

        except Exception as e:
            current_app.logger.error(f"Processing error: {str(e)}")
            # If processing fails, delete the invoice record
            db.session.delete(invoice)
            db.session.commit()
            # Clean up temporary file if it exists
            if os.path.exists(filepath):
                os.remove(filepath)
            raise e

    except Exception as e:
        current_app.logger.error(f"Upload error: {str(e)}")
        # Clean up temporary file if it exists
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:invoice_id>/processing')
@login_required
def processing(invoice_id):
    """Show processing status page"""
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template('invoice/processing.html', invoice=invoice)

@bp.route('/<int:invoice_id>/status')
@login_required
def get_status(invoice_id):
    """Get current processing status"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        if invoice.status == 'processed':
            return jsonify({
                'status': invoice.status,
                'redirect': url_for('invoice.pricing_method', invoice_id=invoice_id, _external=True)
            })
        return jsonify({'status': invoice.status})
    except Exception as e:
        current_app.logger.error(f"Error getting invoice status: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/<int:invoice_id>/retry', methods=['POST'])
@login_required
def retry_processing(invoice_id):
    """Retry failed processing"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        if invoice.status != 'failed':
            return jsonify({'error': 'Can only retry failed invoices'}), 400
        
        invoice.status = 'processing'
        invoice.error_message = None
        db.session.commit()
        
        processor = InvoiceProcessor()
        processor.process_invoice(invoice.id)
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ----- Category and Margin Routes -----
@bp.route('/<int:invoice_id>/categories')
@login_required
def get_categories(invoice_id):
    """Get categorized products for the invoice"""
    try:
        temp_products = TempProduct.query.filter_by(invoice_id=invoice_id).all()
        categories = Category.query.all()
        category_dict = {cat.name: cat.id for cat in categories}
        
        categorized = {}
        for product in temp_products:
            if product.category not in categorized:
                categorized[product.category] = {
                    'category_id': category_dict.get(product.category),
                    'products': []
                }
            
            categorized[product.category]['products'].append({
                'id': product.id,
                'name': product.name,
                'quantity': product.quantity,
                'cost_price': product.cost_price
            })
        
        return jsonify({
            'status': 'success',
            'categories': categorized
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:invoice_id>/margins', methods=['GET', 'POST'])
@login_required
def handle_margins(invoice_id):
    """Handle margin viewing and setting"""
    if request.method == 'GET':
        try:
            invoice = Invoice.query.get_or_404(invoice_id)
            temp_products = TempProduct.query.filter_by(invoice_id=invoice_id).all()
            
            categories = {}
            for product in temp_products:
                if product.category not in categories:
                    categories[product.category] = {
                        'products': []
                    }
                categories[product.category]['products'].append({
                    'name': product.name,
                    'quantity': product.quantity,
                    'cost_price': product.cost_price
                })
            
            return render_template('invoice/margins.html',
                                invoice=invoice,
                                categories=categories)
                                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        try:
            data = request.json
            margins = data.get('margins', {})
            
            service = MarginService()
            result = service.calculate_prices(invoice_id, margins)
            
            return jsonify({
                'status': 'success',
                'task_id': result['task_id']
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@bp.route('/<int:invoice_id>/suggest-margins', methods=['POST'])
@login_required
def suggest_margins(invoice_id):
    """Get AI-suggested margins based on location"""
    try:
        location = request.json.get('location')
        if not location:
            return jsonify({'error': 'Location is required'}), 400
            
        temp_products = TempProduct.query.filter_by(invoice_id=invoice_id).all()
        categories = list(set(p.category for p in temp_products))
        
        service = MarginService()
        margins = service.get_ai_suggestions(categories, location)
        
        return jsonify({
            'status': 'success',
            'margins': margins
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ----- Staff Task Routes -----
@bp.route('/tasks')
@login_required
def list_tasks():
    """List all price update tasks"""
    try:
        tasks = TempProduct.query.filter_by(status='pending').all()
        return render_template('invoice/tasks.html', tasks=tasks)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/tasks/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    """Mark a price update task as complete"""
    try:
        task = TempProduct.query.get_or_404(task_id)
        task.status = 'completed'
        task.completed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/price-updates')
@login_required
def price_updates():
    try:
        updates = TempProduct.query.filter_by(status='pending').all()
        return render_template('invoice/price_updates.html', updates=updates)
    except Exception as e:
        current_app.logger.error(f"Error in price updates: {str(e)}")
        flash('An error occurred while loading price updates.', 'danger')
        return redirect(url_for('main.index'))

@bp.route('/<int:invoice_id>/pricing', methods=['GET'])
@login_required
def pricing_method(invoice_id):
    """Show pricing method selection"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        
        # Check invoice status
        if invoice.status != 'processed':
            flash('Invoice must be processed first', 'warning')
            return redirect(url_for('invoice.processing', invoice_id=invoice_id))
            
        temp_products = TempProduct.query.filter_by(invoice_id=invoice_id).all()
        
        # Calculate summaries
        categories = {}
        total_cost = 0
        
        for product in temp_products:
            if product.category not in categories:
                categories[product.category] = {
                    'count': 0,
                    'total_cost': 0
                }
            categories[product.category]['count'] += 1
            categories[product.category]['total_cost'] += product.cost_price
            total_cost += product.cost_price
        
        return render_template('invoice/pricing_method.html',
                             invoice=invoice,
                             categories=categories,
                             total_products=len(temp_products),
                             total_cost=total_cost)
                             
    except Exception as e:
        current_app.logger.error(f"Error in pricing method: {str(e)}")
        flash('Error loading pricing options', 'error')
        return redirect(url_for('main.index'))

@bp.route('/<int:invoice_id>/manual-pricing', methods=['GET', 'POST'])
@login_required
def manual_pricing(invoice_id):
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        
        if request.method == 'POST':
            margins = request.json.get('margins', {})
            # Process margins...
            return jsonify({'status': 'success', 'redirect': url_for('invoice.review_prices', invoice_id=invoice.id)})
            
        # GET: Show form
        categories = {}
        total_cost = 0
        
        temp_products = TempProduct.query.filter_by(invoice_id=invoice_id).all()
        for product in temp_products:
            if product.category not in categories:
                categories[product.category] = {
                    'product_count': 0,
                    'total_cost': 0
                }
            categories[product.category]['product_count'] += 1
            categories[product.category]['total_cost'] += float(product.cost_price)
            total_cost += float(product.cost_price)
        
        return render_template('invoice/manual_pricing.html',
                             invoice=invoice,
                             categories=categories,
                             total_cost=total_cost)
                             
    except Exception as e:
        current_app.logger.error(f"Error in manual pricing: {str(e)}")
        flash('Error loading manual pricing options', 'error')
        return redirect(url_for('invoice.pricing_method', invoice_id=invoice_id))

@bp.route('/<int:invoice_id>/ai-pricing', methods=['GET', 'POST'])
@login_required
def ai_pricing(invoice_id):
    """Handle AI-based pricing"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        temp_products = TempProduct.query.filter_by(invoice_id=invoice_id).all()

        if request.method == 'POST':
            # If location is provided, get AI suggestions
            if 'location' in request.json:
                location = request.json.get('location')
                
                # Get categories for this invoice
                categories = list(set(p.category for p in temp_products))
                
                # Use MarginService to get AI suggestions
                service = MarginService()
                margins = service.get_ai_suggestions(categories, location)
                
                return jsonify({
                    'status': 'success',
                    'margins': margins
                })
            
            # If margins are provided, save them
            elif 'margins' in request.json:
                margins = request.json.get('margins', {})
                
                # Save margins to temp products
                for product in temp_products:
                    if product.category in margins:
                        margin_percent = float(margins[product.category])
                        product.margin = margin_percent
                        product.selling_price = product.cost_price * (1 + margin_percent/100)
                
                db.session.commit()
                
                return jsonify({
                    'status': 'success',
                    'redirect': url_for('invoice.review_prices', invoice_id=invoice_id)
                })
                
            return jsonify({'error': 'Invalid request'}), 400

        # GET: Show AI pricing page
        # Calculate category summaries
        categories = {}
        total_cost = 0
        
        for product in temp_products:
            if product.category not in categories:
                categories[product.category] = {
                    'count': 0,
                    'total_cost': 0.0
                }
            categories[product.category]['count'] += 1
            categories[product.category]['total_cost'] += float(product.cost_price)
            total_cost += float(product.cost_price)

        # Format numbers for display
        for cat_data in categories.values():
            cat_data['total_cost'] = round(cat_data['total_cost'], 2)

        return render_template('invoice/ai_pricing.html',
                             invoice=invoice,
                             categories=categories,
                             total_cost=total_cost)

    except Exception as e:
        current_app.logger.error(f"Error in AI pricing: {str(e)}")
        flash('Error loading AI pricing options', 'error')
        return redirect(url_for('invoice.pricing_method', invoice_id=invoice_id))

@bp.route('/<int:invoice_id>/review-prices', methods=['GET'])
@login_required
def review_prices(invoice_id):
    """Review calculated prices before finalizing"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        temp_products = TempProduct.query.filter_by(invoice_id=invoice_id).all()
        
        # Group by category for review
        categories = {}
        for product in temp_products:
            if product.category not in categories:
                categories[product.category] = []
            categories[product.category].append(product)

        return render_template('invoice/review_prices.html',
                             invoice=invoice,
                             categories=categories)
    except Exception as e:
        current_app.logger.error(f"Error in price review: {str(e)}")
        flash('Error loading price review', 'error')
        return redirect(url_for('invoice.pricing_method', invoice_id=invoice_id))

@bp.route('/<int:invoice_id>/finalize-prices', methods=['POST'])
@login_required
def finalize_prices(invoice_id):
    """Finalize prices and create staff tasks"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        temp_products = TempProduct.query.filter_by(invoice_id=invoice_id).all()
        
        for product in temp_products:
            product.status = 'pending_update'
            
        invoice.status = 'prices_set'
        db.session.commit()
        
        flash('Prices have been finalized. Staff can now update price tags.', 'success')
        return jsonify({'status': 'success'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error finalizing prices: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500