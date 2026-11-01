// ===================== הגדרות =====================

const RAILWAY_URL =
  "https://YOUR-DOWNLOAD-SERVICE.up.railway.app/download";

const API_KEY = "CHANGE_ME_API_KEY"; // אותו ערך כמו API_KEY ב-Railway

// ===================== אינטגרציה עם מייל החיפוש =====================
// כפתורי "הורד וידאו/אודיו" במייל תוצאות החיפוש פותחים את הטופס הזה
// עם הכל ממולא מראש (קישור + סוג הורדה), והמייל נרשם אוטומטית על ידי
// גוגל כשהטופס מוגש. ההורדה עצמה עוברת כאן את כל הבדיקות הרגילות
// של הטופס: מאושרים, מכסות, נטפרי ומטמון — שום דבר לא עוקף אותן.
//
// זיהוי בקשות מהמייל: הסקריפט החיפוש מטמיע סימון "&via=email-search"
// בתוך הכתובת עצמה. מתודה זו אמינה כי היא עוברת דרך עמודת הקישור
// בגיליון, בלי תלות בעמודת המקור של גוגל.
//
// הגנת כפילויות: לחיצה כפולה על הכפתור (או רענון לאחר שליחה) עלולה
// לשלוח את אותה תשובה פעמיים, וכל תשובה היא הורדה. לכן שומרים כאן
// טביעת עין של כל בקשה מהמייל, ומי שזהה לאחרונה — מדולג עם הודעה.
const EMAILDL_SOURCE_MARKER = "via=email-search";
const EMAILDL_TOKEN_REUSE_WINDOW_MIN = 30;

const FORM_ID =
  "YOUR_DOWNLOAD_FORM_ID";

const FORM_URL =
  "https://forms.gle/YOUR_DOWNLOAD_FORM_SHORT_LINK";

const RESPONSES_SHEET_NAME =
  "תגובות לטופס 1";

const APPROVED_SHEET_NAME =
  "מאושרים";

// כתובת שירות בדיקת NetFree (אופציונלי - שירות חיצוני, אם יש לך גישה לכזה).
// השירות מקבל מזהה סרטון בסוף הכתובת ומחזיר מילה אחת: OPEN / LOCK / PENDING
// להשאיר ריק אם אין שירות כזה - ואז שני המתגים למטה חייבים להיות false.
const NETFREE_CHECK_BASE_URL =
  "";


// שני מתגים שקובעים על מי חלה בדיקת חסימת הנטפרי.
// הטופס מטופל ב-checkFormResponses והתוסף ב-doPost, שני מסלולים
// נפרדים לגמרי, ולכן לא נדרש שום סימן בגיליון כדי להבדיל ביניהם.

// בקשות שמגיעות מהטופס
const NETFREE_CHECK_FOR_FORM = false;

// בקשות שמגיעות מהתוסף
// (כבוי כברירת מחדל כי אין כתובת שירות. להדליק רק אחרי שממלאים NETFREE_CHECK_BASE_URL)
const NETFREE_CHECK_FOR_EXTENSION = false;


// עמודת "נטפרי" הפכה מרשימת "את מי לבדוק" לרשימת "מי פטור".
// ברירת המחדל היא לבדוק את כולם, ומי שכתובה אצלו המילה הזו
// מדלג על הבדיקה.
//
// המילה היא "פטור" ולא "לא" בכוונה: אם בעמודה כבר כתוב "לא"
// בשורות קיימות, מילת פטור כזו הייתה פותחת את כולן בבת אחת.
// כך ברירת המחדל נשארת תמיד הכיוון הבטוח - בדיקה.
//
// תקף בשני מקומות: עמודה 11 ב"מאושרים", ועמודה 8 ב"משתמשי תוסף".
const NETFREE_EXEMPT_WORD = "פטור";


// ===================== מכסה יומית גלובלית =====================

const DAILY_GLOBAL_LIMIT = 200;


// ===================== הודעת מכסה =====================

const DAILY_LIMIT_MESSAGE =
  "המערכת הגיעה למכסה היומית של 200 קבצים.\n\n" +
  "לא ניתן לשלוח בקשות נוספות היום.\n\n" +
  "ניתן לנסות שוב לאחר חצות.";


// ===================== מפתחות שמירה =====================

const GLOBAL_COUNT_KEY =
  "GLOBAL_DAILY_DOWNLOAD_COUNT";

const GLOBAL_DATE_KEY =
  "GLOBAL_DAILY_DOWNLOAD_DATE";


// ===================== מטמון קבצים בדרייב =====================
// כל קובץ שירד נרשם כאן, וכשמבקשים אותו שוב הוא משותף מחדש
// במקום לרדת פעם נוספת.

const FILES_CACHE_SHEET_NAME = "קבצים בדרייב";

// עמודות: מפתח | מזהה | פורמט | שם | מזהה הקובץ | קישור | תאריך | נחסך
const FC_COL_KEY     = 1;
const FC_COL_SOURCE  = 2;
const FC_COL_FORMAT  = 3;
const FC_COL_TITLE   = 4;
const FC_COL_FILE_ID = 5;
const FC_COL_LINK    = 6;
const FC_COL_DATE    = 7;
const FC_COL_HITS    = 8;

// האם הורדה חוזרת (קובץ ששוחזר מהמטמון) נספרת במכסה האישית.
// במכסה היומית הגלובלית היא לעולם לא נספרת - היא קיימת כדי להגן
// על השרת ועל יוטיוב, ושחזור קובץ קיים לא נוגע באף אחד מהם.
const REUSE_COUNTS_AGAINST_USER_QUOTA = true;


// ===================== גיליון משתמשי תוסף =====================

const TM_SHEET_NAME = "משתמשי תוסף";

// עמודות: אימייל | מכסה שעתית | חסום | סה"כ הורדות | מאומת | קוד אימות | טוקני מכשיר
const TM_COL_EMAIL    = 1;
const TM_COL_HOURLY   = 2;
const TM_COL_BLOCKED  = 3;
const TM_COL_TOTAL    = 4;
const TM_COL_VERIFIED = 5;
const TM_COL_CODE     = 6;
const TM_COL_TOKENS   = 7;
const TM_COL_NETFREE  = 8;


// ============================================================
// ===================== Google Form ===========================
// ============================================================

function getGoogleForm() {
  return FormApp.openById(FORM_ID);
}


// ============================================================
// ============ סגירת הטופס בגלל המכסה ========================
// ============================================================

function closeFormForDailyLimit() {
    try {
        const form = getGoogleForm();
        if (form) {
            try {
                form.setCustomClosedFormMessage(DAILY_LIMIT_MESSAGE);
            } catch (err1) {
                Logger.log("התראה בעדכון הודעת סגירה: " + err1.toString());
            }
            try {
                form.setAcceptingResponses(false);
            } catch (err2) {
                Logger.log("התראה בשינוי קבלת תגובות: " + err2.toString());
            }
        }
        Logger.log("הטופס נסגר בגלל הגעה למכסה היומית.");
    } catch (e) {
        Logger.log("שגיאה בסגירת הטופס בגליל המכסה: " + e.toString());
    }
}


// ============================================================
// ================= פתיחת הטופס מחדש ==========================
// ============================================================

function openFormForNewDay() {

  try {

    const form = getGoogleForm();

    form.setAcceptingResponses(true);

    Logger.log(
      "הטופס נפתח מחדש עבור יום חדש."
    );

  } catch (e) {

    Logger.log(
      "שגיאה בפתיחת הטופס: " +
      e.toString()
    );
  }
}


// ============================================================
// ================= תאריך היום ================================
// ============================================================

function getTodayKey() {

  return Utilities.formatDate(
    new Date(),
    Session.getScriptTimeZone(),
    "yyyy-MM-dd"
  );
}


// ============================================================
// =============== מצב המכסה הגלובלית ==========================
// ============================================================

function getGlobalDailyState() {

  const props =
    PropertiesService.getScriptProperties();

  const today =
    getTodayKey();

  let savedDate =
    props.getProperty(
      GLOBAL_DATE_KEY
    );

  let count =
    Number(
      props.getProperty(
        GLOBAL_COUNT_KEY
      )
    ) || 0;


  if (!savedDate) {

    savedDate = today;
    count = 0;

    props.setProperty(
      GLOBAL_DATE_KEY,
      today
    );

    props.setProperty(
      GLOBAL_COUNT_KEY,
      "0"
    );
  }


  // ===================== יום חדש =====================

  if (savedDate !== today) {

    count = 0;

    props.setProperty(
      GLOBAL_DATE_KEY,
      today
    );

    props.setProperty(
      GLOBAL_COUNT_KEY,
      "0"
    );

    openFormForNewDay();

    Logger.log(
      "יום חדש זוהה. המכסה אופסה ל-0."
    );
  }


  return {

    date: today,

    count: count,

    remaining:
      Math.max(
        0,
        DAILY_GLOBAL_LIMIT - count
      )
  };
}


// ============================================================
// ================= נעילות נפרדות לכל לולאה ===================
// ============================================================
// נעילת הסקריפט של גוגל (LockService.getScriptLock) היא אחת לכל
// הפרויקט, ואינה מזהה את ההרצה שכבר מחזיקה בה. שני דברים השתבשו
// כשהיא הוחזקה לאורך הורדה שלמה:
//
//   1. addSuccessfulDownloads, שנקראת באמצע ההורדה, ניסתה לתפוס
//      אותה שוב, חיכתה 30 שניות ונכשלה בחריגה - אחרי שהקובץ כבר
//      ירד ולפני שנשלח המייל ונכתב הסטטוס.
//   2. pollChannelJobs ניסתה לתפוס אותה בזמן שלולאת הטופס רצה,
//      ראתה שהיא תפוסה, ודילגה - כך שהערוצים מעולם לא התעדכנו.
//
// כאן לכל לולאה יש נעילה משלה, השמורה במאפייני הסקריפט עם תוקף.
// נעילת הסקריפט עצמה נתפסת רק לשבריר שנייה, לבדיקה ולרישום.

// אחרי כמה זמן נעילה נחשבת נטושה. הרצה שקרסה לא משחררת את
// הנעילה שלה, ובלי תוקף הלולאה הייתה נחסמת לתמיד.
const NAMED_LOCK_TTL_MS = 10 * 60 * 1000;


function acquireNamedLock(name) {

  const lock =
    LockService.getScriptLock();

  if (!lock.tryLock(10000)) {
    return false;
  }

  try {

    const props =
      PropertiesService.getScriptProperties();

    const key =
      "NAMED_LOCK_" + name;

    const now =
      Date.now();

    const heldSince =
      Number(props.getProperty(key)) || 0;

    if (
      heldSince &&
      (now - heldSince) < NAMED_LOCK_TTL_MS
    ) {
      return false;
    }

    props.setProperty(key, String(now));

    return true;

  } finally {

    lock.releaseLock();
  }
}


function releaseNamedLock(name) {

  PropertiesService
    .getScriptProperties()
    .deleteProperty("NAMED_LOCK_" + name);
}


// משחרר נעילות תקועות ידנית - למקרה שמשהו לא זז ורוצים להתחיל נקי
function TEST_ReleaseAllLocks() {

  ["form", "channels"].forEach(function (name) {

    const held =
      PropertiesService
        .getScriptProperties()
        .getProperty("NAMED_LOCK_" + name);

    releaseNamedLock(name);

    Logger.log(
      name + ": " +
      (held
        ? "שוחררה (הוחזקה מאז " + new Date(Number(held)) + ")"
        : "לא הייתה תפוסה")
    );
  });
}


// ============================================================
// ============ הוספת קובץ מוצלח למונה =========================
// ============================================================

function addSuccessfulDownloads(
  successCount
) {

  if (
    !successCount ||
    successCount <= 0
  ) {

    return getGlobalDailyState();
  }


  const lock =
    LockService.getScriptLock();


  try {

    lock.waitLock(30000);


    const props =
      PropertiesService.getScriptProperties();

    const today =
      getTodayKey();

    let savedDate =
      props.getProperty(
        GLOBAL_DATE_KEY
      );

    let count =
      Number(
        props.getProperty(
          GLOBAL_COUNT_KEY
        )
      ) || 0;


    if (savedDate !== today) {

      savedDate = today;
      count = 0;
    }


    count += successCount;


    count =
      Math.min(
        count,
        DAILY_GLOBAL_LIMIT
      );


    props.setProperty(
      GLOBAL_DATE_KEY,
      today
    );

    props.setProperty(
      GLOBAL_COUNT_KEY,
      String(count)
    );


    Logger.log(
      "מכסה גלובלית: " +
      count +
      "/" +
      DAILY_GLOBAL_LIMIT
    );


    if (
      count >=
      DAILY_GLOBAL_LIMIT
    ) {

      closeFormForDailyLimit();
    }


    return {

      date: today,

      count: count,

      remaining:
        Math.max(
          0,
          DAILY_GLOBAL_LIMIT - count
        )
    };


  } finally {

    lock.releaseLock();
  }
}


// ============================================================
// ============ חילוץ כתובת מתוך Google GOTO/URL ===============
// ============================================================

function extractRealYoutubeUrl(rawUrl) {

  if (!rawUrl) {
    return rawUrl;
  }


  let url =
    rawUrl
      .toString()
      .trim();


  if (
    /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[\w-]+/i
      .test(url)
  ) {

    return url;
  }


  if (
    url.indexOf("google.com/url") !== -1
  ) {

    try {

      const match =
        url.match(
          /[?&]url=([^&]+)/i
        );


      if (
        match &&
        match[1]
      ) {

        const decoded =
          decodeURIComponent(
            match[1]
          );


        Logger.log(
          "קישור Google URL זוהה, חולץ: " +
          decoded
        );


        return decoded;
      }

    } catch (e) {

      Logger.log(
        "שגיאה בחילוץ Google URL: " +
        e.toString()
      );
    }
  }


  if (
    /google\.com\/goto/i.test(url)
  ) {

    Logger.log(
      "קישור Google GOTO זוהה. מנסה לעקוב אחרי ההפניה..."
    );


    const resolved =
      resolveGoogleRedirect(url);


    if (
      resolved &&
      resolved !== url
    ) {

      Logger.log(
        "כתובת Google GOTO נפתרה ל: " +
        resolved
      );


      return resolved;
    }


    try {

      const match =
        url.match(
          /[?&]url=([^&]+)/i
        );


      if (
        match &&
        match[1]
      ) {

        const decoded =
          decodeURIComponent(
            match[1]
          );


        if (
          /youtube\.com|youtu\.be/i.test(
            decoded
          )
        ) {

          Logger.log(
            "נמצאה כתובת YouTube בתוך Google GOTO: " +
            decoded
          );


          return decoded;
        }
      }

    } catch (e) {

      Logger.log(
        "שגיאה בניסיון חילוץ נוסף מ-Google GOTO: " +
        e.toString()
      );
    }
  }


  return url;
}


// ============================================================
// ========== מעקב אחרי הפניות Google ==========================
// ============================================================

function resolveGoogleRedirect(startUrl) {

  let currentUrl =
    startUrl;


  const maxRedirects = 8;


  for (
    let i = 0;
    i < maxRedirects;
    i++
  ) {

    try {

      const response =
        UrlFetchApp.fetch(
          currentUrl,
          {

            method: "get",

            followRedirects: false,

            muteHttpExceptions: true,

            headers: {

              "User-Agent":
                "Mozilla/5.0"
            }
          }
        );


      const code =
        response.getResponseCode();


      Logger.log(
        "Google redirect ניסיון " +
        (i + 1) +
        ": HTTP " +
        code
      );


      if (
        code >= 300 &&
        code < 400
      ) {

        const headers =
          response.getAllHeaders();


        let location =
          headers.Location ||
          headers.location;


        if (
          Array.isArray(location)
        ) {

          location =
            location[0];
        }


        if (
          location
        ) {

          location =
            location.toString();


          if (
            location.indexOf("http") !== 0
          ) {

            const base =
              currentUrl.match(
                /^(https?:\/\/[^\/]+)/
              );


            if (
              base
            ) {

              location =
                base[1] +
                (
                  location.charAt(0) === "/"
                    ? location
                    : "/" + location
                );
            }
          }


          Logger.log(
            "הפניה נמצאה: " +
            location
          );


          if (
            /youtube\.com|youtu\.be/i.test(
              location
            )
          ) {

            return location;
          }


          currentUrl =
            location;


          continue;
        }
      }


      break;


    } catch (e) {

      Logger.log(
        "שגיאה במעקב אחרי Google Redirect: " +
        e.toString()
      );

      break;
    }
  }


  return currentUrl;
}


// ============================================================
// ================= בדיקת קישור ===============================
// ============================================================

function isValidVideoUrl(url) {
  if (!url) { return false; }

  const trimmed = url.toString().trim();

  const patterns = [
    /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[\w-]+/i,
    /^(https?:\/\/)?(www\.)?instagram\.com\/(p|reel|reels|tv)\/[\w-]+/i,
    /^(https?:\/\/)?(www\.|vm\.|vt\.)?tiktok\.com\/(@[\w.\-]+\/video\/\d+|[\w]+)/i,
    /^(https?:\/\/)?([a-zA-Z0-9-]+\.)?(mako\.co\.il|n12\.co\.il|13tv\.co\.il|kan\.org\.il|now14\.co\.il|c14\.co\.il|ynet\.co\.il|immergo\.tv)\/.+/i,
    /\.m3u8/i
  ];

  return patterns.some(function (p) {
    return p.test(trimmed);
  });
}


// ============================================================
// ============= חילוץ מזהה סרטון יוטיוב =======================
// ============================================================

function extractYoutubeVideoId(url) {

  if (!url) {
    return null;
  }


  const trimmed =
    url
      .toString()
      .trim();


  const match =
    trimmed.match(
      /(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]{11})/i
    );


  if (
    match &&
    match[1]
  ) {

    return match[1];
  }


  return null;
}


// ============================================================
// ============= בדיקת חסימת NetFree ============================
// ============================================================
// מחזיר "open" (פתוח), "lock" (נבדק ונחסם), "pending" (עדיין לא
// נבדק - ולכן חסום בפועל), או null אם הבדיקה לא הושלמה.
//
// שגיאה איננה תוצאה: היא לא אומרת חסום ולא פתוח. השירות מחזיר
// שגיאות בצורה "ERROR:<סיבה>" עם קוד שאינו 200.

function checkNetFreeStatus(videoId) {

  if (!videoId) {
    return null;
  }


  try {

    const response =
      UrlFetchApp.fetch(

        NETFREE_CHECK_BASE_URL +
        videoId,

        {

          method: "get",

          muteHttpExceptions: true,

          followRedirects: true

        }
      );


    const code =
      response.getResponseCode();


    const text =
      response
        .getContentText()
        .trim()
        .toUpperCase();


    Logger.log(
      "בדיקת NetFree עבור " +
      videoId +
      ": HTTP " +
      code +
      ", תשובה: " +
      text.substring(0, 40)
    );


    if (
      code !== 200 ||
      text.indexOf("ERROR") === 0
    ) {

      return null;
    }


    if (
      text === "OPEN"
    ) {

      return "open";
    }


    if (
      text === "LOCK"
    ) {

      return "lock";
    }


    if (
      text === "PENDING"
    ) {

      return "pending";
    }


    return null;


  } catch (e) {

    Logger.log(
      "שגיאה בבדיקת NetFree עבור " +
      videoId +
      ": " +
      e.toString()
    );


    return null;
  }
}


