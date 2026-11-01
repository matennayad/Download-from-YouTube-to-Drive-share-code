# מדריך: פרוקסי ישראלי להורדות כאן (kan.org.il)

## למה זה נדרש

בדיקות מ-24/09/2026 אישרו:

| מה | סטטוס |
|---|---|
| אתר kan.org.il | חוסם IP לא-ישראלי של עננים (Railway/Render נחסמים) |
| CDN הווידאו (cdn-redge.media) | חוסם חו"ל לגמרי — גם הסטרים עצמם |
| Kaltura API | חסמה את השותף של כאן עבור yt-dlp (גלובלי, גם מישראל) |
| Wayback Machine | עובד לגילוי פרקים (מחסיר פרקים שלא נארכו) |
| פרוקסים חינמיים | 15 מתוך 15 מתים — לא קיימים בפועל ברשימות הציבוריות |

**המסקנה:** גם גילוי הפרקים וגם הורדת הווידאו דורשים IP ישראלי אמיתי.
השירות כבר בנוי במלואו לעבוד עם פרוקסי — צריך רק לספק אחד.

## פתרון 1: מחשב ביתי כפרוקסי (חינם)

כל מחשב/סטיק עם אינטרנט ביתי רגיל (בלי NetFree) בישראל יכול לשמש כפרוקסי.

### על המחשב הביתי (Windows)

1. הורד את [3proxy](https://github.com/3proxy/3proxy/releases) (קובץ zip קטן, ללא התקנה)
2. צור קובץ `3proxy.cfg` ליד ההרצה:

```
nscache 65536
nserver 8.8.8.8
auth strong
users admin:CL:סיסמא_חזקה_כאן
allow admin
proxy -p3128
```

3. הרץ: `3proxy.exe 3proxy.cfg`
4. פתח את הפורט בנתב: הפניית פורט (Port Forwarding) של פורט **3128** למחשב הזה
5. בדוק את ה-IP הציבורי שלך: חפש "what is my ip" בגוגל

### על המחשב הביתי (Linux / Raspberry Pi)

```bash
sudo apt install tinyproxy -y
sudo nano /etc/tinyproxy/tinyproxy.conf
# הגדר: Port 3128
# הגדר: BasicAuth admin סיסמא_חזקה_כאן
sudo systemctl restart tinyproxy
```

ופתח את פורט 3128 בנתב.

### על Railway

הגדר משתנה סביבה אחד:

```
KAN_PROXY_URL = http://admin:סיסמא@כתובת_ה-IP_הציבורי:3128
```

**חסרון:** אם ה-IP הביתי מתחלף (דינמי), צריך לעדכן את Railway.
פתרון: דומיין חינמי דרך [No-IP](https://www.noip.com/) או DuckDNS — כתובת קבועה שמתעדכנת אוטומטית:

```
KAN_PROXY_URL = http://admin:סיסמא@הדומיין-שלי.ddns.net:3128
```

**חשוב:** המחשב חייב להיות דלוק כדי שההורדות יעבדו. Raspberry Pi מתאים לעבודה סגירה 24/7.

## פתרון 2: VPS ישראלי (5-10$ לחודש)

ספקים עם נוכחות בישראל: InterHost, ServerNet, HostCast, או שרת ביתי ב-Bezeq/HOT דרך ספקי VPS מקומיים.

1. קנה VPS קטן (1 ליבה, 1GB RAM מספיק)
2. התקן Squid כפרוקסי:

```bash
sudo apt install squid apache2-utils -y
sudo htpasswd -c /etc/squid/passwd admin
sudo tee -a /etc/squid/squid.conf <<'EOF'
auth_param basic program /usr/lib/squid/basic_ncsa_auth /etc/squid/passwd
auth_param basic realm Proxy
acl authenticated proxy_auth REQUIRED
http_access allow authenticated
http_access deny all
http_port 3128
EOF
sudo systemctl restart squid
```

3. פתח את פורט 3128 בחומת האש של הספק
4. הגדר ב-Railway:

```
KAN_PROXY_URL = http://admin:סיסמא@כתובת_הVPS:3128
```

## אימות שהפרוקסי עובד

אחרי ההגדרה, הרץ מהריפו: **Actions → Send download request → Run workflow** (action = episodes, עם קישור לעונה של כאן)
(בחר railway, mode=download, קישור עונה/פרק מכאן).

או בדוק ידנית מהמחשב של הפרוקסי:

```bash
curl -x http://admin:סיסמא@localhost:3128 https://www.kan.org.il/ -o /dev/null -w "%{http_code}\n"
# אמור להדפיס 200
```

## איך השירות משתמש בפרוקסי

| מה | דרך מי |
|---|---|
| שליפת עמודי פרקים | הפרוקסי (ערוץ 2 בשרשרת, אחרי ניסיון ישיר) |
| הורדת הווידאו עצמה | הפרוקסי דרך yt-dlp (מאז 24/09/2026) |
| גילוי פרקים | Wayback Machine כשהפרוקסי לא זמין |
| r.jina.ai | fallback אחרון לעמודים |

## סיכום הארכיטקטורה

```
משתמש → Apps Script → Railway (חו"ל)
                        ↓
             גילוי פרקים: Wayback/Jina (עובד מחו"ל)
                        ↓
             הורדת וידאו: → פרוקסי IL → CDN של כאן → דרייב
```
