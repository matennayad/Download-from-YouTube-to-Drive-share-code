import base64
import glob
import html as html_lib
import os
import random
import re
import json
import time
import mimetypes
import uuid
import queue
import shutil
import signal
import threading
import tempfile
import traceback
from concurrent.futures import ThreadPoolExecutor
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import requests
from urllib.parse import urljoin
import yt_dlp
from yt_dlp.utils import smuggle_url
from flask import (Flask, Response, jsonify, make_response, request,
                   stream_with_context)
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaInMemoryUpload
from drive_bridge import bridge_credentials, bridge_url
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

API_KEY = os.environ.get("API_KEY", "")

# מפתח ייעודי לטופס החיפוש המאוחד (Google Forms/Apps Script).
# יש להגדיר UNIFIED_SEARCH_KEY במשתני הסביבה (ערך אקראי משלך). ריק = רק API_KEY מתקבל.
UNIFIED_SEARCH_KEY = os.environ.get('UNIFIED_SEARCH_KEY', '')
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID", "")
YOUTUBE_COOKIES = os.environ.get("YOUTUBE_COOKIES", "")

def _clean_env(name):
    # ערכים שמודבקים ב-Railway מגיעים לפעמים עם רווח, ירידת שורה או
    # מרכאות מסביב - וגוגל דוחה אז את הטוקן כאילו הוא לא תקין.
    return os.environ.get(name, "").strip().strip('"\'').strip()


GOOGLE_OAUTH_CLIENT_ID = _clean_env("GOOGLE_OAUTH_CLIENT_ID")

GOOGLE_OAUTH_CLIENT_SECRET = _clean_env("GOOGLE_OAUTH_CLIENT_SECRET")

GOOGLE_OAUTH_REFRESH_TOKEN = _clean_env("GOOGLE_OAUTH_REFRESH_TOKEN")

DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.file"
]


# ============================================================
# KAN (כאן - תאגיד השידור הישראלי)
# ============================================================
# אתר כאן משתמש בנגן Kaltura (שותף מספר 2717431). עמוד פרק מכיל את
# מזהה ה-entry של Kaltura, ו-yt-dlp יודע להוריד ממנו את כל איכויות
# הווידאו (כולל 1080p) דרך ה-extractor המובנה kaltura:.
# מבנה קישורים:
#   סדרה:  https://www.kan.org.il/content/kan/kan-11/p-11843/
#   עונה:  https://www.kan.org.il/content/kan/kan-11/p-11843/s8/
#   פרק:   https://www.kan.org.il/content/kan/kan-11/p-11843/s8/756427/

KAN_KALTURA_PARTNER = "2717431"

# ------------------------------------------------
# פרוקסי לשליפת עמודי כאן: kan.org.il חוסם IP לא-ישראלי, והשרת רץ
# בחו"ל (Railway/Render). שתי שכבות:
#   1. KAN_PROXY_URL - פרוקסי ידני (משתנה סביבה), עדיפות עליונה.
#   2. ברירת מחדל: רשימת פרוקסים ישראליים חינמיים של proxifly
#      (מתעדכנת כל 5 דקות). בזמן ריצה בודקים מועמדים מול kan.org.il
#      וממננים את הראשון שעובד, עם מטמון של חצי שעה.
# חשוב: רק שליפת ה-HTML עוברת דרך הפרוקסי - הורדת הווידאו עצמה
# מה-CDN של Kaltura פתוחה לכל העולם ולא מושפעת.
# ------------------------------------------------

KAN_PROXY_URL = os.environ.get("KAN_PROXY_URL", "")

KAN_PROXY_LIST_URLS = (
    # רשימות עם סינון-מדינה מובנה - רק IL מוחזר
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/"
    "main/proxies/countries/IL/data.txt",
    "https://proxylist.geonode.com/api/proxy-list?country=IL"
    "&protocols=http%2Chttps&limit=20&page=1&sort_by=lastChecked"
    "&sort_type=desc",
    "https://api.proxyscrape.com/v2/?request=displayproxies"
    "&protocol=http&timeout=10000&country=IL&anonymity=all",
    "https://www.proxy-list.download/api/v1/get?country=IL&type=http",
)

KAN_PROXY_TEST_URL = "https://www.kan.org.il/"

# כמה מועמדים לנסות בכל סבב רענון (לפני שמוותרים לעונה הזאת).
# פרוקסים חינמיים נופלים כל הזמן - ככל שבודקים יותר, הסיכוי למצוא
# חי גבוה יותר.
KAN_PROXY_MAX_CANDIDATES = 14

# כמה זמן פרוקסי שנמצא עובד נשאר במטמון (שניות)
# פג תוקף מטמון מוקטן: 10 דקות במקום 30, כדי שאחרי "לא נמצא פרוקסי
# עובד" לא נדביק את עצמנו למצב הזה לזמן ארוך.
KAN_PROXY_CACHE_TTL = 600

# תקציב זמן כולל לשלב הפרוקסים: אם סך כל בדיקות המועמדים חורג מזה,
# מוותרים וממשיכים ל-fallback של r.jina.ai. בלי זה, מועמדים איטיים
# יכולים לחסום בקשות דקות ארוכות.
KAN_PROXY_BUDGET_SECONDS = 90

# ניסיון ישיר: 20 שניות מספיקים להכרעה אם kan.org.il נגיש מהשרת.
KAN_DIRECT_TIMEOUT = 20

# Wayback Machine: צילום נחשב "טרי" אם ההפרש מהיום בפורמט yyyymmdd
# קטן מהסף (130 ≈ חודש-חודשיים). אחרת מוגש Save-Page-Now לצילום חדש.
KAN_WAYBACK_FRESHNESS = 130

# המתנה לארכוב ראשוני של עמוד שמעולם לא נארכב: SPN לוקח 1-3 דקות
# לעמוד חדש, אז בודקים שוב ושוב עד ~3 דקות לפני ויתור.
KAN_SPN_POLL_ATTEMPTS = 6
KAN_SPN_POLL_INTERVAL = 30

# מטמון עמודים: עמוד פרק נשמר יום (תוכנו יציב), שאר העמודים שעה
KAN_PAGE_CACHE_TTL_EPISODE = 24 * 3600
KAN_PAGE_CACHE_TTL_DEFAULT = 3600
_KAN_PAGE_CACHE = {}


def _kan_page_cache_get(url):

    entry = _KAN_PAGE_CACHE.get(url)

    if not entry:
        return None

    ts, body = entry

    ttl = (
        KAN_PAGE_CACHE_TTL_EPISODE
        if re.search(r"/s\d+/\d+/?$", url.rstrip("/") + "/")
        else KAN_PAGE_CACHE_TTL_DEFAULT
    )

    if time.time() - ts > ttl:
        _KAN_PAGE_CACHE.pop(url, None)
        return None

    return body


def _kan_page_cache_put(url, body):

    _KAN_PAGE_CACHE[url] = (time.time(), body)

    # גבול זיכרון פשוט - מוחקים את הישן ביותר
    while len(_KAN_PAGE_CACHE) > 200:

        oldest = min(_KAN_PAGE_CACHE, key=lambda k: _KAN_PAGE_CACHE[k][0])

        _KAN_PAGE_CACHE.pop(oldest, None)

_kan_proxy_state = {"proxy": None, "checked_at": 0.0}

_kan_proxy_lock = threading.Lock()

KAN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.kan.org.il/",
}

# מזהה entry של Kaltura בתוך כתובת (playManifest / serveFlavor)
KAN_ENTRY_URL_RE = re.compile(
    r"(?:entryId|entry_id)/([01]_[0-9a-zA-Z]{8,})"
)

# מזהה entry של Kaltura כערך של מפתח בקונפיגורציה של הנגן - תומך גם בצורה
# מצוטטת ("entryId": "1_xxx") וגם בצורת attribute של HTML (data-entry-id="1_xxx")
KAN_ENTRY_KEY_RE = re.compile(
    r"[\"']?(?:entryId|entry_id|data-entry-id|data-kaltura-entry-id)[\"']?"
    r"\s*[:=]\s*[\"']([01]_[0-9a-zA-Z]{8,})[\"']"
)

# מספר פרק מתוך כותרת ("בואו לאכול איתי עונה 8 | פרק 1 ...")
KAN_EPISODE_NUMBER_RE = re.compile(r"פרק\s*(\d{1,3})")


# ============================================================
# CHANNEL DOWNLOAD SETTINGS
# ============================================================
# תקרת סרטונים לבקשה אחת. הלקוח שולח את המזהים שכבר ירדו אצלו
# (skip_ids), ואנחנו מורידים רק את החדשים - עד התקרה הזו.

MAX_VIDEOS_PER_JOB = int(
    os.environ.get(
        "MAX_VIDEOS_PER_JOB",
        "30"
    )
)

# כמה סרטונים לסרוק מהערוץ כדי למצוא את החדשים (סריקה "שטוחה",
# בלי הורדה - מהירה מאוד). צריך להיות גדול מהתקרה כדי שנוכל לדלג
# על מה שכבר ירד אצל הלקוח.
CHANNEL_SCAN_LIMIT = int(
    os.environ.get(
        "CHANNEL_SCAN_LIMIT",
        "300"
    )
)

# תקרה עליונה לחלון הסריקה. הסריקה גדלה ככל שיורדים יותר
# מהערוץ, אבל לא מעבר לזה - כדי שההרחבה לא תיקח לנצח.
MAX_CHANNEL_SCAN_LIMIT = int(
    os.environ.get(
        "MAX_CHANNEL_SCAN_LIMIT",
        "10000"
    )
)

# השהייה בין סרטון לסרטון (שניות) - הגנה מפני חסימת IP ביוטיוב
DELAY_BETWEEN_VIDEOS = float(
    os.environ.get(
        "DELAY_BETWEEN_VIDEOS",
        "4"
    )
)

# כמה עבודות ערוץ ירוצו במקביל. 1 = אחת בכל רגע (מומלץ - השרת
# מוגבל בדיסק וברוחב פס, ומקביליות מזמינה חסימה מיוטיוב).
MAX_CONCURRENT_JOBS = int(
    os.environ.get(
        "MAX_CONCURRENT_JOBS",
        "1"
    )
)

# תיקייה לשמירת מצב העבודות (שורד קריסת thread, לא שורד redeploy)
JOBS_DIR = os.environ.get(
    "JOBS_DIR",
    os.path.join(
        tempfile.gettempdir(),
        "yt_jobs"
    )
)


# ============================================================
# BLOCK-CHECK SERVICE (NetFree)
# ============================================================
# GET <BASE>/<מזהה>  ->  מילה אחת בטקסט.
#
#   OPEN      פתוח
#   LOCK      נבדק ונחסם
#   PENDING   עדיין לא נבדק (חסום בפועל, אך טרם הוחלט)
#
# שגיאה מוחזרת עם קוד שאינו 200 וגוף שמתחיל ב-ERROR:
# (invalid_id / rate_limited / throttled_by_youtube / ...).
# שגיאה איננה תוצאה - היא לא אומרת חסום ולא פתוח.
#
# מזהים נתמכים: סרטון (11 תווים), ערוץ (UC + 22), כינוי (@handle).
# מגבלה: 30 בקשות ל-10 שניות מאותו IP, מטמון של 5 דקות.

BLOCK_CHECK_BASE_URL = os.environ.get(
    "BLOCK_CHECK_BASE_URL",
    ""  # כתובת שירות בדיקת חסימת נטפרי (אופציונלי). ריק = הבדיקה כבויה
)

BLOCK_CHECK_TIMEOUT = int(
    os.environ.get(
        "BLOCK_CHECK_TIMEOUT",
        "20"
    )
)

# כמה לחכות ולנסות שוב כשמקבלים rate_limited (429)
BLOCK_CHECK_RETRY_DELAY = float(
    os.environ.get(
        "BLOCK_CHECK_RETRY_DELAY",
        "4"
    )
)

# תוצאות אפשריות
BLOCK_OPEN = "open"
BLOCK_LOCK = "lock"
BLOCK_PENDING = "pending"


# ============================================================
# TOR PROXY
# ============================================================

TOR_PROXY_URL = "socks5h://127.0.0.1:9050"


# ============================================================
# YT-DLP VERSION
# ============================================================

YTDLP_VERSION = getattr(
    yt_dlp.version,
    "__version__",
    "unknown"
)


# ============================================================
# PLATFORM DETECTION
# ============================================================
# מזהה מאיזו פלטפורמה מגיע הקישור, כדי להתאים את אסטרטגיית ההורדה.
# כרגע נתמכים: youtube, instagram, tiktok. כל השאר -> "other"
# (yt-dlp עדיין ינסה לחלץ מידע גם מ"other", פשוט בלי אופטימיזציות ייעודיות)

def detect_platform(url):

    if not url:
        return "other"

    u = url.lower()

    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"

    if "instagram.com" in u:
        return "instagram"

    if "tiktok.com" in u:
        return "tiktok"

    # כאן לפני רשימת אתרי החדשות - יש לו מנוע ייעודי (Kaltura)
    if "kan.org.il" in u:
        return "kan"

    if any(
        domain in u
        for domain in [
            "mako.co.il",
            "mako.tv",
            "n12.co.il",
            "13tv.co.il",
            "kan.org.il",
            "now14.co.il",
            "c14.co.il",
            "ynet.co.il",
            "immergo.tv",
            ".m3u8"
        ]
    ):
        return "news_il"

    return "other"


# ============================================================
# SITE PROFILE: כותרות ועוגיות לפי האתר האמיתי
# ============================================================
# הקוד הקודם שלח Referer/Origin של מאקו גם כשהוריד מכאן 11,
# 13tv או n12 - וה-CDN שלהם דוחה בקשות עם כותרות של אתר אחר.
# הפרופיל נגזר מהכתובת של העמוד עצמו, לא מאתר אחד קבוע.

def il_site_profile(page_url):
    """
    מחזיר (referer, origin, cookie_domain) לפי האתר שממנו הגיעה
    הבקשה. כתובת לא מוכרת מקבלת פרופיל מה-host שלה עצמו.
    """

    source = page_url or ""

    if source and "://" not in source:
        source = "https://" + source

    host = urllib.parse.urlparse(
        source
    ).netloc.lower().split(":")[0]

    if not host:
        return (
            "https://www.mako.co.il/",
            "https://www.mako.co.il",
            ".mako.co.il"
        )

    if "mako" in host or "keshet" in host:
        return (
            "https://www.mako.co.il/",
            "https://www.mako.co.il",
            ".mako.co.il"
        )

    if "kan" in host:
        return (
            "https://www.kan.org.il/",
            "https://www.kan.org.il",
            ".kan.org.il"
        )

    if "13tv" in host:
        return (
            "https://13tv.co.il/",
            "https://13tv.co.il",
            ".13tv.co.il"
        )

    if "n12" in host:
        return (
            "https://www.n12.co.il/",
            "https://www.n12.co.il",
            ".n12.co.il"
        )

    if "now14" in host or "c14" in host:
        return (
            "https://www.now14.co.il/",
            "https://www.now14.co.il",
            ".now14.co.il"
        )

    if "ynet" in host:
        return (
            "https://www.ynet.co.il/",
            "https://www.ynet.co.il",
            ".ynet.co.il"
        )

    return (
        "https://" + host + "/",
        "https://" + host,
        "." + host
    )


# ============================================================
# ANTI-BOT BYPASS: ISRAELI NEWS SITES STREAM SCRAPER
# ============================================================
# פותח דפדפן וירטואלי (בלי ממשק) כדי לגלוש לעמוד באתר חדשות,
# ולתפוס את קישור השידור האמיתי (m3u8) שמוסתר בקוד הדף.

# שרתים של זרמי תוכן באתרים הישראליים - מועמד מהם מדורג גבוה
IL_CONTENT_STREAM_HOSTS = (
    "keshet-vod", "mako-stream", "ott-playback", "akamaized",
    "cloudfront.net", "kanstream", "kan.org.il"
)

# פלייליסטים של פרסומות/מדידה - לא התוכן. במאקו VOD הפרסומות
# הן HLS נפרד שמחזיר 403 לכל מי שאינו הנגן, ולכן חייבים לסנן
# אותן לפני שמנסים להוריד.
IL_STREAM_NOISE = (
    "analytics", "google", "doubleclick", "vast", "vpaid",
    "adserver", "ads.", "/ads/", "adbreak", "adcreative",
    "creative", "pubmatic", "criteo", "adnxs", "ima3",
    "thumb", "banner", "logo"
)


def il_candidate_score(stream_url):
    """
    דירוג מועמד זרם: שרת תוכן מוכר = עדיפות גבוהה,
    master playlist = עדיפות נוספת (הוא מפנה לווריאנטים).
    כתובת חתומה (hdnts/hdnea - טוקן Akamai) = עדיפות הכי גבוהה:
    מה שהנגן בעצמו מביא מה-API הוא חתום ותקף, ואילו התבנית
    הלא-חתומה מגוף העמוד נדחית 403 על ידי ה-CDN.
    """

    low = (stream_url or "").lower()

    score = 0

    # טוקן חתום שהנגן קיבל מה-API - הכתובת היחידה שבאמת עובדת
    # מחוץ לנגן. בלי זה Akamai מחזיר Access Denied.
    if "hdnts=" in low or "hdnea=" in low:
        score += 5

    if any(
        host in low
        for host in IL_CONTENT_STREAM_HOSTS
    ):
        score += 2

    if "master" in low:
        score += 1

    return score


MAKO_PLAYLIST_JS = """
async ([vcmid, chId, galId]) => {
  // אותו מפתח שהנגן של מאקו משתמש בו בצד הלקוח לפענוח תשובת
  // playlist12.jsp. הפענוח נעשה כאן עם WebCrypto - בלי ספריות.
  const rawKey = 'LTf7r/zM2VndHwP+4So6bw==';
  const keyBytes = Uint8Array.from(atob(rawKey), c => c.charCodeAt(0));
  const ivBytes = Uint8Array.from('theExact16Chars=', c => c.charCodeAt(0));
  const key = await crypto.subtle.importKey(
      'raw', keyBytes, {name: 'AES-CBC'}, false, ['decrypt']);
  const dec = async (b64) => {
    const bytes = Uint8Array.from(atob(b64.trim()), c => c.charCodeAt(0));
    const plain = await crypto.subtle.decrypt(
        {name: 'AES-CBC', iv: ivBytes}, key, bytes);
    return new TextDecoder().decode(plain);
  };
  const r = await fetch(
      '/AjaxPage?jspName=playlist12.jsp&vcmid=' + vcmid +
      '&videoChannelId=' + chId + '&galleryChannelId=' + galId +
      '&con=web', {credentials: 'include'});
  const txt = await r.text();
  if (!txt || txt[0] === '<') {
    return {ok: false, why: 'not-encrypted(' + r.status + ')'};
  }
  try {
    return {ok: true, body: (await dec(txt)).slice(0, 60000)};
  } catch (e) {
    return {ok: false, why: 'decrypt-fail'};
  }
}
"""


def mako_extract_ids(page_url):
    """
    חילוץ מזהי הפריט מכתובת מאקו. המזהים דרושים לקריאה הישירה
    ל-playlist12.jsp - ה-API שהנגן פונה אליו. ה-vcmid הוא מזהה הפריט
    (VOD-xxxx.htm), ושני האחרים הם מזהי הערוץ שלא ניתנים להסקה
    מה-URL - ולכן נשלפים מתוך גוף העמוד עצמו.
    """

    m = re.search(r"VOD-([0-9a-f]+)", page_url or "")

    if not m:
        return None

    return {"vcmid_prefix": m.group(1)}


def mako_ids_from_html(html):
    """שליפת מזהי הערוץ מתוך אובייקט ה-vod שנטען עם העמוד."""

    ids = {}

    for key, pat in (
        ("itemVcmId", r'"itemVcmId":"([0-9a-fA-F]+VgnVCM[0-9a-zA-Z]+)"'),
        ("channelId", r'"channelId":"([0-9a-fA-F]+VgnVCM[0-9a-zA-Z]+)"'),
        (
            "galleryChannelId",
            r'"galleryChannelId":"([0-9a-fA-F]+VgnVCM[0-9a-zA-Z]+)"'
        ),
    ):

        m = re.search(pat, html or "")

        if m:
            ids[key] = m.group(1)

    return ids


MAKO_WAYBACK_CACHE = {}


def mako_parse_hub_episode_map(html_text, base_path, season_dir):
    """
    חילוץ מיפוי "פרק N" -> כתובת VOD מתוך HTML של עמוד שער של סדרה.

    מבנה העוגנים זהה בין צילום של ארכיון ה-web לבין העמוד החי,
    ולכן פונקציה אחת משרתת את שני המקורות. ההיפוך יכול להיות
    יחסי (עמוד חי) או מלא (כתובת ארכיון) - שניהם מכילים את
    נתיב העונה ומזהה ה-VOD בתוך ה-href, ומשם בונים כתובת
    קנונית לעמוד ה-VOD של הפרק.
    """

    import html as html_lib

    anchor_pat = re.compile(
        r'<a[^>]+href="[^"]*?'
        + re.escape(season_dir)
        + r'/VOD-([0-9a-f]+)\.htm[^"]*"[^>]*>(.*?)</a>',
        re.S,
    )

    mapping = {}

    for vid, raw_text in anchor_pat.findall(html_text or ""):

        text = re.sub(r"<[^>]+>", " ", raw_text)
        text = html_lib.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()

        m = re.search(r"פרק\s*(\d+)", text)

        if m:
            mapping[int(m.group(1))] = (
                "https://www.mako.co.il/"
                f"{base_path}/{season_dir}/VOD-{vid}.htm"
            )

    return mapping


def mako_fetch_hub_html_via_jina(page_url):
    """
    שליפת עמוד השער החי של מאקו דרך r.jina.ai (קורא אתרים מבצעי).

    web.archive.org יורד מדי פעם לגמרי ("Temporarily Offline") וגם
    לא מחזיק תמיד צילום עדכני, ואז פתרון הסדרה נשאר בלי מקור.
    r.jina.ai משחזר את העמוד החי מצד השרתים שלו - כולל רשימת
    הפרקים - וחוזר 200 גם כשמאקו עצמו חוסם כתובות IP של ענן
    בהגנת Radware. מוחזר גוף HTML מלא, או None בכישלון.
    """

    try:

        # בלי כותרת User-Agent מתחזה: קורא של r.jina.ai מחזיר 403
        # כשהלקוח נראה כמו דפדפן שאינו דפדפן. עם ברירת המחדל של
        # Python ו-X-Return-Format: html מוחזר גוף HTML מלא של העמוד.
        req = urllib.request.Request(
            "https://r.jina.ai/" + page_url,
            headers={
                "X-Return-Format": "html",
            },
        )

        body = None

        # ניסיון שני - r.jina.ai מגיב מדי פעמים 403 חד-פעמי
        # על בקשות מאותו מקום.
        for jina_attempt in range(2):

            try:

                with urllib.request.urlopen(req, timeout=90) as resp:
                    body = resp.read().decode("utf-8", "replace")
                break

            except Exception as jina_ex:

                if jina_attempt == 0:
                    print(
                        "Mako jina: first attempt failed ("
                        + str(jina_ex)[:100] + "), retrying",
                        flush=True,
                    )
                    time.sleep(3)

        if body is None:
            raise RuntimeError("jina unreachable after 2 attempts")

        # דף חסימה של Radware שעבר דרך jina לא מכיל קישורי VOD -
        # נרשם בלוג אך עדיין מוחזר: קוראי הגוף מחלצים ממנו גם את
        # דפוסי העונות (slug-sN) גם כשאין בו עוגני פרקים.
        if "VOD-" not in body:
            print(
                "Mako jina: hub page fetched but no VOD links inside",
                flush=True,
            )

        return body

    except Exception as ex:
        print(
            "Mako jina: fetch failed: " + str(ex)[:120],
            flush=True,
        )
        return None


def mako_extract_season_dirs(html_text, hub_slug):
    """
    מספרי העונות המופיעים ב-HTML של עמוד שער של סדרה.

    דפוסי slug-sN מופיעים בשני אורכים: קישורי עונה ישירים
    (.../eretz_nehederet-s13/) וקישורי VOD בתוך עונה
    (.../eretz_nehederet-s13/VOD-xxx.htm). נחלץ רק כאלה שאחריהם
    מופיע סלש-VOD או גבול מילה - כדי שלא ניתפסו סדרות אחרות
    שמתחילות באותו שם. מוחזרת רשימה ממוינת מהעונה החדשה לישנה.
    """

    return sorted(
        {
            int(n)
            for n in re.findall(
                re.escape(hub_slug) + r"-s(\d{1,2})(?:/VOD-|\b)",
                html_text or "",
            )
        },
        reverse=True,
    )


def mako_season_from_url(url):
    """
    חילוץ מספר עונה מכתובת עמוד עונה של מאקו.

    עמודי העונה של מאקו נושאים את העונה בסיומת הנתיב:
      .../mako-vod-keshet/nutuk_drama-s1/          (עמוד שער של עונה)
      .../mako-vod-keshet/nutuk_drama-s1/VOD-...   (פרק בתוך עונה)
    מוחזר מספר שלם, או None אם אין סיומת עונה בכתובת.
    """

    if not isinstance(url, str) or not url:
        return None

    path = urllib.parse.urlparse(url).path or ""

    m = re.search(r"-s(\d{1,2})(?:/|$)", path)

    return int(m.group(1)) if m else None


def mako_episode_map(page_url, season, trace=None):
    """
    רשימת פרקי עונה שלמה של סדרת מאקו: מיפוי מספר פרק -> קישור VOD.

    אותם מקורות בדיוק כמו פתרון פרק בודד (mako_resolve_episode_via_wayback):
    צילום עמוד השער מארכיון ה-web, ובהיעדרו עמוד השער החי דרך r.jina.ai.
    חילוץ העוגנים משותף - mako_parse_hub_episode_map - וגם המטמון
    משותף עם הפותר הקיים, כך בקשת פרק אחרי רשימה (ולהפך) לא גוררת
    גישה כפולה לארכיון.

    מוחזר מילון (ריק אם לא נמצא כלום), בלי חריגות - התנהגות זהה
    לפותר הפרק הבודד.
    """

    if (
        not (page_url or "")
        or "mako.co.il" not in page_url
        or "VOD-" in page_url
        or ".m3u8" in page_url.lower()
    ):
        return {}

    parsed = urllib.parse.urlsplit(page_url)
    path = (parsed.path or "").strip("/")

    if not path or "/" not in path:
        return {}

    cache_key = (path, season)

    cached = MAKO_WAYBACK_CACHE.get(cache_key)

    if cached:

        if trace is not None:
            trace.append(f"episodes: {len(cached)} episodes from cache")

        return dict(cached)

    slug = path.rsplit("/", 1)[-1]
    base_path = path.rsplit("/", 1)[0]

    # קישור שמגיע מהחיפוש המאוחד כבר כולל את העונה בנתיב
    # (.../nutuk_drama-s1/), ואילו קישור סדרה רגיל לא (.../nutuk_drama).
    # לא להוסיף -sN פעמיים - אחרת החיפוש "nutuk_drama-s1-s1" לא ימצא
    # דבר והעונה תחזור ריקה.
    if re.search(r"-s\d{1,2}$", slug):

        season_dir = slug

    else:

        season_dir = f"{slug}-s{season}"

    html_text = None

    # מקור 1: צילום עמוד השער בארכיון ה-web.
    try:

        # sort=reverse: הצילומים החדשים ראשה - בלי זה CDX מחזיר את
        # 50 הצילומים הישנים ביותר, וסדרה ותיקה היתה מקבלת צילום
        # בן עשור עם עונות ישנות בלבד.
        cdx_url = (
            "https://web.archive.org/cdx/search/cdx"
            f"?url={parsed.netloc}/{path}"
            "&output=json&fl=timestamp,original,statuscode"
            "&limit=50&sort=reverse"
        )

        req = urllib.request.Request(
            cdx_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )

        with urllib.request.urlopen(req, timeout=40) as resp:
            rows = json.loads(resp.read().decode("utf-8", "replace"))

        snapshots = [
            (row[0], row[1])
            for row in (rows or [])[1:]
            if len(row) >= 3 and row[2] == "200"
        ]

        if snapshots:

            latest_ts, latest_url = max(snapshots, key=lambda r: r[0])

            snap_req = urllib.request.Request(
                f"https://web.archive.org/web/{latest_ts}/{latest_url}",
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            )

            with urllib.request.urlopen(snap_req, timeout=45) as resp:
                html_text = resp.read().decode("utf-8", "replace")

    except Exception as ex:

        if trace is not None:
            trace.append("episodes: wayback failed: " + str(ex)[:100])

        print(
            "Mako episodes: wayback failed: " + str(ex)[:120],
            flush=True,
        )

    mapping = {}

    # מקור 1: עוגני הפרקים מצילום ארכיון ה-web (אם הוחזר).
    if html_text:

        mapping = mako_parse_hub_episode_map(
            html_text, base_path, season_dir
        )

        if mapping:
            MAKO_WAYBACK_CACHE[cache_key] = dict(mapping)

    # מקור 2: עמוד השער החי דרך r.jina.ai - גם כשארכיון ה-web נכשל
    # כליל וגם כשהצילום הצליח אך אינו מכיל את העונה (צילום ישן).
    if not mapping:

        try:
            jina_html = mako_fetch_hub_html_via_jina(page_url)
        except Exception as ex:
            jina_html = None

            if trace is not None:
                trace.append("episodes: jina failed: " + str(ex)[:100])

            print(
                "Mako episodes: jina failed: " + str(ex)[:120],
                flush=True,
            )

        if jina_html:

            mapping = mako_parse_hub_episode_map(
                jina_html, base_path, season_dir
            )

            if mapping:
                MAKO_WAYBACK_CACHE[cache_key] = dict(mapping)

    if trace is not None:
        trace.append(
            f"episodes: mapped {len(mapping)} episodes for season {season}"
        )

    return mapping


def mako_resolve_episode_via_wayback(
    page_url, season=None, episode=None, trace=None
):
    """
    פתרון "סדרה + עונה + פרק" -> קישור VOD ישיר, בלי לגעת בעמוד
    השער של מאקו.

    עמודי השער של סדרות מאקו מוגנים באתגר hCaptcha של Radware
    ("Anomaly Detected") - גם דפדפן אמיתי מקבל אותו מכתובות IP
    של שרתים, ולכן הניווט "פתח את הסדרה ולחץ על הפרק" נכשל.
    עמודי VOD עצמם מוגנים רק באתגר JavaScript שהדפדפן עובר
    לבד, ולכן כל מה שצריך הוא מזהה ה-VOD של הפרק.

    ארכיון ה-web (web.archive.org) שומר צילומים של עמודי השער,
    ובתוכם רשימת הפרקים: טקסט העוגן כולל "פרק N" והקישור מוביל
    לעמוד ה-VOD של אותו פרק. המיפוי כאן דטרמיניסטי ונשמר
    בזיכרון התהליך. אם אין צילום, או שהפרק חדש מדי וטרם נארכב -
    מוחזר None והזרימה הישנה (עמוד השער בדפדפן) מנסה את מזלה.
    """

    import html as html_lib

    def note(message):
        # אבחון: רשימת שלבי הפתרון שתוצמד לתשובת שגיאה, כדי
        # שנוכל לראות מה בדיוק נכשל גם בלי גישה ללוגי השרת.
        if trace is not None:
            trace.append(message)

    def resolve_from_jina():

        jina_html = mako_fetch_hub_html_via_jina(page_url)

        if not jina_html:
            note("jina: hub fetch failed")
            return None

        jina_mapping = mako_parse_hub_episode_map(
            jina_html, base_path, season_dir
        )

        if not jina_mapping:
            note("jina: hub fetched but no episode anchors parsed")
            return None

        print(
            "Mako jina: "
            f"mapped {len(jina_mapping)} episodes from live hub /{path}",
            flush=True,
        )

        note(f"jina: mapped {len(jina_mapping)} episodes from live hub")

        MAKO_WAYBACK_CACHE[cache_key] = jina_mapping

        resolved_ep = jina_mapping.get(int(episode))

        if resolved_ep:
            note(f"jina: episode {episode} -> VOD link")
        else:
            note(
                f"jina: episode {episode} missing "
                f"({len(jina_mapping)} episodes known)"
            )

        return resolved_ep

    if not (season and episode):
        return None

    if (
        "mako.co.il" not in (page_url or "")
        or "VOD-" in page_url
        or ".m3u8" in page_url.lower()
    ):
        return None

    parsed = urllib.parse.urlsplit(page_url)
    path = (parsed.path or "").strip("/")

    if not path or "/" not in path:
        # אין מקטע סדרות בנתיב - אין מה לפתור
        return None

    slug = path.rsplit("/", 1)[-1]
    # בסיס הנתיב בלי ה-slug: "mako-vod-keshet/nutuk_drama" ->
    # "mako-vod-keshet". עמודי הפרקים יושבים מתחתיו בתיקיית העונה.
    base_path = path.rsplit("/", 1)[0]

    # קישור שמגיע מהחיפוש המאוחד כבר כולל את העונה בנתיב
    # (.../nutuk_drama-s1/), ואילו קישור סדרה רגיל לא (.../nutuk_drama).
    # לא להוסיף -sN פעמיים - אחרת החיפוש "nutuk_drama-s1-s1" לא ימצא
    # דבר והעונה תחזור ריקה.
    if re.search(r"-s\d{1,2}$", slug):

        season_dir = slug

    else:

        season_dir = f"{slug}-s{season}"

    cache_key = (path, season)

    mapping = MAKO_WAYBACK_CACHE.get(cache_key)

    if mapping is None:

        # sort=reverse: הצילומים החדשים ראשה. בלי זה CDX מחזיר את
        # 50 הצילומים הישנים ביותר - סדרה ותיקה עם אלפי צילומים
        # היתה מקבלת צילום בן עשור עם עונות ישנות בלבד.
        cdx_url = (
            "https://web.archive.org/cdx/search/cdx"
            f"?url={parsed.netloc}/{path}"
            "&output=json&fl=timestamp,original,statuscode"
            "&limit=50&sort=reverse"
        )

        snapshots = []

        # web.archive.org איטי ולא יציב משרתי ענן - שני ניסיונות
        for attempt in range(2):

            try:

                req = urllib.request.Request(
                    cdx_url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        )
                    },
                )

                with urllib.request.urlopen(req, timeout=40) as resp:
                    rows = json.loads(
                        resp.read().decode("utf-8", "replace")
                    )

                snapshots = [
                    (row[0], row[1])
                    for row in (rows or [])[1:]
                    if len(row) >= 3 and row[2] == "200"
                ]

                break

            except Exception as ex:

                note(
                    f"wayback: cdx attempt {attempt + 1} failed: "
                    + str(ex)[:100]
                )

                print(
                    "Mako wayback: CDX query failed "
                    f"(attempt {attempt + 1}): " + str(ex)[:120],
                    flush=True,
                )

        if not snapshots:

            # ארכיון ה-web לא זמין (הוא יורד מדי פעם לגמרי) או שאין
            # צילום - מנסים לשלוף את עמוד השער החי דרך r.jina.ai,
            # שמצליח לעבור את הגנת Radware מכתובות ה-IP שלו.
            note("wayback: no usable snapshots")
            return resolve_from_jina()

        latest_ts, latest_url = max(snapshots, key=lambda r: r[0])

        try:

            snap_url = (
                f"https://web.archive.org/web/{latest_ts}/{latest_url}"
            )

            req = urllib.request.Request(
                snap_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            )

            with urllib.request.urlopen(req, timeout=45) as resp:
                html_text = resp.read().decode("utf-8", "replace")

        except Exception as ex:

            note(
                "wayback: snapshot fetch failed: " + str(ex)[:100]
            )

            print(
                "Mako wayback: snapshot fetch failed: " + str(ex)[:120],
                flush=True,
            )

            return resolve_from_jina()

        mapping = mako_parse_hub_episode_map(
            html_text, base_path, season_dir
        )

        print(
            "Mako wayback: "
            f"mapped {len(mapping)} episodes from snapshot "
            f"{latest_ts} of /{path}",
            flush=True,
        )

        note(
            f"wayback: snapshot {latest_ts} mapped {len(mapping)} episodes"
        )

        MAKO_WAYBACK_CACHE[cache_key] = mapping

        if not mapping:

            # צילום ישן בלי רשימת פרקים שמישה - אותו פתרון חי
            note("wayback: snapshot had no episode anchors")
            return resolve_from_jina()

    resolved = mapping.get(int(episode))

    if resolved:
        note(f"resolved season {season} episode {episode} from cache/source")
        print(
            "Mako wayback: season "
            f"{season} episode {episode} -> {resolved}",
            flush=True,
        )
    else:
        note(
            f"episode {episode} not in episode list "
            f"({len(mapping)} episodes known)"
        )
        print(
            "Mako wayback: episode "
            f"{episode} not in archived list for season {season} "
            f"({len(mapping)} episodes known)",
            flush=True,
        )

    return resolved


