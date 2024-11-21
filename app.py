from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import mysql.connector
import os
from configparser import ConfigParser

from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure file uploads
UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_config():
    """Reads database configuration from config.ini"""
    config = ConfigParser()
    config.read('config.ini')
    return {
        'host': config['mysql']['host'],
        'user': config['mysql']['user'],
        'password': config['mysql']['password'],
        'database': config['mysql']['database']
    }

def connect_to_database():
    """Connects to the MySQL database using the configuration file"""
    try:
        db_config = get_db_config()
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            return connection
    except mysql.connector.Error as err:
        print(f"Database Connection Error: {err}")
    return None

# Homepage
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register_team', methods=['GET', 'POST'])
def register_team():
    if request.method == 'POST':
        team_name = request.form['team_name']
        password = generate_password_hash(request.form['password'])
        connection = connect_to_database()
        if connection:
            cursor = connection.cursor()
            try:
                query = "INSERT INTO teams (team_name, password) VALUES (%s, %s)"
                cursor.execute(query, (team_name, password))
                connection.commit()
                flash('Team registered successfully!')
                return redirect(url_for('login'))
            except mysql.connector.Error as err:
                flash(f"Error: {err}")
            finally:
                cursor.close()
                connection.close()
    return render_template('team_register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        team_name = request.form['team_name']
        password = request.form['password']
        connection = connect_to_database()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM teams WHERE team_name = %s", (team_name,))
            team = cursor.fetchone()
            cursor.close()
            connection.close()
            if team and check_password_hash(team['password'], password):
                session['team_id'] = team['id']
                return redirect(url_for('player_register'))
            else:
                flash('Invalid credentials, please try again.')
    return render_template('login.html')


@app.route('/player_register', methods=['GET', 'POST'])
def player_register():
    if 'team_id' not in session:
        return redirect(url_for('login'))

    connection = connect_to_database()
    if connection:
        cursor = connection.cursor(dictionary=True)
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            age = request.form['age']
            role = request.form['role']
            city = request.form['city']
            strike_rate = request.form['strike_rate']
            is_captain = 'is_captain' in request.form
            photo = request.files['photo']

            # Handle file upload
            if photo and photo.filename != '':
                filename = secure_filename(photo.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                photo.save(filepath)
            else:
                filename = None

            # Save player info to the database
            try:
                query = """
                    INSERT INTO players 
                    (team_id, name, email, photo, age, role, city, strike_rate, is_captain) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (
                    session['team_id'], name, email, filename, age, role, city, strike_rate, is_captain
                ))
                connection.commit()
                flash('Player registered successfully!')
            except mysql.connector.Error as err:
                flash(f"Database Error: {err}")

        # Retrieve players for this team
        cursor.execute("SELECT * FROM players WHERE team_id = %s", (session['team_id'],))
        players = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('player_register.html', players=players)
    else:
        flash("Database connection failed.")
        return redirect(url_for('login'))




@app.route('/available_teams')
def available_teams():
    # Retrieve available teams with 5 or more players
    teams = get_available_teams()
    return render_template('available_teams.html', teams=teams)

def get_available_teams():
    connection = connect_to_database()
    if connection:
        cursor = connection.cursor(dictionary=True)
        try:
            # Fetch teams with 5 or more players
            cursor.execute("""
                SELECT t.id, t.team_name
                FROM teams t
                JOIN players p ON p.team_id = t.id
                GROUP BY t.id, t.team_name
                HAVING COUNT(p.id) >= 5
            """)
            teams = cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Database Error: {err}")
            teams = []
        finally:
            cursor.close()
            connection.close()
        return teams
    else:
        return []


# Logout
@app.route('/logout')
def logout():
    session.pop('team_id', None)
    return redirect(url_for('home'))




@app.route('/process_selection', methods=['POST'])
def process_selection():
    if request.method == 'POST':
        match_date = request.form['match_date']
        match_time = request.form['match_time']
        match_location = request.form['match_location']
        team_id = request.form['team']
        overs = request.form['overs']

        # Get the team and players from the database
        connection = connect_to_database()
        cursor = connection.cursor(dictionary=True)
        
        # Get team name
        cursor.execute("SELECT team_name FROM teams WHERE id = %s", (team_id,))
        team = cursor.fetchone()

        # Get all players of the selected team
        cursor.execute("SELECT name, email FROM players WHERE team_id = %s", (team_id,))
        players = cursor.fetchall()

        # Prepare the email content
        subject = f"Match Details: {team['team_name']} vs Opponent"
        body = f"Match Date: {match_date}\nMatch Time: {match_time}\nLocation: {match_location}\nOvers: {overs}"

        # Send email to each player
        try:
            for player in players:
                send_email(player['email'], subject, body)
            flash('Match details sent to all players successfully!')
        except Exception as e:
            flash(f"Error sending email: {e}")
        
        cursor.close()
        connection.close()
        return redirect(url_for('available_teams'))

# Function to send email
def send_email(to_email, subject, body):
    from_email = "youremail@example.com"
    from_password = "yourpassword"
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

@app.route('/matchstats')
def matchstats():
    return render_template('match_stats.html')

if __name__ == '__main__':
    app.run(debug=True)