// ============================================================
// הגדרות (לא כולל סודות — המפתח ב-Script Properties)
// ============================================================

var APPROVED_SHEET_ID = "YOUR_APPROVED_SPREADSHEET_ID";
var SEARCH_SERVER_URL = "https://YOUR-SEARCH-SERVICE.up.railway.app/search";
var RESULTS_LIMIT = 5;
var SEARCH_LOG_TAB = "חיפושים";
// מזהה הטופס אליו הסקריפט מחובר (משמש ליצירת טריגר ב-fixTriggers)
var FORM_ID = "YOUR_YOUTUBE_SEARCH_FORM_ID";
// לוגו בכותרת המייל. משמש כתמונת הרקע של פס הכותרת —
// "תוצאות חיפוש" ומילות החיפוש יושבות עליו עם מסך כהה לקריאות.
// אם הקישור כאן ריק — הכותרת מוצגת על רקע כהה רגיל, בלי לשבור כלום.
var LOGO_URL = "";

// חתימה בתחתית המייל (אופציונלי). כל שדה ריק פשוט לא מוצג.
var CREDIT_NAME = "";        // למשל: "פותח על ידי ..."
var PROFILE_URL = "";        // קישור לפרופיל/אתר שלך
var PROFILE_IMAGE_URL = "";  // תמונה עגולה ליד הכותרת (קישור ישיר לתמונה)

// ===================== כפתורי הורדה במייל (אינטגרציה) =====================
// לכל תוצאה מתווספים כפתורי "וידאו" ו"אודיו" שפותחים את טופס ההורדות
// עם הכל ממולא מראש: הקישור, סוג ההורדה, והמייל של הנמען (נאסף אוטומטית
// על ידי גוגל). הנמען רק לוחץ "שליחה" — וההורדה עוברת את כל הבדיקות
// הרגילות של מערכת ההורדות (מאושרים, מכסות, נטפרי, מטמון).
// זה docs.google.com — עמוד מוכר שמותר בכל הסינונים, בלי דפים חדשים.
// כתובת הטופס (viewform) + מזהי השדות שלו.
// שים לב: לכל שאלה יש שני מזהים — מזהה פריט פנימי (item id) ומזהה הגשה
// (submission entry). גוגל ממלא מראש רק כששולחים למזהה ההגשה. מזהה ההגשה
// מוצאים דרך "קבלת קישור ממולא מראש" בתפריט הטופס (ראו המדריך).
var DOWNLOAD_FORM_BASE_URL = "https://docs.google.com/forms/d/e/YOUR_DOWNLOAD_FORM_PUBLIC_ID/viewform";
var DOWNLOAD_FORM_ENTRY_URL = "entry.YOUR_URL_FIELD_ENTRY_ID";
var DOWNLOAD_FORM_ENTRY_TYPE = "entry.YOUR_TYPE_FIELD_ENTRY_ID";
// סימון המוטמע בתוך הכתובת עצמה — כך מערכת ההורדות מזהה שהבקשה
// הגיעה ממייל ומפעילה הגנת כפילויות (הפרמטר לא מפריע לאף שלב)
// גם כפתור "טופס הורדות ידני" בפוטר נפתח לכאן.
var EMAILDL_URL_MARKER = "via=email-search";

// פלטת המותג — נשאבה מהלוגו עצמו (קשת: אדום, מג'נטה, כחול, טורקיז, צהוב)
var BRAND_GRADIENT = "linear-gradient(90deg,#ff2a2a 0%,#ff2aa8 35%,#2a6bff 70%,#00d4ff 100%)";
var BRAND_GRADIENT_BTN = "linear-gradient(135deg,#ff2a2a 0%,#ff2aa8 35%,#2a6bff 70%,#00d4ff 100%)";
var BRAND_COLORS = ["#ff2a2a", "#ff2aa8", "#2a6bff", "#00d4ff", "#ffb800"];
// מסגרת גרדיאנט יוקרתית — טבעת דקה סביב כל חלונית (כותרת, כרטיסים, פוטר)
var BRAND_BORDER_GRADIENT = "linear-gradient(135deg,rgba(255,42,42,0.70) 0%,rgba(255,42,158,0.70) 30%,rgba(42,107,255,0.70) 68%,rgba(0,212,255,0.70) 100%)";

function getApiKey() {
  return PropertiesService.getScriptProperties().getProperty("API_KEY") || "";
}


// ============================================================
// בדיקת הגדרות — מריצים פעם אחת מהעורך
// ============================================================

