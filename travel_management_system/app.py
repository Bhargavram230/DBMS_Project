from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_strong_secret_key_here'

# Database configuration
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="qazplm230",
    database="travel_management"
)
cursor = db.cursor()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, hashed_password))
            db.commit()
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f'Error: {err}')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash('Login successful!')
            return redirect(url_for('packages'))
        flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.')
    return redirect(url_for('home'))

@app.route('/packages')
def packages():
    if 'user_id' not in session:
        flash('Login required.')
        return redirect(url_for('login'))
    cursor.execute("SELECT package_id, package_name, destination, price, duration, image_url FROM tourpackages")
    packages = cursor.fetchall()
    return render_template('packages.html', packages=packages)

@app.route('/select_travel_mode/<int:package_id>', methods=['GET', 'POST'])
def select_travel_mode(package_id):
    if request.method == 'POST':
        travel_mode = request.form.get('travel_mode')
        session['selected_package_id'] = package_id
        session['selected_travel_mode'] = travel_mode
        session.modified = True  
        if travel_mode == 'flight':
            return redirect(url_for('flights', package_id=package_id))
        elif travel_mode == 'bus':
            return redirect(url_for('travel_options', package_id=package_id))
        else:
            flash("Invalid travel mode selected.")
            return redirect(url_for('select_travel_mode', package_id=package_id))
    return render_template('select_travel_mode.html', package_id=package_id)

@app.route('/flights/<int:package_id>')
def flights(package_id):
    if 'user_id' not in session:
        flash('Login required.')
        return redirect(url_for('login'))
    
    cursor.execute("SELECT destination FROM tourpackages WHERE package_id = %s", (package_id,))
    result = cursor.fetchone()
    
    if not result:
        flash("Invalid package ID.")
        return redirect(url_for('packages'))
    
    destination = result[0]
    
    # Updated query to avoid case sensitivity and trimming issues
    cursor.execute("""
        SELECT flight_id, flight_name, source, destination, departure_time, arrival_time, price 
        FROM flights 
        WHERE TRIM(LOWER(destination)) = TRIM(LOWER(%s))
    """, (destination,))
    flights = cursor.fetchall()
    
    return render_template('flights.html', flights=flights, destination=destination)

@app.route('/travel_options/<int:package_id>')
def travel_options(package_id):
    if 'user_id' not in session:
        flash('Login required.')
        return redirect(url_for('login'))
    
    travel_mode = session.get('selected_travel_mode')
    if travel_mode not in ['flight', 'bus']:
        flash(f"Invalid travel mode: {travel_mode}")
        return redirect(url_for('packages'))
    
    cursor.execute("SELECT destination FROM tourpackages WHERE package_id = %s", (package_id,))
    result = cursor.fetchone()
    
    if not result:
        flash("Invalid package ID.")
        return redirect(url_for('packages'))
    
    destination = result[0]
    if travel_mode == 'bus':
        cursor.execute("SELECT bus_id, bus_name, departure_time, arrival_time, price FROM buses WHERE destination = %s", (destination,))
        travel_options = cursor.fetchall()
        return render_template('travel_options.html', travel_options=travel_options, travel_mode=travel_mode)
    
    flash(f"Invalid travel mode: {travel_mode}")
    return redirect(url_for('packages'))

@app.route('/book_travel_option/<int:travel_id>', methods=['POST'])
def book_travel_option(travel_id):
    if 'user_id' not in session:
        flash('Login required.')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    package_id = session.get('selected_package_id')
    travel_mode = session.get('selected_travel_mode')
    
    if travel_mode not in ['flight', 'bus']:
        flash("Invalid travel mode.")
        return redirect(url_for('packages'))
    
    table = 'flights' if travel_mode == 'flight' else 'buses'
    try:
        cursor.execute(f"INSERT INTO bookings (user_id, package_id, {table}_id, booking_date) VALUES (%s, %s, %s, NOW())", (user_id, package_id, travel_id))
        db.commit()
        flash('Booking successful!')
        return redirect(url_for('payment'))
    except mysql.connector.Error as err:
        flash(f'Error: {err}')
        return redirect(url_for('travel_options', package_id=package_id))

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if 'user_id' not in session:
        flash('Login required.')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        payment_amount = request.form['amount']
        cursor.execute("SELECT LAST_INSERT_ID()")
        booking_id = cursor.fetchone()[0]
        try:
            cursor.execute("INSERT INTO payments (booking_id, payment_amount, payment_date, payment_status) VALUES (%s, %s, NOW(), 'Completed')", (booking_id, payment_amount))
            db.commit()
            flash('Payment successful!')
            return redirect(url_for('home'))
        except mysql.connector.Error as err:
            flash(f'Error: {err}')
    
    return render_template('payment.html')

if __name__ == '__main__':
    app.run(debug=True)
