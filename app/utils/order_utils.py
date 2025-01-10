# app/utils/order_utils.py
from app import db
from app.models import Wholesaler, Order
from datetime import datetime

def generate_daily_orders():
    today = datetime.utcnow().date()
    daily_wholesalers = Wholesaler.query.filter_by(is_daily=True).all()
    
    for wholesaler in daily_wholesalers:
        existing_order = Order.query.filter_by(wholesaler=wholesaler, date=today).first()
        if not existing_order:
            new_order = Order(wholesaler=wholesaler, date=today)
            db.session.add(new_order)
    
    db.session.commit()