def mako_acquire_stream_ticket(media_url, channel_id=None):
    """
    הנפקת טיקט Akamai משירות ההרשאות של מאקו - אותו שירות שהנגן
    עצמו פונה אליו (mass.mako.co.il). השירות אינו מוגן על ידי
    Radware ולכן זמין גם מכתובות IP של ענן, בניגוד ל-AjaxPage
    ול-CDN עצמו. הטיקט (hdnea=...) מוצמד לכתובת הפלייליסט ופותח
    אותה מכל IP למשך כ-15 דקות.

    ה-payload מוצפן AES-CBC עם המפתחות שמוטמעים בקוד הלקוח של
    הנגן (מפוענחים מ-chunk ה-Next.js שלהם). המפתח הוא מחרוזת
    UTF-8 של 24 תווים - כלומר AES-192, ולא base64.
    """

    path = urllib.parse.urlparse(media_url or "").path

    if not path or not path.lower().endswith(".m3u8"):
        return None

    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad, unpad
    except ImportError:
        from Cryptodome.Cipher import AES
        from Cryptodome.Util.Padding import pad, unpad

    payload = {
        # lp: הנתיב של הפלייליסט, rv: ספק ה-CDN, du: מזהה מכשיר
        # (אקראי - השירות לא מאמת אותו), dv: מזהה הערוץ, na: גרסה
        "lp": path,
        "rv": "akamai",
        "du": str(uuid.uuid4()),
        "dv": channel_id or "1",
        "na": "7.24.0",
    }

    key = b"YhnUaXMmltB6gd8p9SWleQ=="
    iv = b"theExact16Chars="

    cipher = AES.new(key, AES.MODE_CBC, iv)

    body = base64.b64encode(
        cipher.encrypt(pad(json.dumps(payload).encode("utf-8"), 16))
    ).decode("ascii")

    req = urllib.request.Request(
        "https://mass.mako.co.il/ClicksStatistics/"
        "entitlementsServicesV2.jsp?et=egt",
        data=body.encode("utf-8"),
        headers={
            "Content-Type": "text/plain;charset=UTF-8",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Origin": "https://www.mako.co.il",
            "Referer": "https://www.mako.co.il/",
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", "replace")

    except Exception as ex:

        print(
            "Mako ticket service error: " + str(ex),
            flush=True
        )
        return None

    try:

        plain = unpad(
            AES.new(key, AES.MODE_CBC, iv).decrypt(
                base64.b64decode(raw.strip())
            ),
            16,
        )
        data = json.loads(plain.decode("utf-8"))

    except Exception:

        print(
            "Mako ticket service: unexpected response",
            flush=True
        )
        return None

    if str(data.get("caseId", "")) != "1":

        print(
            "Mako ticket service rejected: "
            + str(data.get("status", "unknown")),
            flush=True
        )
        return None

    for ticket in data.get("tickets") or []:

        t = (ticket or {}).get("ticket") or ""

        if t:
            return t

    return None


def mako_headless_stream(page_url):
    """
    שרשרת פתרון ללא דפדפן עבור עמודי VOD של mako-vod.

    עמודי הפריט של מאקו נפתחים גם בבקשת HTTP פשוטה (Radware חוסם
    את AjaxPage ואת עמודי השער, אך לא אותם), ובתוך ה-JSON שנטמע
    בעמוד (__NEXT_DATA__) יש VideoObject עם contentUrl - כתובת HLS
    של הפריט על CloudFront. מהנתיב שלה מסיקים את נתיב /i/VOD/ המקביל
    על mako-vod.akamaized.net - ה-host ששירות הטיקטים בנוי עבורו -
    מנפיקים טיקט Akamai מ-mass.mako.co.il (שירות שאינו עובר דרך
    Radware) ומחזירים את הפלייליסט המאומת.

    כל השלבים עובדים גם מכתובות IP של ענן, ולכן השרשרת עדיפה על
    סריקת הדפדפן, שמאקו חוסם מדי פעם. מוחזר (כתובת m3u8, עוגיות
    ריקות) בהצלחה, או None בכישלון - ואז הזרימה הוותיקה ממשיכה.

    לוגיקת ה-hdnea הוותיקה נשמרת: הכתובת שמוחזרת היא פלייליסט עם
    טוקן Akamai חתום (hdnea=...), בדיוק כמו ה-"Stream candidate (200)"
    שנתפס בעבר בתוך הדפדפן - בלי הטוקן ה-CDN מחזיר Access Denied.
    """

    try:

        html = None

        # עמוד הפריט - קודם ישירות מהשרת הזה, ובחסימה דרך r.jina.ai
        # (אותו עוקף שכבר פותר את עמודי השער - הוא מריץ את העמוד
        # מצד השרתים שלו ומחזיר את ה-HTML המלא, כולל __NEXT_DATA__).
        req = urllib.request.Request(
            page_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html",
            },
        )

        try:

            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", "replace")

        except Exception as direct_ex:

            print(
                "Mako headless: direct fetch failed ("
                + str(direct_ex)[:100] + "), trying jina",
                flush=True,
            )

        if not html or "contentUrl" not in html:

            html = mako_fetch_hub_html_via_jina(page_url)

        if not html:

            return None

        m = re.search(
            r'"contentUrl"\s*:\s*"([^"]+?\.m3u8[^"]*)"',
            html.replace("\\/", "/"),
        )

        if not m:

            print(
                "Mako headless: no contentUrl in VOD page",
                flush=True,
            )
            return None

        content_url = m.group(1)

        # הסקת נתיב אקמאי מהנתיב של קלאודפרונט:
        # /hls/VOD/<...>/<פריט>/<פריפיקס>,<קצבים>,.mp4.csmil/index.m3u8
        # -> /i/VOD/<...>/<פריט>/<פריפיקס>,<קצבים>,.mp4.csmil/master.m3u8
        cf_parts = urllib.parse.urlparse(content_url).path.split("/")

        try:

            vod_i = cf_parts.index("VOD")

        except ValueError:

            print(
                "Mako headless: unexpected contentUrl path",
                flush=True,
            )
            return None

        akamai_path = (
            "/i/" + "/".join(cf_parts[vod_i:-1]) + "/master.m3u8"
        )

        template = (
            "https://mako-vod.akamaized.net" + akamai_path
        )

        ticket = mako_acquire_stream_ticket(template)

        if not ticket:

            print(
                "Mako headless: ticket service refused",
                flush=True,
            )
            return None

        stream = template + "?" + ticket

        # אימות שהפלייליסט באמת נפתח לפני שמוותרים על שאר הזרימות.
        req2 = urllib.request.Request(
            stream,
            headers={"User-Agent": "Mozilla/5.0"},
        )

        with urllib.request.urlopen(req2, timeout=20) as resp2:

            head = resp2.read(16)

        if not head.startswith(b"#EXTM3U"):

            raise RuntimeError("not a valid m3u8 response")

        print(
            "Mako headless: validated playlist for " + akamai_path,
            flush=True,
        )

        return (stream, "")

    except Exception as ex:

        print(
            "Mako headless: failed: " + str(ex)[:120],
            flush=True,
        )
        return None


def mako_fail_fast_hub(page_url, season=None, episode=None):
    """
    כישלון מהיר לעמוד שער של סדרת מאקו שלא נפתר לפרק.

    הבעיה: קישור סדרה בלי season/episode מוביל לסריקת דפדפן
    מלאה של עמוד שמוגן Radware, והיא חוזרת על עצמה שלוש פעמים
    בתוך extract_hidden_m3u8 - בערך 4-5 דקות של המתנה שנגמרות
    תמיד באותה שגיאה. המשתמש רואה תקיעה במקום תשובה.

    עמודי VOD עצמם (VOD-) ופלייליסטים נשארים בזרימה המלאה -
    שם הסריקה באמת מוסיפה ערך.
    """

    if (
        "mako.co.il" not in (page_url or "")
        or "VOD-" in page_url
        or ".m3u8" in page_url.lower()
    ):
        return False

    parsed = urllib.parse.urlsplit(page_url)

    path = (parsed.path or "").strip("/")

    # רק עמודי סדרות VOD (mako-vod-*): עמודי כתבות וחדשות של מאקו
    # ממשיכים לעבור סריקה מלאה - שם הווידאו נתפס בהצלחה.
    if "/" not in path or "vod" not in path.lower():
        return False

    # לא נופלים לסריקה כשבקשו פרק מסוים והוא לא נמצא בארכיון/
    # בעמוד החי - כבר עברנו את המיפוי הדטרמיניסטי, וסריקה של
    # אותו עמוד שער לא תוסיף כלום.
    if season and episode:
        return True

    # בלי season/episode: עמוד השער מכיל בעיקר קדימון, ולכן
    # הסריקה כמעט תמיד תיכשל בפרק לא נמצא. בלי מזל, זה 3 ניסיונות
    # × ~90 שניות של דפדפן - התשובה תהיה זהה. כישלון מהיר עם הדרך
    # הנכונה עדיף על המתנה ארוכה.
    return True


def mako_resolve_vod_stream(vod_page_url, cookies_str=""):
    """
    המרת עמוד VOD של מאקו לכתובת m3u8 מאומתת (עם טוקן hdnea).

    קישור VOD שנשלח ישירות ל-yt-dlp מקבל 403 מ-Radware - הוא לא
    מחלץ ממאקו. צריך קודם לפתור את הפלייליסט המאומת: קודם הנתיב
    ללא דפדפן (mako_headless_stream), ואז הסריקה המלאה
    (extract_hidden_m3u8) כגיבוי. מוחזר (כתובת מדיה, עוגיות) או
    (None, "") בכישלון.
    """

    headless = mako_headless_stream(vod_page_url)

    if headless:
        return headless

    try:
        return extract_hidden_m3u8(
            vod_page_url,
            season=None,
            episode=None
        )
    except Exception as ex:

        print(
            "Mako VOD stream resolution failed: "
            + str(ex)[:150],
            flush=True,
        )
        return (None, "")


def mako_title_from_media_url(media_url):
    """
    שם תיאורי לקובץ מתוך כתובת ה-m3u8 של מאקו.

    מבנה הנתיב: .../VOD/<מותג>/<סדרה...>/S01/EP/<קוד>_<NN>_<...>/
    למשל Nutuk_Clean/S01/EP/Nutuk_01_271025_VOD_vce413 →
    "Nutuk - עונה 1 פרק 01". אם המבנה לא מזוהה - מוחזר קטע
    הנתיב האחרון, ואם גם זה נכשל - שם גנרי.
    """

    try:
        path = urllib.parse.urlsplit(media_url).path
    except Exception:
        path = ""

    parts = [p for p in (path or "").split("/") if p]

    # איתור S01/EP - הסדרה מתחילה שני מקטעים קודם (אחרי /i/VOD/),
    # ומספר הפרק הוא החלק השני בקוד הפריט מתחת ל-EP.
    season_num = None
    episode_num = None
    series_name = None

    for idx, part in enumerate(parts):

        m_season = re.match(r"^S(\d{1,2})$", part, re.I)

        if m_season and idx + 1 < len(parts) and parts[idx + 1].upper() == "EP":

            season_num = int(m_season.group(1))

            if idx + 2 < len(parts):

                ep_code = parts[idx + 2]

                m_ep = re.search(r"_(\d{1,3})_", ep_code)

                if m_ep:
                    episode_num = int(m_ep.group(1))

            # הסדרה: שלושה מקטעים לפני S01 - /i/, /VOD/, <מותג>
            if idx >= 3 and parts[idx - 3].upper() == "VOD":
                series_name = parts[idx - 1]

            break

    if series_name:
        series_name = series_name.replace("_", " ").strip()

    if season_num is not None and episode_num is not None:

        base = series_name or "פרק"

        return (
            "{} - עונה {} פרק {}".format(
                base, season_num, episode_num
            )
        )

    if parts:
        tail = parts[-1]

        tail = re.sub(r"\.m3u8.*$", "", tail)

        tail = re.sub(r",.*$", "", tail)

        tail = tail.replace("_", " ").strip()

        if tail:
            return tail

    return "mako_video"


def extract_hidden_m3u8(url, season=None, episode=None):
    """
    מעטפת עם ניסיונות חוזרים סביב סריקת הזרם.

    הגנת Radware מתנהגת בצורה לא עקבית: אותו עמוד עובר בניסיון
    אחד ונחסם באחר (לפעמים לחלוטין, לפעמים אחרי דקות). במקום
    ניסיון אחד, מריצים את הסריקה עד שלוש פעמים עם הפסקות
    הולכות וגדלות, ומחזירים את ההצלחה הראשונה.
    """

    # נתיב ללא דפדפן לעמודי VOD של מאקו - ראה mako_headless_stream.
    # רץ לפני כל הניסיונות, ורק עבור כתובות פריט ישירות (VOD-):
    # עמוד שער של סדרה מכיל contentUrl של הקדימון ולא של פרק,
    # ולכן אותו חייבים לפתור קודם דרך season/episode כרגיל.
    if "mako.co.il" in (url or "") and "VOD-" in (url or ""):

        headless = mako_headless_stream(url)

        if headless:
            return headless

    # עמוד שער של סדרה שלא נפתר לפרק - כישלון מהיר במקום 3 סריקות
    # דפדפן של כ-90 שניות כל אחת שמסתיימות תמיד באותה שגיאה
    # (זה מה שנראה כ"תקיעה" של דקות ב-benchmark מ-GitHub Actions).
    if mako_fail_fast_hub(url, season=season, episode=episode):

        raise RuntimeError(
            "קישור סדרת מאקו צריך עונה ופרק כדי להוריד פרק: שלחו את "
            "הכתובת עם השדות הנפרדים season ו-episode (למשל 1 ו-1), "
            "או קישור VOD ישיר של הפרק "
            "(.../nutuk_drama-s1/VOD-....htm)."
        )

    last_error = None

    for attempt in range(3):

        if attempt:
            time.sleep(8 * attempt)

        try:
            return _extract_hidden_m3u8_once(
                url,
                season=season,
                episode=episode
            )

        except RuntimeError as e:

            last_error = e

            print(
                f"Scraper attempt {attempt + 1}/3 failed: "
                f"{str(e)[:150]}",
                flush=True
            )

    raise last_error


def _extract_hidden_m3u8_once(url, season=None, episode=None):

    print(
        f"Starting news-site stream scraper for: {url} "
        f"(season={season}, episode={episode})",
        flush=True
    )

    stream_candidates = []
    validation_results = {}
    seen_candidates = set()
    rejected_logged = set()
    ticketed_templates = set()
    found_stream = None
    found_mp4 = None
    cookies_str = ""

    # אבחון סריקה: כל מה שנאסף במהלך הניסיון - מצב העמוד, מספר
    # המועמדים, הסיבות לדחייתם וכישלונות ה-API. מוצמד לשגיאת
    # הסריקה כדי שכישלון ב-Railway יהיה ניתן לאבחון מתוך תשובת
    # ה-API, בלי גישה ללוגי השרת.
    scrape_diag = {"page_title": None, "url": None, "url_is_challenge": None,
                   "content_len": 0, "has_VOD_": False,
                   "candidates": 0, "templates": 0, "tickets": 0,
                   "rejected": [], "api_failed": [], "direct_api_ids": None}

    def mako_scrape_diag(extra=None):

        try:
            scrape_diag["page_title"] = (page.title() or "")[:120]
            scrape_diag["url"] = (page.url or "")[:300]
            scrape_diag["url_is_challenge"] = "perfdrive" in (
                scrape_diag["url"] or ""
            )
        except Exception:
            pass

        try:
            body = page.content()
            scrape_diag["content_len"] = len(body or "")
            scrape_diag["has_VOD_"] = "VOD-" in (body or "")
        except Exception:
            pass

        scrape_diag["candidates"] = len(seen_candidates)
        scrape_diag["rejected"] = sorted(rejected_logged)[:10]

        if extra and extra not in scrape_diag["api_failed"]:
            scrape_diag["api_failed"].append(extra)

        return scrape_diag

    # פרופיל האתר - נדרש לאימות הזרמים בתוך הקונטקסט
    il_referer, il_origin, _il_cookie_domain = il_site_profile(
        url
    )

    # מאקו: נתיב ה-API הישיר - מזהה הפריט מה-URL, שני האחרים מה-HTML
    mako_page_ids = (
        mako_extract_ids(url) if "mako.co.il" in (url or "") else None
    )

    # מזהה הערוץ שנלכד מהעמוד - דרוש להנפקת הטיקט. נלכד מוקדם
    # כדי שגם ניווט אתגר Radware באמצע הסריקה לא יאבד אותו.
    mako_channel_id = None

    def add_candidate(raw_url):
        """
        הוספת מועמד חד-פעמית. האתר משדר את אותה כתובת עשרות פעמים
        בתוך שניות (בגוף ה-API, ב-HTML, ב-iframes) ובלי זה האימות
        היה רץ שוב ושוב על אותו URL והלוג היה מתמלא בזבל.
        """

        if not raw_url or raw_url in seen_candidates:
            return

        seen_candidates.add(raw_url)
        if (("mako-vod.akamaized.net" in raw_url
             or "cloudfront.net" in raw_url)
                and ".m3u8" in raw_url
                and "hdnea" not in raw_url
                and "hdntl" not in raw_url):
            scrape_diag["templates"] += 1
        stream_candidates.append(
            (il_candidate_score(raw_url), raw_url)
        )

    def validate_hls_in_context(stream_url):
        """
        מוודא שהפלייליסט באמת נגיש. למאקו האימות רץ בתוך הדף עצמו
        (fetch של הדפדפן - טביעת TLS אמיתית, עוגיות Radware, וכותרת
        Origin שנשלחת אוטומטית) בדיוק כמו שהנגן שולח את הבקשה. מחוץ
        למאקו נשאר אימות רגיל דרך context.request.
        פלייליסט פרסומות שמוחזר 403 נפסל כאן במקום להגיע אל
        ffmpeg/yt-dlp ולהיכשל שם.
        """

        if mako_page_ids:

            try:

                scrape_diag["direct_api_ids"] = {
                    k: bool(v) for k, v in (mako_page_ids or {}).items()
                }
                res = page.evaluate(
                    """
                    async (u) => {
                      try {
                        const r = await fetch(u, {credentials: 'include'});
                        const t = await r.text();
                        return {status: r.status,
                                ok: t.trimStart().startsWith('#EXTM3U')};
                      } catch (e) {
                        return {status: 0, ok: false};
                      }
                    }
                    """,
                    stream_url
                )

                if res and res.get("ok"):
                    return True

                print(
                    f"Mako in-page check: HTTP "
                    f"{(res or {}).get('status', 0)} on playlist",
                    flush=True
                )

                if (res or {}).get("status"):
                    # תשובת HTTP אמיתית מה-CDN - הדחייה סופית
                    return False

                # status 0 - הבקשה נחסמה ברמת הדפדפן (CORS) ולא
                # הגיעה ל-CDN בכלל; ננסה גם מחוץ לדף לפני שמוותרים

            except Exception:
                pass

        try:

            resp = context.request.fetch(
                stream_url,
                method="GET",
                headers={
                    "Referer": il_referer,
                    "Origin": il_origin,
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
                timeout=15000
            )

            if resp.status != 200:
                return False

            body = resp.text()[:512]

            return body.lstrip().startswith("#EXTM3U")

        except Exception:
            return False

    def validate_mp4_in_context(mp4_url):

        try:

            resp = context.request.fetch(
                mp4_url,
                method="HEAD",
                timeout=15000
            )

            return resp.status == 200

        except Exception:
            return False

    try:

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--start-maximized",
                ]
            )

            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="he-IL",
                timezone_id="Asia/Jerusalem"
            )

            page = context.new_page()

            def click_frame_or_page(scope):
                """
                לחיצת ניגון בסקופ נתון (עמוד או frame). נגן מאקו לא
                מתחיל לנגן עד אינטראקציה; לחיצה ישירה על אלמנט ה-video
                (ולא על מיכליו) כי ברוב הנגנים הקלקה על ה-video עצמו
                מתחילה השמעה והפעלת תהליך ה-API שמחזיר כתובת חתומה.
                """

                for selector in (
                    "video",
                    ".jwplayer video",
                    ".video-js video",
                    ".jwplayer",
                    ".video-js",
                    "[aria-label*='הפעל']",
                    "[aria-label*='Play']",
                ):
                    try:
                        el = scope.locator(selector).first
                        if el.count() == 0:
                            continue
                        if not el.is_visible():
                            continue
                        el.click(timeout=1200)
                        return
                    except Exception:
                        continue

            def inspect_response(response):

                nonlocal found_stream, found_mp4

                try:

                    res_url = response.url.lower()

                    noise = (
                        "google-analytics", "googletagmanager",
                        "googleadservices", "perfdrive",
                        "analytics", "collect", "pixel", "track"
                    )

                    if any(x in res_url for x in noise):
                        return

                    if ".m3u8" in res_url or "keshet-vod" in res_url:

                        # לא כל תשובת m3u8 היא הזרם האמיתי - יש גם
                        # פלייליסטים של פרסומות. כל המועמדים נאספים,
                        # מדורגים, ורק מי שעובר אימות נשלח הלאה.
                        if (
                            200 <= response.status < 300
                            and not any(
                                x in res_url
                                for x in IL_STREAM_NOISE
                            )
                        ):
                            add_candidate(response.url)

                            print(
                                f"Stream candidate ({response.status}): "
                                f"{response.url}",
                                flush=True
                            )

                        return

                    # כתובת mp4 ישירה - חלק מהאתרים (בעיקר כאן 11)
                    # מזרימים mp4 רציף ולא HLS. m3u8 עדיף, ולכן
                    # שומרים את זה רק כגיבוי.
                    if (
                        not found_mp4
                        and ".mp4" in res_url
                        and 200 <= response.status < 300
                        and not any(
                            x in res_url
                            for x in IL_STREAM_NOISE
                        )
                    ):
                        found_mp4 = response.url
                        print(
                            f"Caught direct mp4 URL: {response.url}",
                            flush=True
                        )
                        return

                    content_type = response.headers.get(
                        "content-type", ""
                    ).lower()

                    if any(
                        t in content_type
                        for t in ("json", "text", "javascript")
                    ):

                        body = response.text()

                        matches = re.findall(
                            r'https?://[^"\'<>\s]+\.m3u8[^"\'<>\s]*',
                            body
                        )

                        for m in matches:

                            m_clean = m.replace("\\/", "/")

                            if not any(
                                x in m_clean.lower()
                                for x in ("analytics", "google", "ad")
                            ):
                                # גם מועמד שנתפס בתוך גוף API חייב לעבור
                                # אימות כמו כל מועמד אחר: פלייליסט שמחזיר
                                # 403 מחוץ לנגן (פרסומות / טוקן לא תקף)
                                # לא יגיע עוד ישירות אל ffmpeg/yt-dlp
                                # ויכשיל את כל ההורדה.
                                # ההדפסה רק על מועמד חדש בפועל -
                                # add_candidate מדדפל, והלוג לא יוצף
                                # באותה כתובת עשרות פעמים.
                                is_new = m_clean not in seen_candidates
                                add_candidate(m_clean)

                                if is_new:
                                    print(
                                        "Stream candidate inside API body: "
                                        f"{m_clean}",
                                        flush=True
                                    )

                except Exception:
                    pass

            page.on("response", inspect_response)

            def mako_direct_playlist():
                """
                נתיב ה-API הישיר של מאקו: שולף את רשימת המדיה מה-API
                שהנגן פונה אליו (playlist12.jsp) - מתוך קונטקסט הדף,
                כולל העוגיות שעברו את Radware - ומפענח אותה בדפדפן
                בעזרת WebCrypto. ללא ספריות חיצוניות וללא תלות בניגון.
                זהו הנתיב הדטרמיניסטי - הלחיצות וההאזנה לרשת הן רק
                גיבוי למקרה שמאקו ישנו את מבנה ה-API.
                """

                nonlocal mako_channel_id

                if not mako_page_ids:
                    return

                try:

                    html = page.content()

                    ids = mako_ids_from_html(html)

                    mako_channel_id = ids.get("channelId")

                    if "itemVcmId" not in ids or "channelId" not in ids:

                        print(
                            "Mako direct API: channel ids not found in page",
                            flush=True
                        )
                        return

                    m_urls = []

                    res = page.evaluate(
                        MAKO_PLAYLIST_JS,
                        [
                            ids["itemVcmId"],
                            ids["channelId"],
                            ids.get("galleryChannelId", "")
                        ]
                    )

                    if not (res or {}).get("ok"):

                        mako_scrape_diag(
                            ["Mako direct API failed: "
                             + str((res or {}).get("why", "unknown"))]
                        )
                        print(
                            "Mako direct API failed: "
                            + str((res or {}).get("why", "unknown")),
                            flush=True
                        )

                    else:

                        body = res["body"]

                        # בתוך הפלייליסט המפוענח: media[] עם url לכל איכות.
                        # הנגן עצמו מנרמל http -> https
                        # (replaceUnsecuredProtocols) - אחרת הדפדפן חוסם
                        # mixed-content ואימות ה-fetch מהדף נכשל.
                        m_urls = [
                            u.replace("http://", "https://")
                            for u in re.findall(
                                r'"url":"([^"]+)"',
                                body.replace("\\/", "/")
                            )
                        ]

                        added = 0

                        for mu in m_urls:

                            if ".m3u8" in mu and not any(
                                x in mu.lower() for x in IL_STREAM_NOISE
                            ):

                                add_candidate(mu)
                                added += 1

                        print(
                            f"Mako direct API: {added} playlist URLs "
                            "from media list",
                            flush=True
                        )

                    # שלב המפתח: הנפקת טיקט Akamai משירות ההרשאות של
                    # מאקו (mass.mako.co.il - לא עובר דרך Radware).
                    # הטיקט הוא מה שהופך את פלייליסט הפריט לנגיש
                    # מכל IP - בליו ה-CDN מחזיר Access Denied.
                    template = None

                    for mu in m_urls:

                        if (".m3u8" in mu and "hdntl" not in mu
                                and not any(
                                    x in mu.lower()
                                    for x in IL_STREAM_NOISE
                                )):

                            template = mu
                            break

                    if not template:

                        hm = re.search(
                            r'https://mako-vod\.akamaized\.net'
                            r'/i/VOD/[^"\'\\\s<>]+?master\.m3u8',
                            html.replace("\\/", "/")
                        )

                        template = hm.group(0) if hm else None

                    if template:

                        ticket = mako_acquire_stream_ticket(
                            template,
                            ids.get("channelId")
                        )

                        if ticket:

                            sep = "&" if "?" in template else "?"

                            add_candidate(template + sep + ticket)

                            ticketed_templates.add(template)

                            print(
                                "Mako ticket: issued for " + template,
                                flush=True
                            )

                    else:

                        print(
                            "Mako ticket: no playlist URL found in page",
                            flush=True
                        )

                except Exception as ex:

                    print(
                        "Mako direct API error: " + str(ex),
                        flush=True
                    )

            def mako_ticket_candidates():
                """
                הנפקת טיקט Akamai לכל תבנית פלייליסט של מאקו שנאספה
                עד עכשיו - בנפרד מנתיב ה-API הישיר. כשאתגר Radware
                מנווט את העמוד באמצע הסריקה, קריאת ה-API מתה
                ("Execution context was destroyed") ואיתה גם הטיקט
                שהיה מונפק בתוך אותו try. שירות הטיקטים
                (mass.mako.co.il) אינו מוגן ב-Radware ואינו תלוי
                במצב העמוד, ולכן ההנפקה כאן עובדת גם כשהעמוד עצמו
                חסום - מספיקה תבנית פלייליסט שנתפסה בתשובת API.
                """

                if not mako_page_ids:
                    return

                templates = []

                for _score, cand in list(stream_candidates):

                    if (
                        ".m3u8" in cand
                        and ("mako-vod.akamaized.net" in cand
                             or "cloudfront.net" in cand)
                        and "hdntl" not in cand
                        and "hdnea" not in cand
                        and cand not in ticketed_templates
                    ):

                        templates.append(cand)

                for template in templates:

                    ticketed_templates.add(template)

                    ticket = mako_acquire_stream_ticket(
                        template,
                        mako_channel_id
                    )

                    if ticket:

                        sep = "&" if "?" in template else "?"

                        add_candidate(template + sep + ticket)

                        scrape_diag["tickets"] += 1
                        print(
                            "Mako ticket: issued for " + template,
                            flush=True
                        )

            def try_validate_candidates():
                """
                אימות המועמדים שנאספו - מהמדורג הכי גבוה ומעלה.
                רק פלייליסט שבאמת חוזר 200 עם #EXTM3U נחשב זרם תקף.
                מחזיר True אם נמצא זרם.
                """

                nonlocal found_stream

                if not stream_candidates:
                    return False

                stream_candidates.sort(
                    key=lambda c: c[0],
                    reverse=True
                )

                for _score, cand in list(stream_candidates):

                    # אימות הוא בקשת רשת - כל מועמד נבדק פעם
                    # אחת לכל היותר
                    if cand not in validation_results:

                        validation_results[cand] = \
                            validate_hls_in_context(cand)

                    if validation_results[cand]:

                        found_stream = cand

                        print(
                            "Validated stream: " + cand,
                            flush=True
                        )

                        return True

                    else:

                        if cand not in rejected_logged:

                            rejected_logged.add(cand)
                            mako_scrape_diag()

                            print(
                                "Candidate rejected "
                                "(not accessible): " + cand,
                                flush=True
                            )

                return False

            radware_hard_block = False

            try:

                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=25000
                )

                # שער Radware: מדי פעם הביקור הראשון מקבל עמוד אתגר
                # JavaScript. האתגר מסתיים מעצמו (הוא מציב עוגייה
                # ומרענן לבד), ולכן ממתינים לו במקום לנטוש את הסריקה
                # מיד וליפול ל-yt-dlp שייכשל עם "Unsupported URL".
                def radware_challenge_active():
                    try:
                        t = (page.title() or "").lower()
                    except Exception:
                        return False
                    return "radware" in t or "access denied" in t

                radware_deadline = time.time() + 24

                while (
                    radware_challenge_active()
                    and time.time() < radware_deadline
                ):
                    page.wait_for_timeout(2000)

                if radware_challenge_active():

                    # האתגר לא נפתר. קונטקסט חדש = טביעת דפדפן חדשה,
                    # מריץ את האתגר מאפס ולעיתים עובר בניסיון השני.
                    print(
                        "Radware challenge persisted - retrying with "
                        "a fresh browser context",
                        flush=True
                    )

                    try:
                        context.close()
                    except Exception:
                        pass

                    context = browser.new_context(
                        viewport={"width": 1920, "height": 1080},
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                        locale="he-IL",
                        timezone_id="Asia/Jerusalem"
                    )

                    page = context.new_page()
                    page.on("response", inspect_response)

                    page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=25000
                    )

                    radware_deadline = time.time() + 24

                    while (
                        radware_challenge_active()
                        and time.time() < radware_deadline
                    ):
                        page.wait_for_timeout(2000)

                    if radware_challenge_active():
                        radware_hard_block = True

                try:
                    page.evaluate(
                        "() => { document.querySelectorAll("
                        "'.fc-consent-root, .fc-dialog-overlay')"
                        ".forEach(el => el.remove()); }"
                    )
                except Exception:
                    pass

                # מאקו - נתיב ה-API הישיר. העמוד כבר נטען עם המזהים,
                # אין סיבה לחכות ללחיצות או לניגון: הפלייליסט מתקבל
                # ומפוענח ישירות, והאימות מתרחש בלולאת ההמתנה.
                mako_direct_playlist()

                # גם אם קריאת ה-API נכשלה (אתגר Radware מנווט את
                # העמוד), תבניות שנתפסו בתשובות קודמות מקבלות טיקט
                # כאן - השירות אינו תלוי במצב העמוד.
                mako_ticket_candidates()

                # גלילה מרובה - נגנים מסוימים נטענים רק כשגוללים אליהם
                for _ in range(5):
                    page.mouse.wheel(0, 700)
                    page.wait_for_timeout(600)

                page.wait_for_timeout(1500)

                if season:

                    # סדרה עם כמה עונות: קודם בוחרים את העונה,
                    # ואז הפרק נמצא בתוכה.
                    try:

                        season_locator = page.locator(
                            f"text=עונה {season}"
                        ).first

                        if season_locator.is_visible():

                            season_locator.click(timeout=3000)

                            print(
                                f"Clicked Season {season}",
                                flush=True
                            )

                            page.wait_for_timeout(2500)

                    except Exception as ex:
                        print(f"Season click note: {ex}", flush=True)

                if episode:

                    try:

                        print(
                            f"Searching for Episode {episode}...",
                            flush=True
                        )

                        ep_locator = page.locator(
                            f"text=פרק {episode}"
                        ).first

                        if ep_locator.is_visible():

                            ep_locator.click(timeout=3000)

                            print(
                                f"Clicked Episode {episode}",
                                flush=True
                            )

                            page.wait_for_timeout(4000)

                    except Exception as ex:
                        print(f"Episode click note: {ex}", flush=True)

                else:

                    for selector in (
                        "video",
                        ".video-js",
                        ".jwplayer",
                        ".immergo-player",
                        ".video-player",
                        "[aria-label*='הפעל']",
                        "[aria-label*='Play']",
                        "iframe[src*='player']",
                        "iframe[src*='immergo']",
                        "iframe"
                    ):
                        try:
                            el = page.locator(selector).first
                            if el.is_visible():
                                el.click(timeout=2000)
                                break
                        except Exception:
                            continue

            except Exception as e:
                print(f"Navigation note: {e}", flush=True)

            if radware_hard_block:

                raise RuntimeError(
                    "מאקו חסם את הגישה (הגנת Radware) גם אחרי המתנה "
                    "לאתגר וניסיון עם דפדפן חדש. המתינו כמה דקות "
                    "ונסו שוב.\n\n"
                    + json.dumps(mako_scrape_diag(), ensure_ascii=False)
                )

            # זיהוי חסימת Radware בשלב מוקדם - אם העמוד חסום אין טעם
            # להמשיך 60 שניות של נסיונות לחיצה על עמוד שאינו קיים.
            def page_is_blocked():
                try:
                    title = (page.title() or "").lower()
                    return (
                        "radware" in title
                        or "access denied" in title
                    )
                except Exception:
                    return False

            print(
                "Waiting for real stream initialization...",
                flush=True
            )

            for _ in range(30):

                if found_stream or found_mp4:
                    break

                if page_is_blocked():

                    # אתגר Radware באמצע הסריקה. שירות הטיקטים של
                    # מאקו אינו עובר דרך Radware - גם עמוד חסום לא
                    # מונע הנפקת טיקט לתבנית שכבר נתפסה. מנסים את
                    # הדרך הישירה לפני שנוטשים את הסריקה.
                    print(
                        "Bot protection detected (Radware page) - "
                        "trying ticket fallback before aborting",
                        flush=True
                    )

                    mako_ticket_candidates()

                    if try_validate_candidates():
                        break

                    # האתגר מסתיים מעצמו (עוגייה ורענון). נותנים לו
                    # הזדמנות קצרה לפני נטישת הסריקה.
                    radware_deadline = time.time() + 24

                    while (
                        page_is_blocked()
                        and time.time() < radware_deadline
                    ):
                        page.wait_for_timeout(2000)

                    if page_is_blocked():
                        print(
                            "Bot protection persisted (Radware block "
                            "page) - aborting scrape early.",
                            flush=True
                        )
                        break

                # ניסיונות לחיצה חוזרים. נגן ה-VOD של מאקו יושב בתוך
                # iframe (immergo) - לחיצה על אלמנט ה-iframe בעמוד
                # האב רק ממקדת אותו בלי להפעיל אותו. צריך ללחוץ על
                # הנגן *בתוך* כל frame, וגם ישירות על ה-video element.
                # רק אחרי ניגון אמיתי ה-API מחזיר כתובת m3u8 חתומה.
                if not found_stream:

                    click_frame_or_page(page)

                    for frame in page.frames:
                        if frame is page.main_frame:
                            continue
                        click_frame_or_page(frame)

                page.wait_for_timeout(2000)

                try:

                    content = page.content().replace("\\/", "/")

                    # תוכן iframes - חלק מהנגנים יושבים בתוכם ולא
                    # נתפסים בגוף העמוד עצמו
                    for frame in page.frames:
                        try:
                            content += (
                                "\n"
                                + frame.content().replace("\\/", "/")
                            )
                        except Exception:
                            pass

                    html_matches = re.findall(
                        r'https?://[^"\'<>\s]+\.m3u8[^"\'<>\s]*',
                        content
                    )

                    for hm in html_matches:

                        if not any(
                            x in hm.lower()
                            for x in IL_STREAM_NOISE
                        ):
                            is_new = hm not in seen_candidates
                            add_candidate(hm)

                            if is_new:
                                print(
                                    f"Stream candidate in HTML: {hm}",
                                    flush=True
                                )

                            break

                except Exception:
                    pass

                # הנפקת טיקטים לתבניות חדשות שנתפסו, ואז אימות
                # המועמדים - מהמדורג הכי גבוה ומעלה. רק פלייליסט
                # שבאמת חוזר 200 עם #EXTM3U נחשב זרם תקף.
                mako_ticket_candidates()

                try_validate_candidates()

                if found_stream or found_mp4:
                    break

            cookies = context.cookies()

            cookies_str = "; ".join(
                f"{c['name']}={c['value']}"
                for c in cookies
            )

            browser.close()

        if found_mp4 and not validate_mp4_in_context(
            found_mp4
        ):
            found_mp4 = None

        stream = found_stream or found_mp4

        if stream:
            return stream, cookies_str

        raise RuntimeError(
            "הדפדפן סרק את העמוד אך לא נמצא קישור תקף (m3u8/mp4).\n\n"
            + json.dumps(mako_scrape_diag(), ensure_ascii=False)
        )

    except Exception as e:

        print(f"Scraper error: {e}", flush=True)

        raise RuntimeError(
            f"שגיאה בסריקה: {str(e)}"
        )


