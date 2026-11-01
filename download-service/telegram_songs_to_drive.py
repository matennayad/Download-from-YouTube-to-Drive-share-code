"""
telegram_songs_to_drive.py
==========================
Daemon שעוקב אחרי ערוצי טלגרם ציבוריים, ומוריד כל שיר חדש שעולה
בהם לשרת ומעלה אותו ל-Drive - אוטומטית, בלי לפתוח טלגרם.

איך זה עובד:
  1. מתחבר לטלגרם עם סשן משתמש (MTProto, ספריית Telethon).
     הסשן הוא הרשאה חד-פעמית שנוצרת בפקודת ה-login, ואין בה צורך
     להיות חבר בערוץ - ערוץ ציבורי אפשר לקרוא מבלי להצטרף.
  2. כל POLL_SECONDS מבקש את ההודעות שחדשות מאז הבדיקה הקודמת.
  3. לכל הודעת שמע: מוריד את הקובץ, מעלה ל-Drive (אותם משתני סביבה
     כמו app.py), מוחק את העותק המקומי ורושם בקובץ מצב שהוא טופל.
  4. אם הוגדר TELEGRAM_NOTIFY_CHAT - שולח חזרה לצ'אט את קישור
     ה-Drive, כך שגם את הקישור אין צורך לחפש.

הרצה:
  python3 telegram_songs_to_drive.py --login   # פעם אחת, ליצור סשן
  python3 telegram_songs_to_drive.py           # הרצה רציפה

שרת בריאות: GET http://127.0.0.1:8081 (או TELEGRAM_HEALTH_PORT)
"""

import asyncio
import base64
import html
import json
import os
import re
import signal
import sys
import tempfile
import threading
import time
import traceback
from datetime import datetime, timezone

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from telethon.sessions import StringSession
from telethon.tl.types import (
    DocumentAttributeAudio,
    DocumentAttributeFilename,
    DocumentAttributeVideo,
)

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from drive_bridge import bridge_credentials


# ============================================================
# CONFIGURATION (משתני סביבה - זהים לשמות ב-app.py כשמדובר ב-Drive)
# ============================================================

TELEGRAM_API_ID = int(os.environ.get("TELEGRAM_API_ID", "0") or 0)
TELEGRAM_API_HASH = os.environ.get("TELEGRAM_API_HASH", "")

# רשימת ערוצים, מופרדים בפסיק: "@songs,@newsongs,https://t.me/hebrew"
TELEGRAM_CHANNELS = os.environ.get("TELEGRAM_CHANNELS", "")

# סשן כמחרוזת (מומלץ בענן) - מה-login החד-פעמי
TELEGRAM_SESSION_STRING = os.environ.get("TELEGRAM_SESSION_STRING", "")

# או סשן כקובץ (מומלץ ב-VPS עם דיסק קבוע)
SESSION_DIR = os.environ.get(
    "TELEGRAM_SESSION_DIR",
    os.path.join(tempfile.gettempdir(), "tg_songs_session")
)
SESSION_FILE = os.path.join(SESSION_DIR, "songs.session")

# תיקיית עבודה לקבצים בזמן ההורדה/העלאה
DOWNLOAD_DIR = os.environ.get(
    "TELEGRAM_SONGS_DOWNLOAD_DIR",
    os.path.join(tempfile.gettempdir(), "tg_songs")
)

# קובץ המצב: אילו הודעות כבר טופלו, ומה מזהה ההודעה האחרון בכל ערוץ
STATE_FILE = os.environ.get(
    "TELEGRAM_SONGS_STATE_FILE",
    os.path.join(
        tempfile.gettempdir(),
        "tg_songs_state.json"
    )
)

# כמה שניות בין בדיקות ערוץ
POLL_SECONDS = int(os.environ.get("TELEGRAM_POLL_SECONDS", "120"))

