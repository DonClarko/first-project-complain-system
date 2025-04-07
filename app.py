from flask import Flask, render_template
from auth import auth_bp, create_default_admin


app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')


create_default_admin()

# ... rest of your routes ...
@app.route('/')
def home():
    return render_template('landingpage.html')

@app.route('/resident/dashboard')
def resident_dashboard():
    return render_template('residentdashboard.html')

@app.route('/official/dashboard')
def official_dashboard():
    return render_template('barangayofficialsdashboard.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admindashboard.html')

if __name__ == '__main__':
    app.run(debug=True)