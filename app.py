# app.py
import os
from flask import Flask, render_template, request
from attendance_scraper import login, get_student_details, get_subjects, fetch_attendance

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "your-secret-key-here")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check', methods=['POST'])
def check_attendance():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    
    # Basic validation
    if not username or not password:
        return render_template('error.html', 
                             error_message="Please provide both username and password.",
                             back_url="/")
    
    try:
        # Login and fetch data
        session = login(username, password)
        details = get_student_details(session)
        subjects = get_subjects(session, details)
        df_summary = fetch_attendance(session, subjects)
        
        # Calculate totals using the SimpleDataFrame methods
        total_days = df_summary.sum_column("Total Days")
        total_present = df_summary.sum_column("No. of Present")
        overall_attendance_pct = round((total_present / total_days) * 100, 2) if total_days > 0 else 0
        
        return render_template('result.html', 
                             details=details, 
                             df=df_summary.to_dict(orient="records"), 
                             total_days=total_days, 
                             total_present=total_present,
                             overall_attendance_pct=overall_attendance_pct)
                             
    except ValueError as e:
        # Login failed or validation error
        return render_template('error.html', 
                             error_message=str(e),
                             back_url="/")
                             
    except Exception as e:
        # Other errors (network, parsing, etc.)
        return render_template('error.html', 
                             error_message=f"An error occurred while fetching attendance data: {str(e)}",
                             back_url="/")

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', 
                         error_message="Page not found.",
                         back_url="/"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', 
                         error_message="Internal server error. Please try again later.",
                         back_url="/"), 500

# For Vercel deployment
if __name__ == '__main__':
    app.run(debug=False)

# Vercel serverless function handler
def handler(request):
    return app(request.environ, lambda status, headers: None)