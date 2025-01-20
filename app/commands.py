import click
from flask.cli import with_appcontext
from app import db
from app.models import Category

@click.command('add-categories')
@with_appcontext
def add_categories_command():
    """Add initial categories to the database."""
    categories = [
        {'name': 'Beverages', 'default_margin': 0.25},
        {'name': 'Snacks', 'default_margin': 0.30},
        {'name': 'Dairy', 'default_margin': 0.20},
        {'name': 'Bread', 'default_margin': 0.15},
        {'name': 'Canned Goods', 'default_margin': 0.25},
        {'name': 'Cleaning', 'default_margin': 0.35},
        {'name': 'Personal Care', 'default_margin': 0.40},
        {'name': 'Stationery', 'default_margin': 0.45},
        {'name': 'Household', 'default_margin': 0.30},
        {'name': 'Pet Supplies', 'default_margin': 0.25}
    ]
    
    try:
        for cat_data in categories:
            category = Category.query.filter_by(name=cat_data['name']).first()
            if not category:
                category = Category(**cat_data)
                db.session.add(category)
                click.echo(f"Added category: {cat_data['name']}")
            else:
                click.echo(f"Category already exists: {cat_data['name']}")
        
        db.session.commit()
        click.echo('Categories added successfully!')
        
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error adding categories: {str(e)}', err=True) 