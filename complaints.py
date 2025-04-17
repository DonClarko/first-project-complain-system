from flask import Blueprint, request, jsonify, session, flash, redirect, url_for
import json
import os
from datetime import datetime
from auth import login_required
import uuid

complaint_bp = Blueprint('complaint', __name__)

# Path to JSON file for complaint data
COMPLAINTS_FILE = 'complaints.json'

def load_complaints():
    if not os.path.exists(COMPLAINTS_FILE):
        return []
    with open(COMPLAINTS_FILE, 'r') as f:
        return json.load(f)

def save_complaints(complaints):
    with open(COMPLAINTS_FILE, 'w') as f:
        json.dump(complaints, f, indent=4)

@complaint_bp.route('/complaint/submit', methods=['POST'])
@login_required
def submit_complaint():
    try:
        # Get the current user email from session
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'success': False, 'message': 'User not logged in'}), 401
        
        # Generate a unique complaint ID
        complaint_id = f"BCMS-{datetime.now().strftime('%Y')}-{str(uuid.uuid4())[:8]}"
        
        # Get form data
        title = request.form.get('title')
        category = request.form.get('category')
        description = request.form.get('description')
        location = request.form.get('location')
        incident_date = request.form.get('incident-date')
        
        # Create complaint object
        new_complaint = {
            'id': complaint_id,
            'title': title,
            'category': category,
            'description': description,
            'location': location,
            'incident_date': incident_date,
            'submitted_date': datetime.now().isoformat(),
            'user_email': user_email,  # Associate complaint with user
            'status': 'New',
            'updates': []
        }
        
        # Save contact info if provided
        contact_preference = request.form.get('contact-preference')
        if contact_preference == 'yes':
            new_complaint['contact_info'] = {
                'name': request.form.get('full-name'),
                'phone': request.form.get('contact-number'),
                'email': request.form.get('email')
            }
        
        # Add to complaints database
        complaints = load_complaints()
        complaints.append(new_complaint)
        save_complaints(complaints)
        
        return jsonify({
            'success': True,
            'complaint_id': complaint_id,
            'message': 'Complaint submitted successfully'
        })
        
    except Exception as e:
        print(f"Error submitting complaint: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@complaint_bp.route('/complaint/recent')
@login_required
def get_recent_complaints():
    try:
        # Get the current user email from session
        user_email = session.get('user_email')
        if not user_email:
            return jsonify([])
        
        # Load all complaints
        all_complaints = load_complaints()
        
        # Filter complaints for the current user
        user_complaints = [c for c in all_complaints if c.get('user_email') == user_email]
        
        # Sort by date (newest first) and take the most recent ones
        recent_complaints = sorted(
            user_complaints, 
            key=lambda x: x.get('submitted_date', ''), 
            reverse=True
        )[:5]  # Limit to 5 most recent
        
        return jsonify(recent_complaints)
        
    except Exception as e:
        print(f"Error fetching recent complaints: {str(e)}")
        return jsonify([])

@complaint_bp.route('/complaint/all')
@login_required
def get_all_complaints():
    try:
        # Get the current user email from session
        user_email = session.get('user_email')
        if not user_email:
            return jsonify([])
        
        # Load all complaints
        all_complaints = load_complaints()
        
        # Filter complaints for the current user
        user_complaints = [c for c in all_complaints if c.get('user_email') == user_email]
        
        # Sort by date (newest first)
        sorted_complaints = sorted(
            user_complaints, 
            key=lambda x: x.get('submitted_date', ''), 
            reverse=True
        )
        
        return jsonify(sorted_complaints)
        
    except Exception as e:
        print(f"Error fetching all complaints: {str(e)}")
        return jsonify([])

@complaint_bp.route('/complaint/details')
@login_required
def get_complaint_details():
    try:
        complaint_id = request.args.get('id')
        user_email = session.get('user_email')
        
        if not complaint_id or not user_email:
            return jsonify({'error': 'Invalid request'}), 400
        
        # Load all complaints
        all_complaints = load_complaints()
        
        # Find the specific complaint for this user
        complaint = next((c for c in all_complaints if c['id'] == complaint_id and c['user_email'] == user_email), None)
        
        if not complaint:
            return jsonify({'error': 'Complaint not found or access denied'}), 404
        
        return jsonify(complaint)
        
    except Exception as e:
        print(f"Error fetching complaint details: {str(e)}")
        return jsonify({'error': str(e)}), 500