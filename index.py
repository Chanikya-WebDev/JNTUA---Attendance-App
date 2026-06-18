import os
from datetime import datetime
from flask import (
    Flask, flash, render_template, request,
    redirect, send_from_directory, session,  make_response
)
from flask_wtf.csrf import CSRFProtect

from flask_mail import Mail, Message

from attendance_scraper import (
    student_login,
    get_student_details,
    get_subjects,
    fetch_attendance,
)


app = Flask(__name__)
csrf = CSRFProtect(app)


app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY","jntua")

app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Mail config
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "True") == "True"
app.config["MAIL_USE_SSL"] = os.environ.get("MAIL_USE_SSL", "False") == "True"
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER")

mail = Mail(app)

# State stores
ACTIVE_SESSIONS = {}

# --------------------------------------------------
# ROUTES
# --------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def login_page():
    if request.method == "GET":
        if "query" in request.args:
            return redirect("/", code=301)
        resp = make_response(render_template("index.html"))
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        resp.headers["Pragma"]        = "no-cache"
        resp.headers["Expires"]       = "0"
        return resp

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        flash("Username and password are required.", "error")
        return redirect("/")

    try:
        # Utilizing the secure regex array-solving session loop
        auth_session = student_login(username, password)

        session.clear()
        session["user"] = username
        ACTIVE_SESSIONS[username] = auth_session

        # Automatically cache profile metadata settings
        details = get_student_details(auth_session)
        ACTIVE_SESSIONS[username + "_details"] = details
        print(ACTIVE_SESSIONS)
        return redirect("/dashboard")

    except Exception as e:
        flash(str(e), "error")
        return redirect("/")                   


@app.route("/dashboard", methods=["GET"])
def dashboard():
    if "user" not in session:
        return redirect("/")

    username = session["user"]
    auth_session = ACTIVE_SESSIONS.get(username)

    if not auth_session:
        session.clear()
        return redirect("/")

    try:
        # AUTOMATIC SCRAPE AND CALCULATION PIPELINE
        details = get_student_details(auth_session)
        subjects = get_subjects(auth_session, details)
        df_summary = fetch_attendance(auth_session, subjects)

        df = df_summary.to_dict(orient="records")

        # MATH CALCULATION ENGINE (75% Threshold Target Checks)
        for row in df:
            total = row.get("Total Days", 0) or 0
            present = row.get("No. of Present", 0) or 0
            pct = row.get("Attendance %", 0) or 0

            try:
                total = int(total)
                present = int(present)
                pct = float(pct)
            except Exception:
                total = present = pct = 0

            if total == 0:
                row["Can Skip"] = 0
                row["Need to Attend"] = 0
            elif pct >= 75:
                # Calculates max classes a student can safely skip while staying above 75%
                row["Can Skip"] = max(0, int((present / 0.75) - total))
                row["Need to Attend"] = 0
            else:
                row["Can Skip"] = 0
                # Calculates minimum consecutive classes needed to restore standing to 75%
                row["Need to Attend"] = max(0, int((0.75 * total - present) / 0.25))

        total_days = sum(r.get("Total Days", 0) for r in df)
        total_present = sum(r.get("No. of Present", 0) for r in df)
        overall_pct = round((total_present / total_days) * 100, 2) if total_days else 0

        
        
        return render_template(
            "result.html",
            details=details,
            df=df,
            total_days=total_days,
            total_present=total_present,
            overall_attendance_pct=overall_pct,
            show=False,
            mess=None,
        )

    except Exception as e:
        return render_template(
            "error.html",
            error_message=str(e),
            back_url="/"
        )

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_FILE_SIZE = 2 * 1024 * 1024

def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        try:
            admission = request.form.get("admission")
            email = request.form.get("user_email")
            message = request.form.get("message")

            if not admission or not email or not message:
                flash("All fields are required.", "error")
                return redirect("/contact")
            
            screenshot = request.files.get("screenshot")

            if screenshot:
                file_data=b""
                if not allowed_file(screenshot.filename):
                    flash("Only PNG, JPG, JPEG and WEBP allowed.", "error")
                    return redirect("/contact")

                file_data = screenshot.read()

            if len(file_data) > MAX_FILE_SIZE:
                flash("Image exceeds 2MB.", "error")
                return redirect("/contact")

                
            issue_data = f"\nIssue Report\n============\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nAdmission Number: {admission}\nEmail: {email}\nMessage:\n{message}\n{'=' * 50}\n"
            mail_configured = app.config.get("MAIL_USERNAME") and app.config.get("MAIL_PASSWORD")
            
            if mail_configured:
                try:
                    recipient_email = app.config.get("MAIL_DEFAULT_SENDER") or app.config.get("MAIL_USERNAME")
                    msg = Message(
                        subject=f"Issue Report from {admission}",
                        recipients=[recipient_email] if isinstance(recipient_email, str) else [recipient_email],
                        body=issue_data,
                        sender=app.config.get("MAIL_DEFAULT_SENDER") or app.config.get("MAIL_USERNAME")
                    )
                    if screenshot and screenshot.filename:

                        msg.attach(
                            secure_filename(screenshot.filename),
                            screenshot.mimetype,
                            file_data
                        )

                        mail.send(msg)
                    flash("Issue submitted successfully!", "success")
                except:
                    with open("issues.log", "a", encoding="utf-8") as f:
                        f.write(issue_data)
                    flash("Issue logged successfully to system storage.", "success")
            else:
                with open("issues.log", "a", encoding="utf-8") as f:
                    f.write(issue_data)
                flash("Issue logged successfully to system storage.", "success")
            
            return redirect("/contact")
        except Exception as e:
            flash(f"Error submitting issue: {str(e)}", "error")
            return redirect("/contact")

    return render_template("contact.html")


@app.route("/contributors")
def contributors():
    return render_template("contributors.html")


@app.route("/loh")
def list_of_holidays():
    return render_template("list_of_holidays.html")

@app.route("/robots.txt")
def robots():
    content = """
        User-agent: *
        Allow: /

        Sitemap: https://jntua-attendance-app.vercel.app/sitemap.xml
            """
    response = make_response(content)
    response.headers["Content-Type"] = "text/plain"
    return response

@app.route("/sitemap.xml")
def sitemap():
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset
xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">

<url>
<loc>https://jntua-attendance-app.vercel.app/</loc>
<priority>1.0</priority>
</url>

<url>
<loc>https://jntua-attendance-app.vercel.app/contact</loc>
<priority>0.8</priority>
</url>

<url>
<loc>https://jntua-attendance-app.vercel.app/contributors</loc>
<priority>0.7</priority>
</url>

<url>
<loc>https://jntua-attendance-app.vercel.app/loh</loc>
<priority>0.7</priority>
</url>

</urlset>
"""
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@app.after_request
def security_headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )
    return response



@app.route("/icon.png")
def favicon():
    return send_from_directory("templates", "icon.png")


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", error_message="Page not found.", back_url="/"), 404


@app.errorhandler(500)
def server_error(_):
    return render_template("error.html", error_message="Internal server error.", back_url="/"), 500


# Required interface hook configuration for Vercel deployment pipelines
def handler(environ, start_response):
    return app(environ, start_response)


if __name__ == "__main__":
    app.run(port=5001, debug=False)
