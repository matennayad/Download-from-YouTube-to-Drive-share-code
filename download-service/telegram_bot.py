"""
telegram_bot.py
===============
בוט טלגרם להורדות יוטיוב/מאקו/כאן ל-Drive, כולל /record להקלטת שידור חי.

דפוס הרצה: תהליך-בן של app.py (בדיוק כמו telegram_songs_to_drive.py).
הבוט לא מוריד בעצמו — הוא קורא ל-Flask המקומי על 127.0.0.1:$PORT
עם X-API-KEY, וכך משתמש באותו מנוע הורדה, באותם עובדים ובאותן משימות.

הרשאות: נמעני העלאות המייל המאושרים (טור "נשלח אל" בגיליון המאושרים)
או מנהלים מ-TELEGRAM_ADMIN_IDS. משתמש חדש מאושר ב-/link עם קוד חד-פעמי.

הרצה ידנית לבדיקה:
  TELEGRAM_BOT_TOKEN=... API_KEY=... python3 telegram_bot.py
"""

import base64
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import traceback
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from drive_bridge import bridge_credentials

# ============================================================
# CONFIGURATION (משתני סביבה)
# ============================================================

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# ה-API הפנימי — loopback על אותו PORT של השרת
INTERNAL_BASE = "http://127.0.0.1:" + str(
    int(os.environ.get("PORT", "8080"))
)

# מפתח ה-API של השרת (אותו ערך שכבר מוגדר ב-Railway)
API_KEY = os.environ.get("API_KEY", "")

# מנהלים לפי מזהה טלגרם מספרי (פסיקים), למשל "123456789"
ADMIN_IDS = {
    int(x)
    for x in re.split(
        r"[\s,]+", os.environ.get("TELEGRAM_ADMIN_IDS", "").strip()
    )
    if x.strip()
}

# גיליון המאושרים — אותו מקור אמת של ה-Apps Script
APPROVED_SHEET_ID = os.environ.get(
    "APPROVED_SHEET_ID",
    "",  # מזהה הגיליון של מערכת ההורדות - להגדיר במשתני הסביבה
)
APPROVED_TAB_NAME = os.environ.get("APPROVED_TAB_NAME", "מאושרים")

# ערוצי שידור חי: "שם=כתובת" מופרדים בפסיק-נקודה-פסיק.
# ברירת מחדל: קשת 12 (HLS פתוח ללא DRM נכון להיום).
DEFAULT_LIVE = "12=https://mako-streaming.akamaized.net/direct/hls/live/20000821/k12ni-bu/index.m3u8"
LIVE_CHANNELS = {}
for _item in os.environ.get("TELEGRAM_LIVE_CHANNELS", DEFAULT_LIVE).split(";"):
    if "=" in _item:
        _k, _v = _item.split("=", 1)
        if _k.strip() and _v.strip():
            LIVE_CHANNELS[_k.strip()] = _v.strip()

# תזמון הקלטות: "HH:MM=דקות=ערוץ;..." (אופציונלי)
RECORD_SCHEDULES = [
    s.strip()
    for s in os.environ.get("TELEGRAM_RECORD_SCHEDULES", "").split(";")
    if s.strip()
]

# הגבלות הקלטה
RECORD_MAX_MINUTES = int(os.environ.get("RECORD_MAX_MINUTES", "180"))
RECORD_DIR = os.path.join(tempfile.gettempdir(), "tgbot_records")

# ערוצי שירים: "TELEGRAM_SONGS_CHANNELS=@songs,@new_music"
# הבוט חייב להיות מנהל בערוץ. כל פוסט עם שמע יורד אוטומטית ל-Drive.
# הגבלת Bot API: הורדת קבצים עד 20MB (מספיק לרוב ה-mp3).
SONGS_CHANNELS = {
    c.strip().lower().lstrip("@")
    for c in os.environ.get("TELEGRAM_SONGS_CHANNELS", "").split(",")
    if c.strip()
}
SONGS_DIR = os.path.join(tempfile.gettempdir(), "tgbot_songs")
SONGS_MAX_MB = 20
SONGS_SEEN = set()

# תקרה על כמה קבצים יורדים במקביל. בלי זה, העברה של 100 שירים לבוט
# הייתה פותחת 100 הורדות בו-זמנית ומפילה את הקונטיינר.
_MEDIA_SEM = threading.Semaphore(3)

# תיקיית Drive להעלאות (אופציונלי) — כמו ב-app.py
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID", "")
def _clean_env(name):
    # ערכים שמודבקים ב-Railway מגיעים לפעמים עם רווח, ירידת שורה או
    # מרכאות מסביב - וגוגל דוחה אז את הטוקן כאילו הוא לא תקין.
    return os.environ.get(name, "").strip().strip('"\'').strip()