# כמה הודעות למשוך בכל בדיקה לכל ערוץ
POLL_LIMIT = int(os.environ.get("TELEGRAM_POLL_LIMIT", "50"))

# בהרצה הראשונה על ערוץ חדש: 0 = נקודת פתיחה מהיום (לא להוריד היסטוריה).
# N > 0 = להוריד גם את N הפריטים האחרונים שכבר קיימים בערוץ.
BACKFILL = int(os.environ.get("TELEGRAM_BACKFILL", "0"))

# הגדרות Drive - בדיוק אותם משתנים ש-app.py כבר משתמש בהם
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID", "")
def _clean_env(name):
    # ערכים שמודבקים ב-Railway מגיעים לפעמים עם רווח, ירידת שורה או
    # מרכאות מסביב - וגוגל דוחה אז את הטוקן כאילו הוא לא תקין.
    return os.environ.get(name, "").strip().strip('"\'').strip()


GOOGLE_OAUTH_CLIENT_ID = _clean_env("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = _clean_env("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_OAUTH_REFRESH_TOKEN = _clean_env("GOOGLE_OAUTH_REFRESH_TOKEN")
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# לשלוח את קישור ה-Drive בחזרה לצ'אט (מזהה מספרי או @username שלי)
TELEGRAM_NOTIFY_CHAT = os.environ.get("TELEGRAM_NOTIFY_CHAT", "")

# האם להוריד גם הודעות קול (voice) וגם וידאו (ברירת מחדל: שמע בלבד)
INCLUDE_VOICE = os.environ.get("TELEGRAM_DOWNLOAD_VOICE", "0") == "1"
INCLUDE_VIDEO = os.environ.get("TELEGRAM_DOWNLOAD_VIDEO", "0") == "1"

# פורט לשרת הבריאות (0 = כבוי)
HEALTH_PORT = int(os.environ.get("TELEGRAM_HEALTH_PORT", "8081"))


# ============================================================
# PURE HELPERS (נבדקים ב-test_telegram_songs.py)
# ============================================================

# תווים אסורים בשמות קבצים (Windows + Linux) - מוחלפים ברווח
_FILENAME_FORBIDDEN_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')

# רצפי רווח/נקודה בקצוות מסוכנים ב-Windows
_FILENAME_EDGE_RE = re.compile(r"[\s.]+$")

MAX_FILENAME_LEN = 120


def sanitize_filename(name):
    """
    שם קובץ בטוח: בלי תווים אסורים, בלי רווחים כפולים, באורך סביר.
    עברית ותווים לא-לטיניים נשמרים כמו שהם.
    """

    cleaned = _FILENAME_FORBIDDEN_RE.sub(" ", name or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # נקודות/רווחים בסוף נחתכים (Windows לא מרשה, ולנו זה מכוער)
    cleaned = _FILENAME_EDGE_RE.sub("", cleaned)

    # נקודה בהתחלה יוצרת קובץ נסתר בלינוקס - מנקים
    cleaned = cleaned.lstrip(".").strip()

    if len(cleaned) > MAX_FILENAME_LEN:
        cleaned = cleaned[:MAX_FILENAME_LEN].rstrip()

    return cleaned


def extract_channel_username(raw):
    """
    מנרמל קלט ערוץ לשם משתמש טהור:
      "@songs", "songs", "https://t.me/songs", "t.me/s/songs" -> "songs"
    מוחזר None עבור קלט ריק או לא חוקי.
    """

    if not raw:
        return None

    text = raw.strip()

    if "://" in text:
        text = text.split("://", 1)[1]

    text = text.lstrip("@")

    # t.me/s/xxx או t.me/xxx - לוקחים את המקטע האחרון
    parts = [p for p in text.split("/") if p]

    if parts and parts[0].lower() in ("t.me", "telegram.me", "www.t.me"):
        parts = parts[1:]

    parts = [p for p in parts if p.lower() != "s"]

    if not parts:
        return None

    username = parts[0]

    if not re.fullmatch(r"[A-Za-z0-9_]{3,64}", username):
        return None

    return username


def parse_channels(raw):
    """
    מפרק מחרוזת ערוצים מופרדת בפסיק לרשימת שמות מנורמלים,
    בלי כפילויות ובסדר ההופעה.
    """

    seen = []
    for item in (raw or "").split(","):
        username = extract_channel_username(item)
        if username and username not in seen:
            seen.append(username)
    return seen


def dedupe_filename(name, taken):
    """
    אם name כבר תפוס, מחזיר "name (2)", "name (3)" וכו'.
    taken הוא סט (או רשימה) של שמות שתפוסים; השם המוחזר גם נוסף אליו.
    """

    if name not in taken:
        taken.add(name)
        return name

    base, dot, ext = name.rpartition(".")

    if dot and base:
        stem, ext = base, "." + ext
    else:
        stem, ext = name, ""

    counter = 2

    while True:
        candidate = f"{stem} ({counter}){ext}"
        if candidate not in taken:
            taken.add(candidate)
            return candidate
        counter += 1


def build_title(audio_title, performer, original_name, caption, fallback_key):
    """
    בחירת שם לשיר, לפי סדר עדיפות:
      1. "מבצע - כותרת" מתכונות האודיו
      2. הכותרת לבד
      3. שם הקובץ המקורי
      4. טקסט ההודעה (caption) - שורה ראשונה
      5. fallback דטרמיניסטי לפי הערוץ והתאריך
    """

    audio_title = (audio_title or "").strip()
    performer = (performer or "").strip()
    original_name = (original_name or "").strip()
    caption = (caption or "").strip()

    if performer and audio_title:
        candidate = f"{performer} - {audio_title}"

    else:
        candidate = audio_title or original_name

    if not candidate and caption:
        # השורה הראשונה של הטקסט, בלי סימוני ערוץ @...
        first_line = caption.splitlines()[0]
        first_line = re.sub(r"@\w+", "", first_line).strip()

        if first_line:
            candidate = first_line

    candidate = sanitize_filename(candidate)

    if not candidate:
        candidate = sanitize_filename(fallback_key) or "song"

    return candidate


def load_state(path):
    """
    טעינת קובץ המצב. קובץ חסר או פגום מחזיר מצב ריק (ולא קורס) -
    המחיר הוא רק אפשרות להורדה כפולה של אותו שיר, לא יותר.
    """

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            return {
                "channels": data.get("channels") or {},
                "done": data.get("done") or {},
            }
    except FileNotFoundError:
        pass
    except Exception as ex:
        print(
            f"State: failed to read {path} ({ex}); starting fresh",
            flush=True,
        )

    return {"channels": {}, "done": {}}


def save_state(path, state):
    """
    שמירה אטומית: כותבים לקובץ זמני ומחליפים, כדי שהפסקת חשמל
    באמצע לא תשאיר קובץ מצב חצי-כתוב.
    """

    directory = os.path.dirname(path) or "."

    os.makedirs(directory, exist_ok=True)

    tmp_path = f"{path}.{os.getpid()}.tmp"

    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)

    os.replace(tmp_path, path)


def message_key(username, message_id):
    """מפתח ייחודי להודעה בתוך קובץ המצב."""

    return f"{username}:{message_id}"


# ============================================================
# GOOGLE DRIVE (עצמאי - אותה ההיגיון כמו ב-app.py)
# ============================================================

def get_drive_service():
    """שירות Drive: גשר ה-Apps Script, ואם אינו זמין - refresh token."""

    try:
        creds = bridge_credentials(os.environ.get("API_KEY", ""))
        if creds is not None:
            return build("drive", "v3", credentials=creds)
    except Exception as e:
        print(f"Drive bridge failed, using refresh token: {e}", flush=True)
        if not GOOGLE_OAUTH_REFRESH_TOKEN:
            raise

    if not (
        GOOGLE_OAUTH_CLIENT_ID
        and GOOGLE_OAUTH_CLIENT_SECRET
        and GOOGLE_OAUTH_REFRESH_TOKEN
    ):
        raise RuntimeError(
            "חסרות פרטי OAuth ל-Drive: "
            "GOOGLE_OAUTH_CLIENT_ID / SECRET / REFRESH_TOKEN"
        )

    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_OAUTH_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_OAUTH_CLIENT_ID,
        client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=DRIVE_SCOPES,
    )

    creds.refresh(GoogleAuthRequest())

    return build("drive", "v3", credentials=creds)


