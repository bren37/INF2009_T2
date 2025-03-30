from dateutil import parser
from flask import Flask, render_template, redirect, url_for, request, session, flash, request, jsonify
import joblib
import firebase_admin
import pandas as pd
from firebase_admin import credentials, firestore
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateField, IntegerField
from wtforms.validators import DataRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import base64

app = Flask(__name__)
app.config['SECRET_KEY'] = '9wrjq9w8ruWqrfF'

# Initialize Firebase
cred = credentials.Certificate("credentials/credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Load the trained model and scaler when the Flask app starts
model_filename = 'pushup_rate_prediction_model.joblib'
loaded_model = joblib.load(model_filename)

scaler_filename = 'pushup_rate_scaler.joblib'
loaded_scaler = joblib.load(scaler_filename)

# Define the feature names used during training
features_rate = ['weight', 'age', 'gender', 'pushups', 'frequency', 'cumulative_pushups', 'time_elapsed']

class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=50)])
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    date_of_birth = DateField('Date of Birth', format='%Y-%m-%d', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    height = StringField('Height (M)', validators=[DataRequired(), Length(min=2, max=4)])
    weight = StringField('weight (Kg)', validators=[DataRequired(), Length(min=2, max=4)])
    pushup_goal = IntegerField('Push-up Goal', validators=[DataRequired()])
    frequency = IntegerField('Frequency', validators=[DataRequired()])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

def calculate_age(born):
    today = datetime.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def format_timestamp_to_iso(timestamp_str):
    """
    Convert "25 March 2025 at 19:07:31 UTC+8" to "2025-03-25"
    """
    try:
        # Parse the original timestamp
        dt = parser.parse(timestamp_str)
        # Format to YYYY-MM-DD
        return dt.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Error formatting timestamp {timestamp_str}: {e}")
        return None

def predict_progress(user_profile, past_records):
    try:
        goal_reps = int(user_profile['pushup_goal'])
        current_weight = float(user_profile['weight'])
        current_age = int(user_profile['age'])
        current_gender_str = user_profile.get('gender', 'Unknown') # Handle potential missing gender
        frequency = int(user_profile.get('frequency', 1)) # Handle potential missing frequency
    except (ValueError, TypeError) as e:
        return None, f"Error: Invalid user profile data: {e}"

    gender_encoded = 0 if current_gender_str.lower() == 'male' else 1

    progress_data = []
    if not past_records:
        current_reps = 1
        cumulative_reps = 0
        time_elapsed = 0
        start_date = datetime.now(timezone(timedelta(hours=8))).date() # Use Singapore time
        progress_data.append({'date': start_date, 'pushups': current_reps})
    else:
        past_df = pd.DataFrame(past_records)
        past_df['no_of_reps'] = pd.to_numeric(past_df['total_pushups'], errors='coerce').fillna(0).astype(int)
        past_df['timestamp'] = pd.to_datetime(past_df['timestamp'], errors='coerce')
        past_df = past_df.dropna(subset=['timestamp', 'no_of_reps'])
        past_df = past_df.sort_values(by='timestamp')
        if not past_df.empty:
            current_reps = past_df.iloc[-1]['no_of_reps']
            start_time = past_df.iloc[0]['timestamp'].to_pydatetime().date()
            latest_time = past_df.iloc[-1]['timestamp'].to_pydatetime().date()
            time_elapsed = (latest_time - start_time).days if (latest_time - start_time).days >= 0 else 0
            cumulative_reps = past_df['no_of_reps'].sum()
            for index, row in past_df.iterrows():
                progress_data.append({'date': row['timestamp'].to_pydatetime().date(), 'pushups': row['no_of_reps']})
        else:
            current_reps = 1
            cumulative_reps = 0
            time_elapsed = 0
            start_date = datetime.now(timezone(timedelta(hours=8))).date() # Use Singapore time
            progress_data.append({'date': start_date, 'pushups': current_reps})

    days = 0
    predicted_pushups = current_reps
    all_progress = progress_data[:]

    while predicted_pushups < goal_reps:
        input_data = [[current_weight, current_age, gender_encoded, predicted_pushups, frequency, cumulative_reps, time_elapsed]]
        input_df = pd.DataFrame(input_data, columns=features_rate)
        input_features_scaled = loaded_scaler.transform(input_df)
        predicted_rate = loaded_model.predict(input_features_scaled)[0]

        if predicted_rate <= 0:
            return all_progress, "Prediction stalled: No progress expected."

        reps_to_goal = goal_reps - predicted_pushups
        reps_increment = min(1, reps_to_goal)
        estimated_days = reps_increment / predicted_rate
        days += estimated_days
        time_elapsed += estimated_days
        predicted_pushups += reps_increment
        predicted_date = progress_data[-1]['date'] + timedelta(days=round(time_elapsed)) # Estimate date
        all_progress.append({'date': predicted_date, 'pushups': predicted_pushups})

        if time_elapsed > 365 * 5:
            return all_progress, "Prediction taking too long, goal might be unrealistic."

    return all_progress, None

def create_progress_graph(progress_data, goal):
    if not progress_data:
        return None

    # Use day numbers instead of actual dates
    days = list(range(1, len(progress_data) + 1))
    pushups = [item['pushups'] for item in progress_data]

    plt.figure(figsize=(12, 6))
    plt.plot(days, pushups, marker='o', linestyle='-', color='blue', label='Predicted Progress')
    plt.axhline(y=goal, color='r', linestyle='--', label=f'Goal: {goal} Pushups')

    # Annotate the last predicted point with the total number of days
    if progress_data:
        last_point = progress_data[-1]
        total_days = len(progress_data)
        plt.annotate(f"End: Day {total_days}, {last_point['pushups']} reps",
                     xy=(total_days, last_point['pushups']),
                     xytext=(10, -15), textcoords='offset points',
                     arrowprops=dict(facecolor='black', shrink=0.05))

    plt.xlabel('Day')
    plt.ylabel('Number of Pushups')
    plt.title('Predicted Pushup Progress')
    plt.legend()
    plt.grid(True)
    plt.xticks(days)  # Ensure all day numbers are displayed on the x-axis
    plt.tight_layout()

    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()
    plot_url = base64.b64encode(img.getvalue()).decode('utf8')
    return plot_url

@app.route('/predict')
def predict():
    if 'username' not in session:
        flash("Please log in to get a prediction.", "warning")
        return redirect(url_for('login'))

    username = session['username']

    # Fetch user profile from Firestore
    user_ref = db.collection('users').document(username).get()
    if not user_ref.exists:
        flash("User profile not found.", "danger")
        return redirect(url_for('main_home'))
    user_profile_from_db = user_ref.to_dict()

    # Fetch past records from Firestore
    recordings_ref = db.collection('sessions').where('username', '==', username).order_by('timestamp').stream()
    sessions = []  # Array to store session data

    for recording in recordings_ref:
        recording_data = recording.to_dict()
        
        if 'stats' in recording_data and 'timestamp' in recording_data['stats']:
            total_pushups = recording_data['stats'].get('total_pushups', 0)
            raw_timestamp = recording_data['stats'].get('timestamp')  # Take the timestamp from nested stats
            
            # Handle both UNIX timestamps and string timestamps
            if isinstance(raw_timestamp, (int, float)):
                formatted_timestamp = datetime.utcfromtimestamp(raw_timestamp).strftime("%Y-%m-%d")
            elif isinstance(raw_timestamp, str):
                try:
                    formatted_timestamp = datetime.strptime(raw_timestamp, "%d %B %Y at %H:%M:%S UTC%z").strftime("%Y-%m-%d")
                except ValueError:
                    print(f"Warning: Timestamp format issue in recording {recording.id}")
                    formatted_timestamp = "Unknown"
            else:
                formatted_timestamp = "Unknown"
            
            session_entry = {
                "timestamp": formatted_timestamp,
                "username": username,
                "total_pushups": total_pushups
                
            }
            sessions.append(session_entry)
        else:
            print(f"Warning: Recording missing required fields: {recording.id}")

    # Print sessions array to verify
    print(sessions)
    print(username)

    progress_data, error_message = predict_progress(user_profile_from_db, sessions)
    goal = int(user_profile_from_db.get('pushup_goal', 0))

    if error_message:
        return render_template('prediction.html', error=error_message)
    elif progress_data:
        plot_url = create_progress_graph(progress_data, goal)
        return plot_url
    else:
        return render_template('prediction.html', error="Could not generate prediction.")




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

    # Fetch all sessions for the user
    sessions_query = db.collection('sessions').where('username', '==', username).stream()
    user_sessions = []
    for session_doc in sessions_query:
        session_data = session_doc.to_dict()
        if 'stats' in session_data and 'total_pushups' in session_data['stats']:
            user_sessions.append(session_data)

    # Sort sessions by timestamp (ascending order)
    user_sessions.sort(key=lambda x: x['timestamp'])

    # Prepare data for the chart
    labels = []
    data = []
    
    # For each session, get the total_pushups from stats and create a label
    for i, session_data in enumerate(user_sessions):
        session_id = session_data['session_id']
        
        # Get the attempt number from wrong_forms table for this session
        wrong_forms_ref = db.collection('wrong_forms').where('session_id', '==', session_id).stream()
        attempt_numbers = []
        for wrong_form in wrong_forms_ref:
            wrong_form_data = wrong_form.to_dict()
            if 'attempt_number' in wrong_form_data:
                attempt_numbers.append(int(wrong_form_data['attempt_number']))
        
        # Use the highest attempt number if available, otherwise use index
        attempt_number = max(attempt_numbers) if attempt_numbers else i + 1
        
        labels.append(f"Attempt {attempt_number}")
        data.append(session_data['stats'].get('total_pushups', 0))

    # Fetch the most recent session and its wrong forms
    most_recent_session_ref = db.collection('sessions').where('username', '==', username)\
                                .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                                .limit(1).stream()
    
    most_recent_session = None
    wrong_forms = []
    attempt_numbers = []  # To store all attempt numbers for this session

    for recent_session in most_recent_session_ref:
        most_recent_session = recent_session.to_dict()
        session_id = most_recent_session['session_id']
        
        # Get wrong forms for this session
        wrong_forms_ref = db.collection('wrong_forms').where('session_id', '==', session_id).stream()
        for wrong_form in wrong_forms_ref:
            wrong_form_data = wrong_form.to_dict()
            wrong_forms.append(wrong_form_data)
            if 'attempt_number' in wrong_form_data:
                attempt_numbers.append(int(wrong_form_data['attempt_number']))
        
        # Set the attempt number for the session (highest from wrong_forms or default to 1)
        most_recent_session['attempt_number'] = max(attempt_numbers) if attempt_numbers else 1
    
    prediction = predict()

    return render_template('home.html', 
                        name=user_data['name'], 
                        username=user_data['username'], 
                        labels=labels, 
                        data=data, 
                        most_recent_session=most_recent_session,
                        wrong_forms=wrong_forms,
                        prediction=prediction)
                          

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
                'age': age,
                'pushup_goal': form.pushup_goal.data,
                'frequency': form.frequency.data
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

    # Fetch user data from Firestore users collection
    username = session['username']
    user_ref = db.collection('users').document(username).get()
    if not user_ref.exists:
        flash("User data not found.", "danger")
        return redirect(url_for('home'))

    user_data = user_ref.to_dict()

    # Fetch user's sessions from sessions collection
    sessions_ref = db.collection('sessions').where('username', '==', username).stream()
    sessions = []
    for session_doc in sessions_ref:
        session_data = session_doc.to_dict()
        if 'stats' in session_data:  # Ensure session has stats
            sessions.append(session_data)

    # Sort sessions by timestamp (newest first)
    sessions.sort(key=lambda x: x['timestamp'], reverse=True)

    # Fetch wrong forms for attempt numbers
    wrong_forms_ref = db.collection('wrong_forms').where('username', '==', username).stream()
    wrong_forms = [wrong_form.to_dict() for wrong_form in wrong_forms_ref]

    # Combine session data with attempt numbers from wrong_forms
    session_attempts = []
    for user_session in sessions:
        session_id = user_session['session_id']
        # Find matching wrong forms for this session
        matching_forms = [wf for wf in wrong_forms if wf.get('session_id') == session_id]
        # Get highest attempt number or default to 1
        attempt_numbers = [int(wf['attempt_number']) for wf in matching_forms if 'attempt_number' in wf]
        attempt_number = max(attempt_numbers) if attempt_numbers else 1
        
        session_attempts.append({
            'session_id': session_id,
            'attempt_number': attempt_number,
            'total_pushups': user_session['stats']['total_pushups'],
            'timestamp': user_session['timestamp'],
            'success_rate': user_session['stats']['success_rate'],
            'session_duration': user_session['stats']['session_duration']
        })

    return render_template('profile.html', 
                        name=user_data['name'], 
                        username=user_data['username'], 
                        date_of_birth=user_data['date_of_birth'],
                        age=user_data['age'],
                        weight=user_data['weight'],
                        height=user_data['height'],
                        pushup_goal=user_data['pushup_goal'],
                        frequency=user_data['frequency'],
                        session_attempts=session_attempts)


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
            'height': float(request.form['height']),
            'pushup_goal': int(request.form['pushup_goal']),
            'frequency': int(request.form['frequency'])
        })
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    # Pre-fill the form with current user dataE
    return render_template('update_profile.html', 
                           name=user_data['name'], 
                           weight=user_data['weight'], 
                           height=user_data['height'],
                           goal=user_data['pushup_goal'],
                           frequency=user_data['frequency']
                           )