GOOGLE_OAUTH_CLIENT_ID = _clean_env("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = _clean_env("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_OAUTH_REFRESH_TOKEN = _clean_env("GOOGLE_OAUTH_REFRESH_TOKEN")
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# פורט בריאות פנימי (0 = כבוי)
HEALTH_PORT = int(os.environ.get("TELEGRAM_BOT_HEALTH_PORT", "8082"))

# יצירת תמונות דרך ה-API הרשמי של גוגל (/img <תיאור>)
# GEMINI_API_KEY - מפתח חינמי מ-https://aistudio.google.com/apikey
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_IMAGE_MODEL = os.environ.get(
    "GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image"
)
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

LINK_TTL_SECONDS = 2 * 3600  # תוקף קוד /link
STOP = threading.Event()

# ============================================================
# STATE
# ============================================================

STATE_LOCK = threading.Lock()
STATE = {
    "started_at": datetime.now().isoformat(timespec="seconds"),
    "approved_count": 0,
    "linked_users": 0,
    "downloads_started": 0,
    "records_done": 0,
    "songs_uploaded": 0,
    "errors_total": 0,
}

# אישורי משתמשים: telegram_id -> {"email": ..., "name": ...}
LINKS = {}
LINKS_FILE = os.path.join(tempfile.gettempdir(), "tgbot_links.json")

# קודי /link פעילים: code -> {"email", "ts", "used"}
PENDING_CODES = {}

# הקלטות פעילות: chat_id -> {"proc", "path", "channel", "started", "minutes"}
RECORDINGS = {}
RECORDINGS_LOCK = threading.Lock()

# ריצות הורדה פעילות: chat_id -> {"job_id", "url", ...}
ACTIVE_DL = {}
ACTIVE_DL_LOCK = threading.Lock()

_last_status_edit = {}


def state_inc(key, amount=1):
    with STATE_LOCK:
        STATE[key] = STATE.get(key, 0) + amount


def state_set(key, value):
    with STATE_LOCK:
        STATE[key] = value


# ============================================================
# APPROVED LIST (קריאה בלבד דרך gviz, כמו ה-Apps Script)
# ============================================================

_approved_cache = {"emails": set(), "fetched_at": 0.0}
_APPROVED_TTL = 3600.0


def _normalize_email(email):
    e = (email or "").strip().lower()
    if e.endswith("@gmail.com"):
        local = e.split("@", 1)[0].replace(".", "")
        return local + "@gmail.com"
    return e


def get_approved_emails(max_age=_APPROVED_TTL):
    """מחזיר קבוצת המיילים המאושרים מגיליון המאושרים (עם קאש שעה)."""
    now = time.time()
    if now - _approved_cache["fetched_at"] < max_age:
        return _approved_cache["emails"]

    try:
        gviz_url = (
            "https://docs.google.com/spreadsheets/d/"
            + APPROVED_SHEET_ID
            + "/gviz/tq?tqx=out:csv&sheet="
            + urllib.parse.quote(APPROVED_TAB_NAME)
        )
        resp = requests.get(gviz_url, timeout=20)
        resp.raise_for_status()
        import csv
        import io

        rows = list(csv.reader(io.StringIO(resp.text)))
        col = None
        if rows:
            header = rows[0]
            for i, cell in enumerate(header):
                if "נשלח" in cell or "mail" in cell.lower():
                    col = i
                    break
        emails = set()
        for row in rows[1:]:
            if col is not None and col < len(row):
                e = _normalize_email(row[col])
                if "@" in e:
                    emails.add(e)
            else:
                for cell in row:
                    e = _normalize_email(cell)
                    if "@" in e:
                        emails.add(e)
        if emails:
            _approved_cache["emails"] = emails
            _approved_cache["fetched_at"] = now
            state_set("approved_count", len(emails))
        return _approved_cache["emails"]
    except Exception as e:
        print("[tgbot] approved-list load failed:", e, flush=True)
        return _approved_cache["emails"]


def load_links():
    global LINKS
    try:
        with open(LINKS_FILE, "r", encoding="utf-8") as f:
            LINKS = json.load(f)
    except Exception:
        LINKS = {}
    state_set("linked_users", len(LINKS))


def save_links():
    try:
        with open(LINKS_FILE, "w", encoding="utf-8") as f:
            json.dump(LINKS, f, ensure_ascii=False, indent=1)
    except Exception as e:
        print("[tgbot] save_links failed:", e, flush=True)


def is_admin(tg_id):
    return int(tg_id) in ADMIN_IDS


def get_linked_email(tg_id):
    entry = LINKS.get(str(tg_id)) or {}
    return entry.get("email")


def user_allowed(tg_id, username):
    """מנהל, או משתמש שקושר למייל מאושר (או שהמייל שלו עדיין בגיליון)."""
    if is_admin(tg_id):
        return True
    email = get_linked_email(tg_id)
    if email:
        # אם המייל הוסר מהגיליון - ההרשאה נשללת (בדיקה מהקאש העדכני)
        approved = get_approved_emails()
        if approved and _normalize_email(email) not in approved:
            return False
        return True
    return False


# ============================================================
# TELEGRAM API (Bot API דרך requests, ללא ספריות נוספות)
# ============================================================

TG_BASE = "https://api.telegram.org"


# שגיאת ה-API האחרונה (לגיבוי שליחה כטקסט רגיל כשה-HTML נדחה)
_last_tg_error = ""


def tg_call(method, max_retries=3, **params):
    """קריאה ל-Bot API עם טיפול ב-429 וניסיונות חוזרים."""
    global _last_tg_error
    url = "%s/bot%s/%s" % (TG_BASE, BOT_TOKEN, method)
    # טלגרם דוחה פרמטרים אופציונליים שנשלחים כ-null (למשל reply_markup) -
    # לכן משמיטים אותם לגמרי במקום לשלוח null.
    params = {k: v for k, v in params.items() if v is not None}
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=params, timeout=35)
            data = resp.json()
            if data.get("ok"):
                result = data.get("result")
                _last_tg_error = ""
                if method == "sendMessage" and isinstance(result, dict):
                    print(
                        "[tgbot] sent chat=%s msg_id=%s text=%s"
                        % (
                            params.get("chat_id"),
                            result.get("message_id"),
                            str(params.get("text", ""))[:40].replace("\n", " "),
                        ),
                        flush=True,
                    )
                return result
            desc = data.get("description", "")
            retry_after = (data.get("parameters") or {}).get("retry_after")
            if resp.status_code == 429 and retry_after:
                time.sleep(min(retry_after + 1, 30))
                continue
            print("[tgbot] %s error: %s" % (method, desc), flush=True)
            _last_tg_error = desc
            return None
        except Exception as e:
            print("[tgbot] %s attempt %d failed: %s" % (method, attempt + 1, e), flush=True)
            time.sleep(2)
    return None


_HTML_TAG_RE = re.compile(r"</?(?:b|i|u|s|code|pre|a|tg-spoiler)(?:\s[^>]*)?>")


def _plain_text(text):
    """מסיר תגי HTML ומפענח ישויות - לגיבוי כשטלגרם דוחה את ה-HTML."""
    out = _HTML_TAG_RE.sub("", text or "")
    for entity, char in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&amp;", "&")):
        out = out.replace(entity, char)
    return out


