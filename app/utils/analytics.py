# app/utils/analytics.py

from sqlalchemy import func, extract
from collections import defaultdict
from datetime import datetime, timedelta
from app.models import DailySales, OrderList, OrderListItem, Product, Wholesaler
from app import db

def get_previous_period_sales(start_date, end_date):
    """Get sales data for previous period"""
    days_diff = (end_date - start_date).days
    prev_end_date = start_date - timedelta(days=1)
    prev_start_date = prev_end_date - timedelta(days=days_diff)

    prev_sales = DailySales.query\
        .filter(DailySales.date.between(prev_start_date, prev_end_date))\
        .all()

    return sum(sale.total_actual for sale in prev_sales) if prev_sales else 0

def get_previous_period_orders(start_date, end_date):
    """Get order data for previous period"""
    days_diff = (end_date - start_date).days
    prev_end_date = start_date - timedelta(days=1)
    prev_start_date = prev_end_date - timedelta(days=days_diff)

    prev_orders = OrderList.query\
        .filter(OrderList.date.between(prev_start_date, prev_end_date))\
        .options(joinedload(OrderList.items))\
        .all()

    return sum(
        item.quantity * item.product.price 
        for order in prev_orders 
        for item in order.items
    ) if prev_orders else 0

def analyze_sales_patterns(sales_data):
    """Analyze sales patterns by day, hour, and month"""
    patterns = {
        'weekday': defaultdict(lambda: {
            'total': 0,
            'count': 0,
            'max': 0,
            'min': float('inf')
        }),
        'hourly': defaultdict(lambda: {
            'total': 0,
            'count': 0,
            'max': 0,
            'min': float('inf')
        }),
        'monthly': defaultdict(lambda: {
            'total': 0,
            'count': 0,
            'max': 0,
            'min': float('inf')
        })
    }

    if sales_data:
        for sale in sales_data:
            # Weekday analysis
            weekday = sale.date.strftime('%A')
            patterns['weekday'][weekday]['total'] += sale.total_actual
            patterns['weekday'][weekday]['count'] += 1
            patterns['weekday'][weekday]['max'] = max(patterns['weekday'][weekday]['max'], sale.total_actual)
            patterns['weekday'][weekday]['min'] = min(patterns['weekday'][weekday]['min'], sale.total_actual)

            # Hourly analysis
            hour = sale.report_time.strftime('%H:00')
            patterns['hourly'][hour]['total'] += sale.total_actual
            patterns['hourly'][hour]['count'] += 1
            patterns['hourly'][hour]['max'] = max(patterns['hourly'][hour]['max'], sale.total_actual)
            patterns['hourly'][hour]['min'] = min(patterns['hourly'][hour]['min'], sale.total_actual)

            # Monthly analysis
            month = sale.date.strftime('%B')
            patterns['monthly'][month]['total'] += sale.total_actual
            patterns['monthly'][month]['count'] += 1
            patterns['monthly'][month]['max'] = max(patterns['monthly'][month]['max'], sale.total_actual)
            patterns['monthly'][month]['min'] = min(patterns['monthly'][month]['min'], sale.total_actual)

        # Calculate averages and handle min values
        for pattern_type in patterns.values():
            for stats in pattern_type.values():
                if stats['count'] > 0:
                    stats['avg'] = stats['total'] / stats['count']
                    if stats['min'] == float('inf'):
                        stats['min'] = stats['total']
                else:
                    stats['avg'] = 0
                    stats['min'] = 0

    return patterns

def calculate_sales_metrics(sales_data, start_date, end_date):
    """Calculate key sales metrics"""
    metrics = {
        'total_sales': 0,
        'prev_period_sales': 0,
        'total_discrepancy': 0,
        'transaction_count': 0,
        'avg_transaction': 0,
        'discrepancy_count': 0,
        'payment_totals': {
            'cash': 0,
            'card': 0,
            'otc': 0
        }
    }

    if sales_data:
        metrics['total_sales'] = sum(sale.total_actual for sale in sales_data)
        metrics['total_discrepancy'] = sum(sale.overall_discrepancy for sale in sales_data)
        metrics['transaction_count'] = len(sales_data)
        metrics['avg_transaction'] = metrics['total_sales'] / metrics['transaction_count'] if metrics['transaction_count'] > 0 else 0
        metrics['discrepancy_count'] = sum(1 for sale in sales_data if abs(sale.overall_discrepancy) > 10)

        metrics['payment_totals'] = {
            'cash': sum((sale.front_register_cash + sale.back_register_cash) for sale in sales_data),
            'card': sum(sale.credit_card_total for sale in sales_data),
            'otc': sum((sale.otc1_total + sale.otc2_total) for sale in sales_data)
        }

        # Get previous period data
        metrics['prev_period_sales'] = get_previous_period_sales(start_date, end_date)

    return metrics