function checkSetup() {
  var missing = [];

  if (!getApiKey()) missing.push("API_KEY (Script Properties)");

  try {
    var resp = UrlFetchApp.fetch("https://YOUR-SEARCH-SERVICE.up.railway.app/", { muteHttpExceptions: true });
    if (resp.getResponseCode() !== 200) missing.push("שרת החיפוש לא מגיב (HTTP " + resp.getResponseCode() + ")");
  } catch (err) {
    missing.push("שרת החיפוש לא נגיש: " + err);
  }

  try {
    SpreadsheetApp.openById(APPROVED_SHEET_ID);
  } catch (err) {
    missing.push("גיליון המאושרים לא נגיש: " + err);
  }

  if (missing.length === 0) {
    Logger.log("✅ הכל תקין! המפתח מוגדר, השרת מגיב והגיליון נגיש.");
  } else {
    Logger.log("❌ בעיות שנמצאו:\n- " + missing.join("\n- "));
  }
}


// ============================================================
// בדיקה ידנית — מריצים מהעורך כדי לבדוק את כל השרשרת
// (חיפוש בשרת + שליחת מייל + רישום בגיליון) בלי הטופס
// ============================================================

function testSearchAndEmail() {

  var email = Session.getActiveUser().getEmail();
  var query = "מוטי שטיינמץ הנשמה בקרבי";

  Logger.log("מריץ חיפוש בדיקה עבור: " + email);

  var results = searchYoutube(query);

  Logger.log("החיפוש החזיר " + results.length + " תוצאות");

  sendResultsEmail(email, query, results);

  logSearch(email, query, results, "נשלח בהצלחה (בדיקה ידנית)");

  Logger.log("✅ מייל בדיקה נשלח ל: " + email + " — בדוק את תיבת הדואר וגם ספאם");
}


// ============================================================
// תיקון טריגרים — מריצים פעם אחת מהעורך אם הטופס לא שולח מייל
// מוודא שיש בדיוק טריגר אחד על שליחת טופס (מוחק כפילויות,
// יוצר חדש אם חסר)
//
// דורש הרשאת script.scriptapp — אם היא חסרה במסך האישור, הפונקציה
// מדפיסה הודעה ברורה במקום לקרוס, ומסבירה איך לתקן.
// שים לב: עצם הרצת onFormSubmit (הטריגר עצמו) לא צריכה את ההרשאה
// הזו — רק קריאה/יצירה/מחיקה של טריגרים מקוד.
// ============================================================

function fixTriggers() {

  // פותחים את הטופס לפי מזהה ישירות (הגיליון שלנו הוא לא גיליון-תשובות של הטופס,
  // ולכן getFormUrl() עליו לא עובד)
  var form = FormApp.openById(FORM_ID);

  var existing;
  try {
    existing = ScriptApp.getProjectTriggers();
  } catch (permErr) {
    Logger.log("❌ אין הרשאה לנהל טריגרים: " + permErr.message);
    Logger.log("הפתרון: הריצו שוב את מסך האישור של הסקריפט (כל פונקציה מהעורך → " +
      "'Review permissions') וודאו שההרשאה 'ניהול טריגרים חיצוניים' מאושרת.\n" +
      "או התקינו את הטריגר ידנית: בעורך לחצו על הסמל השעון (Triggers) ← " +
      "Add Trigger ← פונקציה: onFormSubmit ← event source: From form ← On form submit");
    Logger.log("טופס: " + form.getEditUrl());
    return;
  }

  var formTriggers = 0;

  for (var i = 0; i < existing.length; i++) {
    if (existing[i].getHandlerFunction() === "onFormSubmit") {
      formTriggers++;
      if (formTriggers > 1) {
        ScriptApp.deleteTrigger(existing[i]);
        Logger.log("נמחק טריגר כפול");
      }
    }
  }

  if (formTriggers === 0) {
    ScriptApp.newTrigger("onFormSubmit").forForm(form).onFormSubmit().create();
    Logger.log("✅ נוצר טריגר חדש על שליחת הטופס");
  } else {
    Logger.log("✅ קיים טריגר אחד תקין על שליחת הטופס");
  }

  Logger.log("טופס: " + form.getEditUrl());
}


// ============================================================
// פונקציה ראשית - רצה אוטומטית בכל שליחה של הטופס
// ============================================================

