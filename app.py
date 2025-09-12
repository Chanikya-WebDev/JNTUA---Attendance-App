# app.py
import os
from flask import Flask, render_template, request
from attendance_scraper import login, get_student_details, get_subjects, fetch_attendance

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-prod")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check', methods=['POST'])
def check_attendance():
    username = request.form['username']
    password = request.form['password']
    
    try:
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
    except Exception as e:
        return f"<h3>Error: {str(e)}</h3><a href='/'>← Back to Login</a>"

# Only for local dev
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=False)