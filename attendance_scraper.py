import requests
from bs4 import BeautifulSoup
import re
import time
import concurrent.futures

BASE_URL = "https://jntuaceastudents.classattendance.in/"

# --------------------------------------------------
# CORE AUTHENTICATION ENGINE
# --------------------------------------------------
def student_login(username: str, password: str) -> requests.Session:
    """Authenticates against the portal by solving the obfuscated 
    integrity token arrays dynamically and returns an active session.
    """
    session = requests.Session()
    session.headers.update({
        "Host": "jntuaceastudents.classattendance.in",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Accept-Language": "en-US,en;q=0.9",
    })

    try:
        # Step 1: Hit landing page to register backend session cookies
        response = session.get(BASE_URL, timeout=10)
        html_content = response.text
        
        soup = BeautifulSoup(html_content, "html.parser")
        login_form = soup.find("form", id="loginForm")
        if not login_form:
            raise ValueError("Portal structure changed or blocked (Missing loginForm).")

        # Step 2: Extract the obfuscated JavaScript arrays dynamically
        try:
            name_parts = re.findall(r'var nameParts = \[(.*?)\];', html_content)[0]
            computed_name = "".join(re.findall(r'"([^"]*)"', name_parts))

            value_parts = re.findall(r'var valueParts = \[(.*?)\];', html_content)[0]
            computed_value = "".join(re.findall(r'"([^"]*)"', value_parts))
        except (IndexError, TypeError):
            # Fallback values if parsing fails
            computed_name = "a_3f754265"
            computed_value = "1c9e4f41f180f641253c1fbb861d3022"

        # Step 3: Build the structural payload
        payload = {}
        for input_tag in login_form.find_all("input"):
            input_type = input_tag.get("type")
            name_attr = input_tag.get("name")
            id_attr = input_tag.get("id")
            val_attr = input_tag.get("value", "")
            
            if input_type == "hidden":
                if name_attr == "dummy_field" or id_attr == "integrity_token":
                    payload[computed_name] = computed_value
                elif name_attr:
                    payload[name_attr] = val_attr
            elif input_type == "submit" and name_attr:
                payload[name_attr] = val_attr

        payload["username"] = username
        payload["password"] = password

        # Mimic human cadence
        time.sleep(0.4)

        # Step 4: Re-align headers for form navigation context
        session.headers.update({
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://jntuaceastudents.classattendance.in",
            "Referer": "https://jntuaceastudents.classattendance.in/",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document"
        })

        # Step 5: Send POST request to authentication loop
        auth_response = session.post(BASE_URL, data=payload, timeout=10, allow_redirects=True)
        
        # Step 6: Success Verification
        if "studenthome.php" not in auth_response.url.lower():
            fail_soup = BeautifulSoup(auth_response.text, "html.parser")
            error_msg = fail_soup.find(class_=["alert", "text-danger", "invalid-feedback"])
            error_details = error_msg.text.strip() if error_msg else "Invalid credentials or session mismatch."
            raise ValueError(f"Portal Rejected Request: {error_details}")
        
        return session

    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed connecting to university server: {str(e)}")


# --------------------------------------------------
# STUDENT DETAILS DASHBOARD PARSER
# --------------------------------------------------
def get_student_details(session: requests.Session) -> dict:
    """Parses user bio info and extracts default tracking parameters."""
    home_res = session.get(BASE_URL + "studenthome.php", timeout=10)

    if home_res.status_code != 200 or not home_res.text:
        raise ValueError("Failed to load student home page.")
        
    soup = BeautifulSoup(home_res.text, "html.parser")
    details = {}

    # Extract metadata blocks cleanly
    for card in soup.find_all("div", class_="card"):
        header = card.find("div", class_="card-header")
        if header and "My Details" in header.text:
            for li in card.find_all("li", class_="list-group-item"):
                strong = li.find("strong")
                if strong:
                    key = strong.text.replace(":", "").strip()
                    value = li.text.replace(strong.text, "").strip()
                    details[key] = value
            break

    # Robust fallback selector mechanics for hidden parameters
    # Targets current active session form attributes dynamically
    form = soup.find("form", action="studentsubjects.php")
    if form:
        for inp in form.find_all("input", type="hidden"):
            name = inp.get("name")
            if name:
                details[name] = inp.get("value", "")

    # Ensure keys are initialized cleanly
    details.setdefault("Role", "Student")
    return details


# --------------------------------------------------
# SUBJECTS EXTRACTOR
# --------------------------------------------------
def get_subjects(session: requests.Session, student_info: dict) -> list:
    """Fetches hidden form parameter structures mapped to subject lists."""
    payload = {
        "student_id": student_info.get("student_id"),
        "class_id": student_info.get("class_id"),
        "classname": student_info.get("classname"),
        "acad_year": student_info.get("acad_year"),
    }
    
    session.headers.update({
        "Referer": BASE_URL + "studenthome.php"
    })
    
    res = session.post(BASE_URL + "studentsubjects.php", data=payload, timeout=15)
    if not res.text:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    subjects = []

    # Iterate structural row data elements mapping to individual form entries
    for form in soup.find_all("form", action="studentsubatt.php"):
        data = {}
        for inp in form.find_all("input"):
            if inp.get("name"):
                data[inp["name"]] = inp.get("value", "")
        if data:
            subjects.append(data)

    return subjects


# --------------------------------------------------
# DATAFRAME UTILITY FOR RESULT FORMATTING
# --------------------------------------------------
class SimpleDataFrame:
    def __init__(self, data):
        self.data = data if isinstance(data, list) else []

    def to_dict(self, orient="records"):
        return self.data


# --------------------------------------------------
# MULTI-THREADED ATTENDANCE RETRIEVAL ENGINE
# --------------------------------------------------
def fetch_single_attendance(session, payload):
    """Hits subatt vectors parsing transactional timelines to compute metrics."""
    try:
        # Re-align validation targets per transaction context
        headers = {
            "Referer": BASE_URL + "studentsubjects.php",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        res = session.post(BASE_URL + "studentsubatt.php", data=payload, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table", class_="table")

        if not table:
            raise ValueError

        records = []
        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) >= 3:
                records.append({
                    "date": cols[0].text.strip(),
                    "status": cols[2].text.strip()
                })

        total = len(records)
        present = sum(1 for r in records if r["status"] == "Present")

        return {
            "Subject": payload.get("sub_fullname", "Unknown"),
            "Start Date": records[0]["date"] if records else "",
            "End Date": records[-1]["date"] if records else "",
            "Total Days": total,
            "No. of Present": present,
            "No. of Absent": total - present,
            "Attendance %": round((present / total) * 100, 1) if total else 0,
            "Details": records,
        }

    except Exception:
        return {
            "Subject": payload.get("sub_fullname", "Unknown"),
            "Start Date": "",
            "End Date": "",
            "Total Days": 0,
            "No. of Present": 0,
            "No. of Absent": 0,
            "Attendance %": 0,
            "Details": [],
        }


def fetch_attendance(session: requests.Session, subjects: list):
    """Pools subject requests dynamically across 5 worker threads."""
    if not subjects:
        return SimpleDataFrame([])

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(fetch_single_attendance, session, s)
            for s in subjects if isinstance(s, dict)
        ]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    return SimpleDataFrame(results)