function onFormSubmit(e) {

  var respondentEmail = null;
  var query = null;

  try {

    respondentEmail = e.response.getRespondentEmail();

    if (!respondentEmail) {
      Logger.log("No respondent email found - form is not set to collect verified emails.");
      return;
    }

    if (!isApproved(respondentEmail)) {
      Logger.log("Rejected - not approved: " + respondentEmail);
      return;
    }

    query = getQueryFromResponse(e.response);

    if (!query) {
      Logger.log("No search query found in the form response.");
      return;
    }

    var results = searchYoutube(query);

    sendResultsEmail(respondentEmail, query, results);

    logSearch(respondentEmail, query, results, "נשלח בהצלחה");

  } catch (err) {

    Logger.log("Error in onFormSubmit: " + err);

    try {
      logSearch(respondentEmail || "לא ידוע", query || "לא ידוע", [], "שגיאה: " + err);
    } catch (logErr) {
      Logger.log("Failed to write error to search log: " + logErr);
    }
  }
}


// ============================================================
// רישום חיפוש בגיליון - לשונית "חיפושים"
// ============================================================

function logSearch(email, query, results, status) {

  var ss = SpreadsheetApp.openById(APPROVED_SHEET_ID);
  var sheet = ss.getSheetByName(SEARCH_LOG_TAB);

  // יצירת הלשונית עם כותרות בפעם הראשונה
  if (!sheet) {
    sheet = ss.insertSheet(SEARCH_LOG_TAB);
    sheet.appendRow(["תאריך ושעה", "אימייל", "מילות חיפוש", "מספר תוצאות", "כותרות שנשלחו", "סטטוס"]);
    sheet.getRange("A1:F1").setFontWeight("bold").setBackground("#2a6bff").setFontColor("#ffffff");
    sheet.setFrozenRows(1);
    sheet.setColumnWidth(3, 260);
    sheet.setColumnWidth(5, 420);
  }

  var titles = "";
  for (var i = 0; i < results.length; i++) {
    titles += (i + 1) + ". " + (results[i].title || "") + "\n";
  }
  titles = titles.trim();

  var timestamp = Utilities.formatDate(new Date(), "Asia/Jerusalem", "dd/MM/yyyy HH:mm:ss");

  sheet.appendRow([timestamp, email, query, results.length, titles, status]);
}


// ============================================================
// בדיקה מול גיליון המאושרים
// ============================================================

function isApproved(email) {

  var sheet = SpreadsheetApp.openById(APPROVED_SHEET_ID).getSheets()[0];
  var data = sheet.getDataRange().getValues();

  var target = String(email).trim().toLowerCase();

  for (var i = 0; i < data.length; i++) {

    var cellValue = String(data[i][0] || "").trim().toLowerCase();

    if (cellValue === target) {
      return true;
    }
  }

  return false;
}


// ============================================================
// שליפת מילות החיפוש מהתשובה בטופס
// ============================================================

function getQueryFromResponse(response) {

  var itemResponses = response.getItemResponses();

  for (var i = 0; i < itemResponses.length; i++) {
    var title = itemResponses[i].getItem().getTitle();
    if (title.indexOf("לחפש") !== -1) {
      return itemResponses[i].getResponse();
    }
  }

  // אם לא נמצאה שאלה עם "לחפש" בכותרת - ניקח את התשובה הראשונה
  if (itemResponses.length > 0) {
    return itemResponses[0].getResponse();
  }

  return null;
}


// ============================================================
// קריאה לשרת החיפוש ב-Railway
// ============================================================