def _drive_find_taken_names(service, parent_id):
    """שמות הקבצים שכבר קיימים בתיקיית היעד - למניעת כפילויות."""

    taken = set()

    page_token = None

    while True:
        query = "trashed=false"

        if parent_id:
            query += f" and '{parent_id}' in parents"

        resp = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(name)",
                pageSize=200,
                pageToken=page_token,
            )
            .execute()
        )

        for item in resp.get("files", []):
            taken.add(item.get("name") or "")

        page_token = resp.get("nextPageToken")

        if not page_token:
            break

    return taken


def upload_to_drive(local_path, filename, service=None, parent_id=None):
    """
    העלאה ל-Drive עם הימנעות מכפילויות שמות בתוך תיקיית היעד.
    מוחזר (link, file_id).
    """

    svc = service or get_drive_service()

    target_parent = parent_id or DRIVE_FOLDER_ID or None

    # שמות תפוסים בתיקייה - רק אם הוגדרה תיקייה (בליה אישית זה יקר)
    if target_parent:
        taken = _drive_find_taken_names(svc, target_parent)
        filename = dedupe_filename(filename, taken)

    metadata = {
        "name": filename,
        "parents": [target_parent] if target_parent else [],
    }

    media = MediaFileUpload(local_path, resumable=True)

    uploaded = (
        svc.files()
        .create(body=metadata, media_body=media, fields="id, webViewLink")
        .execute()
    )

    return (
        uploaded.get("webViewLink"),
        uploaded.get("id"),
    )


