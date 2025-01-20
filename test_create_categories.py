# test_create_categories.py
from app import create_app
from app.extensions import db
from app.models import Category, Product

def create_categories():
    app = create_app()
    with app.app_context():
        try:
            # Instead of deleting, let's get existing categories
            existing_categories = {cat.name: cat for cat in Category.query.all()}
            
            # List of retail store categories with default margins
            categories = [
                # Beverages
                ("Soft Drinks", 0.30),
                ("Juices", 0.30),
                ("Water & Soda", 0.25),
                ("Energy Drinks", 0.35),
                ("Tea & Coffee", 0.40),
                
                # Food Items
                ("Snacks & Chips", 0.35),
                ("Biscuits & Cookies", 0.35),
                ("Chocolates & Candies", 0.40),
                ("Instant Foods", 0.30),
                ("Dry Fruits & Nuts", 0.45),
                ("Packaged Foods", 0.30),
                ("Cooking Oil", 0.20),
                ("Rice & Grains", 0.20),
                ("Spices & Masalas", 0.35),
                ("Noodles & Pasta", 0.30),
                ("Breakfast Items", 0.30),
                
                # Dairy & Fresh
                ("Dairy Products", 0.20),
                ("Bread & Bakery", 0.25),
                ("Ice Cream", 0.35),
                
                # Personal Care
                ("Soaps & Body Wash", 0.40),
                ("Hair Care Products", 0.45),
                ("Shampoos & Conditioners", 0.45),
                ("Hair Oils", 0.40),
                ("Hair Colors & Dyes", 0.45),
                ("Skin Care", 0.45),
                ("Dental Care", 0.40),
                ("Deodorants & Perfumes", 0.50),
                ("Feminine Hygiene", 0.35),
                ("Men's Grooming", 0.45),
                
                # Cleaning & Household
                ("Detergents", 0.30),
                ("Dish Washing", 0.35),
                ("Floor Cleaners", 0.35),
                ("Bathroom Cleaners", 0.35),
                ("Air Fresheners", 0.45),
                ("Insecticides", 0.35),
                ("Cleaning Tools", 0.40),
                ("Paper Products", 0.35),
                ("Disposable Items", 0.40),
                
                # Baby Care
                ("Baby Food", 0.30),
                ("Baby Care", 0.35),
                ("Diapers & Wipes", 0.25),
                
                # Others
                ("Pet Supplies", 0.35),
                ("Stationery", 0.50),
                ("Batteries", 0.45),
                ("Light Bulbs", 0.40),
                ("Plastic Ware", 0.45),
                ("Kitchen Items", 0.40),
                ("Home Storage", 0.45),
                ("Cell Accessories", 0.50),
                
                # Seasonal Items
                ("Festive Items", 0.50),
                ("School Supplies", 0.45),
                ("Garden Items", 0.40),
                
                # Health & Wellness
                ("Health Supplements", 0.40),
                ("First Aid", 0.35),
                ("Face Masks", 0.40),
                ("Sanitizers", 0.35)
            ]
            
            # Update or create categories
            for name, margin in categories:
                if name in existing_categories:
                    # Update existing category
                    cat = existing_categories[name]
                    cat.default_margin = margin
                    print(f"Updated category: {name}")
                else:
                    # Create new category
                    cat = Category(
                        name=name,
                        default_margin=margin
                    )
                    db.session.add(cat)
                    print(f"Created new category: {name}")
            
            db.session.commit()
            
            # Display all categories
            print("\nCurrent Categories:")
            print("-" * 60)
            
            # Group categories for better display
            last_group = ""
            for category in sorted(Category.query.all(), key=lambda x: x.name):
                # Try to determine group from category name
                if "Drinks" in category.name or "Juice" in category.name or "Water" in category.name or "Tea" in category.name:
                    group = "BEVERAGES"
                elif "Food" in category.name or "Snacks" in category.name or "Chocolate" in category.name:
                    group = "FOOD ITEMS"
                elif "Hair" in category.name or "Skin" in category.name or "Care" in category.name:
                    group = "PERSONAL CARE"
                elif "Clean" in category.name or "Detergent" in category.name:
                    group = "CLEANING & HOUSEHOLD"
                else:
                    group = "OTHERS"
                
                # Print group header if it's a new group
                if group != last_group:
                    print(f"\n{group}:")
                    last_group = group
                
                # Get product count for this category
                product_count = Product.query.filter_by(category_id=category.id).count()
                print(f"  • {category.name:<25} (Margin: {category.default_margin * 100:.1f}%, Products: {product_count})")
            
            print(f"\nTotal Categories: {Category.query.count()}")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error managing categories: {str(e)}")

if __name__ == "__main__":
    create_categories()