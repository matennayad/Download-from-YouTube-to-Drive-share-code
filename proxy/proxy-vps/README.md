# הקמת פרוקסי ישראלי על VPS (10 דקות)

זה הפתרון האמין: שרת קטן בישראל שרץ 24/7, לא תלוי במחשב שלך ולא ב-NetFree.
מי שיבקש הורדה — תמיד יעבוד.

## שלב 1: קניית ה-VPS (5-10$ לחודש)

אפשרויות ישראליות (נכון ל-09/2026):

| ספק | מחיר מתחיל | הערה |
|---|---|---|
| [omc.cloud](https://omc.cloud/products/vps/he) | **$4/חודש** | 25 מיקומים, 30 יום ניסיון חינם, תמיכה 24/7 |
| [DNSCloud](https://www.dnscloud.co.il/vps_cloud_linux.php) | **15₪/חודש** | הזול ביותר, לינוקס SSD |
| [LiveDNS](https://www.livedns.co.il/cloud) | 50₪/חודש | ענן מאובטח ישראלי מבוסס |
| [ClubVPS](https://il.clubvps.com/) | חודש ניסיון חינם | ישראלי, ללא התחייבות |

**מה לבחור בהזמנה:**
- מיקום: **ישראל** (חובה!)
- מערכת הפעלה: **Ubuntu 22.04 / 24.04**
- מפרט: 1 ליבה, 1GB RAM, 10GB דיסק — בשפע
- בסוף ההזמנה תקבל במייל: **IP ציבורי + סיסמת root** (או SSH key)

## שלב 2: התחברות לשרת

מ-Windows: פתח PowerShell (או הורד את [PuTTY](https://www.putty.org/)):

```powershell
ssh root@כתובת_הIP_מהמייל
```

הזן את הסיסמה מהמייל. עכשיו אתה בתוך השרת הישראלי.

## שלב 3: התקנת הפרוקסי (שורה אחת!)

```bash
bash <(curl -s https://raw.githubusercontent.com/YOUR_GITHUB_USER/YOUR_REPO/main/proxy/proxy-vps/setup.sh) "הסיסמה_שתבחר"
```

הסקריפט יתקין Squid, יגדיר משתמש+סיסמה, ויפעיל הכל אוטומטית.

> **שים לב:** הסיסמה בשורה מופיעה בהיסטוריית השרת. אחרי שהכל עובד אפשר
> למחוק אותה: `history -c`

## שלב 4: פתיחת הפורט בחומת האש

**א. בלוח הבקרה של ספק ה-VPS** — מצא "Firewall" ופתח פורט:
- TCP **3128** (HTTP proxy) — חובה
- TCP **22** (SSH) — בדרך כלל כבר פתוח

**ב. על השרת עצמו** (אם יש ufw):

```bash
ufw allow 3128/tcp
ufw status
```

## שלב 5: בדיקה על השרת

```bash
bash <(curl -s https://raw.githubusercontent.com/YOUR_GITHUB_USER/YOUR_REPO/main/proxy/proxy-vps/test.sh) "הסיסמה"
```

**מצופה:**
1. IP ישראלי מוצג (מתחיל ב-8x / 31. / 82. / 84. / 87. / 89.)
2. `HTTP: 200` מאתר כאן
3. `HTTP: 200` (או 302) מה-CDN → **✅ הפרוקסי עובד מלא!**

## שלב 6: חיבור ל-Railway

1. היכנס ל-Railway → הפרויקט שלך → **Variables**
2. הוסף משתנה:

```
KAN_PROXY_URL = http://admin:הסיסמה@כתובת_הIP_של_הVPS:3128
```

3. Railway יפעיל מחדש אוטומטית (redeploy)

## שלב 7: הבדיקה הסופית 🎉

בגיטהאב: **Actions → Test KAN Series Download → Run workflow**

- target: `railway`
- mode: `download`
- kan_url: `https://www.kan.org.il/content/kan/kan-11/p-11843/s8/756427/`

הפרק צריך לרדת ולהיות מועלה לדרייב. אם עבר — גם עונה שלמה תעבוד.

## אחזקה (מינימלית)

| מתי | מה |
|---|---|
| כלום קורה | השרת רץ לבד, אין מה לתחזק |
| עדכון אבטחה | `apt update && apt upgrade -y` אחת לחודש-שניים |
| לשנות סיסמה | `htpasswd -cb /etc/squid/passwd admin "סיסמה_חדשה" && systemctl restart squid` ועדכן ב-Railway |

## פתרון בעיות

| בעיה | פתרון |
|---|---|
| `HTTP: 407` מהשרת | סיסמה שגויה ב-`KAN_PROXY_URL` — תווים מיוחדים צריכים קידוד URL (`@` → `%40`, `!` → `%21`) |
| פורט סגור מבחוץ | חומת האש של הספק — רק פתיחה משם תפתור |
| כאן מחזיר 403 | ה-IP של ה-VPS מזוהה כענן — פנה לספק על "IP residential" או נסה ספק אחר (נדיר אצל ספקים ישראליים קטנים) |
| Railway עדיין לא מוריד | ודא שהמשתנה בשם המדויק `KAN_PROXY_URL` ושה-redeploy בוצע |
| הכל עבד ופתאום נעצר | בדוק שה-VPS דלוק ושהסיסמה לא השתנתה: `systemctl status squid` |

## עלות סופית

- VPS: **4-15$/חודש** (החל מ-30 יום חינם ב-omc.cloud / ClubVPS)
- Railway: ללא שינוי (הפרוקסי לא מוסיף תעבורה ל-Railway — הווידאו זורם מה-CDN ישירות בתוך ה-VPS? לא: הווידאו זורם דרך ה-VPS ל-Railway ומשם לדרייב, אז שקול תעבורה ב-VPS — 1TB חודשי מספיק לכ-30-50 פרקים ב-1080p)
