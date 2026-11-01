// ============================================================
// טופס חיפוש מאוחד: יוטיוב + מאקו + כאן 11
// ============================================================
// מקבל מילות חיפוש + בחירת מקורות מהטופס, שולח ל-/search של
// שירות ההורדות, ומחזיר למשתמש מייל מעוצב עם כרטיסי תוצאות
// וכפתורי "הורד וידאו/אודיו" שפותחים את טופס ההורדות הקיים
// עם מילוי אוטומטי מלא.
//
// עיצוב המייל ומנגנון התמונות המוטמעות — מהפרויקט הקודם
// (חיפוש יוטיוב), שם המבנה הוכח בפועל: multipart/related עם
// Content-ID לכל תמונה, ו-MailApp עם inlineImages כגיבוי.
//
// התקנה (מדריך מלא: UNIFIED_SEARCH_SETUP.md בריפו):
//   1. צור Google Form חדש עם שלוש שאלות (ראו המדריך)
//   2. חבר גיליון תשובות
//   3. הדבק את הסקריפט הזה בעורך
//   4. מלא את FORM_ID + APPROVED_SHEET_ID למטה
//   5. Script Properties: API_KEY = המפתח של השירות
//   6. הרץ fixTriggers + checkSetup מהעורך
// ============================================================

// ---------- הגדרות שחובה למלא ----------

// מזהה הטופס החדש (מה-URL של עריכת הטופס)
var FORM_ID = "YOUR_UNIFIED_SEARCH_FORM_ID";

// גיליון המאושרים — מקור האמת האחד: הקובץ של מערכת ההורדות
// (אותו קובץ שטופס הבקשות והתוסף קוראים). אין יותר רשימה נפרדת
// לחיפוש המאוחד — מוסיפים מאושר פעם אחת וזה עובד בכל המערכות.
var APPROVED_SHEET_ID = "YOUR_DOWNLOADS_SPREADSHEET_ID";

// שם הלשונית עם רשימת המאושרים בתוך הקובץ
var APPROVED_TAB_NAME = "מאושרים";

// ---------- הגדרות קבועות ----------

// שרת ההורדות (endpoint החיפוש המאוחד החדש)
var SEARCH_SERVER_URL =
  "https://YOUR-DOWNLOAD-SERVICE.up.railway.app/search";

var SEARCH_LOG_TAB = "חיפושים מאוחדים";
var RESULTS_LIMIT_PER_SOURCE = 7;

// נקודת קצה לרשימת פרקים של עונה בכאן (להרחבת תוצאות עונה במייל)
var KAN_EPISODES_URL =
  "https://YOUR-DOWNLOAD-SERVICE.up.railway.app/episodes";

// מקסימום כפתורי פרקים בכרטיס עונה אחד
var MAX_EPISODE_BUTTONS = 40;

// לוגו בכותרת המייל (אותו לוגו מפרויקט החיפוש ביוטיוב).
// משמש כתמונת הרקע של העמוד השלם — הכרטיסים צפים מעליו.
// אם הקישור כאן ריק — הרקע כהה רגיל, בלי לשבור כלום.
var LOGO_URL = "";

// חתימה בתחתית המייל (אופציונלי). כל שדה ריק פשוט לא מוצג.
var CREDIT_NAME = "";        // למשל: "פותח על ידי ..."
var PROFILE_URL = "";        // קישור לפרופיל/אתר שלך
var PROFILE_IMAGE_URL = "";  // תמונה עגולה ליד הכותרת (קישור ישיר לתמונה)

// טופס ההורדות הקיים + מזהי ההגשה שלו (אומתו בפרויקט היוטיוב)
var DOWNLOAD_FORM_BASE_URL =
  "https://docs.google.com/forms/d/e/YOUR_DOWNLOAD_FORM_PUBLIC_ID/viewform";
var DOWNLOAD_FORM_ENTRY_URL = "entry.YOUR_URL_FIELD_ENTRY_ID";
var DOWNLOAD_FORM_ENTRY_TYPE = "entry.YOUR_TYPE_FIELD_ENTRY_ID";

// סימון המקור המוטמע בכתובת עצמה — מערכת ההורדות מזהה שהבקשה
// הגיעה ממייל ומפעילה הגנת כפילויות (הפרמטר לא מפריע לאף שלב)
var EMAILDL_URL_MARKER = "via=email-search";

// פלטת המותג — נשאבה מהלוגו עצמו (קשת: אדום, מג'נטה, כחול, טורקיז, צהוב)
var BRAND_GRADIENT =
  "linear-gradient(90deg,#ff2a2a 0%,#ff2aa8 35%,#2a6bff 70%,#00d4ff 100%)";

// סורק את השאלה "איפה לחפש" וממפה אותה למקורות של השרת
var SOURCE_LABELS = {
  "יוטיוב": "youtube",
  "מאקו": "mako",
  "כאן": "kan",
};

// מפתח ברירת מחדל מובנה כדי שהטופס יעבוד בלי הגדרה ידנית.
// אם מוגדר API_KEY ב-Script Properties הוא גובר על ברירת המחדל.
// המפתח נשמר ב-Script Properties בשם API_KEY (ערך UNIFIED_SEARCH_KEY או API_KEY של השרת)
var DEFAULT_API_KEY = "";

function getApiKey() {
  return (
    PropertiesService.getScriptProperties().getProperty("API_KEY") ||
    DEFAULT_API_KEY
  );
}

// ============================================================
// בדיקת הגדרות — מריצים פעם אחת מהעורך
// ============================================================

function checkSetup() {
  var missing = [];

  if (!getApiKey()) missing.push("API_KEY (Script Properties)");
  if (!FORM_ID || FORM_ID.indexOf("הזן") !== -1) {
    missing.push("FORM_ID (מזהה הטופס החדש)");
  }

  try {
    var resp = UrlFetchApp.fetch(
      "https://YOUR-DOWNLOAD-SERVICE.up.railway.app/",
      { muteHttpExceptions: true }
    );
    if (resp.getResponseCode() !== 200) {
      missing.push("שרת ההורדות לא מגיב (HTTP " + resp.getResponseCode() + ")");
    }
  } catch (err) {
    missing.push("שרת ההורדות לא נגיש: " + err);
  }

  try {
    SpreadsheetApp.openById(APPROVED_SHEET_ID);
  } catch (err) {
    missing.push("גיליון המאושרים לא נגיש: " + err);
  }

  // בדיקת מסלול המייל (Gmail API) — התקלה הנפוצה ביותר, והסימפטום שלה מטעה:
  // המייל נראה כאילו הוא "נשלח", אבל בפועל הוא נכשל ונופל לגיבוי MailApp.
  var gmailProbe = probeGmailApi();

  if (gmailProbe.kind === "api_disabled") {
    missing.push(
      "Gmail API כבוי בפרויקט ה-GCP של הסקריפט — הריצו checkGmailApi לפירוט ותיקון"
    );
  } else if (!gmailProbe.ok) {
    missing.push(
      "מסלול המייל לא תקין (" + gmailProbe.kind + ") — הריצו checkGmailApi"
    );
  }

  if (missing.length === 0) {
    Logger.log("✅ הכל תקין! המפתח מוגדר, השרת מגיב והגיליון נגיש.");
  } else {
    Logger.log("❌ בעיות שנמצאו:\n- " + missing.join("\n- "));
  }
}