# ============================================================
# FFMPEG DIRECT DOWNLOAD FOR M3U8
# ============================================================
# חלק מאתרי החדשות עובדים יותר טוב עם הורדה ישירה דרך ffmpeg
# (עם ה-cookies וה-headers שנתפסו בסריקה) מאשר עם yt-dlp.

def download_m3u8_with_ffmpeg(
    m3u8_url,
    output_path,
    cookies_str="",
    referer=None
):

    il_referer, il_origin, _il_cookie_domain = il_site_profile(
        referer
    )

    headers = (
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36\r\n"
        f"Referer: {il_referer}\r\n"
        f"Origin: {il_origin}\r\n"
    )

    if cookies_str:
        headers += f"Cookie: {cookies_str}\r\n"

    cmd = [
        "ffmpeg",
        "-headers", headers,
        "-i", m3u8_url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        output_path,
        "-y"
    ]

    print("Running ffmpeg download for m3u8...", flush=True)

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed: {result.stderr[-300:]}"
        )

    return output_path




# סימון מקור שטופס החיפוש המאוחד מצמיד לקישור בכפתורי ההורדה
# ("...?via=email-search"). Apps Script משתמש בו להגנת כפילויות,
# אבל השרת עצמו לא מכיר בו: הוא נשאר בסוף הכתובת ושובר השוואות
# סיומת (למשל זיהוי קישור פרק של כאן .../s1/88374/ בתוך
# unified download), ולכן מנטרלים אותו מיד בכניסה לכל נקודה
# שמקבלת כתובת.
EMAIL_SOURCE_MARKER = "via=email-search"


def strip_email_source_marker(url):
    """
    הסרת סימון המקור via=email-search מכתובת, עם טיפול נכון במפרידים:
    פרמטר ראשון עם אחרים ("?via=email-search&x=1" -> "?x=1"),
    פרמטר אמצעי ("&via=email-search&x=1" -> "&x=1"), ואחרון/יחיד
    ("?via=email-search" -> נתיב נקי ללא ה-"?").
    """

    if not isinstance(url, str):
        return url

    text = url.strip()

    # קודם המקרים שבהם אחרי הסימון באים פרמטרים נוספים -
    # כדי שהמפריד שנותר יישאר תקין.
    text = text.replace("?" + EMAIL_SOURCE_MARKER + "&", "?")
    text = text.replace("&" + EMAIL_SOURCE_MARKER + "&", "&")

    # ואז המקרה של סימון בסוף הכתובת (הנפוץ מכול - כך כפתורי
    # ההורדה במייל בונים את הקישור).
    text = re.sub(
        r"[?&]" + re.escape(EMAIL_SOURCE_MARKER) + r"$",
        "",
        text,
    )

    return text


VIDEO_URL_PATTERNS = [
    re.compile(
        r"(https?://)?(www\.)?"
        r"(youtube\.com/watch\?v=|youtu\.be/)"
        r"[\w\-]+[^\s]*",
        re.IGNORECASE
    ),
    re.compile(
        r"(https?://)?(www\.)?"
        r"instagram\.com/(p|reel|reels|tv)/"
        r"[\w\-]+[^\s]*",
        re.IGNORECASE
    ),
    re.compile(
        r"(https?://)?(www\.|vm\.|vt\.)?"
        r"tiktok\.com/"
        r"(@[\w.\-]+/video/\d+|[\w]+)[^\s]*",
        re.IGNORECASE
    ),
    re.compile(
        r"(https?://)?([a-zA-Z0-9-]+\.)?"
        r"(mako\.co\.il|mako\.tv|n12\.co\.il|13tv\.co\.il|"
        r"kan\.org\.il|now14\.co\.il|c14\.co\.il|"
        r"ynet\.co\.il|immergo\.tv)/.+",
        re.IGNORECASE
    ),
    re.compile(
        r".*\.m3u8.*",
        re.IGNORECASE
    ),
]


def is_valid_video_url(url):

    if not url:
        return False

    text = url.strip()

    # סימון מקור מהמייל ("...?via=email-search") לא צריך לפסול
    # כתובת תקינה - מנטרלים אותו לפני בדיקת התבניות.
    text = strip_email_source_marker(text)

    return any(
        pattern.match(text)
        for pattern in VIDEO_URL_PATTERNS
    )


def split_glued_season_episode(url, season=None, episode=None):
    """
    פענוח הגנתי של עונה/פרק שהודבקו לתוך שדה ה-URL.

    הפורמט הנכון הוא url, season ו-episode כשדות JSON נפרדים.
    אבל לקוחות שולחים לפעמים הכל לשדה url אחד -
    "https://.../nutuk_drama 1 1" - ואז הכתובת יוצאת עם רווחים
    לא חוקיים, season ו-episode מגיעים None, הסריקה מפספסת
    את הפרק המבוקש ונופלת ל-yt-dlp על עמוד ההגנה של Radware.

    אם שני השדות הנפרדים כבר הגיעו - הכתובת נשארת כמו שהיא.
    אחרת, מספרים טריים בסוף הכתובת מפורשים ממנה:
    שני מספרים = עונה ואז פרק, מספר אחד = פרק בלבד.
    """

    if not isinstance(url, str):
        return url, season, episode

    # סימון מקור מהמייל מוסר כאן - כך הכתובת הנקייה ממשיכה לכל
    # הזרימות (פרק כאן, מאקו, סריקות) בלי שברי סיומת.
    text = strip_email_source_marker(url.strip())

    if season is not None and episode is not None:
        return text, season, episode

    m = re.match(
        r"^(https?://\S+?)\s+([0-9]{1,3})(?:\s+([0-9]{1,3}))?$",
        text,
    )

    if not m:
        return text, season, episode

    clean_url, first, second = m.group(1), m.group(2), m.group(3)

    if season is None and episode is None:

        # שני מספרים: עונה ואז פרק. מספר אחד: פרק בלבד.
        if second is not None:
            season, episode = int(first), int(second)
        else:
            episode = int(first)

    elif season is None:
        season = int(first)

    elif episode is None:
        episode = int(first)

    print(
        "Split glued season/episode out of url: "
        f"{clean_url} (season={season}, episode={episode})",
        flush=True,
    )

    return clean_url, season, episode




# ============================================================
# KAN (כאן) - ENGINE
# ============================================================
# שליפת עמודים, חילוץ מזהה Kaltura, ופירוק עמוד סדרה לעונות/פרקים.

def _kan_fetch_proxy_candidates():

    """
    מביא פרוקסים ישראליים חינמיים מכל המקורות:
      1. proxifly - רשימת IL שמתעדכנת כל 5 דקות (פורמט שורה-פרוקסי)
      2. geonode API - סינון מדינה IL (פורמט JSON)
    מחזיר רשימת מחרוזות פרוקסי מעורבבת כדי שלא כולם ינחתו
    על אותו פרוקסי ראשון.
    """

    candidates = []

    for source_url in KAN_PROXY_LIST_URLS:

        try:

            response = requests.get(source_url, timeout=15)

            if response.status_code != 200:
                continue

            if source_url.endswith(".txt") or "proxyscrape" in source_url:

                candidates.extend(
                    line.strip()
                    for line in response.text.splitlines()
                    if line.strip() and "://" in line
                )

            elif "proxy-list.download" in source_url:

                # פורמט IP:PORT פשוט - הרשימה כבר מסוננת ל-IL בצד השרת
                candidates.extend(
                    f"http://{line.strip()}"
                    for line in response.text.splitlines()
                    if line.strip() and ":" in line and "://" not in line
                )

            else:

                data = response.json()

                for item in data.get("data", []):

                    ip = item.get("ip")
                    port = item.get("port")
                    protocols = item.get("protocols") or []

                    if not ip or not port:
                        continue

                    scheme = (
                        "https"
                        if "https" in protocols
                        else "http"
                    )

                    candidates.append(f"{scheme}://{ip}:{port}")

        except Exception as src_err:

            print(
                "KAN proxy source failed:",
                source_url.split("/")[2] if "//" in source_url else "?",
                str(src_err)[:100],
                flush=True,
            )

    random.shuffle(candidates)

    return candidates[:KAN_PROXY_MAX_CANDIDATES]


def _kan_proxy_works(proxy):

    """בודק אם פרוקסי מסוים מגיע בפועל לכאן."""

    try:

        response = requests.get(
            KAN_PROXY_TEST_URL,
            proxies={"http": proxy, "https": proxy},
            headers=KAN_HEADERS,
            timeout=20,
            verify=False,
        )

        return response.status_code == 200

    except Exception:
        return False


def _kan_get_working_proxy():

    """
    מחזיר פרוקסי עובד לשליפת עמודי כאן, או None.

    סדר עדיפויות:
      1. KAN_PROXY_URL מהסביבה (אם הוגדר - מוחזר תמיד, בלי בדיקה,
         כי ההנחה היא שהמנהל יודע מה הוא עושה).
      2. פרוקסי מהמטמון אם לא פג תוקף.
      3. בדיקת מועמדים חדשה מהרשימה החינמית; הראשון שעובד נשמר.
    """

    # פרוקסי ידני - תמיד קודם
    if KAN_PROXY_URL:
        return KAN_PROXY_URL

    now = time.time()

    with _kan_proxy_lock:

        cached = _kan_proxy_state.get("proxy")

        if cached and now - _kan_proxy_state["checked_at"] < KAN_PROXY_CACHE_TTL:
            return cached

    # מטמון פג או לא קיים - מרעננים (מחוץ לנעילה כדי לא לחסום
    # בקשות מקבילות לזמן הבדיקה)
    candidates = _kan_fetch_proxy_candidates()

    budget_deadline = time.time() + KAN_PROXY_BUDGET_SECONDS

    for proxy in candidates:

        if time.time() >= budget_deadline:

            print(
                "KAN proxy: time budget exhausted, giving up on "
                f"the remaining candidates",
                flush=True,
            )

            break

        if _kan_proxy_works(proxy):

            with _kan_proxy_lock:
                _kan_proxy_state["proxy"] = proxy
                _kan_proxy_state["checked_at"] = time.time()

            print(
                "KAN proxy: using free IL proxy",
                proxy,
                flush=True,
            )

            return proxy

    print(
        "KAN proxy: no working free IL proxy found "
        f"(tried {len(candidates)} candidates)",
        flush=True,
    )

    # לא נמצא - מנקים מטמון כדי שהבקשה הבאה תנסה שוב
    with _kan_proxy_lock:
        _kan_proxy_state["proxy"] = None
        _kan_proxy_state["checked_at"] = now

    return None


try:

    from curl_cffi import requests as curl_requests

except ImportError:  # pragma: no cover

    curl_requests = None


def _kan_fetch_impersonated(url, proxy=None, timeout=45):

    """
    שליפת עמוד כאן עם חיקוי דפדפן מלא (curl_cffi, chrome124).
    ה-WAF של kan.org.il מזהה טביעת אצבע TLS של לקוחות שאינם
    דפדפנים (requests/curl) ומחזיר 403 גם מ-IP ישראלי תקין -
    חיקוי טביעת האצבע של כרום עוקף את זה.
    מחזיר (status_code, body). body ריק בכישלון.
    """

    if curl_requests is None:
        return 0, ""

    proxies = (
        {"http": proxy, "https": proxy} if proxy else None
    )

    try:

        response = curl_requests.get(
            url,
            headers=KAN_HEADERS,
            proxies=proxies,
            timeout=timeout,
            impersonate="chrome124",
            allow_redirects=True,
            verify=False,
        )

        return response.status_code, (response.text or "")

    except Exception as imp_err:

        print(
            "KAN impersonated fetch failed:",
            str(imp_err)[:120],
            flush=True,
        )

        return 0, ""


def kan_page_fetch(url, session=None, spn_polls=None):

    # מטמון תוצאות: עמוד פרק אינו משתנה (מזהה Kaltura קבוע),
    # ושאר העמודים נשמרים שעה - מגן מתקלות זמניות של
    # Wayback/פרוקסים ומונע שליפות חוזרות בהורדת עונה שלמה.
    cached_body = _kan_page_cache_get(url)

    if cached_body is not None:
        return cached_body

    """
    שליפת עמוד מכאן. סדר הערוצים:
      1. ישירות (רלוונטי אם השרת עם IP ישראלי)
      2. פרוקסי ישראלי (אם קיים עובד)
      3. Wayback Machine (צילום קיים או יצירת צילום חי)
      4. r.jina.ai
    כל ערוץ עובר ולידציית תוכן - עמוד לא שמיש (ג'אנק, חסימה
    חלקית, עמוד פרק בלי נגן) לא עוצר את השרשרת.
    spn_polls - מספר ניסיונות ההמתנה לארכוב חי ב-Wayback.
    """

    http = session or requests

    # ניסיון ישיר
    try:

        response = http.get(
            url,
            headers=KAN_HEADERS,
            timeout=KAN_DIRECT_TIMEOUT,
            verify=True,
        )

        response.raise_for_status()

        if _kan_wayback_content_ok(response.text, url):
            _kan_page_cache_put(url, response.text)
            return response.text

        print(
            "KAN direct: fetched but content not usable, continuing",
            flush=True,
        )

    except requests.exceptions.RequestException as direct_error:

        print(
            "KAN direct fetch failed:",
            str(direct_error)[:120],
            flush=True,
        )

    # ניסיון ישיר עם חיקוי דפדפן - עוקף זיהוי טביעת אצבע TLS
    imp_status, imp_body = _kan_fetch_impersonated(url)

    if imp_status == 200 and _kan_wayback_content_ok(imp_body, url):
        _kan_page_cache_put(url, imp_body)
        return imp_body

    # ניסיון דרך פרוקסי ישראלי
    proxy = _kan_get_working_proxy()

    if proxy:

        # דרך הפרוקסי עם חיקוי דפדפן - ההגרלה החזקה ביותר:
        # IP ישראלי + טביעת אצבע של כרום אמיתי
        imp_status, imp_body = _kan_fetch_impersonated(
            url, proxy=proxy
        )

        if imp_status == 200 and _kan_wayback_content_ok(
            imp_body, url
        ):
            _kan_page_cache_put(url, imp_body)
            return imp_body

        print(
            f"KAN proxy impersonated: status={imp_status}, "
            "falling back to plain requests",
            flush=True,
        )

        try:

            response = requests.get(
                url,
                headers=KAN_HEADERS,
                proxies={"http": proxy, "https": proxy},
                timeout=45,
                verify=False,
            )

            response.raise_for_status()

            if _kan_wayback_content_ok(response.text, url):
                _kan_page_cache_put(url, response.text)
                return response.text

            print(
                "KAN proxy: content not usable, continuing",
                flush=True,
            )

        except Exception as proxy_err:

            print(
                "KAN proxy fetch failed:",
                str(proxy_err)[:120],
                flush=True,
            )

    # Wayback Machine: הערוץ שאומת בפועל כעובד גם מחו"ל -
    # צילום קיים טרי, ואם אין - יצירת צילום חי עם Save-Page-Now.
    wayback_body = _kan_fetch_via_wayback(url, spn_polls=spn_polls)

    if wayback_body:
        _kan_page_cache_put(url, wayback_body)
        return wayback_body

    # גישה אחרונה: קורא האתרים r.jina.ai משחזר את העמוד החי
    # מצד השרתים שלו - אותו טריק שמאקו משתמש בו (ראה
    # mako_fetch_hub_html_via_jina). הוא לא תמיד מחזיק את כל
    # ה-HTML הגולמי של הנגן, אבל שווה ניסיון לפני כישלון מלא.
    body = _kan_fetch_via_jina(url)

    if body:
        _kan_page_cache_put(url, body)
        return body

    raise RuntimeError(
        "שליפת עמוד כאן נכשלה בכל הערוצים (ישירות, פרוקסי ישראלי, "
        "Wayback Machine, r.jina.ai). kan.org.il חוסם IP לא-ישראלי "
        "של עננים ציבוריים - הגדירו KAN_PROXY_URL לפרוקסי ישראלי "
        "יציב, או הריצו את השרת עם IP ישראלי."
    )


def _kan_fetch_via_jina(page_url):

    """
    שליפת עמוד כאן דרך r.jina.ai (אותו מנגנון של מאקו).
    מוחזר גוף HTML או None בכישלון. מזהה entry של Kaltura צריך
    להימצא בגוף כדי שהתוצאה תהיה שימושית.
    """

    try:

        req = urllib.request.Request(
            "https://r.jina.ai/" + page_url,
            headers={
                "X-Return-Format": "html",
            },
        )

        body = None

        for jina_attempt in range(2):

            try:

                with urllib.request.urlopen(req, timeout=90) as resp:
                    body = resp.read().decode("utf-8", "replace")
                break

            except Exception as jina_ex:

                if jina_attempt == 0:
                    print(
                        "KAN jina: first attempt failed ("
                        + str(jina_ex)[:100] + "), retrying",
                        flush=True,
                    )
                    time.sleep(3)

        if not body:
            return None

        # ולידציה מודעת-URL: עמוד פרק חייב להכיל מזהה נגן,
        # ואילו עמוד סדרה/עונה מסתפק בקישורי פרקים (הוא בכלל
        # לא מכיל נגן - זו לא עדות לכישלון).
        is_episode = bool(
            re.search(r"/s\d+/\d+/?$", page_url.rstrip("/") + "/")
        )

        if is_episode:

            if not kan_find_kaltura_entries(body):

                print(
                    "KAN jina: episode page fetched but no Kaltura entry inside",
                    flush=True,
                )
                return None

        elif not re.search(
            r'href=[\"\'][^\"\']*?/p-\d+/s\d+/\d+/?[\"\']',
            body
        ):

            print(
                "KAN jina: season page fetched but no episode links inside",
                flush=True,
            )
            return None

        print("KAN jina: fetched page with Kaltura entry", flush=True)

        return body

    except Exception as ex:

        print(
            "KAN jina: fetch failed: " + str(ex)[:120],
            flush=True,
        )
        return None


def _kan_wayback_content_ok(body, url=None):

    """
    תוקף תוכן צילום. עמוד פרק חייב להכיל מזהה נגן (Kaltura) -
    עמוד שמכיל רק קישורי ניווט/פרקים ייפסל עבורו. עמוד סדרה או
    עונה מסתפק בקישורי פרקים.
    """

    if not body:
        return False

    if kan_find_kaltura_entries(body):
        return True

    # עמוד פרק (מסתיים ב-/s8/756427/): אין נגן = צילום לא שמיש
    if url and re.search(r"/p-\d+/s\d+/\d+/?$", url.rstrip("/") + "/"):
        return False

    return bool(
        re.search(r'href=["\'][^"\']*?/p-\d+/s\d+/\d+/?["\']', body)
    )


def _kan_wayback_closest(url, timestamp):

    """
    מחזיר (timestamp, body) של הצילום הקרוב ביותר ב-Wayback,
    או (None, None). הגוף מאומת עם _kan_wayback_content_ok.
    """

    try:

        response = requests.get(
            "http://archive.org/wayback/available",
            params={"url": url, "timestamp": timestamp or ""},
            timeout=15,
        )

        closest = (
            (response.json().get("archived_snapshots") or {})
            .get("closest")
            or {}
        )

        snap_ts = closest.get("timestamp")

        if not closest.get("available") or not snap_ts:
            return None, None

        # שתי וריאציות של אותו צילום: id_ מחזיר את ה-HTML הגולמי,
        # ולפעמים הוא קטום/חלופי - אז גם הגרסה עם סרגל הכלים של
        # הארכיון, שנמצאה בפועל מכילה את כל התוכן. הרג'קסים שלנו
        # סובלניים להזרקות של הסרגל, אז שתיהן מתאימות לפרסינג.
        for raw_url in (
            f"http://web.archive.org/web/{snap_ts}id_/{url}",
            f"http://web.archive.org/web/{snap_ts}/{url}",
        ):

            try:

                response = requests.get(raw_url, timeout=60)

                response.raise_for_status()

            except Exception as snap_err:

                print(
                    "KAN wayback: variant fetch failed: "
                    + str(snap_err)[:100],
                    flush=True,
                )

                continue

            body = response.text

            if _kan_wayback_content_ok(body, url):
                return snap_ts, body

            print(
                "KAN wayback: snapshot content invalid "
                f"({len(body)} bytes), trying next variant",
                flush=True,
            )

        return snap_ts, None

    except Exception as ex:

        print(
            "KAN wayback: snapshot fetch failed: " + str(ex)[:120],
            flush=True,
        )

        return None, None


def _kan_fetch_via_wayback(url, spn_polls=None):

    """
    שליפת עמוד כאן דרך Wayback Machine - הערוץ שאינו נחסם על ידי
    kan.org.il (אומת בפועל: צילום עמוד פרק מכיל את מזהה הנגן המלא):
      1. צילום קיים טרי מספיק - נשלף ישירות.
      2. אין צילום טרי - Save-Page-Now יוצר צילום חי, ואז שולפים אותו.
      3. אם SPN נכשל - מוחזר צילום ישן תקין אם קיים (עדיף על כלום).
    spn_polls - מספר ניסיונות ההמתנה לארכוב חי (ברירת מחדל: מלא).
    """

    now_stamp = time.strftime("%Y%m%d")

    snap_ts, body = _kan_wayback_closest(url, now_stamp)

    fresh = (
        snap_ts is not None
        and body is not None
        and int(now_stamp) - int(snap_ts[:8]) <= KAN_WAYBACK_FRESHNESS
    )

    # עמודי פרק: מזהה ה-Kaltura של פרק שפורסם אינו משתנה לעולם,
    # אז כל צילום תקין - גם ישן - שווה ערך לעמוד החי. עמודי
    # סדרה/עונה לעומת זאת עלולים להחסיר פרקים חדשים, ולכן דורשים
    # צילום טרי (או המתנה לצילום חי דרך Save-Page-Now).
    is_episode_page = bool(
        re.search(r"/s\d+/\d+/?$", url.rstrip("/") + "/")
    )

    if fresh or (is_episode_page and body is not None):
        print(
            f"KAN wayback: using existing snapshot {snap_ts}"
            + ("" if fresh else " (stale but episode-stable)"),
            flush=True,
        )
        return body

    # עמוד עונה שהצילום הקרוב שלו לא תקין (למשל צילום 204 ריק
    # שנוצר מניסיון SPN כושל): המתנת SPN קצרה, ואז - צילום ישן
    # מלפני שנה, כי רשימת הפרקים של עונה שהסתיימה כמעט ואינה משתנה.
    year_stamp = (
        str(int(now_stamp[:4]) - 1) + now_stamp[4:]
        if not is_episode_page
        else None
    )

    polls = (
        KAN_SPN_POLL_ATTEMPTS if spn_polls is None else spn_polls
    )

    if polls > 0:

        print(
            "KAN wayback: submitting Save-Page-Now for a fresh snapshot",
            flush=True,
        )

        try:

            requests.get(
                "https://web.archive.org/save/" + url,
                timeout=60,
                headers={
                    "User-Agent": KAN_HEADERS.get("User-Agent", "Mozilla/5.0"),
                },
            )

        except Exception as save_err:

            print(
                "KAN wayback: SPN submit failed: " + str(save_err)[:120],
                flush=True,
            )

        for poll in range(polls):

            time.sleep(KAN_SPN_POLL_INTERVAL)

            poll_ts, poll_body = _kan_wayback_closest(url, now_stamp)

            if poll_body and poll_ts != snap_ts:

                print(
                    f"KAN wayback: fresh snapshot ready ({poll_ts}) "
                    f"after {(poll + 1) * KAN_SPN_POLL_INTERVAL}s",
                    flush=True,
                )

                return poll_body

            print(
                f"KAN wayback: SPN poll {(poll + 1)}/"
                f"{KAN_SPN_POLL_ATTEMPTS} not ready yet",
                flush=True,
            )

    if year_stamp:

        old_ts, old_body = _kan_wayback_closest(url, year_stamp)

        if old_body:

            print(
                f"KAN wayback: using older snapshot {old_ts} "
                "(season lists are stable)",
                flush=True,
            )

            return old_body

    # לא נוצר צילום חדש - הישן עדיין עדיף על כלום. חריגה:
    # המתנה בוטלה (spn_polls=0) - עמוד עונה ישן עלול להחסיר
    # פרקים חדשים ולהטעות, אז מחזירים None; עמוד פרק יציב,
    # אז צילום ישן תקין שלו מותר.
    if polls > 0 or is_episode_page:
        return body

    return None


def kan_find_kaltura_entries(text):

    entries = []

    for match in KAN_ENTRY_KEY_RE.finditer(text):
        if match.group(1) not in entries:
            entries.append(match.group(1))

    if not entries:

        for match in KAN_ENTRY_URL_RE.finditer(text):
            if match.group(1) not in entries:
                entries.append(match.group(1))

    if not entries:

        # גיבוי גנרי: בצילומי Wayback של עמודי פרק מבנה הנגן משתנה
        # ולפעמים המזהה מופיע בלי הקשר מילולי ברור. מזהה אמיתי
        # חוזר בד"כ כמה פעמים בעמוד - הנפוץ ביותר זוכה, ורק אם
        # הופיע לפחות פעמיים (לצמצם ג'אנק של מחרוזות אקראיות).
        generic_counts = {}

        for match in re.finditer(
            r"\b([01]_[0-9a-z]{8,12})\b",
            text,
        ):
            generic_counts[match.group(1)] = (
                generic_counts.get(match.group(1), 0) + 1
            )

        if generic_counts:

            best_candidate = max(
                generic_counts,
                key=generic_counts.get,
            )

            if generic_counts[best_candidate] >= 2:
                entries.append(best_candidate)

    return entries


def kan_extract_kaltura_entry(page_url, html=None):

    page_html = html if html is not None else kan_page_fetch(page_url)

    entries = kan_find_kaltura_entries(page_html)

    if not entries:
        raise RuntimeError(
            "לא נמצא מזהה נגן (Kaltura entry) בעמוד הפרק של כאן"
        )

    print(
        "KAN: found Kaltura entries:",
        entries,
        flush=True
    )

    kaltura_url = f"kaltura:{KAN_KALTURA_PARTNER}:{entries[0]}"

    # מעביר את ה-Referer של עמוד כאן לתוך ה-extractor של Kaltura
    kaltura_url = smuggle_url(
        kaltura_url,
        {
            "force_videoid": entries[0],
            "to_generic": False,
            "referer": page_url,
        }
    )

    return kaltura_url, entries[0]


def kan_episode_slug(url):

    return url.rstrip("/").rsplit("/", 1)[-1]


def kan_extract_m3u8_urls(page_html):

    """
    חילוץ קישורי m3u8 ישירים מעמוד פרק (הנגן של כאן מקבל אותם
    מוכנים). מטפל גם בקישורים שנכתבו מחדש בצילומי Wayback.
    """

    urls = []

    for match in re.finditer(
        r'https?:\/\/[^"\'\s<>]+?\.m3u8[^"\'\s<>]*',
        page_html,
    ):

        m3u8 = match.group(0)

        # החזרת קישורים שנכתבו מחדש על ידי Wayback לצורתם המקורית
        m3u8 = re.sub(
            r"^https?://web\.archive\.org/web/\d+(?:[a-z_]{2})?/",
            "",
            m3u8,
        )

        # לפעמים הקישור המקורי מוצפן ב-HTML entity
        m3u8 = html_lib.unescape(m3u8)

        if m3u8 not in urls:
            urls.append(m3u8)

    return urls


def kan_get_episode_page(url, session=None, html=None, spn_polls=None):

    page_html = (
        html if html is not None
        else kan_page_fetch(url, session, spn_polls=spn_polls)
    )

    return _kan_parse_episode_page(url, page_html)


def kan_episode_stream_candidates(page_url, page_html=None):

    """
    מקורות הזרמה אפשריים לפרק, לפי סדר עדיפות:
      1. kaltura: (yt-dlp) - כל האיכויות עד 1080p, אבל השותף של
         כאן נחסם כרגע עבור yt-dlp בצד Kaltura.
      2. m3u8 ישירים מהעמוד (CDN של redge) - עובד רק מ-IP ישראלי.
    """

    page_html = (
        page_html if page_html is not None
        else kan_page_fetch(page_url)
    )

    candidates = []

    try:
        yt_url, _entry = kan_extract_kaltura_entry(
            page_url,
            page_html,
        )
        candidates.append(yt_url)
    except RuntimeError:
        pass

    for m3u8 in kan_extract_m3u8_urls(page_html):

        smuggled = smuggle_url(
            m3u8,
            {"http_headers": {
                "Referer": page_url,
                "Origin": "https://www.kan.org.il",
                "User-Agent": KAN_HEADERS.get("User-Agent", "Mozilla/5.0"),
            }},
        )

        candidates.append(smuggled)

    if not candidates:
        raise RuntimeError(
            "לא נמצא מקור הזרמה בעמוד הפרק של כאן"
        )

    return candidates


def _kan_parse_episode_page(url, page_html):

    try:
        yt_url, entry_id = kan_extract_kaltura_entry(url, page_html)
    except RuntimeError:
        return None

    title_match = re.search(
        r"<title>([^<]+)</title>",
        page_html
    )

    title = (
        html_lib.unescape(title_match.group(1)).strip()
        if title_match
        else None
    )

    ep_num_match = KAN_EPISODE_NUMBER_RE.search(title or "")

    return {
        "url": url,
        "entry_id": entry_id,
        "yt_url": yt_url,
        "title": title,
        "episode_number": (
            int(ep_num_match.group(1)) if ep_num_match else None
        ),
    }


def kan_extract_hub_season_nums(html):
    """
    מספרי העונות שעמוד שער של סדרת כאן מקשר אליהן.

    עמודי שער מסוימים (למשל "ארץ נהדרת") מקשרים לעמודי עונות
    (.../p-XXXXX/s2/) ולא לפרקים - ואז החילוץ הרגיל של
    kan_extract_series_page זורק "אינו מכיל קישורי פרקים".
    מוחזרת רשימה ממוינת מהעונה החדשה לישנה.
    """

    return sorted(
        {
            int(m.group(1))
            for m in re.finditer(
                r"href=[\"\'][^\"\']*?/p-\d+/s(\d+)/?[\"\']",
                html or "",
            )
        },
        reverse=True,
    )


def kan_extract_series_page(url, session=None, html=None, spn_polls=None):

    html = html if html is not None else kan_page_fetch(
        url, session, spn_polls=spn_polls
    )

    # עמוד לא שמיש: אין קישורי פרקים וזה גם לא עמוד פרק בודד.
    # בלי זה, עמוד עונה שהתקבל מ-Jina (markdown בלי href) מוחזר
    # כ"הצלחה" עם 0 פרקים במקום לדווח על הכישלון האמיתי.
    is_single_episode = bool(
        re.search(r"/s\d+/\d+/?$", url.rstrip("/") + "/")
    )

    if not is_single_episode and not re.search(
        r'href=[\"\'][^\"\']*?/p-\d+/s\d+/\d+/?[\"\']',
        html
    ):
        raise RuntimeError(
            "עמוד הסדרה/עונה שהתקבל אינו מכיל קישורי פרקים"
        )

    episode_links = []
    seen = set()

    for match in re.finditer(
        r'href=[\"\']([^\"\']*?/p-\d+/s\d+/\d+/?)[\"\']',
        html
    ):

        href = match.group(1)

        if href not in seen:
            seen.add(href)
            episode_links.append(urljoin(url, href))

    # זיהוי העונה: מעמוד סדרה/עונה ("/p-11843/s8/") או מעמוד פרק
    # ("/p-11843/s8/756427/") - בלי המזהה האחרון הפירוק מחזיר
    # season=None והקישורים לא מסוננים לעונה הנכונה.
    season_match = re.search(
        r"/p-(\d+)/(?:s(\d+))?(?:/\d+)?/?$",
        url.rstrip("/") + "/"
    )

    series_id = season_match.group(1) if season_match else None
    season = (
        int(season_match.group(2))
        if season_match and season_match.group(2)
        else None
    )

    # אם זה עמוד עונה מסוימת - לוקחים רק פרקים מהעונה הזאת
    if season is not None and series_id:

        season_prefix = f"/p-{series_id}/s{season}/"

        episode_links = [
            link for link in episode_links
            if season_prefix in link
        ]

    title_match = re.search(
        r"<title>([^<]+)</title>",
        html
    )

    title = (
        html_lib.unescape(title_match.group(1)).strip()
        if title_match
        else None
    )

    return {
        "url": url,
        "series_id": series_id,
        "season": season,
        "title": title,
        "episode_urls": episode_links,
    }


def kan_resolve_series_url(url, season=None, episode=None):

    if season is None and episode is None:
        return url

    m = re.search(
        r"^(https?://[^/]+/content/.+?/p-\d+)(?:/s\d+)?(?:/\d+)?/?$",
        url
    )

    if not m:
        raise RuntimeError(
            "לא ניתן לזהות עונה/פרק מהקישור - יש להשתמש בקישור סדרה/עונה/פרק תקין"
        )

    base = m.group(1)

    if season is not None:
        base = f"{base}/s{int(season)}"

    if episode is not None:
        return f"{base}/{int(episode)}/"

    return f"{base}/"


def kan_pick_episode_urls(episode_urls, episode=None, session=None):

    """
    בוחר אילו פרקים להוריד מתוך רשימת הקישורים של העונה.

    episode=None          -> כל הפרקים
    episode >= 10000      -> מזהה פרק בכתובת (למשל 756427)
    episode 1..999        -> מספר סידורי ("פרק 5") - נזהה מתוך כותרת העמוד
    """

    if episode is None:
        return list(episode_urls)

    try:
        ep_num = int(episode)
    except (TypeError, ValueError):
        raise RuntimeError(
            "'episode' חייב להיות מספר (מזהה פרק או מספר סידורי)"
        )

    if ep_num >= 10000:

        matches = [
            ep for ep in episode_urls
            if kan_episode_slug(ep) == str(ep_num)
        ]

        if matches:
            return matches

        raise RuntimeError(
            f"לא נמצא פרק עם מזהה {ep_num} בעונה"
        )

    # מספר סידורי - זיהוי דרך כותרת העמוד ("פרק N")
    for ep in episode_urls:

        try:
            info = kan_get_episode_page(ep, session)
        except Exception:
            continue

        if info and info.get("episode_number") == ep_num:
            return [ep]

    raise RuntimeError(
        f"לא נמצא פרק מספר {ep_num} בעונה"
    )