def calculate_order_metrics(orders, start_date, end_date):
    """Calculate key order metrics"""
    metrics = {
        'total_orders_value': 0,
        'prev_period_value': 0,
        'total_orders': 0,
        'pending_orders': 0,
        'pending_orders_value': 0
    }

    if orders:
        metrics['total_orders'] = len(orders)
        metrics['total_orders_value'] = sum(
            item.quantity * item.product.price 
            for order in orders 
            for item in order.items
        )

        pending_orders = [o for o in orders if o.status == 'pending']
        metrics['pending_orders'] = len(pending_orders)
        metrics['pending_orders_value'] = sum(
            item.quantity * item.product.price 
            for order in pending_orders 
            for item in order.items
        )

        # Get previous period data
        metrics['prev_period_value'] = get_previous_period_orders(start_date, end_date)

    return metrics

def analyze_top_products(start_date, end_date, limit=10):
    """Analyze top performing products"""
    products = db.session.query(
        Product,
        func.coalesce(func.sum(OrderListItem.quantity), 0).label('quantity'),
        func.coalesce(func.sum(OrderListItem.quantity * Product.price), 0).label('value')
    ).select_from(OrderList)\
     .join(OrderListItem)\
     .join(Product)\
     .filter(OrderList.date.between(start_date, end_date))\
     .group_by(Product.id)\
     .order_by(func.sum(OrderListItem.quantity * Product.price).desc())\
     .limit(limit)\
     .all()

    return [{
        'name': p[0].name,
        'quantity': int(p[1]),
        'value': float(p[2]),
        'profit': float(p[2]) * 0.4  # 40% profit margin
    } for p in products]

def analyze_wholesaler_performance(start_date, end_date):
    """Analyze wholesaler performance"""
    performance = db.session.query(
        Wholesaler,
        func.count(func.distinct(OrderList.id)).label('orders'),
        func.coalesce(func.sum(OrderListItem.quantity * Product.price), 0).label('value')
    ).select_from(Wholesaler)\
     .join(OrderList)\
     .join(OrderListItem)\
     .join(Product)\
     .filter(OrderList.date.between(start_date, end_date))\
     .group_by(Wholesaler.id)\
     .all()

    return [{
        'name': w[0].name,
        'orders': int(w[1]),
        'value': float(w[2]),
        'profit': float(w[2]) * 0.4
    } for w in performance]

def get_sales_trend_data(start_date, end_date, period='daily'):
    """Get sales trend data for charts"""
    sales_data = DailySales.query\
        .filter(DailySales.date.between(start_date, end_date))\
        .order_by(DailySales.date)\
        .all()

    trends = defaultdict(lambda: {'total': 0, 'count': 0})

    for sale in sales_data:
        key = sale.date.strftime('%Y-%m-%d')
        if period == 'weekly':
            week_start = sale.date - timedelta(days=sale.date.weekday())
            key = week_start.strftime('%Y-%m-%d')
        elif period == 'monthly':
            key = sale.date.strftime('%Y-%m')

        trends[key]['total'] += sale.total_actual
        trends[key]['count'] += 1

    return {
        'labels': list(trends.keys()),
        'totals': [t['total'] for t in trends.values()],
        'counts': [t['count'] for t in trends.values()]
    }

def get_order_trend_data(start_date, end_date, period='daily'):
    """Get order trend data for charts"""
    orders = OrderList.query\
        .filter(OrderList.date.between(start_date, end_date))\
        .options(
            joinedload(OrderList.items),
            joinedload(OrderList.wholesaler)
        )\
        .order_by(OrderList.date)\
        .all()

    trends = defaultdict(lambda: {'total': 0, 'count': 0})

    for order in orders:
        key = order.date.strftime('%Y-%m-%d')
        if period == 'weekly':
            week_start = order.date - timedelta(days=order.date.weekday())
            key = week_start.strftime('%Y-%m-%d')
        elif period == 'monthly':
            key = order.date.strftime('%Y-%m')

        order_value = sum(item.quantity * item.product.price for item in order.items)
        trends[key]['total'] += order_value
        trends[key]['count'] += 1

    return {
        'labels': list(trends.keys()),
        'totals': [t['total'] for t in trends.values()],
        'counts': [t['count'] for t in trends.values()]
    }