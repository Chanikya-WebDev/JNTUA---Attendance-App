import requests
from bs4 import BeautifulSoup
from datetime import datetime

BASE_URL = "https://jntuaceastudents.classattendance.in/"

def login(username: str, password: str) -> requests.Session:
    session = requests.Session()
    login_page = session.get(BASE_URL)
    soup = BeautifulSoup(login_page.text, "html.parser")
    secretcode = soup.find("input", {"name": "secretcode"})["value"]
    
    payload = {"username": username, "password": password, "secretcode": secretcode}
    res = session.post(BASE_URL, data=payload)
    
    if "studenthome.php" not in res.url:
        raise ValueError("Login failed. Check username/password.")
    
    return session

def get_student_details(session: requests.Session) -> dict:
    home_res = session.get(BASE_URL + "studenthome.php")
    soup = BeautifulSoup(home_res.text, "html.parser")
    
    details = {}
    for card in soup.find_all("div", class_="card"):
        header = card.find("div", class_="card-header")
        if header and "My Details" in header.get_text(strip=True):
            for li in card.find_all("li", class_="list-group-item"):
                key = li.find("strong").get_text(strip=True).replace(":", "")
                value = li.get_text(strip=True).replace(li.find("strong").get_text(), "").strip()
                details[key] = value
            break
    
    details["student_id"] = soup.find("input", {"name": "student_id"})["value"]
    details["class_id"] = soup.find("input", {"name": "class_id"})["value"]
    details["classname"] = soup.find("input", {"name": "classname"})["value"]
    details["acad_year"] = soup.find("input", {"name": "acad_year"})["value"]
    
    return details

def get_subjects(session: requests.Session, student_info: dict) -> list:
    payload = {
        "student_id": student_info["student_id"],
        "class_id": student_info["class_id"],
        "classname": student_info["classname"],
        "acad_year": student_info["acad_year"]
    }
    res = session.post(BASE_URL + "studentsubjects.php", data=payload)
    soup = BeautifulSoup(res.text, "html.parser")
    
    subjects = []
    for form in soup.find_all("form", {"id": True}):
        subject_data = {}
        for inp in form.find_all("input", {"type": "hidden"}):
            subject_data[inp["name"]] = inp.get("value", "")
        subjects.append(subject_data)
    
    return subjects

class SimpleDataFrame:
    
    def __init__(self, data):
        self.data = data
    
    def to_dict(self, orient="records"):
        if orient == "records":
            return self.data
        return self.data
    
    def __getitem__(self, key):
        return [row[key] for row in self.data]
    
    def sum_column(self, column):
        # Only sum numeric values, skip "N/A" or non-numeric entries
        return sum(row[column] for row in self.data if isinstance(row[column], (int, float)))

def fetch_attendance(session: requests.Session, subjects: list):
    all_summaries = []

    for att_payload in subjects:
        att_res = session.post(BASE_URL + "studentsubatt.php", data=att_payload)
        soup = BeautifulSoup(att_res.text, "html.parser")
        table = soup.find("table", class_="table table-bordered table-striped")
        
        if table:
            records = []
            for row in table.select("tbody tr"):
                cols = row.find_all("td")
                if not cols:
                    continue
                records.append((cols[0].get_text(strip=True), cols[2].get_text(strip=True)))
            
            dates, statuses = [], []
            for date_str, status in records:
                try:
                    date_obj = datetime.strptime(date_str, "%d-%m-%Y")
                    dates.append(date_obj)
                    statuses.append(status)
                except ValueError:
                    continue
            
            total_days = len(statuses)
            present_count = sum(1 for status in statuses if status == "Present")
            absent_count = total_days - present_count
            attendance_pct = round((present_count / total_days) * 100, 1) if total_days > 0 else 0

            end_date_str = max(dates).strftime("%d-%m-%Y") if dates else None
            end_date_warning = False
            if end_date_str:
                try:
                    end_date_obj = datetime.strptime(end_date_str, "%d-%m-%Y")
                    days_diff = (datetime.now() - end_date_obj).days
                    if days_diff > 30:
                        end_date_warning = True
                except Exception:
                    pass
            summary = {
                "Subject": att_payload.get("sub_fullname", "Unknown"),
                "Start Date": min(dates).strftime("%d-%m-%Y") if dates else None,
                "End Date": end_date_str,
                "Total Days": total_days if dates else 0,
                "No. of Present": present_count if dates else 0,
                "No. of Absent": absent_count if dates else 0,
                "Attendance %": attendance_pct if dates else 0,
                "End Date Warning": end_date_warning
            }
        else:
            # If table not found, store None/0 values
            summary = {
                "Subject": att_payload.get("sub_fullname", "Unknown"),
                "Start Date": None,
                "End Date": None,
                "Total Days": 0,
                "No. of Present": 0,
                "No. of Absent": 0,
                "Attendance %": 0,
                "End Date Warning": False
            }
        
        all_summaries.append(summary)
    
    return SimpleDataFrame(all_summaries)