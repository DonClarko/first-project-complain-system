# complaints.py
import os
import json
from datetime import datetime
from flask import Blueprint, request, jsonify

complaint_bp = Blueprint('complaint', __name__, url_prefix='/complaint')

# Configuration
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)
COMPLAINTS_FILE = os.path.join(DATA_DIR, 'complaints.json')

def load_complaints():
    """Load complaints from JSON file"""
    if not os.path.exists(COMPLAINTS_FILE):
        return []
    with open(COMPLAINTS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_complaints(complaints):
    """Save complaints to JSON file"""
    with open(COMPLAINTS_FILE, 'w') as f:
        json.dump(complaints, f, indent=2)

def generate_complaint_id():
    """Generate a new complaint ID in BCMS-YYYY-NNN format"""
    complaints = load_complaints()
    year = datetime.now().year
    if not complaints:
        return f"BCMS-{year}-001"
    
    max_id = 0
    for complaint in complaints:
        if complaint['id'].startswith(f"BCMS-{year}-"):
            try:
                num = int(complaint['id'].split('-')[-1])
                max_id = max(max_id, num)
            except (IndexError, ValueError):
                continue
    
    return f"BCMS-{year}-{max_id + 1:03d}"

@complaint_bp.route('/submit', methods=['POST'])
def submit_complaint():
    """Handle complaint form submission"""
    form_data = request.form.to_dict()
    
    new_complaint = {
        'id': generate_complaint_id(),
        'title': form_data.get('title', ''),
        'category': form_data.get('category', ''),
        'description': form_data.get('description', ''),
        'location': form_data.get('location', ''),
        'incident_date': form_data.get('incident-date', ''),
        'status': 'New',
        'submitted_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'contact_preference': form_data.get('contact-preference', 'yes'),
        'contact_info': {
            'name': form_data.get('full-name', ''),
            'phone': form_data.get('contact-number', ''),
            'email': form_data.get('email', '')
        }
    }
    
    complaints = load_complaints()
    complaints.append(new_complaint)
    save_complaints(complaints)
    
    return jsonify({
        'success': True,
        'message': 'Complaint submitted successfully',
        'complaint_id': new_complaint['id']
    })

@complaint_bp.route('/recent', methods=['GET'])
def get_recent_complaints():
    """Get the 3 most recent complaints"""
    complaints = load_complaints()
    recent = sorted(complaints, key=lambda x: x['submitted_date'], reverse=True)[:3]
    return jsonify(recent)

@complaint_bp.route('/details', methods=['GET'])
def get_complaint_details():
    """Get details for a specific complaint"""
    complaint_id = request.args.get('id')
    complaints = load_complaints()
    complaint = next((c for c in complaints if c['id'] == complaint_id), None)
    
    if not complaint:
        return jsonify({'success': False, 'message': 'Complaint not found'}), 404
    
    return jsonify(complaint)

@complaint_bp.route('/all', methods=['GET'])
def get_all_complaints():
    """Get all complaints for the current user"""
    # Note: In a real application, you would filter by the logged-in user
    # For now, we'll return all complaints
    complaints = load_complaints()
    return jsonify(complaints)