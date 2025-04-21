from flask import Blueprint, request, jsonify, session, flash, redirect, url_for, Response, render_template
import time
import json
import os
from datetime import datetime
from auth import login_required, role_required
import uuid

complaint_bp = Blueprint('complaint', __name__)

# Path to JSON file for complaint data
COMPLAINTS_FILE = 'complaints.json'

def calculate_urgency(category):
    urgency_map = {
        'security': 'High',
        'emergency': 'High',
        'waste': 'Medium',
        'road': 'Medium',
        'water': 'Medium',
        'others': 'Low'
    }
    return urgency_map.get(category.lower(), 'Low')

def estimate_resolution(urgency):
    return {
        'High': '24 hours',
        'Medium': '3 days',
        'Low': '7 days'
    }[urgency]

def load_complaints():
    if not os.path.exists(COMPLAINTS_FILE):
        return []
    with open(COMPLAINTS_FILE, 'r') as f:
        return json.load(f)

def save_complaints(complaints):
    with open(COMPLAINTS_FILE, 'w') as f:
        json.dump(complaints, f, indent=4)

# SSE Route for real-time updates
@complaint_bp.route('/stream')
def complaint_stream():
    def event_stream():
        last_modified = 0
        while True:
            current_modified = os.path.getmtime(COMPLAINTS_FILE) if os.path.exists(COMPLAINTS_FILE) else 0
            if current_modified != last_modified:
                last_modified = current_modified
                complaints = load_complaints()
                yield f"data: {json.dumps(complaints)}\n\n"
            time.sleep(1)
    return Response(event_stream(), mimetype="text/event-stream")       

