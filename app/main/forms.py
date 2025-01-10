from flask_wtf import FlaskForm
from wtforms import (StringField, FloatField, SelectField, SubmitField, 
                    BooleanField, IntegerField, HiddenField)
from wtforms.validators import DataRequired, Email, NumberRange, Optional
from flask_wtf.file import FileField, FileAllowed

class ProductForm(FlaskForm):
    # Manual entry fields
    product_id = StringField('Product ID', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    size = StringField('Size')
    cost_price = FloatField('Cost Price', validators=[DataRequired(), NumberRange(min=0)])
    selling_price = FloatField('Selling Price', validators=[DataRequired(), NumberRange(min=0)])
    category = SelectField('Category', coerce=int, validators=[Optional()])
    wholesaler = SelectField('Wholesaler', coerce=int, validators=[DataRequired()])
    available_in_store = BooleanField('Available in Store', default=True)
    
    # Bulk upload field
    bulk_file = FileField('Bulk Upload Excel', 
                         validators=[FileAllowed(['xlsx'], 'Please upload only Excel files!')])
    
    submit = SubmitField('Save Product')

class WholesalerForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    is_daily = BooleanField('Is Daily Wholesaler')
    contact_person = StringField('Contact Person', validators=[Optional()])
    email = StringField('Email', validators=[Optional(), Email()])
    phone = StringField('Phone', validators=[Optional()])
    submit = SubmitField('Submit')

class OrderListItemForm(FlaskForm):
    product = IntegerField('Product', validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    comment = StringField('Comment')

class OrderListForm(FlaskForm):
    product_search = StringField('Product')  # No validator as it's just for UI
    product_id = HiddenField('Product ID', validators=[DataRequired(message="Please select a product from the search results")])
    quantity = IntegerField('Quantity', validators=[
        DataRequired(message="Please enter a quantity"),
        NumberRange(min=1, message="Quantity must be at least 1")
    ])
    submit = SubmitField('Add to Order')

class BulkUploadForm(FlaskForm):
    file = FileField('Excel File', validators=[
        FileAllowed(['xlsx'], 'Please upload only Excel files (.xlsx)'),
        DataRequired()
    ])
    submit = SubmitField('Upload Products')

class CustomerOrderForm(FlaskForm):
    customer_name = StringField('Customer Name', validators=[DataRequired()])
    customer_contact = StringField('Customer Contact', validators=[DataRequired()])
    is_paid = BooleanField('Paid')
    status = SelectField('Status', 
                      choices=[('pending', 'Pending'), ('complete', 'Complete')], 
                      validators=[DataRequired()])
    submit = SubmitField('Update Order')

class CustomerOrderItemForm(FlaskForm):
    product_name = StringField('Product Name', validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired()])
    price = FloatField('Price', validators=[Optional()])
    status = SelectField('Status', 
                      choices=[('pending', 'Pending'), ('complete', 'Complete')], 
                      validators=[DataRequired()])
    submit = SubmitField('Add Item')