def kan_download_m3u8_with_ffmpeg(m3u8_url, output_path, referer=None):

    headers = (
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36\r\n"
        f"Referer: {referer or 'https://www.kan.org.il/'}\r\n"
        "Origin: https://www.kan.org.il\r\n"
    )

    cmd = [
        "ffmpeg",
        "-headers", headers,
        "-protocol_whitelist", "file,http,https,tcp,tls",
        "-i", m3u8_url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        output_path,
        "-y"
    ]

    print("KAN: running ffmpeg direct m3u8 download...", flush=True)

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed: {result.stderr[-300:]}"
        )

    return output_path


# ============================================================

# ============================================================
# GOOGLE DRIVE
# ============================================================

# מאיפה הגיע הטוקן בפעם האחרונה ("bridge" / "refresh_token") ומה
# הגשר החזיר אם נכשל - מוצג ב-/diag/drive.
DRIVE_AUTH_STATE = {"source": None, "bridge_error": None}


def get_drive_service():

    # קודם גשר ה-Apps Script (בלי טוקן להחליף), ורק אם הוא לא זמין -
    # ה-refresh token הישן, כדי ששום דבר לא יישבר בזמן המעבר.
    try:

        creds = bridge_credentials(API_KEY)

        if creds is not None:

            DRIVE_AUTH_STATE["source"] = "bridge"
            DRIVE_AUTH_STATE["bridge_error"] = None

            return build(
                "drive",
                "v3",
                credentials=creds
            )

    except Exception as e:

        DRIVE_AUTH_STATE["bridge_error"] = str(e)[:300]

        if not GOOGLE_OAUTH_REFRESH_TOKEN:
            raise

    DRIVE_AUTH_STATE["source"] = "refresh_token"

    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_OAUTH_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_OAUTH_CLIENT_ID,
        client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=DRIVE_SCOPES,
    )

    creds.refresh(
        GoogleAuthRequest()
    )

    return build(
        "drive",
        "v3",
        credentials=creds
    )


def upload_to_drive(local_path, filename, parent_id=None):

    service = get_drive_service()

    target_parent = (
        parent_id
        or DRIVE_FOLDER_ID
    )

    file_metadata = {
        "name": filename,
        "parents": (
            [target_parent]
            if target_parent
            else []
        )
    }

    media = MediaFileUpload(
        local_path,
        resumable=True
    )

    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink"
    ).execute()

    return (
        uploaded.get("webViewLink"),
        uploaded.get("id")
    )


# ============================================================
# COOKIES
# ============================================================

def write_cookies_file(tmp_dir):

    if not YOUTUBE_COOKIES:
        print(
            "YOUTUBE_COOKIES: NOT CONFIGURED"
        )
        return None

    cookies_path = os.path.join(
        tmp_dir,
        "cookies.txt"
    )

    with open(
        cookies_path,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(YOUTUBE_COOKIES)

    try:
        size = os.path.getsize(
            cookies_path
        )
    except OSError:
        size = 0

    print(
        "YOUTUBE_COOKIES: configured, "
        f"cookies.txt created ({size} bytes)"
    )

    if size == 0:
        print(
            "WARNING: cookies.txt is empty"
        )
        return None

    return cookies_path


# ============================================================
# NORMALIZE CLIENTS
# ============================================================

def normalize_player_clients(player_clients):

    if player_clients is None:
        return None

    if isinstance(player_clients, str):

        player_clients = [
            x.strip()
            for x in player_clients.split(",")
            if x.strip()
        ]

    if not isinstance(player_clients, list):
        return None

    result = [
        str(x).strip()
        for x in player_clients
        if str(x).strip()
    ]

    return result or None


# ============================================================
# DEFAULT CLIENT STRATEGY (YouTube בלבד)
# ============================================================
# הרשימה הזו רלוונטית רק ליוטיוב - "player_client" הוא מונח ספציפי
# למנגנון ה-extractor של יוטיוב ב-yt-dlp. לפלטפורמות אחרות (אינסטגרם,
# טיקטוק) אין משמעות לרשימה הזו ולכן לא נעשה בה שימוש עבורן.

DEFAULT_CLIENT_ATTEMPTS = [

    (["android"], True),
    (["ios"], True),
    (["web_embedded"], True),
    (["tv_simply"], True),
    (["tv"], True),
    (["android_vr"], True),
    (["web_safari"], True),
    (["mweb"], True),
    (["web"], True),

    (["android"], False),
    (["ios"], False),
    (["web_embedded"], False),
    (["tv_simply"], False),
    (["tv"], False),
    (["android_vr"], False),
    (["web_safari"], False),
    (["mweb"], False),
    (["web"], False),
]


# ============================================================
# BUILD YT-DLP OPTIONS
# ============================================================

def build_ytdlp_options(
    tmp_dir,
    fmt,
    player_clients,
    use_cookies,
    platform="youtube",
    diagnostic=False,
    use_proxy=False,
    cookies_str="",
    referer=None
):

    outtmpl = os.path.join(
        tmp_dir,
        "%(title)s.%(ext)s"
    )

    extractor_args = {
        "youtubepot-bgutilhttp": {
            "base_url": "http://127.0.0.1:4416"
        }
    }

    # player_client רלוונטי רק לחילוץ מיוטיוב
    if platform == "youtube" and player_clients:
        extractor_args["youtube"] = {
            "player_client": player_clients
        }

    options = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "extractor_args": extractor_args,
        "ignoreerrors": False,
        "continuedl": True,
        "nopart": False,
        "check_formats": "selected",
        # yt-dlp צריך מנוע JavaScript חיצוני כדי לפתור את אתגרי ה-JS של
        # יוטיוב. ברירת המחדל היא deno, שלא מותקן כאן - אבל node כן
        # (תמונת הבסיס היא node:22), אז מפעילים אותו במפורש.
        "js_runtimes": {"node": {}, "deno": {}},
    }

    # הגדרות ייעודיות לכאן (Kaltura) - Referer של האתר עצמו
    if platform == "kan":

        options["nocheckcertificate"] = True

        options["http_headers"] = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.kan.org.il/",
            "Origin": "https://www.kan.org.il"
        }

    # הגדרות ייעודיות לאתרי חדשות ישראליים - לא משפיע על יוטיוב/
    # אינסטגרם/טיקטוק בשום צורה
    if platform == "news_il":

        options["hls_use_mpegts"] = True
        options["nocheckcertificate"] = True

        il_referer, il_origin, il_cookie_domain = il_site_profile(
            referer
        )

        options["http_headers"] = {
            "Accept": "*/*",
            "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": il_referer,
            "Origin": il_origin
        }

        if cookies_str:

            dyn_cookie_path = os.path.join(
                tmp_dir,
                "dyn_cookies.txt"
            )

            with open(
                dyn_cookie_path,
                "w",
                encoding="utf-8"
            ) as cf:

                cf.write("# Netscape HTTP Cookie File\n")

                for c_item in cookies_str.split("; "):

                    if "=" in c_item:

                        c_name, c_val = c_item.split("=", 1)

                        cf.write(
                            f"{il_cookie_domain}\tTRUE\t/\tTRUE\t0\t"
                            f"{c_name.strip()}\t{c_val.strip()}\n"
                        )

            options["cookiefile"] = dyn_cookie_path

    if platform == "kan":

        # כאן: ה-CDN של הווידאו (cdn-redge.media) חוסם חו"ל, ולכן
        # גם הורדת הווידאו עצמה חייבת לעבור דרך פרוקסי ישראלי -
        # לא רק שליפת העמודים. KAN_PROXY_URL קודם, ואז פרוקסי
        # חינמי שנמצא בבדיקה.
        kan_dl_proxy = KAN_PROXY_URL or _kan_get_working_proxy()

        if kan_dl_proxy:

            options["proxy"] = kan_dl_proxy

            print(
                "yt-dlp configuration: KAN download via IL proxy "
                + kan_dl_proxy.split("@")[-1],
                flush=True,
            )

        else:

            print(
                "yt-dlp configuration: no IL proxy available for KAN "
                "- download will likely fail from non-Israeli IP",
                flush=True,
            )

    elif use_proxy:
        options["proxy"] = TOR_PROXY_URL

    if diagnostic:
        options["quiet"] = False
        options["no_warnings"] = False
        # מציג בלוג את שורות ה-[pot] - האם ספק ה-PO Token נטען ויצר טוקן
        options["verbose"] = True
    else:
        options["quiet"] = True
        options["no_warnings"] = True

    if fmt == "audio":

        options["format"] = (
            "bestaudio[acodec!=none]/"
            "best[acodec!=none]/"
            "best"
        )

        options["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]

    else:

        options["format"] = (
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo+bestaudio/"
            "best[ext=mp4]/"
            "best"
        )

        options["merge_output_format"] = "mp4"

    # עוגיות - כרגע נתמך רק עבור יוטיוב (YOUTUBE_COOKIES).
    # אינסטגרם/טיקטוק פועלים כרגע במצב תוכן ציבורי בלבד, ללא עוגיות.
    if use_cookies and platform == "youtube":

        cookies_path = write_cookies_file(
            tmp_dir
        )

        if cookies_path:

            options["cookiefile"] = cookies_path

            print(
                "yt-dlp configuration: "
                "Cookies ENABLED"
            )

        else:

            print(
                "yt-dlp configuration: "
                "Cookies REQUESTED but unavailable"
            )

    else:

        print(
            "yt-dlp configuration: "
            "Cookies DISABLED"
        )

    return options


# ============================================================
# FIND FINAL FILE
# ============================================================

def find_downloaded_file(
    tmp_dir,
    fmt
):

    ignored = {
        "cookies.txt"
    }

    candidates = []

    for root, dirs, files in os.walk(tmp_dir):

        for filename in files:

            if filename in ignored:
                continue

            if filename.endswith(".part"):
                continue

            if filename.endswith(".ytdl"):
                continue

            full_path = os.path.join(
                root,
                filename
            )

            if not os.path.isfile(full_path):
                continue

            try:
                size = os.path.getsize(
                    full_path
                )
            except OSError:
                continue

            if size <= 0:
                continue

            lower_name = filename.lower()

            if fmt == "audio":

                allowed = (
                    ".mp3",
                    ".m4a",
                    ".opus",
                    ".webm",
                    ".aac",
                    ".wav"
                )

            else:

                allowed = (
                    ".mp4",
                    ".mkv",
                    ".webm",
                    ".mov",
                    ".avi"
                )

            if lower_name.endswith(allowed):

                candidates.append(
                    (full_path, size)
                )

    if not candidates:

        for root, dirs, files in os.walk(tmp_dir):

            for filename in files:

                if filename in ignored:
                    continue

                if filename.endswith(".part"):
                    continue

                if filename.endswith(".ytdl"):
                    continue

                full_path = os.path.join(
                    root,
                    filename
                )

                if not os.path.isfile(full_path):
                    continue

                try:
                    size = os.path.getsize(
                        full_path
                    )
                except OSError:
                    continue

                if size > 0:

                    candidates.append(
                        (full_path, size)
                    )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item[1],
        reverse=True
    )

    return candidates[0][0]


# ============================================================
# ONE DOWNLOAD ATTEMPT
# ============================================================

def _try_download_once(
    url,
    fmt,
    tmp_dir,
    player_clients,
    use_cookies,
    platform="youtube",
    use_proxy=False,
    cookies_str="",
    referer=None
):

    # כאן: אם קיבלנו עמוד HTML (ולא כתובת kaltura:) - מחלצים את מזהה
    # הנגן וממירים לכתובת kaltura: שה-extractor המובנה של yt-dlp
    # יודע להוריד ממנה בכל האיכויות (כולל 1080p).
    # שימו לב: כתובת m3u8 מוברחת מכילה את ה-Referer בתוך ה-URL
    # (#__youtubedl_smuggle=...), ולכן הבדיקה חייבת לרוץ על
    # הכתובת לפני ההוספה - אחרת ננסה "לשלוף עמוד" מה-CDN.
    kan_url_bare = url.split("#__youtubedl_smuggle")[0].lower()

    if (
        platform == "kan"
        and kan_url_bare.startswith("http")
        and "kan.org.il" in kan_url_bare
    ):

        kan_ep = kan_get_episode_page(url)

        if not kan_ep:
            raise RuntimeError(
                "לא נמצא נגן (Kaltura) בעמוד הפרק של כאן"
            )

        url = kan_ep["yt_url"]

    if platform == "news_il" and ".m3u8" in url.lower():

        # אודיו: AAC מתוך HLS הוא מכולה ADTS - העתקה ישירה לקובץ
        # .mp3 יוצרת קובץ פגום. m4a היא המכולה הנכונה להעתקה.
        output_ext = "m4a" if fmt == "audio" else "mp4"

        output_path = os.path.join(
            tmp_dir,
            f"downloaded_stream.{output_ext}"
        )

        try:

            download_m3u8_with_ffmpeg(
                url,
                output_path,
                cookies_str,
                referer=referer
            )

            if (
                os.path.exists(output_path)
                and os.path.getsize(output_path) > 0
            ):

                # שם תיאורי מתוך כתובת הפלייליסט - בלי זה
                # כל הקבצים היו נשמרים באותו שם "m3u8_stream".
                media_title = mako_title_from_media_url(url)

                return output_path, media_title

        except Exception as ex:

            print(
                "FFmpeg direct download failed, "
                f"falling back to yt-dlp: {ex}",
                flush=True
            )

    ydl_opts = build_ytdlp_options(
        tmp_dir=tmp_dir,
        fmt=fmt,
        player_clients=player_clients,
        use_cookies=use_cookies,
        platform=platform,
        diagnostic=False,
        use_proxy=use_proxy,
        cookies_str=cookies_str,
        referer=referer
    )

    print(
        "Starting yt-dlp attempt:",
        {
            "platform": platform,
            "format": fmt,
            "clients": player_clients,
            "cookies": use_cookies,
            "cookies_configured": bool(YOUTUBE_COOKIES),
            "yt_dlp_version": YTDLP_VERSION
        }
    )

    with yt_dlp.YoutubeDL(
        ydl_opts
    ) as ydl:

        info = ydl.extract_info(
            url,
            download=True
        )

    if not info:

        raise RuntimeError(
            "yt-dlp לא החזיר מידע על הסרטון"
        )

    title = info.get(
        "title",
        "download"
    )

    final_path = find_downloaded_file(
        tmp_dir,
        fmt
    )

    if not final_path:

        raise RuntimeError(
            "ההורדה הסתיימה אך הקובץ הסופי לא נמצא"
        )

    return (
        final_path,
        title
    )


# ============================================================
# DOWNLOAD ENGINE (multi-platform)
# ============================================================

# ============================================================
# YOUTUBE BLOCK COOLDOWN
# ============================================================
# כשיוטיוב חוסם את ה-IP של השרת ("not a bot" / 429), כל ניסיון נוסף
# רק מאריך את החסימה. לכן: עוצרים בניסיון הראשון שנחסם, ולמשך
# ההפסקה לא פונים ליוטיוב בכלל ועונים מיד עם אותה הודעה.

YOUTUBE_BLOCK_COOLDOWN_SEC = (
    int(os.environ.get("YOUTUBE_BLOCK_COOLDOWN_MIN", "30")) * 60
)

_youtube_block = {"until": 0.0}


def _is_youtube_block_error(text):

    return (
        "Sign in to confirm" in text
        or "not a bot" in text
        or "HTTP Error 429" in text
    )


