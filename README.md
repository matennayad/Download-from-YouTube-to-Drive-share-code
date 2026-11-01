# מערכת הורדות לדרייב + חיפוש במייל — מדריך הקמה מלא

המערכת מורידה סרטונים ושמע מיוטיוב, ממאקו ומכאן 11 ישירות ל-Google Drive.
בנוסף היא שולחת במייל תוצאות חיפוש עם כפתורי "הורד". כל הקוד בחבילה נקי מפרטים
אישיים: כל מקום שצריך למלא בו ערך משלך מסומן ב-`YOUR_...` או `CHANGE_ME_...`.

> 🌐 **מדריך אינטראקטיבי:** פתחו את `guide.html` בדפדפן (לחיצה כפולה על הקובץ). ממלאים בו את הערכים
> שלכם, וכל קטעי הקוד מתעדכנים לבד, עם כפתורי העתקה, קישורים ישירים ואיורי הדגמה.

> 💡 **טיפ:** בקובץ `PROMPT_FOR_AI.md` יש פרומפט מוכן. מדביקים אותו לעוזר AI
> (למשל Claude) יחד עם הקבצים, והוא ילווה אותך צעד אחר צעד.

---

## 📦 מה יש בחבילה

| תיקייה | מה זה | חובה? |
|---|---|---|
| `download-service/` | שרת ההורדות (Python + yt-dlp), רץ על Railway | ✅ חובה |
| `apps-script/downloads/` | סקריפט מערכת ההורדות: טופס, מאושרים, מכסות, מיילים, Web App | ✅ חובה |
| `apps-script/unified-search/` | טופס חיפוש מאוחד (יוטיוב + מאקו + כאן), שולח תוצאות במייל | מומלץ |
| `search-service/` + `apps-script/youtube-search/` | חיפוש יוטיוב בלבד, כשירות נפרד וקטן (גרסה ישנה יותר של החיפוש) | אופציונלי |
| `userscripts/` | תוספי Tampermonkey: כפתור "הורד לדרייב" ביוטיוב, ושמירת תמונות מ-Gemini | אופציונלי |
| `proxy/` | הקמת פרוקסי ישראלי. **נדרש רק להורדות מכאן 11**, שחוסם שרתים מחו"ל | אופציונלי |
| `docs/` | מדריכים מפורטים לכל רכיב (API, ערוצים, טלגרם, לוח בקרה ועוד) | עיון |
| `.github/workflows/` | בדיקות אוטומטיות, וכפתור לשליחת בקשה ישירות מגיטהאב | אופציונלי |
| `tools/` | סקריפטי Node להעלאת קוד Apps Script דרך ה-API (למתקדמים, עם `APPS_SCRIPT_DIR=apps-script/...`) | אופציונלי |

### איך הכל מתחבר

```
משתמש ממלא טופס חיפוש ──► Apps Script (חיפוש) ──► השרת /search ──► מייל עם תוצאות
                                                                        │
                           לחיצה על "הורד" במייל ◄──────────────────────┘
                                     │
                                     ▼
                 טופס ההורדות (ממולא מראש) ──► Apps Script (הורדות)
                     בודק: מאושר? מכסה? כבר הורד בעבר?
                                     │
                                     ▼
                         השרת /download ב-Railway ──► Google Drive
                                     │
                                     ▼
                       מייל למשתמש עם קישור לקובץ
```

השרת לא מחזיק הרשאת Drive משלו. הוא מבקש טוקן מה-Web App של סקריפט ההורדות
(מנגנון "גשר הטוקנים" שב-`drive_bridge.py`), והקבצים נשמרים בדרייב של החשבון
שבו הסקריפט רץ. כך אין צורך ב-OAuth Client, ב-Secret או ב-Refresh Token.

---

## 🧰 מה צריך לפני שמתחילים

1. **חשבון Google**. זה החשבון שהקבצים יישמרו בדרייב שלו ושממנו יישלחו המיילים.
   עדיף חשבון ייעודי למערכת.
