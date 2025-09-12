def fetch_attendance(session: requests.Session, subjects: list):
    """
    Fetch attendance for all subjects.
    Returns a SimpleDataFrame with summary per subject.
    """
    all_summaries = []

    for att_payload in subjects:
        subject_name = att_payload.get("sub_fullname", "Unknown")

        try:
            att_res = session.post(BASE_URL + "studentsubatt.php", data=att_payload)
        except Exception as e:
            # If network fails, still add placeholder entry
            all_summaries.append({
                "Subject": subject_name,
                "Start Date": "N/A",
                "End Date": "N/A",
                "Total Days": 0,
                "No. of Present": 0,
                "No. of Absent": 0,
                "Attendance %": 0,
                "Note": f"Fetch error: {e}"
            })
            continue

        soup = BeautifulSoup(att_res.text, "html.parser")
        table = soup.find("table", class_="table table-bordered table-striped")

        # Case 1: No attendance table
        if not table:
            all_summaries.append({
                "Subject": subject_name,
                "Start Date": "N/A",
                "End Date": "N/A",
                "Total Days": 0,
                "No. of Present": 0,
                "No. of Absent": 0,
                "Attendance %": 0,
                "Note": "No attendance table"
            })
            continue

        # Case 2: Parse attendance rows
        records = []
        for row in table.select("tbody tr"):
            cols = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cols) >= 3:   # Ensure we have enough columns
                date_str, status = cols[0], cols[2]
                records.append((date_str, status))

        if not records:
            all_summaries.append({
                "Subject": subject_name,
                "Start Date": "N/A",
                "End Date": "N/A",
                "Total Days": 0,
                "No. of Present": 0,
                "No. of Absent": 0,
                "Attendance %": 0,
                "Note": "No records"
            })
            continue

        # Extract dates + statuses
        dates, statuses = [], []
        for date_str, status in records:
            try:
                date_obj = datetime.strptime(date_str, "%d-%m-%Y")
                dates.append(date_obj)
                statuses.append(status)
            except ValueError:
                continue

        if not dates:
            all_summaries.append({
                "Subject": subject_name,
                "Start Date": "N/A",
                "End Date": "N/A",
                "Total Days": 0,
                "No. of Present": 0,
                "No. of Absent": 0,
                "Attendance %": 0,
                "Note": "Invalid dates"
            })
            continue

        # Summary stats
        total_days = len(statuses)
        present_count = sum(1 for s in statuses if s.lower() == "present")
        absent_count = total_days - present_count
        attendance_pct = round((present_count / total_days) * 100, 2) if total_days else 0

        all_summaries.append({
            "Subject": subject_name,
            "Start Date": min(dates).strftime("%d-%m-%Y"),
            "End Date": max(dates).strftime("%d-%m-%Y"),
            "Total Days": total_days,
            "No. of Present": present_count,
            "No. of Absent": absent_count,
            "Attendance %": attendance_pct,
            "Note": "OK"
        })

    return SimpleDataFrame(all_summaries)
