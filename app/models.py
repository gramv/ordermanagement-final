from app.extensions import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class PriceUpdate(db.Model):
    __tablename__ = 'price_update'
    id = db.Column(db.Integer, primary_key=True)
    temp_product_id = db.Column(db.Integer, db.ForeignKey('temp_product.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Simplified price fields
    old_price = db.Column(db.Float, nullable=False)
    new_price = db.Column(db.Float, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='employee')  # 'employee', 'owner'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    price_updates_made = db.relationship('PriceUpdate', 
                                       back_populates='updated_by',
                                       foreign_keys=[PriceUpdate.updated_by_id])
    invoices_processed = None
    sales_records = db.relationship('DailySales', backref='employee', lazy=True)
    processed_invoices = db.relationship('Invoice', 
                                       foreign_keys='Invoice.processed_by_id',
                                       back_populates='processor')

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
    __tablename__ = 'wholesaler'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_daily = db.Column(db.Boolean, default=False)
    contact_person = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    
    # Invoice related fields
    invoice_format = db.Column(db.String(50))  # PDF, image, etc.
    invoice_parsing_notes = db.Column(db.Text)  # Notes for AI about invoice structure
    
    # Relationships
    order_lists = db.relationship('OrderList', back_populates='wholesaler')
    products = db.relationship('Product', back_populates='wholesaler')
    invoices = db.relationship('Invoice', back_populates='wholesaler')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Product(db.Model):
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
    wholesaler = db.relationship('Wholesaler', back_populates='products')
    
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
    price_history = db.relationship('PriceHistory', backref='product', lazy=True)
    order_items = db.relationship('OrderListItem', backref='product')
    customer_order_items = db.relationship('CustomerOrderItem', backref='product')

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
    __tablename__ = 'order_list_item'
    id = db.Column(db.Integer, primary_key=True)
    order_list_id = db.Column(db.Integer, db.ForeignKey('order_list.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    
    # Relationships
    order_list = db.relationship('OrderList', back_populates='items')

class CustomerOrder(db.Model):
    __tablename__ = 'customer_order'
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_contact = db.Column(db.String(100), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    is_paid = db.Column(db.Boolean, default=False)
    total_amount = db.Column(db.Float, default=0.0)
    
    # Relationships
    items = db.relationship('CustomerOrderItem', backref='customer_order', lazy='dynamic')

class CustomerOrderItem(db.Model):
    __tablename__ = 'customer_order_item'
    id = db.Column(db.Integer, primary_key=True)
    customer_order_id = db.Column(db.Integer, db.ForeignKey('customer_order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    custom_product_name = db.Column(db.String(100))  # For products not in stock
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')

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
    __tablename__ = 'invoice'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(100), unique=True)
    wholesaler_id = db.Column(db.Integer, db.ForeignKey('wholesaler.id'))
    processed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # File details
    file_path = db.Column(db.String(500))
    cloudinary_public_id = db.Column(db.String(255))
    file_type = db.Column(db.String(50))  # PDF, image, etc.
    
    # Processing status
    status = db.Column(db.String(50), default='uploaded')
    processing_notes = db.Column(db.Text)
    error_message = db.Column(db.Text)
    
    # Timestamps
    invoice_date = db.Column(db.Date, nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    processed_date = db.Column(db.DateTime)
    
    # Relationships
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True)
    price_updates = db.relationship('PriceUpdate', 
                                  back_populates='invoice',
                                  cascade='all, delete-orphan')
    wholesaler = db.relationship('Wholesaler', 
                               back_populates='invoices')
    processor = db.relationship('User', 
                              foreign_keys=[processed_by_id],
                              back_populates='processed_invoices')
    temp_products = db.relationship('TempProduct', 
                                  back_populates='invoice',
                                  cascade='all, delete-orphan')

class InvoiceItem(db.Model):
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
    
    # Extracted/matched data
    quantity = db.Column(db.Integer)
    cost_price = db.Column(db.Float)
    total_amount = db.Column(db.Float)
    
    # Price comparison fields
    previous_cost_price = db.Column(db.Float)
    price_difference = db.Column(db.Float)
    price_difference_percentage = db.Column(db.Float)
    price_status = db.Column(db.String(50))  # 'matched', 'lower', 'higher'
    requires_approval = db.Column(db.Boolean, default=False)
    approval_notes = db.Column(db.Text)
    
    # Processing status
    is_matched = db.Column(db.Boolean, default=False)
    matching_confidence = db.Column(db.Float)
    needs_review = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    staff_processed = db.Column(db.Boolean, default=False)
    price_status = db.Column(db.String(20), default='pending')

    # Cloudinary fields
    cloudinary_public_id = db.Column(db.String(255))
    cloudinary_url = db.Column(db.String(512))

    def calculate_price_difference(self):
        """Calculate price difference and set status"""
        if self.previous_cost_price and self.cost_price:
            self.price_difference = self.cost_price - self.previous_cost_price
            self.price_difference_percentage = (
                (self.cost_price - self.previous_cost_price) / 
                self.previous_cost_price * 100
            )
            
            if abs(self.price_difference) < 0.01:  # Using small epsilon for float comparison
                self.price_status = 'matched'
                self.requires_approval = False
            elif self.price_difference < 0:
                self.price_status = 'lower'
                self.requires_approval = False
            else:
                self.price_status = 'higher'
                self.requires_approval = True

class TempProduct(db.Model):
    __tablename__ = 'temp_product'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100))
    quantity = db.Column(db.Integer)
    cost_price = db.Column(db.Float)
    selling_price = db.Column(db.Float, nullable=True)
    margin = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default='pending')
    
    # Updated relationships
    invoice = db.relationship('Invoice', back_populates='temp_products')
    price_updates = db.relationship('PriceUpdate', 
                                  back_populates='temp_product',
                                  cascade='all, delete-orphan')

class PriceHistory(db.Model):
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

class TempPriceHistory(db.Model):
    __tablename__ = 'temp_price_history'
    id = db.Column(db.Integer, primary_key=True)
    temp_product_id = db.Column(db.Integer, db.ForeignKey('temp_product.id'))
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    cost_price = db.Column(db.Float, nullable=False)
    margin = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Add relationships
    temp_product = db.relationship('TempProduct',
                                 backref=db.backref('price_history', lazy=True))
    invoice = db.relationship('Invoice',
                            backref=db.backref('temp_price_history', lazy=True))
    updated_by = db.relationship('User', backref='price_updates')

class StaffPriceTask(db.Model):
    __tablename__ = 'staff_price_task'
    id = db.Column(db.Integer, primary_key=True)
    temp_product_id = db.Column(db.Integer, db.ForeignKey('temp_product.id'))
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='pending')
    label_printed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    temp_product = db.relationship('TempProduct', backref='staff_tasks')
    staff = db.relationship('User', backref='price_tasks')

def to_dict(self):
    """Convert PriceUpdate instance to dictionary"""
    return {
        'id': self.id,
        'product_id': self.product_id,
        'invoice_id': self.invoice_id,
        'old_cost_price': self.old_cost_price,
        'new_cost_price': self.new_cost_price,
        'old_selling_price': self.old_selling_price,
        'new_selling_price': self.new_selling_price,
        'old_margin': self.old_margin,
        'new_margin': self.new_margin,
        'status': self.status,
        'created_at': self.created_at.isoformat() if self.created_at else None,
        'completed_at': self.completed_at.isoformat() if self.completed_at else None
    }

# Then add relationship references
PriceUpdate.temp_product = db.relationship('TempProduct', back_populates='price_updates')
PriceUpdate.invoice = db.relationship('Invoice', back_populates='price_updates')
PriceUpdate.updated_by = db.relationship('User', back_populates='price_updates_made')