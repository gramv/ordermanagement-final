from flask import (
    Blueprint, 
    render_template, 
    request, 
    jsonify, 
    current_app, 
    url_for,
    flash, 
    redirect
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import json

from app.extensions import db
from app.models import Invoice, Wholesaler, TempProduct
from app.forms import UploadForm
from app.services.cloudinary_service import CloudinaryService
from app.services.invoice_processor import EnhancedInvoiceProcessor as InvoiceProcessor
from app.services.margin_service import EnhancedMarginService
from app.services.location_service import get_demographics, analyze_competition, get_market_insights
from app.utils.error_handling import APIError, handle_database_error, log_api_call

bp = Blueprint('invoice', __name__, url_prefix='/invoice')

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    """
    Check if the uploaded file has an allowed extension
    
    :param filename: Name of the uploaded file
    :return: Boolean indicating if file extension is allowed
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_invoice():
    """
    Handle invoice upload with Cloudinary and OpenAI processing
    
    Follows the system flow:
    Phase 1: Invoice Processing
    a) Upload & Initial Setup (0-25%):
       - Create Invoice Record
       - File Upload to Cloudinary
       - Create Progress Record
    """
    # Create form instance and set up wholesaler choices
    form = UploadForm()
    wholesalers = Wholesaler.query.all()
    form.wholesaler_id.choices = [(w.id, w.name) for w in wholesalers]
    
    if not form.wholesaler_id.choices:
        form.wholesaler_id.choices = [(0, 'No Wholesalers Available')]

    if request.method == 'GET':
        return render_template('invoice/upload.html', form=form)

    if form.validate_on_submit():
        try:
            file = form.file.data
            wholesaler_id = form.wholesaler_id.data
            invoice_date = form.invoice_date.data

            if not file or not allowed_file(file.filename):
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid file type'
                }), 400

            # Create invoice record (0%)
            invoice = Invoice(
                processed_by_id=current_user.id,
                wholesaler_id=wholesaler_id,
                invoice_date=invoice_date,
                status='processing',
                file_path=secure_filename(file.filename)
            )
            db.session.add(invoice)
            db.session.commit()
            current_app.logger.info(f"Created invoice record with ID: {invoice.id}")

            # Save file temporarily (10%)
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{filename}"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            current_app.logger.info(f"Temporary file saved at: {filepath}")

            # Upload to Cloudinary (25%)
            try:
                cloudinary_service = CloudinaryService()
                cloudinary_result = cloudinary_service.upload_invoice(filepath, invoice.id)
                
                invoice.cloudinary_public_id = cloudinary_result.get('public_id')
                invoice.cloudinary_url = cloudinary_result.get('url')
                invoice.cloudinary_secure_url = cloudinary_result.get('secure_url')
                invoice.cloudinary_signature = cloudinary_result.get('signature')
                
                if not invoice.cloudinary_secure_url:
                    raise ValueError("No secure URL returned from Cloudinary")
                    
                db.session.commit()
                current_app.logger.info(f"Cloudinary upload successful: {invoice.cloudinary_secure_url}")
            except Exception as cloudinary_error:
                current_app.logger.error(f"Cloudinary upload failed: {str(cloudinary_error)}")
                invoice.status = 'upload_failed'
                invoice.error_message = str(cloudinary_error)
                db.session.commit()
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({
                    'status': 'error', 
                    'message': 'Cloudinary upload failed',
                    'details': str(cloudinary_error)
                }), 500

            # Process invoice with OpenAI (50%)
            try:
                processor = InvoiceProcessor()
                
                # Extract text (75%)
                extracted_data = processor._extract_text(filepath)
                current_app.logger.info(f"Extracted {len(extracted_data)} products from invoice")
                
                # Categorize products (90%)
                categorized_products = processor._categorize_products(extracted_data)
                
                # Store products in temp_products table (100%)
                for product_data in categorized_products:
                    temp_product = TempProduct(
                        invoice_id=invoice.id,
                        name=product_data['name'],
                        category_name=product_data['category_name'],
                        quantity=product_data['quantity'],
                        cost_price=product_data['price']
                    )
                    db.session.add(temp_product)
                
                invoice.status = 'processed'
                db.session.commit()
                
                current_app.logger.info(f"Stored {len(categorized_products)} temp products for invoice {invoice.id}")
                
                # Clean up temporary file
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                return jsonify({
                    'status': 'success', 
                    'message': 'Invoice processed successfully',
                    'invoice_id': invoice.id,
                    'redirect_url': url_for('invoice.summary', invoice_id=invoice.id)
                }), 200

            except Exception as processing_error:
                current_app.logger.error(f"Invoice processing failed: {str(processing_error)}")
                invoice.status = 'processing_failed'
                invoice.error_message = str(processing_error)
                db.session.commit()
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({
                    'status': 'error', 
                    'message': 'Invoice processing failed',
                    'details': str(processing_error)
                }), 500

        except Exception as e:
            current_app.logger.critical(f"Unexpected error in invoice upload: {str(e)}")
            return jsonify({
                'status': 'error', 
                'message': 'Unexpected server error',
                'details': str(e)
            }), 500
    
    # If form validation fails, return the errors
    errors = {field: errors for field, errors in form.errors.items()}
    current_app.logger.warning(f"Form validation failed: {errors}")
    return jsonify({
        'status': 'error',
        'message': 'Form validation failed',
        'errors': errors
    }), 400

@bp.route('/progress/<int:invoice_id>')
@login_required
def check_progress(invoice_id):
    """Get invoice processing progress"""
    try:
        progress = ProcessingProgress.query.filter_by(invoice_id=invoice_id).first()
        if not progress:
            return jsonify({'error': 'Progress not found'}), 404

        return jsonify({
            'progress': progress.progress,
            'current_step': progress.current_step,
            'detailed_status': progress.detailed_status,
            'invoice_id': invoice_id
        })

    except Exception as e:
        current_app.logger.error(f"Error getting progress: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:invoice_id>/processing')
@login_required
def processing(invoice_id):
    """Show processing status page"""
    if not current_user.role == 'owner':
        abort(403)  # Return HTTP 403 Forbidden
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template('invoice/processing.html', invoice=invoice)

@bp.route('/<int:invoice_id>/status')
@login_required
def check_status(invoice_id):
    """Check the processing status of an invoice"""
    if not current_user.role == 'owner':
        return jsonify({'error': 'Access denied'}), 403

    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Get processing progress from the database
    progress = ProcessingProgress.query.filter_by(invoice_id=invoice_id).first()
    
    if not progress:
        return jsonify({
            'status': 'error',
            'error': 'No progress record found'
        })
    
    if invoice.status == 'processed':
        return jsonify({
            'status': 'processed',
            'redirect': url_for('invoice.summary', invoice_id=invoice_id)
        })
    elif invoice.status == 'failed':
        return jsonify({
            'status': 'failed',
            'error': progress.error_message or invoice.error_message or 'Unknown error'
        })
    else:
        # Return current progress
        return jsonify({
            'status': 'processing',
            'progress': progress.progress,
            'current_step': progress.current_step,
            'detailed_status': progress.detailed_status,
            'estimated_time_remaining': progress.estimated_time_remaining,
            'invoice_id': invoice_id
        })

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
        
        # Create new progress record
        progress = ProcessingProgress(
            invoice_id=invoice.id,
            progress=0,
            current_step='Retrying...',
            detailed_status='Preparing to retry invoice processing...'
        )
        db.session.add(progress)
        db.session.commit()

        # Start processing in background
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
            
            service = EnhancedMarginService()
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
        
        service = EnhancedMarginService()
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

@bp.route('/<int:invoice_id>/pricing')
@login_required
def pricing_method(invoice_id):
    """Show pricing method selection"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        if invoice.status != 'processed':
            flash('Invoice must be processed first', 'warning')
            return redirect(url_for('invoice.upload_invoice'))
            
        return render_template('invoice/pricing_method.html', invoice=invoice)
        
    except Exception as e:
        current_app.logger.error(f"Error loading pricing options: {str(e)}")
        flash('Error loading pricing options', 'error')
        return redirect(url_for('invoice.upload_invoice'))

