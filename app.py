import os
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, text
from flask import Flask, render_template, request, redirect, url_for, make_response, session
from functools import wraps

app = Flask(__name__)

load_dotenv()
app.secret_key = os.urandom(24)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ["CONNECTION_STRING"]
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
db = SQLAlchemy(app)

def nocache(view):
    @wraps(view)
    def no_cache_view(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    return no_cache_view

@nocache
@app.route('/')
def home_page():
    if "username" in session:
        return render_template('dashboard.html', session=session)
    else:
        return redirect(url_for('login'))

@app.route('/admin', methods=['POST', 'GET'])
def admin_page():
    if "admin_username" in session:
        return render_template('admin_dashboard.html', session=session)
    else:
        if "username" in session:
            return redirect(url_for('home_page'))
        else:
            return redirect(url_for('login', message="You are not authorized to access this page."))

@nocache
@app.route('/login', methods=['POST', 'GET'])
def login():
    if "username" in session:
        return redirect(url_for('home_page'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with engine.connect() as connection:
            #Check if the user is an admin or not
            check_admin_query = text("SELECT * FROM admin WHERE BINARY admin_name = :admin_name AND admin_password = :admin_password")
            check_admin_result = connection.execute(check_admin_query, {
                "admin_name": username,
                "admin_password": password
                }).fetchone()
            if check_admin_result is not None:
                session['admin_id'] = check_admin_result[0]
                session['admin_username'] = username
                session['admin_password'] = password
                return redirect(url_for('admin_page'))
            # Check if the user exists or not
            check_query = text("SELECT * FROM user WHERE BINARY username = :username AND password = :password")
            check_result = connection.execute(check_query, {
                "username": username,
                "password": password
                }).fetchone()
            if check_result is not None:
                session['user_id'] = check_result[0]
                session['username'] = username
                session['password'] = password
                return redirect(url_for('home_page'))
            else:
                # User does not exist
                return render_template('login_page.html', error="Invalid credentials. Please try again.")
    
    message = request.args.get('message')
    if message:
        return render_template('login_page.html', error=message)
    else:
        return render_template('login_page.html')

@nocache
@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Check if the user exists or not
        check_query = text("SELECT username FROM user WHERE BINARY username = :username")
        with engine.connect() as connection:
            check_result = connection.execute(check_query, {
                "username": username
                }).fetchone()
            if check_result is None:
                # Insert the new user into the database
                insert_query = text("INSERT INTO user (username, password) VALUES (:username, :password)")
                connection.execute(insert_query, {
                    "username": username,
                    "password": password
                })
                connection.commit()
                return redirect(url_for('login'))
            else:
                # User already exists
                return render_template('register_page.html', error="User already exists. Make sure your username is unique.")
            
    return render_template('register_page.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)