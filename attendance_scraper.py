import requests
from bs4 import BeautifulSoup
import hashlib
import re
import time
import concurrent.futures
from urllib.parse import urljoin

BASE_URL = "https://jntuaceastudents.classattendance.in/"


def _find_login_form(soup: BeautifulSoup):
    """Find the portal login form without depending on one exact form id."""
    login_form = soup.find("form", id="loginForm")
    if login_form:
        return login_form

    for form in soup.find_all("form"):
        has_username = form.find("input", attrs={"name": "username"})
        has_password = form.find("input", attrs={"name": "password"})
        if has_username and has_password:
            return form

    return None


def _solve_hcdn_browser_challenge(
    session: requests.Session,
    response: requests.Response,
) -> requests.Response:
    """Complete Hostinger CDN's JavaScript SHA-256 browser verification."""
    soup = BeautifulSoup(response.text, "html.parser")
    challenge_script = soup.find(
        "script",
        src=lambda value: value and "hcdn-cgi/jschallenge" in value,
    )
    if response.status_code != 403 or not challenge_script:
        return response

    script_url = urljoin(response.url, challenge_script["src"])
    script_response = session.get(
        script_url,
        headers={"Referer": response.url},
        timeout=10,
    )
    script_response.raise_for_status()

    cjs_match = re.search(
        r"""const\s+cjs\s*=\s*(['"])(.*?)\1\s*;""",
        script_response.text,
    )
    endpoint_match = re.search(
        r"""const\s+jsChallengeUrl\s*=\s*(['"])(.*?)\1\s*;""",
        script_response.text,
    )
    uri_match = re.search(
        r"""const\s+uri\s*=\s*(['"])(.*?)\1\s*;""",
        script_response.text,
    )
    if not cjs_match or not endpoint_match:
        raise ValueError(
            "University portal browser verification changed. Please try again later."
        )

    challenge = hashlib.sha256(cjs_match.group(2).encode("utf-8")).hexdigest()
    validation_url = urljoin(response.url, endpoint_match.group(2))
    time.sleep(3)
    validation_response = session.post(
        validation_url,
        data={"challenge": challenge},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": f"{response.url.split('/', 3)[0]}//{response.url.split('/', 3)[2]}",
            "Referer": response.url,
        },
        timeout=10,
    )
    if validation_response.status_code != 200:
        raise ValueError(
            "University portal blocked automated sign-in. Please try again later."
        )

    target_url = uri_match.group(2) if uri_match else response.url
    return session.get(target_url, timeout=10)


def _load_login_page(session: requests.Session):
    response = session.get(BASE_URL, timeout=10)
    response = _solve_hcdn_browser_challenge(session, response)

    soup = BeautifulSoup(response.text, "html.parser")
    login_form = _find_login_form(soup)
    if login_form:
        return response, login_form

    if response.status_code == 403:
        raise ValueError(
            "University portal blocked this login request (HTTP 403). "
            "Please try again later."
        )

    raise ValueError(
        f"University portal login page is unavailable (HTTP {response.status_code})."
    )


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
        response, login_form = _load_login_page(session)
        html_content = response.text

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
