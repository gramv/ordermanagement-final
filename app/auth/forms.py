from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from app.models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message='Please enter your username'),
        Length(min=3, max=64, message='Username must be between 3 and 64 characters')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Please enter your password')
    ])
    remember_me = BooleanField('Remember Me')

    def validate_username(self, field):
        # Remove leading/trailing whitespace and convert to lowercase
        field.data = field.data.strip().lower()

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=64, message='Username must be between 3 and 64 characters')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=6, message='Password must be at least 6 characters long')
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password'),
        EqualTo('password', message='Passwords must match')
    ])

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data.lower().strip()).first()
        if user:
            raise ValidationError('Username already taken. Please choose another.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data.lower().strip()).first()
        if user:
            raise ValidationError('Email already registered. Please use another.')