# Keep your original submit route intact
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
            'user_name': session.get('user_name', 'Anonymous Resident'),  # Added user name
            'status': 'New',
            'urgency': calculate_urgency(category),
            'estimated_resolution': estimate_resolution(calculate_urgency(category)),
            'escalated': False,
            'assigned_to': None,  # New field to track which official is handling it
            'notifications_sent': [],  # Track notifications sent about this complaint
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
        
        # Add a notification for officials about the new complaint
        add_official_notification(new_complaint['id'], 'New complaint submitted', 
                               f"A new {new_complaint['urgency']} urgency complaint has been submitted")
        
        return jsonify({
            'success': True,
            'complaint_id': complaint_id,
            'message': 'Complaint submitted successfully'
        })
        
    except Exception as e:
        print(f"Error submitting complaint: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# Keep your original routes intact
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
        user_role = session.get('user_role')  # Make sure you're storing role in session
        
        if not complaint_id:
            return jsonify({'error': 'Invalid request'}), 400
        
        all_complaints = load_complaints()
        
        # For officials, show any complaint regardless of owner
        if user_role == 'official':
            complaint = next((c for c in all_complaints if c['id'] == complaint_id), None)
        else:
            # For residents, maintain original security check
            complaint = next((c for c in all_complaints if c['id'] == complaint_id and c['user_email'] == user_email), None)
        
        if not complaint:
            return jsonify({'error': 'Complaint not found'}), 404
        
        return jsonify(complaint)
        
    except Exception as e:
        print(f"Error fetching complaint details: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Route for officials dashboard
@complaint_bp.route('/officials/dashboard')
@login_required
@role_required('official')
def officials_dashboard():
    return render_template('barangayofficialsdashboard.html')

# API route to get all complaints for officials
@complaint_bp.route('/officials/complaints')
@login_required
@role_required('official')
def get_official_complaints():
    complaints = load_complaints()
    # Sort by date (newest first)
    sorted_complaints = sorted(
        complaints, 
        key=lambda x: x.get('submitted_date', ''), 
        reverse=True
    )
    return jsonify(sorted_complaints)

# API route to get complaints by status for officials - UPDATED
@complaint_bp.route('/officials/complaints/<status>')
@login_required
@role_required('official')
def get_complaints_by_status(status):
    complaints = load_complaints()
    
    # Handle the 'all' case
    if status.lower() == 'all':
        filtered_complaints = complaints
    # Handle 'escalated' specifically
    elif status.lower() == 'escalated':
         filtered_complaints = [c for c in complaints if c.get('escalated', True) and c.get('status') == 'Escalated']
    # Handle normal status filtering
    else:
        status_map = {
            'new': 'New',
            'pending': 'Pending Review',
            'pending-review': 'Pending Review',
            'in-progress': 'In Progress',
            'resolved': 'Resolved'
        }
        actual_status = status_map.get(status.lower(), status.capitalize())
        filtered_complaints = [c for c in complaints if c.get('status') == actual_status]
    
    # Sort by urgency (High first) then by date (newest first)
    sorted_complaints = sorted(
        filtered_complaints,
        key=lambda x: (
            0 if x.get('urgency') == 'High' else 1 if x.get('urgency') == 'Medium' else 2,
            -datetime.fromisoformat(x.get('submitted_date', datetime.now().isoformat())).timestamp()
        )
    )
    
    return jsonify(sorted_complaints)

# Route to handle complaint status updates by officials - UPDATED
@complaint_bp.route('/officials/update', methods=['POST'])
@login_required
@role_required('official')
def update_complaint_status():
    try:
        data = request.get_json()
        complaint_id = data.get('complaint_id')
        new_status = data.get('status')
        action_note = data.get('action_note', '')
        notify_resident = data.get('notify_resident', True)  # Default to True for backward compatibility
        
        if not complaint_id or not new_status:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        complaints = load_complaints()
        
        # Map status values to standardized format
        status_map = {
            'new': 'New',
            'pending': 'Pending Review',
            'in progress': 'In Progress',
            'resolved': 'Resolved',
            'escalated': 'Escalated'
        }
        
        # Standardize the status if it matches a key in our map
        standardized_status = status_map.get(new_status.lower(), new_status)
        
        # Find the specific complaint
        for complaint in complaints:
            if complaint['id'] == complaint_id:
                old_status = complaint['status']
                complaint['status'] = standardized_status
                
                # If being escalated
                if standardized_status == 'Escalated' or data.get('escalate') == True:
                    complaint['escalated'] = True
                    
                # If being assigned
                if data.get('assign_to'):
                    complaint['assigned_to'] = data.get('assign_to')
                
                # Record the update
                update_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'from_status': old_status,
                    'to_status': standardized_status,
                    'action_note': action_note,
                    'by_official': session.get('user_email'),
                    'official_name': session.get('user_name', 'Barangay Official')
                }
                
                if 'updates' not in complaint:
                    complaint['updates'] = []
                    
                complaint['updates'].append(update_entry)
                
                # Send notification to the resident
                if notify_resident:
                    add_resident_notification(
                        complaint['user_email'],
                        complaint['id'],
                        f"Complaint status updated to {standardized_status}",
                        f"Your complaint has been {standardized_status.lower()}. {action_note if action_note else ''}"
                    )
                
                save_complaints(complaints)
                return jsonify({'success': True})
                
        return jsonify({'success': False, 'error': 'Complaint not found'}), 404
    
    except Exception as e:
        print(f"Error updating complaint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Route to get stats for officials dashboard - UPDATED
@complaint_bp.route('/officials/stats')
@login_required
@role_required('official')
def get_complaint_stats():
    complaints = load_complaints()
    
    # Calculate overall stats
    total = len(complaints)
    new_count = len([c for c in complaints if c.get('status') == 'New'])
    pending_count = len([c for c in complaints if c.get('status') == 'Pending Review'])
    in_progress_count = len([c for c in complaints if c.get('status') == 'In Progress'])
    resolved_count = len([c for c in complaints if c.get('status') == 'Resolved'])
    escalated_count = len([c for c in complaints if c.get('escalated', True) and c.get('status') == 'Escalated'])
    
    # Count urgent pending complaints
    urgent_pending = len([c for c in complaints if c.get('status') in ['New', 'Pending Review'] and c.get('urgency') == 'High'])
    
    # Calculate average resolution time for resolved complaints
    resolution_times = []
    for complaint in complaints:
        if complaint.get('status') == 'Resolved' and complaint.get('updates'):
            submitted = datetime.fromisoformat(complaint.get('submitted_date'))
            
            # Find the resolved update
            for update in reversed(complaint.get('updates', [])):
                if update.get('to_status') == 'Resolved':
                    resolved = datetime.fromisoformat(update.get('timestamp'))
                    resolution_time = (resolved - submitted).total_seconds() / 86400  # Convert to days
                    resolution_times.append(resolution_time)
                    break
    
    avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
    
    # Get counts by category
    categories = {}
    for complaint in complaints:
        category = complaint.get('category', 'others')
        if category not in categories:
            categories[category] = 0
        categories[category] += 1
    
    return jsonify({
        'total': total,
        'new': new_count,
        'pending': pending_count,
        'in_progress': in_progress_count,
        'resolved': resolved_count,
        'escalated': escalated_count,
        'urgent_pending': urgent_pending,
        'avg_resolution_time': round(avg_resolution_time, 1),  # Round to 1 decimal place
        'categories': categories
    })

# Function to add notification for officials
def add_official_notification(complaint_id, title, message):
    # In a full implementation, this would save to a database
    # For now we'll add it to the complaint record
    complaints = load_complaints()
    
    for complaint in complaints:
        if complaint['id'] == complaint_id:
            if 'official_notifications' not in complaint:
                complaint['official_notifications'] = []
                
            notification = {
                'id': str(uuid.uuid4())[:8],
                'timestamp': datetime.now().isoformat(),
                'title': title,
                'message': message,
                'read': False
            }
            
            complaint['official_notifications'].append(notification)
            break
    
    save_complaints(complaints)

# Function to add notification for residents
def add_resident_notification(user_email, complaint_id, title, message):
    # In a full implementation, this would save to a user notifications database
    # For now we'll add it to the complaint record
    complaints = load_complaints()
    
    for complaint in complaints:
        if complaint['id'] == complaint_id:
            if 'resident_notifications' not in complaint:
                complaint['resident_notifications'] = []
                
            notification = {
                'id': str(uuid.uuid4())[:8],
                'user_email': user_email,
                'timestamp': datetime.now().isoformat(),
                'title': title,
                'message': message,
                'read': False
            }
            
            complaint['resident_notifications'].append(notification)
            complaint['notifications_sent'].append({
                'timestamp': datetime.now().isoformat(),
                'message': title
            })
            break
    
    save_complaints(complaints)

# Route to assign complaint to an official
@complaint_bp.route('/officials/assign', methods=['POST'])
@login_required
@role_required('official')
def assign_complaint():
    data = request.get_json()
    complaint_id = data.get('complaint_id')
    official_email = data.get('official_email')
    official_name = data.get('official_name', 'Barangay Official')
    
    if not complaint_id or not official_email:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    complaints = load_complaints()
    
    for complaint in complaints:
        if complaint['id'] == complaint_id:
            complaint['assigned_to'] = official_email
            complaint['assigned_name'] = official_name
            
            # Add update entry
            update_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'assigned',
                'to_official': official_email,
                'official_name': official_name,
                'by_official': session.get('user_email')
            }
            
            if 'updates' not in complaint:
                complaint['updates'] = []
                
            complaint['updates'].append(update_entry)
            
            save_complaints(complaints)
            return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Complaint not found'}), 404

# Route to mark a complaint as escalated and provide resolution - UPDATED
@complaint_bp.route('/officials/escalate', methods=['POST'])
@login_required
@role_required('official')
def escalate_complaint():
    data = request.get_json()
    complaint_id = data.get('complaint_id') 
    escalate_note = data.get('escalate_note', '')
    
    if not complaint_id:
        return jsonify({'success': False, 'error': 'Missing complaint ID'}), 400
    
    complaints = load_complaints()
    
    for complaint in complaints:
        if complaint['id'] == complaint_id:
            complaint['escalated'] = True
            complaint['escalate_note'] = escalate_note
            complaint['status'] = 'Escalated'  # Update status to reflect escalation
            
            # Add update entry
            update_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'escalated',
                'from_status': complaint.get('status', 'New'),
                'to_status': 'Escalated',
                'note': escalate_note,
                'by_official': session.get('user_email'),
                'official_name': session.get('user_name', 'Barangay Official')
            }
            
            if 'updates' not in complaint:
                complaint['updates'] = []
                
            complaint['updates'].append(update_entry)
            
            # Add notification for the resident
            add_resident_notification(
                complaint['user_email'],
                complaint['id'],
                "Complaint has been escalated",
                f"Your complaint has been escalated for further attention. {escalate_note if escalate_note else ''}"
            )
            
            save_complaints(complaints)
            return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Complaint not found'}), 404