def send_message(chat_id, text, reply_markup=None):
    result = tg_call(
        "sendMessage",
        chat_id=chat_id,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=reply_markup,
    )
    if result is None and "parse entities" in _last_tg_error.lower():
        # רשת ביטחון: טקסט שמכיל < > מילוליים נדחה כ-HTML - שולחים בלי עיצוב
        print(
            "[tgbot] HTML rejected (%s) - retrying as plain text" % _last_tg_error,
            flush=True,
        )
        result = tg_call(
            "sendMessage",
            chat_id=chat_id,
            text=_plain_text(text),
            disable_web_page_preview=True,
            reply_markup=reply_markup,
        )
    if result is None and reply_markup is not None and "reply markup" in _last_tg_error.lower():
        # רשת ביטחון: מקלדת פגומה - שולחים בלי מקלדת במקום לאבד את ההודעה
        print(
            "[tgbot] reply_markup rejected (%s) - retrying without markup" % _last_tg_error,
            flush=True,
        )
        result = tg_call(
            "sendMessage",
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    return result


def edit_message(chat_id, message_id, text, reply_markup=None):
    now = time.time()
    key = "%s:%s" % (chat_id, message_id)
    # הגבלת קצב: לא יותר מעדכון כל 3 שניות להודעה
    if now - _last_status_edit.get(key, 0) < 3:
        return
    _last_status_edit[key] = now
    return tg_call(
        "editMessageText",
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=reply_markup,
    )


def notify_admins(text):
    for admin_id in ADMIN_IDS:
        send_message(admin_id, text)


# ============================================================
# INTERNAL API (127.0.0.1:$PORT - אותו שרת Flask)
# ============================================================


def api_get(path, params=None):
    resp = requests.get(
        INTERNAL_BASE + path,
        params=params or {},
        headers={"X-API-KEY": API_KEY},
        timeout=60,
    )
    return resp.json()


def api_post(path, payload):
    resp = requests.post(
        INTERNAL_BASE + path,
        json=payload,
        headers={"X-API-KEY": API_KEY},
        timeout=60,
    )
    return resp.json()


def start_download(chat_id, url, fmt="audio", email=None):
    """שולח קישור ל-/download הפנימי ומחזיר (job_id או None, drive_link, שגיאה)."""
    try:
        data = api_post("/download", {"url": url, "format": fmt})
    except Exception as e:
        return None, None, "השרת לא עונה: %s" % e
    if not data.get("success"):
        return None, None, data.get("error") or "שגיאה לא ידועה"
    drive_link = data.get("driveLink")
    job_id = data.get("jobId")
    return job_id, drive_link, None


def watch_job(chat_id, message_id, job_id):
    """עוקב אחרי משימה ומעדכן את ההודעה בטלגרם עד לסיום."""
    last_text = ""
    while not STOP.is_set():
        try:
            # items=0: לא למשוך את רשימת הפריטים המלאה בכל סקר
            data = api_get("/job/" + job_id, {"items": "0"})
        except Exception as e:
            print("[tgbot] job poll failed:", e, flush=True)
            time.sleep(5)
            continue
        if not data.get("success"):
            break
        status = data.get("status")
        pct = data.get("percent", 0)
        done = data.get("done", 0)
        total = data.get("total", 0)
        failed = data.get("failed", 0)
        bar = "#" * int(pct / 10) + "." * (10 - int(pct / 10))
        text = (
            "⏳ <b>%d%%</b> [%s]\n"
            "✅ %d / %d   ❌ %d\n"
            "<code>%s</code>"
        ) % (pct, bar, done, total, failed, (data.get("current") or "")[:80])
        if text != last_text:
            edit_message(chat_id, message_id, text)
            last_text = text
        if status in ("done", "completed", "finished", "success"):
            folder = data.get("folderLink")
            send_message(
                chat_id,
                "🎉 המשימה הסתיימה!\n✅ %d ירדו, ❌ %d נכשלו%s"
                % (
                    done,
                    failed,
                    ("\n📁 " + folder) if folder else "",
                ),
            )
            return
        if status in ("cancelled", "canceled"):
            edit_message(chat_id, message_id, "🚫 המשימה בוטלה.")
            return
        if status in ("failed", "error"):
            edit_message(
                chat_id,
                message_id,
                "❌ המשימה נכשלה: %s" % (data.get("error") or "?"),
            )
            return
        time.sleep(5)


def handle_download_command(chat_id, url, fmt, email):
    """מריץ הורדה ומנהל את הודעת ההתקדמות. רץ ב-thread."""
    send_message(chat_id, "מקבל את הקישור…")
    job_id, drive_link, error = start_download(chat_id, url, fmt, email)
    if error:
        send_message(chat_id, "❌ " + str(error)[:400])
        return
    if drive_link:
        shared = share_drive_url(drive_link, email)
        send_message(
            chat_id,
            "🎉 הקובץ מוכן ב-Drive!\n"
            + drive_link
            + ("\n🔗 שותף למייל שלך" if shared else ""),
        )
        return
    if not job_id:
        send_message(chat_id, "❌ לא התקבל מזהה משימה מהשרת.")
        return
    sent = send_message(chat_id, "⏳ המשימה התקבלה, מתחיל…")
    with ACTIVE_DL_LOCK:
        ACTIVE_DL[str(chat_id)] = {"job_id": job_id, "url": url}
    try:
        watch_job(chat_id, sent["message_id"], job_id)
    finally:
        with ACTIVE_DL_LOCK:
            ACTIVE_DL.pop(str(chat_id), None)


# ============================================================
# DRIVE (העלאת הקלטות + שיתוף עם מייל מאושר)
# ============================================================

_drive_svc = None
_drive_lock = threading.Lock()


def get_drive_service():
    global _drive_svc
    with _drive_lock:
        if _drive_svc is not None:
            return _drive_svc
        # קודם גשר ה-Apps Script, ואם אינו זמין - ה-refresh token
        try:
            creds = bridge_credentials(os.environ.get("API_KEY", ""))
            if creds is not None:
                _drive_svc = build("drive", "v3", credentials=creds)
                return _drive_svc
        except Exception as e:
            print("[tgbot] Drive bridge failed, using refresh token:", e, flush=True)
            if not GOOGLE_OAUTH_REFRESH_TOKEN:
                raise
        creds = Credentials(
            refresh_token=GOOGLE_OAUTH_REFRESH_TOKEN,
            client_id=GOOGLE_OAUTH_CLIENT_ID,
            client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=DRIVE_SCOPES,
        )
        creds.refresh(GoogleAuthRequest())
        _drive_svc = build("drive", "v3", credentials=creds)
        return _drive_svc


def share_drive_file(file_id, email):
    """שיתוף קובץ/תיקייה עם מייל (כמו share_with_email ב-app.py)."""
    if not file_id or not email:
        return False
    try:
        svc = get_drive_service()
        svc.permissions().create(
            fileId=file_id,
            body={"role": "reader", "type": "user", "emailAddress": email},
            sendNotificationEmail=False,
        ).execute()
        return True
    except Exception as e:
        print("[tgbot] share failed:", e, flush=True)
        return False


def share_drive_url(url, email):
    """חילוץ מזהה הקובץ מקישור Drive ושיתוף."""
    if not url or not email:
        return False
    m = re.search(r"/d/([A-Za-z0-9_-]{10,})", url) or re.search(
        r"[?&]id=([A-Za-z0-9_-]{10,})", url
    )
    if not m:
        return False
    return share_drive_file(m.group(1), email)


def upload_to_drive(local_path, filename):
    """העלאת קובץ ל-Drive, מחזיר קישור."""
    svc = get_drive_service()
    metadata = {"name": filename}
    if DRIVE_FOLDER_ID:
        metadata["parents"] = [DRIVE_FOLDER_ID]
    media = MediaFileUpload(local_path, resumable=True)
    uploaded = (
        svc.files()
        .create(body=metadata, media_body=media, fields="id, webViewLink")
        .execute()
    )
    return uploaded.get("webViewLink"), uploaded.get("id")


# ============================================================
# יצירת תמונות (/img - Gemini API) והעלאה ישירה ל-Drive
# ============================================================


def gemini_generate_image(prompt):
    """יוצר תמונה דרך ה-API הרשמי של גוגל. מחזיר בייטים של PNG.
    השרת (Railway) מדבר עם גוגל ישירות - בלי דפדפן, בלי סינון,
    בלי תלות באינטרנט של המשתמש."""
    resp = requests.post(
        "%s/models/%s:generateContent" % (GEMINI_API_BASE, GEMINI_IMAGE_MODEL),
        params={"key": GEMINI_API_KEY},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        },
        timeout=180,
    )
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError("תשובה לא תקינה מגוגל (HTTP %s)" % resp.status_code)

    if resp.status_code != 200:
        msg = (data.get("error") or {}).get("message") or (
            "HTTP %s" % resp.status_code
        )
        raise RuntimeError("גוגל דחתה את הבקשה: %s" % msg)

    candidates = data.get("candidates") or []
    parts = (
        ((candidates[0].get("content") or {}).get("parts")) or []
        if candidates
        else []
    )
    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            return base64.b64decode(inline["data"])

    # אין תמונה - ייתכן שהמודל סירב (בטיחות) או החזיר טקסט בלבד
    text = "".join(
        p.get("text", "") for p in parts if isinstance(p, dict)
    ).strip()
    if text:
        raise RuntimeError("המודל החזיר טקסט במקום תמונה: %s" % text[:200])
    raise RuntimeError("המודל לא החזיר תמונה - נסה ניסוח אחר")