// ============================================================
// בדיקה ידנית של השרשרת (בלי טופס)
// ============================================================

function testSearchAndEmail() {
  var email =
    Session.getActiveUser().getEmail() ||
    Session.getEffectiveUser().getEmail();
  var query = "בואו לאכול איתי";

  Logger.log("מריץ חיפוש בדיקה עבור: " + email);

  var results = unifiedSearch(query, ["youtube", "mako", "kan"]);

  Logger.log("החיפוש החזיר " + results.length + " תוצאות");

  sendResultsEmail(email, query, results);

  logSearch(email, query, results, "נשלח בהצלחה (בדיקה ידנית)");

  Logger.log("✅ מייל בדיקה נשלח ל: " + email);
}

// ============================================================
// הגדרת הטופס פעם אחת: איסוף מייל מאומת (נדרש לזיהוי הנמען)
// ============================================================

function setupForm() {
  var form = FormApp.openById(FORM_ID);

  try {
    form.setEmailCollectionType(FormApp.EmailCollectionType.VERIFIED);
  } catch (e) {
    form.setCollectEmail(true); // גרסת API ישנה
  }

  Logger.log("✅ הטופס מוגדר לאסוף מייל מאומת: " + form.getEditUrl());
}

// ============================================================
// תיקון טריגרים — מריצים פעם אחת מהעורך
// ============================================================