def download_video(
    url,
    fmt,
    tmp_dir,
    player_clients=None,
    use_cookies=True,
    use_proxy=False,
    cookies_str="",
    referer=None,
    platform=None
):

    platform = platform or detect_platform(url)

    if platform == "youtube":

        remaining = _youtube_block["until"] - time.time()

        if remaining > 0:

            # "not a bot" נשאר בהודעה כדי שהתוסף יציג את חלון החסימה
            raise RuntimeError(
                "Sign in to confirm you're not a bot | יוטיוב חסם את "
                "השרת, והשרת בהפסקה כדי לא להאריך את החסימה. "
                f"אפשר לנסות שוב בעוד {int(remaining // 60) + 1} דקות."
            )

    attempts = []

    if platform == "youtube":

        # ליוטיוב - שימור האסטרטגיה הקיימת: ניסיון עם ה-client
        # שהתבקש (אם הוגדר), ואז שורת גיבוי ארוכה של קליינטים שונים.
        requested_clients = normalize_player_clients(
            player_clients
        )

        if requested_clients:

            requested_attempt = (
                requested_clients,
                bool(use_cookies)
            )

            attempts.append(
                requested_attempt
            )

            if use_cookies:

                no_cookie_attempt = (
                    requested_clients,
                    False
                )

                if no_cookie_attempt not in attempts:

                    attempts.append(
                        no_cookie_attempt
                    )

        for combo in DEFAULT_CLIENT_ATTEMPTS:

            if combo not in attempts:

                attempts.append(combo)

    else:

        # אינסטגרם / טיקטוק / אחר - אין מושג "player_client",
        # אז מספיק ניסיון ישיר אחד (ועם/בלי עוגיות אם התבקש).
        attempts.append((None, bool(use_cookies)))

        if use_cookies:
            attempts.append((None, False))

    # כשאין עוגיות מוגדרות (YOUTUBE_COOKIES ריק), ניסיון "עם עוגיות"
    # זהה לחלוטין לניסיון בלי - מנרמלים את הדגל ומסירים כפילויות,
    # אחרת כל כשל של יוטיוב לוקח פי שניים זמן (עד 24 שניות מיותרות)
    # לפני שההודעה מגיעה למשתמש.
    if not YOUTUBE_COOKIES:

        normalized = []
        seen = set()

        for clients, cookies_flag in attempts:

            key = (
                tuple(clients) if clients else None,
                False,
            )

            if key in seen:
                continue

            seen.add(key)
            normalized.append((clients, False))

        attempts = normalized

    if fmt == "auto":

        formats_to_try = [
            "video",
            "audio"
        ]

    else:

        formats_to_try = [
            fmt
        ]

    last_error = None
    blocked = False

    for target_fmt in formats_to_try:

        if blocked:
            break

        for clients, cookies_flag in attempts:

            safe_clients = (
                "_".join(clients)
                if clients
                else "default"
            )

            sub_dir = os.path.join(
                tmp_dir,
                (
                    f"try_"
                    f"{target_fmt}_"
                    f"{safe_clients}_"
                    f"{int(cookies_flag)}"
                )
            )

            os.makedirs(
                sub_dir,
                exist_ok=True
            )

            print(
                "--------------------------------------------------"
            )

            print(
                "DOWNLOAD ATTEMPT",
                {
                    "platform": platform,
                    "format": target_fmt,
                    "clients": clients,
                    "cookies": cookies_flag,
                    "cookies_configured": bool(YOUTUBE_COOKIES),
                    "proxy": use_proxy
                }
            )

            try:

                result = _try_download_once(
                    url=url,
                    fmt=target_fmt,
                    tmp_dir=sub_dir,
                    player_clients=clients,
                    use_cookies=cookies_flag,
                    platform=platform,
                    use_proxy=use_proxy,
                    cookies_str=cookies_str,
                    referer=referer
                )

                print(
                    "SUCCESSFUL yt-dlp attempt:",
                    {
                        "platform": platform,
                        "format": target_fmt,
                        "clients": clients,
                        "cookies": cookies_flag
                    }
                )

                return result

            except Exception as e:

                last_error = e

                print(
                    "Download attempt failed:",
                    {
                        "platform": platform,
                        "format": target_fmt,
                        "clients": clients,
                        "cookies": cookies_flag,
                        "error": str(e)
                    }
                )

                if (
                    platform == "youtube"
                    and _is_youtube_block_error(str(e))
                ):

                    _youtube_block["until"] = (
                        time.time() + YOUTUBE_BLOCK_COOLDOWN_SEC
                    )

                    print(
                        "YouTube blocked this server - stopping attempts, "
                        f"cooldown {YOUTUBE_BLOCK_COOLDOWN_SEC // 60} min",
                        flush=True
                    )

                    blocked = True
                    break

                continue

    if last_error:

        message = (
            "כל ניסיונות ההורדה נכשלו. "
            f"yt-dlp האחרון החזיר: {last_error}"
        )

        # חסימת אימות האנושיות של יוטיוב ("Sign in to confirm you're
        # not a bot") - חסימה לפי כתובת IP של השרת, לא בעיה בקוד.
        # הפתרון היחיד הוא עוגיות חשבון יוטיוב ב-YOUTUBE_COOKIES.
        error_text = str(last_error)

        if (
            "Sign in to confirm" in error_text
            or "not a bot" in error_text
        ):

            if not YOUTUBE_COOKIES:

                message += (
                    " | יוטיוב חוסם את כתובת ה-IP של השרת ודורש אימות. "
                    "פתרון: להגדיר את משתנה הסביבה YOUTUBE_COOKIES ב-Railway "
                    "עם תוכן קובץ עוגיות יוטיוב בפורמט Netscape "
                    "(cookies.txt שמיוצא מהדפדפן בזמן שמחוברים ליוטיוב)."
                )

            else:

                message += (
                    " | יוטיוב חוסם את כתובת ה-IP של השרת. השרת עוצר "
                    f"ל-{YOUTUBE_BLOCK_COOLDOWN_SEC // 60} דקות כדי לא "
                    "להאריך את החסימה."
                )

        raise RuntimeError(message)

    raise RuntimeError(
        "כל ניסיונות ההורדה נכשלו"
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route(
    "/",
    methods=["GET"]
)
def health():

    # ?drive=1 - בדיקה חיה של גשר הטוקנים לדרייב. מחזיר רק הצלחה או
    # את הודעת השגיאה, אף פעם לא את הטוקן עצמו.
    drive_bridge_check = None

    if request.args.get("drive") == "1":

        try:

            bridge_credentials(API_KEY)
            drive_bridge_check = "ok"

        except Exception as e:

            drive_bridge_check = "failed: " + str(e)[:300]

    return jsonify({

        "drive_auth": {
            "source": DRIVE_AUTH_STATE["source"],
            "bridge_error": DRIVE_AUTH_STATE["bridge_error"],
            "bridge_check": drive_bridge_check,
        },

        "status": "ok",

        "build": "unified-search-2",

        "commit": (
            os.environ.get("RAILWAY_GIT_COMMIT_SHA")
            or os.environ.get("RENDER_GIT_COMMIT")
            or os.environ.get("GIT_COMMIT")
            or ""
        ),

        "cookies_configured":
            bool(YOUTUBE_COOKIES),

        "pot_provider":
            "http://127.0.0.1:4416",

        "mako_stream": "ticket-v2",

        "supported_platforms": [
            "youtube",
            "instagram",
            "tiktok",
            "news_il"
        ],

        "channel_downloads": {
            "enabled": True,
            "max_videos_per_job": MAX_VIDEOS_PER_JOB,
            "delay_between_videos": DELAY_BETWEEN_VIDEOS,
            "block_check": BLOCK_CHECK_BASE_URL,
            "active_jobs": JOB_QUEUE.qsize()
        }

    })


# ============================================================
# FORMATS DIAGNOSTIC
# ============================================================

@app.route(
    "/formats",
    methods=["POST"]
)
def list_formats():

    provided_key = request.headers.get(
        "X-API-KEY",
        ""
    )

    if (
        not API_KEY
        or provided_key != API_KEY
    ):

        return jsonify({
            "success": False,
            "error": "unauthorized"
        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    url = data.get("url")

    player_clients = data.get(
        "player_client"
    )

    use_cookies = data.get(
        "use_cookies",
        True
    )

    use_proxy = data.get(
        "use_proxy",
        False
    )

    season = data.get("season")
    episode = data.get("episode")

    # פענוח הגנתי - ראה הסבר ב-/download.
    mako_trace = []
    url, season, episode = split_glued_season_episode(
        url,
        season=season,
        episode=episode
    )

    # פתרון "סדרה + עונה + פרק" דרך ארכיון ה-web: עמודי השער של
    # מאקו מוגנים באתגר hCaptcha של Radware (גם לדפדפן אמיתי),
    # אבל עמודי VOD עוברים - מספיק להפוך את הבקשה לקישור VOD
    # ישיר של הפרק המבוקש.
    resolved_vod = mako_resolve_episode_via_wayback(
        url,
        season=season,
        episode=episode,
        trace=mako_trace
    )

    if resolved_vod:
        url = resolved_vod

    if not url:

        return jsonify({
            "success": False,
            "error": "missing 'url'"
        }), 400

    page_url = url
    cookies_str = ""

    # ------------------------------------------------
    # כאן (kan.org.il): המרת עמוד פרק לכתובת kaltura: לצורך
    # הצגת הפורמטים בלבד - בלי הורדה.
    # ------------------------------------------------

    kan_extract_url = url

    if (
        "kan.org.il" in url.lower()
        and ".m3u8" not in url.lower()
    ):

        try:

            kan_ep_diag = kan_get_episode_page(url)

            if not kan_ep_diag:

                raise RuntimeError(
                    "לא נמצא נגן (Kaltura) בעמוד הפרק של כאן"
                )

            kan_extract_url = kan_ep_diag["yt_url"]

        except Exception as e:

            return jsonify({
                "success": False,
                "error": str(e)
            }), 400

    il_news_domains = [
        "mako.co.il", "n12.co.il", "13tv.co.il",
        "now14.co.il", "c14.co.il",
        "ynet.co.il"
    ]

    if (
        ".m3u8" not in url.lower()
        and any(
            domain in url.lower()
            for domain in il_news_domains
        )
    ):

        try:

            url, cookies_str = extract_hidden_m3u8(
                url,
                season=season,
                episode=episode
            )

        except Exception as e:

            return jsonify({
                "success": False,
                "error": str(e),
                "mako_resolution": mako_trace
            }), 400

    platform = detect_platform(url)

    player_clients = normalize_player_clients(
        player_clients
    )

    # ברירת המחדל של player_client רלוונטית רק ליוטיוב
    if platform == "youtube" and not player_clients:

        player_clients = [
            "web_embedded"
        ]

    diagnostic = {

        "yt_dlp_version":
            YTDLP_VERSION,

        "platform":
            platform,

        "player_client":
            player_clients,

        "use_cookies":
            bool(use_cookies),

        "use_proxy":
            bool(use_proxy),

        "cookies_configured":
            bool(YOUTUBE_COOKIES),

        "pot_provider":
            "http://127.0.0.1:4416"

    }

    print(
        "FORMAT REQUEST:",
        diagnostic
    )

    try:

        with tempfile.TemporaryDirectory() as tmp_dir:

            ydl_opts = build_ytdlp_options(
                tmp_dir=tmp_dir,
                fmt="video",
                player_clients=player_clients,
                use_cookies=use_cookies,
                platform=platform,
                diagnostic=True,
                use_proxy=use_proxy,
                cookies_str=cookies_str,
                referer=page_url
            )

            ydl_opts["skip_download"] = True

            with yt_dlp.YoutubeDL(
                ydl_opts
            ) as ydl:

                info = ydl.extract_info(
                    kan_extract_url,
                    download=False,
                    process=False
                )

            if not info:

                raise RuntimeError(
                    "yt-dlp לא החזיר מידע"
                )

            formats = (
                info.get(
                    "formats",
                    []
                )
                or []
            )

            simplified = []

            for f in formats:

                simplified.append({

                    "format_id":
                        f.get("format_id"),

                    "ext":
                        f.get("ext"),

                    "acodec":
                        f.get("acodec"),

                    "vcodec":
                        f.get("vcodec"),

                    "abr":
                        f.get("abr"),

                    "tbr":
                        f.get("tbr"),

                    "height":
                        f.get("height"),

                    "width":
                        f.get("width"),

                    "fps":
                        f.get("fps"),

                    "note":
                        f.get("format_note"),

                    "has_url":
                        bool(
                            f.get("url")
                        ),

                    "protocol":
                        f.get("protocol"),

                    "filesize":
                        f.get("filesize"),

                    "filesize_approx":
                        f.get("filesize_approx"),

                })

            real_formats = [

                f
                for f in simplified

                if not str(
                    f["format_id"]
                ).startswith("sb")

            ]

            video_formats = [

                f
                for f in real_formats

                if (
                    f.get("vcodec")
                    and
                    f.get("vcodec") != "none"
                )

            ]

            audio_formats = [

                f
                for f in real_formats

                if (
                    f.get("acodec")
                    and
                    f.get("acodec") != "none"
                )

            ]

            combined_formats = [

                f
                for f in real_formats

                if (
                    f.get("vcodec")
                    and
                    f.get("vcodec") != "none"
                    and
                    f.get("acodec")
                    and
                    f.get("acodec") != "none"
                )

            ]

            return jsonify({

                "success": True,

                "diagnostic":
                    diagnostic,

                "video_info": {

                    "id":
                        info.get("id"),

                    "title":
                        info.get("title"),

                    "extractor":
                        info.get("extractor"),

                    "webpage_url":
                        info.get("webpage_url"),

                    "duration":
                        info.get("duration"),

                    "format_count":
                        len(formats)

                },

                "count":
                    len(simplified),

                "real_count":
                    len(real_formats),

                "video_format_count":
                    len(video_formats),

                "audio_format_count":
                    len(audio_formats),

                "combined_format_count":
                    len(combined_formats),

                "real_formats":
                    real_formats,

                "all_formats":
                    simplified

            })

    except Exception as e:

        traceback.print_exc()

        return jsonify({

            "success": False,

            "diagnostic":
                diagnostic,

            "error":
                str(e),

            "error_type":
                type(e).__name__

        }), 500


# ============================================================
# DOWNLOAD API
# ============================================================

@app.route(
    "/download",
    methods=["POST"]
)
def download():

    provided_key = request.headers.get(
        "X-API-KEY",
        ""
    )

    if (
        not API_KEY
        or provided_key != API_KEY
    ):

        return jsonify({

            "success": False,

            "error":
                "unauthorized"

        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    # כתובות מהמייל נושאות את סימון המקור ("?via=email-search") -
    # מנטרלים אותו קודם, אחרת הוא שובר את זיהוי סוג הקישור
    # (למשל פרק כאן .../s1/88374/ מזוהה בטעות כעונה).
    url = strip_email_source_marker(data.get("url"))

    fmt = data.get(
        "format",
        "audio"
    )

    player_clients = data.get(
        "player_client"
    )

    use_cookies = data.get(
        "use_cookies",
        True
    )

    use_proxy = data.get(
        "use_proxy",
        False
    )

    if not url:

        return jsonify({

            "success": False,

            "error":
                "missing 'url'"

        }), 400

    if not is_valid_video_url(url):

        return jsonify({

            "success": False,

            "error":
                "קישור לא נתמך - יש לשלוח קישור תקין "
                "מיוטיוב, אינסטגרם, טיקטוק או אתרי חדשות"

        }), 400

    if fmt not in (
        "audio",
        "video",
        "auto"
    ):

        return jsonify({

            "success": False,

            "error":
                "format must be "
                "'audio', 'video' or 'auto'"

        }), 400

    season = data.get("season")
    episode = data.get("episode")

    # לקוח שדבק "עונה פרק" לתוך שדה ה-url מקבל פענוח הגנתי -
    # בלי זה הכתובת יוצאת עם רווחים והסריקה מפספסת את הפרק.
    mako_trace = []
    url, season, episode = split_glued_season_episode(
        url,
        season=season,
        episode=episode
    )

    # ------------------------------------------------
    # all_episodes=true: הורדת עונה שלמה כעבודת רקע.
    # רלוונטי רק לקישור סדרה של מאקו (עמוד mako-vod-*/slug);
    # הרשימה מגיעה מאותו מיפוי דטרמיניסטי של /episodes.
    # ------------------------------------------------

    all_episodes = bool(
        data.get("all_episodes")
    )

    if all_episodes:

        parsed_for_season = urllib.parse.urlsplit(url)

        season_path = (
            parsed_for_season.path or ""
        ).strip("/")

        # ------------------------------------------------
        # כאן (kan.org.il): עונה שלמה כעבודת רקע.
        # קישור עונה (.../p-<מזהה>/s<עונה>/) מפורק לרשימת פרקים
        # דרך עמוד העונה עצמו, וכל פרק מומר ל-kaltura: בהרצה.
        # ------------------------------------------------

        is_kan_series = (
            "kan.org.il" in url
            and ".m3u8" not in url.lower()
        )

        if is_kan_series:

            kan_episode_urls = None
            kan_series_info = {}
            resolved_kan = None

            # קיצור-דרך: מזהה פרק (>=10000) על קישור עונה -
            # בונים את כתובת הפרק ישירות, בלי לפרק את עמוד
            # העונה (תלות מיותרת ב-Wayback הלא-יציב).
            shortcut_ep = None

            try:
                shortcut_ep = (
                    int(episode) if episode is not None else None
                )
            except (TypeError, ValueError):
                shortcut_ep = None

            if (
                shortcut_ep is not None
                and shortcut_ep >= 10000
                and re.search(r"/s\d+/?$", url.rstrip("/") + "/")
            ):
                season_m = re.search(r"/s(\d+)/", url)

                kan_series_info = {
                    "title": (
                        "kan-season-"
                        + (season_m.group(1) if season_m else "0")
                    ),
                    "season": (
                        int(season_m.group(1)) if season_m else None
                    ),
                }

                kan_episode_urls = [
                    url.rstrip("/") + "/" + str(shortcut_ep) + "/"
                ]

            else:

                try:

                    resolved_kan = kan_resolve_series_url(
                        url,
                        season=season,
                        episode=None
                    )

                    kan_series_info = kan_extract_series_page(
                        resolved_kan,
                        spn_polls=1
                    )

                    kan_episode_urls = kan_series_info["episode_urls"]

                    if not kan_episode_urls:

                        # ייתכן שזה עמוד פרק בודד
                        if re.search(
                            r"/p-\d+/s\d+/\d+/?$",
                            resolved_kan.rstrip("/")
                        ):
                            kan_episode_urls = [resolved_kan]

                except Exception as kan_ex:

                    return jsonify({
                        "success": False,
                        "error": (
                            "פירוק עמוד הסדרה של כאן נכשל: "
                            + str(kan_ex)
                        )
                    }), 400

            if not kan_episode_urls:

                return jsonify({
                    "success": False,
                    "error": (
                        "לא נמצאו פרקים בעמוד הסדרה/עונה של כאן. "
                        "ודאו שהקישור הוא עמוד עונה "
                        "(למשל .../p-11843/s8/)"
                    )
                }), 400

            # בחירת פרק בודד אם התבקש
            try:

                kan_episode_urls = kan_pick_episode_urls(
                    kan_episode_urls,
                    episode=episode
                )

            except RuntimeError as kan_pick_ex:

                return jsonify({
                    "success": False,
                    "error": str(kan_pick_ex)
                }), 400

            # בניית פריטי העבודה
            kan_items = []
            kan_pending = 0

            for kan_ep_url in kan_episode_urls:

                kan_item = {
                    "id": kan_episode_slug(kan_ep_url),
                    "url": kan_ep_url,
                    "title": None,
                    "status": "pending",
                    "reason": None,
                    "driveLink": None,
                    "fileId": None
                }

                if kan_pending >= MAX_EPISODES_PER_JOB:

                    kan_item["status"] = "skipped"
                    kan_item["reason"] = (
                        "חורג מתקרת הפרקים לבקשה ("
                        + str(MAX_EPISODES_PER_JOB) + ")"
                    )

                else:
                    kan_pending += 1

                kan_items.append(kan_item)

            kan_slug = (
                (kan_series_info.get("title") or "kan-series")
                .replace("|", "-")
                .strip()
            )

            kan_season_num = kan_series_info.get("season")

            # במסלול הקיצור (מזהה פרק על קישור עונה) לא פירקנו
            # עמוד סדרה, אז אין resolved_kan - משתמשים בקישור
            # העונה המקורי מהמשתמש.
            kan_job_url = resolved_kan or url

            kan_job_id = uuid.uuid4().hex[:12]

            kan_job = {
                "id": kan_job_id,
                "kind": "season",
                "platform": "kan",
                "status": "queued",
                "created_at": time.time(),
                "updated_at": time.time(),

                "url": kan_job_url,
                "series": kan_slug,
                "season": kan_season_num,

                "email": (
                    (data.get("email") or "")
                    .strip()
                    .lower()
                ),
                "format": fmt,
                "netfree": False,

                "player_clients": data.get("player_client"),
                "use_cookies": False,
                "use_proxy": data.get("use_proxy", False),

                "total": kan_pending,
                "done_count": 0,
                "failed_count": 0,
                "blocked_count": 0,
                "downloaded_ids": [],

                "resolution": [],

                "items": kan_items
            }

            with JOBS_LOCK:
                JOBS[kan_job_id] = kan_job

            save_job(kan_job)

            JOB_QUEUE.put(kan_job_id)

            return jsonify({
                "success": True,
                "kind": "season",
                "platform": "kan",
                "jobId": kan_job_id,
                "series": kan_slug,
                "season": kan_season_num,
                "total": kan_pending,
                "skipped": len(kan_items) - kan_pending,
                "queuePosition": JOB_QUEUE.qsize(),
                "folderName": (
                    kan_slug
                    + (" - עונה " + str(kan_season_num)
                       if kan_season_num else "")
                ),
                "episodes": [
                    {
                        "episode": i["id"],
                        "url": i["url"],
                        "status": i["status"]
                    }
                    for i in kan_items
                ],
                "progressUrl": "/job/" + kan_job_id
            })

        is_mako_hub = (
            "mako.co.il" in url
            and "VOD-" not in url
            and ".m3u8" not in url.lower()
            and "/" in season_path
            and "vod" in season_path.lower()
        )

        if not is_mako_hub:

            return jsonify({
                "success": False,
                "error": (
                    "all_episodes נתמך כרגע רק לקישור סדרה "
                    "של מאקו (עמוד mako-vod-.../שם-הסדרה). "
                    "קישור VOD של פרק בודד שולחים רגיל, "
                    "בלי all_episodes."
                )
            }), 400

        try:
            season_num = int(season)
        except (TypeError, ValueError):
            season_num = None

        if season_num is None:

            return jsonify({
                "success": False,
                "error": (
                    "all_episodes דורש season מספרי - "
                    'למשל {"url": "...", "season": 1, '
                    '"all_episodes": true}'
                )
            }), 400

        season_trace = []

        ep_map = mako_episode_map(
            url,
            season_num,
            trace=season_trace
        )

        if not ep_map:

            return jsonify({
                "success": False,
                "error": (
                    "לא נמצאו פרקים לעונה "
                    + str(season_num)
                    + " - נסו שוב מאוחר יותר, או שלחו "
                      "קישור VOD ישיר לפרק בודד."
                ),
                "mako_resolution": season_trace
            }), 502

        skip_eps = set()

        for raw_ep in (data.get("skip_episodes") or []):

            try:
                skip_eps.add(int(raw_ep))
            except (TypeError, ValueError):
                continue

        items = []
        pending_count = 0

        for num in sorted(ep_map):

            item = {
                "id": str(num),
                "url": ep_map[num],
                "title": "פרק " + str(num),
                "status": "pending",
                "reason": None,
                "driveLink": None,
                "fileId": None
            }

            if num in skip_eps:

                item["status"] = "skipped"
                item["reason"] = "דולג לפי skip_episodes"

            elif pending_count >= MAX_EPISODES_PER_JOB:

                item["status"] = "skipped"
                item["reason"] = (
                    "חורג מתקרת הפרקים לבקשה ("
                    + str(MAX_EPISODES_PER_JOB) + ")"
                )

            else:
                pending_count += 1

            items.append(item)

        slug = season_path.rsplit("/", 1)[-1]

        job_id = uuid.uuid4().hex[:12]

        job = {
            "id": job_id,
            "kind": "season",
            "status": "queued",
            "created_at": time.time(),
            "updated_at": time.time(),

            "url": url,
            "series": slug,
            "season": season_num,

            "email": (
                (data.get("email") or "")
                .strip()
                .lower()
            ),
            "format": fmt,
            "netfree": False,

            "player_clients": data.get("player_client"),
            "use_cookies": data.get("use_cookies", False),
            "use_proxy": data.get("use_proxy", False),

            "total": pending_count,
            "done_count": 0,
            "failed_count": 0,
            "blocked_count": 0,
            "downloaded_ids": [],

            "resolution": season_trace,

            "items": items
        }

        with JOBS_LOCK:
            JOBS[job_id] = job

        save_job(job)

        JOB_QUEUE.put(job_id)

        return jsonify({
            "success": True,
            "kind": "season",
            "jobId": job_id,
            "series": slug,
            "season": season_num,
            "total": pending_count,
            "skipped": len(items) - pending_count,
            "queuePosition": JOB_QUEUE.qsize(),
            "folderName": slug + " - עונה " + str(season_num),
            "episodes": [
                {
                    "episode": int(i["id"]),
                    "url": i["url"],
                    "status": i["status"]
                }
                for i in items
            ],
            "resolution": season_trace,
            "progressUrl": "/job/" + job_id
        })



    # פתרון "סדרה + עונה + פרק" דרך ארכיון ה-web: עמודי השער של
    # מאקו מוגנים באתגר hCaptcha של Radware (גם לדפדפן אמיתי),
    # אבל עמודי VOD עוברים - מספיק להפוך את הבקשה לקישור VOD
    # ישיר של הפרק המבוקש.
    resolved_vod = mako_resolve_episode_via_wayback(
        url,
        season=season,
        episode=episode,
        trace=mako_trace
    )

    if resolved_vod:
        url = resolved_vod

    page_url = url
    cookies_str = ""

    # ------------------------------------------------
    # כאן (kan.org.il) פרק בודד: מומר ל-kaltura: ויורד ישירות,
    # בלי הסריקה של אתרי החדשות.
    # ------------------------------------------------

    if (
        "kan.org.il" in url.lower()
        and ".m3u8" not in url.lower()
    ):

        # אימות שהפרק קיים + בניית מקורות הזרמה:
        # kaltura: (yt-dlp) וגם m3u8 ישירים מהעמוד כגיבוי,
        # כי Kaltura חוסמת כרגע את השותף של כאן עבור yt-dlp.
        try:

            # קביעת כתובת הפרק: הקישור יכול להיות פרק ישיר
            # (.../s8/756427/), עונה עם פרמטר episode, או עונה
            # בלי פרמטר - ואז שגיאה ברורה (בלי זה ניסינו לשלוף
            # את עמוד העונה כאילו היה פרק, וקיבלנו "לא נמצא
            # מקור הזרמה").
            episode_url = url

            if not re.search(
                r"/s\d+/\d+/?$", url.rstrip("/") + "/"
            ):

                if episode is None:

                    return jsonify({
                        "success": False,
                        "error": (
                            "קישור עונה/סדרה של כאן דורש בחירת פרק: "
                            "הוסיפו פרמטר episode (מספר סידורי או מזהה "
                            "פרק כמו 756427), או שלחו קישור ישיר לפרק "
                            "(.../s1/756427/). רשימת הפרקים זמינה ב-"
                            "POST /episodes {\"url\": \"...\"}, ולהורדת "
                            "עונה שלמה השתמשו ב-all_episodes."
                        )
                    }), 400

                try:
                    ep_num = int(episode)
                except (TypeError, ValueError):
                    ep_num = None

                if (
                    ep_num is not None
                    and ep_num >= 10000
                    and re.search(r"/s\d+/?$", url.rstrip("/") + "/")
                ):
                    # מזהה פרק על קישור עונה - שרשור ישיר,
                    # שומר על העונה מהקישור של המשתמש
                    episode_url = (
                        url.rstrip("/") + "/" + str(ep_num) + "/"
                    )

                else:
                    # מספר סידורי או קישור סדרה - דרך עמוד העונה
                    resolved_kan = kan_resolve_series_url(
                        url,
                        season=season,
                        episode=None
                    )

                    series_info = kan_extract_series_page(
                        resolved_kan,
                        spn_polls=1
                    )

                    picked = kan_pick_episode_urls(
                        series_info["episode_urls"],
                        episode=episode
                    )

                    episode_url = picked[0]

            kan_page_html = kan_page_fetch(episode_url)

            kan_ep_page = _kan_parse_episode_page(
                episode_url,
                kan_page_html
            )

            kan_candidates = kan_episode_stream_candidates(
                episode_url,
                page_html=kan_page_html,
            )

        except Exception as e:

            return jsonify({
                "success": False,
                "error": str(e)
            }), 400

        platform = "kan"

        print(
            "DOWNLOAD REQUEST:",
            {
                "platform": "kan",
                "format": fmt,
                "entry_id": kan_ep_page["entry_id"],
                "yt_dlp_version": YTDLP_VERSION
            },
            flush=True
        )

        kan_last_error = None
        kan_source_errors = []

        try:

            local_path = title = None

            for kan_source in kan_candidates:

                try:

                    with tempfile.TemporaryDirectory() as tmp_dir:

                        local_path, title = download_video(
                            url=kan_source,
                            fmt=fmt,
                            tmp_dir=tmp_dir,
                            player_clients=player_clients,
                            use_cookies=False,
                            use_proxy=use_proxy,
                            cookies_str="",
                            referer=episode_url,
                            platform="kan"
                        )

                    break

                except Exception as kan_source_err:

                    kan_last_error = kan_source_err

                    kan_source_errors.append({
                        "source": str(kan_source)[:160],
                        "error": str(kan_source_err)[:400],
                    })

                    print(
                        "KAN source attempt failed:",
                        {
                            "source": str(kan_source)[:120],
                            "error": str(kan_source_err)[:160]
                        },
                        flush=True,
                    )

            if not local_path:

                raise kan_last_error or RuntimeError(
                    "לא נמצא מקור הזרמה שעובד"
                )

            drive_link, file_id = upload_to_drive(
                local_path,
                os.path.basename(local_path)
            )

            return jsonify({
                "success": True,
                "platform": "kan",
                "title": title,
                "driveLink": drive_link,
                "fileId": file_id
            })

        except Exception as e:

            traceback.print_exc()

            # דיווח מפורט - בלי ליפול לנתיב הכללי שמאבד את
            # פרטי הכישלון של כל מקור (kaltura / m3u8).
            return jsonify({
                "success": False,
                "platform": "kan",
                "error": "הורדת כאן נכשלה: " + str(e)[:400],
                "sources_tried": kan_source_errors,
            }), 502

    il_news_domains = [
        "mako.co.il", "mako.tv", "n12.co.il", "13tv.co.il",
        "now14.co.il", "c14.co.il",
        "ynet.co.il"
    ]

    if (
        ".m3u8" not in url.lower()
        and any(
            domain in url.lower()
            for domain in il_news_domains
        )
    ):

        try:

            url, cookies_str = extract_hidden_m3u8(
                url,
                season=season,
                episode=episode
            )

        except Exception as e:

            # ל-yt-dlp אין מחלץ למאקו: נפילה לשם תייצר רק
            # "Unsupported URL" מעמוד האתגר של Radware ותבלבל.
            # מדווחים את שגיאת הסריקה עצמה.
            if "mako.co.il" in (page_url or "") or "mako.tv" in (page_url or ""):
                return jsonify({
                    "success": False,
                    "error": "סריקת הדפדפן נכשלה: " + str(e),
                    "mako_resolution": mako_trace
                }), 502

            # הסריקה נכשלה - לא נופלים מיד. yt-dlp מחזיק מחלצים
            # מובנים לחלק מהאתרים, ואם גם הוא ייכשל נדווח למעלה.
            print(
                "Playwright scrape failed, trying yt-dlp directly:",
                {
                    "url": page_url,
                    "error": str(e)[:200]
                },
                flush=True
            )

            url = page_url
            cookies_str = ""

    platform = detect_platform(url)

    print(
        "DOWNLOAD REQUEST:",
        {
            "platform": platform,
            "format": fmt,
            "player_client": player_clients,
            "use_cookies": bool(use_cookies),
            "cookies_configured": bool(YOUTUBE_COOKIES),
            "use_proxy": bool(use_proxy),
            "yt_dlp_version": YTDLP_VERSION
        }
    )

    try:

        with tempfile.TemporaryDirectory() as tmp_dir:

            local_path, title = (
                download_video(

                    url=url,

                    fmt=fmt,

                    tmp_dir=tmp_dir,

                    player_clients=player_clients,

                    use_cookies=use_cookies,

                    use_proxy=use_proxy,

                    cookies_str=cookies_str,

                    referer=page_url

                )
            )

            drive_link, file_id = (
                upload_to_drive(

                    local_path,

                    os.path.basename(
                        local_path
                    )

                )
            )

            return jsonify({

                "success": True,

                "platform":
                    platform,

                "title":
                    title,

                "driveLink":
                    drive_link,

                "fileId":
                    file_id

            })

    except Exception as e:

        traceback.print_exc()

        return jsonify({

            "success": False,

            "error":
                str(e)

        }), 500


# ============================================================
# EPISODES LIST (MAKO SERIES)
# ============================================================

@app.route("/diag/kan", methods=["POST", "GET"])
def kan_diag():

    """
    אבחון חי של שרשרת כאן: מצב הפרוקסי, כל ערוץ בנפרד,
    ומה השרשרת המלאה מחזירה (entry + מספר m3u8).
    """

    provided_key = request.headers.get("X-API-KEY", "")

    if (
        not API_KEY
        or provided_key != API_KEY
    ):
        return jsonify({
            "success": False,
            "error": "unauthorized"
        }), 401

    data = request.get_json(silent=True) or {}

    episode_url = (
        data.get("url")
        or "https://www.kan.org.il/content/kan/kan-11/p-11843/s8/756427/"
    )

    proxy = _kan_get_working_proxy()

    result = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "proxy": {
            "KAN_PROXY_URL_set": bool(KAN_PROXY_URL),
            "host": (
                KAN_PROXY_URL.split("@")[-1] if KAN_PROXY_URL else None
            ),
            "resolved": (
                proxy.split("@")[-1] if proxy else None
            ),
        },
        "channels": {},
    }

    # ---- ערוץ 1: ישיר עם חיקוי דפדפן ----
    try:
        status, body = _kan_fetch_impersonated(
            episode_url, timeout=KAN_DIRECT_TIMEOUT
        )
        result["channels"]["direct"] = {
            "status": status,
            "len": len(body),
            "usable": _kan_wayback_content_ok(body, episode_url),
            "m3u8": (
                len(kan_extract_m3u8_urls(body))
                if status == 200 and body
                else 0
            ),
        }
    except Exception as e:
        result["channels"]["direct"] = {"error": str(e)[:120]}

    # ---- ערוץ 2: פרוקסי ישראלי עם חיקוי דפדפן ----
    if proxy:
        try:
            status, body = _kan_fetch_impersonated(
                episode_url, proxy=proxy, timeout=90
            )
            result["channels"]["proxy"] = {
                "status": status,
                "len": len(body),
                "usable": _kan_wayback_content_ok(
                    body, episode_url
                ),
                "m3u8": (
                    len(kan_extract_m3u8_urls(body))
                    if status == 200 and body
                    else 0
                ),
                "via": proxy.split("@")[-1],
            }
        except Exception as e:
            result["channels"]["proxy"] = {
                "error": str(e)[:120],
                "via": proxy.split("@")[-1],
            }
    else:
        result["channels"]["proxy"] = {"skipped": "no proxy available"}

    # ---- השרשרת המלאה (כמו בהורדה) ----
    try:
        body = kan_page_fetch(episode_url, spn_polls=1)
        entry = None
        entry_error = None
        try:
            _yt, entry = kan_extract_kaltura_entry(episode_url, body)
        except Exception as entry_err:
            entry_error = str(entry_err)[:120]
        result["channels"]["full_chain"] = {
            "len": len(body or ""),
            "entry": entry,
            "entry_error": entry_error,
            "m3u8": len(kan_extract_m3u8_urls(body or "")),
        }
    except Exception as e:
        result["channels"]["full_chain"] = {"error": str(e)[:120]}

    return jsonify(result)


def _drive_error_hint(error_text):

    """הסבר בעברית לשגיאות החידוש הנפוצות של גוגל."""

    text = error_text.lower()

    if "unauthorized_client" in text:
        return (
            "הטוקן נוצר עם Client אחר. ב-OAuth Playground יש לסמן "
            "'Use your own OAuth credentials' ולהזין את אותם Client ID "
            "ו-Secret שמוגדרים ב-Railway, ואז להפיק טוקן חדש."
        )

    if "invalid_scope" in text:
        return (
            "הטוקן נוצר עם הרשאה אחרת. יש להפיק אותו עם ההרשאה "
            "https://www.googleapis.com/auth/drive.file בדיוק."
        )

    if "invalid_client" in text:
        return (
            "ה-Client ID או ה-Client Secret ב-Railway שגויים, או שה-Client "
            "נמחק ב-Google Cloud Console."
        )

    if "invalid_grant" in text:
        return (
            "גוגל ביטלה את הטוקן או שהוא לא שייך ל-Client הזה. סיבות נפוצות: "
            "האפליקציה במצב Testing (טוקנים פגים אחרי 7 ימים - יש לפרסם "
            "אותה ב-OAuth consent screen), טוקן שהופק ב-Playground בלי "
            "'Use your own OAuth credentials', או Client ID מפרויקט אחר."
        )

    return None


@app.route("/diag/drive", methods=["GET", "POST"])
def drive_diag():

    """
    אבחון חי של מעלה הדרייב: האם המשתנים מוגדרים, והאם חידוש
    ה-access token מה-refresh token מצליח כרגע. כישלון חידוש
    (invalid_grant) פירושו שה-refresh token בוטל/פג - ואז כל
    הורדה שתעבוד תיפול בשלב ההעלאה לדרייב.
    """

    provided_key = request.headers.get("X-API-KEY", "")

    if (
        not API_KEY
        or provided_key != API_KEY
    ):
        return jsonify({
            "success": False,
            "error": "unauthorized"
        }), 401

    result = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "config": {
            "client_id_set": bool(GOOGLE_OAUTH_CLIENT_ID),
            "client_secret_set": bool(GOOGLE_OAUTH_CLIENT_SECRET),
            "refresh_token_set": bool(GOOGLE_OAUTH_REFRESH_TOKEN),
            "refresh_token_length": (
                len(GOOGLE_OAUTH_REFRESH_TOKEN)
                if GOOGLE_OAUTH_REFRESH_TOKEN
                else 0
            ),
            "drive_folder_id_set": bool(DRIVE_FOLDER_ID),
            # סוף ה-Client ID (לא סודי) - להשוואה מול Google Cloud Console
            # ומול מה שהוזן ב-OAuth Playground.
            "client_id_tail": (
                "..." + GOOGLE_OAUTH_CLIENT_ID[-30:]
                if GOOGLE_OAUTH_CLIENT_ID
                else None
            ),
        },
    }

    # בדיקת חידוש אמיתית - אותו מסלול ש-get_drive_service עובר
    try:

        service = get_drive_service()

        about = service.about().get(
            fields="user, storageQuota"
        ).execute()

        result["refresh"] = "ok"
        result["auth_source"] = DRIVE_AUTH_STATE["source"]
        result["user"] = (
            (about.get("user") or {}).get("emailAddress")
        )

    except Exception as e:

        result["refresh"] = "failed"
        result["error"] = str(e)[:300]
        result["hint"] = _drive_error_hint(str(e))

    result["bridge_url_set"] = bool(bridge_url())
    if DRIVE_AUTH_STATE["bridge_error"]:
        result["bridge_error"] = DRIVE_AUTH_STATE["bridge_error"]

    return jsonify(result)


@app.route("/episodes", methods=["POST"])
def list_episodes():

    # מספר העונות האחרונות שמוחזרות עבור קישור סדרה בלי עונה.
    # לא מחזירים לעולם את כל הפרקים של כל העונות (מאות סרטונים) -
    # טופס החיפוש בונה מהעונות האלה כרטיסי "בחרו פרק" בלבד.
    MAX_SEASONS_IN_EPISODES = 2

    provided_key = request.headers.get("X-API-KEY", "")

    # מקבלים את מפתח ה-API הרגיל או את מפתח טופס החיפוש -
    # טופס החיפוש קורא לנקודה הזאת כדי להרחיב תוצאות עונה
    # של כאן לכפתורי פרקים במייל
    allowed = {API_KEY, UNIFIED_SEARCH_KEY}
    allowed.discard("")

    if (
        not provided_key
        or provided_key not in allowed
    ):
        return jsonify({
            "success": False,
            "error": "unauthorized"
        }), 401

    data = request.get_json(silent=True) or {}

    raw_url = data.get("url")

    if not raw_url:
        return jsonify({
            "success": False,
            "error": "missing 'url'"
        }), 400

    # פענוח הגנתי - אם הודבקו "עונה פרק" לתוך הכתובת, העונה מנוצלת
    # כאן במקום להיזרק (שדה season מפורש גובר על המודבק).
    url, glued_season, _glued_episode = split_glued_season_episode(
        raw_url
    )

    season = data.get("season", glued_season)

    # ------------------------------------------------
    # כאן (kan.org.il): רשימת פרקים מעמוד סדרה/עונה.
    # הקישור כבר מכיל את העונה, והעונה מהפרמטר אופציונלית.
    # ------------------------------------------------

    if "kan.org.il" in url.lower():

        try:

            resolved = kan_resolve_series_url(
                url,
                season=season,
                episode=None
            )

        except Exception as e:

            return jsonify({
                "success": False,
                "error": str(e)
            }), 400

        # ------------------------------------------------
        # קישור סדרה בלי עונה (…/p-11843/): מחזירים את שתי
        # העונות האחרונות שיצאו בלבד - לא את כל הפרקים של
        # כל העונות. המייל של טופס החיפוש בונה מהן כרטיסי
        # "בחרו פרק" לכל עונה, בלי אופציית הורדת-הכל.
        # ------------------------------------------------
        if not re.search(
            r"/p-\d+/s\d+/?$",
            resolved.rstrip("/") + "/"
        ):

            # עמוד שער של סדרה עשוי לקשר לעמודי עונות במקום לפרקים -
            # ואז קישורי הפרקים חסרים והחילוץ הרגיל זורק שגיאה. במקרה
            # כזה (וגם כשהפרקים שהוחזרו בלי סיומת עונה) שולפים את
            # ה-HTML ישירות ומחלצים ממנו את קישורי העונות.
            season_nums = []
            series_info = None
            hub_html = None

            try:
                series_info = kan_extract_series_page(
                    resolved, spn_polls=1
                )

                season_nums = sorted(
                    {
                        int(m.group(1))
                        for m in (
                            re.search(r"/p-\d+/s(\d+)/\d+/", ep)
                            for ep in series_info["episode_urls"]
                        )
                        if m
                    },
                    reverse=True,
                )

            except Exception:

                # כנראה עמוד שער שמקשר לעונות ולא לפרקים -
                # ממשיכים לחילוץ עונות מה-HTML הגולמי.
                pass

            if not season_nums:

                try:
                    hub_html = kan_page_fetch(resolved, spn_polls=1)
                except Exception as e:
                    return jsonify({
                        "success": False,
                        "error": str(e)
                    }), 400

                season_nums = kan_extract_hub_season_nums(hub_html)

            if not season_nums:
                return jsonify({
                    "success": False,
                    "error": "לא נמצאו עונות בעמוד הסדרה"
                }), 404

            seasons_payload = []

            for sn in season_nums[:MAX_SEASONS_IN_EPISODES]:

                season_url = resolved.rstrip("/") + f"/s{sn}/"

                try:
                    s_info = kan_extract_series_page(
                        season_url, spn_polls=1
                    )
                except Exception:
                    continue

                seasons_payload.append({
                    "season": sn,
                    "count": len(s_info["episode_urls"]),
                    "episodes": [
                        {"episode": kan_episode_slug(ep), "url": ep}
                        for ep in s_info["episode_urls"]
                    ],
                })

            seasons_payload = [
                s for s in seasons_payload if s["count"] > 0
            ]

            if not seasons_payload:
                return jsonify({
                    "success": False,
                    "error": "לא הצליח לטעון את עונות הסדרה"
                }), 502

            latest = seasons_payload[0]

            # בענף עמוד-השער ייתכן שאין series_info - כותרת מה-HTML
            # הגולמי, ומזהה הסדרה מהכתובת עצמה.
            hub_title = None

            title_match = re.search(
                r"<title>([^<]+)</title>",
                hub_html or ""
            )

            if title_match:
                hub_title = html_lib.unescape(
                    title_match.group(1)
                ).strip()

            id_match = re.search(r"/p-(\d+)/", resolved)

            return jsonify({
                "success": True,
                "platform": "kan",
                "url": resolved,
                "series": {
                    "title": (
                        (series_info or {}).get("title") or hub_title
                    ),
                    "series_id": (
                        (series_info or {}).get("series_id")
                        or (id_match.group(1) if id_match else None)
                    ),
                    "season": latest["season"]
                },
                "season": latest["season"],
                "count": latest["count"],
                "episodes": latest["episodes"],
                "seasons": seasons_payload,
                "latestSeasonsOnly": True
            })

        try:

            series_info = kan_extract_series_page(resolved, spn_polls=1)

        except Exception as e:

            return jsonify({
                "success": False,
                "error": str(e)
            }), 400

        episodes = [
            {
                "episode": kan_episode_slug(ep),
                "url": ep
            }
            for ep in series_info["episode_urls"]
        ]

        return jsonify({
            "success": True,
            "platform": "kan",
            "url": resolved,
            "series": {
                "title": series_info["title"],
                "series_id": series_info["series_id"],
                "season": series_info["season"]
            },
            "season": series_info["season"],
            "count": len(episodes),
            "episodes": episodes
        })

    # ------------------------------------------------
    # מאקו: המיפוי הדטרמיניסטי הקיים - דורש עונה מספרית
    # ------------------------------------------------

    # קישור עמוד עונה של מאקו (...-s3/VOD-xxx.htm או השער
    # ...-s3/) כבר מכיל את העונה - חולצים אותה משם, בדיוק כמו
    # שקישור עונה של כאן נושא את העונה בעצמו. פרמטר season
    # מפורש גובר על החילוץ מהקישור.
    if season is None:
        season = mako_season_from_url(url)

    # ------------------------------------------------
    # קישור שער של סדרה בלי עונה (.../nutuk_drama): מחזירים
    # את שתי העונות האחרונות שיצאו בלבד - לא הורדת-הכל.
    # ------------------------------------------------
    if season is None:

        trace = []

        parsed_hub = urllib.parse.urlsplit(url)
        hub_path = (parsed_hub.path or "").strip("/")

        if not hub_path or "/" not in hub_path:
            return jsonify({
                "success": False,
                "error": "קישור סדרת מאקו לא מזוהה"
            }), 400

        hub_slug = hub_path.rsplit("/", 1)[-1]
        hub_base = hub_path.rsplit("/", 1)[0]

        html_text = None

        # מקור 1: צילום עמוד השער בארכיון ה-web (אותו מנגנון
        # של mako_episode_map). sort=reverse: צילומים חדשים ראשה -
        # סדרה ותיקה עם אלפי צילומים לא תקבל צילום בן עשור.
        try:

            cdx_url = (
                "https://web.archive.org/cdx/search/cdx"
                f"?url={parsed_hub.netloc}/{hub_path}"
                "&output=json&fl=timestamp,original,statuscode"
                "&limit=50&sort=reverse"
            )

            req = urllib.request.Request(
                cdx_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            )

            with urllib.request.urlopen(req, timeout=40) as resp:
                rows = json.loads(resp.read().decode("utf-8", "replace"))

            snapshots = [
                (row[0], row[1])
                for row in (rows or [])[1:]
                if len(row) >= 3 and row[2] == "200"
            ]

            if snapshots:

                latest_ts, latest_url = max(
                    snapshots, key=lambda r: r[0]
                )

                snap_req = urllib.request.Request(
                    f"https://web.archive.org/web/{latest_ts}/{latest_url}",
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        )
                    },
                )

                with urllib.request.urlopen(snap_req, timeout=45) as resp:
                    html_text = resp.read().decode("utf-8", "replace")

        except Exception as ex:

            trace.append(
                "series: wayback failed: " + str(ex)[:100]
            )

        # מקור 2: עמוד השער החי דרך r.jina.ai - לא רק כגיבוי לכישלון
        # הארכיון אלא גם כהשלמה: צילום ישן יכול להיות חסר את העונות
        # החדשות, ולכן מחברים את שני המקורות וקודם כל מוצים את
        # דפוסי העונות מהחי (אם הוחזר).
        jina_html = None

        if html_text:
            # הצילום הצליח - עדיין שולפים את העמוד החי להשלמת עונות
            # חדשות שטרם נארכבו. כישלון שקט: הצילום נשאר המקור.
            try:
                jina_html = mako_fetch_hub_html_via_jina(url)
            except Exception:
                jina_html = None
        else:
            # הארכיון נכשל לגמרי - העמוד החי הוא המקור היחיד.
            html_text = mako_fetch_hub_html_via_jina(url)
            jina_html = html_text

        if not html_text and not jina_html:
            return jsonify({
                "success": False,
                "error": "לא הצליח לטעון את עמוד הסדרה",
                "resolution": trace
            }), 502

        # איחוד שני המקורות לטובת חילוץ העונות: העונות מהעמוד החי
        # (עדכני) וגם מהצילום (לגיבוי). לא מזיק - הרשימה ממוינת
        # ומנוקה מכפילויות.
        combined_html = "\n".join(
            part for part in (html_text, jina_html) if part
        )

        season_nums = mako_extract_season_dirs(
            combined_html, hub_slug
        )

        seasons_payload = []

        for sn in season_nums[:MAX_SEASONS_IN_EPISODES]:

            season_dir = f"{hub_slug}-s{sn}"

            # עוגני הפרקים נשלפים מהמקור הראשון שמכיל אותם:
            # קודם הצילום, ואז העמוד החי דרך jina. צילום ישן לא
            # חוסם פרקים חדשים - אם אין בו עוגנים, החי נוסה.
            mapping = {}

            for source_html in (html_text, jina_html):

                if not source_html:
                    continue

                mapping = mako_parse_hub_episode_map(
                    source_html, hub_base, season_dir
                )

                if mapping:
                    break

            if mapping:
                MAKO_WAYBACK_CACHE[(hub_path, sn)] = dict(mapping)

            seasons_payload.append({
                "season": sn,
                "count": len(mapping),
                "episodes": [
                    {"episode": num, "url": link}
                    for num, link in sorted(mapping.items())
                ],
            })

        seasons_payload = [
            s for s in seasons_payload if s["count"] > 0
        ]

        if not seasons_payload:
            return jsonify({
                "success": False,
                "error": (
                    "לא נמצאו פרקים לעונות האחרונות - "
                    "נסו קישור עונה ישיר"
                ),
                "resolution": trace
            }), 502

        latest = seasons_payload[0]

        return jsonify({
            "success": True,
            "url": url,
            "season": latest["season"],
            "count": latest["count"],
            "episodes": latest["episodes"],
            "seasons": seasons_payload,
            "latestSeasonsOnly": True,
            "resolution": trace
        })

    try:
        season = int(season)
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "error": (
                "season חייב להיות מספר - שלחו למשל "
                '{"url": "...", "season": 1}'
            )
        }), 400

    trace = []

    mapping = mako_episode_map(url, season, trace=trace)

    episodes = [
        {"episode": num, "url": link}
        for num, link in sorted(mapping.items())
    ]

    return jsonify({
        "success": True,
        "url": url,
        "season": season,
        "count": len(episodes),
        "episodes": episodes,
        "resolution": trace
    })


# ============================================================
# TAMPERMONKEY / EXTERNAL API INTEGRATION
# ============================================================