# ============================================================
# RUNTIME STATE (לשרת הבריאות)
# ============================================================

STATUS = {
    "started_at": datetime.now(timezone.utc).isoformat(),
    "last_cycle_at": None,
    "last_cycle_ok": None,
    "last_error": None,
    "channels": {},
    "uploads_total": 0,
    "errors_total": 0,
}

STATUS_LOCK = threading.Lock()


def status_update(**kwargs):
    with STATUS_LOCK:
        STATUS.update(kwargs)


def status_channel(username, **kwargs):
    with STATUS_LOCK:
        channel = STATUS["channels"].setdefault(username, {})
        channel.update(kwargs)


# ============================================================
# MEDIA CLASSIFICATION
# ============================================================

def classify_media(message, include_voice=False, include_video=False):
    """
    מסווג מדיה של הודעה. מוחזר dict עם הפרטים הדרושים להורדה,
    או None אם זה לא שיר שמעיין.
    """

    media = getattr(message, "media", None)

    document = getattr(media, "document", None) if media else None

    if not document:
        return None

    mime = (getattr(document, "mime_type", "") or "").lower()

    audio_title = None
    performer = None
    original_name = None
    is_voice = False
    is_video = False

    for attr in getattr(document, "attributes", None) or []:

        if isinstance(attr, DocumentAttributeAudio):

            if getattr(attr, "voice", False):
                is_voice = True
            else:
                audio_title = getattr(attr, "title", None)
                performer = getattr(attr, "performer", None)

        elif isinstance(attr, DocumentAttributeFilename):
            original_name = getattr(attr, "file_name", None)

        elif isinstance(attr, DocumentAttributeVideo):
            is_video = True

    if is_voice:
        if not include_voice:
            return None

        kind = "voice"

    elif mime.startswith("audio/") or audio_title is not None:
        kind = "audio"

    elif is_video or mime.startswith("video/"):
        if not include_video:
            return None

        kind = "video"

    else:
        # מסמכים אחרים (pdf, apk...) - לא מעניינים אותנו
        return None

    size = int(getattr(document, "size", 0) or 0)

    return {
        "kind": kind,
        "mime": mime,
        "size": size,
        "audio_title": audio_title,
        "performer": performer,
        "original_name": original_name,
    }