# Route to provide resolution for escalated complaints
@complaint_bp.route('/officials/resolve-escalated', methods=['POST'])
@login_required
@role_required('official')
def resolve_escalated():
    data = request.get_json()
    complaint_id = data.get('complaint_id')
    resolution = data.get('resolution', '')
    
    if not complaint_id or not resolution:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    complaints = load_complaints()
    
    for complaint in complaints:
        if complaint['id'] == complaint_id and complaint.get('escalated', False):
            # Change status to In Progress since a solution was found
            complaint['status'] = 'In Progress'
            complaint['resolution_plan'] = resolution
            
            # Add update entry
            update_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'resolution_provided',
                'from_status': 'Escalated',
                'to_status': 'In Progress',
                'resolution': resolution,
                'by_official': session.get('user_email'),
                'official_name': session.get('user_name', 'Barangay Official')
            }
            
            if 'updates' not in complaint:
                complaint['updates'] = []
                
            complaint['updates'].append(update_entry)
            
            # Notify the resident
            add_resident_notification(
                complaint['user_email'],
                complaint['id'],
                "Solution found for your complaint",
                f"A solution has been found for your escalated complaint. Your complaint is now in progress. {resolution}"
            )
            
            save_complaints(complaints)
            return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Complaint not found or not escalated'}), 404