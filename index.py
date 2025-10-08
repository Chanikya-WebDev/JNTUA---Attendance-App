
import os
from dotenv import load_dotenv
from flask import Flask, flash, render_template, request,redirect, url_for,send_from_directory
from flask_mail import Mail, Message
from attendance_scraper import login, get_student_details, get_subjects, fetch_attendance

load_dotenv()
# Initialize Flask app

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "your-secret-key-here")

# Flask-Mail configuration using environment variables
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False') == 'True'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')
mail = Mail(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    back_url = request.args.get('back_url', url_for('index'))
    if request.method == 'POST':
        admission = request.form.get('admission', '').strip()
        user_email = request.form.get('user_email', '').strip()
        message = request.form.get('message', '').strip()
        screenshot = request.files.get('screenshot')
        if not admission or not message or not user_email:
            flash('Admission number, your email, and issue message are required.', 'error')
            return redirect(url_for('contact'))
            # Prepare email
        msg = Message(
            subject=f"Attendance App Issue from {admission}",
            recipients=[app.config['MAIL_DEFAULT_SENDER']],
            body=f"Admission Number: {admission}\nUser Email: {user_email}\n\nIssue Message:\n{message}"
        )
        # Attach screenshot if provided
        if screenshot and screenshot.filename:
            ext = screenshot.filename.rsplit('.', 1)[-1].lower()
            if ext in ['png', 'jpg', 'jpeg']:
                msg.attach(screenshot.filename, screenshot.mimetype, screenshot.read())
        mail.send(msg)
        flash('Your issue has been submitted successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('contact.html', back_url=back_url)


@app.route('/check', methods=['POST'])
def check_attendance():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()

    # Basic validation
    if not username or not password:
        return render_template(
            'error.html',
            error_message="Please provide both username and password.",
            back_url="/"
        )

    try:
        # Login and fetch data
        session = login(username, password)
        details = get_student_details(session)
        subjects = get_subjects(session, details)
        df_summary = fetch_attendance(session, subjects)

        # Calculate totals using the SimpleDataFrame methods
        total_days = df_summary.sum_column("Total Days")
        total_present = df_summary.sum_column("No. of Present")
        overall_attendance_pct = (
            round((total_present / total_days) * 100, 2)
            if total_days > 0 else 0
        )
        username_env = os.environ.get('S_USERNAME')
        show = details['Username'] == username_env
        mess = None  
        if show:
            mess = os.environ.get('S_MESSAGE')
        return render_template(
            'result.html',
            details=details,
            df=df_summary.to_dict(orient="records"),
            total_days=total_days,
            total_present=total_present,
            overall_attendance_pct=overall_attendance_pct,
            show=show,
            mess=mess,
            back_url=request.url
        )

    except ValueError as e:
        # Login failed or validation error
        return render_template(
            'error.html',
            error_message=str(e),
            back_url="/"
        )

    except Exception as e:
        # Other errors (network, parsing, etc.)
        return render_template(
            'error.html',
            error_message=f"An error occurred while fetching attendance data: {str(e)}",
            back_url="/"
        )

@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory("static", "sitemap.xml")

# Serve robots.txt
@app.route("/robots.txt")
def robots():
    return send_from_directory("static", "robots.txt")


@app.errorhandler(404)
def not_found(error):
    return render_template(
        'error.html',
        error_message="Page not found.",
        back_url="/"
    ), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template(
        'error.html',
        error_message="Internal server error. Please try again later.",
        back_url="/"
    ), 500


# Local dev only (Vercel will ignore this and import `app`)
if __name__ == '__main__':
    app.run(debug=False)