def send_photo(chat_id, png_path, caption=""):
    """שליחת תמונה לטלגרם (multipart - ה-json הרגיל לא מתאים לקבצים)."""
    try:
        with open(png_path, "rb") as f:
            requests.post(
                "%s/bot%s/sendPhoto" % (TG_BASE, BOT_TOKEN),
                data={
                    "chat_id": str(chat_id),
                    "caption": (caption or "")[:1024],
                    "parse_mode": "HTML",
                },
                files={"photo": ("image.png", f, "image/png")},
                timeout=120,
            )
    except Exception as e:
        print("[tgbot] sendPhoto failed:", e, flush=True)


def img_worker(chat_id, prompt, email):
    """יוצר את התמונה, מעלה ל-Drive ושולח חזרה תצוגה + קישור."""
    tmp_path = ""
    try:
        png = gemini_generate_image(prompt)

        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        with os.fdopen(fd, "wb") as f:
            f.write(png)

        filename = "גמיני - %s - %s.png" % (
            _safe_name(prompt, 40),
            datetime.now().strftime("%Y-%m-%d %H-%M-%S"),
        )
        drive_link, file_id = upload_to_drive(tmp_path, filename)

        if email and file_id:
            share_drive_file(file_id, email)

        state_inc("images_generated")

        caption = "🎨 <b>%s</b>\n📂 <a href=\"%s\">פתח ב-Drive</a>" % (
            _safe_name(prompt, 80),
            drive_link or "",
        )
        send_photo(chat_id, tmp_path, caption)
    except Exception as e:
        traceback.print_exc()
        state_inc("images_failed")
        try:
            send_message(chat_id, "❌ יצירת התמונה נכשלה: %s" % e)
        except Exception:
            pass
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def cmd_img(msg, args):
    tg_id = msg["from"]["id"]
    chat_id = msg["chat"]["id"]
    if not user_allowed(tg_id, msg["from"].get("username")):
        send_message(chat_id, "⛔ אין לך הרשאה. השתמש ב-/link &lt;קוד&gt; או פנה למנהל.")
        return
    if not GEMINI_API_KEY:
        send_message(
            chat_id,
            "⚠️ מפתח Gemini API חסר בשרת.\n"
            "הוסף משתנה סביבה GEMINI_API_KEY ב-Railway "
            "(מפתח חינמי מ-https://aistudio.google.com/apikey) והפעל מחדש.",
        )
        return
    prompt = " ".join(args).strip()
    if not prompt:
        send_message(
            chat_id,
            "🎨 שימוש: /img &lt;תיאור התמונה&gt;\n"
            "למשל: /img חתול אסטרונאוט על רקע גלקסיה",
        )
        return
    email = get_linked_email(tg_id) or (
        os.environ.get("BOT_OWNER_EMAIL", "") if is_admin(tg_id) else ""
    )
    send_message(chat_id, "🎨 יוצר את התמונה... (עד דקה)")
    threading.Thread(
        target=img_worker,
        args=(chat_id, prompt, email),
        daemon=True,
    ).start()


# ============================================================
# RECORDING (/record - ffmpeg על m3u8)
# ============================================================


def _ffmpeg_available():
    return shutil.which("ffmpeg") is not None


def record_worker(chat_id, channel_key, stream_url, minutes):
    """מקליט מ-m3u8 עם ffmpeg, מעלה ל-Drive ומודיע. רץ ב-thread."""
    os.makedirs(RECORD_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    base = "%s_%s" % (re.sub(r"[^\w\-]", "_", channel_key), stamp)
    out_path = os.path.join(RECORD_DIR, base + ".ts")
    duration = minutes * 60

    cmd = [
        "ffmpeg", "-y",
        "-i", stream_url,
        "-t", str(duration),
        "-c", "copy",
        "-f", "mpegts",
        out_path,
    ]
    proc = None
    try:
        send_message(
            chat_id,
            "🔴 מתחיל להקליט <b>%s</b> ל-%d דקות…\n(ניתן לעצור עם /stoprecord)"
            % (channel_key, minutes),
        )
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.PIPE,
        )
        with RECORDINGS_LOCK:
            RECORDINGS[str(chat_id)] = {
                "proc": proc,
                "path": out_path,
                "channel": channel_key,
                "started": time.time(),
                "minutes": minutes,
            }
        try:
            proc.wait(timeout=duration + 120)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except Exception:
                proc.kill()
    except Exception as e:
        traceback.print_exc()
        send_message(chat_id, "❌ ההקלטה נכשלה: %s" % e)
        return
    finally:
        with RECORDINGS_LOCK:
            RECORDINGS.pop(str(chat_id), None)

    if not os.path.exists(out_path) or os.path.getsize(out_path) < 10000:
        send_message(chat_id, "❌ ההקלטה לא הפיקה קובץ תקין (ייתכן חסימה או DRM).")
        return

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    edit = send_message(chat_id, "⬆️ מעלה ל-Drive… (%.0f MB)" % size_mb)
    try:
        mp4_path = out_path[:-3] + ".mp4"
        os.rename(out_path, mp4_path)
        link, file_id = upload_to_drive(mp4_path, base + ".mp4")
        try:
            os.remove(mp4_path)
        except OSError:
            pass
        email = get_linked_email(chat_id) or (
            "מנהל" if is_admin(chat_id) else None
        )
        if email and isinstance(email, str) and "@" in email:
            share_drive_file(file_id, email)
        text = "🎥 ההקלטה של <b>%s</b> מוכנה!\n%s" % (channel_key, link)
        if edit and edit.get("message_id"):
            edit_message(chat_id, edit["message_id"], text)
        else:
            send_message(chat_id, text)
        state_inc("records_done")
    except Exception as e:
        traceback.print_exc()
        send_message(chat_id, "❌ ההעלאה ל-Drive נכשלה: %s" % e)


