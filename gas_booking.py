from flask import Flask, request, render_template, redirect, url_for, session, jsonify,flash
import mysql.connector
import requests
import os
from werkzeug.utils import secure_filename
import smtplib
from email.message import EmailMessage
from flask_mail import Mail, Message 
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random  # Add this import for generating OTPs
import math
from datetime import datetime  # Add this import for getting the current date



app = Flask(__name__)

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'thulasijinka99@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'whajgxzagekygtdk'  # Replace with your App Password
mail=Mail(app)
app.secret_key = "Thulasi"

API_KEY = "YWFyWGIwQlo3MDRMM3d0Y0VTeDRKNHhWbEtPajcyT3ZPZERwVDI3UA=="
API_BASE_URL = "https://api.countrystatecity.in/v1"

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='admin',
        database='project'
    )
    cursor = conn.cursor(dictionary=True)
    print("Connected to MySQL database")
    print("=====================================")
    print(cursor)
except mysql.connector.Error as e:
    print("Error connecting to MySQL database:", e)

# app.secret_key = 'your_secret_key'  # Replace with your actual secret key

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))  

@app.route('/registration', methods=['GET', 'POST'])
def registration():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        # created_at = request.form['created_at']
        # confirm_pwd = request.form['confirmPassword']
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM admin WHERE name = %s', (username,))
        user = cursor.fetchone()
        
        if user:
            msg = 'Account already exists'
        elif not username or not password or not email:
            msg = 'Please fill out the form'
        # elif password != confirm_pwd:
        #     msg = 'Passwords do not match'
        else:
            cursor.execute('INSERT INTO admin (name, email, password) VALUES (%s, %s, %s)', (username, email, password))
            conn.commit()
            msg = 'You have successfully registered'
            return redirect(url_for('login'))
    return render_template('registration.html', msg=msg)

# @app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST', 'GET'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM admin WHERE name = %s', (username,))
        account = cursor.fetchone()
        
        if account and account['password'] == password:
            otp = str(random.randint(100000, 999999))
            send_otp(account['email'], otp)
            session['otp'] = otp
            session['admin_id'] = account['admin_id']
            session['username'] = username
            session['password'] = password
            print("yyyyyyyyyyyyyyyyyyyy",session['admin_id'])
            return redirect(url_for('verify_login_otp'))
        else:
            error = 'No account found with the provided username and password'
    
    return render_template('login.html', error=error)

@app.route('/verify_login_otp', methods=['GET', 'POST'])
def verify_login_otp():
    error = None
    if request.method == 'POST':
        entered_otp = request.form['otp']
        if 'otp' in session and entered_otp == session['otp']:
            session.pop('otp', None)
            session['loggedin'] = True
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid OTP. Please try again.'
    
    return render_template('verify_login_otp.html', error=error)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/login_page')
def login_page():
    return render_template('login.html')

@app.route('/contactus_page')
def contactus_page():
    return render_template('contactus.html')

# @app.route('/new_booking_page')
# def new_booking_page():
#     cursor = conn.cursor(dictionary=True)
#     cursor.execute('SELECT user_id, name FROM user_info')
#     users = cursor.fetchall()
#     cursor.close()
#     return render_template('new_booking.html', users=users)


@app.route('/new_booking_page')
def new_booking_page():
    admin_id = session.get('admin_id')  # Assuming admin_id is stored in session
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT user_id, name FROM user_info WHERE admin_id = %s', (admin_id,))
    users = cursor.fetchall()
    cursor.close()
    return render_template('new_booking.html', users=users)

@app.route('/new_connection_page')
def new_connection_page():
    admin_id = session.get('admin_id')
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT user_id, name FROM user_info where admin_id = %s', (admin_id,))
    users = cursor.fetchall()
    cursor.execute('SELECT branch_id, name FROM branch')
    branches = cursor.fetchall()
    cursor.close()
    return render_template('new_connection.html', users=users, branches=branches)

