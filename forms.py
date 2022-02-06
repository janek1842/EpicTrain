from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, validators, FileField, SelectField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Email, ValidationError
from models import User


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[
        validators.DataRequired(message="Please Fill This Field"),
        validators.EqualTo(fieldname="confirm", message="Your Passwords Do Not Match")
    ])
    confirm = PasswordField("Confirm Password", validators=[validators.DataRequired(message="Please Fill This Field")])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('A user with this username already exists')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('A user with this email address already exists')


class AccountForm(FlaskForm):
    username = StringField('Username')
    email = StringField('Email')
    discount = SelectField('Discount', choices=[
        ('0', 'Brak zniżki (0%)'),
        ('37', 'Uczniowie (37%)'),
        ('51', 'Studenci (51%)')
    ], validate_choice=True)
    avatar = FileField('Avatar')
    submit = SubmitField('Save')
    description = TextAreaField('Description')


class OpinionForm(FlaskForm):
    opinion = TextAreaField('Opinion')
    rate = IntegerField('Rate', validators=[
                validators.NumberRange(min=0, max=5)
            ])
    submit = SubmitField("Submit")