def start_record(chat_id, channel_key, minutes):
    if not _ffmpeg_available():
        send_message(chat_id, "❌ ffmpeg לא זמין בשרת — אי אפשר להקליט.")
        return
    stream_url = LIVE_CHANNELS.get(channel_key)
    if not stream_url:
        keys = ", ".join(sorted(LIVE_CHANNELS)) or "(אין)"
        send_message(chat_id, "❌ ערוץ לא מוכר. זמינים: %s" % keys)
        return
    with RECORDINGS_LOCK:
        if RECORDINGS:
            send_message(
                chat_id,
                "⚠️ כבר מתבצעת הקלטה עכשיו (ערוץ %s). "
                "הפעל /stoprecord קודם — הקלטה אחת בכל פעם."
                % next(iter(RECORDINGS.values()))["channel"],
            )
            return
    threading.Thread(
        target=record_worker,
        args=(chat_id, channel_key, stream_url, minutes),
        daemon=True,
    ).start()


def stop_record(chat_id):
    with RECORDINGS_LOCK:
        rec = RECORDINGS.get(str(chat_id))
        if not rec:
            if RECORDINGS:
                rec = next(iter(RECORDINGS.values()))
            else:
                send_message(chat_id, "אין הקלטה פעילה כרגע.")
                return
    try:
        rec["proc"].send_signal(signal.SIGINT)
    except Exception:
        rec["proc"].terminate()
    send_message(chat_id, "⏹ עוצר את ההקלטה — מיד מעלה ל-Drive…")


def scheduler_worker():
    """תזמון הקלטות קבועות: TELEGRAM_RECORD_SCHEDULES="21:00=45=12;...\""""
    fired = set()
    while not STOP.is_set():  # noqa
        try:
            now = datetime.now()
            for spec in RECORD_SCHEDULES:
                parts = spec.split("=")
                if len(parts) != 3:
                    continue
                hhmm, minutes_s, channel = [p.strip() for p in parts]
                key = "%s_%s_%s" % (now.strftime("%Y-%m-%d"), hhmm, channel)
                if key in fired:
                    continue
                if now.strftime("%H:%M") == hhmm:
                    fired.add(key)
                    minutes = int(minutes_s)
                    notify_admins(
                        "⏰ הקלטה מתוזמנת מתחילה: %s ל-%d דקות"
                        % (channel, minutes)
                    )
                    report_to = _notify_chat_id()
                    if report_to:
                        start_record(report_to, channel, minutes)
        except Exception:
            traceback.print_exc()
        STOP.wait(20)


def _notify_chat_id():
    # הקלטות מתוזמנות: מדווחות למנהל הראשון, או ל-TELEGRAM_NOTIFY_CHAT
    if ADMIN_IDS:
        return str(next(iter(ADMIN_IDS)))
    nc = os.environ.get("TELEGRAM_NOTIFY_CHAT", "")
    if nc.lstrip("-").isdigit():
        return nc
    return ""


# ============================================================
# SONGS CHANNELS (הורדת שירים אוטומטית מערוצים)
# ============================================================


# כמה פוסטי ערוץ כבר דיווחנו עליהם ללוג (לפי מזהה ערוץ) — כדי לגלות
# מזהה של ערוץ חדש בלי להציף את הלוג בכל פוסט.
_CHANNEL_LOGGED = set()


def _log_channel_once(chat, line):
    """רושם שורה אחת לכל ערוץ, גם אם מפרסמים בו הרבה."""
    key = str((chat or {}).get("id") or "")
    if not key or key in _CHANNEL_LOGGED:
        return
    _CHANNEL_LOGGED.add(key)
    print(line, flush=True)


def _is_songs_post(update):
    """האם זה פוסט ערוץ של אחד מערוצי השירים."""
    msg = update.get("channel_post") or update.get("edited_channel_post")
    if not msg:
        return None, None

    chat = msg.get("chat") or {}
    username = (chat.get("username") or "").lower()
    title = chat.get("title") or ""
    chat_id = str(chat.get("id") or "")

    # התאמה לפי שם משתמש ציבורי או לפי מזהה מספרי (ערוץ פרטי)
    if username and username in SONGS_CHANNELS:
        return msg, title or ("@" + username)
    if chat_id and chat_id in SONGS_CHANNELS:
        return msg, title or ("ערוץ " + chat_id)

    # הבוט מנהל בערוץ שהמשתמש לא הגדיר: רושמים פעם אחת את הזהות של
    # הערוץ, כדי שאפשר יהיה להעתיק מכאן את הערך של TELEGRAM_SONGS_CHANNELS
    # (הן @username והן המזהה המספרי של ערוץ פרטי).
    _log_channel_once(
        chat,
        "[tgbot] channel_post לא מוגדר: chat_id=%s username=%s title=%s "
        "(הוסף ל-TELEGRAM_SONGS_CHANNELS כדי שהבוט יוריד משם שירים)"
        % (chat_id or "?", "@" + username if username else "(פרטי)", title or "?"),
    )

    return None, None


def _safe_name(name, maxlen=60):
    return re.sub(r"[\\/:*?\"<>|]+", " ", name or "")[:maxlen].strip() or "song"


def _safe_filename(name, fallback="file", maxlen=80):
    """שם קובץ בטוח, אבל בלי לאבד את הסיומת (למשל .mp3 / .pdf)."""
    stem, dot, ext = (name or "").rpartition(".")
    if not dot:
        return _safe_name(name or fallback)
    clean_ext = re.sub(r"[^0-9A-Za-z]", "", ext)[:6]
    base = _safe_name(stem, maxlen=maxlen) or fallback
    return base + "." + clean_ext if clean_ext else base


