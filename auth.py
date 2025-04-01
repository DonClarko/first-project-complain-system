from flask import Blueprint, render_template, request, redirect, url_for, flash
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

# Path to JSON file for user data
USERS_FILE = 'users.json'

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

@auth_bp.route('/<form_type>')
def show_auth(form_type):
    # Validate form_type
    if form_type not in ['login', 'signup']:
        form_type = 'login'
    return render_template('auth.html', form_type=form_type)

@auth_bp.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'resident')
        remember = True if request.form.get('remember') else False
        
        users = load_users()
        user = users.get(email)
        
        if not user or not check_password_hash(user['password'], password):
            flash('Invalid email or password', 'error')
            return redirect(url_for('auth.show_auth', form_type='login'))
        
        if user['role'] != role:
            flash(f'Please login as {user["role"]}', 'error')
            return redirect(url_for('auth.show_auth', form_type='login'))
        
        flash('Login successful!', 'success')
        # In a real app, you would login_user here and redirect to dashboard
        return redirect(url_for('home'))
    
    return redirect(url_for('auth.show_auth', form_type='login'))

@auth_bp.route('/signup', methods=['POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('fullName')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirmPassword')
        role = request.form.get('role', 'resident')
        
        users = load_users()
        
        if email in users:
            flash('Email already exists', 'error')
            return redirect(url_for('auth.show_auth', form_type='signup'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('auth.show_auth', form_type='signup'))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters', 'error')
            return redirect(url_for('auth.show_auth', form_type='signup'))
        
        # Create new user
        users[email] = {
            'full_name': full_name,
            'email': email,
            'phone': phone,
            'password': generate_password_hash(password),
            'role': role,
            'created_at': datetime.now().isoformat()
        }
        
        save_users(users)
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('auth.show_auth', form_type='login'))
    
    return redirect(url_for('auth.show_auth', form_type='signup'))