@app.route("/tampermonkey-download", methods=["POST"])
def tampermonkey_download():
    provided_key = request.headers.get("X-API-KEY", "")
    if not API_KEY or provided_key != API_KEY:
        return jsonify({"success": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    # כתובות מהמייל נושאות את סימון המקור - מנטרלים אותו קודם
    url = strip_email_source_marker(data.get("url"))
    fmt = data.get("format", "audio")
    email = data.get("email", "").strip().lower()

    if not url or not email:
        return jsonify({"success": False, "error": "missing 'url' or 'email'"}), 400

    if not is_valid_video_url(url):
        return jsonify({"success": False, "error": "קישור לא נתמך"}), 400

    # פענוח הגנתי של עונה/פרק שהודבקו ל-url - ראה הסבר ב-/download.
    url, tm_season, tm_episode = split_glued_season_episode(url)

    tm_resolved = mako_resolve_episode_via_wayback(
        url,
        season=tm_season,
        episode=tm_episode
    )

    if tm_resolved:
        url = tm_resolved

    page_url = url
    cookies_str = ""
    il_news_domains = ["mako.co.il", "mako.tv", "n12.co.il", "13tv.co.il", "kan.org.il", "now14.co.il", "c14.co.il", "ynet.co.il"]
    if ".m3u8" not in url.lower() and any(domain in url.lower() for domain in il_news_domains):
        try:
            url, cookies_str = extract_hidden_m3u8(
                url,
                season=tm_season,
                episode=tm_episode
            )
        except Exception as e:
            print(
                "Playwright scrape failed, trying yt-dlp directly:",
                {"url": page_url, "error": str(e)[:200]},
                flush=True
            )
            url = page_url
            cookies_str = ""

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            local_path, title = download_video(
                url=url,
                fmt=fmt,
                tmp_dir=tmp_dir,
                cookies_str=cookies_str,
                referer=page_url
            )
            drive_link, file_id = upload_to_drive(local_path, os.path.basename(local_path))

            return jsonify({
                "success": True,
                "title": title,
                "driveLink": drive_link,
                "fileId": file_id
            })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": repr(e)}), 500


# ============================================================
# GEMINI IMAGES -> DRIVE
# ============================================================
# תוסף הדפדפן ל-gemini.google.com שולח לכאן כל תמונה שגמיני יוצר
# (base64, או כתובת לשליפה בשרת כגיבוי), השרת מעלה אותה לדרייב
# עם אותם פרטי OAuth שמשמשים להורדות הווידאו, ומחזיר קישור.
# כך התמונות נשמרות בדרייב ולא רק בהתכתבות עם גמיני.
#
# תיקיית היעד: DRIVE_FOLDER_ID אם הוגדר, אחרת תיקיית
# "תמונות גמיני" בשורש הדרייב (נוצרת אוטומטית בפעם הראשונה).
#
# אבטחה: ה-Apps Script מאמת משתמש/מכשיר ומכסות לפני ההעברה
# לכאן, וכאן נדרש X-API-KEY כרגיל. תקרת גודל מגינה מפני בקשות ענק.

GEMINI_IMAGE_MAX_BYTES = int(
    os.environ.get(
        "GEMINI_IMAGE_MAX_BYTES",
        str(20 * 1024 * 1024)
    )
)

GEMINI_FOLDER_NAME = "תמונות גמיני"

_gemini_folder_id = None


def _get_or_create_gemini_folder(service):
    """
    מזהה תיקיית GEMINI_FOLDER_NAME בשורש הדרייב, ויוצר אותה אם
    היא עוד לא קיימת. התוצאה נשמרת בזיכרון התהליך כדי שלא נריץ
    חיפוש מול ה-API על כל תמונה.
    """

    global _gemini_folder_id

    if _gemini_folder_id:
        return _gemini_folder_id

    query = (
        "mimeType='application/vnd.google-apps.folder' "
        f"and name='{GEMINI_FOLDER_NAME}' and trashed=false"
    )

    results = (
        service.files()
        .list(
            q=query,
            spaces="drive",
            fields="files(id)",
            pageSize=1,
        )
        .execute()
    )

    existing = results.get("files", [])

    if existing:
        _gemini_folder_id = existing[0]["id"]
        return _gemini_folder_id

    created = (
        service.files()
        .create(
            body={
                "name": GEMINI_FOLDER_NAME,
                "mimeType": "application/vnd.google-apps.folder",
            },
            fields="id",
        )
        .execute()
    )

    _gemini_folder_id = created["id"]

    return _gemini_folder_id


def upload_gemini_image(image_bytes, filename):
    """
    העלאת תמונה מזיכרון לדרייב. מוחזר (קישור webViewLink, מזהה קובץ).
    """

    service = get_drive_service()

    try:
        folder_id = _get_or_create_gemini_folder(service)
    except Exception:

        # גם אם איתור/יצירת התיקייה נכשל - העלאה לשורש עדיפה על כישלון
        folder_id = DRIVE_FOLDER_ID or None

    uploaded = (
        service.files()
        .create(
            body={
                "name": filename,
                "parents": [folder_id] if folder_id else [],
            },
            media_body=MediaInMemoryUpload(
                image_bytes,
                mimetype="image/png",
                resumable=False,
            ),
            fields="id, webViewLink",
        )
        .execute()
    )

    return (
        uploaded.get("webViewLink"),
        uploaded.get("id"),
    )


@app.route("/gemini-image", methods=["POST"])
def gemini_image_upload():

    provided_key = request.headers.get("X-API-KEY", "")
    if not API_KEY or provided_key != API_KEY:
        return jsonify({"success": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    prompt = (data.get("prompt") or "").strip()
    image_b64 = (data.get("image") or "").strip()
    image_url = (data.get("image_url") or "").strip()

    if not email:
        return jsonify({"success": False, "error": "missing 'email'"}), 400

    image_bytes = None

    if image_b64:

        # תמיכה ב-Data URL מלא ("data:image/png;base64,...") וב-base64 חשוף
        if image_b64.startswith("data:image"):
            _, _, image_b64 = image_b64.partition(",")

        try:
            image_bytes = base64.b64decode(image_b64, validate=True)
        except Exception:
            return jsonify(
                {"success": False, "error": "image is not valid base64"}
            ), 400

    elif image_url:

        # גיבוי: הדפדפן לא הצליח להוריד את התמונה - השרת מנסה בעצמו.
        # כתובות googleusercontent של תמונות גמיני פומביות ונגישות מכל IP.
        if not image_url.startswith(("http://", "https://")):
            return jsonify(
                {"success": False, "error": "invalid 'image_url'"}
            ), 400

        try:
            req = urllib.request.Request(
                image_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                image_bytes = resp.read(GEMINI_IMAGE_MAX_BYTES + 1)

        except Exception as e:
            return jsonify(
                {
                    "success": False,
                    "error": "image download failed: " + str(e)[:120],
                }
            ), 502

    if not image_bytes:
        return jsonify(
            {"success": False, "error": "missing 'image' or 'image_url'"}
        ), 400

    if len(image_bytes) > GEMINI_IMAGE_MAX_BYTES:
        return jsonify(
            {"success": False, "error": "image too large"}
        ), 413

    # שם הקובץ: הנחיה מנוקה + חותמת זמן, או חותמת זמן בלבד
    safe_prompt = "".join(
        ch if (ch.isalnum() or ch in " -_.") else " "
        for ch in prompt
    )
    safe_prompt = re.sub(r"\s+", " ", safe_prompt).strip()[:60]

    stamp = time.strftime("%Y-%m-%d %H-%M-%S")

    if safe_prompt:
        filename = f"גמיני - {safe_prompt} - {stamp}.png"
    else:
        filename = f"גמיני - {stamp}.png"

    try:
        drive_link, file_id = upload_gemini_image(image_bytes, filename)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": repr(e)}), 500

    print(
        "Gemini image uploaded: "
        f"{filename} ({len(image_bytes)} bytes) for {email}",
        flush=True,
    )

    return jsonify(
        {
            "success": True,
            "title": filename,
            "driveLink": drive_link,
            "fileId": file_id,
        }
    )


# ============================================================
# CHANNEL / PLAYLIST URL DETECTION
# ============================================================
# כתובות ערוץ ופלייליסט לא עוברות ב-is_valid_video_url (שם נמצאות
# רק כתובות של סרטון בודד), ולכן יש להן זיהוי נפרד.

CHANNEL_URL_PATTERNS = [

    # https://www.youtube.com/@handle  (+ /videos /shorts /streams)
    re.compile(
        r"(https?://)?(www\.|m\.)?youtube\.com/@[\w\-.]+",
        re.IGNORECASE
    ),

    # https://www.youtube.com/channel/UCxxxx
    re.compile(
        r"(https?://)?(www\.|m\.)?youtube\.com/channel/[\w\-]+",
        re.IGNORECASE
    ),

    # כתובות ישנות: /c/name  /user/name
    re.compile(
        r"(https?://)?(www\.|m\.)?youtube\.com/(c|user)/[\w\-.]+",
        re.IGNORECASE
    ),

    # פלייליסט
    re.compile(
        r"(https?://)?(www\.|m\.)?youtube\.com/playlist\?list=[\w\-]+",
        re.IGNORECASE
    ),
]


def is_channel_url(url):

    if not url:
        return False

    return any(
        pattern.match(url.strip())
        for pattern in CHANNEL_URL_PATTERNS
    )


def normalize_channel_url(url):
    """
    מוסיף /videos לכתובת ערוץ, כדי ש-yt-dlp יביא את רשימת הסרטונים
    ולא את עמוד הבית של הערוץ (שמכיל גם פלייליסטים ותוכן מוטמע
    של ערוצים אחרים).
    """

    if not url:
        return url

    clean = url.strip()

    if not clean.lower().startswith("http"):
        clean = "https://" + clean

    # פלייליסט - משאירים כמו שהוא
    if "list=" in clean.lower():
        return clean

    # אם כבר מצוין טאב מפורש - לא נוגעים
    for tab in (
        "/videos",
        "/shorts",
        "/streams",
        "/playlists",
        "/featured"
    ):
        if tab in clean.lower():
            return clean

    return clean.rstrip("/") + "/videos"


CHANNEL_TABS = (
    "/videos",
    "/shorts",
    "/streams",
    "/playlists",
    "/featured",
    "/live"
)


def channel_listing_candidates(url):
    """
    לא לכל ערוץ יש טאב /videos (יש ערוצים של שורטס או שידורים
    חיים בלבד). מחזיר רשימת כתובות לנסות לפי הסדר, עד שאחת מהן
    מחזירה סרטונים.
    """

    if not url:
        return []

    clean = url.strip()

    if not clean.lower().startswith("http"):
        clean = "https://" + clean

    # פלייליסט - אין טאבים
    if "list=" in clean.lower():
        return [clean]

    lower = clean.lower()

    for tab in CHANNEL_TABS:

        if lower.rstrip("/").endswith(tab):

            base = clean.rstrip("/")[: -len(tab)]

            # קודם מה שהמשתמש ביקש במפורש, ואז גיבויים
            return [
                clean,
                base + "/videos",
                base + "/streams",
                base + "/shorts",
                base
            ]

    base = clean.rstrip("/")

    return [
        base + "/videos",
        base + "/streams",
        base + "/shorts",
        base
    ]


def extract_channel_identifier(url):
    """
    מחזיר מזהה יציב לערוץ, לשימוש מול שירות בדיקת החסימה ולשמירת
    הלוג אצל הלקוח. מחזיר טאפל (סוג, מזהה).
    """

    if not url:
        return (None, None)

    text = url.strip()

    match = re.search(
        r"youtube\.com/channel/([\w\-]+)",
        text,
        re.IGNORECASE
    )

    if match:
        return ("channel_id", match.group(1))

    match = re.search(
        r"youtube\.com/@([\w\-.]+)",
        text,
        re.IGNORECASE
    )

    if match:
        return ("handle", "@" + match.group(1))

    match = re.search(
        r"[?&]list=([\w\-]+)",
        text,
        re.IGNORECASE
    )

    if match:
        return ("playlist_id", match.group(1))

    match = re.search(
        r"youtube\.com/(?:c|user)/([\w\-.]+)",
        text,
        re.IGNORECASE
    )

    if match:
        return ("legacy_name", match.group(1))

    return (None, None)


# ============================================================
# BLOCK CHECK (NetFree)
# ============================================================
# מחזיר True = פתוח, False = חסום, None = לא הצלחנו לקבל תשובה
# ברורה (השירות למטה / timeout / פורמט לא מוכר).

def _block_check_request(identifier, _is_retry=False):
    """
    מחזיר "open" / "lock" / "pending", או None אם הבדיקה לא הושלמה
    (שגיאה, timeout, תשובה לא מוכרת). None הוא לא "פתוח" ולא "חסום".
    """

    if not identifier or not BLOCK_CHECK_BASE_URL:
        return None

    check_url = (
        BLOCK_CHECK_BASE_URL.rstrip("/")
        + "/"
        + urllib.parse.quote(
            str(identifier).strip(),
            safe="@"
        )
    )

    status = None
    text = ""

    try:

        req = urllib.request.Request(
            check_url,
            headers={
                "User-Agent": "yt-download-service"
            }
        )

        with urllib.request.urlopen(
            req,
            timeout=BLOCK_CHECK_TIMEOUT
        ) as response:

            status = response.getcode()

            text = response.read().decode(
                "utf-8",
                errors="replace"
            ).strip()

    except urllib.error.HTTPError as e:

        status = e.code

        try:
            text = e.read().decode(
                "utf-8",
                errors="replace"
            ).strip()
        except Exception:
            text = ""

        print(
            "BLOCK CHECK error:",
            {
                "url": check_url,
                "http": status,
                "body": text[:80]
            },
            flush=True
        )

        # חריגה מהמגבלה (30 בקשות ל-10 שניות) - שווה ניסיון נוסף
        if (
            status == 429
            and not _is_retry
            and BLOCK_CHECK_RETRY_DELAY > 0
        ):

            time.sleep(BLOCK_CHECK_RETRY_DELAY)

            return _block_check_request(
                identifier,
                _is_retry=True
            )

        return None

    except Exception as e:

        print(
            "BLOCK CHECK failed:",
            {
                "url": check_url,
                "error": str(e)
            },
            flush=True
        )

        return None

    upper = text.upper()

    print(
        "BLOCK CHECK:",
        {
            "id": identifier,
            "http": status,
            "answer": upper[:40]
        },
        flush=True
    )

    if status != 200 or upper.startswith("ERROR"):
        return None

    if upper == "OPEN":
        return BLOCK_OPEN

    if upper == "LOCK":
        return BLOCK_LOCK

    if upper == "PENDING":
        return BLOCK_PENDING

    return None


def check_video_open(video_id):

    return _block_check_request(video_id)


def check_channel_open(channel_identifier):
    """
    השירות מקבל מזהה ערוץ בצורת UC+22 או @handle בלבד.
    כל דבר אחר (למשל /c/name ישן או פלייליסט) לא נבדק ברמת הערוץ,
    וייבדק סרטון-סרטון.
    """

    if not channel_identifier:
        return None

    ident = str(channel_identifier).strip()

    is_channel_id = bool(
        re.match(r"^UC[\w\-]{22}$", ident)
    )

    is_handle = bool(
        re.match(r"^@[\w\-.]{3,30}$", ident)
    )

    if not (is_channel_id or is_handle):

        print(
            "BLOCK CHECK skipped - unsupported channel identifier:",
            ident,
            flush=True
        )

        return None

    return _block_check_request(ident)


# ============================================================
# DRIVE FOLDERS + LOG FILE
# ============================================================

def sanitize_drive_name(name):

    if not name:
        return "ללא שם"

    clean = re.sub(
        r'[\\/:*?"<>|]',
        "-",
        str(name)
    ).strip()

    return clean[:120] or "ללא שם"


def ensure_drive_folder(folder_name, parent_id=None):
    """
    מחזיר (folder_id, folder_link) לתיקייה בשם הנתון. אם כבר קיימת
    תיקייה כזו תחת אותו הורה - משתמשים בה, כדי שהורדה חוזרת של
    אותו ערוץ תיכנס לאותו מקום.
    """

    service = get_drive_service()

    safe_name = sanitize_drive_name(
        folder_name
    )

    target_parent = (
        parent_id
        or DRIVE_FOLDER_ID
    )

    escaped = safe_name.replace("'", "\\'")

    query_parts = [
        "mimeType = 'application/vnd.google-apps.folder'",
        "trashed = false",
        "name = '{}'".format(escaped)
    ]

    if target_parent:
        query_parts.append(
            "'{}' in parents".format(target_parent)
        )

    try:

        existing = service.files().list(
            q=" and ".join(query_parts),
            fields="files(id, webViewLink)",
            pageSize=1
        ).execute()

        files = existing.get("files", [])

        if files:

            return (
                files[0].get("id"),
                files[0].get("webViewLink")
            )

    except Exception as e:

        # drive.file לא תמיד מאפשר חיפוש - במקרה כזה פשוט ניצור חדשה
        print(
            "Drive folder lookup failed, creating a new one:",
            str(e),
            flush=True
        )

    metadata = {
        "name": safe_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": (
            [target_parent]
            if target_parent
            else []
        )
    }

    created = service.files().create(
        body=metadata,
        fields="id, webViewLink"
    ).execute()

    return (
        created.get("id"),
        created.get("webViewLink")
    )


def share_with_email(file_id, email):

    if not file_id or not email:
        return False

    try:

        service = get_drive_service()

        service.permissions().create(
            fileId=file_id,
            body={
                "type": "user",
                "role": "reader",
                "emailAddress": email
            },
            sendNotificationEmail=False
        ).execute()

        return True

    except Exception as e:

        print(
            "Sharing failed:",
            {
                "fileId": file_id,
                "email": email,
                "error": str(e)
            },
            flush=True
        )

        return False


def write_log_file_to_drive(
    folder_id,
    content,
    existing_file_id=None,
    filename="log.txt"
):
    """
    כותב או מעדכן קובץ טקסט עם סיכום ההורדה בתוך תיקיית הערוץ.
    מחזיר את מזהה הקובץ, כדי שהעדכון הבא ידרוס את אותו קובץ
    ולא ייצור עשרות עותקים.
    """

    tmp_path = None

    try:

        service = get_drive_service()

        fd, tmp_path = tempfile.mkstemp(
            suffix=".txt"
        )

        with os.fdopen(
            fd,
            "w",
            encoding="utf-8"
        ) as f:
            f.write(content)

        media = MediaFileUpload(
            tmp_path,
            mimetype="text/plain",
            resumable=False
        )

        if existing_file_id:

            service.files().update(
                fileId=existing_file_id,
                media_body=media
            ).execute()

            return existing_file_id

        created = service.files().create(
            body={
                "name": filename,
                "parents": (
                    [folder_id]
                    if folder_id
                    else []
                )
            },
            media_body=media,
            fields="id"
        ).execute()

        return created.get("id")

    except Exception as e:

        print(
            "Writing the log file failed:",
            str(e),
            flush=True
        )

        return existing_file_id

    finally:

        if tmp_path and os.path.exists(tmp_path):

            try:
                os.remove(tmp_path)
            except OSError:
                pass


# ============================================================
# CHANNEL EXPANSION
# ============================================================
# סריקה "שטוחה" - מביאה רק את רשימת המזהים והכותרות, בלי להוריד
# כלום. מהירה גם על ערוצים גדולים.

def expand_channel(url, scan_limit=None):

    limit = (
        scan_limit
        or CHANNEL_SCAN_LIMIT
    )

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
        "ignoreerrors": False,
        "playlistend": limit
    }

    candidates = channel_listing_candidates(url)

    info = None

    listing_url = candidates[0] if candidates else url

    last_error = None

    tried = set()

    for candidate in candidates:

        if candidate in tried:
            continue

        tried.add(candidate)

        try:

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:

                candidate_info = ydl.extract_info(
                    candidate,
                    download=False
                )

        except Exception as e:

            last_error = str(e)

            print(
                "Channel listing attempt failed:",
                {
                    "url": candidate,
                    "error": last_error[:200]
                },
                flush=True
            )

            continue

        if candidate_info and (
            candidate_info.get("entries")
        ):

            info = candidate_info
            listing_url = candidate

            break

        last_error = "הכתובת לא החזירה סרטונים"

    if not info:

        message = last_error or ""

        if (
            "404" in message
            or "not found" in message.lower()
            or "does not exist" in message.lower()
        ):

            raise RuntimeError(
                "הערוץ לא נמצא. יש לוודא שכתובת הערוץ נכונה."
            )

        raise RuntimeError(
            "לא נמצאו סרטונים בערוץ. "
            "ייתכן שהוא פרטי, ריק, או שהתוכן שלו אינו זמין. "
            + message[:200]
        )

    entries = info.get("entries") or []

    videos = []

    for entry in entries:

        if not entry:
            continue

        # ערוץ יכול להחזיר "פלייליסט של פלייליסטים" - משטחים שכבה
        if entry.get("_type") == "playlist":

            for sub in (entry.get("entries") or []):

                if sub and sub.get("id"):

                    videos.append({
                        "id": sub.get("id"),
                        "title": sub.get("title") or sub.get("id"),
                        "duration": sub.get("duration")
                    })

            continue

        video_id = entry.get("id")

        if not video_id:
            continue

        videos.append({
            "id": video_id,
            "title": entry.get("title") or video_id,
            "duration": entry.get("duration")
        })

    is_playlist = "list=" in listing_url.lower()

    if is_playlist:

        # פלייליסט - התיקייה תיקרא על שם הפלייליסט עצמו
        channel_name = (
            info.get("title")
            or info.get("channel")
            or "פלייליסט"
        )

    else:

        channel_name = (
            info.get("channel")
            or info.get("uploader")
            or info.get("title")
            or "ערוץ"
        )

    # yt-dlp מחזיר לפעמים "by <שם>" - מנקים
    channel_name = re.sub(
        r"^by\s+",
        "",
        str(channel_name).strip(),
        flags=re.IGNORECASE
    )

    # yt-dlp מוסיף " - Videos" לשם כשמבקשים טאב מסוים
    channel_name = re.sub(
        r"\s*[-–]\s*(Videos|Shorts|Live)$",
        "",
        str(channel_name)
    ).strip()

    return {
        "channel": channel_name,
        "channel_id": info.get("channel_id") or info.get("id"),
        "channel_url": info.get("channel_url") or listing_url,
        "videos": videos
    }


# ============================================================
# JOB STORE
# ============================================================
# עבודות ערוץ נשמרות בזיכרון וגם כקובץ JSON בדיסק, כדי שסטטוס
# ישרוד קריסה של thread. הן לא שורדות redeploy של הקונטיינר -
# ולכן הלקוח שומר אצלו את רשימת המזהים שכבר ירדו.

JOBS = {}

JOBS_LOCK = threading.Lock()

JOB_QUEUE = queue.Queue()


def _job_path(job_id):

    return os.path.join(
        JOBS_DIR,
        "{}.json".format(job_id)
    )


def save_job(job):

    job["updated_at"] = time.time()

    try:

        os.makedirs(
            JOBS_DIR,
            exist_ok=True
        )

        with open(
            _job_path(job["id"]),
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                job,
                f,
                ensure_ascii=False
            )

    except Exception as e:

        print(
            "Saving the job to disk failed:",
            str(e),
            flush=True
        )


def get_job(job_id):

    with JOBS_LOCK:

        job = JOBS.get(job_id)

        if job:

            try:

                # עותק עמוק - ה-worker ממשיך לכתוב לאובייקט המקורי
                return json.loads(
                    json.dumps(job)
                )

            except Exception:

                # נתפס באמצע כתיבה - ניפול לגרסה שבדיסק
                pass

    # לא בזיכרון - אולי נשאר בדיסק
    try:

        with open(
            _job_path(job_id),
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return None


def update_job(job_id, **fields):

    with JOBS_LOCK:

        job = JOBS.get(job_id)

        if not job:
            return None

        job.update(fields)

    save_job(job)

    return job


# ============================================================
# LOG FILE CONTENT
# ============================================================

STATUS_LABELS = {
    "pending": "⏳ ממתין",
    "running": "⬇️ בהורדה",
    "ok": "✅ ירד",
    "failed": "❌ נכשל",
    "blocked": "⛔ חסום",
    "pending_netfree": "⏳ טרם נבדק בנטפרי",
    "unchecked": "⚠️ הבדיקה לא הושלמה",
    "skipped": "⏭️ דולג"
}


def build_season_log_text(job):
    """
    לוג לעבודת עונה: שורה לכל פרק - מספר, מה קרה, ולמי שירד -
    הקישור לדרייב. מועלה לתיקיית העונה ומתעדכן אחרי כל פרק.
    """

    lines = []

    lines.append("לוג הורדת עונה")
    lines.append("=" * 40)

    lines.append(
        "סדרה: {}".format(job.get("series") or "-")
    )

    lines.append(
        "עונה: {}".format(job.get("season") or "-")
    )

    lines.append(
        "כתובת: {}".format(job.get("url") or "-")
    )

    lines.append(
        "פורמט: {}".format(
            "וידאו"
            if job.get("format") == "video"
            else "אודיו"
        )
    )

    lines.append(
        "מזהה עבודה: {}".format(job.get("id"))
    )

    lines.append(
        "התחיל בתאריך: {}".format(
            time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(
                    job.get("created_at") or time.time()
                )
            )
        )
    )

    lines.append(
        "עודכן לאחרונה: {}".format(
            time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime()
            )
        )
    )

    lines.append("")

    for item in job.get("items") or []:

        status = item.get("status")

        label = STATUS_LABELS.get(status, status or "ממתין")

        line = "פרק {}: {}".format(item.get("id"), label)

        if item.get("reason"):
            line += " - " + item["reason"]

        if item.get("driveLink"):
            line += " | " + item["driveLink"]

        lines.append(line)

    lines.append("")

    lines.append(
        "סיכום: ✅ {} ירדו | ❌ {} נכשלו | "
        "סה\"כ בתור: {}".format(
            job.get("done_count", 0),
            job.get("failed_count", 0),
            job.get("total", 0)
        )
    )

    return "\n".join(lines)


def build_log_text(job):

    if job.get("kind") == "season":
        return build_season_log_text(job)

    lines = []

    lines.append(
        "לוג הורדת ערוץ"
    )

    lines.append(
        "=" * 40
    )

    lines.append(
        "ערוץ: {}".format(
            job.get("channel") or "-"
        )
    )

    lines.append(
        "כתובת: {}".format(
            job.get("channel_url") or job.get("url") or "-"
        )
    )

    lines.append(
        "פורמט: {}".format(
            "וידאו"
            if job.get("format") == "video"
            else "אודיו"
        )
    )

    lines.append(
        "מזהה עבודה: {}".format(
            job.get("id")
        )
    )

    lines.append(
        "התחיל בתאריך: {}".format(
            time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(
                    job.get("created_at") or time.time()
                )
            )
        )
    )

    lines.append(
        "עודכן לאחרונה: {}".format(
            time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime()
            )
        )
    )

    channel_open = job.get("channel_open")

    if job.get("netfree"):

        if channel_open == BLOCK_OPEN:

            lines.append(
                "בדיקת חסימה: הערוץ פתוח - "
                "לא נבדק כל סרטון בנפרד"
            )

        elif channel_open == BLOCK_LOCK:

            lines.append(
                "בדיקת חסימה: הערוץ חסום - "
                "כל סרטון נבדק בנפרד"
            )

        elif channel_open == BLOCK_PENDING:

            lines.append(
                "בדיקת חסימה: הערוץ עדיין לא נבדק - "
                "כל סרטון נבדק בנפרד"
            )

        else:

            lines.append(
                "בדיקת חסימה: לא התקבלה תשובה על הערוץ - "
                "כל סרטון נבדק בנפרד"
            )

    else:

        lines.append(
            "בדיקת חסימה: לא נדרשה"
        )

    lines.append("")

    lines.append(
        "סיכום: ✅ {} ירדו | ❌ {} נכשלו | "
        "⛔ {} נחסמו | סה\"כ בתור: {}".format(
            job.get("done_count", 0),
            job.get("failed_count", 0),
            job.get("blocked_count", 0),
            job.get("total", 0)
        )
    )

    lines.append("")

    lines.append(
        "-" * 40
    )

    for index, item in enumerate(
        job.get("items") or [],
        start=1
    ):

        label = STATUS_LABELS.get(
            item.get("status"),
            item.get("status")
        )

        line = "{}. [{}] {} | {}".format(
            index,
            item.get("id"),
            label,
            item.get("title") or "(ללא שם)"
        )

        if item.get("reason"):

            line += " | סיבה: {}".format(
                item.get("reason")
            )

        if item.get("driveLink"):

            line += " | {}".format(
                item.get("driveLink")
            )

        else:

            # סרטון שלא ירד - הקישור אליו, כדי שאפשר יהיה
            # לבדוק אותו ידנית
            line += " | https://www.youtube.com/watch?v={}".format(
                item.get("id")
            )

        lines.append(line)

    lines.append("")

    lines.append(
        "-" * 40
    )

    lines.append(
        "מזהים שירדו בהצלחה (להעתקה / שמירה אצל הלקוח):"
    )

    lines.append(
        ",".join(
            job.get("downloaded_ids") or []
        )
        or "(אין)"
    )

    return "\n".join(lines)


def flush_log(job):
    """
    כותב את הלוג העדכני לתוך תיקיית הערוץ בדרייב.
    """

    if not job.get("folder_id"):
        return

    log_file_id = write_log_file_to_drive(
        job["folder_id"],
        build_log_text(job),
        existing_file_id=job.get("log_file_id")
    )

    if log_file_id:
        job["log_file_id"] = log_file_id


# ============================================================
# CHANNEL JOB WORKER
# ============================================================
# מוריד סרטון אחד בכל רגע: הורדה -> העלאה לדרייב -> מחיקה מיידית
# מהדיסק המקומי. כך השרת אף פעם לא מחזיק יותר מקובץ אחד.

MAX_CONSECUTIVE_FAILURES = int(
    os.environ.get(
        "MAX_CONSECUTIVE_FAILURES",
        "5"
    )
)

# תקרת פרקים לעבודת עונה בודדת - הגנה מפני מיפוי תקול
# שמנפח עשרות פרקים לעבודה אחת.
MAX_EPISODES_PER_JOB = int(
    os.environ.get(
        "MAX_EPISODES_PER_JOB",
        "50"
    )
)


def run_channel_job(job_id):

    job = None

    with JOBS_LOCK:
        job = JOBS.get(job_id)

    if not job:
        return

    if job.get("cancel_requested"):

        job["status"] = "cancelled"
        job["finished_at"] = time.time()

        for item in job.get("items") or []:

            if item.get("status") in ("pending", None):

                item["status"] = "skipped"
                item["reason"] = "העבודה בוטלה לפני שהתחילה"

        save_job(job)

        return

    job["status"] = "running"
    job["started_at"] = time.time()

    save_job(job)

    consecutive_failures = 0

    try:

        # ------------------------------------------------
        # תיקיית הערוץ בדרייב + לוג ראשוני
        # ------------------------------------------------

        folder_id, folder_link = ensure_drive_folder(
            job.get("channel")
        )

        job["folder_id"] = folder_id
        job["folder_link"] = folder_link

        save_job(job)

        # פרטיות: אין שיתוף של התיקייה עצמה. כל קובץ שיורד משותף
        # בנפרד למייל של המבקש (ראה share_with_email למטה) - כך
        # המבקש רואה רק את הקבצים שלו ולא את שאר התיקיה.

        flush_log(job)

        save_job(job)

        # ------------------------------------------------
        # מעבר על הסרטונים
        # ------------------------------------------------

        for item in job["items"]:

            if job.get("cancel_requested"):

                item["status"] = "skipped"
                item["reason"] = "העבודה בוטלה"

                continue

            if item.get("status") not in (
                "pending",
                None
            ):
                continue

            video_id = item["id"]

            item["status"] = "running"

            job["current"] = video_id

            save_job(job)

            # ---- בדיקת חסימה לסרטון בודד ----
            # רק אם הערוץ עצמו לא נמצא פתוח

            if (
                job.get("netfree")
                and job.get("channel_open") != BLOCK_OPEN
            ):

                answer = check_video_open(
                    video_id
                )

                if answer != BLOCK_OPEN:

                    if answer == BLOCK_LOCK:

                        item["status"] = "blocked"

                        item["reason"] = (
                            "הסרטון חסום בנטפרי"
                        )

                    elif answer == BLOCK_PENDING:

                        item["status"] = "pending_netfree"

                        item["reason"] = (
                            "הסרטון עדיין לא נבדק בנטפרי "
                            "(ולכן חסום בפועל)"
                        )

                    else:

                        item["status"] = "unchecked"

                        item["reason"] = (
                            "בדיקת החסימה לא הושלמה - "
                            "השירות לא החזיר תשובה"
                        )

                    job["blocked_count"] = (
                        job.get("blocked_count", 0) + 1
                    )

                    flush_log(job)
                    save_job(job)

                    continue

            # ---- הורדה + העלאה ----

            video_url = (
                "https://www.youtube.com/watch?v="
                + video_id
            )

            try:

                with tempfile.TemporaryDirectory() as tmp_dir:

                    local_path, title = download_video(
                        url=video_url,
                        fmt=job.get("format") or "audio",
                        tmp_dir=tmp_dir,
                        player_clients=job.get("player_clients"),
                        use_cookies=job.get("use_cookies", True),
                        use_proxy=job.get("use_proxy", False)
                    )

                    drive_link, file_id = upload_to_drive(
                        local_path,
                        os.path.basename(local_path),
                        parent_id=job.get("folder_id")
                    )

                # ה-TemporaryDirectory כבר נמחק כאן, כולל הקובץ

                item["status"] = "ok"
                item["title"] = title or item.get("title")
                item["driveLink"] = drive_link
                item["fileId"] = file_id

                # פרטיות: הקובץ הספציפי משותף למייל המבקש בלבד -
                # במקום שיתוף תיקיית הערוץ/העונה שחשפה את כל התוכן.
                # כישלון שיתוף לא מכשיל את הפריט - רק נרשם.
                if job.get("email") and file_id:

                    if not share_with_email(file_id, job["email"]):

                        item["share_error"] = (
                            "שיתוף הקובץ נכשל"
                        )

                job["done_count"] = (
                    job.get("done_count", 0) + 1
                )

                job.setdefault(
                    "downloaded_ids",
                    []
                ).append(video_id)

                consecutive_failures = 0

            except Exception as e:

                item["status"] = "failed"

                item["reason"] = str(e)[:400]

                job["failed_count"] = (
                    job.get("failed_count", 0) + 1
                )

                consecutive_failures += 1

                print(
                    "Video download failed:",
                    {
                        "job": job_id,
                        "video": video_id,
                        "error": str(e)
                    },
                    flush=True
                )

            flush_log(job)
            save_job(job)

            if (
                consecutive_failures
                >= MAX_CONSECUTIVE_FAILURES
            ):

                job["error"] = (
                    "העבודה נעצרה אחרי {} כשלונות רצופים - "
                    "כנראה חסימה זמנית של יוטיוב".format(
                        consecutive_failures
                    )
                )

                break

            # השהייה קצרה בין סרטונים, נגד חסימת IP
            if DELAY_BETWEEN_VIDEOS > 0:

                time.sleep(
                    DELAY_BETWEEN_VIDEOS
                )

        job["status"] = (
            "cancelled"
            if job.get("cancel_requested")
            else "done"
        )

    except Exception as e:

        traceback.print_exc()

        job["status"] = "error"

        job["error"] = str(e)[:500]

    finally:

        job["current"] = None

        job["finished_at"] = time.time()

        try:
            flush_log(job)
        except Exception:
            pass

        save_job(job)

        print(
            "CHANNEL JOB FINISHED:",
            {
                "job": job_id,
                "status": job.get("status"),
                "ok": job.get("done_count"),
                "failed": job.get("failed_count"),
                "blocked": job.get("blocked_count")
            },
            flush=True
        )


def run_season_job(job_id):
    """
    עובד עונה שלמה של סדרת מאקו: פרק אחד בכל רגע - הורדה,
    העלאה לתיקיית העונה בדרייב, מחיקה מיידית מהדיסק.

    המבנה זהה לעבודת ערוץ בכוונה, כך שגם /job/<id> (התקדמות)
    וגם /job/<id>/cancel (ביטול) עובדים עליו בלי שינוי.
    """

    job = None

    with JOBS_LOCK:
        job = JOBS.get(job_id)

    if not job:
        return

    if job.get("cancel_requested"):

        job["status"] = "cancelled"
        job["finished_at"] = time.time()

        for item in job.get("items") or []:

            if item.get("status") in ("pending", None):

                item["status"] = "skipped"
                item["reason"] = "העבודה בוטלה לפני שהתחילה"

        save_job(job)

        return

    job["status"] = "running"
    job["started_at"] = time.time()

    save_job(job)

    consecutive_failures = 0

    try:

        # ------------------------------------------------
        # תיקיית העונה בדרייב ("slug - עונה N") + לוג ראשוני
        # ------------------------------------------------

        try:

            folder_id, folder_link = ensure_drive_folder(
                "{} - עונה {}".format(
                    job.get("series") or "season",
                    job.get("season")
                )
            )

            job["folder_id"] = folder_id
            job["folder_link"] = folder_link

        except Exception as folder_ex:

            # כישלון תיקייה לא צריך להרוג את העונה: ההעלאות ייפלו
            # לתיקיית ברירת המחדל של דרייב, והלוג פשוט לא ייכתב
            # לתיקייה (הוא מוחזר אם התיקייה תצליח בהמשך).
            job["folder_error"] = str(folder_ex)[:200]

            print(
                "Season folder creation failed, continuing:",
                str(folder_ex)[:150],
                flush=True
            )

        save_job(job)

        # פרטיות: גם כאן - אין שיתוף של תיקיית העונה. הפרקים עצמם
        # משותפים בנפרד למייל המבקש בעת העלאתם.

        flush_log(job)

        save_job(job)

        # ------------------------------------------------
        # מעבר על הפרקים
        # ------------------------------------------------

        for item in job["items"]:

            if job.get("cancel_requested"):

                item["status"] = "skipped"
                item["reason"] = "העבודה בוטלה"

                continue

            if item.get("status") not in (
                "pending",
                None
            ):
                continue

            episode_url = item.get("url")

            if not episode_url:

                item["status"] = "failed"
                item["reason"] = "חסר קישור לפרק"

                job["failed_count"] = (
                    job.get("failed_count", 0) + 1
                )

                flush_log(job)
                save_job(job)

                continue

            item["status"] = "running"

            job["current"] = (
                item.get("title")
                or "פרק " + str(item.get("id"))
            )

            save_job(job)

            try:

                # ------------------------------------------------
                # כאן (kan): עמוד הפרק מומר ל-kaltura: ש-yt-dlp יודע
                # להוריד ממנו בכל האיכויות. הפלטפורמה עוברת מפורשות
                # כדי שההורדה לא תנסה להיפתר שוב כ-news_il.
                # ------------------------------------------------

                media_sources = []
                media_cookies = ""

                if job.get("platform") == "kan":

                    # כאן (kan): כל מקורות ההזרמה מעמוד הפרק -
                    # כתובת kaltura: ל-yt-dlp, וגם m3u8 ישירים מהעמוד
                    # כגיבוי, כי Kaltura חוסמת כרגע את השותף של כאן
                    # עבור yt-dlp.
                    media_sources = kan_episode_stream_candidates(
                        episode_url
                    )

                else:

                    # עמוד VOD של מאקו חייב להיפתר קודם לפלייליסט
                    # מאומת (hdnea) - שליחתו ישירות ל-yt-dlp מקבלת
                    # 403 מהגנת Radware. בקשת /download הרגילה עושה
                    # את הפתרון הזה בדיוק כך, וגם העונה תעשה.
                    _media_url, media_cookies = mako_resolve_vod_stream(
                        episode_url
                    )

                    if _media_url:
                        media_sources = [_media_url]

                if not media_sources:

                    raise RuntimeError(
                        "לא הצלחנו לפתור את קישור הפרק לזרם "
                        "(מאקו חסם את הגישה) - נסו שוב מאוחר"
                    )

                kan_item_error = None

                for media_url in media_sources:

                    try:

                        with tempfile.TemporaryDirectory() as tmp_dir:

                            local_path, title = download_video(
                                url=media_url,
                                fmt=job.get("format") or "video",
                                tmp_dir=tmp_dir,
                                player_clients=job.get("player_clients"),
                                use_cookies=job.get("use_cookies", False),
                                use_proxy=job.get("use_proxy", False),
                                cookies_str=media_cookies,
                                referer=(
                                    "https://www.kan.org.il/"
                                    if job.get("platform") == "kan"
                                    else "https://www.mako.co.il/"
                                ),
                                platform=job.get("platform")
                            )

                            # שם קובץ ייחודי לפרק - בלי זה כל הפרקים
                            # היו עולים באותו שם ודורסים זה את זה.
                            episode_label = (
                                item.get("title")
                                or "פרק " + str(item.get("id"))
                            )

                            upload_name = (
                                "{} - {}.{}".format(
                                    job.get("series") or "season",
                                    episode_label,
                                    os.path.splitext(local_path)[1]
                                    or ".mp4"
                                )
                            )

                            drive_link, file_id = upload_to_drive(
                                local_path,
                                upload_name,
                                parent_id=job.get("folder_id")
                            )

                        break

                    except Exception as media_err:

                        kan_item_error = media_err

                        print(
                            "Episode source attempt failed:",
                            {
                                "source": str(media_url)[:120],
                                "error": str(media_err)[:160]
                            },
                            flush=True,
                        )

                else:

                    raise (
                        kan_item_error
                        or RuntimeError("לא נמצא מקור הזרמה שעובד")
                    )

                item["status"] = "ok"
                item["title"] = title or item.get("title")
                item["driveLink"] = drive_link
                item["fileId"] = file_id

                # פרטיות: הקובץ הספציפי משותף למייל המבקש בלבד -
                # במקום שיתוף תיקיית הערוץ/העונה שחשפה את כל התוכן.
                # כישלון שיתוף לא מכשיל את הפריט - רק נרשם.
                if job.get("email") and file_id:

                    if not share_with_email(file_id, job["email"]):

                        item["share_error"] = (
                            "שיתוף הקובץ נכשל"
                        )

                job["done_count"] = (
                    job.get("done_count", 0) + 1
                )

                job.setdefault(
                    "downloaded_ids",
                    []
                ).append(str(item.get("id")))

                consecutive_failures = 0

            except Exception as e:

                item["status"] = "failed"

                item["reason"] = str(e)[:400]

                job["failed_count"] = (
                    job.get("failed_count", 0) + 1
                )

                consecutive_failures += 1

                print(
                    "Episode download failed:",
                    {
                        "job": job_id,
                        "episode": item.get("id"),
                        "error": str(e)[:200]
                    },
                    flush=True
                )

            flush_log(job)
            save_job(job)

            if (
                consecutive_failures
                >= MAX_CONSECUTIVE_FAILURES
            ):

                job["error"] = (
                    "העבודה נעצרה אחרי {} כשלונות רצופים. "
                    "הפרקים שכבר ירדו נשמרו בדרייב - אפשר "
                    "להריץ שוב עם skip_episodes כדי להמשיך "
                    "מהנקודה שבה נעצר.".format(
                        consecutive_failures
                    )
                )

                break

            # השהייה קצרה בין פרקים, נגד חסימת IP
            if DELAY_BETWEEN_VIDEOS > 0:

                time.sleep(
                    DELAY_BETWEEN_VIDEOS
                )

        job["status"] = (
            "cancelled"
            if job.get("cancel_requested")
            else "done"
        )

    except Exception as e:

        traceback.print_exc()

        job["status"] = "error"

        job["error"] = str(e)[:500]

    finally:

        job["current"] = None

        job["finished_at"] = time.time()

        try:
            flush_log(job)
        except Exception:
            pass

        save_job(job)

        print(
            "SEASON JOB FINISHED:",
            {
                "job": job_id,
                "status": job.get("status"),
                "ok": job.get("done_count"),
                "failed": job.get("failed_count")
            },
            flush=True
        )


