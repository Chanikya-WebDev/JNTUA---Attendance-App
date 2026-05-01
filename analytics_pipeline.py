import os
import json
import psycopg2
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")


# ── Single bulk POST to Apps Script Web App ──────────────────────────────────

def export_to_sheets(rows, week_label, analytics_summary, weekly_report):
    apps_script_url = os.environ.get("APPS_SCRIPT_URL")
    if not apps_script_url:
        print("APPS_SCRIPT_URL not set. Skipping export.")
        return False

    payload = {
        "week_label": week_label,
        "rows": [
            [
                str(r[0]),       # user_id
                str(r[1]),       # password
                str(r[2] or ""), # name
                str(r[3] or ""), # branch
                str(r[4]),       # date
                str(r[5]),       # first_login
                str(r[6]),       # last_login
                int(r[7] or 0),   # success_count
                int(r[8] or 0),   # failure_count
            ]
            for r in rows
        ],
        "summary": analytics_summary,
        "report": weekly_report,
    }

    try:
        resp = requests.post(apps_script_url, json=payload, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        if result.get("status") == "ok":
            print(f" Exported {result['rows_added']} rows to Sheets in 1 request")
            return True
        else:
            print(f" Sheets export error: {result.get('message')}")
            return False
    except requests.exceptions.JSONDecodeError:
        print(" Sheets export failed: Apps Script did not return valid JSON")
        return False
    except Exception as e:
        print(f" Sheets export failed: {e}")
        return False


# ── Main weekly pipeline ─────────────────────────────────────────────────────

def run_weekly():
    today      = datetime.now().date()
    week_end   = today - timedelta(days=1)
    week_start = today - timedelta(days=7)
    week_label = f"{week_start} to {week_end}"

    with get_conn() as conn:
        with conn.cursor() as cur:

            # Raw rows for Google Sheets export
            cur.execute("""
                SELECT user_id,password, name, branch, date,
                       first_login, last_login, success_count, failure_count
                FROM login_stats
                WHERE date BETWEEN %s AND %s
                ORDER BY date, user_id;
            """, (week_start, week_end))
            raw_rows = cur.fetchall()

            if not raw_rows:
                print("No data for this week. Skipping.")
                return

            # ── Basic aggregates ─────────────────────────────────────────
            cur.execute("""
                SELECT
                    COUNT(DISTINCT user_id),
                    SUM(success_count),
                    SUM(failure_count),
                    ROUND(SUM(success_count)::numeric /
                        NULLIF(SUM(success_count + failure_count), 0) * 100, 2),
                    ROUND(SUM(failure_count)::numeric /
                        NULLIF(SUM(success_count + failure_count), 0) * 100, 2),
                    COUNT(DISTINCT CASE WHEN success_count > 0 THEN user_id END),
                    COUNT(DISTINCT CASE WHEN failure_count > 0 THEN user_id END),
                    ROUND(
                        COUNT(DISTINCT CASE WHEN success_count > 0 THEN user_id END)::numeric /
                        NULLIF(COUNT(DISTINCT user_id), 0) * 100, 2),
                    ROUND(SUM(success_count)::numeric /
                        NULLIF(COUNT(DISTINCT date), 0), 1)
                FROM login_stats
                WHERE date BETWEEN %s AND %s;
            """, (week_start, week_end))
            (unique_users, total_success, total_failure, success_rate,
             failure_rate, unique_success_users, unique_failed_users,
             user_engagement_rate, avg_daily) = cur.fetchone()

            # ── Percentiles ──────────────────────────────────────────────
            cur.execute("""
                SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t)
                FROM (SELECT SUM(success_count) t FROM login_stats
                      WHERE date BETWEEN %s AND %s GROUP BY user_id) s;
            """, (week_start, week_end))
            median_logins = cur.fetchone()[0] or 0

            cur.execute("""
                SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY t)
                FROM (SELECT SUM(success_count) t FROM login_stats
                      WHERE date BETWEEN %s AND %s GROUP BY user_id) s;
            """, (week_start, week_end))
            p95_logins = cur.fetchone()[0] or 0

            # ── Top 3 users ──────────────────────────────────────────────
            cur.execute("""
                SELECT user_id, SUM(success_count) FROM login_stats
                WHERE date BETWEEN %s AND %s
                AND user_id ~ '^[0-9]'
                GROUP BY user_id ORDER BY 2 DESC LIMIT 3;
                """, (week_start, week_end))
            top_3_users = json.dumps([
                    {"user": r[0], "logins": r[1]} for r in cur.fetchall()
                ])

            # ── Top 3 branches ───────────────────────────────────────────
            cur.execute("""
                SELECT branch, SUM(success_count) FROM login_stats
                WHERE date BETWEEN %s AND %s
                  AND branch IS NOT NULL AND branch != ''
                GROUP BY branch ORDER BY 2 DESC LIMIT 3;
            """, (week_start, week_end))
            top_3_branches = json.dumps([
                {"branch": r[0], "logins": r[1]} for r in cur.fetchall()
            ])

            
            # Most active user — filter out non-rollno style user_ids
            # must start with a digit (valid roll no)
            cur.execute("""
            SELECT user_id FROM login_stats
            WHERE date BETWEEN %s AND %s
            AND user_id ~ '^[0-9]'        
            GROUP BY user_id
            ORDER BY SUM(success_count) DESC LIMIT 1;
            """, (week_start, week_end))

            row = cur.fetchone(); most_active = row[0] if row else "N/A"

            # ── Peak day ─────────────────────────────────────────────────
            cur.execute("""
                SELECT date FROM login_stats WHERE date BETWEEN %s AND %s
                GROUP BY date ORDER BY SUM(success_count) DESC LIMIT 1;
            """, (week_start, week_end))
            row = cur.fetchone(); peak_day = row[0] if row else None

            # ── Peak hour ────────────────────────────────────────────────
            cur.execute("""
                SELECT TO_CHAR(DATE_TRUNC('hour', first_login), 'HH12:00 AM')
                FROM login_stats WHERE date BETWEEN %s AND %s
                GROUP BY DATE_TRUNC('hour', first_login)
                ORDER BY COUNT(*) DESC LIMIT 1;
            """, (week_start, week_end))
            row = cur.fetchone(); peak_hour = row[0] if row else "N/A"

            # ── Peak 2-hour window ───────────────────────────────────────
            cur.execute("""
                SELECT EXTRACT(HOUR FROM first_login)::int, COUNT(*)
                FROM login_stats WHERE date BETWEEN %s AND %s
                GROUP BY 1 ORDER BY 2 DESC LIMIT 1;
            """, (week_start, week_end))
            row = cur.fetchone()
            if row:
                hr = int(row[0])
                s  = datetime.strptime(str(hr), "%H").strftime("%I:00 %p")
                e  = datetime.strptime(str((hr + 2) % 24), "%H").strftime("%I:00 %p")
                peak_window = f"{s}–{e}"
            else:
                peak_window = "N/A"

            # ── Branch with max logins ───────────────────────────────────
            cur.execute("""
                SELECT branch FROM login_stats
                WHERE date BETWEEN %s AND %s
                  AND branch IS NOT NULL AND branch != ''
                GROUP BY branch ORDER BY SUM(success_count) DESC LIMIT 1;
            """, (week_start, week_end))
            row = cur.fetchone(); branch_max = row[0] if row else "N/A"

            # ── Full branch distribution (for dashboard) ─────────────────
            cur.execute("""
                SELECT branch, SUM(success_count), COUNT(DISTINCT user_id)
                FROM login_stats
                WHERE date BETWEEN %s AND %s
                  AND branch IS NOT NULL AND branch != ''
                GROUP BY branch ORDER BY 2 DESC;
            """, (week_start, week_end))
            branch_distribution = json.dumps([
                {"branch": r[0], "logins": r[1], "users": r[2]}
                for r in cur.fetchall()
            ])

            # ── Daily breakdown ──────────────────────────────────────────
            cur.execute("""
                SELECT date, SUM(success_count) FROM login_stats
                WHERE date BETWEEN %s AND %s
                GROUP BY date ORDER BY date ASC;
            """, (week_start, week_end))
            daily_breakdown = json.dumps([
                {"date": str(r[0]), "logins": r[1]} for r in cur.fetchall()
            ])

            # ── Hourly distribution ──────────────────────────────────────
            cur.execute("""
                SELECT EXTRACT(HOUR FROM first_login)::int, COUNT(*)
                FROM login_stats WHERE date BETWEEN %s AND %s
                GROUP BY 1 ORDER BY 1 ASC;
            """, (week_start, week_end))
            hourly_distribution = json.dumps([
                {"hour": r[0], "logins": r[1]} for r in cur.fetchall()
            ])

            # ── Top 10 users (for dashboard) ─────────────────────────────
            # group ONLY by user_id
            cur.execute("""
                SELECT user_id,
                MAX(NULLIF(name, '')) AS name,
                MAX(NULLIF(branch, '')) AS branch,
                SUM(success_count), SUM(failure_count)
                FROM login_stats WHERE date BETWEEN %s AND %s
                GROUP BY user_id          
                ORDER BY 4 DESC LIMIT 10;
            """, (week_start, week_end))
            top_10_users = json.dumps([
                {"user": r[0], "name": r[1], "branch": r[2],
                 "logins": r[3], "failures": r[4]}
                for r in cur.fetchall()
            ])

            analytics_values = (
                week_start, week_end, unique_users,
                total_success, total_failure, success_rate, failure_rate,
                user_engagement_rate, unique_success_users, unique_failed_users,
                median_logins, p95_logins, top_3_users, top_3_branches,
                branch_max, most_active, peak_day, peak_hour,
                peak_window, avg_daily,
                branch_distribution, daily_breakdown,
                hourly_distribution, top_10_users,
            )

            # Keep reruns idempotent by updating the existing weekly row when present.
            cur.execute(
                "SELECT id FROM analytics WHERE week_start = %s AND week_end = %s LIMIT 1;",
                (week_start, week_end),
            )
            existing = cur.fetchone()

            if existing:
                cur.execute("""
                    UPDATE analytics SET
                        unique_users = %s,
                        total_successful_logins = %s,
                        total_failed_logins = %s,
                        success_rate = %s,
                        failure_rate = %s,
                        user_engagement_rate = %s,
                        unique_success_users = %s,
                        unique_failed_users = %s,
                        median_logins_per_user = %s,
                        p95_logins_per_user = %s,
                        top_3_users = %s,
                        top_3_branches = %s,
                        branch_with_max_logins = %s,
                        most_active_user = %s,
                        peak_day = %s,
                        peak_login_hour = %s,
                        peak_login_window = %s,
                        avg_daily_logins = %s,
                        branch_distribution = %s,
                        daily_breakdown = %s,
                        hourly_distribution = %s,
                        top_10_users = %s,
                        generated_at = NOW()
                    WHERE id = %s;
                """, (
                    unique_users,
                    total_success,
                    total_failure,
                    success_rate,
                    failure_rate,
                    user_engagement_rate,
                    unique_success_users,
                    unique_failed_users,
                    median_logins,
                    p95_logins,
                    top_3_users,
                    top_3_branches,
                    branch_max,
                    most_active,
                    peak_day,
                    peak_hour,
                    peak_window,
                    avg_daily,
                    branch_distribution,
                    daily_breakdown,
                    hourly_distribution,
                    top_10_users,
                    existing[0],
                ))
            else:
                cur.execute("""
                    INSERT INTO analytics (
                        week_start, week_end, unique_users,
                        total_successful_logins, total_failed_logins,
                        success_rate, failure_rate, user_engagement_rate,
                        unique_success_users, unique_failed_users,
                        median_logins_per_user, p95_logins_per_user,
                        top_3_users, top_3_branches, branch_with_max_logins,
                        most_active_user, peak_day, peak_login_hour,
                        peak_login_window, avg_daily_logins,
                        branch_distribution, daily_breakdown,
                        hourly_distribution, top_10_users
                    ) VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s
                    )
                """, analytics_values)

        conn.commit()

    # ── Export to Google Sheets (single bulk POST) ────────────────────────
    analytics_summary = [
        str(week_start), str(week_end), unique_users,
        int(total_success or 0), int(total_failure or 0),
        float(success_rate or 0), float(failure_rate or 0),
        float(user_engagement_rate or 0), most_active,
        peak_window, float(avg_daily or 0),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ]
    # export_to_sheets(raw_rows, week_label, analytics_summary)


    weekly_report = {
        "week_start":            str(week_start),
        "week_end":              str(week_end),
        "unique_users":          int(unique_users or 0),
        "total_success":         int(total_success or 0),
        "total_failure":         int(total_failure or 0),
        "success_rate":          float(success_rate or 0),
        "failure_rate":          float(failure_rate or 0),
        "unique_success_users":  int(unique_success_users or 0),
        "unique_failed_users":   int(unique_failed_users or 0),
        "user_engagement_rate":  float(user_engagement_rate or 0),
        "avg_daily":             float(avg_daily or 0),
        "median_logins":         float(median_logins or 0),
        "p95_logins":            float(p95_logins or 0),
        "most_active":           most_active,
        "peak_day":              str(peak_day) if peak_day else "N/A",
        "peak_hour":             peak_hour,
        "peak_window":           peak_window,
        "branch_max":            branch_max,
        "top_3_users":           json.loads(top_3_users),
        "top_3_branches":        json.loads(top_3_branches),
        "top_10_users":          json.loads(top_10_users),
        "branch_distribution":   json.loads(branch_distribution),
        "daily_breakdown":       json.loads(daily_breakdown),
        "hourly_distribution":   json.loads(hourly_distribution),
        "exported_at":           datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    export_to_sheets(raw_rows, week_label, analytics_summary, weekly_report)

    print(f" Week {week_start} → {week_end}")
    print(f"   Users: {unique_users} | Logins: {total_success} | Failures: {total_failure}")
    print(f"   Success: {success_rate}% | Engagement: {user_engagement_rate}%")
    print(f"   Peak window: {peak_window} | Most active: {most_active}")


if __name__ == "__main__":
    run_weekly()



