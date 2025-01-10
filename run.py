from app import create_app, db
from app.models import User, Product, Wholesaler, OrderList, OrderListItem, CustomerOrder, CustomerOrderItem, DailySales, SalesDocument

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Product': Product,
        'Wholesaler': Wholesaler,
        'OrderList': OrderList,
        'OrderListItem': OrderListItem,
        'CustomerOrder': CustomerOrder,
        'CustomerOrderItem': CustomerOrderItem,
        'DailySales': DailySales,
        'SalesDocument': SalesDocument
    }

if __name__ == '__main__':
    app.run(debug=True)