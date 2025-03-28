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
       - Username: `tom1`
       - Password: `passw0rd`
    
## Key Features
### Main Page
- Display a line graph of past history of user push-ups record.
- Includes the most recent push-up recording with attempt number, number of pushups, timestamp and the bad form images captured during the attempt.

### Profile Page
- Display the user's name, username, date of birth, weight and height
- Includes a table of past push-up attempts, showing the number of push-ups completed and the timestamp of each attempt.

### Edit Profile Page
- Allows users to edit their name, weight and height through the "Edit Profile" button.

### View Attempt Details Page
- Allow users to view more details in each attempt through the "View Details" button.

    
## Troubleshooting
- Ensure that `credentials.json` file path is updated to your file path location
  - `credentials.json` file is located in credentials folder
