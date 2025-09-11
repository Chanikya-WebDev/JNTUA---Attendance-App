import requests
from bs4 import BeautifulSoup
import pandas as pd

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

def fetch_attendance(session: requests.Session, subjects: list) -> pd.DataFrame:
    all_summaries = []

    for att_payload in subjects:
        att_res = session.post(BASE_URL + "studentsubatt.php", data=att_payload)
        soup = BeautifulSoup(att_res.text, "html.parser")
        table = soup.find("table", class_="table table-bordered table-striped")
        
        if not table:
            continue
        
        records = []
        for row in table.select("tbody tr"):
            cols = row.find_all("td")
            if not cols:
                continue
            records.append((cols[0].get_text(strip=True), cols[2].get_text(strip=True)))
        
        if not records:
            continue
        
        df = pd.DataFrame(records, columns=["Date", "Status"])
        df["Date"] = pd.to_datetime(df["Date"], format="%d-%m-%Y")
        
        summary = {
            "Subject": att_payload.get("sub_fullname", "Unknown"),
            "Start Date": df["Date"].min().strftime("%d-%m-%Y"),
            "End Date": df["Date"].max().strftime("%d-%m-%Y"),
            "Total Days": len(df),
            "No. of Present": (df["Status"] == "Present").sum(),
            "No. of Absent": (df["Status"] == "Absent").sum(),
            "Attendance %": round((df["Status"] == "Present").sum() / len(df) * 100, 2)
        }
        all_summaries.append(summary)
    
    return pd.DataFrame(all_summaries)
