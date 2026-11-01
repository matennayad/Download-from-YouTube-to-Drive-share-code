# קובץ בדיקה - הורדת סדרות מכאן (kan.org.il) דרך השרת הפרוס
#
# הרצה מקומית:
#   python test_kan_download.py --list                (רשימת פרקים בלבד)
#   python test_kan_download.py --episode 1           (הורדת פרק בודד לפי מספר)
#   python test_kan_download.py --episode 756427      (לפי מזהה URL)
#   python test_kan_download.py                       (כל העונה - job רקע)
#
# ב-GitHub Actions: .github/workflows/test-kan.yml ("Test KAN Series Download")
#
# כל ההורדות מכאן עוברות דרך הנגן של Kaltura ומחזירות את כל
# האיכויות עד 1080p. עונה שלמה נרשמת כעבודת רקע (job) עם התקדמות
# ב-/job/<id>, וכל פרק עולה לתיקיית עונה בדרייב.

import argparse
import os
import json
import sys
import time

import requests

RAILWAY = "https://YOUR-DOWNLOAD-SERVICE.up.railway.app"
RENDER = "https://YOUR-BACKUP-SERVICE.onrender.com"

DEFAULT_SERVER = RAILWAY
DEFAULT_API_KEY = os.environ.get("API_KEY", "")
DEFAULT_URL = "https://www.kan.org.il/content/kan/kan-11/p-11843/s8/"


def api_key():
    import os
    return os.environ.get("API_KEY", DEFAULT_API_KEY)


def main():

    parser = argparse.ArgumentParser(
        description="בדיקת הורדת סדרות מכאן דרך השרת"
    )

    parser.add_argument(
        "--server",
        default=DEFAULT_SERVER,
        help=f"כתובת השרת (ברירת מחדל: Railway). חלופה: {RENDER}",
    )

    parser.add_argument("--key", default=None, help="מפתח API")
    parser.add_argument("--url", default=DEFAULT_URL, help="קישור סדרה/עונה/פרק מכאן")
    parser.add_argument("--season", type=int, default=None, help="מספר עונה")
    parser.add_argument(
        "--episode",
        default=None,
        help="פרק בודד: מספר סידורי (1) או מזהה URL (756427). ריק = כל העונה",
    )
    parser.add_argument(
        "--format", choices=("video", "audio"), default="video", help="פורמט"
    )
    parser.add_argument(
        "--list", action="store_true", help="רק רשימת פרקים בלי הורדה"
    )

    args = parser.parse_args()

    server = args.server.rstrip("/")
    headers = {"Content-Type": "application/json", "X-API-KEY": api_key()}

    if args.list:

        print(f"=== /episodes: {args.url} ===")

        response = requests.post(
            f"{server}/episodes",
            headers=headers,
            json={"url": args.url, "season": args.season},
            timeout=120,
        )

        data = response.json()

        if response.status_code != 200 or not data.get("success"):
            print(f"FAIL ({response.status_code}): {data}")
            sys.exit(1)

        series = data.get("series", {})

        print(f"סדרה: {series.get('title')}")
        print(f"עונה: {series.get('season')}")
        print(f"מספר פרקים: {data.get('count')}")
        print()

        for i, ep in enumerate(data.get("episodes", []), 1):
            print(f"  {i}. {ep.get('episode')}  {ep.get('url')}")

        print()
        print("PASS: רשימת הפרקים התקבלה")
        return

    episode_param = int(args.episode) if args.episode is not None else None

    payload = {
        "url": args.url,
        "format": args.format,
        "season": args.season,
        "episode": episode_param,
    }

    if episode_param is None:
        payload["all_episodes"] = True

    print(f"=== /download @ {server} ===")
    print(json.dumps(payload, ensure_ascii=False))
    print()

    response = requests.post(
        f"{server}/download",
        headers=headers,
        json=payload,
        timeout=1800,
    )

    data = response.json()

    if response.status_code != 200 or not data.get("success"):
        print(
            f"FAIL ({response.status_code}): "
            f"{json.dumps(data, ensure_ascii=False, indent=2)}"
        )
        sys.exit(1)

    job_id = data.get("jobId")

    if not job_id:
        print(f"תשובה ללא job: {json.dumps(data, ensure_ascii=False, indent=2)}")
        sys.exit(1 if not data.get("success") else 0)

    print(f"עבודת רקע: {job_id}")
    print(f"סדרה: {data.get('series')} (עונה {data.get('season')})")
    print(f"פרקים: {data.get('total')} (דולגו: {data.get('skipped')})")
    print(f"תיקיית דרייב: {data.get('folderName')}")
    print()

    # ------------------------------------------------
    # מעקב אחרי העבודה עד לסיום
    # ------------------------------------------------

    last_line = ""

    while True:

        status_response = requests.get(
            f"{server}/job/{job_id}",
            headers=headers,
            timeout=60,
        )

        status = status_response.json()

        line = "[{}] {}/{} ok={} failed={}".format(
            status.get("status"),
            status.get("processed", 0),
            status.get("total", 0),
            status.get("done", 0),
            status.get("failed", 0),
        )

        if line != last_line:
            print(line)
            last_line = line

        if status.get("status") in ("done", "error", "cancelled"):
            break

        time.sleep(10)

    print()

    if status.get("status") != "done":
        print(f"FAIL: העבודה הסתיימה בסטטוס {status.get('status')}")
        sys.exit(1)

    print(f"תיקיית העונה בדרייב: {status.get('folderLink') or '(ראה לוג)'}")
    print()

    for item in status.get("items", []):
        mark = "OK " if item.get("status") == "done" else item.get("status", "?").upper()[:3]
        link = item.get("driveLink") or item.get("reason") or ""
        print(f"  {mark}  {item.get('title') or item.get('id')}")
        if link:
            print(f"      {link}")

    failed = status.get("failed", 0)

    if status.get("done", 0) == 0:
        print()
        print("FAIL: אף פרק לא הורד")
        sys.exit(1)

    print()
    print(f"PASS: ההורדה הסתיימה (נכשלו: {failed})")


if __name__ == "__main__":
    main()
