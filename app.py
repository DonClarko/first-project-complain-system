from flask import Flask, render_template
from auth import auth_bp

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Register Blueprint
app.register_blueprint(auth_bp, url_prefix='/auth')

@app.route('/')
def home():
    return render_template('landingpage.html')

@app.route('/resident/dashboard')
def resident_dashboard():
    return render_template('residentdashboard.html')

@app.route('/official/dashboard')
def official_dashboard():
    return render_template('barangayofficialsdashboard.html')

if __name__ == '__main__':
    app.run(debug=True)