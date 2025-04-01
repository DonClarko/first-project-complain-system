from flask import Flask, render_template
from auth import auth_bp
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this for production!

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')

@app.route('/')
def home():
    return render_template('landingpage.html')

if __name__ == '__main__':
    app.run(debug=True)