from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField, IntegerField, SubmitField, FieldList, FormField
from wtforms.validators import DataRequired, Length

class LoginForm(FlaskForm):
    email = StringField('Email',validators=[DataRequired()])
    password = PasswordField('Password',validators=[DataRequired()])
    submit = SubmitField("Login")

class ResourceForm(FlaskForm):
    r_name = StringField('Resource Name')
    quantity = IntegerField('Resource Quantity')

class AddResourceForm(FlaskForm):
    resources = FieldList(FormField(ResourceForm))
    submit = SubmitField('Add Resource')


class ResourceListForm(FlaskForm):
    resources = FieldList(FormField(ResourceForm), min_entries=1)
    submit = SubmitField('Submit')

class CreateOrgForm(FlaskForm):
    name = StringField('Name',validators=[DataRequired(), Length(min=4, max=64)])
    submit = SubmitField("Create")

class AddMemberForm(FlaskForm):
    email = StringField('email', validators=[DataRequired()])
    submit = SubmitField('add')

class RegForm(FlaskForm):
    email = StringField('Email',validators=[DataRequired(), Length(min=4, max=64)])
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=32)])
    password = PasswordField('Password',validators=[DataRequired(), Length(min=8, max=128)])
    submit = SubmitField("Register")

class EditQuantityForm(FlaskForm):
    qty = IntegerField(validators=[DataRequired()])
    submit = SubmitField('Save')