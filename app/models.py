from app.extensions import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from datetime import timedelta

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class PriceUpdate(db.Model):
    """Model for tracking price updates"""
    __tablename__ = 'price_update'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    temp_product_id = db.Column(db.Integer, db.ForeignKey('temp_product.id'), nullable=False)
    old_price = db.Column(db.Float)
    new_price = db.Column(db.Float)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    update_date = db.Column(db.DateTime, default=datetime.utcnow)
    reason = db.Column(db.Text)
    
    # Relationships
    temp_product = db.relationship('TempProduct', back_populates='price_updates')
    invoice = db.relationship('Invoice', back_populates='price_updates')
    updated_by = db.relationship('User', back_populates='price_updates_made')
    
    def to_dict(self):
        """Convert PriceUpdate instance to dictionary"""
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'temp_product_id': self.temp_product_id,
            'old_price': self.old_price,
            'new_price': self.new_price,
            'updated_by_id': self.updated_by_id,
            'update_date': self.update_date.isoformat() if self.update_date else None,
            'reason': self.reason
        }

class User(UserMixin, db.Model):
    """User model for staff and owners"""
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))  # Increased from 128 to 255
    role = db.Column(db.String(20), default='staff')  # owner, staff
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    assigned_tasks = db.relationship('Task',
                                   foreign_keys='Task.assigned_to_id',
                                   backref='assigned_to')
    created_tasks = db.relationship('Task',
                                  foreign_keys='Task.created_by_id',
                                  backref='created_by')
    sales_records = db.relationship('DailySales', backref='employee', lazy=True)
    processed_invoices = db.relationship('Invoice', 
                                       foreign_keys='Invoice.processed_by_id',
                                       back_populates='processed_by')
    price_updates_made = db.relationship('PriceUpdate',
                                       foreign_keys='PriceUpdate.updated_by_id',
                                       back_populates='updated_by')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def is_owner(self):
        return self.role == 'owner'

class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    default_margin = db.Column(db.Float, default=0.3)  # 30% default margin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    products = db.relationship('Product', backref='category', lazy=True)