def _worker_loop():

    while True:

        job_id = JOB_QUEUE.get()

        try:

            job_kind = None

            peek = get_job(job_id)

            if peek:
                job_kind = peek.get("kind")

            if job_kind == "season":
                run_season_job(job_id)
            else:
                run_channel_job(job_id)

        except Exception:

            traceback.print_exc()

        finally:

            JOB_QUEUE.task_done()


def cleanup_stale_jobs(max_age_days=7):
    """
    עבודות חיות בזיכרון התהליך. אחרי redeploy או קריסה נשארים
    בדיסק קבצים של עבודות שמסומנות "רצות" ואף אחד לא ימשיך
    אותן - מסמנים אותן ככשלון, כדי שהלקוח יקבל תשובה ברורה
    במקום להמתין לנצח. בדרך גם מוחקים קבצים ישנים.
    """

    if not os.path.isdir(JOBS_DIR):
        return

    now = time.time()

    max_age = max_age_days * 24 * 60 * 60

    for filename in os.listdir(JOBS_DIR):

        if not filename.endswith(".json"):
            continue

        full_path = os.path.join(JOBS_DIR, filename)

        try:

            if (now - os.path.getmtime(full_path)) > max_age:

                os.remove(full_path)

                continue

            with open(
                full_path,
                "r",
                encoding="utf-8"
            ) as f:

                job = json.load(f)

            if job.get("status") not in ("queued", "running"):
                continue

            job["status"] = "error"

            job["error"] = (
                "העבודה נקטעה כשהשרת עלה מחדש. "
                "הקבצים שכבר עלו לדרייב נשמרו - "
                "אפשר לשלוח את אותו ערוץ שוב והמערכת "
                "תמשיך מהנקודה שבה נעצרה."
            )

            job["current"] = None

            with open(
                full_path,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    job,
                    f,
                    ensure_ascii=False
                )

            print(
                "Marked a stale job as interrupted:",
                job.get("id"),
                flush=True
            )

        except Exception as e:

            print(
                "Cleaning a job file failed:",
                {
                    "file": filename,
                    "error": str(e)
                },
                flush=True
            )


cleanup_stale_jobs()


for _ in range(max(1, MAX_CONCURRENT_JOBS)):

    threading.Thread(
        target=_worker_loop,
        daemon=True
    ).start()


# ============================================================
# CHANNEL PLAN (expansion + filtering)
# ============================================================

def build_channel_plan(
    url,
    skip_ids=None,
    max_videos=None,
    newest_first=True
):
    """
    מרחיב את הערוץ, מסנן את מה שכבר ירד אצל הלקוח, ומחזיר
    את רשימת הסרטונים שיירדו בפועל (עד התקרה).
    """

    limit = MAX_VIDEOS_PER_JOB

    if max_videos:

        try:
            limit = min(
                int(max_videos),
                MAX_VIDEOS_PER_JOB
            )
        except (TypeError, ValueError):
            limit = MAX_VIDEOS_PER_JOB

    limit = max(1, limit)

    skip_set = set()

    for raw_id in (skip_ids or []):

        if raw_id:
            skip_set.add(
                str(raw_id).strip()
            )

    # חלון הסריקה חייב לגדול יחד עם מה שכבר ירד, אחרת אחרי
    # CHANNEL_SCAN_LIMIT סרטונים נקבל "אין חדשים" למרות שיש עוד
    scan_limit = min(
        MAX_CHANNEL_SCAN_LIMIT,
        max(
            CHANNEL_SCAN_LIMIT,
            len(skip_set) + limit * 3
        )
    )

    expanded = expand_channel(
        url,
        scan_limit=scan_limit
    )

    all_videos = expanded["videos"]

    if not newest_first:
        all_videos = list(
            reversed(all_videos)
        )

    remaining = [
        v
        for v in all_videos
        if v["id"] not in skip_set
    ]

    selected = remaining[:limit]

    return {
        "channel": expanded["channel"],
        "channel_id": expanded["channel_id"],
        "channel_url": expanded["channel_url"],
        "scanned": len(all_videos),
        "already_downloaded": len(all_videos) - len(remaining),
        "remaining": len(remaining),
        "selected": selected,
        "limit": limit,
        "scan_limit": scan_limit
    }


# ============================================================
# CHANNEL API
# ============================================================

def _require_api_key():

    provided_key = request.headers.get(
        "X-API-KEY",
        ""
    )

    if (
        not API_KEY
        or provided_key != API_KEY
    ):
        return False

    return True


@app.route(
    "/channel/preview",
    methods=["POST"]
)
def channel_preview():
    """
    מחזיר מה *היה* יורד, בלי להוריד כלום. מיועד לתוסף - להראות
    למשתמש "נמצאו 12 סרטונים חדשים" לפני שהוא מאשר.
    """

    if not _require_api_key():

        return jsonify({
            "success": False,
            "error": "unauthorized"
        }), 401

    data = request.get_json(silent=True) or {}

    # כתובות מהמייל נושאות את סימון המקור - מנטרלים אותו קודם
    url = strip_email_source_marker((data.get("url") or "").strip())

    if not url or not is_channel_url(url):

        return jsonify({
            "success": False,
            "error": "קישור הערוץ אינו תקין"
        }), 400

    try:

        plan = build_channel_plan(
            url,
            skip_ids=data.get("skip_ids"),
            max_videos=data.get("max_videos")
        )

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

    return jsonify({
        "success": True,
        "channel": plan["channel"],
        "channelId": plan["channel_id"],
        "scanned": plan["scanned"],
        "alreadyDownloaded": plan["already_downloaded"],
        "remaining": plan["remaining"],
        "willDownload": len(plan["selected"]),
        "maxPerRequest": MAX_VIDEOS_PER_JOB,
        "videos": plan["selected"]
    })


@app.route(
    "/channel/download",
    methods=["POST"]
)
def channel_download():
    """
    פותח עבודת הורדת ערוץ ומחזיר מיד job_id. ההורדה עצמה רצה
    ברקע - הלקוח בודק התקדמות דרך /job/<id>.
    """

    if not _require_api_key():

        return jsonify({
            "success": False,
            "error": "unauthorized"
        }), 401

    data = request.get_json(silent=True) or {}

    # כתובות מהמייל נושאות את סימון המקור - מנטרלים אותו קודם
    url = strip_email_source_marker((data.get("url") or "").strip())

    fmt = data.get("format", "audio")

    email = (
        (data.get("email") or "")
        .strip()
        .lower()
    )

    if not url or not is_channel_url(url):

        return jsonify({
            "success": False,
            "error": "קישור הערוץ אינו תקין"
        }), 400

    if fmt not in ("audio", "video"):

        return jsonify({
            "success": False,
            "error": "format must be 'audio' or 'video'"
        }), 400

    netfree = bool(
        data.get("netfree", False)
    )

    # ------------------------------------------------
    # הרחבת הערוץ וסינון מה שכבר ירד אצל הלקוח.
    # קודם ההרחבה - היא מחזירה את מזהה הערוץ האמיתי
    # (UC...) שנדרש לבדיקת החסימה.
    # ------------------------------------------------

    try:

        plan = build_channel_plan(
            url,
            skip_ids=data.get("skip_ids"),
            max_videos=data.get("max_videos")
        )

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

    # ------------------------------------------------
    # בדיקת חסימה ברמת הערוץ. אם הערוץ פתוח - לא נבדוק
    # כל סרטון בנפרד. בכל מצב אחר - כל סרטון ייבדק לחוד.
    #
    # פלייליסט לא נבדק ברמת האוסף: הסרטונים בו יכולים
    # להגיע מכמה ערוצים, ולכן כל אחד נבדק לחוד.
    # ------------------------------------------------

    channel_open = None

    if netfree:

        id_type, url_identifier = extract_channel_identifier(url)

        if id_type == "playlist_id":

            identifier = None

        else:

            # מזהה הערוץ מ-yt-dlp הוא הבטוח ביותר - הוא תמיד
            # בצורת UC+22, גם כשהכתובת היא /c/name ישן
            identifier = (
                plan.get("channel_id")
                or url_identifier
            )

        if identifier:

            channel_open = check_channel_open(
                identifier
            )

        print(
            "CHANNEL BLOCK CHECK:",
            {
                "type": id_type,
                "identifier": identifier,
                "answer": channel_open
            },
            flush=True
        )

    if not plan["selected"]:

        return jsonify({
            "success": True,
            "nothingNew": True,
            "channel": plan["channel"],
            "scanned": plan["scanned"],
            "alreadyDownloaded": plan["already_downloaded"],
            "message": "לא נמצאו סרטונים חדשים בערוץ"
        })

    job_id = uuid.uuid4().hex[:12]

    job = {
        "id": job_id,
        "status": "queued",
        "created_at": time.time(),
        "updated_at": time.time(),

        "url": url,
        "channel": plan["channel"],
        "channel_id": plan["channel_id"],
        "channel_url": plan["channel_url"],

        "email": email,
        "format": fmt,
        "netfree": netfree,
        "channel_open": channel_open,

        "player_clients": data.get("player_client"),
        "use_cookies": data.get("use_cookies", True),
        "use_proxy": data.get("use_proxy", False),

        "total": len(plan["selected"]),
        "done_count": 0,
        "failed_count": 0,
        "blocked_count": 0,
        "downloaded_ids": [],

        "scanned": plan["scanned"],
        "already_downloaded": plan["already_downloaded"],
        "remaining_after": max(
            0,
            plan["remaining"] - len(plan["selected"])
        ),

        "items": [
            {
                "id": v["id"],
                "title": v.get("title"),
                "status": "pending",
                "reason": None,
                "driveLink": None,
                "fileId": None
            }
            for v in plan["selected"]
        ]
    }

    with JOBS_LOCK:
        JOBS[job_id] = job

    save_job(job)

    JOB_QUEUE.put(job_id)

    return jsonify({
        "success": True,
        "jobId": job_id,
        "channel": plan["channel"],
        "total": job["total"],
        "scanned": plan["scanned"],
        "alreadyDownloaded": plan["already_downloaded"],
        "remainingAfter": job["remaining_after"],
        "channelOpen": channel_open,
        "queuePosition": JOB_QUEUE.qsize(),
        "videos": [
            {
                "id": i["id"],
                "title": i["title"]
            }
            for i in job["items"]
        ]
    })


@app.route(
    "/job/<job_id>",
    methods=["GET"]
)
def job_status(job_id):

    if not _require_api_key():

        return jsonify({
            "success": False,
            "error": "unauthorized"
        }), 401

    job = get_job(job_id)

    if not job:

        return jsonify({
            "success": False,
            "error": "העבודה לא נמצאה"
        }), 404

    include_items = (
        request.args.get(
            "items",
            "1"
        ) != "0"
    )

    payload = {
        "success": True,
        "jobId": job.get("id"),
        "status": job.get("status"),
        "channel": job.get("channel"),
        "format": job.get("format"),
        "total": job.get("total", 0),
        "done": job.get("done_count", 0),
        "failed": job.get("failed_count", 0),
        "blocked": job.get("blocked_count", 0),
        "current": job.get("current"),
        "folderLink": job.get("folder_link"),
        "downloadedIds": job.get("downloaded_ids") or [],
        "remainingAfter": job.get("remaining_after", 0),
        "error": job.get("error")
    }

    if job.get("kind") == "season":

        payload["kind"] = "season"
        payload["series"] = job.get("series")
        payload["season"] = job.get("season")

    processed = (
        payload["done"]
        + payload["failed"]
        + payload["blocked"]
    )

    payload["processed"] = processed

    payload["percent"] = (
        int(
            processed * 100 / payload["total"]
        )
        if payload["total"]
        else 0
    )

    if include_items:

        payload["items"] = job.get("items") or []

    return jsonify(payload)


@app.route(
    "/job/<job_id>/cancel",
    methods=["POST"]
)
def job_cancel(job_id):

    if not _require_api_key():

        return jsonify({
            "success": False,
            "error": "unauthorized"
        }), 401

    updated = update_job(
        job_id,
        cancel_requested=True
    )

    if not updated:

        return jsonify({
            "success": False,
            "error": "העבודה לא נמצאה או שכבר הסתיימה"
        }), 404

    return jsonify({
        "success": True,
        "jobId": job_id,
        "message": "בקשת הביטול נרשמה. "
                   "הסרטון הנוכחי יסתיים ואז העבודה תיעצר."
    })




# ============================================================
# DIRECT DOWNLOAD API
# ============================================================
# עוקף את הטופס ואת הגיליון לגמרי: מוריד, מחזיר את הקובץ עצמו
# בגוף התשובה, ומוחק אותו מיד. שום דבר לא נשאר בדרייב ושום דבר
# לא נרשם בגיליון.
#
# כל מה שה-Apps Script מספק הוא מדיניות - מכסות, בדיקת נטפרי,
# מיילים ורישום. הורדה דרך כאן היא לכן לא מסוננת ובלי מכסה
# יומית, ולכן היא מוגנת בטוקן נפרד ובמגבלות משלה.

# טוקן נפרד מ-API_KEY, כדי שאפשר יהיה לבטל אותו בלי לגעת
# בטופס ובתוסף. כל עוד הוא לא מוגדר - נקודת הקצה מכובה.
DIRECT_API_KEY = os.environ.get(
    "DIRECT_API_KEY",
    ""
)

# כמה הורדות ישירות במקביל. הקובץ יושב על הדיסק עד שהתשובה
# נשלחת, ולכן מקביליות גבוהה ממלאת את הדיסק של הקונטיינר.
DIRECT_MAX_CONCURRENT = int(
    os.environ.get(
        "DIRECT_MAX_CONCURRENT",
        "2"
    )
)

# תקרת בקשות לשעה. לא כדי לחסוך משאבים אלא כדי להגן על כתובת
# ה-IP: רצף בקשות מהיר גורם ליוטיוב לחסום את השרת, וזה משבית
# גם את הטופס וגם את התוסף.
DIRECT_HOURLY_LIMIT = int(
    os.environ.get(
        "DIRECT_HOURLY_LIMIT",
        "30"
    )
)

_direct_slots = threading.Semaphore(
    max(1, DIRECT_MAX_CONCURRENT)
)

_direct_history = []

_direct_history_lock = threading.Lock()


def _direct_rate_ok():
    """
    מחזיר (מותר, כמה נשארו, בעוד כמה שניות ישתחרר מקום).
    חלון מתגלגל של שעה.
    """

    now = time.time()

    with _direct_history_lock:

        while _direct_history and (now - _direct_history[0]) > 3600:
            _direct_history.pop(0)

        used = len(_direct_history)

        if used >= DIRECT_HOURLY_LIMIT:

            # הבקשה הישנה ביותר תצא מהחלון בעוד כך וכך שניות,
            # ואז יתפנה מקום אחד
            wait = int(
                3600 - (now - _direct_history[0])
            ) + 1

            return (False, 0, max(1, wait))

        _direct_history.append(now)

        return (True, DIRECT_HOURLY_LIMIT - used - 1, 0)


def _retry_response(message, seconds, reason, status):
    """
    תשובה אחידה לכל מצב שבו כדאי פשוט לחכות ולנסות שוב.
    הלקוח יכול להסתמך על retryAfter בלי לפענח טקסט.
    """

    body = jsonify({
        "success": False,
        "error": message,
        "retryable": True,
        "retryAfter": seconds,
        "reason": reason
    })

    response = make_response(body, status)

    response.headers["Retry-After"] = str(seconds)

    return response


def _looks_temporary(error_text):
    """
    האם כישלון ההורדה נראה זמני - חסימה מצד יוטיוב, עומס או
    תקלת רשת - להבדיל מסרטון שפשוט לא קיים.
    """

    text = (error_text or "").lower()

    temporary_signs = [
        "sign in to confirm",
        "not a bot",
        "too many requests",
        "429",
        "rate",
        "timed out",
        "timeout",
        "temporarily",
        "connection",
        "throttl",
        "503",
        "502"
    ]

    return any(
        sign in text
        for sign in temporary_signs
    )


def _ascii_header(value):
    """
    כותרות HTTP חייבות להיות ASCII. שם בעברית עובר קידוד אחוזים.
    """

    return urllib.parse.quote(
        str(value or ""),
        safe=""
    )


@app.route(
    "/direct",
    methods=["POST"]
)
def direct_download():

    # ---------- טוקן ----------

    if not DIRECT_API_KEY:

        return jsonify({
            "success": False,
            "error": "ה-API הישיר אינו מופעל. "
                     "יש להגדיר DIRECT_API_KEY במשתני הסביבה."
        }), 503

    provided = request.headers.get(
        "X-DIRECT-KEY",
        ""
    )

    if provided != DIRECT_API_KEY:

        return jsonify({
            "success": False,
            "error": "unauthorized"
        }), 401

    data = request.get_json(silent=True) or {}

    # כתובות מהמייל נושאות את סימון המקור - מנטרלים אותו קודם
    url = strip_email_source_marker((data.get("url") or "").strip())

    fmt = data.get("format", "audio")

    if not url:

        return jsonify({
            "success": False,
            "error": "missing 'url'"
        }), 400

    if fmt not in ("audio", "video"):

        return jsonify({
            "success": False,
            "error": "format must be 'audio' or 'video'"
        }), 400

    # ערוץ שלם לא יכול לחזור כקובץ אחד
    if is_channel_url(url):

        return jsonify({
            "success": False,
            "error": "כתובת של ערוץ אינה נתמכת כאן - "
                     "יש להשתמש ב-/channel/download"
        }), 400

    if not is_valid_video_url(url):

        return jsonify({
            "success": False,
            "error": "קישור לא נתמך"
        }), 400

    # ---------- מגבלת קצב ----------

    allowed, remaining, wait_seconds = _direct_rate_ok()

    if not allowed:

        return _retry_response(
            "הגעת לתקרה של {} הורדות ישירות בשעה. "
            "מקום יתפנה בעוד {} דקות.".format(
                DIRECT_HOURLY_LIMIT,
                max(1, wait_seconds // 60)
            ),
            wait_seconds,
            "hourly_limit",
            429
        )

    # ---------- מקום פנוי ----------

    if not _direct_slots.acquire(blocking=False):

        # התפנות תלויה בסיום הורדה אחרת, ואי אפשר לדעת מתי בדיוק
        return _retry_response(
            "כרגע רצות {} הורדות במקביל, וזו התקרה. "
            "יש לנסות שוב בעוד כחצי דקה.".format(
                DIRECT_MAX_CONCURRENT
            ),
            30,
            "busy",
            503
        )

    tmp_dir = None

    slot_released = False

    def release_slot():

        nonlocal slot_released

        if not slot_released:
            slot_released = True
            _direct_slots.release()

    try:

        print(
            "DIRECT DOWNLOAD:",
            {
                "platform": detect_platform(url),
                "format": fmt,
                "remaining_this_hour": remaining
            },
            flush=True
        )

        tmp_dir = tempfile.mkdtemp(
            prefix="direct_"
        )

        local_path, title = download_video(
            url=url,
            fmt=fmt,
            tmp_dir=tmp_dir,
            player_clients=data.get("player_client"),
            use_cookies=data.get("use_cookies", True),
            use_proxy=data.get("use_proxy", False)
        )

        filename = os.path.basename(local_path)

        size = os.path.getsize(local_path)

        mime = (
            mimetypes.guess_type(filename)[0]
            or "application/octet-stream"
        )

        sent_dir = tmp_dir

        # הזרמה בנתחים, וניקוי ב-finally של הגנרטור. כך הקובץ
        # נמחק גם כשההעברה מסתיימת וגם כשהלקוח מתנתק באמצע,
        # ובלי להחזיק את כל הקובץ בזיכרון.
        def stream_and_cleanup():

            try:

                with open(local_path, "rb") as f:

                    while True:

                        chunk = f.read(64 * 1024)

                        if not chunk:
                            break

                        yield chunk

            finally:

                release_slot()

                shutil.rmtree(
                    sent_dir,
                    ignore_errors=True
                )

                print(
                    "DIRECT DOWNLOAD finished, disk cleaned:",
                    filename,
                    flush=True
                )

        response = Response(
            stream_with_context(
                stream_and_cleanup()
            ),
            mimetype=mime
        )

        # שם קובץ בעברית: גרסת ASCII לתאימות, ולצידה
        # השם האמיתי בקידוד RFC 5987
        ascii_name = re.sub(
            r"[^A-Za-z0-9._-]",
            "_",
            filename
        ) or "download"

        response.headers["Content-Disposition"] = (
            "attachment; filename=\"{}\"; filename*=UTF-8''{}".format(
                ascii_name,
                _ascii_header(filename)
            )
        )

        response.headers["Content-Length"] = str(size)

        response.headers["X-Video-Title"] = _ascii_header(title)

        response.headers["X-File-Size"] = str(size)

        response.headers["X-Remaining-This-Hour"] = str(remaining)

        # הניקוי עבר לאחריות הגנרטור
        tmp_dir = None

        return response

    except Exception as e:

        traceback.print_exc()

        message = str(e)

        # כישלון זמני מקבל המלצת המתנה, כישלון קבוע לא - אין טעם
        # לגרום ללקוח לנסות שוב סרטון שנמחק
        if _looks_temporary(message):

            return _retry_response(
                "ההורדה נכשלה זמנית, כנראה חסימה מצד יוטיוב. "
                "כדאי לנסות שוב בעוד כ-20 דקות.\n\n" + message[:300],
                1200,
                "upstream_blocked",
                503
            )

        return jsonify({
            "success": False,
            "error": message,
            "retryable": False,
            "reason": "failed"
        }), 500

    finally:

        # רץ רק אם לא הוחזרה תשובה שמזרימה קובץ
        if tmp_dir is not None:

            release_slot()

            shutil.rmtree(
                tmp_dir,
                ignore_errors=True
            )


# ============================================================
# KAN DIAGNOSTIC (temporary, no auth) - pinpoints why kan.org.il
# fetch fails on the deployed server while working from GitHub runners.
# DELETE THIS ENDPOINT once the root cause is identified.
# ============================================================

@app.route("/debug/kan", methods=["GET"])
def debug_kan():

    import ssl

    target = request.args.get(
        "url",
        "https://www.kan.org.il/content/kan/kan-11/p-11843/s8/756427/",
    )

    result = {
        "target": target,
        "time": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "build": "wayback-5",
        "outbound_ip": None,
        "tests": [],
    }

    # איזה IP יוצא כרגע מהשרת?
    try:

        who = requests.get(
            "https://api.ipify.org?format=json",
            timeout=10,
        ).json()

        result["outbound_ip"] = who.get("ip")

    except Exception as who_err:

        result["outbound_ip"] = f"error: {str(who_err)[:80]}"

    # בדיקה 1: requests עם UA של דפדפן - בדיוק כמו kan_page_fetch
    try:

        response = requests.get(
            target,
            headers=KAN_HEADERS,
            timeout=25,
        )

        result["tests"].append({
            "name": "requests+UA",
            "status": response.status_code,
            "size": len(response.text),
            "kaltura_entries": kan_find_kaltura_entries(response.text),
        })

    except Exception as req_err:

        result["tests"].append({
            "name": "requests+UA",
            "error": str(req_err)[:200],
        })

    # בדיקה 2: requests בלי UA - לשלול חסימת User-Agent
    try:

        response = requests.get(
            target,
            timeout=25,
        )

        result["tests"].append({
            "name": "requests-noUA",
            "status": response.status_code,
            "size": len(response.text),
            "kaltura_entries": kan_find_kaltura_entries(response.text),
        })

    except Exception as req_err2:

        result["tests"].append({
            "name": "requests-noUA",
            "error": str(req_err2)[:200],
        })

    # בדיקה 3: urllib (טביעת TLS שונה מ-request) + UA
    try:

        req_obj = urllib.request.Request(target, headers=dict(KAN_HEADERS))

        with urllib.request.urlopen(req_obj, timeout=25) as resp:

            body = resp.read().decode("utf-8", "replace")

        result["tests"].append({
            "name": "urllib+UA",
            "status": resp.status,
            "size": len(body),
            "kaltura_entries": kan_find_kaltura_entries(body),
        })

    except Exception as url_err:

        result["tests"].append({
            "name": "urllib+UA",
            "error": str(url_err)[:200],
        })

    # בדיקה 4: curl דרך subprocess - מחוץ לפייתון לגמרי
    try:

        curl_run = subprocess.run(
            ["curl", "-s", "-o", "-", "-w", "%{http_code}|%{size_download}",
             "--max-time", "25", "-A", KAN_HEADERS.get("User-Agent", ""),
             target],
            capture_output=True,
            timeout=30,
        )

        output = curl_run.stdout.decode("utf-8", "replace")
        meta = output.split("|")[-1]

        http_code, size = (
            meta.split("|")[0],
            meta.split("|")[1] if "|" in meta else "?",
        )

        result["tests"].append({
            "name": "curl+UA",
            "status": http_code,
            "size": size,
            "kaltura_entries": kan_find_kaltura_entries(output[: -len(meta) - 1]),
        })

    except Exception as curl_err:

        result["tests"].append({
            "name": "curl+UA",
            "error": str(curl_err)[:200],
        })

    # בדיקה 5: שרשרת Wayback מלאה מהשרת עצמו + פירוק וריאנטים
    try:

        wb_body = _kan_fetch_via_wayback(target)

        result["tests"].append({
            "name": "wayback-chain",
            "ok": bool(wb_body),
            "size": len(wb_body) if wb_body else 0,
            "kaltura_entries": (
                kan_find_kaltura_entries(wb_body) if wb_body else []
            ),
        })

    except Exception as wb_err:

        result["tests"].append({
            "name": "wayback-chain",
            "error": str(wb_err)[:200],
        })

    # בדיקה 6: פירוק כל וריאנט בנפרד - מה יש בתוכו
    try:

        response = requests.get(
            "http://archive.org/wayback/available",
            params={"url": target},
            timeout=15,
        )

        closest = (
            (response.json().get("archived_snapshots") or {})
            .get("closest")
            or {}
        )

        snap_ts = closest.get("timestamp")

        result["snapshot_ts"] = snap_ts

        if snap_ts:

            for label, vurl in (
                ("id_", f"http://web.archive.org/web/{snap_ts}id_/{target}"),
                ("toolbar", f"http://web.archive.org/web/{snap_ts}/{target}"),
            ):

                try:

                    vresp = requests.get(vurl, timeout=60)

                    vbody = vresp.text

                    import re as _re

                    tokens = _re.findall(r"\b[01]_[0-9a-z]{8,12}\b", vbody)

                    result["tests"].append({
                        "name": f"variant-{label}",
                        "status": vresp.status_code,
                        "size": len(vbody),
                        "token_occurrences": len(tokens),
                        "unique_tokens": sorted(set(tokens))[:5],
                        "entries_found": kan_find_kaltura_entries(vbody)[:3],
                        "content_ok": _kan_wayback_content_ok(vbody, target),
                    })

                except Exception as v_err:

                    result["tests"].append({
                        "name": f"variant-{label}",
                        "error": str(v_err)[:150],
                    })

    except Exception as vlist_err:

        result["tests"].append({
            "name": "variant-listing",
            "error": str(vlist_err)[:200],
        })

    # בדיקה 7: זרימת הפרק המלאה - פתרון episode=1 מעמוד העונה,
    # שליפת עמוד הפרק, וחילוץ מזהה ה-Kaltura - בדיוק כמו /download
    try:

        season_url = "https://www.kan.org.il/content/kan/kan-11/p-11843/s8/"

        # פתרון רשימת הפרקים - בלי המתנת SPN, ועם נפילה לצילום ישן
        try:

            series_info = kan_extract_series_page(
                season_url,
                spn_polls=0,
            )

        except RuntimeError:

            series_info = kan_extract_series_page(
                season_url,
                spn_polls=1,
            )

        episode_urls = series_info["episode_urls"]

        # בחירת פרק בודד - בדיוק כמו ב-/download
        picked = kan_pick_episode_urls(episode_urls, episode=1)

        resolved = picked[0]

        flow = {
            "episodes_found": len(episode_urls),
            "resolved_url": resolved,
        }

        ep_page = None

        try:

            # עמוד פרק: צילום קיים כלשהו מספיק - בלי המתנת SPN
            ep_page = kan_page_fetch(resolved, spn_polls=0)

        except RuntimeError:

            pass

        if ep_page:

            flow["episode_page"] = {
                "fetched": True,
                "size": len(ep_page),
                "entries": kan_find_kaltura_entries(ep_page)[:5],
            }

            parsed = _kan_parse_episode_page(resolved, ep_page)

        else:

            flow["episode_page"] = {
                "fetched": False,
                "note": "no usable snapshot without SPN wait",
            }

            parsed = None

        flow["parsed"] = {
            "title": parsed["title"] if parsed else None,
            "entry_id": parsed["entry_id"] if parsed else None,
        }

        result["tests"].append({"name": "episode-flow", **flow})

    except Exception as flow_err:

        result["tests"].append({
            "name": "episode-flow",
            "error": str(flow_err)[:300],
        })

    result["ssl"] = ssl.OPENSSL_VERSION

    return jsonify(result)



# ============================================================
# UNIFIED SEARCH - יוטיוב + מאקו + כאן
# ============================================================
# Endpoint לטופס החיפוש המאוחד (Apps Script): מקבל מילות חיפוש
# ורשימת מקורות, מחזיר תוצאות עם קישורים שטופס ההורדות מזהה.

YOUTUBE_SEARCH_RESULTS_LIMIT = 7
IL_SEARCH_RESULTS_PER_SOURCE = 7


def _search_youtube_via_ytdlp(query, limit):

    """
    חיפוש יוטיוב דרך yt-dlp (אותו מנגנון של yt-search-service).
    מחזיר רשימת תוצאות: title/url/channel/duration.
    """

    options = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
        "extractor_args": {
            "youtube": {
                "search": [query]
            }
        },
    }

    results = []

    with yt_dlp.YoutubeDL(options) as ydl:

        info = ydl.extract_info(
            f"ytsearch{int(limit)}:{query}",
            download=False
        )

        entries = (info or {}).get("entries") or []

        for entry in entries:

            if not entry:
                continue

            # תמונה ממוזערת: hqdefault בלבד - הקובץ היחיד שיוטיוב מבטיח
            # לכל סרטון (כולל שידורי בכורה שלהם mqdefault חסר). הרשימה
            # של yt-dlp מכילה כתובות גדולות יותר (maxresdefault וכו')
            # שה-API מדווח עליהן גם כשהקובץ לא קיים בפועל - הן חוזרות
            # 404 והתמונה יוצאת ריקה במייל, ולכן לא משתמשים בהן.
            video_id = entry.get("id") or ""

            if not re.fullmatch(r"[\w-]{11}", video_id or ""):

                m_id = re.search(
                    r"(?:v=|youtu\.be/|shorts/)([\w-]{11})",
                    entry.get("url") or "",
                )

                video_id = m_id.group(1) if m_id else ""

            thumb = (
                "https://i.ytimg.com/vi/" + video_id + "/hqdefault.jpg"
                if video_id
                else None
            )

            results.append({
                "title": entry.get("title"),
                "url": entry.get("url") or entry.get("webpage_url"),
                "channel": entry.get("uploader") or entry.get("channel"),
                "duration": entry.get("duration"),
                "thumbnail": thumb,
                "source": "youtube",
            })

    return results


