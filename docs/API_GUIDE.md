# 📖 מדריך API — yt-download-service

מדריך מלא לשליחת בקשות לשירות ההורדות, כולל דרכים מעשיות לשליחה מהמחשב/טלפון.

---

## 🌐 כתובות השרתים

| שרת | כתובת |
|---|---|
| **Railway** (ראשי) | `https://YOUR-DOWNLOAD-SERVICE.up.railway.app` |
| **Render** (גיבוי) | `https://YOUR-BACKUP-SERVICE.onrender.com` |

בדוגמאות במדריך אשתמש בכתובת Railway. אפשר להחליף ל-Render בכל עת.

---

## 🔑 אימות (Authorization)

כל ה-endpoints הרגישים דורשים **Header**:

```
X-API-KEY: <ה-API_KEY שלך>
```

המפתח מוגדר כמשתנה סביבה `API_KEY` בלוחות של Railway ו-Render (Variables).
לצפייה: Railway → הפרויקט שלך → השירות → Variables.

חריגים שלא דורשים מפתח:
- `GET /` (בדיקת תקינות)
- `GET /job/<jobId>` (מעקב אחרי עבודה)

Endpoint אחד (`/direct`) משתמש במפתח **נפרד** — `DIRECT_API_KEY` (ראו למטה).

---

## 📡 רשימת ה-endpoints

| Endpoint | Method | מטרה |
|---|---|---|
| `/` | GET | בדיקת תקינות |
| `/episodes` | POST | רשימת פרקים של סדרה/עונה (מכאן או מאקו) |
| `/formats` | POST | אבחון: אילו איכויות זמינות לקישור |
| `/download` | POST | הורדה — פרק בודד או עונה שלמה |
| `/job/<jobId>` | GET | מעקב אחרי עבודה רצה |
| `/job/<jobId>/cancel` | POST | ביטול עבודה |
| `/tampermonkey-download` | POST | הורדה מהירה (מיועד לסקריפט דפדפן) |
| `/channel/preview` | POST | תצוגה מקדימה של ערוץ יוטיוב |
| `/channel/download` | POST | הורדת ערוץ יוטיוב שלם |
| `/direct` | POST | הורדה ישירה עם מפתח נפרד (DIRECT_API_KEY) |
| `/gemini-image` | POST | העלאת תמונת גמיני לדרייב (base64 או URL) |
| `/diag/kan` | POST/GET | אבחון שרשרת כאן (פרוקסי, ערוצים) |

---

# 🚀 איך תכלס שולחים בקשות?

## ⚠️ המצב האמיתי: NetFree חוסם את השרתים מהמחשב שלך

NetFree מסווג את הדומיינים של Railway/Render כ"unknown" וחוסם אותם.
כלומר: **Postman, curl, ודפדפן מהמחשב שלך לא יגיעו לשרת.**
בדקנו ואושר: Railway מחזיר 418 (חסימת NetFree), Render לא מתקבל כלל.

לכן הנה הדרכים שעובדות בפועל, מהטובה לשאר:

---

## ✅ דרך 1 (מומלצת): כפתור בגיטהאב — עובד תמיד, גם עם NetFree

בריפו יש workflow בשם **"Send download request"** שמאפשר לשלוח כל בקשה
בלחיצת כפתור — הרץ של גיטהאב שולח אותה מרשת נקייה:

1. פתח: `https://github.com/YOUR_GITHUB_USER/YOUR_REPO/actions/workflows/send-request.yml`
   (פעם אחת לפני כן: Settings → Secrets and variables → Actions → הוסף `API_KEY` ו-`DOWNLOAD_SERVICE_URL`)
2. לחץ על **"Run workflow"** (כפתור ירוק מימין למעלה)
3. מלא את השדות:

| שדה | מה לבחור |
|---|---|
| **action** | `download` (הורדה) / `episodes` (רשימת פרקים) / `health` (בדיקה) |
| **url** | הקישור להורדה (פרק/עונה/סרטון) |
| **format** | `video` או `audio` |
| **episode** | ריק = כל העונה. מזהה פרק (כמו `756427`) = פרק בודד |

4. לחץ **Run workflow** — ותרד רגע למטה לרשימת הריצות
5. לחץ על הריצה החדשה → תראה התקדמות חיה (מה שהורד, כמה הועלה)
6. **בסוף יופיעו קישורי הדרייב בלוג, מסומנים ב-`🔗`**

יתרונות: עובד מכל מקום (גם מהטלפון), NetFree לא מפריע, והתוצאות נשמרות בלוג.