2. **חשבון GitHub** (חינמי).
3. **חשבון Railway** ב-[railway.com](https://railway.com). Railway הוא שירות בתשלום
   עם תקופת ניסיון; כדאי לבדוק באתר את המחיר העדכני.
4. **מפתח API**: מחרוזת אקראית ארוכה שתמציא בעצמך, למשל 32 אותיות ומספרים
   ממחולל סיסמאות. נקרא לה כאן **API_KEY**. אותו ערך בדיוק נכנס גם ל-Railway
   וגם לסקריפט ההורדות.
5. (מומלץ) **מפתח חיפוש** נוסף, מחרוזת אקראית אחרת בשם **UNIFIED_SEARCH_KEY**.
   הוא משמש את טופס החיפוש, כך שלא צריך לשים בו את המפתח הראשי.

> ⚠️ את המפתחות לא מעלים לגיטהאב ולא משתפים. אם מפתח דלף, מחליפים אותו בכל המקומות.

---

## שלב 1 — העלאת הקוד לגיטהאב

1. ב-GitHub: **New repository**. תן שם (למשל `yt-drive-system`) וסמן **Private** (מומלץ).
2. העלה את **כל** תוכן החבילה: **Add file → Upload files**, גרור את כל התיקיות,
   ואז **Commit**. אפשר גם עם git:

```bash
git init && git add . && git commit -m "initial" && git branch -M main
```

```bash
git remote add origin https://github.com/YOUR_GITHUB_USER/yt-drive-system.git
```

```bash
git push -u origin main
```

---

## שלב 2 — פתיחת שרת ההורדות ב-Railway

1. היכנס ל-Railway: **New Project → Deploy from GitHub repo**. אשר גישה לגיטהאב ובחר את הריפו.
2. לחץ על השירות שנוצר → **Settings**:
   - **Root Directory**: `download-service`. זה חשוב: כך Railway ימצא את ה-`Dockerfile`.
   - **Builder**: Dockerfile. Railway מזהה אותו לבד מתוך התיקייה.
3. **Settings → Networking → Generate Domain**. תתקבל כתובת כמו
   `https://xxxx.up.railway.app`, וזו **כתובת השרת** שלך. שמור אותה.
4. **Variables**: הוסף משתני סביבה. בשלב זה מספיקים שני הראשונים, ואת השלישי
   ממלאים בשלב 4:

| משתנה | ערך | חובה? |
|---|---|---|
| `API_KEY` | המפתח שהמצאת | ✅ |
| `UNIFIED_SEARCH_KEY` | מפתח החיפוש שהמצאת | מומלץ |
| `DRIVE_TOKEN_BRIDGE_URL` | כתובת ה-Web App (מסתיימת ב-`/exec`), מתקבלת בשלב 4 | ✅ |
| `DRIVE_FOLDER_ID` | מזהה תיקייה בדרייב שאליה יישמרו הקבצים (החלק שאחרי `folders/` בכתובת התיקייה) | אופציונלי |
| `KAN_PROXY_URL` | פרוקסי ישראלי להורדות מכאן 11, בפורמט `http://admin:סיסמה@IP:3128` (ראו `proxy/`) | רק לכאן |
| `YOUTUBE_COOKIES` | עוגיות יוטיוב, למקרה שיוטיוב חוסם. בדרך כלל לא נדרש, כי השרת מייצר PO Token לבד | אופציונלי |
| `GEMINI_API_KEY` | ליצירת תמונות דרך הבוט/התוסף (מ-aistudio.google.com) | אופציונלי |
| `TELEGRAM_*` | בוט טלגרם. ראו `docs/TELEGRAM_BOT_SETUP.md` | אופציונלי |

   רשימה מלאה עם הסברים נמצאת בקובץ `download-service/.env.example`.

5. Railway יבנה ויעלה את השרת. הבנייה הראשונה לוקחת כמה דקות.
6. **בדיקה:** פתח בדפדפן את כתובת השרת. אמורה להופיע תשובת JSON עם `"status": "ok"`.

> 🔒 **משתמשי NetFree:** בדרך כלל דומיינים של railway.app חסומים מהמחשב, וזה לא
> משנה, כי כל התקשורת עוברת דרך Apps Script שרץ בשרתי גוגל. לבדיקה ישירה אפשר
> להשתמש בכפתור שבגיטהאב (ראו "בונוס" בסוף), או בטלפון עם גלישה סלולרית.

---

## שלב 3 — טופס ההורדות + הגיליון

### 3א. יצירת הטופס

1. [forms.google.com](https://forms.google.com) → טופס ריק חדש. כותרת לדוגמה: "בקשת הורדה לדרייב".
2. **שאלה 1**: כותרת **`קישור`**, סוג: תשובה קצרה, חובה.
3. **שאלה 2**: כותרת **`סוג הורדה`**, סוג: בחירה מרובה (כפתורי רדיו), חובה. האפשרויות
   חייבות להיות כתובות **בדיוק** כך:
   - `וידאו`
   - `אודיו`
   - `וידאו ואודיו`
4. ⚙️ **הגדרות → תשובות → איסוף כתובות אימייל → "מאומתות"**. גוגל יוסיף את
   עמודת האימייל לבד.
   - אפשר במקום זה להוסיף שאלה שלישית בשם `כתובת אימייל`. הסקריפט מזהה את העמודות
     לפי הכותרות, אבל צריך להיות **בדיוק** 3 עמודות אחרי חותמת הזמן (B, C, D).
5. **תשובות → קישור לגיליון (Link to Sheets) → יצירת גיליון חדש**.

### 3ב. הכנת הגיליון

1. פתח את הגיליון שנוצר. הלשונית תיקרא **`תגובות לטופס 1`**. אם ממשק גוגל שלך באנגלית
   היא תיקרא `Form Responses 1`; במקרה כזה שנה את שמה ל-`תגובות לטופס 1`.
2. הוסף לשונית חדשה בשם **`מאושרים`**. אלה המשתמשים שמורשים להוריד:

| עמודה | כותרת (שורה 1) | מה כותבים |
|---|---|---|
| A | אימייל | כתובת המשתמש |
| B | מכסה | מספר הורדות כולל (יורד בכל הורדה), **או** `ללא הגבלה` |
| C | מכסה יומית | מספר הורדות ליום. משמש רק אם B ריק |
| D | שימוש היום | הסקריפט ממלא לבד |
| E | עדכון אחרון | הסקריפט ממלא לבד |

   מעמודה F והלאה הסקריפט מוסיף לבד עמודות סטטיסטיקה, ובנוסף: K = נטפרי (`פטור`),
   L = חסום (`כן`/`לא`), M = מכסה שעתית מותאמת לתוסף.

   **הוסף את עצמך** בשורה 2, עם `ללא הגבלה` בעמודה B.

3. את שאר הלשוניות (קבצים בדרייב, משתמשי תוסף, ערוצים, לוג ועוד) הסקריפט יוצר לבד.

### 3ג. מזהים שצריך לאסוף מהטופס

- **FORM_ID**: בעריכת הטופס, הכתובת היא `docs.google.com/forms/d/`**`המזהה`**`/edit`.
- **FORM_URL**: כפתור "שליחה" → 🔗 → קישור מקוצר (`forms.gle/...`).
- **כתובת מילוי מראש ומזהי entry** (בשביל כפתורי ההורדה במייל):
  ⋮ בטופס → **קבלת קישור ממולא מראש** → כתוב `AAA` בשדה הקישור ובחר `וידאו` →
  **קבלת קישור** → העתק. הקישור ייראה כך:
  `https://docs.google.com/forms/d/e/`**`1FAIpQL...`**`/viewform?usp=pp_url&`**`entry.111111`**`=AAA&`**`entry.222222`**`=וידאו`
  - כל מה שלפני `?` הוא `DOWNLOAD_FORM_BASE_URL`.
  - `entry.111111` הוא `DOWNLOAD_FORM_ENTRY_URL`, ו-`entry.222222` הוא `DOWNLOAD_FORM_ENTRY_TYPE`.
- **מזהה הגיליון** (`APPROVED_SHEET_ID`): בכתובת הגיליון, `docs.google.com/spreadsheets/d/`**`המזהה`**`/edit`.

---

## שלב 4 — סקריפט ההורדות + פריסת Web App

1. בגיליון: **תוספים (Extensions) → Apps Script**. נפתח פרויקט שמחובר לגיליון.
2. ⚙️ **Project Settings** → סמן ✓ **Show "appsscript.json" manifest file in editor**.
3. בעורך:
   - פתח את `Code.gs`, מחק את כל מה שיש בו, והדבק את `apps-script/downloads/Code.gs`.
   - ➕ → Script → קרא לקובץ `channels`, והדבק את `apps-script/downloads/channels.gs`.
   - פתח את `appsscript.json` והחלף בתוכן של `apps-script/downloads/appsscript.json`.
4. בראש `Code.gs` מלא:

```javascript
const RAILWAY_URL = "https://כתובת-השרת-שלך.up.railway.app/download";
const API_KEY = "המפתח שהמצאת";   // זהה ל-API_KEY ב-Railway
const FORM_ID = "המזהה מ-3ג";
const FORM_URL = "https://forms.gle/...";
```

   אפשר לשנות לפי הצורך גם את `DAILY_GLOBAL_LIMIT` (מכסה יומית כוללת, ברירת מחדל 200)
   ואת `DAILY_LIMIT_MESSAGE`.
   בדיקת חסימות נטפרי כבויה כברירת מחדל (`NETFREE_CHECK_BASE_URL` ריק). מדליקים אותה
   רק אם יש לך שירות בדיקה כזה.
5. שמור (Ctrl+S).
6. **אישור הרשאות:** בתפריט הפונקציות בחר **`__התקן_טריגר_סריקת_ערוצים`** → **Run** →
   **Review permissions** → בחר חשבון → "Google hasn't verified this app" → **Advanced** →
   **Go to ... (unsafe)** → **Allow**. זה הסקריפט שלך, ולכן זה בטוח.
   - הפעולה מתקינה טריגר שרץ כל 5 דקות, ומתקין לבד גם את טריגר בדיקת הטופס.
7. הרץ **`__עבד_בקשות_טופס_עכשיו`** פעם אחת, כדי לוודא שהכל רץ בלי שגיאות.
8. הרץ **`__אשר_הרשאת_שליחת_מייל`**, ואחריו **`__בדוק_שליחת_מייל`**.
   - המיילים נשלחים דרך Gmail API, וגיבוי דרך MailApp (100 ביום). אם הבדיקה מדווחת
     ש-Gmail API כבוי: Project Settings → **GCP Project → Change project** → חבר
     פרויקט GCP רגיל → ב-Cloud Console: **APIs & Services → Library → Gmail API → Enable**.
     בלי זה הכל עדיין עובד, רק עם מגבלה של 100 מיילים ביום.

### פריסה כ-Web App (חובה: הגשר לדרייב + התוספים)

9. **Deploy → New deployment** → ⚙️ **Web app**:
   - **Execute as**: `Me`
   - **Who has access**: `Anyone`
   - **Deploy** → אשר הרשאות → העתק את **Web app URL** (מסתיים ב-`/exec`).
10. ב-Railway → **Variables** → `DRIVE_TOKEN_BRIDGE_URL` = הכתובת הזו. Railway יעלה את השרת מחדש.
11. **בדיקה:** פתח `https://כתובת-השרת/?drive=1`. התשובה אמורה להראות שהגשר לדרייב תקין.

> 🔁 **חשוב לעדכונים עתידיים:** כשמשנים קוד בסקריפט, **Deploy → Manage deployments →
> ✏️ → Version: New version → Deploy**. כך הכתובת נשארת אותה כתובת. אם יוצרים
> "New deployment" חדש, הכתובת משתנה וצריך לעדכן אותה בכל המקומות.

### בדיקה מקצה לקצה

12. מלא את טופס ההורדות עם קישור ליוטיוב, מהמייל שהוספת ל"מאושרים". תוך עד 5 דקות
    הסטטוס יופיע בגיליון, יגיע מייל עם קישור, והקובץ יופיע בדרייב.

---

## שלב 5 — טופס החיפוש המאוחד (מומלץ)

המדריך המלא נמצא ב-`docs/UNIFIED_SEARCH_SETUP.md`. בקצרה:

1. צור טופס חדש עם שתי שאלות:
   - `מה לחפש?`: תשובה קצרה.
   - `איפה לחפש?`: תיבות סימון, עם האפשרויות `יוטיוב`, `מאקו`, `כאן 11`.

   בהגדרות: **איסוף כתובות אימייל מאומתות**.
2. בטופס: ⋮ → **Apps Script**. הדבק את `apps-script/unified-search/קוד.js`, החלף את
   `appsscript.json` בקובץ מהתיקייה, וצור קובץ HTML בשם `admin_dashboard` עם התוכן של
   `admin_dashboard.html`.
3. מלא בראש הקובץ:

```javascript
var FORM_ID = "מזהה טופס החיפוש";
var APPROVED_SHEET_ID = "מזהה הגיליון של מערכת ההורדות";   // מאותו גיליון מאושרים
var SEARCH_SERVER_URL = "https://כתובת-השרת/search";
var KAN_EPISODES_URL = "https://כתובת-השרת/episodes";
var DOWNLOAD_FORM_BASE_URL = "https://docs.google.com/forms/d/e/.../viewform";  // מ-3ג
var DOWNLOAD_FORM_ENTRY_URL = "entry.111111";
var DOWNLOAD_FORM_ENTRY_TYPE = "entry.222222";
```

   יש גם שדות אופציונליים למראה המייל: `LOGO_URL`, `CREDIT_NAME`, `PROFILE_URL`, `PROFILE_IMAGE_URL`.
4. **Project Settings → Script Properties → Add**: `API_KEY` = הערך של `UNIFIED_SEARCH_KEY`
   (או של `API_KEY`).
5. הרץ לפי הסדר: `checkSetup` → `checkGmailApi` → `fixTriggers` → `testSearchAndEmail`.
6. לוח בקרה למנהל: ראו `docs/DASHBOARD_AND_EMAIL_COMMANDS.md`. הוא דורש פריסת Web App גם לפרויקט הזה.

---

## שלב 6 — חיפוש יוטיוב כשירות נפרד (אופציונלי)

זו גרסה קלה וישנה יותר: שרת קטן שמחפש רק ביוטיוב. מי שהקים את שלב 5 לא צריך אותה.

1. Railway → בפרויקט הקיים: **New → GitHub Repo** (אותו ריפו) → **Root Directory** = `search-service`
   → Variables: `API_KEY` = מפתח (יכול להיות מפתח נפרד) → Generate Domain.
2. טופס עם שאלת טקסט אחת לחיפוש, ואיסוף אימיילים מאומתים → ⋮ → Apps Script → הדבק את
   `apps-script/youtube-search/קוד.js` + `appsscript.json`.
3. מלא את `SEARCH_SERVER_URL`, `FORM_ID`, ואת פרטי טופס ההורדות (כמו בשלב 5).
   `APPROVED_SHEET_ID` הוא גיליון שבלשונית הראשונה שלו, בעמודה A, רשימת המיילים המאושרים.
4. Script Properties: `API_KEY`. אחר כך הרץ `checkSetup` → `fixTriggers` → `testSearchAndEmail`.

---

## שלב 7 — תוספי דפדפן (אופציונלי)

1. התקן את התוסף **Tampermonkey** בדפדפן.
2. Tampermonkey → **Create a new script** → מחק הכל → הדבק את
   `userscripts/Download from YouTube to Drive.user.js`.
3. בראש הקובץ מלא את `WEB_APP_URL` (הכתובת משלב 4, שמסתיימת ב-`/exec`). אפשר גם למלא
   את `ADMIN_EMAIL`, ולהחליף את תמונות הכפתורים (`BTN_..._IMG`) בקישור לתמונה משלך.
4. שמור. ביוטיוב יופיע כפתור Drive. משתמש שמופיע ב"מאושרים" עובד בלי אימות.
   משתמש אחר מקבל למייל קוד אימות בן 6 ספרות, ומנוהל בלשונית "משתמשי תוסף"
   (מכסה שעתית, חסימה וכו').
5. באותו אופן: `Gemini Images to Drive.user.js`. ראו `docs/GEMINI_IMAGES_SETUP.md`.

---

## שלב 8 — תוספות (אופציונלי)

| רכיב | מדריך |
|---|---|
| פרוקסי ישראלי לכאן 11 | `docs/IL_PROXY_GUIDE.md`, `proxy/proxy-vps/README.md`, `proxy/proxy-home/README.md` |
| הורדת ערוצים שלמים | `docs/CHANNELS.md` |
| בוט טלגרם (הורדות + הקלטת שידור חי) | `docs/TELEGRAM_BOT_SETUP.md` |
| שירים מערוץ טלגרם לדרייב | `docs/TELEGRAM_CHANNEL_SETUP.md`, `docs/TELEGRAM_SONGS_SETUP.md` |
| לוח בקרה + פקודות במייל | `docs/DASHBOARD_AND_EMAIL_COMMANDS.md` |
| כל נקודות הקצה של השרת | `docs/API_GUIDE.md` |

> במדריכים שבתיקיית `docs/` יש כתובות לדוגמה כמו `YOUR-DOWNLOAD-SERVICE.up.railway.app`.
> מחליפים אותן בכתובות שלך.

---

## 🎁 בונוס — שליחת בקשה ישירות מגיטהאב

ב-GitHub → הריפו → **Settings → Secrets and variables → Actions → New repository secret**:
- `API_KEY`: המפתח.
- `DOWNLOAD_SERVICE_URL`: כתובת השרת, בלי `/` בסוף.

אחר כך: **Actions → Send download request → Run workflow**. זה עובד גם מאחורי NetFree,
כי הבקשה יוצאת מהשרתים של גיטהאב.

---

## ✅ רשימת "חפש והחלף" — כל המקומות שממלאים

| ערך | איפה |
|---|---|
| כתובת השרת ב-Railway | `Code.gs` (`RAILWAY_URL`), `unified-search/קוד.js` (`SEARCH_SERVER_URL`, `KAN_EPISODES_URL`) |
| `API_KEY` | Railway, `Code.gs` |
| `UNIFIED_SEARCH_KEY` | Railway, Script Properties של טופס החיפוש |
| `FORM_ID` / `FORM_URL` של טופס ההורדות | `Code.gs` |
| כתובת המילוי מראש + 2 מזהי entry | `unified-search/קוד.js`, `youtube-search/קוד.js` |
| מזהה גיליון ההורדות | `unified-search/קוד.js` (`APPROVED_SHEET_ID`), ובטלגרם: משתנה `APPROVED_SHEET_ID` |
| כתובת ה-Web App (`/exec`) | Railway (`DRIVE_TOKEN_BRIDGE_URL`), שני התוספים (`WEB_APP_URL`) |

כדי לבדוק שלא נשאר שום ערך למילוי, אפשר לחפש בכל הקבצים את המחרוזות
`YOUR_`, `YOUR-` ו-`CHANGE_ME`.

---

## 🩺 פתרון בעיות נפוצות

| תקלה | מה בודקים |
|---|---|
| `unauthorized` מהשרת | `API_KEY` ב-Railway וב-`Code.gs` חייבים להיות זהים, בלי רווחים |
| הורדה נכשלת בשגיאת דרייב / `invalid_grant` | `DRIVE_TOKEN_BRIDGE_URL` נכון? ה-Web App פרוס עם "Anyone"? בדוק `/?drive=1` |
| הטופס לא מעובד | הלשוניות נקראות בדיוק `תגובות לטופס 1` ו-`מאושרים`? הרץ `__הצג_טריגרים_פעילים` |
| "לא מאושר" | המייל בטופס זהה למה שכתוב בעמודה A של `מאושרים`? יש מכסה בעמודה B או C? |
| מיילים לא מגיעים | `__בדוק_שליחת_מייל`, ובדוק גם בספאם. מכסת MailApp היא 100 ביום |
| כאן 11 נכשל | חובה פרוקסי ישראלי (`KAN_PROXY_URL`) |
| יוטיוב: "Sign in to confirm you're not a bot" | השרת מייצר PO Token לבד. אם התקלה חוזרת, הגדר `YOUTUBE_COOKIES` |
| שינוי בסקריפט לא נכנס לתוקף בתוסף | Manage deployments → New version (ראו שלב 4) |
| לוגים של השרת | Railway → השירות → **Deployments → View logs** |