function fixTriggers() {
  var form = FormApp.openById(FORM_ID);

  var existing;
  try {
    existing = ScriptApp.getProjectTriggers();
  } catch (permErr) {
    Logger.log("❌ אין הרשאה לנהל טריגרים: " + permErr.message);
    Logger.log(
      "הפתרון: הריצו שוב את מסך האישור של הסקריפט, או התקינו ידנית: " +
        "Triggers → Add Trigger → onFormSubmit → From form → On form submit"
    );
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
// פונקציה ראשית — רצה אוטומטית בכל שליחת טופס
// ============================================================

function onFormSubmit(e) {
  var respondentEmail = null;
  var query = null;

  try {
    respondentEmail = e.response.getRespondentEmail();

    if (!respondentEmail) {
      Logger.log("No respondent email - form must collect verified emails.");
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

    var sources = getSourcesFromResponse(e.response);

    var results = unifiedSearch(query, sources);

    sendResultsEmail(respondentEmail, query, results);

    logSearch(
      respondentEmail,
      query,
      results,
      "נשלח בהצלחה (" + sources.join(", ") + ")"
    );
  } catch (err) {
    Logger.log("Error in onFormSubmit: " + err);

    try {
      logSearch(respondentEmail || "לא ידוע", query || "לא ידוע", [], "שגיאה: " + err);
    } catch (logErr) {
      Logger.log("Failed to write error to log: " + logErr);
    }
  }
}

// ============================================================
// בדיקה מול גיליון המאושרים (אותו גיליון של ההורדות)
// ============================================================

function isApproved(email) {
  var ss = SpreadsheetApp.openById(APPROVED_SHEET_ID);

  // זיהוי הלשונית: קודם התאמה מדויקת לשם, אחר כך לשונית ששמה
  // מכיל את המילה (חסין לשינויי ניסוח קלים), ורק בסוף — הראשונה.
  var target = String(APPROVED_TAB_NAME).replace(/\s+/g, "");
  var sheet =
    ss.getSheetByName(APPROVED_TAB_NAME) ||
    ss.getSheets().filter(function (s) {
      return String(s.getName()).replace(/\s+/g, "").indexOf(target) !== -1;
    })[0] ||
    ss.getSheets()[0];

  var data = sheet.getDataRange().getValues();

  Logger.log("בדיקת אישור מול הלשונית: " + sheet.getName() +
    " (קובץ " + APPROVED_SHEET_ID + ")");

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
// חילוץ מילות החיפוש והמקורות מהתשובה בטופס
// ============================================================

function getQueryFromResponse(response) {
  var itemResponses = response.getItemResponses();

  for (var i = 0; i < itemResponses.length; i++) {
    var title = itemResponses[i].getItem().getTitle();

    // "מה לחפש?" היא שאלת החיפוש; "איפה לחפש?" היא שאלת המקורות —
    // לא לבלבל ביניהן (שתיהן מכילות את המילה "לחפש")
    if (title.indexOf("לחפש") !== -1 && title.indexOf("איפה") === -1) {
      return String(itemResponses[i].getResponse() || "").trim();
    }
  }

  if (itemResponses.length > 0) {
    return String(itemResponses[0].getResponse() || "").trim();
  }

  return null;
}

function getSourcesFromResponse(response) {
  var itemResponses = response.getItemResponses();
  var sources = [];

  for (var i = 0; i < itemResponses.length; i++) {
    var title = itemResponses[i].getItem().getTitle();

    if (title.indexOf("איפה") !== -1 || title.indexOf("מקור") !== -1) {
      var chosen = itemResponses[i].getResponse();

      if (!chosen) {
        break;
      }

      var chosenList = Array.isArray(chosen) ? chosen : [chosen];

      for (var j = 0; j < chosenList.length; j++) {
        var label = String(chosenList[j]);

        for (var key in SOURCE_LABELS) {
          if (label.indexOf(key) !== -1) {
            sources.push(SOURCE_LABELS[key]);
          }
        }
      }

      break;
    }
  }

  if (sources.length === 0) {
    sources = ["youtube", "mako", "kan"];
  }

  return sources;
}

// ============================================================
// קריאה לשרת — החיפוש המאוחד
// ============================================================

function unifiedSearch(query, sources) {
  var payload = {
    query: query,
    sources: sources,
    limit: RESULTS_LIMIT_PER_SOURCE,
  };

  var apiKey = getApiKey();

  if (!apiKey) {
    throw new Error("API_KEY לא מוגדר ב-Script Properties");
  }

  var options = {
    method: "post",
    contentType: "application/json",
    headers: {
      "X-API-KEY": apiKey,
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  };

  var response = UrlFetchApp.fetch(SEARCH_SERVER_URL, options);

  if (response.getResponseCode() === 401) {
    throw new Error("המפתח נדחה על ידי השרת (401) - בדוק את API_KEY");
  }

  var data = JSON.parse(response.getContentText());

  if (!data.success) {
    throw new Error(data.error || "החיפוש נכשל");
  }

  return data.results || [];
}

// ============================================================
// רישום החיפוש בגיליון - לשונית "חיפושים מאוחדים"
// ============================================================

function logSearch(email, query, results, status) {
  var ss = SpreadsheetApp.openById(APPROVED_SHEET_ID);
  var sheet = ss.getSheetByName(SEARCH_LOG_TAB);

  if (!sheet) {
    sheet = ss.insertSheet(SEARCH_LOG_TAB);
    sheet.appendRow([
      "תאריך ושעה",
      "אימייל",
      "מילות חיפוש",
      "מספר תוצאות",
      "כותרות שנשלחו",
      "סטטוס",
    ]);
    sheet
      .getRange("A1:F1")
      .setFontWeight("bold")
      .setBackground("#2a6bff")
      .setFontColor("#ffffff");
    sheet.setFrozenRows(1);
    sheet.setColumnWidth(3, 260);
    sheet.setColumnWidth(5, 420);
  }

  var titles = "";
  for (var i = 0; i < results.length; i++) {
    titles +=
      (i + 1) + ". [" + (results[i].source || "?") + "] " + (results[i].title || "") + "\n";
  }
  titles = titles.trim();

  var timestamp = Utilities.formatDate(
    new Date(),
    "Asia/Jerusalem",
    "dd/MM/yyyy HH:mm:ss"
  );

  sheet.appendRow([timestamp, email, query, results.length, titles, status]);
}

// ============================================================
// שליחת אימייל התוצאות (Gmail API עד 500 ביום, MailApp גיבוי)
// ============================================================

function sendResultsEmail(toEmail, query, results) {
  var subject = "תוצאות חיפוש: " + query;

  var body = "חיפשת: " + query + "\n\n";

  if (results.length === 0) {
    body += "לא נמצאו תוצאות.";
  } else {
    for (var i = 0; i < results.length; i++) {
      var r = results[i];

      // עונה/סדרה של כאן/מאקו: הפרקים מוצגים ככפתורים בגרסת ה-HTML
      if (
        (r.source === "kan" &&
          (isKanSeasonUrl(r.url) || isKanSeriesHubUrl(r.url))) ||
        (r.source === "mako" &&
          (isMakoSeasonUrl(r.url) || isMakoSeriesHubUrl(r.url)))
      ) {
        body +=
          (i + 1) + ". [" + (r.source || "?") + "] " + isolateBidi(r.title || "") +
          " (סדרה/עונה - בחירת פרק בגרסת ה-HTML של המייל)\n\n";
        continue;
      }

      // תוצאה בעייתית בלי כתובת (נדיר) - לא להדפיס קישור ריק
      if (!r.url) {
        body +=
          (i + 1) + ". [" + (r.source || "?") + "] " + isolateBidi(r.title || "") + "\n\n";
        continue;
      }

      body +=
        (i + 1) + ". [" + (r.source || "?") + "] " + isolateBidi(r.title || "") + "\n";
      body += "   קישור: " + r.url + "\n\n";
    }
  }

  // הורדת התמונות והטמעתן בתוך המייל עצמו (inline CID) — אותו מנגנון
  // מוכח מפרויקט החיפוש ביוטיוב: תמונות חיצוניות (i.ytimg.com) עוברות
  // בדיקת סינון של נטפרי ומוצגות כפלסהולדר מפוקסל; תמונה שמצורפת
  // למייל עצמו (multipart/related) מוצגת מההודעה בלי בקשה חיצונית.
  var inlineImages = {};
  var thumbKeys = fetchInlineThumbnails(results, inlineImages);

  // הלוגו משמש כרקע של כרטיס הכותרת (תמונת רקע חיצונית + צבע רקע כהה כגיבוי),
  // ולכן אין צורך להטמיע אותו inline במייל
  var html = buildResultsHtml(query, results, thumbKeys, toEmail);

  // קודם Gmail API (עד 500 נמענים ביום), ואם נכשל - MailApp (עוד 100).
  // MailApp תומך ב-inlineImages מוטמעות, ולכן ה-HTML עם ה-cid נשאר תקף
  // גם בגיבוי — בדיוק כמו בפרויקט הקודם.
  var gmailApiResult = sendEmailViaGmailApi(
    toEmail,
    subject,
    body,
    html,
    inlineImages
  );

  if (gmailApiResult.success) {
    return;
  }

  Logger.log(
    "שליחה דרך Gmail API נכשלה, חוזרים ל-MailApp: " +
      gmailApiResult.error
  );

  try {
    MailApp.sendEmail({
      to: toEmail,
      subject: subject,
      body: body,
      htmlBody: html,
      inlineImages: inlineImages,
    });
  } catch (mailAppError) {
    // שני המסלולים נכשלו. הלוג צריך להגיד את זה בפה מלא, אחרת רואים
    // רק "Service invoked too many times for one day: email" ומחפשים
    // את הבעיה במקום הלא נכון.
    Logger.log(
      "❌ גם Gmail API וגם הגיבוי MailApp נכשלו — המייל לא נשלח אל " +
        toEmail +
        ".\nGmail API: " +
        gmailApiResult.error +
        "\nMailApp: " +
        mailAppError +
        "\nאם MailApp מתלונן על מכסה יומית — זו מכסת 100 הנמענים של החשבון" +
        " (מתאפסת ≈10:00 בישראל). הרץ checkGmailApi כדי לבדוק את מסלול ה-Gmail API."
    );
    throw mailAppError;
  }
}

// ============================================================
// הורדת התמונות הממתינות והטמעתן בתוך המייל (inline CID)
// — כך הן מוצגות גם כשהנמען חוסם תמונות חיצוניות, וגם בלי
// בדיקת הסינון של נטפרי שמציגה פלסהולדר מפוקסל
// ============================================================

function fetchInlineThumbnails(results, inlineImages) {

  var keys = [];

  for (var i = 0; i < results.length; i++) {

    var r = results[i];
    var key = null;

    var isSeason =
      isKanSeasonUrl(r.url) || isMakoSeasonUrl(r.url);

    var videoId = extractVideoId(r.url);

    if ((r.source || "youtube") === "youtube" && videoId && !isSeason) {

      // mqdefault ראשון (16:9 נקי בלי פסים שחורים); הוא חסר לשידורי
      // בכורה/סטרימים — ואז hqdefault שקיים לכל סרטון (הפסים השחורים
      // שלו נבלעים ברקע הכהה של הכרטיס). שתיהן נשלפות משרתי גוגל
      // (רשת נקייה) — לא דרך הסינון של נטפרי.
      var candidates = [
        "https://i.ytimg.com/vi/" + videoId + "/mqdefault.jpg",
        "https://i.ytimg.com/vi/" + videoId + "/hqdefault.jpg",
      ];

      for (var c = 0; c < candidates.length; c++) {

        try {

          var resp = UrlFetchApp.fetch(
            candidates[c],
            { muteHttpExceptions: true }
          );

          if (resp.getResponseCode() === 200) {
            key = "thumb" + i;
            inlineImages[key] = resp.getBlob().setName(key + ".jpg");
            break;
          }

        } catch (err) {
          // ממשיכים למועמד הבא; אם כולם נכשלו — ניפול לתמונה חיצונית
        }
      }
    }

    keys.push(key);
  }

  return keys;
}

function encodeEmailSubject(subject) {
  return (
    "=?UTF-8?B?" +
    Utilities.base64Encode(subject, Utilities.Charset.UTF_8) +
    "?="
  );
}

// ============================================================
// ===== שליחה דרך Gmail REST API‏ (500 נמענים ביום במקום 100) =====
// ============================================================
// MailApp מוגבל ל-100 נמענים ביום בחשבון gmail.com רגיל. שליחה ישירה
// דרך Gmail REST API עם הטוקן של הסקריפט מנצלת את המגבלה הרגילה של
// Gmail עצמו - 500 נמענים ביום - בלי שירות חיצוני ובלי תשלום.
// MailApp נשאר כגיבוי אוטומטי אם ה-API נכשל.
//
// דרישה מקדימה שחייבת להתקיים, אחרת המסלול הזה תמיד ייפול ל-MailApp:
// ה-Gmail API חייב להיות מופעל בפרויקט ה-GCP שאליו משויך הסקריפט.
// פרויקט ה-default האוטומטי של Apps Script לא מאפשר הפעלת APIs — צריך
// לחבר פרויקט GCP רגיל (Project Settings → GCP Project → Change project).
// מריצים checkGmailApi כדי לדעת בדיוק מה המצב.
//
// מבנה ה-MIME: multipart/related שבתוכו multipart/alternative
// (טקסט + HTML) ואז רכיבי התמונות עם Content-ID — המבנה התקני
// לתמונות inline ש-Gmail מציג מההודעה עצמה (מהפרויקט הקודם).

function sendEmailViaGmailApi(toEmail, subject, body, html, inlineImages) {
  try {

    var mixedBoundary = "us_rel_" + Date.now();
    var altBoundary = "us_alt_" + Date.now();

    var mime =
      "To: " + toEmail + "\r\n" +
      "Subject: " + encodeEmailSubject(subject) + "\r\n" +
      "MIME-Version: 1.0\r\n" +
      "Content-Type: multipart/related; boundary=\"" +
      mixedBoundary + "\"\r\n" +
      "\r\n" +
      "--" + mixedBoundary + "\r\n" +
      "Content-Type: multipart/alternative; boundary=\"" +
      altBoundary + "\"\r\n" +
      "\r\n" +
      "--" + altBoundary + "\r\n" +
      "Content-Type: text/plain; charset=UTF-8\r\n" +
      "\r\n" +
      body + "\r\n" +
      "--" + altBoundary + "\r\n" +
      "Content-Type: text/html; charset=UTF-8\r\n" +
      "\r\n" +
      html + "\r\n" +
      "--" + altBoundary + "--\r\n";

    // תמונות מוטמעות: כל רכיב עם Content-ID שמתאים ל-cid: ב-HTML.
    if (inlineImages) {

      for (var cid in inlineImages) {

        if (!inlineImages.hasOwnProperty(cid)) continue;

        var blob = inlineImages[cid];

        mime +=
          "--" + mixedBoundary + "\r\n" +
          "Content-Type: " + blob.getContentType() +
          "; name=\"" + cid + "\"\r\n" +
          "Content-Transfer-Encoding: base64\r\n" +
          "Content-ID: <" + cid + ">\r\n" +
          "Content-Disposition: inline; filename=\"" +
          cid + "\"\r\n" +
          "\r\n" +
          Utilities.base64Encode(blob.getBytes()) + "\r\n";
      }
    }

    mime += "--" + mixedBoundary + "--\r\n";

    var response = UrlFetchApp.fetch(
      "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
      {
        method: "post",
        contentType: "application/json",
        headers: {
          Authorization: "Bearer " + ScriptApp.getOAuthToken(),
        },
        payload: JSON.stringify({
          raw: Utilities.base64EncodeWebSafe(mime, Utilities.Charset.UTF_8),
        }),
        muteHttpExceptions: true,
      }
    );

    var status = response.getResponseCode();

    if (status >= 200 && status < 300) {
      // מחיקת עותק ה"נשלח" מיד אחרי השליחה — מיילי המערכת לא
      // מצטברים בתיבת הנשלח של בעל החשבון. הנמען מקבל כרגיל.
      try {
        var sentId = JSON.parse(response.getContentText() || "{}").id;
        if (sentId) {
          UrlFetchApp.fetch(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/" +
              sentId + "/trash",
            {
              method: "post",
              headers: {
                Authorization: "Bearer " + ScriptApp.getOAuthToken(),
              },
              muteHttpExceptions: true,
            }
          );
        }
      } catch (trashErr) {
        // לא קריטי — העותק יישאר בנשלח וניתן לנקות מהפרויקט השני
      }
      return { success: true };
    }

    // 403 הוא שתי תקלות שונות לחלוטין שנראות אותו דבר:
    //   a) ה-Gmail API כבוי בפרויקט ה-GCP שאליו משויך הסקריפט
    //      (SERVICE_DISABLED / "has not been used in project") — grantGmailScope
    //      לא עוזר כאן, צריך להפעיל את ה-API בקונסולת Google Cloud.
    //   b) חסרה הרשאת OAuth — ואז grantGmailScope כן עוזר.
    // 429/550 = חריגה ממגבלת Gmail עצמו.
    var errorBody = response.getContentText() || "";

    if (isGmailApiDisabledText(errorBody)) {
      return {
        success: false,
        error:
          "Gmail API כבוי בפרויקט ה-GCP של הסקריפט (" +
          (extractGcpProjectNumber(errorBody) || "לא ידוע") +
          "). הפעילו את Gmail API בפרויקט הזה (או חברו פרויקט GCP רגיל) " +
          "והריצו שוב את checkGmailApi. תשובת גוגל: " +
          errorBody.substring(0, 200),
      };
    }

    return {
      success: false,
      error: "Gmail API HTTP " + status + ": " +
        errorBody.substring(0, 200),
    };

  } catch (gmailApiError) {
    return { success: false, error: gmailApiError.toString() };
  }
}

// ============================================================
// אבחון שליחת המייל — מריצים מהעורך וקוראים את הלוג
// ============================================================
// שלוש תקלות שונות לגמרי נראות למשתמש אותו דבר ("המייל לא נשלח"),
// וכל אחת דורשת תיקון אחר. הפונקציה הזו מבדילה ביניהן בדיוק:
//   1. Gmail API כבוי בפרויקט ה-GCP של הסקריפט  → 403 SERVICE_DISABLED
//      (grantGmailScope לא עוזר — אין מה לאשר, ה-API פשוט לא מופעל)
//   2. חסרה הרשאת OAuth                        → 403/401 scope
//      (כאן grantGmailScope הוא הפתרון)
//   3. מכסת שליחה יומית נגמרה                  → 429/550, או MailApp = 0
// הבדיקה שולחת בקשת קריאה בלבד (users.getProfile) ולא שולחת מייל.
// ============================================================

// האם טקסט התשובה של גוגל מעיד שה-API כבוי (ולא בעיית הרשאה)?
function isGmailApiDisabledText(text) {
  return /has not been used in project|SERVICE_DISABLED|is disabled|it is disabled/i.test(
    String(text || "")
  );
}

// מספר פרויקט ה-GCP מתוך תשובת השגיאה ("...in project 123456789012...")
function extractGcpProjectNumber(text) {
  var m = /project (\d+)/i.exec(String(text || ""));
  return m ? m[1] : null;
}

// בקשת בדיקה אחת ל-Gmail API — לא שולחת מייל, רק קוראת את הפרופיל.
// מחזירה { ok, kind, status, message, projectNumber, raw }
// kind: "ok" | "api_disabled" | "no_scope" | "auth" | "quota" | "other"
function probeGmailApi() {
  var status = 0;
  var raw = "";

  try {
    var resp = UrlFetchApp.fetch(
      "https://gmail.googleapis.com/gmail/v1/users/me/profile",
      {
        method: "get",
        headers: { Authorization: "Bearer " + ScriptApp.getOAuthToken() },
        muteHttpExceptions: true,
      }
    );

    status = resp.getResponseCode();
    raw = resp.getContentText() || "";

    if (status >= 200 && status < 300) {
      return {
        ok: true,
        kind: "ok",
        status: status,
        message: "Gmail API פעיל ותקין.",
        projectNumber: null,
        raw: raw,
      };
    }
  } catch (err) {
    return {
      ok: false,
      kind: "other",
      status: 0,
      message: "הבקשה עצמה נכשלה: " + err,
      projectNumber: null,
      raw: String(err),
    };
  }

  var apiMessage = "";
  try {
    var parsed = JSON.parse(raw);
    if (parsed && parsed.error && parsed.error.message) {
      apiMessage = parsed.error.message;
    }
  } catch (parseErr) {
    apiMessage = raw.substring(0, 300);
  }

  var projectNumber = extractGcpProjectNumber(raw);
  var kind;

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
  } else if (status === 429 || /quota|rate limit|too many|exceeded/i.test(raw)) {
    kind = "quota";
  } else {
    kind = "other";
  }

  return {
    ok: false,
    kind: kind,
    status: status,
    message: apiMessage,
    projectNumber: projectNumber,
    raw: raw,
  };
}

// הפונקציה שמריצים מהעורך: מדפיסה בעברית מה חסר ומה בדיוק לעשות.
function checkGmailApi() {
  var lines = [];
  var me = Session.getEffectiveUser().getEmail();

  lines.push("=== אבחון שליחת המייל ===");
  lines.push("חשבון שולח: " + me);

  var remaining = null;
  try {
    remaining = MailApp.getRemainingDailyQuota();
  } catch (quotaErr) {
    remaining = null;
  }

  if (remaining === null) {
    lines.push("מכסת MailApp שנותרה היום: לא זמינה לבדיקה");
  } else if (remaining === 0) {
    lines.push(
      "מכסת MailApp שנותרה היום: 0  ← נגמרה. מתאפסת בחצות שעון פסיפי (≈10:00 בישראל)."
    );
  } else {
    lines.push("מכסת MailApp שנותרה היום: " + remaining);
  }

  lines.push("");
  lines.push("שולח בקשת בדיקה אחת ל-Gmail API (קריאה בלבד, לא נשלח מייל)…");

  var probe = probeGmailApi();

  if (probe.ok) {
    lines.push("✅ " + probe.message);
    lines.push("אפשר להריץ testSearchAndEmail כדי לוודא שהמייל יוצא מקצה לקצה.");
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
      "   3. בקונסולת ה-Cloud (או בקישור למטה): APIs & Services → Library → מחפשים Gmail API → Enable."
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

  var report = lines.join("\n");
  Logger.log(report);
  return report;
}

// אישור הרשאת שליחה חד-פעמי — מריצים מהעורך ומאשרים את המסך
function grantGmailScope() {
  GmailApp.sendEmail(
    Session.getEffectiveUser().getEmail(),
    "הרשאת השליחה אושרה",
    "אם אתה רואה את המייל הזה, ההרשאה נכנסה לתוקף. הרץ את testSearchAndEmail."
  );
  Logger.log("ההרשאה אושרה - הרץ testSearchAndEmail");
  return "OK";
}

// ============================================================
// בניית קישור לטופס ההורדות עם מילוי אוטומטי
// (אותם כללים שאומתו בפרויקט היוטיוב: בלי submit=Submit,
//  הכתובת עם סימון המקור, וגלילה עד "סוג ההורדה")
// ============================================================

function buildEmailDownloadLink(resultUrl, downloadType, email) {
  if (!DOWNLOAD_FORM_BASE_URL || !resultUrl || !email) {
    return "";
  }

  var cleanUrl = String(resultUrl);

  // קישורי יוטיוב מקוצרים ל-youtu.be כדי להימנע מ-& פנימי
  var videoId = extractVideoId(cleanUrl);
  if (videoId) {
    cleanUrl = "https://youtu.be/" + videoId + "?" + EMAILDL_URL_MARKER;
  } else if (cleanUrl.indexOf("?") !== -1 && cleanUrl.indexOf("via=") === -1) {
    // קישורים אחרים (מאקו/כאן): הסימון נצמד עם & אם יש כבר query,
    // אחרת עם ?. המערכת בטופס ההורדות מזהה את הסימון בכל מקום.
    cleanUrl = cleanUrl + "&" + EMAILDL_URL_MARKER;
  } else {
    cleanUrl = cleanUrl + "?" + EMAILDL_URL_MARKER;
  }

  return (
    DOWNLOAD_FORM_BASE_URL +
    "?usp=pp_url" +
    "&" + DOWNLOAD_FORM_ENTRY_URL + "=" + encodeURIComponent(cleanUrl) +
    "&" + DOWNLOAD_FORM_ENTRY_TYPE + "=" + encodeURIComponent(downloadType) +
    "&emailAddress=" + encodeURIComponent(email) +
    // גלילה עד לסוף הטופס — Scroll-To-Text Fragment (#:~:text=).
    // מנגנון ה-text-fragment מופעל על-ידי הדפדפן אחרי שהעמוד רונדר
    // במלואו — ולכן גולל עד הסוף באמת. ה-# בתחילת הקטע חובה.
    "#:~:text=" + encodeURIComponent("סוג ההורדה")
  );
}

// ============================================================
// הרחבת תוצאות "עונה" של כאן ומאקו — קישור עונה הופך לכרטיס עם
// כפתור לכל פרק (כל כפתור ממלא את טופס ההורדות עם הפרק הספציפי),
// במקום כפתורי וידאו/אודיו שהיו נכשלים על עונה בלי פרמטר פרק.
// ============================================================

function isKanSeasonUrl(url) {
  return /^https?:\/\/(www\.)?kan\.org\.il\/content\/.+\/p-\d+\/s\d+\/?($|\?)/.test(
    String(url || "")
  );
}

// עמוד עונה של מאקו: .../mako-vod-<מדור>/<סדרה>-s<מספר>/(VOD-....htm)
// כמו https://www.mako.co.il/mako-vod-keshet/nutuk_drama-s1/
function isMakoSeasonUrl(url) {
  return /^https?:\/\/(www\.)?mako\.co\.il\/.+\/[^/]+-s\d+\/?($|\?)/.test(
    String(url || "")
  );
}

// עמוד שער של סדרת מאקו בלי עונה: .../mako-vod-<מדור>/<סדרה>/
// בדיוק כמו isMakoSeriesUrl בטופס ההורדות — הבסיס להרחבת
// "העונות האחרונות".
function isMakoSeriesHubUrl(url) {
  var text = String(url || "").trim();

  if (!/mako\.co\.il\/mako-vod-[^\/]+\/[^\/\s]+/i.test(text)) {
    return false;
  }

  return (
    text.indexOf("VOD-") === -1 &&
    text.indexOf(".m3u8") === -1 &&
    !isMakoSeasonUrl(text)
  );
}

// עמוד סדרה של כאן בלי עונה: .../p-11843/
function isKanSeriesHubUrl(url) {
  return /^https?:\/\/(www\.)?kan\.org\.il\/content\/.+\/p-\d+\/?($|\?)/.test(
    String(url || "")
  );
}

// עונה בכתובת לכל ספק: מחזיר מספר או מחרוזת ריקה
function seasonNumFromUrl(url) {
  var m = String(url || "").match(/\/-?s(\d+)(?:\/?|$|\?)/);
  if (m) return m[1];
  m = String(url || "").match(/\/s(\d+)\//);
  return m ? m[1] : "";
}

function fetchSeasonEpisodes(seasonUrl) {
  var response = UrlFetchApp.fetch(
    KAN_EPISODES_URL,
    {
      method: "post",
      contentType: "application/json",
      headers: { "X-API-KEY": getApiKey() },
      payload: JSON.stringify({ url: seasonUrl }),
      muteHttpExceptions: true,
    }
  );

  if (response.getResponseCode() !== 200) {
    return [];
  }

  var data = JSON.parse(response.getContentText());

  if (!data.success || !data.episodes || !data.episodes.length) {
    return [];
  }

  return data.episodes;
}

// שליפת "העונות האחרונות" לקישור סדרה בלי עונה (מאקו/כאן).
// השרת מחזיר עבור כל עונה אחרונה את רשימת הפרקים שלה —
// לעולם לא את כל הפרקים של כל העונות יחד.
// מוחזר מערך: [{ season, count, episodes }, ...] (ריק בכישלון).
function fetchLatestSeasons(seriesUrl) {
  var response = UrlFetchApp.fetch(
    KAN_EPISODES_URL,
    {
      method: "post",
      contentType: "application/json",
      headers: { "X-API-KEY": getApiKey() },
      payload: JSON.stringify({ url: seriesUrl }),
      muteHttpExceptions: true,
    }
  );

  if (response.getResponseCode() !== 200) {
    return [];
  }

  var data;
  try {
    data = JSON.parse(response.getContentText());
  } catch (e) {
    return [];
  }

  if (data.success && data.seasons && data.seasons.length) {
    return data.seasons;
  }

  return [];
}

function buildSeasonCard(r, recipientEmail, sourceName, episodesOverride) {
  var seasonNum = seasonNumFromUrl(r.url);
  var title = r.title || "עונה " + seasonNum;

  // צבע ההדגשה לפי מקור: מאקו כחול (כמו תג המקור), כאן ירוק
  var accent = sourceName === "מאקו" ? "#2a6bff" : "#00a884";
  var pillTint =
    sourceName === "מאקו"
      ? "background:rgba(42,107,255,0.18);border:1px solid rgba(42,107,255,0.5);color:#a8c4ff;"
      : "background:rgba(0,168,132,0.18);border:1px solid rgba(0,168,132,0.5);color:#8ce8cb;";

  var episodes = episodesOverride || [];

  if (!episodes.length) {
    try {
      episodes = fetchSeasonEpisodes(r.url);
    } catch (e) {
      episodes = [];
    }
  }

  var bodyInner = "";

  if (!episodes.length) {
    // לא הצלחנו לשלוף את רשימת הפרקים - קישור רגיל לעמוד העונה.
    // במכוון אין כפתורי "הורד וידאו/אודיו" — הם מפעילים הורדת
    // עונה שלמה (מאות פרקים), וזה חסום במערכת.
    bodyInner =
      '<div style="color:#c9c4e4;font-size:13px;line-height:1.6;">' +
      "לא ניתן היה לטעון את רשימת הפרקים כרגע. " +
      'פתחו את <a href="' + r.url + '" style="color:' + accent + ';">עמוד העונה</a> ' +
      "ובחרו פרק, או חפשו שוב מאוחר יותר.</div>";
  } else {
    var buttons = "";
    var shown = Math.min(episodes.length, MAX_EPISODE_BUTTONS);

    for (var i = 0; i < shown; i++) {
      var dlLink = buildEmailDownloadLink(
        episodes[i].url,
        "וידאו",
        recipientEmail
      );

      if (!dlLink) continue;

      buttons +=
        '<a href="' + dlLink + '" style="display:inline-block;background:rgba(0,168,132,0.12);' +
        'border:1px solid rgba(0,168,132,0.55);color:#8ce8cb;font-size:12px;font-weight:bold;' +
        'padding:6px 16px;border-radius:999px;text-decoration:none;margin:4px 2px;">' +
        "פרק " + (i + 1) + "&nbsp;↓</a>";
    }

    bodyInner =
      '<div style="color:#c9c4e4;font-size:12.5px;margin-bottom:8px;">' +
      "בחרו פרק להורדה (" + episodes.length + " פרקים בעונה" +
      (episodes.length > shown
        ? " - מוצגים " + shown
        : "") + "):</div>" +
      '<div style="line-height:2.2;text-align:center;">' + buttons + "</div>";
  }

  return (
    '<tr><td style="padding:0 0 16px 0;">' +
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" dir="ltr" style="direction:ltr;border-collapse:separate;border:2px solid ' + accent + ';border-radius:0 24px 0 24px;background-color:#2a2740;background:rgba(238,235,248,0.18);">' +
    "<tr>" +
    '<td dir="rtl" style="direction:rtl;text-align:right;padding:14px 20px;">' +
    '<div style="margin-bottom:7px;">' +
    '<span style="display:inline-block;background:' + accent + ';color:#ffffff;font-size:11px;font-weight:bold;letter-spacing:0.6px;padding:3px 12px;border-radius:999px;">' + sourceName + "</span>" +
    (seasonNum
      ? '&nbsp;&nbsp;<span style="display:inline-block;' + pillTint + 'font-size:11px;font-weight:bold;padding:3px 12px;border-radius:999px;">עונה ' + seasonNum + "</span>"
      : "") +
    "</div>" +
    '<div style="color:#f2f0f7;font-size:15.5px;font-weight:bold;line-height:1.45;display:block;margin-bottom:7px;">' +
    '<span dir="auto">' + escapeHtml(title) + "</span></div>" +
    bodyInner +
    "</td>" +
    "</tr></table></td></tr>"
  );
}

// ============================================================
// עיצוב המייל — עמוד כהה, פס תמונה בראש, כרטיסים בהירים צפים מעל,
// מספרי עדיפות מוטמעים על התמונות ופוטר ניווט. הפלטה נשאבה מהלוגו עצמו.
// (אותו עיצוב מוכח מפרויקט החיפוש ביוטיוב, עם תג מקור לכל תוצאה)
// ============================================================

var SOURCE_TAG_COLORS = {
  youtube: "#ff2a2a",
  mako: "#2a6bff",
  kan: "#00a884",
};

var SOURCE_TAG_NAMES = {
  youtube: "יוטיוב",
  mako: "מאקו",
  kan: "כאן",
};

function buildResultsHtml(query, results, thumbKeys, recipientEmail) {

  if (!thumbKeys) thumbKeys = [];

  var cards = "";

  for (var i = 0; i < results.length; i++) {

    var r = results[i];
    var source = r.source || "youtube";
    var tagColor = SOURCE_TAG_COLORS[source] || "#666666";
    var tagName = SOURCE_TAG_NAMES[source] || source;

    // תוצאת "עונה" של כאן/מאקו: כרטיס מיוחד עם כפתור לכל פרק במקום
    // כפתורי וידאו/אודיו (שהיו מפעילים הורדת עונה שלמה — חסומה)
    if (source === "kan" && isKanSeasonUrl(r.url)) {
      cards += buildSeasonCard(r, recipientEmail, "כאן");
      continue;
    }

    if (source === "mako" && isMakoSeasonUrl(r.url)) {
      cards += buildSeasonCard(r, recipientEmail, "מאקו");
      continue;
    }

    // תוצאת "סדרה" בלי עונה: מתרחבת לכרטיס לכל עונה אחרונה שיצאה.
    // במכוון אין כפתורי וידאו/אודיו על הסדרה עצמה — הורדת
    // עונה שלמה (מאות פרקים) חסומה במערכת.
    if (
      (source === "kan" && isKanSeriesHubUrl(r.url)) ||
      (source === "mako" && isMakoSeriesHubUrl(r.url))
    ) {

      var hubSeasons = [];

      try {
        hubSeasons = fetchLatestSeasons(r.url);
      } catch (hubErr) {
        hubSeasons = [];
      }

      if (hubSeasons.length) {

        for (var hs = 0; hs < hubSeasons.length; hs++) {

          var seasonResult = {
            title:
              (r.title || "") +
              " - עונה " + hubSeasons[hs].season,
            url: r.url,
            source: source,
          };

          cards += buildSeasonCard(
            seasonResult,
            recipientEmail,
            source === "mako" ? "מאקו" : "כאן",
            hubSeasons[hs].episodes || []
          );
        }

        continue;
      }

      // לא הצליח לטעון עונות - כרטיס מידע בלי כפתורי הורדה
      var hubName = source === "mako" ? "מאקו" : "כאן";

      cards +=
        '<tr><td style="padding:0 0 16px 0;">' +
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" dir="ltr" style="direction:ltr;border-collapse:separate;border:2px solid #6d5cd6;border-radius:0 24px 0 24px;background-color:#2a2740;background:rgba(238,235,248,0.18);">' +
        "<tr>" +
        '<td dir="rtl" style="direction:rtl;text-align:right;padding:14px 20px;">' +
        '<div style="margin-bottom:7px;"><span style="display:inline-block;background:#6d5cd6;color:#ffffff;font-size:11px;font-weight:bold;letter-spacing:0.6px;padding:3px 12px;border-radius:999px;">' + hubName + "</span></div>" +
        '<div style="color:#f2f0f7;font-size:15.5px;font-weight:bold;line-height:1.45;margin-bottom:7px;"><span dir="auto">' + escapeHtml(r.title || "") + "</span></div>" +
        '<div style="color:#c9c4e4;font-size:13px;line-height:1.6;">זוהתה סדרה. ' +
        'פתחו את <a href="' + r.url + '" style="color:#a8c4ff;">עמוד הסדרה</a>, ' +
        "בחרו עונה ופרק, והעתיקו את כתובת הפרק לטופס ההורדות.</div>" +
        "</td>" +
        "</tr></table></td></tr>";

      continue;
    }

    var videoId = extractVideoId(r.url);

    // תמונה חיצונית כגיבוי (אם ההטמעה נכשלה): hqdefault קיים לכל
    // סרטון יוטיוב, כולל שידורי בכורה שלהם mqdefault חסר.
    var externalThumb = videoId
      ? "https://i.ytimg.com/vi/" + videoId + "/hqdefault.jpg"
      : "";

    // אם התמונה הוטמעה במייל (inline CID) — משתמשים בה;
    // אחרת מציגים תמונה חיצונית רגילה כגיבוי
    var inlineKey = thumbKeys[i] || null;
    var thumbSrc = inlineKey ? ("cid:" + inlineKey) : externalThumb;

    var duration = r.duration ? formatDuration(r.duration) : "";

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

    // תג המקור (יוטיוב/מאקו/כאן) — ראשון בשורת הפרטים
    metaParts.push(
      '<span style="display:inline-block;background:' + tagColor + ';color:#ffffff;font-size:11px;font-weight:bold;letter-spacing:0.6px;padding:2px 10px;border-radius:999px;">' + tagName + "</span>"
    );

    if (r.channel) {
      metaParts.push('<span dir="auto">' + escapeHtml(r.channel) + "</span>");
    }

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

    // כפתורי הורדה — עדינים ומהודרים: שקופים עם מסגרת צבעונית עדינה
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
      if (downloadButtons) downloadButtons += "&nbsp;&nbsp;";
      downloadButtons +=
        '<a href="' + dlAudioLink + '" style="display:inline-block;background:rgba(0,212,255,0.08);' +
        'border:1px solid rgba(0,212,255,0.40);color:#6fdcff;font-size:12.5px;font-weight:bold;letter-spacing:0.4px;' +
        'padding:9px 20px;border-radius:999px;text-decoration:none;">הורד אודיו&nbsp;&nbsp;↓</a>';
    }

    if (downloadButtons) {
      // מרוכז בתוך השורה התחתונה שמשתרעת על כל רוחב הכרטיס (colspan)
      downloadButtons =
        '<div class="btnC" style="margin-top:10px;text-align:center;padding-left:23%;">' + downloadButtons + "</div>";
    }

    // כרטיס שקוף עם מסגרת צבעונית ישירה (border) — הרקע נראה דרכו במלואו.
    // שתי שורות: הכותרת לצד התמונה; שורת הפרטים והכפתורים בשורה משלהם
    // שמשתרעת על כל רוחב הכרטיס (colspan) — כך המרכוז שלהם הוא בדיוק
    // מרכז הכרטיס/העמוד, בכל לקוח ובכל רוחב מסך.
    // אלכסון מרובע על הכרטיס עצמו: פינה שמאלית-עליונה מרובעת + ימנית-תחתונה
    // מרובעת (בצד התמונה); ימנית-עליונה ושמאלית-תחתונה מעוגלות 24px.
    // ריפוד-פיצוי (23%) מיישר את מרכז הפרטים והכפתורים אל מרכז הכרטיס;
    // במסכים צרים הריפוד מתאפס (media query)
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

  // תמונת הפרופיל — עיגול אטום לגמרי וגדול (118px), מוצב מימין לכרטיס הכותרת
  // (באזור הריק של העמוד, מחוץ לחלונית), עם כתובית קישור מתחתיה. העיגול:
  // תא עם border-radius:50% + מסגרת לבנה (טכניקה יציבה בלקוחות מייל);
  // תמונה מרובעת בתוכו
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
    ">" +
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
    "<tr><td>" +
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
    "<tr><td>" +
    '<div style="border-radius:24px;overflow:hidden;">' +
    '<div style="height:3px;background:' + BRAND_GRADIENT + ';opacity:0.75;"></div>' +
    '<div style="padding:20px 16px;text-align:center;">' +
    "<div>" + footerButtons + "</div>" +
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

function isolateBidi(text) {
  if (!text) return "";
  // FSI ... PDI - בידוד בידיאלי לערבוב עברית/אנגלית
  return "\u2068" + text.toString() + "\u2069";
}


// ============================================================
// ==== שמות הפעלה בעברית — לתפריט הפונקציות של העורך ==========
// ============================================================
// כינויים בעברית לפונקציות ההרצה הידניות. הטריגרים האוטומטיים
// נשארים מחוברים לשמות האנגליים וממשיכים לעבוד בדיוק כמו קודם.

// בדיקת הגדרות — מפתח, שרת וגיליון המאושרים.
function __בדוק_הגדרות() {
  checkSetup();
}

// בדיקה מלאה של השרשרת: חיפוש + שליחת מייל בדיקה אליך.
function __בדוק_חיפוש_ומייל() {
  testSearchAndEmail();
}

// הגדרת טופס החיפוש המאוחד (פעם אחת).
function __הגדר_טופס_חיפוש() {
  setupForm();
}

// תיקון טריגר הטופס אם המיילים לא נשלחים.
function __תקן_טריגרים() {
  fixTriggers();
}

// אישור חד-פעמי של הרשאת שליחת המייל (Gmail).
function __אשר_הרשאת_שליחת_מייל() {
  grantGmailScope();
}

// ============================================================
// לוח בקרה (אפשרות 12)
// ============================================================
// דף ניהול שנפתח מהעורך (פונקציה openDashboard) או מהמייל החודשי.
// כל הקריאות לשרת עוברות מ-Apps Script בענן — כך עוקפים את חסימת
// railway.app בדפדפן שלך (NetFree). כל פעולה דורשת מייל מאושר.
// ============================================================

var DASHBOARD_API_KEY =
  PropertiesService.getScriptProperties().getProperty("API_KEY") ||
  DEFAULT_API_KEY;

function dashboardGuard_() {
  var email =
    (Session.getActiveUser().getEmail() ||
      Session.getEffectiveUser().getEmail() || "").toLowerCase();

  if (!email || !isApproved(email)) {
    throw new Error(
      "אין הרשאה: רק מיילים מהרשימה המאושרת יכולים להשתמש בלוח (" +
        (email || "לא מזוהה") + ")"
    );
  }

  return email;
}

function dashFetch_(path, options) {
  var resp = UrlFetchApp.fetch(
    "https://YOUR-DOWNLOAD-SERVICE.up.railway.app" + path,
    Object.assign(
      {
        headers: { "X-API-KEY": DASHBOARD_API_KEY },
        muteHttpExceptions: true,
      },
      options || {}
    )
  );

  var code = resp.getResponseCode();
  var text = resp.getContentText();

  if (code !== 200) {
    var err = "HTTP " + code;
    try {
      err += ": " + JSON.parse(text).error;
    } catch (e) {
      /* לא JSON - משאירים את הקוד */
    }
    throw new Error("השרת החזיר שגיאה — " + err);
  }

  return JSON.parse(text);
}

function getServerStatus() {
  dashboardGuard_();

  var result = { reachable: false, time: new Date().toLocaleString("he-IL") };

  try {
    var health = dashFetch_("/");
    result.reachable = true;
    result.health = health;
  } catch (e) {
    result.error = String(e.message || e).slice(0, 150);
    return result;
  }

  try {
    var drive = dashFetch_("/diag/drive");
    result.drive = drive.refresh === "ok" ? "ok" : "failed";
  } catch (e) {
    result.drive = "failed";
  }

  try {
    var rec = dashFetch_("/record/list");
    result.recording = rec.current || null;
  } catch (e) {
    result.recording = null;
  }

  return result;
}

function getRecentJobs() {
  dashboardGuard_();
  return dashFetch_("/jobs/recent?items=0");
}

function getRecordStatus() {
  dashboardGuard_();
  return dashFetch_("/record/list");
}

function startRecording(channel, minutes, notifyEmail) {
  dashboardGuard_();

  var m = parseInt(minutes, 10);
  if (!(m >= 1 && m <= 180)) {
    return { success: false, error: "דקות חייבות להיות בין 1 ל-180" };
  }

  return dashFetch_("/record/start", {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify({
      channel: String(channel || "12"),
      minutes: m,
      notify_email: String(notifyEmail || "").trim(),
    }),
  });
}

function stopRecording() {
  dashboardGuard_();
  return dashFetch_("/record/stop", {
    method: "post",
    contentType: "application/json",
    payload: "{}",
  });
}

function openDashboard() {
  var url = ScriptApp.getService().getUrl();

  if (!url) {
    Logger.log(
      "❌ הפרויקט עוד לא מופץ כ-Web App. הפץ פעם אחת (Deploy → New deployment → Web app) ואז הרץ שוב."
    );
    return;
  }

  var dashUrl = url + "/admin";

  Logger.log("✅ כתובת לוח הבקרה (שמור במועדפים!):");
  Logger.log(dashUrl);
}

// doGet: /admin מציג את לוח הבקרה (דורש התחברות + מייל מאושר),
// כל נתיב אחר מציג קישור לטופס החיפוש.
function doGet(e) {
  var path = String((e && e.pathInfo) || "").toLowerCase();

  if (path.indexOf("admin") !== -1) {
    try {
      dashboardGuard_();
    } catch (err) {
      return HtmlService.createHtmlOutput(
        "<div dir=rtl style=font-family:sans-serif;padding:24px>" +
          "<h2>⛔ " + err.message + "</h2></div>"
      );
    }

    return HtmlService.createHtmlOutputFromFile("admin_dashboard")
      .setTitle("לוח בקרה — שירות ההורדות")
      .addMetaTag("viewport", "width=device-width, initial-scale=1");
  }

  return HtmlService.createHtmlOutput(
    "<div dir=rtl style=font-family:sans-serif;padding:24px>" +
      "<h2>🔍 טופס החיפוש המאוחד</h2>" +
      "<p><a href=https://docs.google.com/forms/d/" + FORM_ID + "/viewform>פתיחת הטופס</a></p>" +
      "<p>לוח הבקרה: הוסף /admin בסוף כתובת ה-Web App.</p>" +
      "</div>"
  );
}