function searchYoutube(query) {

  var payload = {
    query: query,
    limit: RESULTS_LIMIT
  };

  var apiKey = getApiKey();

  if (!apiKey) {
    throw new Error("API_KEY לא מוגדר ב-Script Properties");
  }

  var options = {
    method: "post",
    contentType: "application/json",
    headers: {
      "X-API-KEY": apiKey
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  var response = UrlFetchApp.fetch(SEARCH_SERVER_URL, options);

  if (response.getResponseCode() === 401) {
    throw new Error("המפתח נדחה על ידי השרת (401) - כנראה ש-API_KEY ב-Script Properties שגוי");
  }

  var data = JSON.parse(response.getContentText());

  if (!data.success) {
    throw new Error(data.error || "החיפוש נכשל");
  }

  return data.results || [];
}


// ============================================================
// שליחת אימייל עם התוצאות
// ============================================================

function sendResultsEmail(toEmail, query, results) {

  var subject = "תוצאות חיפוש: " + query;

  var body = "חיפשת: " + query + "\n\n";

  if (results.length === 0) {

    body += "לא נמצאו תוצאות.";

  } else {

    for (var i = 0; i < results.length; i++) {
      var r = results[i];
      body += (i + 1) + ". " + isolateBidi(r.title) + "\n";
      body += "   ערוץ: " + isolateBidi(r.channel || "לא ידוע") + "\n";
      if (r.duration) body += "   אורך: " + formatDuration(r.duration) + "\n";
      body += "   קישור: " + r.url + "\n\n";
    }
  }

  var inlineImages = {};
  var thumbKeys = fetchInlineThumbnails(results, inlineImages);

  // הלוגו משמש כרקע של כרטיס הכותרת (תמונת רקע חיצונית + צבע רקע כהה כגיבוי),
  // ולכן אין צורך להטמיע אותו inline במייל
  var html = buildResultsHtml(query, results, thumbKeys, toEmail);

  MailApp.sendEmail({
    to: toEmail,
    subject: subject,
    body: body,
    htmlBody: html,
    inlineImages: inlineImages
  });
}


// ============================================================
// הורדת התמונות הממתינות והטמעתן בתוך המייל (inline CID)
// — כך הן מוצגות גם כשהנמען חוסם תמונות חיצוניות, בלי לשנות הגדרות
// ============================================================

function fetchInlineThumbnails(results, inlineImages) {

  var keys = [];

  for (var i = 0; i < results.length; i++) {

    var videoId = extractVideoId(results[i].url);
    var key = null;

    if (videoId) {
      try {
        var resp = UrlFetchApp.fetch("https://i.ytimg.com/vi/" + videoId + "/mqdefault.jpg", { muteHttpExceptions: true });
        if (resp.getResponseCode() === 200) {
          key = "thumb" + i;
          inlineImages[key] = resp.getBlob().setName(key + ".jpg");
        }
      } catch (err) {
        // ניפול חזרה לתמונה חיצונית רגילה
      }
    }

    keys.push(key);
  }

  return keys;
}


// ============================================================
// עיצוב המייל — עמוד כהה, פס תמונה בראש, כרטיסים בהירים צפים מעל,
// מספרי עדיפות מוטמעים על התמונות ופוטר ניווט. הפלטה נשאבה מהלוגו עצמו.
// ============================================================

// בניית קישור לטופס ההורדות עם מילוי אוטומטי: הקישור, סוג ההורדה
// והמייל של הנמען (מנגנון איסוף האימייל המובנה של גוגל).
//
// שני כללים שהוכחו בפועל:
// 1. בלי submit=Submit — גוגל מנקה את כל הפרמטרים כשהוא קיים.
// 2. הכתובת נשלחת בפורמט youtu.be/מזהה + הסימון — כדי שלא יהיה
//    בתוכה & פנימי (ששובר מילוי), ועדיין תהיה מזוהה כמקור-מייל
//    במערכת ההורדות לצורך הגנת הכפילויות.
function buildEmailDownloadLink(videoUrl, downloadType, email) {

  if (!DOWNLOAD_FORM_BASE_URL || !videoUrl || !email) {
    return "";
  }

  // מקוצרים ל-youtu.be/מזהה כשאפשר, ומוסיפים את סימון המקור כפרמטר בודד
  var id = extractVideoId(videoUrl);
  var cleanUrl = id
    ? "https://youtu.be/" + id + "?" + EMAILDL_URL_MARKER
    : String(videoUrl);

  return DOWNLOAD_FORM_BASE_URL
    + "?usp=pp_url"
    + "&" + DOWNLOAD_FORM_ENTRY_URL + "=" + encodeURIComponent(cleanUrl)
    + "&" + DOWNLOAD_FORM_ENTRY_TYPE + "=" + encodeURIComponent(downloadType)
    + "&emailAddress=" + encodeURIComponent(email)
    // גלילה עד לסוף הטופס — Scroll-To-Text Fragment (#:~:text=).
    // למה עוגני-מזהה (#mG61Hd, #i15, #i24) נכשלו כולם: הדפדפן מגלול לעוגן
    // מיד בתחילת טעינת העמוד, לפני שהטופס סיים להיבנות — העמוד עדיין קצר,
    // הגלילה נעצרת בקצה ומבוטלת כשהתוכן גדל אחר-כך. מנגנון ה-text-fragment
    // דווקא מופעל על-ידי הדפדפן אחרי שהעמוד רונדר במלואו — ולכן גולל עד
    // הסוף באמת. הטקסט "סוג ההורדה" = כותרת השאלה האחרונה, ממש מעל
    // כפתור השליחה, נכתב בעברית בתוך הטופס עצמו (יציב בכל שפת דפדפן),
    // ומופיע פעם אחת בלבד בתוכן הגלוי — אומת מול הטופס החי.
    // ⚠️ חשוב: ה-# בתחילת הקטע הוא חובה — בליו הטקסט נדבק לערך הפרמטר האחרון
    // והדפדפן לא מזהה fragment ולא גולל (זה בדיוק הבאג שהיה)
    + "#:~:text=" + encodeURIComponent("סוג ההורדה");
}

function buildResultsHtml(query, results, thumbKeys, recipientEmail) {

  if (!thumbKeys) thumbKeys = [];

  var cards = "";

  for (var i = 0; i < results.length; i++) {

    var r = results[i];
    var videoId = extractVideoId(r.url);
    var thumb = videoId
      ? "https://i.ytimg.com/vi/" + videoId + "/mqdefault.jpg"
      : "";
    var duration = r.duration ? formatDuration(r.duration) : "";
    var inlineKey = thumbKeys[i] || null;

    // אם התמונה הוטמעה במייל (inline CID) — משתמשים בה;
    // אחרת מציגים תמונה חיצונית רגילה כגיבוי
    var thumbSrc = inlineKey ? ("cid:" + inlineKey) : thumb;

    // תמונת הסרטון (200×113) צמודה לקצה הימני של הכרטיס, בסגנון "אלכסון מרובע":
    // פינה שמאלית-עליונה מרובעת + פינה ימנית-תחתונה מרובעת (דרך פס המספר);
    // שתי הפינות האחרות מעוגלות ומקננות בעיקול הכרטיס — סימטריה מגניבה ומכוונת
    var thumbCell = thumbSrc
      ? '<td width="200" valign="top" style="padding:0 0 0 16px;">' +
        '<a href="' + r.url + '"><img src="' + thumbSrc +
        '" width="200" height="113" alt="תמונה ממתינה" ' +
        'style="display:block;width:200px;height:113px;border:0;border-radius:0 22px 0 0;background:#1b1830;"></a>' +
        '<div style="background:#f0e9dc;color:#2b2237;font-size:12px;font-weight:bold;text-align:center;' +
        'padding:6px 0;border-radius:0 0 0 12px;letter-spacing:1px;">' + (i + 1) + "</div>" +
        "</td>"
      : "";

    var metaParts = [];
    if (r.channel) metaParts.push('<span dir="auto">' + escapeHtml(r.channel) + "</span>");
    // "צפייה ביוטיוב" — הסמל הרשמי של יוטיוב מה-CDN של גוגל עצמו (gstatic):
    // ג'ימייל תמיד טוען מ-gstatic (הדומיין שלו), אומת 200 OK — PNG 48×48
    metaParts.push(
      '<a href="' + r.url + '" style="color:#7fb3ff;font-weight:bold;text-decoration:underline;">' +
      '<img src="https://ssl.gstatic.com/images/branding/product/1x/youtube_48dp.png" width="19" height="19" alt="YouTube" ' +
      'style="display:inline-block;width:19px;height:19px;border:0;vertical-align:-4px;margin-left:6px;">' +
      " צפייה ביוטיוב</a>"
    );
    if (duration) {
      metaParts.push(
        '<span style="background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.14);border-radius:999px;padding:3px 10px;font-size:11.5px;color:#c3c6d4;font-weight:bold;">' +
        duration + "</span>"
      );
    }

    // כפתורי הורדה — עדינים ומהודרים: שקופים עם מסגרת צבעונית עדינה (במקום גרדיאנטים צועקים)
    var dlVideoLink = buildEmailDownloadLink(r.url, "וידאו", recipientEmail);
    var dlAudioLink = buildEmailDownloadLink(r.url, "אודיו", recipientEmail);

    var downloadButtons = "";

    if (dlVideoLink) {
      downloadButtons +=
        '<a href="' + dlVideoLink + '" style="display:inline-block;background:rgba(255,42,42,0.10);' +
        'border:1px solid rgba(255,42,42,0.45);color:#ff8a8a;font-size:12.5px;font-weight:bold;letter-spacing:0.4px;' +
        'padding:9px 20px;border-radius:999px;text-decoration:none;">הורד וידאו&nbsp;&nbsp;↓</a>';
    }

    if (dlAudioLink) {
      if (downloadButtons) downloadButtons += '&nbsp;&nbsp;';
      downloadButtons +=
        '<a href="' + dlAudioLink + '" style="display:inline-block;background:rgba(0,212,255,0.08);' +
        'border:1px solid rgba(0,212,255,0.40);color:#6fdcff;font-size:12.5px;font-weight:bold;letter-spacing:0.4px;' +
        'padding:9px 20px;border-radius:999px;text-decoration:none;">הורד אודיו&nbsp;&nbsp;↓</a>';
    }

    if (downloadButtons) {
      // מרוכז בתוך השורה התחתונה שמשתרעת על כל רוחב הכרטיס (colspan)
      downloadButtons = '<div class="btnC" style="margin-top:10px;text-align:center;padding-left:23%;">' + downloadButtons + "</div>";
    }

    // כרטיס שקוף עם מסגרת צבעונית ישירה (border) — הרקע נראה דרכו במלואו.
    // שתי שורות: הכותרת לצד התמונה; שורת הפרטים והכפתורים בשורה משלהם
    // שמשתרעת על כל רוחב הכרטיס (colspan) — כך המרכוז שלהם הוא בדיוק
    // מרכז הכרטיס/העמוד, בכל לקוח ובכל רוחב מסך
    // כרטיס בשורה אחת — מסתיים בדיוק בגובה התמונה + פס המספר.
    // אלכסון מרובע על הכרטיס עצמו: פינה שמאלית-עליונה מרובעת + ימנית-תחתונה
    // מרובעת (בצד התמונה); ימנית-עליונה ושמאלית-תחתונה מעוגלות 24px
    // שורת הפרטים והכפתורים ממורכזים עם ריפוד-פיצוי (23%) שמיישר את
    // מרכזם אל מרכז הכרטיס כולו; במסכים צרים הריפוד מתאפס (media query)
    cards +=
      '<tr><td style="padding:0 0 16px 0;">' +
      '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" dir="ltr" ' +
      'style="direction:ltr;border-collapse:separate;border:2px solid #6d5cd6;border-radius:0 24px 0 24px;background-color:#2a2740;background:rgba(238,235,248,0.18);">' +
      "<tr>" +
      '<td dir="rtl" valign="middle" style="direction:rtl;text-align:right;padding:14px 2px 14px 20px;">' +
      '<a href="' + r.url + '" style="color:#f2f0f7;font-size:15.5px;font-weight:bold;text-decoration:none;line-height:1.45;display:block;margin-bottom:7px;">' +
      '<span dir="auto">' + escapeHtml(r.title || "ללא כותרת") + "</span></a>" +
      '<div class="metaC" style="color:#a5a3b8;font-size:13px;text-align:center;padding-left:23%;">' + metaParts.join(" &nbsp;·&nbsp; ") + "</div>" +
      downloadButtons +
      "</td>" +
      thumbCell +
      "</tr></table></td></tr>";
  }

  if (!cards) {
    cards =
      '<tr><td>' +
      '<div style="background:#1e1a30;border:1px solid #332e4d;border-radius:16px;padding:30px 24px;text-align:center;">' +
      '<div style="font-size:30px;margin-bottom:8px;">🔍</div>' +
      '<div style="color:#ffffff;font-size:15px;font-weight:bold;">לא נמצאו תוצאות</div>' +
      '<div style="color:#9aa0b4;font-size:13px;margin-top:6px;">נסו ניסוח אחר או מילות חיפוש שונות</div>' +
      "</div></td></tr>";
  }

  var dateStr = Utilities.formatDate(new Date(), "Asia/Jerusalem", "dd/MM/yyyy");

  // Preheader — שורה נסתרת בראש המייל שמופיעה בתיבת הדואר לצד הנושא
  var preheader =
    results.length > 0
      ? "נמצאו " + results.length + " תוצאות עבור: " + query
      : "לא נמצאו תוצאות עבור: " + query;

  // כתובת טופס החיפוש — לכפתור "חיפוש חדש" בפוטר (אם לא נטענת, הכפתור לא מופיע)
  var searchFormUrl = "";
  try {
    searchFormUrl = FormApp.openById(FORM_ID).getPublishedUrl() || "";
  } catch (e) {}

  var footerButtons = "";
  if (searchFormUrl) {
    footerButtons +=
      '<a href="' + searchFormUrl + '" style="display:inline-block;background:rgba(255,255,255,0.10);border:1px solid rgba(255,255,255,0.28);color:#ffffff;font-size:12.5px;font-weight:bold;padding:9px 18px;border-radius:999px;text-decoration:none;">🔍 &nbsp;חיפוש חדש</a>';
  }
  if (DOWNLOAD_FORM_BASE_URL) {
    if (footerButtons) footerButtons += "&nbsp;&nbsp;";
    footerButtons +=
      '<a href="' + DOWNLOAD_FORM_BASE_URL + '" style="display:inline-block;background:rgba(255,255,255,0.10);border:1px solid rgba(255,255,255,0.28);color:#ffffff;font-size:12.5px;font-weight:bold;padding:9px 18px;border-radius:999px;text-decoration:none;">⬇ &nbsp;טופס הורדות ידני</a>';
  }

  // תמונת הפרופיל — עיגול אטום לגמרי וגדול (96px), מוצב מימין לכרטיס הכותרת
  // (באזור הריק של העמוד, מחוץ לחלונית), עם כתובית קישור מתחתיה שנשברת
  // לשתי שורות כשהיא ארוכה. העיגול: תא עם border-radius:50% + מסגרת לבנה
  // (טכניקה יציבה בלקוחות מייל); תמונה מרובעת 96×96 בתוכו
  var profileUrl = PROFILE_URL;
  var profileHtml =
    '<table role="presentation" cellpadding="0" cellspacing="0" align="center" style="margin:0 auto;"><tr>' +
    '<td style="border-radius:50%;background:#1b1830;padding:4px;border:3px solid rgba(255,255,255,0.92);">' +
    '<a href="' + profileUrl + '"><img src="' + PROFILE_IMAGE_URL + '" width="118" height="118" alt="הפרופיל שלי" ' +
    'style="display:block;width:118px;height:118px;border:0;border-radius:50%;background:#1b1830;"></a>' +
    "</td></tr></table>" +
    '<div style="text-align:center;margin-top:10px;padding:0 8px;">' +
    '<a href="' + profileUrl + '" style="color:#c9b8e8;font-size:12.5px;font-weight:bold;text-decoration:underline;line-height:1.7;display:block;">לפרופיל שלי</a>' +
    '<a href="' + profileUrl + '" style="color:#8fd8c8;font-size:12.5px;font-weight:bold;text-decoration:underline;line-height:1.7;display:block;">לחצו על התמונה</a>' +
    "</div>";
  if (!PROFILE_URL || !PROFILE_IMAGE_URL) profileHtml = "";

  return (
    // מדיה-קוורי: במסכים צרים מבטל את ריפוד-הפיצוי כדי שהמרכוז לא יגלוש
    // (ג'ימייל, Apple Mail ורוב הלקוחות תומכים; מי שלא תומך — מקבל את
    // הפריסה הרגילה בלי נזק)
    '<style>@media only screen and (max-width:620px){.metaC,.btnC{padding-left:0 !important;}}</style>' +
    // עמוד שלם = התמונה שבחרת + מסך כהה שקוף. הכרטיסים הכהים צפים מעליו.
    // טכניקת רקע-עמוד אמינה בלקוחות מייל: טבלת עטיפה עם מאפיין background על התא
    // (+ סטייל inline משלים); אם התמונה נחסמת — נכנס צבע הרקע הכהה
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"' +
    (LOGO_URL ? ' background="' + LOGO_URL + '"' : "") +
    '><tr><td' +
    (LOGO_URL
      ? " style=\"background-color:#171322;background-image:url('" + LOGO_URL + "');background-repeat:no-repeat;background-position:center top;background-size:cover;\""
      : ' style="background-color:#171322;"') +
    '>' +
    // שכבת מסך כהה — מעמיקה את הרקע ומשפרת ניגודיות של כל מה שמעליו
    '<div style="background:rgba(16,13,26,0.55);padding:28px 14px;font-family:Arial,sans-serif;direction:rtl;color-scheme:light;">' +
    // טקסט תצוגה מקדימה — מוסתר ויזואלית אבל נקרא בתיבת הדואר
    '<div style="display:none;max-height:0;overflow:hidden;opacity:0;">' + escapeHtml(preheader) + "&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;</div>" +
    '<div style="max-width:1100px;margin:0 auto;">' +

    // שורת הכותרת: כרטיס הכותרת (620px) במרכז העמוד, ובתא הראשון — שמוצג מימין
    // בכיוון rtl — עיגול הפרופיל הגדול עם הכתובית, באזור הריק מימין לחלונית
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>' +
    '<td width="238" valign="middle" style="vertical-align:middle;">' + profileHtml + "</td>" +
    '<td valign="top">' +
    // פס הכותרת: שכבה עדינה על הרקע, בלי גבולות חדים — נושם יחד עם העמוד
    '<table role="presentation" width="620px" cellpadding="0" cellspacing="0" align="center" style="border-collapse:separate;border:2px solid #6d5cd6;border-radius:30px;background-color:#211d36;background:rgba(30,25,52,0.55);">' +
    '<tr><td>' +
    '<div style="padding:30px 24px 34px 24px;text-align:center;">' +
    '<div style="font-size:12px;color:#d9d2f0;letter-spacing:2.5px;margin-bottom:8px;font-weight:bold;">תוצאות חיפוש</div>' +
    '<div style="color:#ffffff;font-size:22px;font-weight:bold;line-height:1.4;text-shadow:0 2px 10px rgba(0,0,0,0.6);">' + escapeHtml(query) + "</div>" +
    // צ'יף מספר תוצאות ותאריך
    '<div style="margin-top:12px;display:inline-block;background:rgba(255,255,255,0.10);border:1px solid rgba(255,255,255,0.22);border-radius:999px;padding:5px 16px;font-size:12px;color:#e8e6f2;font-weight:bold;">נמצאו ' + results.length + " תוצאות &nbsp;·&nbsp; " + dateStr + "</div>" +
    "</div></td></tr></table>" +
    "</td>" +
    // תא שמאלי ריק — מאזן את הכרטיס במרכז (238 + 624 + 238 = 1100)
    '<td width="238">&nbsp;</td>' +
    "</tr></table>" +

    // ריווח בין הכותרת לכרטיסים
    '<div style="height:18px;line-height:18px;">&nbsp;</div>' +

    // כרטיסי התוצאות — צפים מעל הרקע
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">' +
    cards +
    "</table>" +

    // פוטר: פס גרדיאנט דק, כפתורי ניווט וחתימה
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:4px;border-collapse:separate;border:2px solid #6d5cd6;border-radius:26px;background:#100d1c;">' +
    '<tr><td>' +
    '<div style="border-radius:24px;overflow:hidden;">' +
    '<div style="height:3px;background:' + BRAND_GRADIENT + ';opacity:0.75;"></div>' +
    '<div style="padding:20px 16px;text-align:center;">' +
    '<div>' + footerButtons + "</div>" +
    (CREDIT_NAME ? '<div style="color:#ffffff;font-size:13px;font-weight:bold;margin-top:14px;">' + escapeHtml(CREDIT_NAME) + '</div>' : "") +
    '<div style="color:#8f8ca3;font-size:11.5px;margin-top:5px;">' +
    (PROFILE_URL ? '<a href="' + PROFILE_URL + '" style="color:#7fd8ef;font-weight:bold;text-decoration:none;">הפרופיל שלי</a> &nbsp;·&nbsp; ' : "") +
    "נשלח אוטומטית בעקבות מילוי הטופס</div>" +
    "</div></div>" +
    "</td></tr></table>" +

    "</div></div>" +
    "</td></tr></table>"
  );
}


// ============================================================
// פונקציות עזר
// ============================================================

// המרת שניות לפורמט דקות:שניות (למשל 176 -> "2:56")
function formatDuration(seconds) {

  if (!seconds || seconds <= 0) return "";

  var h = Math.floor(seconds / 3600);
  var m = Math.floor((seconds % 3600) / 60);
  var s = seconds % 60;

  if (h > 0) {
    return h + ":" + pad2(m) + ":" + pad2(s);
  }
  return m + ":" + pad2(s);
}

function pad2(n) {
  return (n < 10 ? "0" : "") + n;
}

// חילוץ מזהה הווידאו מקישור יוטיוב
function extractVideoId(url) {

  if (!url) return null;

  var m = String(url).match(/[?&]v=([\w-]{11})/);
  if (m) return m[1];

  m = String(url).match(/youtu\.be\/([\w-]{11})/);
  if (m) return m[1];

  m = String(url).match(/\/shorts\/([\w-]{11})/);
  if (m) return m[1];

  return null;
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// עוטף טקסט בתווי בידוד יוניקוד - כדי שערבוב עברית/אנגלית לא ישבש את סדר התצוגה בגוף הטקסטואלי
function isolateBidi(text) {
  if (!text) return "";
  return "\u2068" + text.toString() + "\u2069"; // FSI ... PDI
}
