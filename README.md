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
    
## Troubleshooting
- Ensure that `credentials.json` file path is updated to your file path location
  - `credentials.json` file is located in credentials folder
