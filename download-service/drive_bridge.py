# ============================================================
# גשר טוקנים לדרייב דרך Apps Script
# ============================================================
# במקום refresh token מ-OAuth Playground (שדורש Client משלנו ב-Google
# Cloud ופג/נפסל), השרת מבקש access token טרי מה-Web App של מערכת
# ההורדות (apps-script/Code.gs, פעולה drive_token). הסקריפט רץ בשם
# הבעלים, ולכן הטוקן כותב לדרייב שלו. אין Client ID, אין Secret ואין
# טוקן להחליף - הגישה נשמרת כל עוד הסקריפט מאושר.
# ============================================================

import datetime
import os

import requests
from google.auth.credentials import Credentials as _BaseCredentials

# ה-Web App הקיים של מערכת ההורדות (אותו URL שהתוסף משתמש בו).
# יש להגדיר את משתנה הסביבה DRIVE_TOKEN_BRIDGE_URL לכתובת ה-Web App שלך
# (מסתיימת ב-/exec). אפשר גם להדביק אותה כאן.
DEFAULT_BRIDGE_URL = ""


def bridge_url():
    # "off" מכבה את הגשר וחוזר ל-refresh token בלבד
    url = os.environ.get("DRIVE_TOKEN_BRIDGE_URL", "").strip()
    if url.lower() == "off":
        return ""
    return url or DEFAULT_BRIDGE_URL


class AppsScriptDriveCredentials(_BaseCredentials):
    """Credentials שמתחדשים מהגשר. googleapiclient קורא ל-refresh
    לבד כשהטוקן פג, כך שגם העלאה ארוכה ממשיכה."""

    def __init__(self, url, key):
        super().__init__()
        self._url = url
        self._key = key

    def refresh(self, request):
        # Apps Script עונה ב-302 ל-googleusercontent; requests ממשיך
        # אחרי ההפניה ב-GET, וזה בדיוק מה שהסקריפט מצפה לו.
        resp = requests.post(
            self._url,
            json={"action": "drive_token", "key": self._key},
            timeout=30,
        )
        try:
            data = resp.json()
        except ValueError:
            raise RuntimeError(
                "גשר הטוקנים לא החזיר JSON (HTTP %s) - כנראה שהקוד "
                "החדש עוד לא נפרס ל-Apps Script" % resp.status_code
            )
        if not data.get("success") or not data.get("token"):
            raise RuntimeError(
                "גשר הטוקנים סירב: %s" % (data.get("error") or data)
            )
        self.token = data["token"]
        self.expiry = datetime.datetime.utcnow() + datetime.timedelta(
            seconds=int(data.get("expiresIn") or 1800)
        )


def bridge_credentials(key):
    """Credentials מוכנים מהגשר, או None אם הגשר כבוי."""
    url = bridge_url()
    if not url:
        return None
    creds = AppsScriptDriveCredentials(url, key)
    creds.refresh(None)
    return creds