@app.route('/view_recording_details/<string:session_id>')
def view_recording_details(session_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']

    # Fetch the session data
    session_ref = db.collection('sessions').where('username', '==', username)\
                                          .where('session_id', '==', session_id)\
                                          .limit(1).stream()
    
    session_data = None
    for attempt_session in session_ref:
        session_data = attempt_session.to_dict()

    if not session_data:
        flash("Session not found.", "danger")
        return redirect(url_for('profile'))

    # Fetch wrong forms for this session
    wrong_forms_ref = db.collection('wrong_forms').where('session_id', '==', session_id).stream()
    wrong_forms = [wf.to_dict() for wf in wrong_forms_ref]
    
    # Get the highest attempt number
    attempt_numbers = [int(wf['attempt_number']) for wf in wrong_forms if 'attempt_number' in wf]
    attempt_number = max(attempt_numbers) if attempt_numbers else 1

    # Prepare form issues with images
    form_issues = []
    for wf in wrong_forms:
        if 'form_issue' in wf:
            issue = {
                'description': wf['form_issue'],
                'attempt_number': wf.get('attempt_number', 'N/A'),
                'image': wf.get('image')
            }
            form_issues.append(issue)

    return render_template('recording_details.html', 
                         session=session_data,
                         attempt_number=attempt_number,
                         form_issues=form_issues)

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