def pick_extension(info, fallback=".mp3"):
    """סיומת קובץ סבירה לפי ה-mime/שם המקורי."""

    name = info.get("original_name") or ""

    if "." in name:
        ext = name.rsplit(".", 1)[1].lower()

        if 1 <= len(ext) <= 5 and ext.isalnum():
            return f".{ext}"

    mime = info.get("mime") or ""

    mapping = {
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "audio/ogg": ".ogg",
        "audio/opus": ".opus",
        "audio/flac": ".flac",
        "audio/wav": ".wav",
        "audio/webm": ".webm",
        "video/mp4": ".mp4",
    }

    return mapping.get(mime, fallback)


# ============================================================
# DOWNLOAD + UPLOAD FLOW
# ============================================================

async def process_one_message(
    client,
    message,
    username,
    info,
    state,
    drive_service,
    notify_client=None,
):
    """
    הורדת קובץ אחד והעלאתו ל-Drive. מוחזר True אם הסתיים בהצלחה.
    ההורדה אסינכרונית וההעלאה רצה בת'רד נפרד, כדי שהלופ לא ייחסם.
    """

    msg_id = message.id

    date = getattr(message, "date", None) or datetime.now(timezone.utc)

    fallback_key = (
        f"{username}_{date.strftime('%Y%m%d_%H%M%S')}"
    )

    title = build_title(
        info.get("audio_title"),
        info.get("performer"),
        info.get("original_name"),
        getattr(message, "message", None) or "",
        fallback_key,
    )

    ext = pick_extension(info)

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # שם ייחודי בתיקיית ההורדות - שתי הודעות באותו שם לא ידרסו זו את זו
    taken = set(os.listdir(DOWNLOAD_DIR))
    local_name = dedupe_filename(f"{title}{ext}", taken)
    local_path = os.path.join(DOWNLOAD_DIR, local_name)

    print(
        f"[{username}] msg {msg_id}: downloading "
        f"{info.get('kind')} ({info.get('size', 0) // 1024} KB) -> {local_name}",
        flush=True,
    )

    downloaded = await client.download_media(message, file=local_path)

    if not downloaded or not os.path.exists(downloaded):
        raise RuntimeError("download returned no file")

    try:
        # ההעלאה חוסמת - מריצים אותה מחוץ ללופ האסינכרוני
        link, file_id = await asyncio.to_thread(
            upload_to_drive,
            downloaded,
            local_name,
            service=drive_service,
        )

    finally:
        try:
            os.remove(downloaded)
        except OSError:
            pass

    state["done"][message_key(username, msg_id)] = {
        "name": local_name,
        "drive_id": file_id,
        "link": link,
        "ts": datetime.now(timezone.utc).isoformat(),
    }

    status_channel(
        username,
        last_upload=local_name,
        last_upload_at=datetime.now(timezone.utc).isoformat(),
    )

    with STATUS_LOCK:
        STATUS["uploads_total"] += 1

    print(
        f"[{username}] msg {msg_id}: uploaded -> {link}",
        flush=True,
    )

    # שליחת הקישור בחזרה לצ'אט שלי, אם הוגדר
    if notify_client is not None and TELEGRAM_NOTIFY_CHAT:

        try:
            await notify_client.send_message(
                TELEGRAM_NOTIFY_CHAT,
                f"🎵 {html.escape(local_name)}\n{link}",
                parse_mode="html",
            )
        except Exception as ex:
            print(f"Notify failed: {ex}", flush=True)

    return True


