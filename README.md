# INF2009_T2 Project

## Set up Virtual Environment
1. `python -m venv venv`
2. `venv\Scripts\activate`

## Libraries used
1. Flask
2. Flask-WTF
3. firebase_admin
4. Werkzeug

## Install Libraries
1. `pip install -r requirements.txt`

## Running the Application
1. Ensure virtual environment is activated
   - `venv\Scripts\activate`
2. run `py app.py` to start the application
3. Navigate to `http://127.0.0.1:5000` in browser
   - test account:
       - Username: `testing`
       - Password: `testing`
    
## Key Features
### Main Page
- **Pushup History Chart**: Display a line graph of past history of user push-ups record.
- **Latest Attempt Summary**: Includes the most recent push-up recording with attempt number, number of pushups, timestamp and the bad form images captured during the attempt.

### Profile Page
- **User Information Overview**: Display the user's name, username, date of birth, weight and height
- **Attempt History Table**: Includes a table of past push-up attempts, showing the number of push-ups completed and the timestamp of each attempt.

### Edit Profile Page
- **User Details Update**: Allows users to edit their name, weight and height through the "Edit Profile" button.

### View Attempt Details Page
- **Detailed Attempt Insights**: Allow users to view more details in each attempt through the "View Details" button.

### ML-Powered Pushup Progress Tracker
- **Machine Learning Model**: Utilizes a trained regression model to forecast how the user's push-up count will improve over time.
- **Goal Setting**: Takes into account the user's entered push-up goal, personal data (weight, age, etc.), and historical attempt records.
- **Interactive Predictions**: Generates a chart predicting daily progress toward their goal, providing an estimated timeline and intermediate milestones.
- **Seamless Integration**: The prediction is automatically displayed under the “Push-up Prediction” section on the Home page once the user is logged in and have completed at least one push-up attempt.
    
## Troubleshooting
- Ensure that `credentials.json` file path is updated to your file path location
  - `credentials.json` file is located in credentials folder
