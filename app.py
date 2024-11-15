from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure file uploads
UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database configuration
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="cricket_registration1"
)

# Homepage
@app.route('/')
def home():
    return render_template('home.html')

# Register team
@app.route('/register_team', methods=['GET', 'POST'])
def register_team():
    if request.method == 'POST':
        team_name = request.form['team_name']
        password = generate_password_hash(request.form['password'])
        cursor = db.cursor()
        cursor.execute("INSERT INTO teams (team_name, password) VALUES (%s, %s)", (team_name, password))
        db.commit()
        cursor.close()
        flash('Team registered successfully!')
        return redirect(url_for('login'))
    return render_template('team_register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        team_name = request.form['team_name']
        password = request.form['password']
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM teams WHERE team_name = %s", (team_name,))
        team = cursor.fetchone()
        cursor.close()
        if team and check_password_hash(team['password'], password):
            session['team_id'] = team['id']
            return redirect(url_for('player_register'))
        else:
            flash('Invalid credentials, please try again.')
    return render_template('login.html')

# Player registration
@app.route('/player_register', methods=['GET', 'POST'])
def player_register():
    if 'team_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        role = request.form['role']
        city = request.form['city']
        strike_rate = request.form['strike_rate']
        
        # Handle file upload
        if 'photo' in request.files:
            photo = request.files['photo']
            filename = secure_filename(photo.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(filepath)
        
        # Save player info to the database
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO players (team_id, name, photo, age, role, city, strike_rate) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (session['team_id'], name, filename, age, role, city, strike_rate)
        )
        db.commit()
        cursor.close()
        
        flash('Player registered successfully!')
    
    # Retrieve players for this team to show in the view
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM players WHERE team_id = %s", (session['team_id'],))
    players = cursor.fetchall()
    cursor.close()
    
    return render_template('player_register.html', players=players)

# Logout
@app.route('/logout')
def logout():
    session.pop('team_id', None)
    return redirect(url_for('home'))



if __name__ == '__main__':
    app.run(debug=True)