def _media_from_message(msg):
    """מוציא מהודעה את הקובץ שאפשר להוריד דרך הבוט.

    מחזיר (file_id, file_unique_id, size, file_name) או None. תומך
    בכל מה שנשלח כקובץ: שיר, הודעה קולית, וידאו ומסמך.
    """
    audio = msg.get("audio")
    if audio:
        # שם הקובץ: "מבצע - כותרת" (תגיות השיר), אחרת שם הקובץ המקורי
        performer = audio.get("performer") or ""
        title = audio.get("title") or ""
        if performer and title:
            fname = _safe_name(performer + " - " + title) + ".mp3"
        elif title:
            fname = _safe_name(title) + ".mp3"
        else:
            fname = _safe_filename(
                audio.get("file_name"),
                fallback="song_%s.mp3" % msg.get("message_id"),
            )
        return (
            audio.get("file_id"),
            audio.get("file_unique_id"),
            audio.get("file_size") or 0,
            fname,
        )

    voice = msg.get("voice")
    if voice:
        return (
            voice.get("file_id"),
            voice.get("file_unique_id"),
            voice.get("file_size") or 0,
            "הקלטה_%s.ogg" % msg.get("message_id"),
        )

    video = msg.get("video")
    if video:
        return (
            video.get("file_id"),
            video.get("file_unique_id"),
            video.get("file_size") or 0,
            _safe_filename(
                video.get("file_name"),
                fallback="video_%s.mp4" % msg.get("message_id"),
            ),
        )

    doc = msg.get("document")
    if doc:
        return (
            doc.get("file_id"),
            doc.get("file_unique_id"),
            doc.get("file_size") or 0,
            _safe_filename(
                doc.get("file_name"),
                fallback="file_%s" % msg.get("message_id"),
            ),
        )

    return None


def _download_media_to_drive(file_id, fname):
    """מוריד קובץ מטלגרם ומעלה ל-Drive. מחזיר (קישור, מזהה) או זורק חריגה."""
    info = tg_call("getFile", file_id=file_id)
    if not info or not info.get("file_path"):
        raise RuntimeError("getFile נכשל")

    os.makedirs(SONGS_DIR, exist_ok=True)
    local_path = os.path.join(SONGS_DIR, fname)
    try:
        resp = requests.get(
            "%s/file/bot%s/%s" % (TG_BASE, BOT_TOKEN, info["file_path"]),
            timeout=180,
        )
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(resp.content)
        return upload_to_drive(local_path, fname)
    finally:
        try:
            os.remove(local_path)
        except OSError:
            pass


def handle_songs_post(msg, source_name):
    """מוריד אודיו מפוסט ערוץ ומעלה ל-Drive. רץ ב-thread."""
    if not msg.get("audio"):
        # סוג לא נתמך: רושמים רק כשזה *כן* נראה כמו קובץ שירים שהוחמץ
        # (מסמך/וידאו/הודעה קולית) — אחרת כל פוסט טקסט בערוץ יציף את הלוג.
        # ההודעה עוזרת להבין למה שיר לא ירד: mp3 שנשלח כמסמך לא מזוהה כשיר.
        kind = (
            "document" if msg.get("document")
            else "video" if msg.get("video")
            else "voice" if msg.get("voice")
            else ""
        )
        if kind:
            print(
                "[tgbot] songs: פוסט מ-%s בלי audio (סוג=%s) - דילוג"
                % (source_name, kind),
                flush=True,
            )
        return

    media = _media_from_message(msg)
    if not media:
        return
    file_id, unique_id, size, fname = media

    if size > SONGS_MAX_MB * 1024 * 1024:
        print(
            "[tgbot] songs: קובץ גדול מדי (%.1f MB) - דילוג" % (size / 1048576.0),
            flush=True,
        )
        return

    key = "ch:" + (unique_id or file_id or "")
    if key in SONGS_SEEN:
        return
    SONGS_SEEN.add(key)

    with _MEDIA_SEM:
        try:
            link, _drive_id = _download_media_to_drive(file_id, fname)
            state_inc("songs_uploaded")
            print("[tgbot] songs: %s -> %s" % (fname, link), flush=True)

            # דיווח למנהלים
            for admin_id in ADMIN_IDS:
                send_message(
                    admin_id,
                    "🎵 שיר חדש מ-%s:\n<b>%s</b>\n%s" % (source_name, fname, link),
                )
        except Exception as e:
            state_inc("errors_total")
            print("[tgbot] songs: שגיאה ב-%s: %s" % (fname, e), flush=True)


