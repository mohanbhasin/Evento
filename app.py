import os
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, text
from flask import Flask, render_template, request, redirect, url_for, make_response, session
from functools import wraps
from datetime import datetime, timedelta

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

def get_prev_day():
    today = datetime.now()
    prev_day = today - timedelta(days=1)
    return prev_day.strftime('%Y-%m-%d')

@nocache
@app.route('/')
def home_page():
    if "username" in session or "admin_username" in session:
        with engine.connect() as connection:
            events_query = text("SELECT event_id FROM event;")
            society_query = text("SELECT society_id FROM society;")
            society_result = connection.execute(society_query)
            events_result = connection.execute(events_query)
            number_of_events = len(events_result.fetchall())
            number_of_societies = len(society_result.fetchall())
            upcoming_events_query = text("SELECT * FROM event WHERE date >= :prev_day ORDER BY date ASC;")
            prev_day = get_prev_day()
            upcoming_events_result = connection.execute(upcoming_events_query, {"prev_day": prev_day})
            upcoming_events = len(upcoming_events_result.fetchall())

            events_list = []
            all_events_query = text("SELECT name, society, date, venue FROM event WHERE date >= :prev_day ORDER BY date ASC;")
            all_events_query_result = connection.execute(all_events_query, {"prev_day": prev_day})
            for row in all_events_query_result:
                event = {
                    "name": row[0],
                    "society": row[1],
                    "date": row[2],
                    "venue": row[3]
                }
                events_list.append(event)
            
            past_events = []
            past_events_query = text("SELECT name, society, date, venue FROM event WHERE date < :prev_day ORDER BY date DESC;")
            past_events_query_result = connection.execute(past_events_query, {"prev_day": prev_day})
            for row in past_events_query_result:
                event = {
                    "name": row[0],
                    "society": row[1],
                    "date": row[2],
                    "venue": row[3]
                }
                past_events.append(event)

        return render_template('dashboard.html', session=session, events=number_of_events, 
                               societies=number_of_societies, upcoming_events=upcoming_events, events_list=events_list, past_events=past_events)
    else:
        return redirect(url_for('login'))

@nocache
@app.route('/admin', methods=['POST', 'GET'])
def admin_page():
    if request.method == 'POST':
        with engine.connect() as connection:
            if "block1" in request.form:
                title = request.form['eventTitle']
                society = request.form['society']
                date = request.form['eventDateTime']
                venue = request.form['venue']
                description = request.form['description']
                eventBanner = request.form['eventBanner']
                insert_query = text("INSERT INTO event(name, society, date, venue, description, image_path) VALUES(UPPER(:name), UPPER(:society), :date, :venue, :description, :image_path);")
                connection.execute(insert_query, {
                    "name": title,
                    "society": society,
                    "date": date,
                    "venue": venue,
                    "description": description,
                    "image_path": eventBanner
                })
                connection.commit()
            
            else:
                name = request.form['societyName']
                head = request.form['societyHead']
                category = request.form['category']
                insert_query = text("INSERT INTO society(name, society_head, category) VALUES(:name, :head, :category);")
                connection.execute(insert_query, {
                    "name": name,
                    "head": head,
                    "category": category
                })
                connection.commit()

    if "admin_username" in session:
        societies = []
        with engine.connect() as connection:
            query = text("SELECT name from society")
            result = connection.execute(query)
            societies = [row[0] for row in result]


        return render_template('admin_dashboard.html', session=session, societies=societies)
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