@bp.route('/<int:invoice_id>/manual-pricing')
@login_required
def manual_pricing(invoice_id):
    """Handle manual pricing"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        if invoice.status != 'processed':
            flash('Invoice must be processed first', 'warning')
            return redirect(url_for('invoice.pricing_method', invoice_id=invoice_id))
            
        # Get all temp products for this invoice
        temp_products = TempProduct.query.filter_by(invoice_id=invoice_id).all()
        
        # Group products by category
        products_by_category = {}
        for product in temp_products:
            if product.category_name not in products_by_category:
                products_by_category[product.category_name] = []
            products_by_category[product.category_name].append(product)
        
        # Sort categories alphabetically
        categories = sorted(products_by_category.keys())
        
        return render_template('invoice/pricing.html',
                             invoice=invoice,
                             categories=categories,
                             products_by_category=products_by_category,
                             is_ai_pricing=False)
                             
    except Exception as e:
        current_app.logger.error(f"Error loading manual pricing: {str(e)}")
        flash('Error loading manual pricing', 'error')
        return redirect(url_for('invoice.pricing_method', invoice_id=invoice_id))

@bp.route('/<int:invoice_id>/ai-pricing')
@login_required
def ai_pricing(invoice_id):
    """Handle AI-based pricing"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        if invoice.status != 'processed':
            flash('Invoice must be processed first', 'warning')
            return redirect(url_for('invoice.pricing_method', invoice_id=invoice_id))
            
        # Get all temp products for this invoice
        temp_products = TempProduct.query.filter_by(invoice_id=invoice_id).all()
        
        # Group products by category
        products_by_category = {}
        for product in temp_products:
            if product.category_name not in products_by_category:
                products_by_category[product.category_name] = []
            products_by_category[product.category_name].append(product)
        
        # Sort categories alphabetically
        categories = sorted(products_by_category.keys())
        
        return render_template('invoice/pricing.html',
                             invoice=invoice,
                             categories=categories,
                             products_by_category=products_by_category,
                             is_ai_pricing=True)
                             
    except Exception as e:
        current_app.logger.error(f"Error loading AI pricing: {str(e)}")
        flash('Error loading AI pricing', 'error')
        return redirect(url_for('invoice.pricing_method', invoice_id=invoice_id))