@app.route('/new_user_page')
def new_user_page():
    return render_template('user.html', max_date=datetime.now().strftime('%Y-%m-%d'))

@app.route('/new_branch_page')
def new_branch_page():
    return render_template('new_branch.html')

def get_paginated_data(query, page, per_page):
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query + f" LIMIT {per_page} OFFSET {(page - 1) * per_page}")
    data = cursor.fetchall()
    cursor.execute("SELECT FOUND_ROWS()")
    total = cursor.fetchone()['FOUND_ROWS()']
    cursor.close()
    return data, total

@app.route('/book_report_page')
def book_report_page():
    admin_id = session.get('admin_id')
    if not admin_id:
        return redirect(url_for('login'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 2
    
    query = f'''
        SELECT SQL_CALC_FOUND_ROWS b.booking_id, u.name as user_name, u.mobile, b.amount, b.booking_date, b.delivery_date
        FROM booking b
        JOIN user_info u ON b.user_id = u.user_id
        WHERE b.admin_id = {admin_id}
    '''
    bookings, total = get_paginated_data(query, page, per_page)
    
    return render_template('book_report.html', bookings=bookings, page=page, per_page=per_page, total=total)

@app.route('/branch_report_page')
def branch_report_page():
    admin_id = session.get('admin_id')
    if not admin_id:
        return redirect(url_for('login'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 2
    
    query = f'''
        SELECT SQL_CALC_FOUND_ROWS branch_id, name, email, phone, state, city
        FROM branch
        WHERE admin_id = {admin_id}
    '''
    print(query)
    branches, total = get_paginated_data(query, page, per_page)
    
    return render_template('branch_report.html', branches=branches, page=page, per_page=per_page, total=total)

@app.route('/connection_report_page')
def connection_report_page():
    admin_id = session.get('admin_id')
    if not admin_id:
        return redirect(url_for('login'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 2
    
    query = f'''
        SELECT SQL_CALC_FOUND_ROWS c.conn_id, u.name as user_name, b.name as branch_name, c.conn_date, c.total_cylindar, c.total_cost, c.full_address, c.description
        FROM connection c
        JOIN user_info u ON c.user_id = u.user_id
        JOIN branch b ON c.branch_id = b.branch_id
        WHERE c.admin_id = {admin_id}
    '''
    connections, total = get_paginated_data(query, page, per_page)
    
    return render_template('connection_report.html', connections=connections, page=page, per_page=per_page, total=total)
    
@app.route('/user_report_page')
def user_report_page():
    admin_id = session.get('admin_id')
    if not admin_id:
        return redirect(url_for('login'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 2
    
    query = f'''
        SELECT SQL_CALC_FOUND_ROWS user_id, name, email, gender, dob, picture
        FROM user_info
        WHERE admin_id = {admin_id}
    '''
    users, total = get_paginated_data(query, page, per_page)
    
    return render_template('user_report.html', users=users, page=page, per_page=per_page, total=total)

@app.route('/about')
def about():
    return render_template('about.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/account_page', methods=['GET', 'POST'])
def account_page():
    msg = ''
    admin_id = session.get('admin_id')
    if not admin_id:
        return redirect(url_for('login'))

    cursor = conn.cursor(dictionary=True)  # Ensure cursor is defined here

    if request.method == 'POST':
        gender = request.form['gender']
        mobile = request.form['mobile']
        dob = request.form['dob'] if request.form['dob'] else None
        address1 = request.form['address1']
        address2 = request.form['address2']
        email = request.form['email']  # Add email field
        country = request.form['country_name']
        state = request.form['state_name']
        city = request.form['city_name']
        photo = None

        if 'photo' in request.files:
            file = request.files['photo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                photo = filename

        cursor.execute('SELECT * FROM admin_info WHERE admin_id = %s', (admin_id,))
        admin_info = cursor.fetchone()

        if admin_info:
            cursor.execute('''
                UPDATE admin_info 
                SET gender = %s, mobile = %s, dob = %s, address1 = %s, address2 = %s, country = %s, state = %s, city = %s, photo = %s
                WHERE admin_id = %s
            ''', (gender, mobile, dob, address1, address2, country, state, city, photo, admin_id))
            cursor.execute('UPDATE admin SET email = %s WHERE admin_id = %s', (email, admin_id))
            conn.commit()
            msg = 'Admin info successfully updated'
        else:
            cursor.execute('''
                INSERT INTO admin_info (admin_id, gender, mobile, dob, address1, address2, country, state, city, photo) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (admin_id, gender, mobile, dob, address1, address2, country, state, city, photo))
            cursor.execute('UPDATE admin SET email = %s WHERE admin_id = %s', (email, admin_id))
            conn.commit()
            msg = 'Admin info successfully created'
            return redirect(url_for('dashboard'))

    cursor.execute('SELECT * FROM admin_info WHERE admin_id = %s', (admin_id,))
    admin_info = cursor.fetchone()
    cursor.execute('SELECT email FROM admin WHERE admin_id = %s', (admin_id,))
    admin_email = cursor.fetchone()
    cursor.close()

    return render_template('account.html', msg=msg, admin_info=admin_info, admin_email=admin_email)

@app.route('/password_page', methods=['GET', 'POST'])
def password_page():
    msg = ''
    if request.method == 'POST':
        admin_id = session.get('admin_id')
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM admin WHERE admin_id = %s AND password = %s', (admin_id, old_password))
        account = cursor.fetchone()
        
        if account is None:
            msg = 'Old password is incorrect'
        elif account['password'] != old_password:
            error = 'Old password is incorrect!'
        elif new_password != confirm_password:
            msg = 'New passwords do not match'
        else:
            cursor.execute('UPDATE admin SET password = %s WHERE admin_id = %s', (new_password, admin_id))
            conn.commit()
            msg = 'Password successfully updated'
            return redirect(url_for('dashboard'))
    return render_template('password.html', msg=msg)

@app.route('/new_user', methods=['GET', 'POST'])
def new_user():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        gender = request.form['gender']
        mobile = request.form['mobile']
        dob = request.form['dob'] if request.form['dob'] else None
        address1 = request.form['address1']
        address2 = request.form['address2']
        country = request.form['country']
        state = request.form['state']
        city = request.form['city']
        picture = None
        admin_id = session.get('admin_id')

        if 'photo' in request.files:
            file = request.files['photo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                picture = filename
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM user_info WHERE name = %s', (username,))
        user = cursor.fetchone()
        
        if user:
            msg = 'Account already exists'
        elif not username or not password or not email:
            msg = 'Please fill out the form'
        else:
            cursor.execute('''
                INSERT INTO user_info (name, password, email, gender, mobile, dob, address1, address2, country, state, city, picture, admin_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (username, password, email, gender, mobile, dob, address1, address2, country, state, city, picture, admin_id))
            conn.commit()
            msg = 'You have successfully registered'
            return redirect(url_for('dashboard'))
    return render_template('user.html', msg=msg)

@app.route('/new_booking', methods=['GET', 'POST'])
def new_booking():
    msg = ''
    if request.method == 'POST':
        user_id = request.form['user_id']
        booking_date = request.form['booking_date']
        delivery_date = request.form['delivery_date']
        amount = request.form['amount']
        description = request.form['description']
        admin_id = session.get('admin_id')
        
        cursor = conn.cursor(dictionary=True)
        # Check if the user has an existing connection
        cursor.execute('SELECT * FROM connection WHERE user_id = %s AND admin_id = %s', (user_id, admin_id))
        connection = cursor.fetchone()
        
        if not connection:
            msg = 'User does not have an existing connection'
        elif not user_id or not booking_date or not delivery_date or not amount:
            msg = 'Please fill out the form'
        else:
            cursor.execute('INSERT INTO booking (user_id, booking_date, delivery_date, amount, description, admin_id) VALUES (%s, %s, %s, %s, %s, %s)', 
                           (user_id, booking_date, delivery_date, amount, description, admin_id))
            conn.commit()
            msg = 'Booking successfully created'
            return redirect(url_for('dashboard'))
    return render_template('new_booking.html', msg=msg)

@app.route('/new_branch', methods=['GET', 'POST'])
def new_branch():
    msg = ''
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        country = request.form['country']
        state = request.form['state']
        city = request.form['city']
        admin_id = session.get('admin_id')
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM branch WHERE name = %s', (name,))
        branch = cursor.fetchone()
        
        if branch:
            msg = 'Branch already exists'
        elif not name or not email or not phone:
            msg = 'Please fill out the form'
        else:
            cursor.execute('INSERT INTO branch (name, email, phone, country, state, city, admin_id) VALUES (%s, %s, %s, %s, %s, %s, %s)', (name, email, phone, country, state, city, admin_id))
            conn.commit()
            msg = 'Branch successfully created'
            return redirect(url_for('dashboard'))
    return render_template('new_branch.html', msg=msg)

@app.route('/new_connection', methods=['GET', 'POST'])
def new_connection():
    msg = ''
    if request.method == 'POST':
        user_id = request.form['user_id']
        branch_id = request.form['branch_id']
        conn_date = request.form['conn_date']
        total_cylindar = request.form['total_cylindar']
        total_cost = request.form['total_cost']
        full_address = request.form['full_address']
        description = request.form['description']
        admin_id = session.get('admin_id')
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM connection WHERE user_id = %s AND conn_date = %s', (user_id, conn_date))
        connection = cursor.fetchone()
        
        if connection:
            msg = 'Connection already exists'
        elif not user_id or not branch_id or not conn_date or not total_cylindar or not total_cost or not full_address:
            msg = 'Please fill out the form'
        else:
            cursor.execute('INSERT INTO connection (user_id, branch_id, conn_date, total_cylindar, total_cost, full_address, description, admin_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', 
                           (user_id, branch_id, conn_date, total_cylindar, total_cost, full_address, description, admin_id))
            conn.commit()
            msg = 'Connection successfully created'
            return redirect(url_for('dashboard'))
    return render_template('new_connection.html', msg=msg)

@app.route('/user_report', methods=['GET'])
def user_report():
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT user_id, picture, name, email, gender, dob FROM user_info WHERE admin_id = {admin_id}')
    users = cursor.fetchall()
    cursor.close()
    return render_template('user_report.html', users=users)

@app.route('/branch_report', methods=['GET'])
def branch_report():
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT branch_id, name, email, phone, state, city FROM branch WHERE admin_id = {admin_id}')
    branches = cursor.fetchall()
    cursor.close()
    return render_template('branch_report.html', branches=branches)

@app.route('/view_booking/<int:booking_id>', methods=['GET'])
def view_booking(booking_id):
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT b.booking_id, u.name as user_name, u.mobile, b.amount, b.booking_date, b.delivery_date, b.description
        FROM booking b
        JOIN user_info u ON b.user_id = u.user_id
        WHERE b.booking_id = %s
    ''', (booking_id,))
    booking = cursor.fetchone()
    cursor.close()
    
    if booking:
        return render_template('view_booking.html', booking=booking)
    else:
        return "Booking not found", 404

@app.route('/delete_booking/<int:booking_id>', methods=['GET'])
def delete_booking(booking_id):
    cursor = conn.cursor()
    cursor.execute('DELETE FROM booking WHERE booking_id = %s', (booking_id,))
    conn.commit()
    cursor.close()
    return redirect(url_for('book_report_page'))

@app.route('/edit_booking/<int:booking_id>', methods=['GET', 'POST'])
def edit_booking(booking_id):
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT b.booking_id, b.user_id, u.name as user_name, u.mobile, b.amount, b.booking_date, b.delivery_date, b.description
        FROM booking b
        JOIN user_info u ON b.user_id = u.user_id
        WHERE b.booking_id = %s
    ''', (booking_id,))
    booking = cursor.fetchone()
    cursor.close()

    if not booking:
        return "Booking not found", 404

    if request.method == 'POST':
        user_id = request.form['user_id']
        booking_date = request.form['booking_date']
        delivery_date = request.form['delivery_date']
        amount = request.form['amount']
        description = request.form['description']

        cursor = conn.cursor()
        cursor.execute('''
            UPDATE booking
            SET user_id = %s, booking_date = %s, delivery_date = %s, amount = %s, description = %s
            WHERE booking_id = %s
        ''', (user_id, booking_date, delivery_date, amount, description, booking_id))
        conn.commit()
        cursor.close()

        return redirect(url_for('book_report_page'))

    return render_template('edit_booking.html', booking=booking)

@app.route('/edit_branch/<int:branch_id>', methods=['GET', 'POST'])
def edit_branch(branch_id):
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        cursor = conn.cursor()
        cursor.execute('UPDATE branch SET name = %s, email = %s, phone = %s WHERE branch_id = %s', (name, email, phone, branch_id))
        conn.commit()
        cursor.close()
        return redirect(url_for('branch_report_page'))
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM branch WHERE branch_id = %s', (branch_id,))
    branch = cursor.fetchone()
    cursor.close()
    return render_template('edit_branch.html', branch=branch)

@app.route('/view_branch/<int:branch_id>', methods=['GET'])
def view_branch(branch_id):
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM branch WHERE branch_id = %s', (branch_id,))
    branch = cursor.fetchone()
    cursor.close()
    if branch:
        return render_template('view_branch.html', branch=branch)
    else:
        return "Branch not found", 404

@app.route('/delete_branch/<int:branch_id>', methods=['POST'])
def delete_branch(branch_id):
    cursor = conn.cursor()
    cursor.execute('DELETE FROM branch WHERE branch_id = %s', (branch_id,))
    conn.commit()
    cursor.close()
    return redirect(url_for('branch_report_page'))

@app.route('/edit_connection/<int:conn_id>', methods=['GET', 'POST'])
def edit_connection(conn_id):
    if request.method == 'POST':
        user_id = request.form['user_id']
        branch_id = request.form['branch_id']
        conn_date = request.form['conn_date']
        total_cylindar = request.form['total_cylindar']
        total_cost = request.form['total_cost']
        full_address = request.form['full_address']
        description = request.form['description']
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE connection
            SET user_id = %s, branch_id = %s, conn_date = %s, total_cylindar = %s, total_cost = %s, full_address = %s, description = %s
            WHERE conn_id = %s
        ''', (user_id, branch_id, conn_date, total_cylindar, total_cost, full_address, description, conn_id))
        conn.commit()
        cursor.close()
        return redirect(url_for('connection_report_page'))
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM connection WHERE conn_id = %s', (conn_id,))
    connection = cursor.fetchone()
    cursor.close()
    return render_template('edit_connection.html', connection=connection)

@app.route('/view_connection/<int:conn_id>', methods=['GET'])
def view_connection(conn_id):
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT c.conn_id, u.name as user_name, b.name as branch_name, c.conn_date, c.total_cylindar, c.total_cost, c.full_address, c.description
        FROM connection c
        JOIN user_info u ON c.user_id = u.user_id
        JOIN branch b ON c.branch_id = b.branch_id
        WHERE c.conn_id = %s
    ''', (conn_id,))
    connection = cursor.fetchone()
    cursor.close()
    if connection:
        return render_template('view_connection.html', connection=connection)
    else:
        return "Connection not found", 404

@app.route('/delete_connection/<int:conn_id>', methods=['POST'])
def delete_connection(conn_id):
    cursor = conn.cursor()
    cursor.execute('DELETE FROM connection WHERE conn_id = %s', (conn_id,))
    conn.commit()
    cursor.close()
    return redirect(url_for('connection_report_page'))

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        gender = request.form['gender']
        dob = request.form['dob']
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_info
            SET name = %s, email = %s, gender = %s, dob = %s
            WHERE user_id = %s
        ''', (name, email, gender, dob, user_id))
        conn.commit()
        cursor.close()
        return redirect(url_for('user_report_page'))
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM user_info WHERE user_id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    return render_template('edit_user.html', user=user)

@app.route('/view_user/<int:user_id>', methods=['GET'])
def view_user(user_id):
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM user_info WHERE user_id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return render_template('view_user.html', user=user)
    else:
        return "User not found", 404

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_info WHERE user_id = %s', (user_id,))
    conn.commit()
    cursor.close()
    return redirect(url_for('user_report_page'))

@app.route('/contact_us', methods=['GET', 'POST'])
def contact_us():
    if request.method == 'POST':
        name = request.form['name'] 
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']

        # Create the email message
        msg = MIMEMultipart()
        msg['From'] = email
        msg['To'] = 'thulasijinka99@gmail.com'  # Replace with your email
        msg['Subject'] = subject
        body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
        msg.attach(MIMEText(body, 'plain'))

        # Send the email
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login('thulasijinka99@gmail.com', 'whajgxzagekygtdk')  # Replace with your email and App Password
            text = msg.as_string()
            server.sendmail(email, 'thulasijinka99@gmail.com', text)  # Replace with your email
            server.quit()
            flash('Message sent successfully', 'success')
        except Exception as e:
            flash(f'An error occurred while sending the message: {str(e)}', 'danger')

        return redirect(url_for('contact_us'))
    return render_template('contactus.html')

def send_otp(email, otp):
    msg = Message('Your OTP', sender='thulasijinka99@gmail.com', recipients=[email])
    msg.body = f'Your OTP is {otp}'
    mail.send(msg)
    return otp


@app.route('/forgot_pswd', methods=['GET', 'POST'])
def forgot_pswd():
    debug_info = ""
    if request.method == 'POST':
        email = request.form['email']
        debug_info += f"Email entered: {email}\n"
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM admin WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        
        if user:
            debug_info += f"User found: {user}\n"
            otp = str(random.randint(100000, 999999))
            send_otp(email, otp)
            session['otp'] = otp
            session['email'] = email
            flash('OTP sent to your email address', 'info')
            return redirect(url_for('verify_otp'))
        else:
            debug_info += "User not found\n"
            flash('Email is not registered', 'danger')
            return render_template('forgot_pswd.html', debug=True, debug_info=debug_info)
    return render_template('forgot_pswd.html', debug=False)

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form['otp']
        if 'otp' in session and entered_otp == session['otp']:
            return redirect(url_for('reset_password'))
        else:
            flash('Invalid OTP. Please try again.', 'danger')
            return redirect(url_for('verify_otp'))
    return render_template('verify_otp.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        new_password = request.form['newPassword']
        confirm_password = request.form['confirmPassword']
        email = session.get('email')

        if new_password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('reset_password'))

        cursor = conn.cursor()
        cursor.execute('UPDATE admin SET password = %s WHERE email = %s', (new_password, email))
        conn.commit()
        cursor.close()
        flash('Password reset successfully. Please log in with your new password.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html')





@app.route('/api/countries', methods=['GET'])
def get_countries():
    headers = {
        "X-CSCAPI-KEY": API_KEY
    }
    response = requests.get(f"{API_BASE_URL}/countries", headers=headers)
    return jsonify(response.json())

@app.route('/api/countries/<country_iso>/states', methods=['GET'])
def get_states(country_iso):
    headers = {
        "X-CSCAPI-KEY": API_KEY
    }
    response = requests.get(f"{API_BASE_URL}/countries/{country_iso}/states", headers=headers)
    return jsonify(response.json())

@app.route('/api/countries/<country_iso>/states/<state_iso>/cities', methods=['GET'])
def get_cities(country_iso, state_iso):
    headers = {
        "X-CSCAPI-KEY": API_KEY
    }
    response = requests.get(f"{API_BASE_URL}/countries/{country_iso}/states/{state_iso}/cities", headers=headers)
    return jsonify(response.json())

if __name__ == '__main__':
    app.run(debug=True)