// ============================================================
// =================== ביצוע הורדה ===============================
// ============================================================

function performDownload(url, fmt, kanSeason, kanEpisode, email) {
  try {

    // קישורי כאן (kan.org.il): אפשר להוריד עונה שלמה (all_episodes)
    // או פרק בודד. העונה מזוהה מהקישור, הפרק אופציונלי.
    const isKan = String(url).toLowerCase().indexOf("kan.org.il") !== -1;

    const payload = {
      url: url,
      format: fmt,
      player_client: ["android"],
      use_cookies: false,
      use_proxy: false,
      // השרת משתף כל פרק שיורד בעבודת רקע ישירות למייל הזה —
      // בלי זה המבקש לא רואה את הקבצים בדרייב בכלל.
      email: (email || "").toString().trim()
    };

    if (isKan) {

      if (kanEpisode !== undefined && kanEpisode !== null && String(kanEpisode).trim() !== "") {
        payload.episode = Number(kanEpisode);
      } else {
        payload.all_episodes = true;
      }

      // הפרמטר season רלוונטי רק אם הקישור הוא עמוד סדרה בלי עונה
      if (kanSeason !== undefined && kanSeason !== null && String(kanSeason).trim() !== "") {
        payload.season = Number(kanSeason);
      }
    }

    const response = UrlFetchApp.fetch(RAILWAY_URL, {
      method: "post",
      contentType: "application/json",
      headers: {
        "X-API-KEY": API_KEY
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    });

    const result = JSON.parse(response.getContentText());

    if (!result.success) {
      Logger.log("הורדה נכשלה (" + fmt + "). שגיאה טכנית: " + (result.error || "לא ידוע"));
      return result;
    }

    // עונה שלמה מכאן: ההורדה נרשמה כעבודת רקע - מדווחים על זה
    // ומחזירים את קישור ההתקדמות. הפרקים יופיעו בתיקיית העונה בדרייב.
    if (result.platform === "kan" && result.jobId) {
      Logger.log(
        "עונה מכאן נרשמה כעבודת רקע: " + result.jobId +
        " (פרקים: " + result.total + "), תיקייה: " + result.folderName
      );

      return {
        success: true,
        kanSeasonJob: true,
        jobId: result.jobId,
        total: result.total,
        folderName: result.folderName,
        progressUrl: result.progressUrl,
        title: result.folderName || ("עונה מכאן (" + result.total + " פרקים)"),
        // בכוונה אין driveLink: קישור המעקב בשרת חסום בנטפרי
        // ואינו קישור הורדה. הפרקים ישותפו ישירות למייל המבקש
        // על ידי השרת, ומייל סיכום יישלח בסיום העבודה.
        driveLink: ""
      };
    }

    // חילוץ אוטומטי של ה-fileId מתוך קישור הדרייב במידה והוא קיים ולא הוגדר לבד
    if (result.driveLink && !result.fileId) {
      const match = result.driveLink.match(/\/d\/([a-zA-Z0-9_-]+)/);
      if (match && match[1]) {
        result.fileId = match[1];
      }
    }

    return result;

  } catch (e) {
    Logger.log("שגיאה טכנית ב-performDownload (" + fmt + "): " + e.toString());
    return {
      success: false,
      error: e.toString()
    };
  }
}

// ============================================================
// ============== מטמון הקבצים שכבר ירדו ======================
// ============================================================
// לפני שפונים לשרת בודקים אם הקובץ הזה כבר ירד פעם. אם כן -
// מוודאים שהוא עדיין קיים בדרייב, משחזרים אותו מהאשפה במידת
// הצורך, משתפים מחדש ומחזירים אותו. הורדה חדשה מתבצעת רק
// כשאין קובץ שאפשר להשתמש בו.
//
// כל הסינון - משתמש מאושר, חסימה, נטפרי, מכסות - קורה לפני
// הנקודה הזו ולא מושפע ממנה.

function ensureFilesCacheSheet() {

  const ss =
    SpreadsheetApp.getActiveSpreadsheet();

  let sheet =
    ss.getSheetByName(
      FILES_CACHE_SHEET_NAME
    );

  if (!sheet) {

    sheet =
      ss.insertSheet(
        FILES_CACHE_SHEET_NAME
      );

    sheet.appendRow([
      "מפתח",
      "מזהה / קישור",
      "פורמט",
      "שם הקובץ",
      "מזהה בדרייב",
      "קישור",
      "ירד בתאריך",
      "הורדות שנחסכו"
    ]);

    sheet.setFrozenRows(1);
  }

  return sheet;
}


// מפתח אחיד לקובץ. הפורמט הוא חלק מהמפתח כי אודיו ווידאו
// הם שני קבצים שונים לגמרי של אותו סרטון.
function buildCacheKey(url, fmt) {

  const videoId =
    extractYoutubeVideoId(url);

  const base =
    videoId
      ? videoId
      : (url || "")
          .toString()
          .trim()
          .toLowerCase()
          .replace(/^https?:\/\//, "")
          .replace(/^www\./, "")
          .replace(/[?&](utm_[^&]*|feature|si)=[^&]*/g, "")
          .replace(/\/$/, "");

  return base + "|" + (fmt === "video" ? "video" : "audio");
}


// מחפש שורה במטמון. מחזיר {rowIndex, fileId, title} או null.
function findCachedRow(cacheSheet, key) {

  const lastRow =
    cacheSheet.getLastRow();

  if (lastRow < 2) {
    return null;
  }

  const values =
    cacheSheet
      .getRange(2, 1, lastRow - 1, FC_COL_HITS)
      .getValues();

  for (let i = 0; i < values.length; i++) {

    if (
      (values[i][FC_COL_KEY - 1] || "")
        .toString()
        .trim() === key
    ) {

      return {
        rowIndex: i + 2,
        fileId: (values[i][FC_COL_FILE_ID - 1] || "").toString().trim(),
        title: (values[i][FC_COL_TITLE - 1] || "").toString(),
        hits: Number(values[i][FC_COL_HITS - 1]) || 0
      };
    }
  }

  return null;
}


// מנסה להשתמש בקובץ קיים. מחזיר תשובה בפורמט של performDownload,
// או null אם אין קובץ שאפשר להשתמש בו.
function tryReuseExistingFile(url, fmt, email) {

  try {

    const cacheSheet =
      ensureFilesCacheSheet();

    const key =
      buildCacheKey(url, fmt);

    const cached =
      findCachedRow(cacheSheet, key);

    if (!cached || !cached.fileId) {
      return null;
    }

    let file;

    try {

      file =
        DriveApp.getFileById(cached.fileId);

      // גישה לשם מוודאת שהקובץ באמת נגיש ולא רק שהמזהה תקין
      file.getName();

    } catch (e) {

      // נמחק לצמיתות או שאיבדנו גישה - מנקים ומורידים מחדש
      Logger.log(
        "הקובץ במטמון אינו נגיש, השורה נמחקת: " +
        cached.fileId + " | " + e.toString()
      );

      cacheSheet.deleteRow(cached.rowIndex);

      return null;
    }

    // קובץ באשפה משוחזר במקום לרדת שוב
    if (file.isTrashed()) {

      file.setTrashed(false);

      Logger.log(
        "הקובץ שוחזר מהאשפה: " + file.getName()
      );
    }

    // מתן הגישה נעשה ב-performDownloadOrReuse, במקום אחד לכל המסלולים

    cacheSheet
      .getRange(cached.rowIndex, FC_COL_HITS)
      .setValue(cached.hits + 1);

    const link =
      file.getUrl();

    cacheSheet
      .getRange(cached.rowIndex, FC_COL_LINK)
      .setValue(link);

    Logger.log(
      "הקובץ נמצא במטמון ולא ירד מחדש: " + key
    );

    return {
      success: true,
      title: cached.title || file.getName(),
      driveLink: link,
      fileId: cached.fileId,
      reused: true
    };

  } catch (e) {

    // תקלה במטמון לא אמורה למנוע הורדה רגילה
    Logger.log(
      "שגיאה בבדיקת המטמון: " + e.toString()
    );

    return null;
  }
}


function recordDownloadedFile(url, fmt, result) {

  try {

    if (!result || !result.success || !result.fileId) {
      return;
    }

    const cacheSheet =
      ensureFilesCacheSheet();

    const key =
      buildCacheKey(url, fmt);

    const existing =
      findCachedRow(cacheSheet, key);

    if (existing) {

      // הקובץ ירד מחדש (הישן נמחק) - מעדכנים את השורה הקיימת
      cacheSheet
        .getRange(existing.rowIndex, FC_COL_FILE_ID)
        .setValue(result.fileId);

      cacheSheet
        .getRange(existing.rowIndex, FC_COL_LINK)
        .setValue(result.driveLink);

      cacheSheet
        .getRange(existing.rowIndex, FC_COL_DATE)
        .setValue(new Date());

      return;
    }

    cacheSheet.appendRow([
      key,
      extractYoutubeVideoId(url) || url,
      fmt === "video" ? "וידאו" : "אודיו",
      result.title || "",
      result.fileId,
      result.driveLink || "",
      new Date(),
      0
    ]);

  } catch (e) {

    Logger.log(
      "רישום הקובץ במטמון נכשל: " + e.toString()
    );
  }
}


// מעניק למבקש גישת צפייה לקובץ.
//
// עד עכשיו זה נעשה רק במסלול התוסף, ומי שהזמין דרך הטופס קיבל
// קישור לקובץ שאין לו הרשאה לפתוח - זה עבד רק כשהתיקייה הייתה
// משותפת ממילא, או כשהמשתמש היה מחובר לחשבון הבעלים.
function grantFileAccess(fileId, email) {

  if (!fileId || !email) {
    return false;
  }

  try {

    DriveApp
      .getFileById(fileId)
      .addViewer(email);

    return true;

  } catch (e) {

    Logger.log(
      "מתן גישה לקובץ נכשל (" + fileId + " -> " +
      email + "): " + e.toString()
    );

    return false;
  }
}


// זו הפונקציה שכל מסלול קורא לה במקום performDownload.
// כאן, במקום אחד, מתבצעים גם השימוש החוזר וגם מתן הגישה - כך
// שכל מסלול ובכל מצב (קובץ חדש או קובץ שכבר היה) מתנהג אותו דבר.
function performDownloadOrReuse(url, fmt, email, kanSeason, kanEpisode) {

  // עונה/פרק של כאן לא עוברים דרך מטמון הקבצים - תמיד בקשה חדשה
  const isKanUrl = String(url).toLowerCase().indexOf("kan.org.il") !== -1;

  if (!isKanUrl) {

    const reused =
      tryReuseExistingFile(url, fmt, email);

    if (reused) {

      grantFileAccess(reused.fileId, email);

      return reused;
    }
  }

  const result =
    performDownload(url, fmt, kanSeason, kanEpisode, email);

  // עבודת עונה של כאן לא נרשמת במטמון (אין קובץ בודד)
  if (!(result && result.kanSeasonJob)) {
    recordDownloadedFile(url, fmt, result);
  }

  if (result && result.success && result.fileId) {

    grantFileAccess(result.fileId, email);
  }

  return result;
}


// ============================================================
// ========== כותרות סטטיסטיקה במאושרים =======================
// ============================================================
function ensureApprovedStatsHeaders(approvedSheet) {
  const headers = [
    "סה\"כ שימוש מצטבר",
    "סה\"כ וידאו",
    "סה\"כ אודיו",
    "הורדות שנכשלו",
    "אחוז הצלחה"
  ];
  for (let col = 0; col < headers.length; col++) {
    const cell = approvedSheet.getRange(1, 6 + col);
    if (!cell.getValue()) {
      cell.setValue(headers[col]);
    }
  }

  if (!approvedSheet.getRange(1, 11).getValue()) {
    approvedSheet.getRange(1, 11).setValue("נטפרי (כן/לא)");
  }
  if (!approvedSheet.getRange(1, 12).getValue()) {
    approvedSheet.getRange(1, 12).setValue("חסום (כן/לא)");
  }
  if (!approvedSheet.getRange(1, 13).getValue()) {
    approvedSheet.getRange(1, 13).setValue("מכסה שעתית מותאמת");
  }
}

// ============================================================
// ========== כותרת סטטיסטיקה בתגובות =========================
// ============================================================
function ensureResponsesStatsHeader(responsesSheet) {
  if (!responsesSheet.getRange(1, 6).getValue()) {
    responsesSheet.getRange(1, 6).setValue("סה\"כ הורדות עד כה");
  }
  if (!responsesSheet.getRange(1, 7).getValue()) {
    responsesSheet.getRange(1, 7).setValue("מקור הגעה");
  }
}


// ============================================================
// ========== עדכון סטטיסטיקת משתמש ============================
// ============================================================

function updateUserStats(
  approvedSheet,
  approvedSheetRowIndex,
  fmt,
  success
) {

  const statsRange =
    approvedSheet.getRange(
      approvedSheetRowIndex,
      6,
      1,
      5
    );


  const stats =
    statsRange.getValues()[0];


  let totalCumulative =
    Number(stats[0]) || 0;

  let totalVideo =
    Number(stats[1]) || 0;

  let totalAudio =
    Number(stats[2]) || 0;

  let totalFailed =
    Number(stats[3]) || 0;


  if (success) {

    totalCumulative += 1;


    if (
      fmt === "video"
    ) {

      totalVideo += 1;

    } else if (
      fmt === "audio"
    ) {

      totalAudio += 1;
    }


  } else {

    totalFailed += 1;
  }


  const totalAttempts =
    totalCumulative +
    totalFailed;


  const successRate =
    totalAttempts > 0

      ? Math.round(
          (
            totalCumulative /
            totalAttempts
          ) * 100
        )

      : 0;


  approvedSheet
    .getRange(
      approvedSheetRowIndex,
      6,
      1,
      5
    )
    .setValues([[
      totalCumulative,
      totalVideo,
      totalAudio,
      totalFailed,
      successRate + "%"
    ]]);


  return totalCumulative;
}


// ============================================================
// ================= פונקציה ראשית =============================
// ============================================================

function checkFormResponses() {

  // הטריגר יכול להיירות שוב בזמן שהריצה הקודמת עדיין מורידה.
  // הסטטוס נכתב לשורה רק בסוף הטיפול בה, ולכן ריצה שנייה הייתה
  // רואה את אותה שורה כריקה, מורידה אותה שוב ושולחת מייל נוסף.
  //
  // הנעילה כאן היא בשם ("form") ולא נעילת הסקריפט - ראו את
  // ההסבר ליד acquireNamedLock.
  if (!acquireNamedLock("form")) {

    Logger.log(
      "checkFormResponses כבר רצה כרגע - מדלגים על ההרצה הזו."
    );

    return;
  }

  try {

    // אם טריגר הערוצים נמחק מסיבה כלשהי - מתקינים אותו מחדש,
    // אחרת עבודות ערוץ שנפתחות מהטופס לא יתעדכנו לעולם
    ensureChannelPollTrigger();

    checkFormResponsesInner();

  } finally {

    releaseNamedLock("form");
  }
}


// מאתר באילו עמודות (B-D) נמצאים הקישור, האימייל וסוג ההורדה,
// לפי מילים בכותרות של גיליון התגובות. מחזיר אינדקסים מבוססי 0.
function detectFormColumns(responsesSheet) {

  const cols = { url: 1, email: 2, type: 3 };

  try {

    const headers =
      responsesSheet.getRange(1, 2, 1, 3).getValues()[0]
        .map(function (h) { return String(h || "").toLowerCase(); });

    const found = {};

    headers.forEach(function (h, idx) {
      const col = idx + 1;
      if (found.email === undefined && /mail|מייל/.test(h)) {
        found.email = col;
      } else if (found.type === undefined && /סוג|פורמט|type|format/.test(h)) {
        found.type = col;
      } else if (found.url === undefined && /קישור|כתובת|link|url/.test(h)) {
        found.url = col;
      }
    });

    if (
      found.url !== undefined &&
      found.email !== undefined &&
      found.type !== undefined
    ) {
      return found;
    }

  } catch (e) {
    Logger.log("זיהוי עמודות הטופס נכשל, משתמשים בברירת המחדל: " + e);
  }

  return cols;
}

function checkFormResponsesInner() {

  const initialState =
    getGlobalDailyState();


  if (
    initialState.count >=
    DAILY_GLOBAL_LIMIT
  ) {

    closeFormForDailyLimit();

    Logger.log(
      "המכסה היומית מלאה."
    );

    return;
  }


  const ss =
    SpreadsheetApp
      .getActiveSpreadsheet();


  const responsesSheet =
    ss.getSheetByName(
      RESPONSES_SHEET_NAME
    );


  const approvedSheet =
    ss.getSheetByName(
      APPROVED_SHEET_NAME
    );


  if (
    !responsesSheet ||
    !approvedSheet
  ) {

    Logger.log(
      "לא נמצא אחד הגליונות הנדרשים"
    );

    return;
  }


  const statusHeaderCell =
    responsesSheet.getRange(
      1,
      5
    );


  if (
    !statusHeaderCell.getValue()
  ) {

    statusHeaderCell.setValue(
      "סטטוס"
    );
  }


  ensureResponsesStatsHeader(
    responsesSheet
  );


  ensureApprovedStatsHeaders(
    approvedSheet
  );


  const lastRow =
    responsesSheet.getLastRow();


  if (
    lastRow < 2
  ) {

    return;
  }


  const dataRange =
    responsesSheet.getRange(
      2,
      1,
      lastRow - 1,
      5
    );


  const data =
    dataRange.getValues();


  // זיהוי עמודות הטופס לפי כותרת (B-D), כדי שסדר השאלות בטופס לא ישנה.
  // ברירת מחדל: B = קישור, C = אימייל, D = סוג הורדה.
  const formCols =
    detectFormColumns(responsesSheet);


  const approvedLastRow =
    approvedSheet.getLastRow();


  const approvedData =
    approvedLastRow >= 2

      ? approvedSheet
          .getRange(
            2,
            1,
            approvedLastRow - 1,
            11
          )
          .getValues()

      : [];


  const today =
    Utilities.formatDate(
      new Date(),
      Session.getScriptTimeZone(),
      "yyyy-MM-dd"
    );


  for (
    let i = 0;
    i < data.length;
    i++
  ) {

    const currentGlobalState =
      getGlobalDailyState();


    if (
      currentGlobalState.count >=
      DAILY_GLOBAL_LIMIT
    ) {

      closeFormForDailyLimit();

      break;
    }


    const row =
      data[i];


    const rawUrl =
      row[formCols.url];


    const email =
      (row[formCols.email] || "")
        .toString()
        .trim()
        .toLowerCase();


    const downloadTypeRaw =
      (row[formCols.type] || "")
        .toString()
        .trim();


    const currentStatus =
      row[4];


    if (
      currentStatus
    ) {

      continue;
    }


    // ---------- הגנת כפילויות לבקשות מהמייל ----------
    // מזהים בקשה מהמייל לפי הסימון המוטמע בתוך כתובת היוטיוב עצמה
    // ("...&via=email-search") — עובר דרך עמודת הקישור בגיליון.
    // לחיצה כפולה / רענון שולחים את אותה תשובה פעמיים, ובלי ההגנה
    // הזאת כל תשובה = הורדה כפולה.
    if (
      (rawUrl || "").toString().indexOf(EMAILDL_SOURCE_MARKER) !== -1 &&
      isEmaildlDuplicate(downloadTypeRaw, rawUrl, email)
    ) {

      responsesSheet
        .getRange(i + 2, 5)
        .setValue("⛔ כפול - דולג");

      continue;
    }


    if (
      !rawUrl ||
      !email
    ) {

      continue;
    }


    const sheetRowIndex =
      i + 2;


    const url =
      extractRealYoutubeUrl(
        rawUrl
      );


    Logger.log(
      "URL מקורי: " +
      rawUrl
    );


    Logger.log(
      "URL לאחר חילוץ: " +
      url
    );


    const isBoth =
      downloadTypeRaw ===
      "וידאו ואודיו";


    const requiredQuota =
      isBoth
        ? 2
        : 1;


    let fmtsToDownload =
      [];


    if (isBoth) {

      fmtsToDownload = [
        "video",
        "audio"
      ];

    } else if (
      downloadTypeRaw ===
      "וידאו"
    ) {

      fmtsToDownload = [
        "video"
      ];

    } else {

      fmtsToDownload = [
        "audio"
      ];
    }


    let approvedRowIndex =
      -1;


    for (
      let j = 0;
      j < approvedData.length;
      j++
    ) {

      const approvedEmail =
        (approvedData[j][0] || "")
          .toString()
          .trim()
          .toLowerCase();


      if (
        approvedEmail ===
        email
      ) {

        approvedRowIndex =
          j;

        break;
      }
    }


    if (
      approvedRowIndex === -1
    ) {

      responsesSheet
        .getRange(
          sheetRowIndex,
          5
        )
        .setValue(
          "❌ לא מאושר"
        );


      sendStatusEmail(
        email,

        "❌ הבקשה שלך לא אושרה",

        "שלום,\n\n" +
        "הבקשה שלך להורדת סרטון לא אושרה, " +
        "כי הכתובת שלך אינה ברשימת המשתמשים המורשים.\n\n" +
        "אם לדעתך זו טעות, פנה למי שאחראי על המערכת."
      );


      continue;
    }


    // ========================================================
    // קישור של ערוץ / פלייליסט - טיפול נפרד לגמרי.
    // ההורדה רצה ברקע בשרת ולוקחת דקות עד שעות, ולכן היא לא
    // מתבצעת כאן אלא נפתחת כעבודה, ו-pollChannelJobs עוקבת
    // אחריה ומעדכנת את הגיליון והמייל בסיום.
    // ========================================================    // ========================================================
    // הורדת עונה שלמה של סדרת מאקו הוסרה — מאות פרקים בבקשה
    // אחת לא נתמכת יותר (החסימה המפורשת למטה דוחה קישורי
    // סדרה/עונה של מאקו וכאן עם הסבר למשתמש).
    // ========================================================



    if (
      isChannelUrl(url)
    ) {

      handleChannelFormRow(
        responsesSheet,
        sheetRowIndex,
        email,
        url,
        downloadTypeRaw,
        approvedData[approvedRowIndex]
      );


      continue;
    }


    // ========================================================
    // חסימת הורדת עונה שלמה — מאות סרטונים בבקשה אחת.
    // קישורי עונה/סדרה של כאן ומאקו נדחים תמיד; המייל מכוון
    // להורדת פרק בודד (הכפתורים במייל החיפוש כבר שולחים פרק).
    // ========================================================

    const isKanSeasonLike =
      /kan\.org\.il\/content\/.+\/p-\d+(\/s\d+)?\/?(\?|$)/.test(url) &&
      !/kan\.org\.il\/content\/.+\/p-\d+\/s\d+\/\d+\//.test(url);

    const isMakoSeasonLike =
      /mako\.co\.il\/.+/.test(url) &&
      url.indexOf("VOD-") === -1 &&
      url.indexOf(".m3u8") === -1 &&
      /mako\.co\.il\/mako-vod-[^\/]+\/[^\/\s]+/.test(url);

    if (isKanSeasonLike || isMakoSeasonLike) {

      responsesSheet
        .getRange(
          sheetRowIndex,
          5
        )
        .setValue(
          "❌ הורדת עונה שלמה לא נתמכת"
        );

      sendStatusEmail(
        email,

        "❌ הורדת עונה שלמה אינה אפשרית",

        "שלום,\n\n" +
        "הבקשה שלך לא בוצעה כי נשלח קישור לעונה/סדרה שלמה - " +
        "והורדה של מאות פרקים בבקשה אחת אינה אפשרית במערכת.\n\n" +
        "איך להוריד פרק בודד:\n" +
        "1. היכנסו לעמוד העונה ובחרו פרק\n" +
        "2. העתיקו את הכתובת של הפרק עצמו\n" +
        "3. שלחו בקשה חדשה עם כתובת הפרק\n\n" +
        "טיפ: במייל תוצאות החיפוש יש כפתור לכל פרק בעונות " +
        "האחרונות - לחיצה עליו ממלאת הכל אוטומטית.\n\n" +
        "לשליחת בקשה חדשה:\n" +
        FORM_URL +
        "\n\nתודה!"
      );

      continue;
    }


    if (
      !isValidVideoUrl(url)
    ) {

      responsesSheet
        .getRange(
          sheetRowIndex,
          5
        )
        .setValue(
          "❌ קישור לא תקין"
        );


      sendStatusEmail(
        email,

        "❌ הקישור שנשלח אינו תקין",

        "שלום,\n\n" +
        "הבקשה שלך לא בוצעה כי הקישור שנשלח אינו קישור תקין לסרטון.\n\n" +
        "נא לשלוח בקשה חדשה עם קישור תקין מאחת הפלטפורמות הנתמכות:\n" +
        "- יוטיוב (סרטון בודד או ערוץ שלם)\n" +
        "- אינסטגרם\n" +
        "- טיקטוק\n" +
        "- אתרי חדשות (מאקו, n12, 13, כאן, now14, c14, ynet)\n\n" +
        "לשליחת בקשה חדשה:\n" +
        FORM_URL +
        "\n\nתודה!"
      );


      continue;
    }


    // ========================================================
    // בדיקת NetFree (רק למשתמשים שמוגדרים עם נטפרי,
    // ורק על קישורי יוטיוב - השירות תומך רק בהם)
    // ========================================================

    const approvedRowForNetfree =
      approvedData[approvedRowIndex];


    const netfreeFlag =
      (approvedRowForNetfree[10] || "")
        .toString()
        .trim();


    const userHasNetfree =
      netfreeFlag === "כן" &&
      NETFREE_CHECK_FOR_FORM;


    if (
      userHasNetfree
    ) {

      const videoId =
        extractYoutubeVideoId(url);


      if (
        videoId
      ) {

        const netfreeAnswer =
          checkNetFreeStatus(
            videoId
          );


        if (
          netfreeAnswer !== "open"
        ) {

          responsesSheet
            .getRange(
              sheetRowIndex,
              5
            )
            .setValue(
              netfreeAnswer === "lock"
                ? "❌ חסום בנטפרי"
                : (
                    netfreeAnswer === "pending"
                      ? "❌ עדיין לא נבדק בנטפרי"
                      : "❌ לא ניתן היה לבדוק נטפרי"
                  )
            );


          sendStatusEmail(
            email,

            "❌ הבקשה שלך לא בוצעה",

            "שלום,\n\n" +
            (
              netfreeAnswer === "lock"

                ? "הסרטון שביקשת חסום ברשת הנטפרי שלך, ולכן לא בוצעה הורדה עבורו."

                : (
                    netfreeAnswer === "pending"

                      ? "הסרטון שביקשת עדיין לא נבדק בנטפרי, ולכן הוא חסום בפועל ולא בוצעה עבורו הורדה."

                      : "לא הצלחנו לוודא האם הסרטון חסום ברשת הנטפרי שלך כרגע, ולכן ליתר בטחון לא בוצעה הורדה."
                  )
            ) +
            "\n\n" +
            "אם ברצונך לנסות שוב מאוחר יותר:\n" +
            FORM_URL +
            "\n\nתודה!"
          );


          continue;
        }
      }
    }


    const approvedRow =
      approvedData[
        approvedRowIndex
      ];


    const quotaValue =
      approvedRow[1];


    const dailyLimitValue =
      approvedRow[2];


    let usedToday =
      approvedRow[3];


    let lastUpdateDate =
      approvedRow[4];


    let allowed =
      false;


    let denyReason =
      "";


    let updateType =
      "none";


    const quotaIsUnlimited =
      (quotaValue || "")
        .toString()
        .trim() ===
      "ללא הגבלה";


    const quotaIsNumber =
      typeof quotaValue ===
      "number";


    const dailyIsNumber =
      typeof dailyLimitValue ===
      "number";


    if (
      quotaIsUnlimited
    ) {

      allowed = true;

      updateType =
        "none";


    } else if (
      quotaIsNumber
    ) {

      if (
        quotaValue >=
        requiredQuota
      ) {

        allowed = true;

        updateType =
          "quota";

      } else {

        denyReason =
          "❌ נגמרה המכסה";
      }


    } else if (
      dailyIsNumber
    ) {

      const lastUpdateStr =
        lastUpdateDate

          ? Utilities.formatDate(
              new Date(
                lastUpdateDate
              ),
              Session.getScriptTimeZone(),
              "yyyy-MM-dd"
            )

          : "";


      if (
        lastUpdateStr !==
        today
      ) {

        usedToday = 0;
      }


      if (
        (
          dailyLimitValue -
          (usedToday || 0)
        ) >=
        requiredQuota
      ) {

        allowed = true;

        updateType =
          "daily";

      } else {

        denyReason =
          "❌ נוצלה ההגבלה היומית";
      }


    } else {

      denyReason =
        "❌ לא הוגדרה הרשאה למשתמש הזה";
    }


    if (
      !allowed
    ) {

      responsesSheet
        .getRange(
          sheetRowIndex,
          5
        )
        .setValue(
          denyReason
        );


      sendStatusEmail(
        email,

        "❌ הבקשה שלך לא בוצעה",

        "שלום,\n\n" +
        "הבקשה שלך להורדת סרטון לא בוצעה.\n\n" +
        "סיבה: " +
        denyReason +
        "\n\n" +
        "אם תרצה להמשיך להשתמש בשירות, " +
        "פנה למי שאחראי על המערכת כדי לחדש את ההרשאה שלך."
      );


      continue;
    }


    const globalBefore =
      getGlobalDailyState();

    if (
      globalBefore.remaining <
      requiredQuota
    ) {
      responsesSheet
        .getRange(
          sheetRowIndex,
          5
        )
        .setValue(
          "❌ המכסה היומית של המערכת הסתיימה"
        );
      closeFormForDailyLimit();
      break;
    }


    const results = [];

    let anySuccess =
      false;

    let latestCumulativeTotal =
      null;


    for (
      let k = 0;
      k < fmtsToDownload.length;
      k++
    ) {

      const fmt =
        fmtsToDownload[k];


      const beforeFile =
        getGlobalDailyState();


      if (
        beforeFile.remaining <= 0
      ) {

        closeFormForDailyLimit();

        break;
      }


      const result =
        performDownloadOrReuse(
          url,
          fmt,
          email
        );


      results.push({

        fmt: fmt,

        result: result

      });


      if (
        result.success
      ) {

        anySuccess = true;

        // קובץ ששוחזר מהמטמון לא נגע בשרת ולא ביוטיוב,
        // ולכן אינו נספר במכסה היומית הגלובלית.
        // עונה של כאן לא נספרת עכשיו — היא נספרת בסיום העבודה
        // דרך pollChannelJobs (אותו מנגנון כמו עונות מאקו).
        if (!result.reused && !result.kanSeasonJob) {

          addSuccessfulDownloads(1);
        }
      }


      latestCumulativeTotal =
        updateUserStats(

          approvedSheet,

          approvedRowIndex + 2,

          fmt,

          result.success
        );
    }


    if (
      latestCumulativeTotal !== null
    ) {

      const refreshedStats =
        approvedSheet
          .getRange(
            approvedRowIndex + 2,
            6,
            1,
            5
          )
          .getValues()[0];


      approvedData[
        approvedRowIndex
      ][5] =
        refreshedStats[0];


      approvedData[
        approvedRowIndex
      ][6] =
        refreshedStats[1];


      approvedData[
        approvedRowIndex
      ][7] =
        refreshedStats[2];


      approvedData[
        approvedRowIndex
      ][8] =
        refreshedStats[3];


      approvedData[
        approvedRowIndex
      ][9] =
        refreshedStats[4];


      responsesSheet
        .getRange(
          sheetRowIndex,
          6
        )
        .setValue(
          latestCumulativeTotal
        );
    }


    if (isBoth) {

      const videoResult =
        results.find(
          function (r) {
            return r.fmt === "video";
          }
        )?.result;


      const audioResult =
        results.find(
          function (r) {
            return r.fmt === "audio";
          }
        )?.result;


      let statusParts = [];

      // האם כל ההצלחות בבקשה הזו הגיעו מהמטמון. קבצים כאלה כבר בדרייב
      // והקישורים שלהם כבר נשלחו בפעם הראשונה, ולכן אין טעם לשרוף
      // מכסת מיילים על הודעה חוזרת.
      const videoWasCached =
        videoResult &&
        videoResult.success &&
        videoResult.reused === true;

      const audioWasCached =
        audioResult &&
        audioResult.success &&
        audioResult.reused === true;

      const hadAnyFailure =
        !videoResult ||
        !videoResult.success ||
        !audioResult ||
        !audioResult.success;

      const allSuccessesFromCache =
        anySuccess &&
        (!videoResult ||
          !videoResult.success ||
          videoResult.reused === true) &&
        (!audioResult ||
          !audioResult.success ||
          audioResult.reused === true);

      let emailBody =
        "שלום,\n\n";

      // רישום עבודות עונה של כאן למעקב (כמו עונות מאקו):
      // pollChannelJobs עוקב ושולח מייל סיכום בסיום.
      for (let si = 0; si < results.length; si++) {

        const sres =
          results[si] && results[si].result;

        if (
          sres &&
          sres.success &&
          sres.kanSeasonJob &&
          sres.jobId
        ) {

          try {

            ensureChannelsSheet().appendRow([
              new Date(),
              email,
              url,
              sres.title || "",
              results[si].fmt === "video" ? "וידאו" : "אודיו",
              sres.jobId,
              "בעבודה",
              "0/" + (sres.total || 0),
              "",
              "",
              new Date(),
              "טופס-כאן",
              sheetRowIndex
            ]);

          } catch (regErr2) {

            Logger.log(
              "רישום עבודת עונה למעקב נכשל: " + regErr2
            );
          }
        }
      }


      if (
        videoResult &&
        videoResult.success
      ) {

        emailBody += videoResult.kanSeasonJob
          ? "הוידאו יורד כעת ברקע - הפרקים ישותפו אליך ישירות בדרייב (ימצאו תחת \"שיתפו איתי\"), ובסיום יישלח מייל סיכום.\n\n"
          : "קישור לוידאו:\n" +
            videoResult.driveLink +
            "\n\n";


        statusParts.push(
          "✅ וידאו: " +
          videoResult.title +
          (videoWasCached ? " (מהמטמון)" : "")
        );


      } else {

        emailBody +=
          "הורדת הוידאו נכשלה.\n\n";


        statusParts.push(
          "❌ וידאו נכשל"
        );


        Logger.log(
          "וידאו נכשל. השגיאה הטכנית נשמרה ב-Logs."
        );
      }


      if (
        audioResult &&
        audioResult.success
      ) {

        emailBody += audioResult.kanSeasonJob
          ? "האודיו יורד כעת ברקע - הפרקים ישותפו אליך ישירות בדרייב (ימצאו תחת \"שיתפו איתי\"), ובסיום יישלח מייל סיכום.\n\n"
          : "קישור לאודיו:\n" +
            audioResult.driveLink +
            "\n\n";


        statusParts.push(
          "✅ אודיו: " +
          audioResult.title +
          (audioWasCached ? " (מהמטמון)" : "")
        );


      } else {

        emailBody +=
          "הורדת האודיו נכשלה.\n\n";


        statusParts.push(
          "❌ אודיו נכשל"
        );


        Logger.log(
          "אודיו נכשל. השגיאה הטכנית נשמרה ב-Logs."
        );
      }


      emailBody +=
        "תודה!";


      // בקשה שכולה מהמטמון ובלי כישלונות - אין חדש לדווח עליו
      // ולא שולחים מייל בכלל. כישלון או הורדה חדשה - שולחים כרגיל.
      const skipCacheEmail =
        allSuccessesFromCache &&
        !hadAnyFailure;


      let emailSent = false;


      if (skipCacheEmail) {

        Logger.log(
          "הבקשה הושלמה מהמטמון ללא הורדות חדשות - מדלגים על מייל אל " +
          email
        );

      } else {

        const hasSeasonJob =
          (videoResult && videoResult.success && videoResult.kanSeasonJob) ||
          (audioResult && audioResult.success && audioResult.kanSeasonJob);

        const hasDirectFile =
          (videoResult && videoResult.success && !videoResult.kanSeasonJob) ||
          (audioResult && audioResult.success && !audioResult.kanSeasonJob);

        const emailSubject =
          !anySuccess
            ? "❌ ההורדה נכשלה"
            : (
                hasSeasonJob && !hasDirectFile
                  ? "🔄 הבקשה שלך מתבצעת"
                  : "✅ הקבצים שלך מוכנים"
              );


        emailSent =
          sendStatusEmailAndTrack(
            email,
            emailSubject,
            emailBody
          );
      }


      responsesSheet
        .getRange(
          sheetRowIndex,
          5
        )
        .setValue(
          statusParts.join(", ") +
          (emailSent
            ? ""
            : (
                skipCacheEmail
                  ? ""
                  : " — ⚠️ מייל לא נשלח: מכסה יומית"
              ))
        );


      if (
        anySuccess
      ) {

        // נרשמה הצלחה — רושמים טביעה להגנת הכפילויות (רק לבקשות מהמייל)
        if ((rawUrl || "").toString().indexOf(EMAILDL_SOURCE_MARKER) !== -1) {
          markEmaildlDone(downloadTypeRaw, rawUrl, email);
        }

        if (
          updateType ===
          "quota"
        ) {

          approvedSheet
            .getRange(
              approvedRowIndex + 2,
              2
            )
            .setValue(
              quotaValue -
              requiredQuota
            );


          approvedData[
            approvedRowIndex
          ][1] =
            quotaValue -
            requiredQuota;


        } else if (
          updateType ===
          "daily"
        ) {

          approvedSheet
            .getRange(
              approvedRowIndex + 2,
              4
            )
            .setValue(
              (usedToday || 0) +
              requiredQuota
            );


          approvedSheet
            .getRange(
              approvedRowIndex + 2,
              5
            )
            .setValue(
              today
            );


          approvedData[
            approvedRowIndex
          ][3] =
            (usedToday || 0) +
            requiredQuota;


          approvedData[
            approvedRowIndex
          ][4] =
            today;
        }
      }


    } else {

      const result =
        results[0]?.result;


      if (
        result &&
        result.success
      ) {

        // נרשמה הצלחה — רושמים טביעה להגנת הכפילויות (רק לבקשות מהמייל)
        if ((rawUrl || "").toString().indexOf(EMAILDL_SOURCE_MARKER) !== -1) {
          markEmaildlDone(downloadTypeRaw, rawUrl, email);
        }

        // כתיבת הסטטוס לפני שליחת המייל, כדי שכישלון מייל
        // בגלל מכסה לא ישאיר את הקישור בלי תיעוד בגיליון.
        const wasCached =
          result.reused === true;

        // עונה של כאן נרשמת למעקב כמו עבודות ערוץ/עונה של מאקו:
        // pollChannelJobs עוקב אחריה ושולח מייל סיכום בסיום.
        for (let ri = 0; ri < results.length; ri++) {

          const seasonRes =
            results[ri] && results[ri].result;

          if (
            seasonRes &&
            seasonRes.kanSeasonJob &&
            seasonRes.jobId
          ) {

            try {

              ensureChannelsSheet().appendRow([
                new Date(),
                email,
                url,
                seasonRes.title || "",
                results[ri].fmt === "video" ? "וידאו" : "אודיו",
                seasonRes.jobId,
                "בעבודה",
                "0/" + (seasonRes.total || 0),
                "",
                "",
                new Date(),
                "טופס-כאן",
                sheetRowIndex
              ]);

            } catch (regErr) {

              Logger.log(
                "רישום עבודת עונה למעקב נכשל: " + regErr
              );
            }
          }
        }

        const successStatus =
          result.kanSeasonJob
            ? ("🔄 " + result.title + " - " +
               (result.total || 0) + " פרקים יורדים ברקע")
            : ("✅ " +
               result.title +
               " - " +
               result.driveLink +
               (wasCached ? " (מהמטמון)" : ""));


        responsesSheet
          .getRange(
            sheetRowIndex,
            5
          )
          .setValue(
            successStatus
          );


        // קובץ מהמטמון כבר היה בדרייב והקישור שלו כבר נשלח בפעם
        // הראשונה - לא שולחים מייל חוזר ולא שורפים עליו מכסה.
        if (wasCached) {

          Logger.log(
            "הקובץ נלקח מהמטמון - מדלגים על מייל אל " + email
          );

        } else if (result.kanSeasonJob) {

          // עונה של כאן יורדת כעבודת רקע — אין קישור הורדה ישיר עכשיו
          // (קישור המעקב בשרת חסום בנטפרי ואינו קישור הורדה).
          // הפרקים ישותפו ישירות למייל המבקש כשירדו, ומייל סיכום
          // יישלח בסיום העבודה דרך pollChannelJobs.
          sendStatusEmailAndTrack(

            email,

            "🔄 הבקשה שלך מתבצעת: " +
            result.title,

            "שלום,\n\n" +
            "הבקשה שלך התקבלה ומבוצעת כעת ברקע.\n\n" +
            "שם: " +
            result.title +
            "\n" +
            "סה\"כ פרקים: " +
            (result.total || 0) +
            "\n\n" +
            "כל פרק שיירד ישותף אליך ישירות בדרייב " +
            "(ימצא תחת \"שיתפו איתי\"), " +
            "ובסיום יישלח מייל סיכום.\n\n" +
            "תודה!"
          );

        } else {

          const emailSent =
            sendStatusEmailAndTrack(

              email,

              "✅ הסרטון שלך מוכן: " +
              result.title,

              "שלום,\n\n" +
              "הסרטון שביקשת ירד " +
              "ועלה לדרייב בהצלחה.\n\n" +
              "שם: " +
              result.title +
              "\n" +
              "קישור להורדה: " +
              result.driveLink +
              "\n\nתודה!"
            );


          if (!emailSent) {

            responsesSheet
              .getRange(
                sheetRowIndex,
                5
              )
              .setValue(
                successStatus +
                " — ⚠️ מייל לא נשלח: מכסה יומית"
              );
          }
        }


        if (
          updateType ===
          "quota"
        ) {

          approvedSheet
            .getRange(
              approvedRowIndex + 2,
              2
            )
            .setValue(
              quotaValue -
              requiredQuota
            );


          approvedData[
            approvedRowIndex
          ][1] =
            quotaValue -
            requiredQuota;


        } else if (
          updateType ===
          "daily"
        ) {

          approvedSheet
            .getRange(
              approvedRowIndex + 2,
              4
            )
            .setValue(
              (usedToday || 0) +
              requiredQuota
            );


          approvedSheet
            .getRange(
              approvedRowIndex + 2,
              5
            )
            .setValue(
              today
            );


          approvedData[
            approvedRowIndex
          ][3] =
            (usedToday || 0) +
            requiredQuota;


          approvedData[
            approvedRowIndex
          ][4] =
            today;
        }


      } else {

        responsesSheet
          .getRange(
            sheetRowIndex,
            5
          )
          .setValue(
            "❌ שגיאה"
          );


        Logger.log(
          "הורדה בודדת נכשלה. שגיאה טכנית: " +
          (
            result?.error ||
            "לא ידוע"
          )
        );


        sendStatusEmail(

          email,

          "❌ ההורדה נכשלה",

          "שלום,\n\n" +
          "לצערנו ההורדה נכשלה עקב שגיאה טכנית.\n\n" +
          "נסה שוב מאוחר יותר, " +
          "או פנה למי שאחראי על המערכת.\n\n" +
          "תודה!"
        );
      }
    }
  }
}


// ============================================================
// ===================== שליחת מייל ============================
// ============================================================

// מייל טקסט רגיל לא נושא מידע על כיוון הכתיבה, ולכן ג'ימייל
// מציג אותו מיושר לשמאל. לכן נשלחת גם גרסת HTML עם dir="rtl",
// והטקסט הרגיל נשאר כגיבוי לתוכנות שלא מציגות HTML.

function escapeHtml(text) {

  return (text || "")
    .toString()
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}


function textToRtlHtml(text) {

  const source =
    (text || "").toString();

  const linkPattern =
    /(https?:\/\/[^\s<>"']+)/g;

  const parts = [];

  let lastIndex = 0;

  let match;

  while ((match = linkPattern.exec(source)) !== null) {

    parts.push(
      escapeHtml(
        source.substring(lastIndex, match.index)
      )
    );

    const safeUrl =
      escapeHtml(match[1]);

    // הקישור עצמו נשאר משמאל לימין גם בתוך פסקה בעברית
    parts.push(
      '<a href="' + safeUrl + '" dir="ltr" ' +
      'style="color:#1a73e8; word-break:break-all;">' +
      safeUrl + '</a>'
    );

    lastIndex = linkPattern.lastIndex;
  }

  parts.push(
    escapeHtml(
      source.substring(lastIndex)
    )
  );

  const html =
    parts
      .join("")
      .replace(/\n/g, "<br>");

  return (
    '<div dir="rtl" style="text-align:right; ' +
    'font-family:Arial, Helvetica, sans-serif; ' +
    'font-size:15px; line-height:1.7; color:#202124;">' +
    html +
    '</div>'
  );
}


// ============================================================
// ==== שליחת מיילים דרך Gmail API‏ (500 ליום, בלי שירות חיצוני) ====
// ============================================================
// חשבון gmail.com רגיל מוגבל ב-Apps Script לכ-100 נמענים ביום דרך
// MailApp‏ ("Service invoked too many times for one day: email").
// אבל המגבלה הרגילה של Gmail עצמו היא 500 נמענים ביום. כאן שולחים
// ישירות דרך Gmail REST API עם הטוקן הפנימי של הסקריפט: בלי הרשמה
// לשירות חיצוני, בלי SMS ובלי מפתחות API — הכל מהחשבון שלכם.
//
// הפעלה חד-פעמית:
//   0. מוודאים שה-Gmail API מופעל בפרויקט ה-GCP שאליו משויך הסקריפט.
//      פרויקט ה-default האוטומטי של Apps Script לא מאפשר הפעלת APIs —
//      צריך פרויקט GCP רגיל (Project Settings → GCP Project → Change project),
//      ואז APIs & Services → Library → Gmail API → Enable.
//      מריצים checkGmailApi כדי לבדוק. (גם אם ה-API כבוי המערכת עובדת,
//      אבל כל המיילים נופלים ל-MailApp וצורכים את המכסה של 100 ביום.)
//   1. מריצים מהעורך את grantGmailScope ומאשרים את ההרשאות.
//      גוגל יציגו אזהרה על "גישה ל-Gmail" — זה נורמלי: זו ההרשאה
//      שמאפשרת לסקריפט לשלוח מהכתובת שלכם. כלום לא נקרא ולא נמחק.
//   2. מריצים את testGmailApi כדי לוודא שמייל בדיקה יוצא.
// מרגע זה כל השליחה עוברת אוטומטית דרך Gmail API‏ (500 ליום),
// ו-MailApp המקורי נשאר רק כגיבוי (100 ליום נוספים).

// פונקציה ריקה שנועדה רק שגוגל יכירו בהרשאת ה-Gmail בזמן האישור.
// מריצים פעם אחת מהעורך, מאשרים, ומאז הטוקן כולל גישת שליחה.
function grantGmailScope() {

  GmailApp.getInboxUnreadCount();
}

// ============================================================
// אבחון שליחת המייל — מריצים מהעורך וקוראים את הלוג
// ============================================================
// הבדיקה שולחת בקשת קריאה בלבד (users.getProfile) ולא שולחת מייל,
// כדי שאפשר יהיה לאבחן גם כשמכסת השליחה נגמרה. היא מבדילה בין:
//   1. Gmail API כבוי בפרויקט ה-GCP            → 403 SERVICE_DISABLED
//   2. חסרה הרשאת OAuth                        → 403/401 scope
//   3. מכסת שליחה יומית נגמרה                  → 429/550, או MailApp = 0
// ============================================================

// האם טקסט התשובה של גוגל מעיד שה-API כבוי (ולא בעיית הרשאה)?
function isGmailApiDisabledText(text) {

  return /has not been used in project|SERVICE_DISABLED|is disabled|it is disabled/i.test(
    String(text || "")
  );
}

// מספר פרויקט ה-GCP מתוך תשובת השגיאה ("...in project 123456789012...")
function extractGcpProjectNumber(text) {

  const match = /project (\d+)/i.exec(String(text || ""));
  return match ? match[1] : null;
}

// בקשת בדיקה אחת ל-Gmail API — קריאה בלבד, לא שולחת מייל.
// מחזיר {ok, kind, status, message, projectNumber, raw}
// kind: "ok" | "api_disabled" | "no_scope" | "auth" | "quota" | "other"
function probeGmailApi() {

  let status = 0;
  let raw = "";

  try {

    const response = UrlFetchApp.fetch(
      "https://gmail.googleapis.com/gmail/v1/users/me/profile",
      {
        method: "get",
        headers: {
          "Authorization":
            "Bearer " + ScriptApp.getOAuthToken()
        },
        muteHttpExceptions: true
      }
    );

    status = response.getResponseCode();
    raw = response.getContentText() || "";

    if (status >= 200 && status < 300) {

      return {
        ok: true,
        kind: "ok",
        status: status,
        message: "Gmail API פעיל ותקין.",
        projectNumber: null,
        raw: raw
      };
    }

  } catch (probeError) {

    return {
      ok: false,
      kind: "other",
      status: 0,
      message: "הבקשה עצמה נכשלה: " + probeError,
      projectNumber: null,
      raw: String(probeError)
    };
  }

  let apiMessage = "";

  try {
    apiMessage =
      JSON.parse(raw).error.message;
  } catch (parseError) {
    apiMessage = raw.substring(0, 300);
  }

  let kind;

  if (isGmailApiDisabledText(raw)) {
    kind = "api_disabled";
  } else if (
    /insufficient authentication scopes|ACCESS_TOKEN_SCOPE_INSUFFICIENT|insufficientPermissions|PERMISSION_DENIED/i.test(
      raw
    )
  ) {
    kind = "no_scope";
  } else if (status === 401) {
    kind = "auth";
  } else if (
    status === 429 ||
    /quota|rate limit|too many|exceeded/i.test(raw)
  ) {
    kind = "quota";
  } else {
    kind = "other";
  }

  return {
    ok: false,
    kind: kind,
    status: status,
    message: apiMessage,
    projectNumber: extractGcpProjectNumber(raw),
    raw: raw
  };
}

// הפונקציה שמריצים מהעורך: מדפיסה בעברית מה חסר ומה בדיוק לעשות.
function checkGmailApi() {

  const lines = [];

  lines.push("=== אבחון שליחת המייל (פרויקט ההורדות) ===");
  lines.push("חשבון שולח: " + Session.getEffectiveUser().getEmail());

  const remaining = MailApp.getRemainingDailyQuota();

  if (remaining === 0) {
    lines.push(
      "מכסת MailApp שנותרה היום: 0  ← נגמרה. מתאפסת בחצות שעון פסיפי (≈10:00 בישראל)."
    );
  } else {
    lines.push("מכסת MailApp שנותרה היום: " + remaining);
  }

  lines.push("");
  lines.push("שולח בקשת בדיקה אחת ל-Gmail API (קריאה בלבד, לא נשלח מייל)…");

  const probe = probeGmailApi();

  if (probe.ok) {

    lines.push("✅ " + probe.message);
    lines.push("אפשר להריץ testGmailApi (שולח מייל בדיקה אמיתי).");

  } else if (probe.kind === "api_disabled") {

    lines.push("❌ הגורם: Gmail API כבוי בפרויקט ה-GCP שאליו משויך הסקריפט.");
    lines.push(
      "   זה לא עניין של הרשאות — grantGmailScope לא יעזור כאן, צריך להפעיל את ה-API."
    );
    lines.push("");
    lines.push("   מה עושים (פעם אחת, מהמחשב):");
    lines.push(
      "   1. בהגדרות הפרויקט בסקריפט (⚙ Project Settings) רואים את מספר הפרויקט."
    );
    lines.push(
      "   2. אם ליד GCP Project כתוב Default / פרויקט אוטומטי — אי אפשר להפעיל בו API:"
    );
    lines.push("      לוחצים על הקישור, בוחרים Change project → Create a new project,");
    lines.push("      ומעדכנים שהסקריפט ישתמש בפרויקט החדש.");
    lines.push(
      "   3. בקונסולת ה-Cloud (או בקישור למטה): APIs & Services → Library → Gmail API → Enable."
    );
    lines.push(
      "   4. חוזרים לעורך, מריצים שוב את checkGmailApi (ייתכן שתתבקשו לאשר הרשאות מחדש)."
    );
    lines.push("");
    lines.push(
      "   פרויקט שזוהה בתשובת גוגל: " +
        (probe.projectNumber || "לא צוין בתשובה (בדקו בהגדרות הפרויקט)")
    );

    if (probe.projectNumber) {
      lines.push(
        "   קישור ישיר להפעלה: https://console.cloud.google.com/apis/library/gmail.googleapis.com?project=" +
          probe.projectNumber
      );
    }

  } else if (probe.kind === "no_scope" || probe.kind === "auth") {

    lines.push("❌ הגורם: חסרה הרשאת OAuth לשליחה בחשבון הזה.");
    lines.push("   מה עושים: מריצים grantGmailScope ומאשרים את מסך ההרשאות,");
    lines.push("   ואז מריצים שוב את checkGmailApi.");

  } else if (probe.kind === "quota") {

    lines.push("❌ הגורם: חריגה ממכסת השליחה היומית של Gmail.");
    lines.push("   מה עושים: לחכות לאיפוס המכסה (≈10:00 בישראל) ולשלוח שוב.");

  } else {

    lines.push("⚠️ לא זוהה דפוס מוכר (HTTP " + probe.status + "). פירוט התשובה למטה.");
    lines.push("   אם כתוב שם משהו על OAuth/scope — הריצו grantGmailScope.");
  }

  lines.push("");
  lines.push("--- פירוט טכני ---");
  lines.push("HTTP " + probe.status);
  lines.push(String(probe.message || probe.raw || "").substring(0, 500));

  const report = lines.join("\n");
  Logger.log(report);
  return report;
}

// בדיקת תקינות: הריצו מהעורך; יישלח מייל בדיקה אליכם דרך Gmail API.
function testGmailApi() {

  const result = sendEmailViaGmailApi(
    Session.getEffectiveUser().getEmail(),
    "בדיקת Gmail API",
    "אם אתם רואים את זה — השליחה דרך Gmail API עובדת."
  );

  Logger.log(result.success
    ? "נשלח בהצלחה, id=" + result.messageId
    : "נכשל: " + result.error);

  return result;
}

// קידוד נושא בעברית לפי תקן RFC 2047‏ (encoded-word ב-Base64).
function encodeEmailSubject(subject) {

  return (
    "=?UTF-8?B?" +
    Utilities.base64Encode(subject, Utilities.Charset.UTF_8) +
    "?="
  );
}

// שליחת מייל אחד דרך Gmail REST API‏ (לא צורך מהמכסה של MailApp).
// מחזיר {success, messageId} בהצלחה ו-{success:false, error} בכישלון.
function sendEmailViaGmailApi(
  toEmail,
  subject,
  body
) {

  try {

    const boundary = "gas_boundary_" + Date.now();

    const mimeMessage =
      "To: " + toEmail + "\r\n" +
      "Subject: " + encodeEmailSubject(subject) + "\r\n" +
      "MIME-Version: 1.0\r\n" +
      "Content-Type: multipart/alternative; boundary=" +
      boundary + "\r\n" +
      "\r\n" +
      "--" + boundary + "\r\n" +
      "Content-Type: text/plain; charset=UTF-8\r\n" +
      "\r\n" +
      body + "\r\n" +
      "--" + boundary + "\r\n" +
      "Content-Type: text/html; charset=UTF-8\r\n" +
      "\r\n" +
      textToRtlHtml(body) + "\r\n" +
      "--" + boundary + "--\r\n";

    const response = UrlFetchApp.fetch(
      "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
      {
        method: "post",
        contentType: "application/json",
        headers: {
          "Authorization":
            "Bearer " + ScriptApp.getOAuthToken()
        },
        payload: JSON.stringify({
          raw: Utilities.base64EncodeWebSafe(
            mimeMessage,
            Utilities.Charset.UTF_8
          )
        }),
        muteHttpExceptions: true
      }
    );

    const status =
      response.getResponseCode();

    if (status >= 200 && status < 300) {

      const sentMessageId =
        JSON.parse(response.getContentText() || "{}").id || "";

      // מחיקת עותק ה"נשלח" מיד אחרי השליחה — רק כשהנמען
      // הוא כתובת אחרת. מייל שנשלח אליך בעצמך נשאר בנשלח.
      deleteSentCopy(sentMessageId, toEmail);

      return {
        success: true,
        messageId: sentMessageId
      };
    }

    // 403 הוא שתי תקלות שונות לחלוטין שנראות אותו דבר:
    //   a) ה-Gmail API כבוי בפרויקט ה-GCP שאליו משויך הסקריפט
    //      (SERVICE_DISABLED / "has not been used in project") — grantGmailScope
    //      לא עוזר כאן, צריך להפעיל את ה-API בקונסולת Google Cloud.
    //   b) חסרה הרשאת OAuth — ואז grantGmailScope הוא הפתרון.
    // 429/550 = חריגה ממגבלת השליחה היומית של Gmail עצמו.
    const errorBody =
      response.getContentText() || "";

    if (isGmailApiDisabledText(errorBody)) {

      return {
        success: false,
        error:
          "Gmail API כבוי בפרויקט ה-GCP של הסקריפט (" +
          (extractGcpProjectNumber(errorBody) || "לא ידוע") +
          "). הפעילו את Gmail API בפרויקט הזה (או חברו פרויקט GCP רגיל) " +
          "והריצו שוב את checkGmailApi. תשובת גוגל: " +
          errorBody.substring(0, 200)
      };
    }

    return {
      success: false,
      error: "Gmail API HTTP " + status + ": " +
        errorBody.substring(0, 300)
    };

  } catch (gmailError) {

    return {
      success: false,
      error: gmailError.toString()
    };
  }
}


// מחיקת עותק ה"נשלח" של מייל שנשלח דרך MailApp (הגיבוי).
// MailApp לא מחזיר מזהה הודעה, ולכן מאתרים את ההודעה לפי נמען + נושא
// בתוך חלון זמן קצר אחרי השליחה. נכשל בשקט אם לא נמצא -
// במקרה כזה הניקוי השבועי יתפוס אותו.
function deleteSentCopyBySubject(toEmail, subject) {

  try {

    const ownerEmail =
      (Session.getEffectiveUser().getEmail() || "").toLowerCase();

    const targetEmail =
      (toEmail || "").toString().trim().toLowerCase();

    if (
      !targetEmail ||
      (ownerEmail && targetEmail === ownerEmail)
    ) {
      return false;
    }

    const wantedSubject =
      (subject || "").toString().trim();

    const threads =
      GmailApp.search(
        "in:sent to:" + targetEmail + " newer_than:1d",
        0,
        10
      );

    const tenMinutesAgo =
      Date.now() - (10 * 60 * 1000);

    for (let i = 0; i < threads.length; i++) {

      const messages =
        threads[i].getMessages() || [];

      for (let m = 0; m < messages.length; m++) {

        const msg = messages[m];

        const msgSubject =
          (msg.getSubject() || "").toString().trim();

        const sentAt =
          msg.getDate().getTime();

        if (
          msgSubject === wantedSubject &&
          sentAt >= tenMinutesAgo
        ) {
          msg.moveToTrash();
          return true;
        }
      }
    }

    return false;

  } catch (err) {

    Logger.log(
      "מחיקת עותק נשלח (MailApp) נכשלה (לא קריטי): " + err
    );

    return false;
  }
}


// ============================================================
// ===== מחיקת עותק ה"נשלח" של מיילי המערכת ===================
// ============================================================
// שליחה דרך Gmail API משאירה עותק בתיבת "נשלח" של בעל החשבון.
// מיילי סטטוס ותוצאות מיותרים שם ומציפים את התיבה, ולכן מיד אחרי
// כל שליחה העותק מועבר לאשפה. הנמען מקבל את המייל כרגיל.

function deleteSentCopy(messageId, toEmail) {

  if (!messageId) {
    return false;
  }

  // מדיניות: נמחק רק העותק של מיילים שנשלחו ממך לכתובת אחרת.
  // מייל שנשלח אליך בעצמך (כמו מי שממלא את הטופס עם המייל שלו)
  // נשאר גם בנשלח וגם בתיבה הנכנסת.
  try {

    const ownerEmail =
      (Session.getEffectiveUser().getEmail() || "").toLowerCase();

    const targetEmail =
      (toEmail || "").toString().trim().toLowerCase();

    if (
      ownerEmail &&
      targetEmail &&
      targetEmail === ownerEmail
    ) {
      return false;
    }

    const msg =
      GmailApp.getMessageById(messageId);

    if (!msg) {
      return false;
    }

    msg.moveToTrash();

    return true;

  } catch (err) {

    Logger.log(
      "מחיקת עותק הנשלח נכשלה (לא קריטי): " + err
    );

    return false;
  }
}


// ============================================================
// ===== ניקוי חד-פעמי של תיבת ה"נשלח" ========================
// ============================================================
// מדיניות מחיקה:
//   נמחקת   — רק העותק בנשלח של מיילים שנשלחו ממך לכתובת אחרת
//   נשאר    — כל מייל שנשלח אליך (העותק בנשלח + ההודעה בנכנסת)
//             וכל מייל רגיל שכתבת בעצמך
//
// הרצה: מהעורך, פונקציה __נקה_את_הנשלח_ממיילי_מערכת.
// הרצה אחת סורקת עד ~2,000 שיחות בלולאות ומדווחת סה"כ.
// ההעברה היא לאשפה (נמחק סופית משם אחרי 30 יום).
//
// בנוסף, בהרצה הראשונה מותקן אוטומטית טריגר שבועי שמנקה לבד —
// רשת ביטחון למקרה שמייל מסוים לא נמחק בזמן אמת.

function cleanupSentSystemEmails() {

  ensureSentCleanupTrigger();

  // הנושאים של מיילי המערכת — רק הודעות עם הנושאים האלה נמחקות.
  const subjects = [
    "הסרטון שלך מוכן",
    "ההורדה הושלמה",
    "ההורדה נכשלה",
    "הבקשה שלך לא אושרה",
    "הקישור שנשלח אינו תקין",
    "הבקשה שלך לא בוצעה",
    "הבקשה שלך מתבצעת",
    "הקבצים שלך מוכנים",
    "הורדת עונה שלמה אינה אפשרית",
    "קוד אימות לשימוש בתוסף",
    "הורדת הערוץ החלה",
    "הורדת הערוץ הסתיימה",
    "הורדת הערוץ בוטלה",
    "הורדת הערוץ נכשלה",
    "הורדת הערוץ לא החלה",
    "הורדת העונה החלה",
    "הורדת העונה לא החלה",
    // נושאים של גרסאות ישנות שעדיין מסתובבות בנשלח
    "הורדת הערוצים המבוקשים",
    "עלה לדרייב בהצלחה",
    "תוצאות חיפוש"
  ];

  // -to:me — לא לגעת במיילים שנשלחו אליך בעצמך.
  let query = "in:sent -to:me (";

  for (let i = 0; i < subjects.length; i++) {
    query += (i > 0 ? " OR " : "") + 'subject:"' + subjects[i] + '"';
  }

  query += ")";

  try {

    // לולאות עד ניקוי מלא: עד 10 סבבים × 200 שיחות.
    //
    // חשוב: המחיקה היא ברמת הודעה בודדת ולא של שיחה שלמה. שיחת נשלח
    // יכולה לכלול גם מייל רגיל שכתבת בעצמך (למשל תשובה באותה שיחה),
    // ומעבר של השיחה כולה לאשפה היה מוחק גם אותו. כאן כל הודעה נבדקת
    // לחוד: נמחקת רק אם הנושא שלה מזוהה כמייל מערכת.
    let totalTrashed = 0;

    for (let round = 0; round < 10; round++) {

      const threads =
        GmailApp.search(query, 0, 200);

      if (!threads.length) {
        break;
      }

      for (let i = 0; i < threads.length; i++) {

        const messages =
          threads[i].getMessages() || [];

        for (let m = 0; m < messages.length; m++) {

          const msgSubject =
            (messages[m].getSubject() || "").toString();

          let isSystem = false;

          for (let s = 0; s < subjects.length; s++) {
            if (msgSubject.indexOf(subjects[s]) !== -1) {
              isSystem = true;
              break;
            }
          }

          if (isSystem) {
            messages[m].moveToTrash();
            totalTrashed++;
          }
        }
      }
    }

    if (totalTrashed === 0) {

      Logger.log(
        "✅ לא נשארו עותקי מיילי מערכת בנשלח " +
        "(מיילים שנשלחו אליך נשמרים בכוונה)."
      );

    } else {

      Logger.log(
        "🗑️ הועברו לאשפה " + totalTrashed +
        " הודעות של מיילי מערכת שנשלחו לאחרים. " +
        "מיילים שנשלחו אליך ומיילים רגילים לא נוגעו."
      );
    }

    return { trashed: totalTrashed };

  } catch (err) {

    Logger.log(
      "❌ הניקוי נכשל - כנראה חסרה הרשאת Gmail. " +
      "הריצו שוב מהעורך ואשרו את מסך ההרשאות שיופיע: " + err
    );

    return { trashed: 0, error: err.toString() };
  }
}


// מתקין טריגר שבועי לניקוי הנשלח (רשת ביטחון בלבד — ברירת המחדל
// היא מחיקה מידית אחרי כל שליחה). מנקה כפילויות אם כבר קיים.
function ensureSentCleanupTrigger() {

  try {

    const exists =
      ScriptApp.getProjectTriggers().some(function (t) {
        return t.getHandlerFunction() === "cleanupSentSystemEmails";
      });

    if (exists) {
      return;
    }

    ScriptApp
      .newTrigger("cleanupSentSystemEmails")
      .timeBased()
      .onWeekDay(ScriptApp.WeekDay.SUNDAY)
      .atHour(6)
      .create();

    Logger.log(
      "טריגר ניקוי שבועי של הנשלח הותקן (יום ראשון 06:00)."
    );

  } catch (e) {

    Logger.log(
      "התקנת טריגר הניקוי השבועי נכשלה: " + e.toString()
    );
  }
}


// זיהוי של חריגה מהמכסה היומית של שירות המייל.
// חשבון gmail.com רגיל מוגבל לכ-100 נמענים ליום, והחריגה מופיעה
// תמיד עם "Service invoked too many times for one day: email".
function isEmailQuotaError(errorText) {

  return (
    (errorText || "").toString().indexOf(
      "Service invoked too many times"
    ) !== -1
  );
}


// עטיפת שליחה שמדווחת האם המייל באמת יצא.
// עדיפות: Gmail API (המגבלה הרגילה של Gmail — 500 נמענים ליום),
// ובגיבוי MailApp המקורי (100 ליום) אם ה-API נכשל או טרם אושר.
// מחזיר true רק אם המייל נשלח בהצלחה. כישלון בגלל מכסה
// מסומן בלוג, והקוראים יכולים להוסיף אזהרה לסטטוס בגיליון.
function sendStatusEmailAndTrack(
  toEmail,
  subject,
  body
) {

  // ניסיון ראשון: Gmail API, שלא צורך את מכסת MailApp.
  const gmailResult =
    sendEmailViaGmailApi(toEmail, subject, body);

  if (gmailResult.success) {

    return true;
  }

  Logger.log(
    "שליחה דרך Gmail API נכשלה, עובר ל-MailApp: " +
    gmailResult.error
  );

  try {

    MailApp.sendEmail({

      to: toEmail,

      subject: subject,

      body: body,

      htmlBody: textToRtlHtml(body)

    });

    // גם הגיבוי משאיר עותק בנשלח - מנקים גם אותו
    deleteSentCopyBySubject(toEmail, subject);

    return true;
  } catch (mailError) {

    if (isEmailQuotaError(mailError)) {

      Logger.log(
        "⚠️ מכסת המיילים היומית נגמרה - המייל אל " +
        toEmail +
        " לא נשלח. הקישורים זמינים בגיליון."
      );

    } else {

      Logger.log(
        "שגיאה בשליחת מייל אל " +
        toEmail +
        ": " +
        mailError.toString()
      );
    }

    return false;
  }
}


// תאימות לאחור: כל הקריאות הישנות ממשיכות לעבוד, אבל עכשיו
// אפשר להשתמש ב-sendStatusEmailAndTrack כשרוצים לדעת אם המייל יצא.
function sendStatusEmail(
  toEmail,
  subject,
  body
) {

  sendStatusEmailAndTrack(toEmail, subject, body);
}


// ============================================================
// ============ גיליון משתמשי התוסף + אימות מכשיר ==============
// ============================================================
// התוסף שולח בכל לחיצה action=checkStatus עם המייל וטוקן המכשיר.
// מכשיר מזוהה לפי טוקן אקראי שנשמר אצלו ב-GM_setValue ואצלנו
// בעמודה "טוקני מכשיר". מכשיר חדש מקבל קוד בן 6 ספרות במייל,
// ורק אחריו מונפק לו טוקן.

function ensureTmSheet() {

  const ss =
    SpreadsheetApp.getActiveSpreadsheet();


  let tmSheet =
    ss.getSheetByName(
      TM_SHEET_NAME
    );


  if (!tmSheet) {

    tmSheet =
      ss.insertSheet(
        TM_SHEET_NAME
      );


    tmSheet.appendRow([
      "אימייל",
      "מכסה שעתית",
      "חסום (כן/לא)",
      "סה\"כ הורדות בתוסף",
      "מאומת (כן/לא)",
      "קוד אימות",
      "טוקני מכשיר",
      "נטפרי (פטור?)"
    ]);


    tmSheet.setFrozenRows(1);
  }


  // הוספת העמודות החדשות לגיליון שנוצר לפני השינוי
  if (
    !tmSheet.getRange(1, TM_COL_TOKENS).getValue()
  ) {

    tmSheet
      .getRange(1, TM_COL_TOKENS)
      .setValue("טוקני מכשיר");
  }

  if (
    !tmSheet.getRange(1, TM_COL_NETFREE).getValue()
  ) {

    tmSheet
      .getRange(1, TM_COL_NETFREE)
      .setValue("נטפרי (פטור?)");
  }


  return tmSheet;
}


function generateVerificationCode() {

  return Math.floor(
    100000 + Math.random() * 900000
  ).toString();
}


function readDeviceTokens(tmSheet, rowIndex) {

  const raw =
    (tmSheet.getRange(rowIndex, TM_COL_TOKENS).getValue() || "")
      .toString();


  return raw
    .split(",")
    .map(function (t) {
      return t.trim();
    })
    .filter(function (t) {
      return t;
    });
}


function issueDeviceToken(tmSheet, rowIndex) {

  const tokens =
    readDeviceTokens(tmSheet, rowIndex);


  const token =
    Utilities.getUuid();


  tokens.push(token);


  // שומרים עד 5 מכשירים לכל משתמש - הישן ביותר נזרק
  const kept =
    tokens.slice(-5);


  tmSheet
    .getRange(rowIndex, TM_COL_TOKENS)
    .setValue(kept.join(","));


  return token;
}


function sendVerificationCodeEmail(email, code) {

  sendStatusEmail(
    email,

    "🔑 קוד אימות לשימוש בתוסף ההורדות",

    "שלום,\n\n" +
    "קיבלנו בקשה לשימוש בתוסף ההורדות לדרייב " +
    "באמצעות כתובת המייל שלך.\n\n" +
    "קוד האימות שלך הוא: " + code + "\n\n" +
    "נא להזין קוד זה בחלונית שנפתחה בתוסף.\n\n" +
    "אם לא ביקשת את זה - אפשר להתעלם מהמייל."
  );
}


// ============================================================
// ============ זיהוי משתמש התוסף (מקום אחד לכולם) =============
// ============================================================
// מחזיר אובייקט שמתאר את המשתמש ואת מצב האימות שלו. משמש גם
// ל-checkStatus, גם להורדת סרטון בודד וגם להורדת ערוץ, כדי
// שהכללים יהיו זהים בכל המסלולים.

// מכסה שעתית מגיליון "משתמשי תוסף" (עמודה 2).
// מחזיר מספר, או null אם הכתובת לא שם או שאין ערך תקין.
//
// למה זה קיים: משתמש שמופיע גם ב"מאושרים" וגם ב"משתמשי תוסף"
// נבדק קודם במאושרים. אם בעמודה 13 שם אין מכסה מותאמת, בלי הפונקציה
// הזאת הוא היה מקבל את ברירת המחדל (3 לשעה) גם אם בגיליון
// משתמשי התוסף הוגדר לו אחרת - וההגדרה שלו לא הייתה מורגשת.
function getTmHourlyLimit(email) {

  try {

    const tmSheet =
      ensureTmSheet();

    const lastRow =
      tmSheet.getLastRow();

    if (lastRow < 2) {
      return null;
    }

    const data =
      tmSheet.getRange(2, 1, lastRow - 1, 2).getValues();

    const wanted =
      (email || "").toString().trim().toLowerCase();

    for (let i = 0; i < data.length; i++) {

      if (
        (data[i][0] || "").toString().trim().toLowerCase() === wanted
      ) {
        const parsed =
          parseInt(data[i][1], 10);

        return isNaN(parsed) ? null : parsed;
      }
    }

    return null;

  } catch (e) {

    Logger.log("קריאת מכסה שעתית ממשתמשי התוסף נכשלה: " + e);

    return null;
  }
}

function resolveExtensionUser(
  email,
  deviceToken,
  verificationCode
) {

  const ss =
    SpreadsheetApp.getActiveSpreadsheet();


  const approvedSheet =
    ss.getSheetByName(
      APPROVED_SHEET_NAME
    );


  const result = {
    email: email,
    found: false,
    target: "",
    rowIndex: -1,
    blocked: false,
    hourlyLimit: 3,
    netfreeExempt: false,
    authenticated: false,
    needsVerification: false,
    newDeviceToken: "",
    error: ""
  };


  if (!email) {

    result.error = "חסר אימייל";

    return result;
  }


  // ---------- 1. רשימת המאושרים הראשית ----------
  // משתמש מאושר לא צריך אימות מכשיר - הוא כבר ברשימה מפורשת.

  const approvedData =
    approvedSheet && approvedSheet.getLastRow() >= 2

      ? approvedSheet
          .getRange(
            2, 1,
            approvedSheet.getLastRow() - 1,
            13
          )
          .getValues()

      : [];


  for (let j = 0; j < approvedData.length; j++) {

    if (
      (approvedData[j][0] || "")
        .toString()
        .trim()
        .toLowerCase() !== email
    ) {
      continue;
    }


    result.found = true;
    result.target = "approved";
    result.rowIndex = j + 2;
    result.authenticated = true;


    if (
      (approvedData[j][11] || "")
        .toString()
        .trim() === "כן"
    ) {
      result.blocked = true;
    }


    if (
      (approvedData[j][10] || "")
        .toString()
        .trim() === NETFREE_EXEMPT_WORD
    ) {
      result.netfreeExempt = true;
    }


    const specificLimit =
      parseInt(approvedData[j][12], 10);


    if (!isNaN(specificLimit)) {
      result.hourlyLimit = specificLimit;
    } else {
      // אין מכסה מותאמת במאושרים - בודקים אם מוגדרת במשתמשי התוסף
      const tmOverride =
        getTmHourlyLimit(email);

      if (tmOverride !== null) {
        result.hourlyLimit = tmOverride;
      }
    }


    return result;
  }


  // ---------- 2. גיליון משתמשי התוסף ----------

  const tmSheet =
    ensureTmSheet();


  const tmLastRow =
    tmSheet.getLastRow();


  const tmData =
    tmLastRow >= 2

      ? tmSheet
          .getRange(2, 1, tmLastRow - 1, TM_COL_NETFREE)
          .getValues()

      : [];


  let rowIndex = -1;


  for (let k = 0; k < tmData.length; k++) {

    if (
      (tmData[k][TM_COL_EMAIL - 1] || "")
        .toString()
        .trim()
        .toLowerCase() === email
    ) {

      rowIndex = k + 2;

      break;
    }
  }


  // ---------- משתמש חדש לגמרי ----------

  if (rowIndex === -1) {

    const code =
      generateVerificationCode();


    tmSheet.appendRow([
      email,
      3,
      "לא",
      0,
      "לא",
      code,
      ""
    ]);


    sendVerificationCodeEmail(email, code);


    result.found = true;
    result.target = "tm";
    result.rowIndex = tmSheet.getLastRow();
    result.needsVerification = true;

    result.error =
      "שלחנו קוד אימות בן 6 ספרות למייל שלך. הכנס אותו כאן:";


    return result;
  }


  result.found = true;
  result.target = "tm";
  result.rowIndex = rowIndex;


  const rowValues =
    tmData[rowIndex - 2];


  if (
    (rowValues[TM_COL_BLOCKED - 1] || "")
      .toString()
      .trim() === "כן"
  ) {
    result.blocked = true;
  }


  const specificLimit =
    parseInt(rowValues[TM_COL_HOURLY - 1], 10);


  if (!isNaN(specificLimit)) {
    result.hourlyLimit = specificLimit;
  }


  if (
    (rowValues[TM_COL_NETFREE - 1] || "")
      .toString()
      .trim() === NETFREE_EXEMPT_WORD
  ) {
    result.netfreeExempt = true;
  }


  const isVerified =
    (rowValues[TM_COL_VERIFIED - 1] || "")
      .toString()
      .trim() === "כן";


  const tokens =
    readDeviceTokens(tmSheet, rowIndex);


  const sentToken =
    (deviceToken || "").toString().trim();


  // ---------- מכשיר מוכר ----------

  if (
    sentToken &&
    tokens.indexOf(sentToken) !== -1
  ) {

    result.authenticated = true;

    return result;
  }


  // ---------- הוזן קוד אימות ----------

  const code =
    (verificationCode || "").toString().trim();


  if (code) {

    const savedCode =
      (tmSheet.getRange(rowIndex, TM_COL_CODE).getValue() || "")
        .toString()
        .trim();


    if (savedCode && code === savedCode) {

      tmSheet
        .getRange(rowIndex, TM_COL_VERIFIED)
        .setValue("כן");

      tmSheet
        .getRange(rowIndex, TM_COL_CODE)
        .setValue("");


      result.authenticated = true;

      result.newDeviceToken =
        issueDeviceToken(tmSheet, rowIndex);


      return result;
    }


    result.needsVerification = true;

    result.error = "קוד האימות שגוי. נסה שוב:";

    return result;
  }


  // ---------- משתמש שאומת בעבר ואין לו עדיין טוקן ----------
  // מצב מעבר: מי שאומת לפני שהיו טוקנים לא צריך לאמת מחדש.

  if (isVerified && tokens.length === 0) {

    result.authenticated = true;

    result.newDeviceToken =
      issueDeviceToken(tmSheet, rowIndex);


    return result;
  }


  // ---------- מכשיר חדש - שולחים קוד ----------

  const newCode =
    generateVerificationCode();


  tmSheet
    .getRange(rowIndex, TM_COL_CODE)
    .setValue(newCode);


  sendVerificationCodeEmail(email, newCode);


  result.needsVerification = true;

  result.error =
    "שלחנו קוד אימות בן 6 ספרות למייל שלך. הכנס אותו כאן:";


  return result;
}


// ============================================================
// ============ ספירת בקשות התוסף בשעה האחרונה =================
// ============================================================

function countHourlyExtensionRequests(responsesSheet, email) {

  const lastRow =
    responsesSheet.getLastRow();


  if (lastRow < 2) {
    return 0;
  }


  const oneHourAgo =
    new Date(
      new Date().getTime() - (60 * 60 * 1000)
    );


  const respData =
    responsesSheet
      .getRange(2, 1, lastRow - 1, 7)
      .getValues();


  let count = 0;


  for (let r = 0; r < respData.length; r++) {

    const respTime =
      new Date(respData[r][0]);

    const respEmail =
      (respData[r][2] || "")
        .toString()
        .trim()
        .toLowerCase();

    const respSource =
      (respData[r][6] || "")
        .toString()
        .trim();


    if (
      respEmail === email &&
      respSource === "Tampermonkey" &&
      respTime >= oneHourAgo
    ) {
      count++;
    }
  }


  return count;
}


// ============================================================
// =================== Web App API (Tampermonkey) ==============
// ============================================================


// ============================================================
// ===== הגנת כפילויות לבקשות המגיעות ממייל החיפוש ===========
// ============================================================
// טביעת העין: סוג ההורדה + הקישור + המייל. אם אותו שילוב נשלח
// בתוך חלון הזמן — מדלגים. בקשות שונות (סרטון אחר / פורמט אחר /
// מייל אחר) או לחיצה חוזרת אחרי החלון — עוברות כרגיל.

function isEmaildlDuplicate(downloadType, url, email) {

  const token = [downloadType, (url || "").toString(), (email || "").toString()].join("|");

  const digest = Utilities.base64EncodeWebSafe(
    Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, token, Utilities.Charset.UTF_8)
  );

  const props = PropertiesService.getScriptProperties();

  const last = props.getProperty("EMAILDL_TOK_" + digest);

  if (!last) {
    return false;
  }

  const ageMin = (Date.now() - Number(last)) / 60000;

  if (ageMin < EMAILDL_TOKEN_REUSE_WINDOW_MIN) {
    Logger.log("בקשה זהה מהמייל הגיעה לפני " + Math.round(ageMin) + " דקות - מדלגים");
    return true;
  }

  return false;
}

function markEmaildlDone(downloadType, url, email) {

  const token = [downloadType, (url || "").toString(), (email || "").toString()].join("|");

  const digest = Utilities.base64EncodeWebSafe(
    Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, token, Utilities.Charset.UTF_8)
  );

  PropertiesService.getScriptProperties()
    .setProperty("EMAILDL_TOK_" + digest, String(Date.now()));
}



function jsonResponse(obj) {

  return ContentService
    .createTextOutput(
      JSON.stringify(obj)
    )
    .setMimeType(ContentService.MimeType.JSON);
}


// ============================================================
// ==================== תמונות גמיני לדרייב ===================
// ============================================================
// התוסף ל-gemini.google.com שולח לכאן כל תמונה שגמיני יוצר,
// ואנחנו מעבירים אותה לשרת ההורדות (endpoint /gemini-image)
// שמעלה אותה לדרייב. התמונה נשמרת בדרייב ולא רק בהתכתבות.
//
// זרימת האימות זהה לתוסף היוטיוב: resolveExtensionUser בודק
// מאושרים/חסומים/מכשיר, ומכסה שעתית נפרדת ונמוכה יותר מגינה
// מפני הצפת השרת בתמונות.

// כמה תמונות משתמש יכול להעלות בשעה
const GEMINI_HOURLY_LIMIT = 10;

// גודל בסיס במטה (תמונה ב-base64). שרת ההורדות מגביל בעצמו 20MB,
// אבל ל-UrlFetchApp יש תקרה משלו ואנחנו לא רוצים לגשת אליה.
const GEMINI_MAX_PAYLOAD_CHARS = 12 * 1024 * 1024;


function handleGeminiImageUpload(
  data,
  email,
  deviceToken,
  verificationCodeInput,
  logsSheet
) {

  const responsesSheet =
    SpreadsheetApp.getActiveSpreadsheet()
      .getSheetByName(RESPONSES_SHEET_NAME);

  const stamp = new Date();

  // ---------- אימות משתמש ומכשיר (זהה לתוסף היוטיוב) ----------

  const who = resolveExtensionUser(
    email,
    deviceToken,
    verificationCodeInput
  );

  if (who.blocked) {
    logsSheet.appendRow([stamp, email, "(תמונת גמיני)", "נכשל", "המשתמש חסום משימוש בתוסף"]);
    return { success: false, error: "המשתמש חסום משימוש בתוסף." };
  }

  if (!who.authenticated) {
    logsSheet.appendRow([stamp, email, "(תמונת גמיני)", "נכשל", "המכשיר טרם אומת"]);
    return {
      success: false,
      needsVerification: true,
      error: who.error || "הכתובת טרם אומתה. הכנס את קוד האימות שקיבלת במייל:"
    };
  }

  // ---------- מכסה שעתית ייעודית לתמונות ----------

  const hourlyCount = countHourlyExtensionRequests(responsesSheet, email);

  if (hourlyCount >= who.hourlyLimit + GEMINI_HOURLY_LIMIT) {
    logsSheet.appendRow([stamp, email, "(תמונת גמיני)", "נכשל",
      "הגעת למכסה השעתית (" + who.hourlyLimit + " הורדות + " + GEMINI_HOURLY_LIMIT + " תמונות)"]);
    return {
      success: false,
      error: "הגעת למכסה השעתית לתמונות (" + GEMINI_HOURLY_LIMIT + " לשעה)."
    };
  }

  // ---------- בדיקת התוכן ----------

  const imageB64 = (data.image || "").toString().trim();
  const imageUrl = (data.image_url || "").toString().trim();
  const prompt = (data.prompt || "").toString().trim();

  if (!imageB64 && !imageUrl) {
    logsSheet.appendRow([stamp, email, "(תמונת גמיני)", "נכשל", "חסר תוכן תמונה"]);
    return { success: false, error: "חסר תוכן תמונה." };
  }

  const payload = {
    email: email,
    prompt: prompt
  };

  if (imageB64) {

    if (imageB64.length > GEMINI_MAX_PAYLOAD_CHARS) {
      logsSheet.appendRow([stamp, email, "(תמונת גמיני)", "נכשל", "תמונה גדולה מדי"]);
      return { success: false, error: "התמונה גדולה מדי להעלאה." };
    }

    payload.image = imageB64;

  } else {

    // כתובת פומבית של googleusercontent - השרת ישלוף בעצמו
    if (imageUrl.indexOf("https://") !== 0) {
      logsSheet.appendRow([stamp, email, "(תמונת גמיני)", "נכשל", "כתובת תמונה לא תקינה"]);
      return { success: false, error: "כתובת התמונה אינה תקינה." };
    }

    payload.image_url = imageUrl;
  }

  // ---------- העברה לשרת ההורדות ----------

  const geminiEndpoint =
    RAILWAY_URL.replace(/\/download$/, "") + "/gemini-image";

  try {

    const response = UrlFetchApp.fetch(geminiEndpoint, {
      method: "post",
      contentType: "application/json",
      headers: {
        "X-API-KEY": API_KEY
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    });

    const code = response.getResponseCode();
    const body = response.getContentText();

    let result = {};

    try {
      result = JSON.parse(body);
    } catch (parseErr) {
      logsSheet.appendRow([stamp, email, "(תמונת גמיני)", "נכשל",
        "תשובה לא תקינה מהשרת (" + code + ")"]);
      return { success: false, error: "תשובה לא תקינה משרת ההורדות (" + code + ")." };
    }

    if (code !== 200 || !result.success) {

      const serverError = result.error || ("שגיאת שרת " + code);
      logsSheet.appendRow([stamp, email, "(תמונת גמיני)", "נכשל", serverError]);

      // העברת סימון אימות מהשרת (שכבת ה-API KEY שלו) כמו שהתוסף מצפה
      if (result.needsVerification) {
        return { success: false, needsVerification: true, error: serverError };
      }

      return { success: false, error: serverError };
    }

    // ---------- הצלחה: לוג + רישום במכסה ----------

    responsesSheet.appendRow([
      stamp,
      "(תמונת גמיני) " + prompt,
      email,
      "תמונה",
      "✅ " + (result.title || "תמונה") + " - " + (result.driveLink || ""),
      "",
      "Tampermonkey"
    ]);

    logsSheet.appendRow([stamp, email, "(תמונת גמיני)", "הושלמה",
      "הועלה לדרייב: " + (result.title || "") + " - " + (result.driveLink || "")]);

    return {
      success: true,
      title: result.title || "תמונת גמיני",
      driveLink: result.driveLink || "",
      fileId: result.fileId || ""
    };

  } catch (fetchErr) {

    logsSheet.appendRow([stamp, email, "(תמונת גמיני)", "נכשל",
      "התקשרות עם שרת ההורדות נכשלה: " + fetchErr.toString()]);

    return { success: false, error: "ההעלאה לשרת נכשלה. נסה שוב בעוד רגע." };
  }
}


// השרת ב-Railway מעלה לדרייב עם הטוקן הזה במקום refresh token
// מ-OAuth Playground. הסקריפט רץ בשם הבעלים, כך שהקבצים נכנסים לדרייב
// שלו בדיוק כמו קודם. מוגן באותו API_KEY שהסקריפט שולח לשרת.
function issueDriveToken(key) {

  if ((key || "").toString() !== API_KEY) {
    return { success: false, error: "unauthorized" };
  }

  // הפנייה ל-DriveApp מבטיחה שסקופ הדרייב ייכלל בטוקן
  DriveApp.getRootFolder();

  return {
    success: true,
    token: ScriptApp.getOAuthToken(),
    // טוקן של Apps Script חי עד שעה; השרת מחדש אחרי חצי שעה
    expiresIn: 1800
  };
}


function doPost(e) {

  let email = "לא ידוע";
  let url = "לא ידוע";

  const ss = SpreadsheetApp.getActiveSpreadsheet();

  // פתיחה או יצירה אוטומטית של גיליון הלוגים
  let logsSheet = ss.getSheetByName("לוג שגיאות ובקשות");
  if (!logsSheet) {
    logsSheet = ss.insertSheet("לוג שגיאות ובקשות");
    logsSheet.appendRow(["תאריך ושעה", "כתובת מייל", "קישור הסרטון", "סטטוס ביצוע", "פירוט / שגיאה"]);
  }

  try {
    const data = JSON.parse(e.postData.contents);

    const action = (data.action || "").toString().trim();
    email = (data.email || "").toString().trim().toLowerCase();
    const fmt = data.format || "audio";
    const deviceToken = (data.deviceToken || "").toString().trim();
    const verificationCodeInput = (data.verificationCode || "").toString().trim();

    // ========================================================
    // גשר טוקנים לשרת (drive_bridge.py): access token טרי לדרייב.
    // ראשון לפני כל השאר - זו קריאה של השרת, לא של משתמש.
    // ========================================================

    if (action === "drive_token") {

      return jsonResponse(issueDriveToken(data.key));
    }

    // ========================================================
    // בדיקת סטטוס של עבודת ערוץ.
    // חייבת להיות ראשונה: אין כאן קישור, וזו פעולה זולה
    // שלא צורכת מכסה ולא דורשת אימות מחדש.
    // ========================================================

    if (action === "job_status") {

      return jsonResponse(
        getChannelJobStatus(
          (data.jobId || "").toString().trim()
        )
      );
    }

    // ========================================================
    // אימות מכשיר - נשלח בכל פתיחה של התוסף, לפני שמוצגים
    // בכלל כפתורי וידאו/אודיו. גם כאן אין קישור.
    // ========================================================

    if (action === "checkStatus") {

      const who = resolveExtensionUser(email, deviceToken, verificationCodeInput);

      if (who.error && !who.needsVerification) {
        return jsonResponse({ success: false, error: who.error });
      }

      if (who.blocked) {
        logsSheet.appendRow([new Date(), email, "-", "נכשל", "המשתמש חסום משימוש בתוסף"]);
        return jsonResponse({ success: false, error: "המשתמש חסום משימוש בתוסף." });
      }

      if (who.needsVerification) {
        return jsonResponse({
          success: false,
          needsVerification: true,
          error: who.error
        });
      }

      return jsonResponse({
        success: true,
        authenticated: true,
        deviceToken: who.newDeviceToken || undefined
      });
    }

    // ========================================================
    // תמונות גמיני -> דרייב. אין כאן קישור יוטיוב בכלל, ולכן
    // מטופל לפני חילוץ הקישור ובדיקות המכסות של ההורדות.
    // ========================================================

    if (action === "uploadGeminiImage") {

      return jsonResponse(
        handleGeminiImageUpload(
          data,
          email,
          deviceToken,
          verificationCodeInput,
          logsSheet
        )
      );
    }

    // ========================================================
    // מכאן והלאה - פעולות שדורשות קישור
    // ========================================================

    url = extractRealYoutubeUrl(data.url);

    // האם הטופס עצמו סגור לקבלת תגובות
    try {
      const form = getGoogleForm();
      if (form && !form.isAcceptingResponses()) {
        logsSheet.appendRow([new Date(), email || "לא ידוע", url || "לא ידוע", "נכשל", "הגעת למכסה היומית (טופס סגור)"]);
        return jsonResponse({ success: false, error: "limit_reached" });
      }
    } catch (formErr) {
      console.log("התראה בבדיקת סטטוס הטופס:", formErr.toString());
    }

    // מכסה גלובלית יומית של המערכת
    const globalState = getGlobalDailyState();
    if (globalState.count >= DAILY_GLOBAL_LIMIT) {
      logsSheet.appendRow([new Date(), email || "לא ידוע", url || "לא ידוע", "נכשל", "הגעת למכסה היומית הגלובלית"]);
      return jsonResponse({ success: false, error: "limit_reached" });
    }

    if (!url || !email) {
      logsSheet.appendRow([new Date(), email || "לא ידוע", url || "לא ידוע", "נכשל", "חסר קישור או אימייל"]);
      return jsonResponse({ success: false, error: "חסר קישור או אימייל" });
    }

    const approvedSheet = ss.getSheetByName(APPROVED_SHEET_NAME);
    const responsesSheet = ss.getSheetByName(RESPONSES_SHEET_NAME);

    // ---------- זיהוי ואימות המשתמש ----------

    const who = resolveExtensionUser(email, deviceToken, verificationCodeInput);

    if (who.blocked) {
      logsSheet.appendRow([new Date(), email, url, "נכשל", "המשתמש חסום משימוש בתוסף"]);
      return jsonResponse({ success: false, error: "המשתמש חסום משימוש בתוסף." });
    }

    if (!who.authenticated) {
      logsSheet.appendRow([new Date(), email, url, "נכשל", "המכשיר טרם אומת"]);
      return jsonResponse({
        success: false,
        needsVerification: true,
        error: who.error || "הכתובת טרם אומתה. הכנס את קוד האימות שקיבלת במייל:"
      });
    }

    // ---------- מכסה שעתית ----------

    const hourlyCount = countHourlyExtensionRequests(responsesSheet, email);

    if (hourlyCount >= who.hourlyLimit) {
      logsSheet.appendRow([new Date(), email, url, "נכשל", "הגעת למכסה השעתית (" + who.hourlyLimit + " לשעה)"]);
      return jsonResponse({
        success: false,
        error: "הגעת למכסה השעתית (" + who.hourlyLimit + " לשעה)."
      });
    }

    // ========================================================
    // ערוץ שלם: תצוגה מקדימה או פתיחת עבודה ברקע
    // ========================================================

    if (
      action === "channel_preview" ||
      action === "channel_download"
    ) {

      if (!isChannelUrl(url)) {
        logsSheet.appendRow([new Date(), email, url, "נכשל", "הקישור אינו כתובת של ערוץ"]);
        return jsonResponse({ success: false, error: "הקישור אינו כתובת של ערוץ" });
      }

      // הלוג של התוסף: מה כבר ירד אצל המשתמש הזה בערוץ הזה
      const clientSkipIds = Array.isArray(data.skipIds) ? data.skipIds : [];

      if (action === "channel_preview") {

        const preview = previewChannelForUser(email, url, fmt, clientSkipIds);

        logsSheet.appendRow([new Date(), email, url, "מידע",
          "תצוגה מקדימה של ערוץ: " + (preview.willDownload || 0) + " חדשים"]);

        return jsonResponse(preview);
      }

      const started = requestChannelDownload(
        email,
        url,
        fmt,
        NETFREE_CHECK_FOR_EXTENSION && !who.netfreeExempt,
        "Tampermonkey",
        "",
        MAX_VIDEOS_PER_CHANNEL_REQUEST,
        clientSkipIds
      );

      if (started.success && started.jobId) {

        // נרשם בגיליון התגובות כדי שייספר במכסה השעתית
        responsesSheet.appendRow([
          new Date(),
          url,
          email,
          fmt === "video" ? "וידאו" : "אודיו",
          "🔄 ערוץ בעבודה (" + started.jobId + ")",
          "",
          "Tampermonkey"
        ]);

        logsSheet.appendRow([new Date(), email, url, "הושלמה",
          "עבודת ערוץ נפתחה: " + started.jobId + " (" + started.total + " סרטונים)"]);

      } else {

        logsSheet.appendRow([new Date(), email, url, "נכשל",
          "פתיחת עבודת ערוץ נכשלה: " + (started.error || "")]);
      }

      return jsonResponse(started);
    }

    // ========================================================
    // הורדת סרטון בודד
    // ========================================================

    if (!isValidVideoUrl(url)) {
      logsSheet.appendRow([new Date(), email, url, "נכשל", "קישור לא תקין"]);
      return jsonResponse({ success: false, error: "קישור לא תקין" });
    }

    // בדיקת חסימה - על כל בקשה מהתוסף, למעט מי שסומן כפטור
    if (NETFREE_CHECK_FOR_EXTENSION && !who.netfreeExempt) {

      const videoId = extractYoutubeVideoId(url);

      if (videoId) {

        const netfreeAnswer = checkNetFreeStatus(videoId);

        if (netfreeAnswer !== "open") {

          const reason =
            netfreeAnswer === "lock"
              ? "הסרטון חסום בנטפרי."
              : (netfreeAnswer === "pending"
                  ? "הסרטון עדיין לא נבדק בנטפרי, ולכן הוא חסום בפועל."
                  : "לא הצלחנו לבדוק את הסרטון מול שירות הנטפרי.");

          logsSheet.appendRow([new Date(), email, url, "נכשל", reason]);

          return jsonResponse({ success: false, error: reason });
        }
      }
    }

    // פרמטרי עונה/פרק לקישורי כאן (אופציונליים, מהטופס או מהממשק)
    const kanSeason = e && e.parameter ? e.parameter.kan_season : undefined;
    const kanEpisode = e && e.parameter ? e.parameter.kan_episode : undefined;

    const downloadResult = performDownloadOrReuse(
      url,
      fmt,
      email,
      kanSeason,
      kanEpisode
    );

    if (!downloadResult.success) {
      const errorMsg = downloadResult.error || "שגיאה בשרת ההורדות";
      logsSheet.appendRow([new Date(), email, url, "נכשל", errorMsg]);
      return jsonResponse({ success: false, error: errorMsg });
    }

    // הגישה לקובץ כבר ניתנה בתוך performDownloadOrReuse

    // קובץ ששוחזר מהמטמון אינו נספר במכסה היומית הגלובלית
    if (!downloadResult.reused) {

      addSuccessfulDownloads(1);
    }

    let cumulativeTotal = 0;

    if (who.target === "approved") {

      cumulativeTotal = updateUserStats(approvedSheet, who.rowIndex, fmt, true);

    } else if (who.target === "tm") {

      const tmSheet = ensureTmSheet();
      const currentTotal = Number(tmSheet.getRange(who.rowIndex, TM_COL_TOTAL).getValue()) || 0;
      cumulativeTotal = currentTotal + 1;
      tmSheet.getRange(who.rowIndex, TM_COL_TOTAL).setValue(cumulativeTotal);
    }

    const remainingQuota = who.hourlyLimit - (hourlyCount + 1);

    responsesSheet.appendRow([
      new Date(),
      url,
      email,
      fmt === "video" ? "וידאו" : "אודיו",
      "✅ " + downloadResult.title + " - " + downloadResult.driveLink,
      cumulativeTotal,
      "Tampermonkey"
    ]);

    logsSheet.appendRow([new Date(), email, url, "הושלמה", "✅ הצלחה - " + downloadResult.title]);

    return jsonResponse({
      success: true,
      driveLink: downloadResult.driveLink,
      title: downloadResult.title,
      remainingQuota: remainingQuota
    });

  } catch (err) {

    try {
      logsSheet.appendRow([new Date(), email, url, "נכשל", err.toString()]);
    } catch (logErr) {}

    return jsonResponse({ success: false, error: err.toString() });
  }
}


// ============================================================
// =============== אבחון עוגיות / פרוקסי ======================
// ============================================================

function diagnosticCheckCookies() {

  const FORMATS_URL =
    "https://YOUR-DOWNLOAD-SERVICE.up.railway.app/formats";


  const TEST_URL =
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ";


  const response =
    UrlFetchApp.fetch(

      FORMATS_URL,

      {

        method: "post",

        contentType:
          "application/json",

        headers: {

          "X-API-KEY":
            API_KEY

        },

        payload:
          JSON.stringify({

            url: TEST_URL,

            player_client: [
              "android"
            ],

            use_cookies: false,

            use_proxy: false

          }),

        muteHttpExceptions:
          true

      }
    );


  Logger.log(
    "קוד תגובה: " +
    response.getResponseCode()
  );


  Logger.log(
    "תוכן תגובה: " +
    response.getContentText()
  );
}


// ============================================================
// =============== בדיקה ידנית של שירות NetFree =================
// ============================================================

function TEST_CheckNetFreeService() {

  const testVideoId = "dQw4w9WgXcQ";


  const result =
    checkNetFreeStatus(
      testVideoId
    );


  if (result === "open") {

    Logger.log("השירות עובד. תוצאה: OPEN (פתוח)");

  } else if (result === "lock") {

    Logger.log("השירות עובד. תוצאה: LOCK (חסום)");

  } else if (result === "pending") {

    Logger.log("השירות עובד. תוצאה: PENDING (עדיין לא נבדק, חסום בפועל)");

  } else {

    Logger.log(
      "לא התקבלה תשובה ברורה מהשירות " +
      "(שגיאה / timeout / פורמט לא צפוי)"
    );
  }
}


// ============================================================
// ===================== בדיקות ================================
// ============================================================


function TEST_ResetDailyCounter() {

  const props =
    PropertiesService
      .getScriptProperties();


  const today =
    getTodayKey();


  props.setProperty(
    GLOBAL_DATE_KEY,
    today
  );


  props.setProperty(
    GLOBAL_COUNT_KEY,
    "0"
  );


  Logger.log(
    "המונה אופס: 0/" + DAILY_GLOBAL_LIMIT
  );
}


function TEST_SetDailyCountTo99() {

  const props =
    PropertiesService
      .getScriptProperties();


  const today =
    getTodayKey();


  props.setProperty(
    GLOBAL_DATE_KEY,
    today
  );


  props.setProperty(
    GLOBAL_COUNT_KEY,
    "99"
  );


  Logger.log(
    "המונה הוגדר ל-" + (DAILY_GLOBAL_LIMIT - 1) + "/" + DAILY_GLOBAL_LIMIT + "."
  );


  Logger.log(
    "לא בוצעה שום הורדה."
  );


  Logger.log(
    "השלב הבא: TEST_SimulateOneMoreDownload"
  );
}


function TEST_SimulateOneMoreDownload() {

  const state =
    getGlobalDailyState();


  if (
    state.count !== DAILY_GLOBAL_LIMIT - 1
  ) {

    Logger.log(
      "הבדיקה מיועדת למצב " + (DAILY_GLOBAL_LIMIT - 1) + "/" + DAILY_GLOBAL_LIMIT + "."
    );


    Logger.log(
      "כרגע המונה הוא: " +
      state.count +
      "/" + DAILY_GLOBAL_LIMIT
    );


    Logger.log(
      "הפעל קודם: TEST_SetDailyCountTo99"
    );


    return;
  }


  addSuccessfulDownloads(1);


  const newState =
    getGlobalDailyState();


  Logger.log(
    "הבדיקה הסתיימה."
  );


  Logger.log(
    "המונה עכשיו: " +
    newState.count +
    "/" + DAILY_GLOBAL_LIMIT
  );


  Logger.log(
    "הטופס אמור להיות סגור."
  );
}


function TEST_SimulateDailyLimitReached() {

  const props =
    PropertiesService
      .getScriptProperties();


  const today =
    getTodayKey();


  props.setProperty(
    GLOBAL_DATE_KEY,
    today
  );


  props.setProperty(
    GLOBAL_COUNT_KEY,
    String(
      DAILY_GLOBAL_LIMIT
    )
  );


  closeFormForDailyLimit();


  Logger.log(
    "בוצעה סימולציה של " + DAILY_GLOBAL_LIMIT + "/" + DAILY_GLOBAL_LIMIT + "."
  );


  Logger.log(
    "הטופס אמור להיות סגור."
  );
}


function TEST_SimulateNewDay() {

  const props =
    PropertiesService
      .getScriptProperties();


  const yesterday =
    new Date(
      Date.now() -
      24 * 60 * 60 * 1000
    );


  const yesterdayKey =
    Utilities.formatDate(

      yesterday,

      Session.getScriptTimeZone(),

      "yyyy-MM-dd"
    );


  props.setProperty(
    GLOBAL_DATE_KEY,
    yesterdayKey
  );


  props.setProperty(
    GLOBAL_COUNT_KEY,
    String(
      DAILY_GLOBAL_LIMIT
    )
  );


  getGlobalDailyState();


  const state =
    getGlobalDailyState();


  Logger.log(
    "בוצעה סימולציה של יום חדש."
  );


  Logger.log(
    "המונה עכשיו: " +
    state.count +
    "/" + DAILY_GLOBAL_LIMIT
  );


  Logger.log(
    "הטופס אמור להיות פתוח."
  );
}


// מדפיס את כתובת הגיליון שהסקריפט מחובר אליו, ואת כתובת הטופס.
// שימושי כשלא זוכרים איפה הכל יושב.
function TEST_ShowSheetUrl() {

  const ss =
    SpreadsheetApp.getActiveSpreadsheet();

  Logger.log("הגיליון: " + ss.getUrl());
  Logger.log("שם הגיליון: " + ss.getName());

  try {
    Logger.log(
      "עורך הסקריפט: https://script.google.com/home/projects/" +
      ScriptApp.getScriptId() + "/edit"
    );
  } catch (e) {
    Logger.log("לא הצלחנו לקרוא את מזהה הסקריפט: " + e.toString());
  }

  const names = [];

  ss.getSheets().forEach(function (sh) {
    names.push(sh.getName());
  });

  Logger.log("לשוניות: " + names.join(" | "));

  try {
    const form = getGoogleForm();
    Logger.log("הטופס (עריכה): " + form.getEditUrl());
    Logger.log("הטופס (מילוי): " + form.getPublishedUrl());
  } catch (e) {
    Logger.log("לא הצלחנו לקרוא את הטופס: " + e.toString());
  }
}


// מציג את כל הטריגרים המותקנים. שני טריגרים לאותה פונקציה
// מכפילים כל עבודה - זו הבדיקה הראשונה כשמגיעים מיילים כפולים.
function TEST_ShowTriggers() {

  const triggers =
    ScriptApp.getProjectTriggers();

  if (!triggers.length) {

    Logger.log(
      "אין טריגרים מותקנים בכלל."
    );

    return;
  }

  const counts = {};

  for (let i = 0; i < triggers.length; i++) {

    const name =
      triggers[i].getHandlerFunction();

    counts[name] = (counts[name] || 0) + 1;

    Logger.log(
      (i + 1) + ". " + name +
      "  |  " + triggers[i].getEventType()
    );
  }

  Logger.log("--------------------");

  Object.keys(counts).forEach(function (name) {

    if (counts[name] > 1) {

      Logger.log(
        "⚠️ " + name + " מותקן " + counts[name] +
        " פעמים - כל עבודה תתבצע " + counts[name] + " פעמים!"
      );
    }
  });

  Logger.log(
    "סה\"כ טריגרים: " + triggers.length
  );
}


// מוחק טריגרים כפולים ומשאיר אחד מכל פונקציה
function TEST_RemoveDuplicateTriggers() {

  const triggers =
    ScriptApp.getProjectTriggers();

  const seen = {};

  let removed = 0;

  for (let i = 0; i < triggers.length; i++) {

    const name =
      triggers[i].getHandlerFunction();

    if (seen[name]) {

      ScriptApp.deleteTrigger(triggers[i]);

      removed++;

      Logger.log("נמחק טריגר כפול: " + name);

    } else {

      seen[name] = true;
    }
  }

  Logger.log(
    removed
      ? "נמחקו " + removed + " טריגרים כפולים."
      : "לא נמצאו טריגרים כפולים."
  );
}


function TEST_ShowDailyLimitStatus() {

  const state =
    getGlobalDailyState();


  Logger.log(
    "תאריך: " +
    state.date
  );


  Logger.log(
    "הורדות היום: " +
    state.count +
    "/" +
    DAILY_GLOBAL_LIMIT
  );


  Logger.log(
    "נשארו: " +
    state.remaining
  );
}


// ============================================================
// ========== בדיקה ידנית של אימות מכשיר =======================
// ============================================================
// מדמה את מה שהתוסף שולח. יש להחליף את המייל לכתובת אמיתית.

function TEST_CheckStatusFlow() {

  const testEmail = "test@example.com";


  const first =
    resolveExtensionUser(testEmail, "", "");


  Logger.log(
    "שלב 1 (בלי טוקן): " +
    JSON.stringify(first)
  );


  Logger.log(
    "אמור להיות needsVerification=true, " +
    "ונשלח קוד למייל."
  );
}


// ============================================================
// ========== אישור אוטומטי של בקשות גישה לדרייב ================
// ============================================================
// כשמישהו שאין לו גישה לוחץ על "בקשת גישה" בקישור שהועבר אליו,
// גוגל שולח מייל לבעלים בנושא "[Google Drive] בקשת גישה" (או
// "wants to share"). אין API רשמי לרשימת הבקשות הממתינות, ולכן
// המאזין הזה סורק את תיבת המייל של הבעלים, מחלץ מהמייל את כתובת
// המבקש ואת מזהה הקובץ, ומעניק גישת-צפייה מיד בעצמו דרך ה-API.
//
// הרצה: טריגר-זמן כל 5 דקות (מותקן ע"י setupAccessRequestListener),
// וכן אפשר להריץ ידנית מהעורך כדי לבדוק.
//
// פרטיות: הסריקה נוגעת רק במיילים שנושאם מתאים לבקשות גישה של
// דרייב מ-Drive-Notification (<noreply@google.com>) ומטופלים
// ומסומנים כנקראים בהתאם. שאר התיבה לא נפתחת ולא נקראת.
// ============================================================

// טביעות עין של בקשות שכבר טופלו (מפתח -> תאריך טיפול),
// הגנה מפני טיפול כפול באותה בקשה.
const ACCESS_REQ_STATE_SHEET = "בקשות גישה";

const ARC_COL_EMAIL    = 1;
const ARC_COL_FILE     = 2;
const ARC_COL_LINK     = 3;
const ARC_COL_TIME     = 4;
const ARC_COL_RESULT   = 5;

// מזהי פורמט המייל של בקשות גישה מדרייב (שתי שפות: עברית ואנגלית)
const ACCESS_REQUEST_SUBJECT_HINTS = [
  "בקשת גישה",
  "Access request",
  "requested access",
  "ביקש גישה",
];

function ensureAccessRequestsSheet() {

  const ss = SpreadsheetApp.getActiveSpreadsheet();

  let sheet = ss.getSheetByName(ACCESS_REQ_STATE_SHEET);

  if (!sheet) {

    sheet = ss.insertSheet(ACCESS_REQ_STATE_SHEET);

    sheet.appendRow([
      "מייל המבקש",
      "מזהה קובץ",
      "קישור",
      "תאריך טיפול",
      "תוצאה",
    ]);

    sheet.getRange("A1:E1")
      .setFontWeight("bold")
      .setBackground("#00a884")
      .setFontColor("#ffffff");

    sheet.setFrozenRows(1);
    sheet.setColumnWidth(3, 420);
  }

  return sheet;
}


// מפתח טביעת-עין לבקשה (מייל + קובץ). אם הזוג הזה כבר טופל
// בשבוע האחרון - מדלגים, גם אם המייל עצמו עדיין נסרק.
function accessRequestKey(email, fileId) {

  return (String(email || "").toLowerCase() + "|" +
    String(fileId || ""));
}


function accessRequestAlreadyHandled(sheet, email, fileId) {

  const key =
    accessRequestKey(email, fileId);

  const data =
    sheet.getDataRange().getValues();

  // בדיקת זוג (מייל, קובץ) שטופל בשבוע האחרון
  const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);

  for (let i = data.length - 1; i >= 1 && i >= data.length - 60; i--) {

    const rowEmail =
      String(data[i][0] || "").toLowerCase();

    const rowFile =
      String(data[i][1] || "");

    if (rowEmail && rowFile &&
        accessRequestKey(rowEmail, rowFile) === key) {

      const when = data[i][3];

      if (when instanceof Date && when >= weekAgo) {
        return true;
      }

      // נרשם בעבר אבל ישן - הבקשה תיכנס שוב במידת הצורך
      return false;
    }
  }

  return false;
}


function logAccessRequestResult(sheet, email, fileId, link, result) {

  sheet.appendRow([
    String(email || "").toLowerCase(),
    String(fileId || ""),
    String(link || ""),
    new Date(),
    result,
  ]);
}


// חילוץ מזהה הקובץ/התיקייה מתוך גוף המייל.
// גוגל שולח את הבקשה עם קישור לקובץ בצורות שונות:
//   https://drive.google.com/file/d/FILE_ID/view?usp=sharing
//   https://drive.google.com/open?id=FILE_ID
//   https://drive.google.com/drive/folders/FOLDER_ID
function extractDriveIdFromText(text) {

  if (!text) return "";

  const patterns = [
    /drive\.google\.com\/(?:file\/d\/|open\?id=|folders\/)([A-Za-z0-9_-]{20,})/,
    /\/d\/([A-Za-z0-9_-]{20,})/,
  ];

  for (let p = 0; p < patterns.length; p++) {

    const m =
      String(text).match(patterns[p]);

    if (m && m[1]) {
      return m[1];
    }
  }

  return "";
}


// חילוץ כתובת המבקש מתוך גוף המייל.
// במיילי בקשות גישה כתובת המבקש מופיעה בגוף
// (כמו "someone@gmail.com requested access").
function extractRequesterEmailFromText(text) {

  if (!text) return "";

  const m =
    String(text).match(
      /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/
    );

  return m ? m[0] : "";
}


function isAccessRequestMessage(subject, from) {

  const s =
    String(subject || "").toLowerCase();

  const f =
    String(from || "").toLowerCase();

  if (f.indexOf("noreply@google.com") === -1) {
    return false;
  }

  for (let i = 0; i < ACCESS_REQUEST_SUBJECT_HINTS.length; i++) {

    if (s.indexOf(ACCESS_REQUEST_SUBJECT_HINTS[i].toLowerCase()) !== -1) {
      return true;
    }
  }

  return false;
}


function grantAccessViaDriveApi(fileId, email) {

  try {

    DriveApp.getFileById(fileId)
      .addViewer(email);

    return true;

  } catch (e) {

    Logger.log(
      "אישור בקשת גישה נכשל (" + fileId +
      " -> " + email + "): " + e.toString()
    );

    return false;
  }
}


function processAccessRequests() {

  // קריאה ישירה דורשת את הסקופ gmail.readonly -
  // מוגדר במניפסט (appsscript.json).
  const threads = GmailApp.search(
    'from:noreply@google.com (subject:"בקשת גישה" OR subject:"Access request" OR subject:"requested access") is:unread',
    0,
    20
  );

  if (!threads.length) {
    Logger.log("אין בקשות גישה חדשות.");
    return { processed: 0, granted: 0 };
  }

  const sheet =
    ensureAccessRequestsSheet();

  let processed = 0;
  let granted = 0;

  for (let t = 0; t < threads.length; t++) {

    const messages =
      threads[t].getMessages();

    for (let m = 0; m < messages.length; m++) {

      const msg =
        messages[m];

      if (!msg.isUnread()) {
        continue;
      }

      const subject =
        msg.getSubject() || "";

      const from =
        msg.getFrom() || "";

      if (!isAccessRequestMessage(subject, from)) {
        continue;
      }

      const body =
        msg.getPlainBody() || "";

      const fileId =
        extractDriveIdFromText(body);

      const requesterEmail =
        extractRequesterEmailFromText(body);

      processed++;

      if (!fileId || !requesterEmail) {

        logAccessRequestResult(
          sheet,
          requesterEmail || "לא זוהה",
          fileId || "לא זוהה",
          msg.getPermalink(),
          "⚠️ לא הצליח לחלץ פרטים"
        );

        continue;
      }

      if (accessRequestAlreadyHandled(sheet, requesterEmail, fileId)) {

        logAccessRequestResult(
          sheet,
          requesterEmail,
          fileId,
          msg.getPermalink(),
          "⏭️ כבר טופל לאחרונה"
        );

        continue;
      }

      const ok =
        grantAccessViaDriveApi(fileId, requesterEmail);

      logAccessRequestResult(
        sheet,
        requesterEmail,
        fileId,
        msg.getPermalink(),
        ok ? "✅ גישה הוענקה" : "❌ נכשל"
      );

      if (ok) {
        granted++;
      }
    }

    // מסומנים כנקראים כדי שלא ייסרקו שוב גם אם הטיפול נכשל -
    // המייל שהגיע שוב ייצור בקשה חדשה עם מייל חדש.
    threads[t].markRead();
  }

  Logger.log(
    "בקשות גישה: נסרקו " + processed +
    ", אושרו " + granted
  );

  return { processed: processed, granted: granted };
}


// מתקין את הטריגר-זמן (כל 5 דקות) להרצת המאזין.
// מריצים פעם אחת מהעורך; מוחק טריגרים קיימים של אותה פונקציה
// קודם כדי לא להכפיל.
function setupAccessRequestListener() {

  const existing =
    ScriptApp.getProjectTriggers();

  for (let i = 0; i < existing.length; i++) {

    if (existing[i].getHandlerFunction() ===
        "processAccessRequests") {

      ScriptApp.deleteTrigger(existing[i]);
    }
  }

  ScriptApp.newTrigger("processAccessRequests")
    .timeBased()
    .everyMinutes(5)
    .create();

  Logger.log(
    "✅ מאזין בקשות הגישה מותקן (כל 5 דקות). " +
    "הרצה ראשונה תתבצע בדקות הקרובות."
  );
}


// מוחק את הטריגר (למקרה שתרצה לעצור את האישור האוטומטי)
function removeAccessRequestListener() {

  const existing =
    ScriptApp.getProjectTriggers();

  let removed = false;

  for (let i = 0; i < existing.length; i++) {

    if (existing[i].getHandlerFunction() ===
        "processAccessRequests") {

      ScriptApp.deleteTrigger(existing[i]);
      removed = true;
    }
  }

  Logger.log(
    removed
      ? "המאזין הוסר."
      : "לא נמצא מאזין."
  );
}


// ============================================================
// ==== שמות הפעלה בעברית — לתפריט הפונקציות של העורך ==========
// ============================================================
// כל פונקציה שמתחילה ב-__ היא כינוי בעברית לפונקציה האנגלית —
// הפעלה שלה זה בדיוק אותו דבר כמו הפעלה של השם האנגלי.
// הטריגרים האוטומטיים (שעונים פנימיים של גוגל) נשארים מחוברים
// לשמות האנגליים וממשיכים לעבוד בדיוק כמו קודם.

// סוגרים את טופס ההורדות לשאר היום (כשהמכסה היומית נגמרה).
function __סגור_את_הטופס_להיום() {
  closeFormForDailyLimit();
}

// פותחים את הטופס מחדש (למשל בבוקר של יום חדש).
function __פתח_את_הטופס_ליום_חדש() {
  openFormForNewDay();
}

// מתקין את המאזין שמאשר אוטומטית בקשות גישה לקבצים בדרייב (כל 5 דקות).
// בהרצה הראשונה גוגל יבקש אישור הרשאות — יש לאשר.
function __התקן_מאזין_בקשות_גישה() {
  setupAccessRequestListener();
}

// מסיר את המאזין (חוזרים לאישור ידני של בקשות גישה).
function __הסר_מאזין_בקשות_גישה() {
  removeAccessRequestListener();
}

// מריץ את סריקת בקשות הגישה מיד, בלי לחכות לטריגר.
function __טפל_בקשות_גישה_עכשיו() {
  processAccessRequests();
}

// אבחון עוגיות היוטיוב של השרת.
function __אבחון_עוגיות() {
  diagnosticCheckCookies();
}

// אישור חד-פעמי של הרשאת שליחת המייל (Gmail).
function __אשר_הרשאת_שליחת_מייל() {
  grantGmailScope();
}

// בדיקה ששליחת מייל עובדת.
function __בדוק_שליחת_מייל() {
  testGmailApi();
}

// עיבוד ידני מיידי של השורות הממתינות בטופס - אותה פונקציה שהטריגר
// מריץ כל 5 דקות. שימושי כשהשורות נשארות ריקות: ההרצה מהעורך
// מטפלת בכל השורות עכשיו, ואם הטריגר האוטומטי נעלם היא גם מתקינה
// אותו מחדש.
function __עבד_בקשות_טופס_עכשיו() {
  checkFormResponses();
}

// שחרור נעילות פנימיות תקועות (רק אם המערכת קפואה).
function __שחרר_נעילות() {
  TEST_ReleaseAllLocks();
}

// בדיקה ששירות נטפרי מגיב.
function __בדוק_שירות_נטפרי() {
  TEST_CheckNetFreeService();
}

// איפוס המונה היומי של ההורדות.
function __אפס_מונה_יומי() {
  TEST_ResetDailyCounter();
}

// הצגת סטטוס המכסה היומית (כמה הורדות נותרו היום).
function __הצג_סטטוס_מכסה_יומית() {
  TEST_ShowDailyLimitStatus();
}

// הצגת כתובת גיליון הניהול.
function __הצג_כתובת_גיליון() {
  TEST_ShowSheetUrl();
}

// הצגת כל הטריגרים הפעילים בפרויקט (מה רץ אוטומטית).
function __הצג_טריגרים_פעילים() {
  TEST_ShowTriggers();
}

// מחיקת טריגרים כפולים (אם משהו רץ פעמיים).
function __נקה_טריגרים_כפולים() {
  TEST_RemoveDuplicateTriggers();
}

// בדיקת תקינות זרימת הסטטוס.
function __בדוק_זרימת_סטטוס() {
  TEST_CheckStatusFlow();
}

// הדמיות לבדיקה (זהירות — משנות נתונים):

// מציב את המונה על 99 (לקראת ההגבלה).
function __הדמיה_מונה_ל99() {
  TEST_SetDailyCountTo99();
}

// מדמה הורדה נוספת אחת.
function __הדמיה_הורדה_נוספת() {
  TEST_SimulateOneMoreDownload();
}

// מדמה הגעה למכסה היומית המלאה.
function __הדמיה_מכסה_מוגמרת() {
  TEST_SimulateDailyLimitReached();
}

// מדמה מעבר ליום חדש (איפוס אוטומטי).
function __הדמיה_יום_חדש() {
  TEST_SimulateNewDay();
}

// מעביר לאשפה את כל עותקי מיילי המערכת שהצטברו בתיבת "נשלח"
// (סטטוס הורדות, תוצאות חיפוש, קודי אימות). הריצו שוב עד שהלוג
// מדווח שלא נשארו. מיילים רגילים שלך לא נוגעים.
function __נקה_את_הנשלח_ממיילי_מערכת() {
  cleanupSentSystemEmails();
}


// ============================================================
// ===== פקודות במייל (תחליף לבוט הטלגרם) ====================
// ============================================================
// כתובות מייל מאושרות שולחות פקודה כנושא של מייל אל חשבון
// הגוגל שבו הסקריפט רץ, והסקריפט סורק את התיבה הנכנסת שלו
// (הסקריפט רץ בתוך החשבון הזה, אז GmailApp רואה את ההודעות).
//
// פקודות (בנושא):
//   הורד <קישור>            — הורדת אודיו (ברירת מחדל)
//   הורד וידאו <קישור>       — הורדת וידאו
//   הקלט <ערוץ> <דקות>       — הקלטת שידור חי (ברירת מחדל: 12 60)
//   עצור הקלטה               — עצירה והעלאה ל-Drive
//   מצב                     — סטטוס השרת, ההקלטה והעבודות
//
// כל פקודה דורשת שהשולח יופיע בגיליון המאושרים. תשובה נשלחת
// חזרה לשולח עם התוצאה, וההודעה מסומנת כנקראה (כדי לא לעבד פעמיים).
// ============================================================

const CMDS_PROCESSED_LABEL = "מערכת-הורדות/פקודה-טופלה";
const CMDS_MAX_PER_RUN = 10;

function cmdNormalizeEmail_(e) {
  const s = (e || "").toString().trim().toLowerCase();
  if (s.endsWith("@gmail.com")) {
    return s.split("@")[0].replace(/\./g, "") + "@gmail.com";
  }
  return s;
}

function cmdIsApproved_(email) {
  const norm = cmdNormalizeEmail_(email);
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet =
    ss.getSheetByName(APPROVED_SHEET_NAME) || ss.getSheets()[0];

  const data =
    sheet.getLastRow() >= 2
      ? sheet.getRange(2, 1, sheet.getLastRow() - 1, 1).getValues()
      : [];

  for (let i = 0; i < data.length; i++) {
    if (
      cmdNormalizeEmail_(data[i][0]) === norm
    ) {
      return true;
    }
  }

  return false;
}

function cmdMarkProcessed_(thread, label) {
  try {
    const labels = GmailApp.getUserLabels();
    let existing = null;
    for (let i = 0; i < labels.length; i++) {
      if (labels[i].getName() === label) {
        existing = labels[i];
        break;
      }
    }
    if (!existing) {
      existing = GmailApp.createLabel(label);
    }
    existing.addToThread(thread);
    thread.markRead();
    // מעביר את הפקודה מהתיבה הנכנסת לארכיון — כך התיבה לא מוצפת
    // במיילי פקודות. ההודעה נשארת נגישה תחת התווית למעקב.
    thread.moveToArchive();
  } catch (e) {
    Logger.log("סימון פקודה כמטופלת נכשל (לא קריטי): " + e);
  }
}

function cmdReply_(toEmail, subject, body) {
  sendStatusEmailAndTrack(toEmail, subject, body);
}

function parseCommand_(subject) {
  const s = (subject || "").toString().trim();

  let m = s.match(/^הורד\s+וידאו\s+(\S+)$/i);
  if (m && /^https?:\/\//i.test(m[1])) {
    return { cmd: "download", fmt: "video", url: m[1].trim() };
  }

  m = s.match(/^הורד\s+(\S+)$/i);
  if (m && /^https?:\/\//i.test(m[1])) {
    return { cmd: "download", fmt: "audio", url: m[1].trim() };
  }

  m = s.match(/^הקלט(?:\s+(\S+))?(?:\s+(\d+))?$/i);
  if (m) {
    return {
      cmd: "record",
      channel: m[1] || "12",
      minutes: m[2] ? parseInt(m[2], 10) : 60,
    };
  }

  if (/^עצור\s+הקלטה$/i.test(s)) {
    return { cmd: "stoprecord" };
  }

  if (/^מצב$/i.test(s)) {
    return { cmd: "status" };
  }

  return null;
}

function executeCommand_(cmd, senderEmail) {
  const base =
    "https://YOUR-DOWNLOAD-SERVICE.up.railway.app";
  const headers = {
    "X-API-KEY": API_KEY,
  };

  try {
    if (cmd.cmd === "download") {
      const resp = UrlFetchApp.fetch(base + "/download", {
        method: "post",
        contentType: "application/json",
        headers: headers,
        payload: JSON.stringify({
          url: cmd.url,
          format: cmd.fmt,
          email: senderEmail,
        }),
        muteHttpExceptions: true,
      });
      const data = JSON.parse(resp.getContentText());

      if (!data.success) {
        return "❌ ההורדה נדחתה: " + (data.error || "לא ידוע");
      }
      if (data.driveLink) {
        return "🎉 הקובץ מוכן ב-Drive:\n" + data.driveLink;
      }
      if (data.jobId) {
        return (
          "⏳ ההורדה נרשמה כעבודת רקע (" + (data.total || "?") +
          " פריטים). הקבצים ישותפו למייל שלך בסיום.\nמזהה: " + data.jobId
        );
      }
      return "⏳ ההורדה התקבלה ומתבצעת. הקובץ ישותף למייל שלך.";
    }

    if (cmd.cmd === "record") {
      const resp = UrlFetchApp.fetch(base + "/record/start", {
        method: "post",
        contentType: "application/json",
        headers: headers,
        payload: JSON.stringify({
          channel: cmd.channel,
          minutes: cmd.minutes,
          notify_email: senderEmail,
        }),
        muteHttpExceptions: true,
      });
      const data = JSON.parse(resp.getContentText());

      if (!data.success) {
        return "❌ ההקלטה לא התחילה: " + (data.error || "לא ידוע");
      }
      return (
        "🔴 ההקלטה של ערוץ " + data.recording.channel + " התחילה ל-" +
        data.recording.minutes + " דקות.\nבסיום הקובץ יעלה ל-Drive " +
        "וישותף למייל שלך. עצירה מוקדמת: שלח מייל עם הנושא \"עצור הקלטה\"."
      );
    }

    if (cmd.cmd === "stoprecord") {
      const resp = UrlFetchApp.fetch(base + "/record/stop", {
        method: "post",
        contentType: "application/json",
        headers: headers,
        payload: "{}",
        muteHttpExceptions: true,
      });
      const data = JSON.parse(resp.getContentText());

      if (!data.success) {
        return "❌ העצירה נכשלה: " + (data.error || "לא ידוע");
      }
      return "⏹ ההקלטה נעצרת — העלאה ל-Drive תימשך דקות אחדות.";
    }

    if (cmd.cmd === "status") {
      const parts = [];

      try {
        const rec = JSON.parse(
          UrlFetchApp.fetch(base + "/record/list", {
            headers: headers,
            muteHttpExceptions: true,
          }).getContentText()
        );
        if (rec.current && rec.current.state === "recording") {
          parts.push(
            "🔴 מקליט ערוץ " + rec.current.channel + " — " +
            (rec.current.elapsed_minutes || 0) + " מתוך " +
            rec.current.minutes + " דקות"
          );
        } else if (rec.current && rec.current.state === "done") {
          parts.push("✅ הקלטה אחרונה הועלתה ל-Drive");
        } else {
          parts.push("אין הקלטה פעילה");
        }
      } catch (e) {
        parts.push("מצב ההקלטה לא זמין");
      }

      try {
        const jobs = JSON.parse(
          UrlFetchApp.fetch(base + "/jobs/recent", {
            headers: headers,
            muteHttpExceptions: true,
          }).getContentText()
        );
        const list = (jobs.jobs || []).slice(0, 5);
        if (list.length) {
          parts.push("\nעבודות אחרונות:");
          for (let i = 0; i < list.length; i++) {
            parts.push(
              "• [" + list[i].status + "] " +
              ((list[i].channel || list[i].url || "").slice(0, 60)) +
              " — " + (list[i].done || 0) + "/" + (list[i].total || 0)
            );
          }
        } else {
          parts.push("אין עבודות אחרונות");
        }
      } catch (e) {
        parts.push("מצב העבודות לא זמין");
      }

      return parts.join("\n");
    }
  } catch (err) {
    return "❌ שגיאת תקשורת עם השרת: " + err;
  }

  return "פקודה לא מוכרת.";
}

function processEmailCommands() {
  const ownerEmail =
    (Session.getEffectiveUser().getEmail() || "").toLowerCase();

  const threads = GmailApp.search(
    "is:unread -from:me subject:(הורד) " +
    "OR subject:(הקלט) OR subject:(עצור הקלטה) OR subject:(מצב)",
    0,
    20
  );

  if (!threads.length) {
    Logger.log("אין פקודות חדשות במייל.");
    return { processed: 0 };
  }

  let processed = 0;

  for (let i = 0; i < threads.length && processed < CMDS_MAX_PER_RUN; i++) {
    const messages = threads[i].getMessages();
    const latest = messages[messages.length - 1];

    if (!latest || !latest.isUnread()) {
      continue;
    }

    const senderMatch = (latest.getFrom() || "").match(/<([^>]+)>/);
    const sender = (
      senderMatch ? senderMatch[1] : latest.getFrom() || ""
    )
      .trim()
      .toLowerCase();

    // דילוג על מיילי מערכת ועל מיילים שנשלחו מהחשבון עצמו
    if (!sender || sender === ownerEmail || sender.indexOf("noreply") !== -1) {
      continue;
    }

    const subject = latest.getSubject() || "";
    const cmd = parseCommand_(subject);

    if (!cmd) {
      continue;
    }

    if (!cmdIsApproved_(sender)) {
      // כתובת לא מאושרת — שתי מקרים:
      // 1) נראה כמו פקודה אמיתית (יש קישור בנושא) — שולחים דחייה ומארכבים.
      // 2) מייל רגיל שנפל בצירוף מקרים למילת הפקודה — לא נוגעים בו בכלל:
      //    נשאר בתיבה הנכנסת, לא נקרא, לא נארכב, לא נשלחת תשובה.
      if ((subject || "").indexOf("http") !== -1) {
        cmdReply_(
          sender,
          "❌ פקודה נדחתה — לא מאושר",
          "הכתובת " + sender + " לא מופיעה ברשימה המאושרת, ולכן הפקודה \"" +
            subject + "\" לא בוצעה."
        );
        cmdMarkProcessed_(threads[i], CMDS_PROCESSED_LABEL);
        processed++;
      }
      continue;
    }

    Logger.log("פקודה מ-" + sender + ": " + subject);

    const resultText = executeCommand_(cmd, sender);

    cmdReply_(sender, "תשובה: " + subject, resultText);
    cmdMarkProcessed_(threads[i], CMDS_PROCESSED_LABEL);
    processed++;
  }

  Logger.log("טופלו " + processed + " פקודות מייל.");
  return { processed: processed };
}

// מתקין טריגר שרץ כל 5 דקות ומעבד פקודות מייל. רצים פעם אחת מהעורך.
function ensureEmailCommandsTrigger() {
  const exists = ScriptApp.getProjectTriggers().some(function (t) {
    return t.getHandlerFunction() === "processEmailCommands";
  });

  if (exists) {
    Logger.log("טריגר פקודות המייל כבר קיים (כל 5 דקות).");
    return;
  }

  ScriptApp.newTrigger("processEmailCommands")
    .timeBased()
    .everyMinutes(5)
    .create();

  Logger.log("✅ טריגר פקודות המייל הותקן — סריקה כל 5 דקות.");
  Logger.log("הודעת בדיקה: שלח מייל לעצמך עם הנושא: מצב");
}

// בדיקה ידנית מהעורך: מריץ סריקה אחת מיד.
function __בדוק_פקודות_מייל() {
  processEmailCommands();
}

// התקנת הטריגר לפקודות מייל (פעם אחת מהעורך).
function __התקן_טריגר_פקודות_מייל() {
  ensureEmailCommandsTrigger();
}