@bp.route('/<int:invoice_id>/analyze-location', methods=['POST'])
@login_required
def analyze_location(invoice_id):
    """Analyze location for AI pricing suggestions"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        location = data.get('location')
        area_type = data.get('areaType')
        
        if not location or not area_type:
            return jsonify({'error': 'Location and area type are required'}), 400
            
        # Get AI suggestions
        service = PriceCalculationService()
        result = service.get_ai_suggestions(invoice_id, location, area_type)
        
        return jsonify({
            'success': True,
            'margins': result.get('margins', {}),
            'insights': result.get('insights', {})
        })
        
    except Exception as e:
        current_app.logger.error(f"Error analyzing location: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:invoice_id>/save-prices', methods=['POST'])
@login_required
def save_prices(invoice_id):
    """Save calculated prices for invoice items"""
    try:
        data = request.get_json()
        if not data or 'prices' not in data:
            return jsonify({'error': 'No prices provided'}), 400
            
        invoice = Invoice.query.get_or_404(invoice_id)
        if invoice.status != 'processed':
            return jsonify({'error': 'Invoice must be processed first'}), 400
            
        # Update prices for each product
        for price_data in data['prices']:
            product_id = price_data.get('product_id')
            margin = price_data.get('margin')
            selling_price = price_data.get('selling_price')
            
            temp_product = TempProduct.query.get(product_id)
            if temp_product and temp_product.invoice_id == invoice_id:
                temp_product.margin = margin
                temp_product.selling_price = selling_price
                temp_product.status = 'pending_update'
        
        invoice.status = 'prices_set'
        db.session.commit()
        
        # Create staff tasks for label updates
        task_service = TaskService()
        task_service.create_price_update_tasks(invoice_id)
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving prices: {str(e)}")
        return jsonify({'error': str(e)}), 500

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

@bp.route('/<int:invoice_id>/summary')
@login_required
def summary(invoice_id):
    from flask import flash, redirect, url_for
    
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Check if invoice is processed
    if invoice.status != 'processed':
        flash('Invoice is not yet processed', 'warning')
        return redirect(url_for('invoice.upload_invoice'))
    
    try:
        # Get products from temp_products table
        temp_products = invoice.temp_products
        current_app.logger.info(f"Retrieved {len(temp_products)} temp products for invoice {invoice_id}")
        
        # Process categories
        categories_dict = {}
        total_value = 0
        total_products = 0
        
        for product in temp_products:
            category_name = product.category_name
            product_total = product.cost_price * product.quantity
            total_value += product_total
            total_products += product.quantity
            
            if category_name not in categories_dict:
                categories_dict[category_name] = {
                    'name': category_name,
                    'products': [],
                    'total': 0
                }
            
            categories_dict[category_name]['products'].append({
                'name': product.name,
                'quantity': product.quantity,
                'cost_price': product.cost_price,
                'total': product.cost_price * product.quantity
            })
            categories_dict[category_name]['total'] += product.cost_price * product.quantity
        
        # Convert to list and sort by category name
        categories = list(categories_dict.values())
        categories.sort(key=lambda x: x['name'])
        
        current_app.logger.info(f"Processed {len(categories)} categories for invoice {invoice_id}")
        
        return render_template('invoice/summary.html',
                             invoice=invoice,
                             categories=categories,
                             total_value=total_value,
                             total_products=total_products)
                             
    except Exception as e:
        current_app.logger.error(f"Error processing summary for invoice {invoice_id}: {str(e)}")
        flash('Error loading invoice summary', 'error')
        return redirect(url_for('invoice.upload_invoice'))

@bp.route('/manage')
@login_required
def manage():
    """Invoice management dashboard"""
    today = datetime.utcnow().date()
    
    # Get invoice statistics
    stats = {
        'total': Invoice.query.count(),
        'processing': Invoice.query.filter_by(status='processing').count(),
        'pending_tasks': Invoice.query.filter_by(status='pending').count(),
        'completed_today': Invoice.query.filter(
            Invoice.status == 'completed',
            func.date(Invoice.upload_date) == today
        ).count()
    }
    
    # Get recent invoices
    invoices = Invoice.query\
        .options(joinedload(Invoice.wholesaler))\
        .order_by(desc(Invoice.upload_date))\
        .limit(10)\
        .all()
    
    return render_template('invoice/manage.html',
                         stats=stats,
                         invoices=invoices)

@bp.route('/test-processing', methods=['GET'])
@login_required
def test_processing():
    try:
        # Use an existing file
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'img20240925_14494371.jpg')
        
        # Create test invoice
        invoice = Invoice(
            wholesaler_id=1,  # Make sure this wholesaler exists
            invoice_date=datetime.utcnow().date(),
            file_path=file_path,
            status='uploaded'
        )
        db.session.add(invoice)
        db.session.commit()
        
        # Initialize processor
        processor = InvoiceProcessor()
        
        # Process invoice
        result = processor.process_invoice(invoice.id, file_path)
        
        # Return the results
        products = TempProduct.query.filter_by(invoice_id=invoice.id).all()
        return jsonify({
            'status': 'success',
            'invoice_id': invoice.id,
            'product_count': len(products),
            'categories': list(set(p.category_name for p in products))
        })
        
    except Exception as e:
        current_app.logger.error(f"Test processing error: {str(e)}")
        return jsonify({'error': str(e)}), 500