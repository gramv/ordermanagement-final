# Order Management System

A Flask-based web application for managing orders, inventory, and sales for retail businesses.

## Features

- Product Management
- Wholesaler Management
- Daily and Monthly Order Lists
- Customer Order Management
- Daily Sales Recording
- Sales Analytics
- Document Management with Cloudinary Integration

## Tech Stack

- Python 3.x
- Flask
- SQLAlchemy
- Cloudinary
- Bootstrap
- JavaScript/jQuery

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd ordermanagement
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory and add:
```
FLASK_APP=ordermanagement.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
CLOUDINARY_URL=your-cloudinary-url
```

5. Initialize the database:
```bash
flask db upgrade
```

6. Run the application:
```bash
flask run
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 