---

## ✅ דרך 2: מהטלפון עם אינטרנט סלולרי

NetFree פועל רק על הרשת שלך (WiFi). סלולרי = רשת נקייה.

- פתח בדפדפן בטלפון (בסלולרי, לא WiFi) את `https://YOUR-DOWNLOAD-SERVICE.up.railway.app`
  — אם מופיע JSON עם `"status": "ok"` — הכל פתוח.
- שליחת POST מהטלפון: אפליקציית **HTTP Shortcuts** (אנדרואיד) או קיצורי-דרך
  של iOS עם פעולת "קבל תוכן מ-URL" (מתודה POST, כותרת X-API-KEY).

---

## ✅ דרך 3: לבקש מ-NetFree לפתוח את השרת (פעם אחת)

פתח בקשת פתיחת אתר ב-NetFree (netfree.link → פנייה/בקשת פתיחה) ובקש
להסיר חסימה משני הדומיינים:

```
YOUR-DOWNLOAD-SERVICE.up.railway.app
YOUR-BACKUP-SERVICE.onrender.com
```

אם יאשרו — **הכל נפתח מהמחשב**: תוכל להשתמש ב-Postman, בדפדפן, ב-curl,
ואף לבנות ממשק אינטרנטי רגיל. זו הדרך הנוחה ביותר לטווח ארוך.

---

## דרך 4: curl מסביבה נקייה

מכל מחשב בלי NetFree (עבודה, חבר, VPS):

```bash
# בדיקת תקינות
curl https://YOUR-DOWNLOAD-SERVICE.up.railway.app/

# רשימת פרקים
curl -X POST "https://YOUR-DOWNLOAD-SERVICE.up.railway.app/episodes" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: ה-API_KEY שלך" \
  -d '{"url": "https://www.kan.org.il/content/kan/kan-11/p-11843/s8/"}'
```

---

# 📚 דוגמאות מלאות לכל סוג הורדה

## 1️⃣ כאן (kan.org.il) — עונה שלמה

```bash
curl -X POST "https://YOUR-DOWNLOAD-SERVICE.up.railway.app/download" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: ה-API_KEY שלך" \
  -d '{
    "url": "https://www.kan.org.il/content/kan/kan-11/p-11843/s8/",
    "format": "video",
    "all_episodes": true
  }'
```

תשובה:
```json
{
  "success": true,
  "kind": "season",
  "jobId": "92fa7347773d",
  "total": 13,
  "progressUrl": "/job/92fa7347773d"
}
```

## 2️⃣ כאן — פרק בודד

שלחו קישור עונה + מזהה פרק (המספר בסוף כתובת הפרק):

```bash
curl -X POST "https://YOUR-DOWNLOAD-SERVICE.up.railway.app/download" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: ה-API_KEY שלך" \
  -d '{
    "url": "https://www.kan.org.il/content/kan/kan-11/p-11843/s8/",
    "episode": 756427,
    "format": "video",
    "all_episodes": true
  }'
```

או פשוט שלחו את כתובת הפרק ישירות:
`"url": "https://www.kan.org.il/content/kan/kan-11/p-11843/s8/756427/"`

> 💡 `episode` מקבל: מזהה מה-URL (≥10000, כמו 756427) או מספר סידורי (1-999, "פרק 5").
> `all_episodes: true` = הורדה ברקע עם jobId מיד (מומלץ! בלי זה ההורדה
> סינכרונית ועלולה להתנתק אחרי 5 דקות).

## 3️⃣ מעקב אחרי עבודה (בלי מפתח!)

```bash
curl "https://YOUR-DOWNLOAD-SERVICE.up.railway.app/job/92fa7347773d"
```

תשובה בסיום:
```json
{
  "status": "done",
  "done": 1,
  "failed": 0,
  "percent": 100,
  "folderLink": "https://drive.google.com/drive/folders/...",
  "items": [
    {
      "status": "ok",
      "title": "פרק 756427",
      "driveLink": "https://drive.google.com/file/d/.../view"
    }
  ]
}
```

ביטול: `curl -X POST .../job/<jobId>/cancel`

## 4️⃣ מאקו — פרק בודד

```bash
curl -X POST "https://YOUR-DOWNLOAD-SERVICE.up.railway.app/download" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: ה-API_KEY שלך" \
  -d '{
    "url": "https://www.mako.co.il/tv-vod/.../vod-XXXX.html",
    "format": "video"
  }'
```

## 5️⃣ מאקו — עונה שלמה

