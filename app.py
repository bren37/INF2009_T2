from flask import Flask, render_template, redirect, url_for, request, session, flash
import firebase_admin
from firebase_admin import credentials, firestore
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateField, IntegerField
from wtforms.validators import DataRequired, Length
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# Initialize Firebase
cred = credentials.Certificate("C:/Users/Brendan/Desktop/INF2009_T2/credentials/credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=50)])
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    date_of_birth = DateField('Date of Birth', format='%Y-%m-%d', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    height = StringField('Height (M)', validators=[DataRequired(), Length(min=2, max=4)])
    weight = StringField('weight (Kg)', validators=[DataRequired(), Length(min=2, max=4)])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

def calculate_age(born):
    today = datetime.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

@app.route('/')
def home():
     if 'username' not in session:  # Check if user is logged in
         return redirect(url_for('login'))  # Redirect to login if not logged in
     return redirect(url_for('main_home'))


@app.route('/home')
def main_home():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Fetch user data from Firestore
    username = session['username']
    user_ref = db.collection('users').document(username).get()
    if not user_ref.exists:
        flash("User data not found.", "danger")
        return redirect(url_for('main_home'))

    user_data = user_ref.to_dict()

    recordings_ref = db.collection('recording').where('username', '==', username).stream()
    recordings = []
    for recording in recordings_ref:
        recordings.append(recording.to_dict())

    # Sort recordings by attempt number (ascending order)
    recordings.sort(key=lambda x: x['attempt'])

    # Prepare data for the chart
    labels = [f"Attempt {recording['attempt']}" for recording in recordings]
    data = [recording['no_of_reps'] for recording in recordings]  # Number of pushups

    # Fetch the most recent recording
    most_recent_recording_ref = db.collection('recording').where('username', '==', username).order_by('timestamp',direction=firestore.Query.DESCENDING).limit(1).stream()
    most_recent_recording = None
    for recording in most_recent_recording_ref:
        most_recent_recording = recording.to_dict()
        if 'bad_form_img' not in most_recent_recording:
            most_recent_recording['bad_form_img'] = []

    # Pass user data, chart data, and most recent recording to the template
    return render_template('home.html', 
                          name=user_data['name'], 
                          username=user_data['username'], 
                          labels=labels, 
                          data=data, 
                          most_recent_recording=most_recent_recording)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user_ref = db.collection('users').document(form.username.data)
        user = user_ref.get()
        if user.exists:
            flash("Username already exists. Choose another.", "danger")
        else:
            age = calculate_age(form.date_of_birth.data)
            hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
            user_ref.set({
                'name': form.name.data,
                'username': form.username.data,
                'date_of_birth': form.date_of_birth.data.strftime('%Y-%m-%d'),
                'height': form.height.data,
                'weight': form.weight.data,
                'password': hashed_password,
                'age': age
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
                return redirect(url_for('main_home'))
            else:
                flash("Invalid password. Try again.", "danger")
        else:
            flash("User not found. Please register.", "danger")
    return render_template('login.html', form=form)

@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Fetch user data from Firestore
    username = session['username']
    user_ref = db.collection('users').document(username).get()
    if not user_ref.exists:
        flash("User data not found.", "danger")
        return redirect(url_for('home'))

    user_data = user_ref.to_dict()

    # Fetch user's pushup recordings from Firestore
    recordings_ref = db.collection('recording').where('username', '==', username).stream()
    recordings = []
    for recording in recordings_ref:
        recordings.append(recording.to_dict())

    # Sort recordings by attempt number (ascending order)
    recordings.sort(key=lambda x: x['attempt'])

    # Pass user data and recordings to the template
    return render_template('profile.html', 
                          name=user_data['name'], 
                          username=user_data['username'], 
                          date_of_birth=user_data['date_of_birth'],
                          age =user_data['age'],
                          weight =user_data['weight'],
                          height =user_data['height'],
                          recordings=recordings)

@app.route('/update_profile', methods=['GET', 'POST'])
def update_profile():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user_ref = db.collection('users').document(username)
    user_data = user_ref.get().to_dict()

    if request.method == 'POST':
        # Update user data in Firestore
        user_ref.update({
            'name': request.form['name'],
            'weight': float(request.form['weight']),
            'height': float(request.form['height'])
        })
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    # Pre-fill the form with current user data
    return render_template('update_profile.html', 
                           name=user_data['name'], 
                           weight=user_data['weight'], 
                           height=user_data['height'])

@app.route('/view_recording_details/<int:attempt>')
def view_recording_details(attempt):
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']

    print(f"Fetching recording for username: {username}, attempt: {attempt}")

    attempt_str = str(attempt)

    # Fetch the specific recording based on the attempt number
    recording_ref = db.collection('recording').where('username', '==', username).where('attempt', '==', attempt_str).stream()

    

    recording = None
    for rec in recording_ref:
        recording = rec.to_dict()

    if not recording:
        flash("Recording not found.", "danger")
        return redirect(url_for('profile'))

    return render_template('recording_details.html', recording=recording)

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
