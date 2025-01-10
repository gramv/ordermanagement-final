from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField, SubmitField, 
                    TextAreaField, FloatField, DateTimeField)
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, NumberRange
from flask_wtf.file import FileField, FileAllowed
from app.models import User
from datetime import datetime  # Add this import

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class DailySalesForm(FlaskForm):
    report_time = DateTimeField('Report Time', 
        default=datetime.now,
        validators=[DataRequired()])
    
    # Register readings
    front_register_amount = FloatField('Front Register Reading', 
        validators=[DataRequired(), NumberRange(min=0)])
    back_register_amount = FloatField('Back Register Reading', 
        validators=[DataRequired(), NumberRange(min=0)])
    credit_card_amount = FloatField('Credit Card Machine Reading', 
        validators=[DataRequired(), NumberRange(min=0)])
    otc1_amount = FloatField('OTC Machine 1 Reading', 
        validators=[DataRequired(), NumberRange(min=0)])
    otc2_amount = FloatField('OTC Machine 2 Reading', 
        validators=[DataRequired(), NumberRange(min=0)])
    
    # Actual collections
    front_register_cash = FloatField('Front Register Cash', 
        validators=[DataRequired(), NumberRange(min=0)])
    back_register_cash = FloatField('Back Register Cash', 
        validators=[DataRequired(), NumberRange(min=0)])
    credit_card_total = FloatField('Actual Credit Card Total', 
        validators=[DataRequired(), NumberRange(min=0)])
    otc1_total = FloatField('Actual OTC 1 Total', 
        validators=[DataRequired(), NumberRange(min=0)])
    otc2_total = FloatField('Actual OTC 2 Total', 
        validators=[DataRequired(), NumberRange(min=0)])
    
    # Document uploads
    register_reports = FileField('Register Reports', 
        validators=[FileAllowed(['jpg', 'jpeg', 'png', 'pdf'])])
    credit_card_statement = FileField('Credit Card Statement', 
        validators=[FileAllowed(['jpg', 'jpeg', 'png', 'pdf'])])
    otc_statements = FileField('OTC Statements', 
        validators=[FileAllowed(['jpg', 'jpeg', 'png', 'pdf'])])
    
    notes = TextAreaField('Notes')
    submit = SubmitField('Submit Sales Report')