```bash
curl -X POST "https://YOUR-DOWNLOAD-SERVICE.up.railway.app/download" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: ה-API_KEY שלך" \
  -d '{
    "url": "https://www.mako.co.il/tv-vod-.../שם-הסדרה",
    "season": 1,
    "all_episodes": true
  }'
```

(חייב עמוד סדרה של מאקו + מספר עונה)

## 6️⃣ יוטיוב / אינסטגרם / טיקטוק

```bash
curl -X POST "https://YOUR-DOWNLOAD-SERVICE.up.railway.app/download" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: ה-API_KEY שלך" \
  -d '{"url": "https://www.youtube.com/watch?v=XXXX", "format": "audio"}'
```

## 7️⃣ ערוץ יוטיוב שלם

```bash
# תצוגה מקדימה
curl -X POST ".../channel/preview" -H "X-API-KEY: ..." \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/@channel"}'

# הורדה
curl -X POST ".../channel/download" -H "X-API-KEY: ..." \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/@channel", "format": "audio"}'
```

## 8️⃣ /direct — מפתח נפרד

```bash
curl -X POST ".../direct" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: ה-DIRECT_API_KEY שלך" \
  -d '{"url": "...", "format": "audio"}'
```

---

## 9️⃣ /gemini-image — תמונות גמיני לדרייב

מקבל תמונה (base64 או כתובת פומבית), מעלה אותה לתיקיית "תמונות גמיני"
בדרייב (נוצרת אוטומטית), ומחזיר קישור. התוסף ל-gemini.google.com שולח
מכאן כל תמונה שגמיני יוצר, דרך ה-Apps Script (אימות מכשיר + מכסה שעתית
של 10 תמונות למשתמש).

```bash
curl -X POST ".../gemini-image" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: ה-API_KEY שלך" \
  -d '{
    "email": "user@gmail.com",
    "prompt": "ציור של חתול אסטרונאוט",
    "image": "data:image/png;base64,iVBORw0KGgo..."
  }'
```

תשובה:
```json
{
  "success": true,
  "title": "גמיני - ציור של חתול אסטרונאוט - 2026-09-30 14-22-05.png",
  "driveLink": "https://drive.google.com/file/d/.../view",
  "fileId": "..."
}
```

- במקום `image` אפשר לשלוח `image_url` (https בלבד) והשרת ישלוף בעצמו.
- תקרת גודל: 20MB (ניתנת לשינוי עם `GEMINI_IMAGE_MAX_BYTES`).
- בלי `parent_id`: הקובץ נכנס לתיקיית "תמונות גמיני" בשורש הדרייב.

---

# 🧪 Python (מסביבה נקייה)

```python
import requests, time

BASE = "https://YOUR-DOWNLOAD-SERVICE.up.railway.app"
KEY = "ה-API_KEY שלך"

# פתיחת עבודה — עונת כאן
r = requests.post(f"{BASE}/download",
    headers={"X-API-KEY": KEY},
    json={"url": "https://www.kan.org.il/content/kan/kan-11/p-11843/s8/",
          "format": "video", "all_episodes": True})
job_id = r.json()["jobId"]
print("job:", job_id)

# מעקב עד לסיום
while True:
    d = requests.get(f"{BASE}/job/{job_id}").json()
    print(f"[{d['status']}] {d.get('processed',0)}/{d['total']}")
    if d["status"] in ("done", "error", "cancelled"):
        for item in d["items"]:
            print(item["title"], "->", item["driveLink"])
        print("תיקייה:", d["folderLink"])
        break
    time.sleep(20)
```

---

# ❓ פתרון בעיות

| תופעה | סיבה | פתרון |
|---|---|---|
| 418 / עמוד NetFree | ניגשת מהמחשב דרך NetFree | השתמש בדרך 1 (גיטהאב) או 2 (סלולרי) |
| 401 unauthorized | מפתח שגוי/חסר | בדוק את X-API-KEY מול Variables ב-Railway |
| 502 בהורדה סינכרונית | ההורדה ארכה מעל 5 דקות | שלח עם `all_episodes: true` (עבודת רקע) |
| "שליפת עמוד כאן נכשלה" | הפרוקסי הישראלי כבוי | בדוק שה-VPS דלוק ב-omc.cloud |
| עבודה תקועה על running | עדיין מוריד/מעלה | סבלנות — פרק וידאו לוקח 3-8 דקות |

**אבחון עצמי של שרשרת כאן:**
```bash
curl -X POST ".../diag/kan" -H "X-API-KEY: ..." -d '{}'
```