def _esc(text):
    """טקסט בטוח לתוך הודעה שנשלחת עם parse_mode=HTML."""
    return (
        (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def handle_forwarded_media(msg):
    """קובץ שנשלח או הועבר לבוט בצ'אט פרטי (מנהל בלבד) - מוריד ל-Drive.

    זה מה שמאפשר הורדה של אחורה: מסמנים בערוץ כמה שירים, מעבירים
    אותם לבוט, והוא מוריד את כולם אחד-אחד ומחזיר קישור לכל אחד.
    """
    chat_id = (msg.get("chat") or {}).get("id")
    media = _media_from_message(msg)
    if not media:
        return
    file_id, unique_id, size, fname = media

    if size > SONGS_MAX_MB * 1024 * 1024:
        send_message(
            chat_id,
            "⚠️ <b>%s</b> גדול מדי לבוט (%.1fMB, התקרה %dMB).\n"
            "קובץ כזה אפשר להוריד עם דימון השירים (TELEGRAM_SONGS_SETUP.md)."
            % (_esc(fname), size / 1048576.0, SONGS_MAX_MB),
        )
        return

    key = "fwd:" + (unique_id or file_id or "")
    if key in SONGS_SEEN:
        send_message(chat_id, "⏭ כבר הורדתי את <b>%s</b>" % _esc(fname))
        return
    SONGS_SEEN.add(key)

    print(
        "[tgbot] fwd: %s (%.1fMB) - מוריד" % (fname, size / 1048576.0),
        flush=True,
    )

    with _MEDIA_SEM:
        try:
            link, _drive_id = _download_media_to_drive(file_id, fname)
            state_inc("songs_uploaded")
            print("[tgbot] fwd: %s -> %s" % (fname, link), flush=True)
            send_message(chat_id, "✅ <b>%s</b>\n%s" % (_esc(fname), link))
        except Exception as e:
            state_inc("errors_total")
            print("[tgbot] fwd: שגיאה ב-%s: %s" % (fname, e), flush=True)
            send_message(chat_id, "❌ נכשל בהורדה של <b>%s</b>" % _esc(fname))


def _health_loop():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            with STATE_LOCK:
                body = json.dumps(STATE, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    try:
        server = HTTPServer(("127.0.0.1", HEALTH_PORT), Handler)
        server.serve_forever()
    except Exception as e:
        print("[tgbot] health server failed:", e, flush=True)


# ============================================================
# COMMANDS
# ============================================================

HELP_TEXT = (
    "🤖 <b>בוט הורדות ל-Drive</b>\n\n"
    "📥 שלח לי קישור מיוטיוב / מאקו / כאן ואוריד אותו ל-Drive.\n"
    "הוראות:\n"
    "/download [audio|video] &lt;קישור&gt; — הורדה (ברירת מחדל: אודיו)\n"
    "/status — מצב ההורדה הנוכחית\n"
    "/cancel — ביטול המשימה הנוכחית\n\n"
    "🎨 יצירת תמונות (מהשרת, בלי חסימות):\n"
    "/img &lt;תיאור&gt; — יוצר תמונה ומעלה ל-Drive\n\n"
    "🔴 הקלטות שידור חי:\n"
    "/record [ערוץ] [דקות] — הקלטה מיידית (ברירת מחדל: 12 ל-60 דקות)\n"
    "/stoprecord — עצירה והעלאה ל-Drive\n\n"
    "🎵 שירים מקבצים:\n"
    "העבר לי שיר (או שלח אותו) ואוריד אותו ל-Drive.\n"
    "אפשר להעביר כמה שירים בבת אחת - הם יורדים בזה אחר זה (מנהל).\n\n"
    "🔗 /link &lt;קוד&gt; — קישור החשבון (פעם אחת)\n"
    "/help — ההודעה הזאת"
)


def cmd_start(msg):
    tg_id = msg["from"]["id"]
    chat_id = msg["chat"]["id"]
    name = msg["from"].get("first_name", "")
    if user_allowed(tg_id, msg["from"].get("username")):
        email = get_linked_email(tg_id)
        who = "מנהל" if is_admin(tg_id) else (email or "")
        send_message(chat_id, "שלום %s! (%s)\n\n%s" % (name, who, HELP_TEXT))
    else:
        send_message(
            chat_id,
            "שלום %s!\nהבוט זמין למשתמשים מאושרים בלבד.\n"
            "אם אתה מופיע ברשימה המאושרת — בקש מהמנהל קוד קישור "
            "והקש /link &lt;קוד&gt;." % name,
        )


def cmd_help(msg):
    send_message(msg["chat"]["id"], HELP_TEXT)


def cmd_download(msg, args):
    tg_id = msg["from"]["id"]
    chat_id = msg["chat"]["id"]
    if not user_allowed(tg_id, msg["from"].get("username")):
        send_message(chat_id, "⛔ אין לך הרשאה. השתמש ב-/link &lt;קוד&gt; או פנה למנהל.")
        return
    fmt = "audio"
    url = ""
    if len(args) >= 2 and args[0] in ("audio", "video", "auto"):
        fmt, url = args[0], args[1]
    elif args:
        url = args[0]
    if not url:
        send_message(
            chat_id,
            "שימוש: /download [audio|video] &lt;קישור&gt;\n"
            "או פשוט שלח לי קישור בהודעה נפרדת.",
        )
        return
    email = get_linked_email(tg_id) or (
        os.environ.get("BOT_OWNER_EMAIL", "") if is_admin(tg_id) else ""
    )
    state_inc("downloads_started")
    threading.Thread(
        target=handle_download_command,
        args=(chat_id, url, fmt, email),
        daemon=True,
    ).start()


def cmd_status(msg):
    chat_id = msg["chat"]["id"]
    with ACTIVE_DL_LOCK:
        active = ACTIVE_DL.get(str(chat_id))
    if active:
        try:
            data = api_get("/job/" + active["job_id"], {"items": "0"})
            if data.get("success"):
                send_message(
                    chat_id,
                    "📊 משימה פעילה: %d%% (%d/%d)\n%s"
                    % (
                        data.get("percent", 0),
                        data.get("done", 0),
                        data.get("total", 0),
                        data.get("current") or "",
                    ),
                )
                return
        except Exception:
            pass
    with RECORDINGS_LOCK:
        if RECORDINGS:
            rec = next(iter(RECORDINGS.values()))
            elapsed = int(time.time() - rec["started"]) / 60
            send_message(
                chat_id,
                "🔴 מקליט %s — עברו %.0f מתוך %d דקות"
                % (rec["channel"], elapsed, rec["minutes"]),
            )
            return
    send_message(chat_id, "אין משימות פעילות כרגע.")


def cmd_cancel(msg):
    chat_id = msg["chat"]["id"]
    with ACTIVE_DL_LOCK:
        active = ACTIVE_DL.get(str(chat_id))
    if not active:
        send_message(chat_id, "אין משימת הורדה פעילה.")
        return
    try:
        api_post("/job/%s/cancel" % active["job_id"], {})
        send_message(chat_id, "🚫 נשלחה בקשת ביטול למשימה.")
    except Exception as e:
        send_message(chat_id, "❌ הביטול נכשל: %s" % e)


def cmd_record(msg, args):
    tg_id = msg["from"]["id"]
    chat_id = msg["chat"]["id"]
    if not user_allowed(tg_id, msg["from"].get("username")):
        send_message(chat_id, "⛔ אין לך הרשאה.")
        return
    channel = "12"
    minutes = 60
    if len(args) >= 2:
        channel = args[0]
        try:
            minutes = int(args[1])
        except ValueError:
            send_message(chat_id, "שימוש: /record [ערוץ] [דקות]")
            return
    elif len(args) == 1:
        if args[0].isdigit():
            minutes = int(args[0])
        else:
            channel = args[0]
    minutes = max(1, min(minutes, RECORD_MAX_MINUTES))
    start_record(chat_id, channel, minutes)


def cmd_stoprecord(msg):
    stop_record(msg["chat"]["id"])


def cmd_link(msg, args):
    tg_id = msg["from"]["id"]
    chat_id = msg["chat"]["id"]
    # מנהל מייצר קוד למייל: /link someone@gmail.com
    if is_admin(tg_id) and args and "@" in args[0]:
        email = _normalize_email(args[0])
        approved = get_approved_emails()
        if approved and email not in approved:
            send_message(
                chat_id,
                "⚠️ %s לא נמצא בגיליון המאושרים — לא ניתן לקשר." % email,
            )
            return
        code = "%06d" % (int(time.time() * 7) % 1000000)
        PENDING_CODES[code] = {
            "email": email,
            "ts": time.time(),
            "used": False,
        }
        send_message(
            chat_id,
            "🔑 קוד קישור עבור %s:\n<code>%s</code>\n"
            "תקף לשעתיים, שימוש אחד. המשתמש מקיש לי: /link %s"
            % (email, code, code),
        )
        return
    # משתמש מקיש קוד: /link 123456
    if args and args[0].isdigit() and len(args[0]) == 6:
        code = args[0]
        entry = PENDING_CODES.get(code)
        if not entry or entry["used"]:
            send_message(chat_id, "❌ קוד לא תקין או כבר נוצל.")
            return
        if time.time() - entry["ts"] > LINK_TTL_SECONDS:
            del PENDING_CODES[code]
            send_message(chat_id, "❌ הקוד פג תוקף. בקש קוד חדש מהמנהל.")
            return
        entry["used"] = True
        LINKS[str(tg_id)] = {
            "email": entry["email"],
            "name": msg["from"].get("username") or msg["from"].get("first_name", ""),
        }
        save_links()
        state_set("linked_users", len(LINKS))
        send_message(
            chat_id,
            "✅ החשבון קושר ל-%s. מעכשיו אפשר לשלוח לי קישורים!" % entry["email"],
        )
        notify_admins("🔗 %s קושר את עצמו ל-%s" % (tg_id, entry["email"]))
        return
    # משתמש רגיל בלי קוד: הסבר (או רשימה למנהל)
    if is_admin(tg_id):
        unlinked = [
            e for e in get_approved_emails()
            if e not in {v["email"] for v in LINKS.values()}
        ][:20]
        if unlinked:
            send_message(
                chat_id,
                "מיילים מאושרים שעדיין לא מקושרים:\n"
                + "\n".join("• " + e for e in unlinked)
                + "\n\nליצירת קוד: /link &lt;מייל&gt;",
            )
        else:
            send_message(chat_id, "כל המיילים המאושרים כבר מקושרים ✅")
        return
    send_message(chat_id, "שימוש: /link &lt;קוד&gt; — קוד מתקבל מהמנהל.")


# ============================================================
# UPDATE LOOP
# ============================================================


def handle_update(update):
    # --- פוסטי ערוץ (שירים אוטומטיים) ---
    cmsg, cname = _is_songs_post(update)
    if cmsg is not None:
        threading.Thread(
            target=handle_songs_post,
            args=(cmsg, cname),
            daemon=True,
        ).start()
        return

    msg = update.get("message") or update.get("edited_message")
    if not msg:
        cb = update.get("callback_query")
        if cb:
            tg_call(
                "answerCallbackQuery",
                callback_query_id=cb["id"],
            )
        return
    chat = msg.get("chat") or {}
    if chat.get("type") != "private":
        return  # רק צ'אט פרטי
    text = (msg.get("text") or "").strip()
    if not text:
        # הודעה בלי טקסט: אולי קובץ שהועבר לבוט (שירים/הקלטות).
        # מנהל בלבד - כדי שמישהו אחר לא ימלא את ה-Drive של הבעלים.
        sender = (msg.get("from") or {}).get("id")
        if sender and is_admin(sender) and _media_from_message(msg):
            threading.Thread(
                target=handle_forwarded_media,
                args=(msg,),
                daemon=True,
            ).start()
        return
    tg_id = msg["from"]["id"]
    chat_id = chat["id"]
    try:
        if text.startswith("/"):
            parts = text.split()
            cmd = parts[0].split("@")[0].lstrip("/").lower()
            args = parts[1:]
            if cmd in ("start",):
                cmd_start(msg)
            elif cmd in ("help",):
                cmd_help(msg)
            elif cmd == "download":
                cmd_download(msg, args)
            elif cmd == "status":
                cmd_status(msg)
            elif cmd == "cancel":
                cmd_cancel(msg)
            elif cmd == "img":
                cmd_img(msg, args)
            elif cmd == "record":
                cmd_record(msg, args)
            elif cmd == "stoprecord":
                cmd_stoprecord(msg)
            elif cmd == "link":
                cmd_link(msg, args)
            else:
                send_message(chat_id, "פקודה לא מוכרת. /help לעזרה.")
        else:
            # טקסט חופשי = קושרים קוד בלי פקודה, או מתייחסים כקישור
            if re.fullmatch(r"\d{6}", text):
                cmd_link(msg, [text])
                return
            if text.startswith("http"):
                cmd_download(msg, [text])
            else:
                send_message(chat_id, "שלח קישור (http…) או /help לעזרה.")
    except Exception:
        state_inc("errors_total")
        traceback.print_exc()
        try:
            send_message(chat_id, "אירעה שגיאה — נסה שוב.")
        except Exception:
            pass


def poll_loop():
    offset = 0
    print("[tgbot] polling started", flush=True)
    while not STOP.is_set():
        try:
            resp = requests.post(
                "%s/bot%s/getUpdates" % (TG_BASE, BOT_TOKEN),
                json={
                    "offset": offset,
                    "timeout": 50,
                    "allowed_updates": [
                        "message", "edited_message", "callback_query",
                        "channel_post", "edited_channel_post",
                    ],
                },
                timeout=60,
            )
            data = resp.json()
            if not data.get("ok"):
                print("[tgbot] getUpdates error:", data.get("description"), flush=True)
                time.sleep(5)
                continue
            for update in data.get("result") or []:
                offset = max(offset, update["update_id"] + 1)
                msg = (
                    update.get("message")
                    or update.get("edited_message")
                    or update.get("channel_post")
                    or update.get("edited_channel_post")
                    or {}
                )
                text = msg.get("text") or ""
                if not text and update.get("callback_query"):
                    text = update["callback_query"].get("data") or ""
                print(
                    "[tgbot] recv update=%s chat=%s text=%s"
                    % (
                        update.get("update_id"),
                        (msg.get("chat") or {}).get("id"),
                        text[:60].replace("\n", " "),
                    ),
                    flush=True,
                )
                threading.Thread(
                    target=handle_update,
                    args=(update,),
                    daemon=True,
                ).start()
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print("[tgbot] poll failed:", e, flush=True)
            STOP.wait(5)


def main():
    if not BOT_TOKEN:
        print(
            "[tgbot] TELEGRAM_BOT_TOKEN לא הוגדר - הבוט לא מופעל.",
            flush=True,
        )
        return

    load_links()
    # מנקה קודים שפג תוקפם
    now = time.time()
    for code in [c for c, v in PENDING_CODES.items() if now - v["ts"] > LINK_TTL_SECONDS]:
        PENDING_CODES.pop(code, None)

    if HEALTH_PORT:
        threading.Thread(target=_health_loop, daemon=True).start()
    if RECORD_SCHEDULES:
        threading.Thread(target=scheduler_worker, daemon=True).start()

    me = tg_call("getMe")
    if me:
        print("[tgbot] מחובר כ: @%s" % me.get("username"), flush=True)
    else:
        print("[tgbot] getMe נכשל - הטוקן תקין? ממשיך בכל זאת.", flush=True)

    def _sig(_s, _f):
        STOP.set()

    signal.signal(signal.SIGTERM, _sig)
    signal.signal(signal.SIGINT, _sig)

    poll_loop()
    print("[tgbot] הסתיים.", flush=True)


if __name__ == "__main__":
    main()