def _ddg_search_links(query, site, limit, trace=None):

    """
    חיפוש קישורים באתר ספציפי דרך מנועי חיפוש (ממשק HTML גולמי).
    השרת מקבל את התוצאות מהמנוע ולא מהאתרים עצמם - וכך עוקף
    גם חסימת WAF של כאן וגם הגנת hCaptcha של מאקו.

    שרשרת: DDG ישירות -> DDG דרך הפרוקסי הישראלי -> Bing.
    (DDG ישירות עובד מראנרים אך מאתגר IP-י ענן של Railway -
    אומת מהפרוב; מעבר לפרוקסי/Bing פותר את זה.)
    מחזיר רשימת (url, title) ייחודיים. trace - רשימה לדיווח
    בתשובת ה-API: מה נוסה וכמה נמצא.
    """

    search_query = f"{query} site:{site}"

    # GET עובד - POST מקבל עמוד anomaly של DDG (אומת מהראנר):
    # html GET החזיר 40 קישורי uddg, lite GET עוד 10.
    # Bing RSS ראשון — מהימן מ-IP ענן, קישורים ישירים בלי ניתובים.
    endpoints = [
        ("https://www.bing.com/search", "rss"),
        ("https://html.duckduckgo.com/html/", None),
        ("https://lite.duckduckgo.com/lite/", None),
        ("https://html.duckduckgo.com/html/", "proxy"),
        ("https://www.bing.com/search", None),
        ("https://www.bing.com/search", "proxy"),
    ]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "he-IL,he;q=0.9,en;q=0.7",
    }

    found = []
    seen = set()

    def _parse_ddg(text):

        # קישורי ניתוב שמכילים uddg=<כתובת מקודדת>. ה-prefix יכול
        # להיות //duckduckgo.com/l/, /l/, או כתובת מלאה.
        for m in re.finditer(
            r'<a[^>]+href=["\'][^"\']*uddg=([^"\'&]+)[^"\']*'
            '["\'][^>]*>(.*?)</a>',
            text,
            re.S | re.I,
        ):

            try:
                real_url = urllib.parse.unquote(m.group(1))
            except Exception:
                continue

            title = re.sub(r"<[^>]+>", " ", m.group(2))
            title = re.sub(
                r"\s+", " ", html_lib.unescape(title)
            ).strip()

            if (
                not real_url
                or real_url in seen
                or site not in real_url
            ):
                continue

            seen.add(real_url)
            found.append((real_url, title))

    def _parse_bing_rss(text):

        # Bing RSS: <item><title>..</title><link>..</link> —
        # הקישורים ישירים (בלי ניתוב ck) והכותרות נקיות.
        for m in re.finditer(
            r"<item>\s*<title>(.*?)</title>\s*<link>(.*?)</link>",
            text,
            re.S | re.I,
        ):

            title = html_lib.unescape(m.group(1)).strip()

            try:
                real_url = html_lib.unescape(m.group(2)).strip()
            except Exception:
                continue

            if (
                not real_url.startswith("http")
                or real_url in seen
                or site not in real_url
            ):
                continue

            seen.add(real_url)
            found.append((real_url, title))

    def _parse_bing(text):

        # Bing: <li class="b_algo"><h2><a href="...">כותרת</a>.
        # ה-href הוא ניתוב bing.com/ck/a?...&u=a1<base64url> שמקודד
        # את הכתובת האמיתית - מפענחים אותו.
        def _decode_bing_href(href):

            if "bing.com/ck/" not in href:
                return href

            # ב-HTML של Bing האמפרסנדים מקודדים (&amp;u=a1),
            # ולכן החיפוש הוא על u=a1 עצמו בלי תלות בתו שלפניו
            m_u = re.search(r"u=a1([A-Za-z0-9_-]+)", href)

            if not m_u:
                return None

            import base64

            payload = m_u.group(1)

            try:
                decoded = base64.urlsafe_b64decode(
                    payload + "=" * (-len(payload) % 4)
                ).decode("utf-8", "replace")
            except Exception:
                return None

            return decoded if decoded.startswith("http") else None

        for m in re.finditer(
            r'<h2[^>]*>\s*<a[^>]+href=["\']([^"\' ]+)["\'][^>]*>(.*?)</a>',
            text,
            re.S | re.I,
        ):

            real_url = _decode_bing_href(m.group(1))

            title = re.sub(r"<[^>]+>", " ", m.group(2))
            title = re.sub(
                r"\s+", " ", html_lib.unescape(title)
            ).strip()

            if (
                not real_url
                or real_url in seen
                or site not in real_url
            ):
                continue

            seen.add(real_url)
            found.append((real_url, title))

        # גיבוי: פענוח כל ניתובי u=a1 בעמוד בלי תלות במבנה ה-anchor
        for m in re.finditer(
            r"u=a1([A-Za-z0-9_-]{20,})",
            text,
            re.I,
        ):

            if len(found) >= limit * 3:
                break

            import base64

            payload = m.group(1)

            try:
                real_url = base64.urlsafe_b64decode(
                    payload + "=" * (-len(payload) % 4)
                ).decode("utf-8", "replace")
            except Exception:
                continue

            if (
                not real_url.startswith("http")
                or real_url in seen
                or site not in real_url
            ):
                continue

            seen.add(real_url)
            found.append((real_url, ""))

    for endpoint, mode in endpoints:

        if len(found) >= limit:
            break

        engine_label = (
            "ddg"
            if "duckduckgo" in endpoint
            else "bing"
        ) + ("-" + mode if mode else "-direct")

        before_count = len(found)

        proxies = None

        if mode == "proxy":

            proxy = _kan_get_working_proxy()

            if not proxy:

                if trace is not None:
                    trace.append(engine_label + ":no-proxy")

                continue

            proxies = {"http": proxy, "https": proxy}

        try:

            if "duckduckgo" in endpoint:

                response = requests.get(
                    endpoint,
                    params={"q": search_query},
                    headers=headers,
                    timeout=25,
                    proxies=proxies,
                    verify=(mode != "proxy"),
                )

            else:  # Bing (HTML או RSS)

                params = {
                    "q": search_query,
                    "setlang": "he",
                    "count": str(max(limit * 2, 15)),
                }

                if mode == "rss":
                    params["format"] = "rss"

                response = requests.get(
                    endpoint,
                    params=params,
                    headers=headers,
                    timeout=25,
                    proxies=proxies,
                )

            if response.status_code != 200:
                print(
                    "IL search:", endpoint, mode,
                    "HTTP", response.status_code,
                    flush=True,
                )

                if trace is not None:
                    trace.append(
                        f"{engine_label}:http{response.status_code}"
                    )

                continue

            if "duckduckgo" in endpoint:
                _parse_ddg(response.text)
            elif mode == "rss":
                _parse_bing_rss(response.text)
            else:
                _parse_bing(response.text)

            gained = len(found) - before_count

            print(
                "IL search:", endpoint, mode,
                "-> total found:", len(found),
                flush=True,
            )

            if trace is not None:
                trace.append(f"{engine_label}:+{gained}")

        except Exception as search_err:

            print(
                "IL search failed:", endpoint, mode,
                str(search_err)[:100],
                flush=True,
            )

            if trace is not None:
                trace.append(
                    f"{engine_label}:err:{str(search_err)[:60]}"
                )

            continue

    return found[:limit]


def _parse_series_query(query):

    """
    חילוץ מובנה של שם סדרה + עונה + פרק משאילתת חיפוש בעברית.
    לדוגמה: "בואו לאכול איתי עונה 1 פרק 2" ->
    {"series": "בואו לאכול איתי", "season": 1, "episode": 2}
    מחזיר None אם אין בשאילתא אזכור מפורש של עונה/פרק.
    """

    season = None
    episode = None

    m = re.search(r"עונה\s*(\d{1,2})", query)
    if m:
        season = int(m.group(1))

    m = re.search(r"פרק\s*(\d{1,4})", query)
    if m:
        episode = int(m.group(1))

    if season is None and episode is None:
        return None

    # שם הסדרה = השאילתא לפני האזכור הראשון של עונה/פרק
    cut = re.search(r"עונה\s*\d|פרק\s*\d", query)
    series = query[: cut.start()].strip(" -–—,?") if cut else query.strip()

    return {
        "series": series,
        "season": season,
        "episode": episode,
    }


def _series_variants(query):

    """
    וריאציות חיפוש לשאילתא: השאילתא המלאה + גרסת שם-סדרה בלבד
    (כשיש אזכור עונה/פרק). כך "בואו לאכול איתי עונה 1 פרק 2"
    יחפש גם רק "בואו לאכול איתי" — שמחזיר את עמודי הסדרה/עונות.
    """

    variants = [query]

    parsed = _parse_series_query(query)
    if parsed and parsed["series"] and parsed["series"] != query:
        variants.append(parsed["series"])

        # וריאציית מרכאות — בינג מתמקד יותר כששם הסדרה במרכאות
        quoted = f'"{parsed["series"]}"'
        if quoted not in variants:
            variants.append(quoted)

    return variants


def _search_kan_site(query, limit, trace=None):

    """
    חיפוש סדרות/פרקים בכאן: מנועי חיפוש עם site:kan.org.il.
    מסנן לעמודי תוכן (סדרה/עונה/פרק) - הקישורים שטופס ההורדות
    מזהה ומטפל בהם.
    """

    pairs = _ddg_search_links(
        query,
        "kan.org.il",
        limit * 3,
        trace=trace,
    )

    matches = []

    for url, title in pairs:

        # עמודי תוכן בלבד, ולא עמודי סטטיים/חדשות
        if not re.search(
            r"kan\.org\.il/content/.+/p-\d+", url
        ):
            continue

        matches.append({
            "title": title or url,
            "url": url,
            "channel": "כאן",
            "duration": None,
            "source": "kan",
        })

        if len(matches) >= limit:
            break

    return matches


def _search_kan_multi(query, limit, trace=None):

    """
    חיפוש כאן עם וריאציות: השאילתא המלאה, ואם יש אזכור עונה/פרק —
    גם שם הסדרה בלבד (שמחזיר עמודי סדרה/עונה). כשהשאילתא מציינת
    עונה מפורשת ונמצא עמוד סדרה בלי עונה — בונים ישירות גם את
    קישור העונה (kan_resolve_series_url מאומת בהורדות).
    """

    all_matches = []
    seen_urls = set()
    parsed = _parse_series_query(query)

    for i, variant in enumerate(_series_variants(query)):

        vtrace = [] if trace is None else []
        found = _search_kan_site(variant, limit, trace=vtrace)

        if trace is not None:
            trace.append(f"variant{i+1}:{variant[:30]}:+{len(found)}")
            trace.extend(vtrace)

        # בניית קישורי עונה מעמודי סדרה כשהשאילתא מציינת עונה
        if parsed and parsed["season"] is not None:

            for item in list(found):

                m = re.match(
                    r"^(https?://(?:www\.)?kan\.org\.il"
                    r"/content/.+/p-\d+)(?:\?.*)?$",
                    item["url"].rstrip("/"),
                )

                if not m:
                    continue

                season_url = f"{m.group(1)}/s{parsed['season']}/"

                if season_url not in seen_urls:
                    seen_urls.add(season_url)
                    all_matches.append({
                        "title": (
                            f"{parsed['series'] or variant} - "
                            f"עונה {parsed['season']}"
                        ),
                        "url": season_url,
                        "channel": "כאן",
                        "duration": None,
                        "source": "kan",
                    })

        for item in found:
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                all_matches.append(item)

        if len(all_matches) >= limit:
            break

    return all_matches[:limit]


def _search_mako_site(query, limit, trace=None):

    """
    חיפוש סדרות במאקו: מנועי חיפוש עם site:mako.co.il.
    מסנן לעמודי סדרות/פרקים VOD - הקישורים שהשרת וטופס
    ההורדות יודעים לטפל בהם.
    """

    pairs = _ddg_search_links(
        query,
        "mako.co.il",
        limit * 3,
        trace=trace,
    )

    matches = []

    for url, title in pairs:

        if "mako.co.il" not in url:
            continue

        # עמודי VOD/סדרות/פרקים - מקבלים כל כתובת תוכן של מאקו
        # שהיא לא עמוד ראשי/חיפוש; עמודים לא נתמכים יחזירו
        # שגיאה ברורה מהשרת בעת ההורדה
        path_lower = url.lower()        # עמודי Tagit (תגיות) מוגנים ב-Radware ולא ניתנים להורדה -
        # לא להציע אותם כתוצאות חיפוש
        if re.search(
            r"mako\.co\.il/(?:$|search|tagit)",
            path_lower
        ):
            continue

        matches.append({
            "title": title or url,
            "url": url,
            "channel": "מאקו",
            "duration": None,
            "source": "mako",
        })

        if len(matches) >= limit:
            break

    return matches


def _search_mako_multi(query, limit, trace=None):

    """
    חיפוש מאקו עם וריאציות (כמו בכאן): השאילתא המלאה + שם סדרה
    בלבד כשיש אזכור עונה/פרק.
    """

    all_matches = []
    seen_urls = set()

    for i, variant in enumerate(_series_variants(query)):

        vtrace = [] if trace is None else []
        found = _search_mako_site(variant, limit, trace=vtrace)

        if trace is not None:
            trace.append(f"variant{i+1}:{variant[:30]}:+{len(found)}")
            trace.extend(vtrace)

        for item in found:
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                all_matches.append(item)

        if len(all_matches) >= limit:
            break

    return all_matches[:limit]


# מטמון תוצאות חיפוש קצר: לחיצה חוזרת על "חפש" (או Apps Script
# שמריץ מחדש את אותה שאילתא) מחזירה תשובה מיידית במקום להמתין
# שוב לכל המקורות, ובנוסף המנועים לא מוצפים בשאילתות זהות.
# 10 דקות מספיקות לניסיון חוזר אנושי ומונעות תוצאות מיושנות מדי.
SEARCH_CACHE_TTL = 600
SEARCH_CACHE_MAX_ENTRIES = 100
_SEARCH_CACHE = {}


def _search_cache_get(key):

    entry = _SEARCH_CACHE.get(key)

    if not entry:
        return None

    ts, payload = entry

    if time.time() - ts > SEARCH_CACHE_TTL:
        _SEARCH_CACHE.pop(key, None)
        return None

    return payload


def _search_cache_put(key, payload):

    _SEARCH_CACHE[key] = (time.time(), payload)

    # גבול זיכרון פשוט - מוחקים את הישן ביותר
    while len(_SEARCH_CACHE) > SEARCH_CACHE_MAX_ENTRIES:

        oldest = min(_SEARCH_CACHE, key=lambda k: _SEARCH_CACHE[k][0])

        _SEARCH_CACHE.pop(oldest, None)


@app.route("/search", methods=["POST", "GET"])
def unified_search():

    """
    חיפוש מאוחד: יוטיוב + מאקו + כאן.
    גוף הבקשה: {"query": "...", "sources": ["youtube","mako","kan"],
                  "limit": 6}
    מחזיר {"success": true, "results": [...], "by_source": {...}}
    """

    provided_key = request.headers.get("X-API-KEY", "")

    # מקבלים את מפתח ה-API הרגיל או את המפתח הייעודי של טופס החיפוש
    allowed = {API_KEY, UNIFIED_SEARCH_KEY}
    allowed.discard("")

    if (
        not provided_key
        or provided_key not in allowed
    ):
        return jsonify({
            "success": False,
            "error": "unauthorized"
        }), 401

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
    else:
        data = request.args

    query = (data.get("query") or "").strip()

    if not query:
        return jsonify({
            "success": False,
            "error": "missing 'query'"
        }), 400

    sources = data.get("sources") or ["youtube", "mako", "kan"]

    if isinstance(sources, str):
        sources = [s.strip() for s in sources.split(",") if s.strip()]

    sources = [s.lower() for s in sources]

    try:
        limit = max(1, min(int(data.get("limit", 6)), 10))
    except (TypeError, ValueError):
        limit = 6

    cache_key = (query, tuple(sources), limit)

    cached = _search_cache_get(cache_key)

    if cached is not None:

        response = jsonify(cached)
        response.headers["X-Cache"] = "HIT"
        return response

    results = []
    by_source = {}
    source_errors = {}
    search_trace = {}

    # המקורות נשלפים במקביל: יוטיוב, כאן ומאקו הן שרשראות עצמאיות
    # שכל אחת מהן יכולה לקחת עשרות שניות (בעיקר כאן/מאקו דרך מנועי
    # החיפוש), וריצה סדרתית מחברת את כל ההמתנות. סדר התוצאות
    # בתשובה נשמר זהה לריצה הסדרתית - pool.map מחזיר לפי סדר הקלט.
    def _run_source(source):

        if source == "youtube":

            try:
                found = _search_youtube_via_ytdlp(
                    query, YOUTUBE_SEARCH_RESULTS_LIMIT
                )

                # יוטיוב מטלטל: לפעמים מחזיר 0 בלי שגיאה.
                # ניסיון חוזר פעם אחת על תוצאות ריקות.
                if not found:
                    time.sleep(2)
                    found = _search_youtube_via_ytdlp(
                        query, YOUTUBE_SEARCH_RESULTS_LIMIT
                    )

                return ("youtube", found, None, None)

            except Exception as yt_err:
                return ("youtube", [], str(yt_err)[:200], None)

        if source == "kan":

            kan_trace = []

            try:
                found = _search_kan_multi(
                    query,
                    IL_SEARCH_RESULTS_PER_SOURCE,
                    trace=kan_trace,
                )
                return ("kan", found, None, kan_trace)

            except Exception as kan_err:
                return ("kan", [], str(kan_err)[:200], kan_trace)

        if source == "mako":

            mako_trace = []

            try:
                found = _search_mako_multi(
                    query,
                    IL_SEARCH_RESULTS_PER_SOURCE,
                    trace=mako_trace,
                )
                return ("mako", found, None, mako_trace)

            except Exception as mako_err:
                return ("mako", [], str(mako_err)[:200], mako_trace)

        # מקור לא מוכר - מתעלמים ממנו (אותה התנהגות כמו קודם)
        return (source, [], None, None)

    with ThreadPoolExecutor(max_workers=3) as pool:

        for source, found, source_error, s_trace in pool.map(
            _run_source, sources
        ):

            if source_error:
                source_errors[source] = source_error
            else:
                # נרשם גם 0 - כדי שהאבחון (probe/by_source) יראה
                # שהמקור ענה אך לא מצא כלום, ולא שנפל.
                by_source[source] = len(found)
                results.extend(found)

            if s_trace is not None:
                search_trace[source] = s_trace

    payload = {
        "success": True,
        "query": query,
        "sources": sources,
        "count": len(results),
        "by_source": by_source,
        "source_errors": source_errors,
        "search_trace": search_trace,
        "parsed": _parse_series_query(query),
        "results": results,
    }

    _search_cache_put(cache_key, payload)

    response = jsonify(payload)
    response.headers["X-Cache"] = "MISS"
    return response


# ============================================================
# TELEGRAM SONGS WATCHER (אופציונלי)
# ============================================================
# דימון נפרד (telegram_songs_to_drive.py) שעוקב אחרי ערוצי טלגרם,
# מוריד שירים חדשים ומעלה אותם ל-Drive. קם אוטומטית לצד השרת רק
# כשמוגדרים Secrets: TELEGRAM_API_ID, TELEGRAM_API_HASH,
# TELEGRAM_SESSION_STRING ו-TELEGRAM_CHANNELS.
# בלי ההגדרות - לא קורה כלום והשרת מתנהג בדיוק כמו קודם.

TELEGRAM_WATCHER_ENABLED = all(
    os.environ.get(name)
    for name in (
        "TELEGRAM_API_ID",
        "TELEGRAM_API_HASH",
        "TELEGRAM_SESSION_STRING",
        "TELEGRAM_CHANNELS",
        "GOOGLE_OAUTH_CLIENT_ID",
        "GOOGLE_OAUTH_REFRESH_TOKEN",
    )
)

if TELEGRAM_WATCHER_ENABLED:

    def _start_telegram_watcher():

        import subprocess
        import sys

        script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "telegram_songs_to_drive.py",
        )

        try:

            process = subprocess.Popen(
                [sys.executable, script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

        except Exception as e:
            print(
                "Telegram watcher: failed to start:",
                e,
                flush=True,
            )
            return

        # מעביר את הלוגים של הדימון ללוג של השרת - כך רואים הכל
        # במקום אחד (Console של ריוולי / לוגים של Railway).
        def _pump():

            try:

                for line in process.stdout:
                    print("[tg-watcher]", line.rstrip(), flush=True)

            except Exception:
                pass

            code = process.wait()
            print(
                "Telegram watcher exited with code",
                code,
                flush=True,
            )

        threading.Thread(target=_pump, daemon=True).start()

        return process

    _start_telegram_watcher()

# ============================================================
# LIVE RECORDER (/record/* - הקלטת שידור חי)
# ============================================================
# הקלטת זרם HLS חי (כרגע: קשת 12, HLS פתוח ללא DRM) עם ffmpeg,
# העלאה ל-Drive ומחיקה מקומית. הקלטה אחת בכל פעם, תקרת דקות.
# אלה הנתיבים שלוח הבקרה (Apps Script) והבוט (אם יופעל) קוראים.

LIVE_CHANNELS_APP = {
    "12": "https://mako-streaming.akamaized.net/direct/hls/live/20000821/k12ni-bu/index.m3u8",
}

RECORD_MAX_MINUTES_APP = int(
    os.environ.get("RECORD_MAX_MINUTES", "180")
)

RECORD_DIR_APP = os.path.join(
    tempfile.gettempdir(),
    "live_records"
)

RECORDS_LOCK_APP = threading.Lock()
RECORDS_APP = {}


def _record_worker_app(chat_label, channel_key, minutes, notify_email=None):

    """
    מקליט, מעלה ל-Drive, מודיע בלוג. רץ ב-thread דמון.
    """

    rec = RECORDS_APP.get(chat_label)
    out_path = rec["path"]
    duration = minutes * 60
    started_at = time.time()

    cmd = [
        "ffmpeg", "-y",
        "-i", LIVE_CHANNELS_APP[channel_key],
        "-t", str(duration),
        "-c", "copy",
        "-f", "mpegts",
        out_path,
    ]

    proc = None
    stopped_manually = {"flag": False}

    try:

        os.makedirs(RECORD_DIR_APP, exist_ok=True)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.PIPE,
        )

        with RECORDS_LOCK_APP:
            rec["pid"] = proc.pid
            rec["state"] = "recording"

        try:
            proc.wait(timeout=duration + 120)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except Exception:
                proc.kill()

    except Exception as e:

        print("[record] worker failed:", e, flush=True)

        with RECORDS_LOCK_APP:
            rec["state"] = "failed"
            rec["error"] = str(e)[:200]

        try:
            os.remove(out_path)
        except OSError:
            pass

        return

    with RECORDS_LOCK_APP:
        rec["state"] = "uploading"

    file_size = (
        os.path.getsize(out_path)
        if os.path.exists(out_path)
        else 0
    )

    if file_size < 10000:

        with RECORDS_LOCK_APP:
            rec["state"] = "failed"
            rec["error"] = "empty recording (blocked or DRM?)"

        try:
            os.remove(out_path)
        except OSError:
            pass

        return

    # העלאה לתיקיית "הקלטות" בתוך תיקיית היעד
    try:

        parent = (
            ensure_drive_folder("הקלטות")
            if DRIVE_FOLDER_ID
            else None
        )

        svc = get_drive_service()

        file_name = "הקלטה_{}_{}.mp4".format(
            channel_key,
            time.strftime("%Y-%m-%d_%H-%M", time.gmtime())
        )

        media = MediaFileUpload(out_path, resumable=True)

        uploaded = (
            svc.files()
            .create(
                body={
                    "name": file_name,
                    "parents": [parent] if parent else [],
                },
                media_body=media,
                fields="id, webViewLink",
            )
            .execute()
        )

        link = uploaded.get("webViewLink")
        file_id = uploaded.get("id")

        if notify_email:
            try:
                share_with_email(file_id, notify_email)
            except Exception as se:
                print("[record] share failed:", se, flush=True)

        with RECORDS_LOCK_APP:
            rec["state"] = "done"
            rec["driveLink"] = link
            rec["file_id"] = file_id
            rec["finished_at"] = time.time()

        print(
            "[record] done: {} -> {}".format(file_name, link),
            flush=True
        )

    except Exception as e:

        print("[record] upload failed:", e, flush=True)

        with RECORDS_LOCK_APP:
            rec["state"] = "failed"
            rec["error"] = str(e)[:200]

    finally:

        try:
            os.remove(out_path)
        except OSError:
            pass


def _record_status_app(chat_label):

    with RECORDS_LOCK_APP:
        rec = RECORDS_APP.get(chat_label)

        if not rec:
            return None

        return json.loads(json.dumps(rec))


@app.route("/record/start", methods=["POST"])
def record_start():

    provided_key = request.headers.get("X-API-KEY", "")

    if (
        not API_KEY
        or provided_key != API_KEY
    ):
        return jsonify({"success": False, "error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}

    channel = str(data.get("channel", "12"))
    minutes = data.get("minutes", 60)
    notify_email = (
        (data.get("notify_email") or "").strip() or None
    )

    try:
        minutes = max(1, min(int(minutes), RECORD_MAX_MINUTES_APP))
    except (TypeError, ValueError):
        minutes = 60

    if channel not in LIVE_CHANNELS_APP:
        return jsonify({
            "success": False,
            "error": "unknown channel",
            "available": sorted(LIVE_CHANNELS_APP),
        }), 400

    with RECORDS_LOCK_APP:

        current = RECORDS_APP.get("current")

        if current and current.get("state") in (
            "recording", "uploading", "starting"
        ):
            return jsonify({
                "success": False,
                "error": "recording already in progress",
                "current": {
                    "channel": current.get("channel"),
                    "started_at": current.get("started_at_iso"),
                },
            }), 409

    rec_id = "rec_{}".format(int(time.time()))
    out_path = os.path.join(
        RECORD_DIR_APP,
        "{}_{}.ts".format(channel, rec_id),
    )

    rec = {
        "id": rec_id,
        "channel": channel,
        "minutes": minutes,
        "path": out_path,
        "state": "starting",
        "started_at": time.time(),
        "started_at_iso": time.strftime(
            "%Y-%m-%d %H:%M:%S UTC", time.gmtime()
        ),
        "notify_email": notify_email,
    }

    with RECORDS_LOCK_APP:
        RECORDS_APP["current"] = rec

    threading.Thread(
        target=_record_worker_app,
        args=("current", channel, minutes, notify_email),
        daemon=True,
    ).start()

    return jsonify({
        "success": True,
        "recording": {
            "id": rec_id,
            "channel": channel,
            "minutes": minutes,
            "started_at": rec["started_at_iso"],
        },
    })


@app.route("/record/stop", methods=["POST"])
def record_stop():

    provided_key = request.headers.get("X-API-KEY", "")

    if (
        not API_KEY
        or provided_key != API_KEY
    ):
        return jsonify({"success": False, "error": "unauthorized"}), 401

    with RECORDS_LOCK_APP:
        rec = RECORDS_APP.get("current")

    if not rec or rec.get("state") not in ("starting", "recording"):
        return jsonify({
            "success": False,
            "error": "no active recording",
        }), 404

    # ffmpeg מסיים בניקוי קובץ mpegts תקין כששולחים SIGINT
    try:
        os.kill(rec.get("pid"), signal.SIGINT)
    except Exception:
        pass

    return jsonify({"success": True, "stopping": rec.get("id")})


@app.route("/record/list", methods=["GET"])
def record_list():

    provided_key = request.headers.get("X-API-KEY", "")

    if (
        not API_KEY
        or provided_key != API_KEY
    ):
        return jsonify({"success": False, "error": "unauthorized"}), 401

    with RECORDS_LOCK_APP:
        current = (
            json.loads(json.dumps(RECORDS_APP.get("current")))
            if RECORDS_APP.get("current")
            else None
        )

    if current and current.get("state") == "recording":
        current["elapsed_minutes"] = round(
            (time.time() - current.get("started_at", time.time())) / 60,
            1,
        )

    # היסטוריית הקלטות מהדיסק - רק קישורי Drive של ההקלטות האחרונות
    # (ה-state חי רק בזיכרון; אחרי redeploy ההיסטוריה מתחילה מחדש)

    return jsonify({
        "success": True,
        "current": current,
        "max_minutes": RECORD_MAX_MINUTES_APP,
        "channels": sorted(LIVE_CHANNELS_APP),
    })


@app.route("/jobs/recent", methods=["GET"])
def jobs_recent():

    """
    20 העבודות האחרונות ללוח הבקרה. קורא את קבצי ה-JSON של העבודות
    מהדיסק - בלי לגעת ב-JOBS שבזיכרון.
    """

    provided_key = request.headers.get("X-API-KEY", "")

    if (
        not API_KEY
        or provided_key != API_KEY
    ):
        return jsonify({"success": False, "error": "unauthorized"}), 401

    jobs = []

    try:

        paths = glob.glob(
            os.path.join(JOBS_DIR, "*.json")
        )

        entries = []

        for p in paths:

            try:

                with open(p, "r", encoding="utf-8") as f:
                    j = json.load(f)

                entries.append({
                    "id": j.get("id"),
                    "status": j.get("status"),
                    "kind": j.get("kind", "single"),
                    "url": (j.get("url") or "")[:120],
                    "channel": j.get("channel"),
                    "total": j.get("total", 1 if j.get("kind") != "season" else 0),
                    "done": j.get("done_count", 0),
                    "failed": j.get("failed_count", 0),
                    "created_at": j.get("created_at"),
                    "updated_at": j.get("updated_at", 0),
                })

            except Exception:
                continue

        entries.sort(
            key=lambda x: x.get("updated_at") or 0,
            reverse=True,
        )

        jobs = entries[:20]

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)[:200],
        }), 500

    return jsonify({
        "success": True,
        "jobs": jobs,
    })


# ============================================================
# בוט טלגרם (הורדות ל-Drive + הקלטות) - אותו דפוס של ה-watcher:
# תהליך-בן שמופעל רק אם TELEGRAM_BOT_TOKEN מוגדר. בלי הטוקן השרת
# מתנהג בדיוק כמו קודם. הבוט קורא ל-API הפנימי על loopback, כך
# שכל ההורדות עוברות דרך אותו מנוע ואותן משימות.
#
# ניטור: /bot/status מדווח את מצב תהליך-הבן, את פלטו האחרון ואת
# בדיקת getMe/getUpdates מצד השרת (כולל זיהוי 409 = הבוט באמת
# מקשיב). /bot/restart מפעיל אותו מחדש. אם הבוט נופל, watchdog
# מחזיר אותו אוטומטית אחרי השהיה קצרה.
# ------------------------------------------------------------

TELEGRAM_BOT_ENABLED = bool(
    os.environ.get("TELEGRAM_BOT_TOKEN")
)

TG_BOT_STATE = {
    "proc": None,
    "started_at": None,
    "restarts": 0,
    "last_exit_code": None,
    "lines": [],
}

_BOT_LOG_MAX_LINES = 200


def _bot_log(line):

    lines = TG_BOT_STATE["lines"]

    # חותמת זמן לכל שורה - קריטי לאבחון "Conflict" חוזר: בלי זמן לא
    # נדע אם ההתנגשויות דועכות (חפיפת פריסה) או ממשיכות (מופע שני).

    lines.append("[%s] %s" % (time.strftime("%H:%M:%S"), line))

    if len(lines) > _BOT_LOG_MAX_LINES:

        del lines[: len(lines) - _BOT_LOG_MAX_LINES]


def _spawn_telegram_bot(reason="start"):

    import subprocess
    import sys

    if not TELEGRAM_BOT_ENABLED:
        return None

    old = TG_BOT_STATE.get("proc")

    if old is not None and old.poll() is None:

        try:

            old.terminate()

        except Exception:

            pass

    script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "telegram_bot.py",
    )

    try:

        process = subprocess.Popen(
            [sys.executable, script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

    except Exception as e:
        print(
            "Telegram bot: failed to start:",
            e,
            flush=True,
        )
        _bot_log("[parent] spawn failed: %r" % e)
        return None

    TG_BOT_STATE["proc"] = process
    TG_BOT_STATE["started_at"] = time.time()

    if reason != "start":

        TG_BOT_STATE["restarts"] += 1

    print(
        "Telegram bot: spawned (pid %s, %s)" % (process.pid, reason),
        flush=True,
    )

    _bot_log("[parent] spawned pid=%s (%s)" % (process.pid, reason))

    def _pump():

        try:

            for line in process.stdout:

                text = line.rstrip()

                print("[tgbot]", text, flush=True)

                _bot_log(text)

        except Exception:
            pass

        code = process.wait()

        TG_BOT_STATE["last_exit_code"] = code

        print(
            "Telegram bot exited with code",
            code,
            flush=True,
        )

        _bot_log("[parent] exited code=%s" % code)

    threading.Thread(target=_pump, daemon=True).start()

    return process


def _bot_watchdog():

    # אם תהליך הבוט נופל (קריסה, OOM, שגיאה קטלנית) - מחזירים אותו
    # אחרי השהיה קצרה. בלי זה, בוט שמת משאיר אותנו שקטים עד ל-deploy
    # הבא, והמשתמש רואה סתם בוט שלא עונה.

    while True:

        time.sleep(60)

        proc = TG_BOT_STATE.get("proc")

        if proc is None:

            _spawn_telegram_bot("watchdog: missing")

            continue

        if proc.poll() is not None:

            time.sleep(15)

            _spawn_telegram_bot("watchdog: respawn after exit")


def _bot_api_probe():

    # בדיקת תקינות מצד השרת: getMe מוכיח שהטוקן תקין וש-api.telegram.org
    # נגיש מהקונטיינר. getUpdates (timeout=0) מחזיר 409 כשתהליך הבוט
    # באמת מחזיק את ה-polling - דרך קלה לאמת שהוא חי בלי לגעת בעדכונים.

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")

    base = "https://api.telegram.org/bot" + token

    result = {}

    try:

        req = urllib.request.Request(base + "/getMe")

        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))

        result["getme_ok"] = bool(data.get("ok"))
        result["bot_username"] = (data.get("result") or {}).get("username")

    except Exception as e:

        result["getme_ok"] = False
        result["getme_error"] = str(e)[:120]

    # getWebhookInfo - בדיקה לא פולשנית: מדווח pending_update_count
    # וגם last_error_message/last_error_date. בוט שמתחרה על getUpdates
    # מול מופע אחר יראה כאן Conflict עם תאריך עדכני - בלי לשבש את
    # ה-polling בעצמנו.

    try:

        req = urllib.request.Request(base + "/getWebhookInfo")

        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))

        if data.get("ok"):

            res = data.get("result") or {}

            result["pending_updates"] = res.get("pending_update_count")
            result["last_error_message"] = res.get("last_error_message")
            result["last_error_date"] = res.get("last_error_date")

    except Exception as e:

        result["webhook_info_error"] = str(e)[:120]

    # בדיקת ה-409 עצמה פולשנית: טלגרם מחזיר Conflict לבקשת ה-getUpdates
    # הפעילה של הבוט ומפיל אותה לרגע. לכן היא רצה רק כשמבקשים אותה
    # מפורשות - /bot/status?key=...&probe=1

    if request.args.get("probe"):

        try:

            req = urllib.request.Request(
                base + "/getUpdates?timeout=0"
            )

            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(
                    resp.read().decode("utf-8", "replace")
                )

            result["getupdates_ok"] = bool(data.get("ok"))

        except urllib.error.HTTPError as e:

            # 409 = מישהו (הבוט שלנו) כבר מחזיק את getUpdates - סימן טוב.

            result["getupdates_ok"] = None
            result["getupdates_conflict"] = e.code == 409
            result["getupdates_error"] = str(e)[:120]

        except Exception as e:

            result["getupdates_ok"] = False
            result["getupdates_error"] = str(e)[:120]

    return result


def _bot_key_ok():

    key = (
        request.args.get("key")
        or request.headers.get("X-API-KEY")
        or ""
    )

    return (not API_KEY) or (key == API_KEY)


if TELEGRAM_BOT_ENABLED:

    _spawn_telegram_bot("start")

    threading.Thread(target=_bot_watchdog, daemon=True).start()

    @app.route("/bot/status")
    def bot_status():

        if not _bot_key_ok():

            return jsonify(
                {"success": False, "error": "unauthorized"}
            ), 401

        proc = TG_BOT_STATE.get("proc")

        alive = bool(proc is not None and proc.poll() is None)

        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")

        admin_ids = [
            x
            for x in re.split(
                r"[\s,]+",
                os.environ.get("TELEGRAM_ADMIN_IDS", "").strip(),
            )
            if x
        ]

        songs_channels = [
            x.strip()
            for x in os.environ.get(
                "TELEGRAM_SONGS_CHANNELS", ""
            ).split(",")
            if x.strip()
        ]

        return jsonify({
            "enabled": TELEGRAM_BOT_ENABLED,
            "token_set": bool(token),
            "token_tail": (
                "..." + token[-4:]
            ) if len(token) >= 8 else None,
            "admin_ids": admin_ids,
            "songs_channels": songs_channels,
            "child_alive": alive,
            "child_pid": proc.pid if proc is not None else None,
            "last_exit_code": TG_BOT_STATE.get("last_exit_code"),
            "started_at": TG_BOT_STATE.get("started_at"),
            "uptime_seconds": (
                int(time.time() - TG_BOT_STATE["started_at"])
                if TG_BOT_STATE.get("started_at")
                else None
            ),
            "restarts": TG_BOT_STATE.get("restarts", 0),
            "recent_log": list(TG_BOT_STATE["lines"])[-60:],
            "probe": _bot_api_probe(),
        })

    @app.route("/bot/restart")
    def bot_restart():

        if not _bot_key_ok():

            return jsonify(
                {"success": False, "error": "unauthorized"}
            ), 401

        _spawn_telegram_bot("manual restart")

        return jsonify({"success": True, "restarted": True})

# ============================================================
# START SERVER
# ============================================================
# חייב להישאר בסוף הקובץ - כל route שמוגדר אחריו לא נרשם.

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=int(
            os.environ.get(
                "PORT",
                8080
            )
        ),

        threaded=True
    )