# ============================================================
# MAIN LOOP
# ============================================================

def make_client():
    """בניית לקוח Telethon לפי סוג הסשן שהוגדר."""

    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print(
            "חסרים TELEGRAM_API_ID ו-TELEGRAM_API_HASH. "
            "הרץ: python3 telegram_songs_to_drive.py --login",
            flush=True,
        )
        sys.exit(1)

    if TELEGRAM_SESSION_STRING:
        session = StringSession(TELEGRAM_SESSION_STRING)
    else:
        os.makedirs(SESSION_DIR, exist_ok=True)
        session = SESSION_FILE

    return TelegramClient(
        session,
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH,
        device_model="songs-to-drive",
        system_version="linux",
        app_version="1.0",
    )


def interactive_login():
    """
    פקודת ה-login החד-פעמית: מקבל מספר טלפון + קוד אימות,
    ומדפיס מחרוזת סשן להכניס ל-TELEGRAM_SESSION_STRING.
    """

    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("חסרים TELEGRAM_API_ID / TELEGRAM_API_HASH בסביבה.")
        sys.exit(1)

    client = TelegramClient(
        SESSION_FILE,
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH,
    )

    client.start()

    string = StringSession.save(client.session)

    print()
    print("=" * 60)
    print("הסשן נוצר בהצלחה! הגדר בסביבה:")
    print()
    print(f"TELEGRAM_SESSION_STRING={string}")
    print()
    print("שמור את המחרוזת הזאת בסוד - היא גישה מלאה לחשבון שלך.")
    print("=" * 60)

    client.disconnect()


async def scan_channel(client, username, state, drive_service):
    """
    סריקה אחת של ערוץ: משיכת הודעות חדשות ועיבודן.
    מוחזר מספר הקבצים שהועלו.
    """

    entity = await client.get_entity(username)

    channel_state = state["channels"].setdefault(username, {})
    min_id = channel_state.get("min_id") or 0

    messages = []

    async for msg in client.iter_messages(
        entity,
        limit=POLL_LIMIT,
        min_id=min_id,
    ):
        messages.append(msg)

    if not messages:
        status_channel(username, last_check_ok=True, new_messages=0)
        return 0

    newest_id = max(m.id for m in messages)

    first_run = min_id == 0

    uploaded = 0

    # מסדרים כרונולוגית: מהישן לחדש
    for msg in sorted(messages, key=lambda m: m.id):

        if first_run and BACKFILL <= 0:
            # בפתיחה של ערוץ חדש - רק לתעד את נקודת הפתיחה
            break

        if BACKFILL > 0 and first_run:
            # backfill: לוקחים רק את N האחרונים
            if msg.id <= newest_id - BACKFILL:
                continue

        if message_key(username, msg.id) in state["done"]:
            continue

        info = classify_media(msg, INCLUDE_VOICE, INCLUDE_VIDEO)

        if not info:
            continue

        try:
            await process_one_message(
                client,
                msg,
                username,
                info,
                state,
                drive_service,
                notify_client=client,
            )
            uploaded += 1

        except FloodWaitError as flood:
            print(
                f"FloodWait {flood.seconds}s - ממתין וממשיך",
                flush=True,
            )
            await asyncio.sleep(flood.seconds + 1)

        except Exception as ex:
            with STATUS_LOCK:
                STATUS["errors_total"] += 1
                STATUS["last_error"] = f"{username}:{msg.id}: {ex}"

            print(
                f"[{username}] msg {msg.id} failed: {ex}",
                flush=True,
            )
            traceback.print_exc()

    # עדכון נקודת ההמשך - אחרי שכל הקבצים בסבב טופלו
    channel_state["min_id"] = max(min_id, newest_id)
    channel_state["last_check"] = datetime.now(timezone.utc).isoformat()

    status_channel(
        username,
        last_check_ok=True,
        last_check=channel_state["last_check"],
        min_id=channel_state["min_id"],
    )

    return uploaded