class Wholesaler(db.Model):
    """Model for wholesalers/suppliers"""
    __tablename__ = 'wholesaler'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    invoices = db.relationship('Invoice', back_populates='wholesaler')
    products = db.relationship('Product', back_populates='wholesaler')
    order_lists = db.relationship('OrderList', back_populates='wholesaler')
    
    def __repr__(self):
        return f'<Wholesaler {self.name}>'

    def to_dict(self):
        """Convert wholesaler to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'contact_person': self.contact_person,
            'email': self.email,
            'phone': self.phone,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Product(db.Model):
    """Model for products"""
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    size = db.Column(db.String(50))
    unit = db.Column(db.String(20))  # e.g., 'ml', 'tablets', 'pcs'
    
    # Price related fields
    cost_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    margin = db.Column(db.Float)  # Current margin percentage
    last_purchase_price = db.Column(db.Float)
    price_trend = db.Column(db.String(20))  # 'stable', 'increasing', 'decreasing'
    price_alert_threshold = db.Column(db.Float, default=10.0)  # Default 10% threshold
    last_price_update = db.Column(db.DateTime)
    price_update_notes = db.Column(db.Text)
    
    # Categorization and relationships
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    wholesaler_id = db.Column(db.Integer, db.ForeignKey('wholesaler.id'))
    
    # Product status
    available_in_store = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Invoice matching fields
    invoice_identifier = db.Column(db.String(100))  # How product appears on invoices
    alternative_names = db.Column(db.String(500))  # Comma-separated alternative names
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    wholesaler = db.relationship('Wholesaler', back_populates='products')
    invoice_items = db.relationship('InvoiceItem', back_populates='product')
    price_history = db.relationship('PriceHistory', back_populates='product', 
                                  cascade='all, delete-orphan')
    order_items = db.relationship('OrderListItem', back_populates='product')
    customer_order_items = db.relationship('CustomerOrderItem', back_populates='product')

    def calculate_margin(self):
        """Calculate and update the margin based on cost_price and selling_price"""
        if self.cost_price and self.cost_price > 0:
            self.margin = ((self.selling_price - self.cost_price) / self.cost_price) * 100
        else:
            self.margin = 0
        return self.margin

    def update_price_trend(self, new_price):
        """Update price trend based on new purchase price"""
        if self.last_purchase_price:
            if new_price > self.last_purchase_price:
                self.price_trend = 'increasing'
            elif new_price < self.last_purchase_price:
                self.price_trend = 'decreasing'
            else:
                self.price_trend = 'stable'
        
        self.last_purchase_price = new_price
        self.last_price_update = datetime.utcnow()

class OrderList(db.Model):
    __tablename__ = 'order_list'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    wholesaler_id = db.Column(db.Integer, db.ForeignKey('wholesaler.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'finalized'
    type = db.Column(db.String(10), nullable=False)  # 'daily' or 'monthly'
    finalized_date = db.Column(db.DateTime)
    
    # Relationships
    wholesaler = db.relationship('Wholesaler', back_populates='order_lists')
    items = db.relationship('OrderListItem', back_populates='order_list', cascade='all, delete-orphan')

    def total_value(self):
        return sum(item.quantity * item.product.selling_price for item in self.items)

class OrderListItem(db.Model):
    """Model for items in an order list"""
    __tablename__ = 'order_list_item'
    
    id = db.Column(db.Integer, primary_key=True)
    order_list_id = db.Column(db.Integer, db.ForeignKey('order_list.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    
    # Relationships
    order_list = db.relationship('OrderList', back_populates='items')
    product = db.relationship('Product', back_populates='order_items')

class CustomerOrder(db.Model):
    """Model for customer orders"""
    __tablename__ = 'customer_order'
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_contact = db.Column(db.String(100), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    is_paid = db.Column(db.Boolean, default=False)
    total_amount = db.Column(db.Float, default=0.0)
    
    # Relationships
    items = db.relationship('CustomerOrderItem', back_populates='customer_order', lazy='dynamic')

class CustomerOrderItem(db.Model):
    """Model for items in a customer order"""
    __tablename__ = 'customer_order_item'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_order_id = db.Column(db.Integer, db.ForeignKey('customer_order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    custom_product_name = db.Column(db.String(100))
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    
    # Relationships
    customer_order = db.relationship('CustomerOrder', back_populates='items')
    product = db.relationship('Product', back_populates='customer_order_items')

class DailySales(db.Model):
    __tablename__ = 'daily_sales'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    report_time = db.Column(db.DateTime, nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Register readings
    front_register_amount = db.Column(db.Float, nullable=False)
    back_register_amount = db.Column(db.Float, nullable=False)
    credit_card_amount = db.Column(db.Float, nullable=False)
    otc1_amount = db.Column(db.Float, nullable=False)
    otc2_amount = db.Column(db.Float, nullable=False)
    
    # Actual collections
    front_register_cash = db.Column(db.Float, nullable=False)
    back_register_cash = db.Column(db.Float, nullable=False)
    credit_card_total = db.Column(db.Float, nullable=False)
    otc1_total = db.Column(db.Float, nullable=False)
    otc2_total = db.Column(db.Float, nullable=False)
    
    # Calculated fields
    total_expected = db.Column(db.Float, nullable=False)
    total_actual = db.Column(db.Float, nullable=False)
    front_register_discrepancy = db.Column(db.Float, nullable=False)
    back_register_discrepancy = db.Column(db.Float, nullable=False)
    overall_discrepancy = db.Column(db.Float, nullable=False)
    
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    
    # Relationships
    documents = db.relationship('SalesDocument', backref='sales_report', cascade='all, delete-orphan')

    def calculate_discrepancies(self):
        self.front_register_discrepancy = self.front_register_cash - self.front_register_amount
        self.back_register_discrepancy = self.back_register_cash - self.back_register_amount
        self.total_expected = (
            self.front_register_amount +
            self.back_register_amount +
            self.credit_card_amount +
            self.otc1_amount +
            self.otc2_amount
        )
        self.total_actual = (
            self.front_register_cash +
            self.back_register_cash +
            self.credit_card_total +
            self.otc1_total +
            self.otc2_total
        )
        self.overall_discrepancy = self.total_actual - self.total_expected

    @property
    def has_significant_discrepancy(self):
        return abs(self.overall_discrepancy) > 10

class SalesDocument(db.Model):
    __tablename__ = 'sales_documents'
    id = db.Column(db.Integer, primary_key=True)
    sales_id = db.Column(db.Integer, db.ForeignKey('daily_sales.id'), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    cloudinary_public_id = db.Column(db.String(255), nullable=False)
    secure_url = db.Column(db.String(512), nullable=False)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)

class Invoice(db.Model):
    """Model for supplier invoices"""
    __tablename__ = 'invoice'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(100))
    wholesaler_id = db.Column(db.Integer, db.ForeignKey('wholesaler.id'), nullable=False)
    processed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    file_path = db.Column(db.String(255))
    cloudinary_public_id = db.Column(db.String(255))
    cloudinary_url = db.Column(db.String(512))
    cloudinary_secure_url = db.Column(db.String(512))
    cloudinary_signature = db.Column(db.String(255))
    
    # Dates
    invoice_date = db.Column(db.Date, nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    processed_date = db.Column(db.DateTime)
    
    # Processing status
    status = db.Column(db.String(20), default='uploaded')  # uploaded, processing, pricing, completed, error
    error_message = db.Column(db.Text)
    
    # Summary data
    total_amount = db.Column(db.Float)
    total_items = db.Column(db.Integer)
    category_summary = db.Column(db.JSON)  # Store category-wise summary
    
    # Location and pricing info for AI suggestions
    location = db.Column(db.String(100))
    area_type = db.Column(db.String(50))
    
    # Relationships
    wholesaler = db.relationship('Wholesaler', back_populates='invoices')
    processed_by = db.relationship('User', back_populates='processed_invoices')
    temp_products = db.relationship('TempProduct', back_populates='invoice',
                                  cascade='all, delete-orphan')
    items = db.relationship('InvoiceItem', back_populates='invoice',
                          cascade='all, delete-orphan')
    price_updates = db.relationship('PriceUpdate', back_populates='invoice',
                                  cascade='all, delete-orphan')
    price_history = db.relationship('PriceHistory', back_populates='invoice',
                                  cascade='all, delete-orphan')
    temp_price_history = db.relationship('TempPriceHistory', back_populates='invoice',
                                       cascade='all, delete-orphan')
    margin_suggestions = db.relationship('MarginSuggestion', back_populates='related_invoice',
                                      cascade='all, delete-orphan')
    tasks = db.relationship('Task', back_populates='invoice',
                          cascade='all, delete-orphan')
    processing_progress = db.relationship('ProcessingProgress', back_populates='invoice',
                                        cascade='all, delete-orphan',
                                        uselist=False)  # One-to-one relationship

    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'

    def update_status(self, new_status, error_message=None):
        """Update invoice status and optionally set error message"""
        self.status = new_status
        if error_message:
            self.error_message = error_message
        if new_status == 'completed':
            self.processed_date = datetime.utcnow()

    def update_category_summary(self):
        """Update category summary based on temp products"""
        summary = {}
        for product in self.temp_products:
            category = product.category_name
            if category not in summary:
                summary[category] = {
                    'count': 0,
                    'total_cost': 0,
                    'total_selling': 0
                }
            summary[category]['count'] += 1
            summary[category]['total_cost'] += product.cost_price
            if product.selling_price:
                summary[category]['total_selling'] += product.selling_price
        
        self.category_summary = summary
        self.total_items = sum(cat['count'] for cat in summary.values())
        self.total_amount = sum(cat['total_cost'] for cat in summary.values())

    def create_price_update_tasks(self):
        """Create tasks for staff to update price tags"""
        if not self.temp_products:
            return
            
        # Group products by category for better task organization
        categories = {}
        for product in self.temp_products:
            if product.category_name not in categories:
                categories[product.category_name] = []
            categories[product.category_name].append(product)
        
        # Create tasks for each category
        for category, products in categories.items():
            product_list = "\n".join([
                f"- {p.name}: New price ${p.selling_price:.2f}" 
                for p in products
            ])
            
            task = Task(
                title=f"Update price tags - {category}",
                description=f"Please update price tags for the following products:\n{product_list}",
                invoice_id=self.id,
                created_by_id=self.processed_by_id,
                assigned_to_id=self.processed_by_id,  # Initially assign to same person
                priority='high' if len(products) > 10 else 'normal',
                due_date=datetime.utcnow() + timedelta(days=1)
            )
            db.session.add(task)
        
        db.session.commit()

class InvoiceItem(db.Model):
    """Model for individual items in an invoice"""
    __tablename__ = 'invoice_item'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    temp_product_id = db.Column(db.Integer, db.ForeignKey('temp_product.id'))
    
    # Raw data from invoice
    raw_product_name = db.Column(db.String(200))
    raw_product_code = db.Column(db.String(100))
    raw_size = db.Column(db.String(50))
    raw_unit = db.Column(db.String(20))
    raw_quantity = db.Column(db.Float)
    raw_unit_price = db.Column(db.Float)
    raw_total = db.Column(db.Float)
    
    # Processed data
    quantity = db.Column(db.Float)
    unit_price = db.Column(db.Float)
    total = db.Column(db.Float)
    
    # Processing status
    status = db.Column(db.String(20), default='pending')  # pending, matched, unmatched
    confidence_score = db.Column(db.Float)  # AI matching confidence
    matching_notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    invoice = db.relationship('Invoice', back_populates='items')
    product = db.relationship('Product', back_populates='invoice_items')
    temp_product = db.relationship('TempProduct', back_populates='invoice_items')

    def __repr__(self):
        return f'<InvoiceItem {self.raw_product_name}>'

class TempProduct(db.Model):
    """Temporary storage for products during invoice processing"""
    __tablename__ = 'temp_product'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    category_name = db.Column(db.String(100))
    quantity = db.Column(db.Integer)
    cost_price = db.Column(db.Float)
    suggested_margin = db.Column(db.Float)
    margin = db.Column(db.Float)
    selling_price = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    invoice = db.relationship('Invoice', back_populates='temp_products')
    invoice_items = db.relationship('InvoiceItem', back_populates='temp_product')
    price_updates = db.relationship('PriceUpdate', back_populates='temp_product',
                                  cascade='all, delete-orphan')
    price_history = db.relationship('TempPriceHistory', back_populates='temp_product',
                                  cascade='all, delete-orphan')

    def calculate_selling_price(self):
        """Calculate selling price based on cost and margin"""
        if self.cost_price and self.margin:
            self.selling_price = self.cost_price * (1 + self.margin / 100)
        return self.selling_price

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category_name,
            'quantity': self.quantity,
            'cost_price': self.cost_price,
            'suggested_margin': self.suggested_margin,
            'margin': self.margin,
            'selling_price': self.selling_price
        }

class PriceHistory(db.Model):
    """Model for tracking product price history"""
    __tablename__ = 'price_history'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    old_cost_price = db.Column(db.Float, nullable=False)
    new_cost_price = db.Column(db.Float, nullable=False)
    old_selling_price = db.Column(db.Float, nullable=False)
    new_selling_price = db.Column(db.Float, nullable=False)
    margin = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    product = db.relationship('Product', back_populates='price_history')
    invoice = db.relationship('Invoice', back_populates='price_history')

class TempPriceHistory(db.Model):
    """Model for tracking temporary product price history during invoice processing"""
    __tablename__ = 'temp_price_history'
    id = db.Column(db.Integer, primary_key=True)
    temp_product_id = db.Column(db.Integer, db.ForeignKey('temp_product.id'))
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    cost_price = db.Column(db.Float, nullable=False)
    margin = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    temp_product = db.relationship('TempProduct', back_populates='price_history')
    invoice = db.relationship('Invoice', back_populates='temp_price_history')
    updated_by = db.relationship('User', backref=db.backref('temp_price_updates', lazy=True))

class Task(db.Model):
    """Task model for staff assignments"""
    __tablename__ = 'task'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed
    priority = db.Column(db.String(20), default='normal')  # low, normal, high
    due_date = db.Column(db.DateTime)
    
    # Foreign Keys
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationship to Invoice
    invoice = db.relationship('Invoice', back_populates='tasks')
    
    def complete(self):
        """Mark task as completed"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
    
    def to_dict(self):
        """Convert task to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'assigned_to': self.assigned_to.username,
            'created_by': self.created_by.username,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class ProcessingProgress(db.Model):
    """Track invoice processing progress"""
    __tablename__ = 'processing_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    progress = db.Column(db.Integer, default=0)
    current_step = db.Column(db.String(100))
    step_number = db.Column(db.Integer, default=1)
    total_steps = db.Column(db.Integer, default=6)
    detailed_status = db.Column(db.Text)
    stage_details = db.Column(db.JSON)
    ui_message = db.Column(db.Text)
    estimated_time_remaining = db.Column(db.Integer)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    invoice = db.relationship('Invoice', back_populates='processing_progress', uselist=False)

    def __init__(self, invoice_id, progress=0, current_step=None, detailed_status=None, 
                 step_number=1, total_steps=6, estimated_time_remaining=None, error_message=None):
        self.invoice_id = invoice_id
        self.progress = progress
        self.current_step = current_step
        self.detailed_status = detailed_status
        self.step_number = step_number
        self.total_steps = total_steps
        self.estimated_time_remaining = estimated_time_remaining
        self.error_message = error_message

    def update_progress(self, stage, message, progress, details=None):
        """Update progress of invoice processing"""
        self.current_step = stage
        self.ui_message = message
        self.progress = progress
        if details:
            self.stage_details = details
        self.updated_at = datetime.utcnow()

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'progress': self.progress,
            'current_step': self.current_step,
            'step_number': self.step_number,
            'total_steps': self.total_steps,
            'detailed_status': self.detailed_status,
            'stage_details': self.stage_details,
            'ui_message': self.ui_message,
            'estimated_time_remaining': self.estimated_time_remaining,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class MarginSuggestion(db.Model):
    """Model for AI margin suggestions"""
    __tablename__ = 'margin_suggestion'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    category = db.Column(db.String(100))
    suggested_margin = db.Column(db.Float)
    reasoning = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    related_invoice = db.relationship('Invoice', back_populates='margin_suggestions')

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'suggested_margin': self.suggested_margin,
            'reasoning': self.reasoning,
            'created_at': self.created_at.isoformat()
        }