from flask import Flask, render_template, redirect, url_for, request, session, flash
import firebase_admin
from firebase_admin import credentials, firestore
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateField
from wtforms.validators import DataRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# Initialize Firebase
cred = credentials.Certificate("C:/Users/brend/Desktop/IN2009_T2/credentials/credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=50)])
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    date_of_birth = DateField('Date of Birth', format='%Y-%m-%d', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

@app.route('/')
def home():
    if 'username' not in session:  # Check if user is logged in
        return redirect(url_for('login'))  # Redirect to login if not logged in
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user_ref = db.collection('users').document(form.username.data)
        user = user_ref.get()
        if user.exists:
            flash("Username already exists. Choose another.", "danger")
        else:
            hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
            user_ref.set({
                'name': form.name.data,
                'username': form.username.data,
                'date_of_birth': form.date_of_birth.data.strftime('%Y-%m-%d'),
                'password': hashed_password
            })
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user_ref = db.collection('users').document(form.username.data).get()
        if user_ref.exists:
            user_data = user_ref.to_dict()
            if check_password_hash(user_data['password'], form.password.data):
                session['username'] = user_data['username']
                flash("Login successful!", "success")
                return redirect(url_for('home'))
            else:
                flash("Invalid password. Try again.", "danger")
        else:
            flash("User not found. Please register.", "danger")
    return render_template('login.html', form=form)

@app.route('/profile')
def profile():
    if 'username' in session:
        return render_template('profile.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