async def main_loop():
    """לולאת העבודה: סריקת כל הערוצים, המתנה, וחזרה."""

    channels = parse_channels(TELEGRAM_CHANNELS)

    if not channels:
        print(
            "לא הוגדרו ערוצים. הגדר TELEGRAM_CHANNELS=@songs,@other",
            flush=True,
        )
        sys.exit(1)

    print(f"ערוצים במעקב: {', '.join('@' + c for c in channels)}", flush=True)

    # בדיקת תקינות מוקדמת של Drive - כדי שחסרון הגדרות ייפול מיד
    # עם הודעה ברורה, ולא בכל מחזור סריקה שוב ושוב.
    try:
        get_drive_service()
    except Exception as drive_ex:
        print(
            "שגיאת הגדרות Drive - הדימון לא יכול לרוץ: "
            + str(drive_ex),
            flush=True,
        )
        sys.exit(1)

    state = load_state(STATE_FILE)
    drive_service = None

    client = make_client()

    await client.connect()

    if not await client.is_user_authorized():
        print(
            "הסשן אינו מורשה. הרץ פעם אחת: "
            "python3 telegram_songs_to_drive.py --login",
            flush=True,
        )
        sys.exit(1)

    me = await client.get_me()
    print(f"מחובר כ: {getattr(me, 'first_name', '') or me.phone}", flush=True)

    stop_event = asyncio.Event()

    def request_stop(*_):
        stop_event.set()

    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_stop)
        except NotImplementedError:
            signal.signal(sig, request_stop)

    while not stop_event.is_set():

        cycle_started = time.time()

        try:
            # שירות Drive מתחדש לכל מחזור (ה-token מתרענן מעצמו)
            drive_service = get_drive_service()

            for username in channels:

                if stop_event.is_set():
                    break

                try:
                    await scan_channel(
                        client,
                        username,
                        state,
                        drive_service,
                    )

                except Exception as ex:
                    with STATUS_LOCK:
                        STATUS["errors_total"] += 1
                        STATUS["last_error"] = f"{username}: {ex}"

                    status_channel(username, last_check_ok=False, error=str(ex))

                    print(
                        f"Channel @{username} scan failed: {ex}",
                        flush=True,
                    )

            save_state(STATE_FILE, state)

            status_update(
                last_cycle_at=datetime.now(timezone.utc).isoformat(),
                last_cycle_ok=True,
                last_error=None,
            )

        except Exception as ex:
            status_update(
                last_cycle_at=datetime.now(timezone.utc).isoformat(),
                last_cycle_ok=False,
                last_error=str(ex),
            )

            print(f"Cycle failed: {ex}", flush=True)
            traceback.print_exc()

        elapsed = time.time() - cycle_started
        wait = max(5, POLL_SECONDS - elapsed)

        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=wait,
            )
        except asyncio.TimeoutError:
            pass

    print("מתכבה...", flush=True)
    await client.disconnect()


# ============================================================
# HEALTH SERVER
# ============================================================

def start_health_server():
    """
    שרת HTTP מיני לניטור: GET / מחזיר JSON עם המצב.
    בלי Flask - סטדליב, כדי שה-daemon יישאר קל.
    """

    if not HEALTH_PORT:
        return None

    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):

        def do_GET(self):
            with STATUS_LOCK:
                snapshot = json.dumps(
                    STATUS,
                    ensure_ascii=False,
                    indent=1,
                )

            body = snapshot.encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("0.0.0.0", HEALTH_PORT), Handler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print(f"Health server: http://0.0.0.0:{HEALTH_PORT}", flush=True)

    return server


# ============================================================
# ENTRY POINT
# ============================================================

def main():
    if "--login" in sys.argv:
        interactive_login()
        return

    start_health_server()

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
