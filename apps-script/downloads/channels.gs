// ============================================================
// ============ הורדת ערוצים שלמים - קובץ נפרד ================
// ============================================================
// הקובץ הזה עומד בפני עצמו. יש להוסיף אותו לפרויקט ה-Apps Script
// כקובץ חדש (channels.gs), ולבצע את ההוספות הקטנות שמתוארות
// בקובץ PATCH.md בתוך הקוד הקיים.
//
// עקרון העבודה:
// הורדת ערוץ לוקחת דקות עד שעות, ו-Apps Script מוגבל ל-6 דקות
// להרצה. לכן אנחנו לא ממתינים לתשובה: שולחים בקשה לשרת, מקבלים
// מזהה עבודה (jobId), ומריצים טריגר כל 5 דקות שבודק התקדמות
// ומעדכן את הגיליון. בסיום נשלח מייל אחד עם קישור לתיקייה.


// ===================== הגדרות =====================

// כתובת הבסיס של השרת (בלי /download בסוף).
//
// חשוב: זו פונקציה ולא משתנה ברמת הקובץ. גוגל מריץ את הקוד שנמצא
// ברמת הקובץ (מחוץ לפונקציות) מיד עם טעינת הקבצים, לפי סדר
// אלפבתי — channels נטען לפני קובץ קוד.js שמגדיר את RAILWAY_URL,
// ולכן חישוב הכתובת ברמת הקובץ הפיל כל הרצה (כולל טריגרים) עם
// "RAILWAY_URL is not defined" עוד לפני שההרצה האמיתית התחילה.
// מכאן שהחישוב נעשה רק בזמן שימוש, אחרי שכל הקבצים נטענו, ואם
// RAILWAY_URL בכלל לא מוגדר — יש ברירת מחדל קבועה ששומרת על עבודה
// תקינה בכל מצב.
function getServerBaseUrl() {

  var raw =
    (typeof RAILWAY_URL !== "undefined" && RAILWAY_URL)
      ? String(RAILWAY_URL)
      : "https://YOUR-DOWNLOAD-SERVICE.up.railway.app/download";

  return raw.replace(
    /\/download\/?$/,
    ""
  );
}


// גיליון מעקב אחרי עבודות ערוץ
const CHANNELS_SHEET_NAME =
  "ערוצים";


// תקרת סרטונים לבקשה אחת (חייב להתאים לשרת)
const MAX_VIDEOS_PER_CHANNEL_REQUEST = 30;


// עמודות בגיליון הערוצים
const CH_COL_DATE          = 1;
const CH_COL_EMAIL         = 2;
const CH_COL_URL           = 3;
const CH_COL_NAME          = 4;
const CH_COL_FORMAT        = 5;
const CH_COL_JOB_ID        = 6;
const CH_COL_STATUS        = 7;
const CH_COL_PROGRESS      = 8;
const CH_COL_FOLDER        = 9;
const CH_COL_DOWNLOADED_ID = 10;
const CH_COL_LAST_UPDATE   = 11;
const CH_COL_SOURCE        = 12;
const CH_COL_SOURCE_ROW    = 13;


// סטטוסים סופיים - שורות כאלה כבר לא נבדקות
const CHANNEL_FINAL_STATUSES = [
  "הושלם",
  "הושלם עם שגיאות",
  "נכשל",
  "בוטל"
];


// ============================================================
// =============== זיהוי כתובת ערוץ ============================
// ============================================================

function isChannelUrl(url) {

  if (!url) {
    return false;
  }

  const text =
    url.toString().trim();

  const patterns = [
    /^(https?:\/\/)?(www\.|m\.)?youtube\.com\/@[\w\-.]+/i,
    /^(https?:\/\/)?(www\.|m\.)?youtube\.com\/channel\/[\w\-]+/i,
    /^(https?:\/\/)?(www\.|m\.)?youtube\.com\/(c|user)\/[\w\-.]+/i,
    /^(https?:\/\/)?(www\.|m\.)?youtube\.com\/playlist\?list=[\w\-]+/i
  ];

  return patterns.some(function (p) {
    return p.test(text);
  });
}


// ============================================================
// =============== תקשורת מול השרת =============================
// ============================================================

function serverRequest(path, method, payload) {

  const options = {
    method: method,
    headers: {
      "X-API-KEY": API_KEY
    },
    muteHttpExceptions: true
  };

  if (payload) {
    options.contentType = "application/json";
    options.payload = JSON.stringify(payload);
  }

  const response =
    UrlFetchApp.fetch(
      getServerBaseUrl() + path,
      options
    );

  const text =
    response.getContentText();

  try {

    return JSON.parse(text);

  } catch (e) {

    Logger.log(
      "תשובה לא תקינה מהשרת (" +
      path +
      "): " +
      text.substring(0, 300)
    );

    return {
      success: false,
      error: "תשובה לא תקינה מהשרת"
    };
  }
}


function startChannelJob(
  channelUrl,
  email,
  fmt,
  skipIds,
  maxVideos,
  netfree
) {

  return serverRequest(
    "/channel/download",
    "post",
    {
      url: channelUrl,
      email: email,
      format: fmt,
      skip_ids: skipIds || [],
      max_videos: maxVideos ||
                  MAX_VIDEOS_PER_CHANNEL_REQUEST,
      netfree: !!netfree,
      player_client: ["android"],
      use_cookies: false,
      use_proxy: false
    }
  );
}


function previewChannelJob(
  channelUrl,
  skipIds,
  maxVideos
) {

  return serverRequest(
    "/channel/preview",
    "post",
    {
      url: channelUrl,
      skip_ids: skipIds || [],
      max_videos: maxVideos ||
                  MAX_VIDEOS_PER_CHANNEL_REQUEST
    }
  );
}


function getChannelJobStatus(jobId) {

  return serverRequest(
    "/job/" + encodeURIComponent(jobId) + "?items=0",
    "get",
    null
  );
}


// ============================================================
// =============== גיליון הערוצים ==============================
// ============================================================

function ensureChannelsSheet() {

  const ss =
    SpreadsheetApp.getActiveSpreadsheet();

  let sheet =
    ss.getSheetByName(
      CHANNELS_SHEET_NAME
    );

  if (!sheet) {

    sheet =
      ss.insertSheet(
        CHANNELS_SHEET_NAME
      );

    sheet.appendRow([
      "תאריך",
      "אימייל",
      "כתובת הערוץ",
      "שם הערוץ",
      "פורמט",
      "מזהה עבודה",
      "סטטוס",
      "התקדמות",
      "תיקייה בדרייב",
      "מזהי סרטונים שירדו",
      "עדכון אחרון",
      "מקור",
      "שורת מקור בתגובות"
    ]);

    sheet.setFrozenRows(1);
  }

  return sheet;
}


// ============================================================
// ====== הלוג שנשמר אצלנו: מה כבר ירד בערוץ הזה ==============
// ============================================================
// זה בדיוק ה"לוג בצד הלקוח" - בפעם הבאה שמבקשים את אותו ערוץ,
// המזהים האלה נשלחים לשרת כ-skip_ids והוא מדלג עליהם.

function getKnownVideoIds(
  channelsSheet,
  email,
  channelUrl,
  fmt
) {

  const lastRow =
    channelsSheet.getLastRow();

  if (lastRow < 2) {
    return [];
  }

  const data =
    channelsSheet
      .getRange(
        2,
        1,
        lastRow - 1,
        CH_COL_SOURCE_ROW
      )
      .getValues();

  const wantedEmail =
    (email || "")
      .toString()
      .trim()
      .toLowerCase();

  const wantedChannel =
    normalizeChannelKey(channelUrl);

  // הלוג מנוהל בנפרד לכל פורמט - מי שהוריד וידאו מהערוץ עדיין
  // יכול להוריד ממנו אודיו, ולהיפך.
  const wantedFormat =
    fmt === "video" ? "וידאו" : "אודיו";

  const seen = {};

  for (let i = 0; i < data.length; i++) {

    const rowEmail =
      (data[i][CH_COL_EMAIL - 1] || "")
        .toString()
        .trim()
        .toLowerCase();

    const rowChannel =
      normalizeChannelKey(
        data[i][CH_COL_URL - 1]
      );

    const rowFormat =
      (data[i][CH_COL_FORMAT - 1] || "")
        .toString()
        .trim();

    if (
      rowEmail !== wantedEmail ||
      rowChannel !== wantedChannel ||
      rowFormat !== wantedFormat
    ) {
      continue;
    }

    const idsRaw =
      (data[i][CH_COL_DOWNLOADED_ID - 1] || "")
        .toString();

    idsRaw
      .split(",")
      .forEach(function (id) {

        const clean = id.trim();

        if (clean) {
          seen[clean] = true;
        }
      });
  }

  return Object.keys(seen);
}


// מאחד את מה שרשום אצלנו בגיליון עם מה שהלקוח (התוסף) שלח.
// כך זה עובד גם כשמישהו מוריד פעם מהטופס ופעם מהתוסף.
function mergedSkipIds(
  channelsSheet,
  email,
  channelUrl,
  fmt,
  extraIds
) {

  const merged = {};

  getKnownVideoIds(
    channelsSheet,
    email,
    channelUrl,
    fmt
  ).forEach(function (id) {
    if (id) merged[id] = true;
  });

  (extraIds || []).forEach(function (id) {

    const clean = (id || "").toString().trim();

    if (clean) merged[clean] = true;
  });

  return Object.keys(merged);
}


// תצוגה מקדימה שמתחשבת גם בלוג שלנו וגם בלוג של הלקוח
function previewChannelForUser(
  email,
  channelUrl,
  fmt,
  extraSkipIds
) {

  const channelsSheet =
    ensureChannelsSheet();

  return previewChannelJob(
    channelUrl,
    mergedSkipIds(
      channelsSheet,
      email,
      channelUrl,
      fmt,
      extraSkipIds
    ),
    MAX_VIDEOS_PER_CHANNEL_REQUEST
  );
}


// מפתח אחיד לערוץ, כדי ש-/videos או www. לא ייחשבו לערוץ אחר
function normalizeChannelKey(url) {

  if (!url) {
    return "";
  }

  return url
    .toString()
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .replace(/^www\./, "")
    .replace(/^m\./, "")
    .replace(
      /\/(videos|shorts|streams|featured|playlists)\/?$/,
      ""
    )
    .replace(/\/$/, "");
}


// ============================================================
// =============== פתיחת עבודת ערוץ ============================
// ============================================================
// מחזיר אובייקט עם התוצאה, ורושם שורה בגיליון הערוצים.

function requestChannelDownload(
  email,
  channelUrl,
  fmt,
  netfree,
  source,
  sourceRow,
  limitOverride,
  extraSkipIds
) {

  const channelsSheet =
    ensureChannelsSheet();

  // כמה מותר להוריד מבחינת המכסה הגלובלית של המערכת
  const globalState =
    getGlobalDailyState();

  if (globalState.remaining <= 0) {

    return {
      success: false,
      error: "limit_reached"
    };
  }

  const maxVideos =
    Math.min(
      limitOverride || MAX_VIDEOS_PER_CHANNEL_REQUEST,
      MAX_VIDEOS_PER_CHANNEL_REQUEST,
      globalState.remaining
    );

  const skipIds =
    mergedSkipIds(
      channelsSheet,
      email,
      channelUrl,
      fmt,
      extraSkipIds
    );

  Logger.log(
    "פותח עבודת ערוץ: " +
    channelUrl +
    " | כבר ירדו: " +
    skipIds.length +
    " | תקרה: " +
    maxVideos
  );

  const result =
    startChannelJob(
      channelUrl,
      email,
      fmt,
      skipIds,
      maxVideos,
      netfree
    );

  if (!result || !result.success) {

    return {
      success: false,
      error:
        (result && result.error) ||
        "השרת לא הצליח לפתוח את העבודה"
    };
  }

  if (result.nothingNew) {

    return {
      success: true,
      nothingNew: true,
      channel: result.channel,
      alreadyDownloaded: result.alreadyDownloaded,
      message:
        "כל הסרטונים בערוץ הזה כבר ירדו עבורך בעבר."
    };
  }

  channelsSheet.appendRow([
    new Date(),
    email,
    channelUrl,
    result.channel || "",
    fmt === "video" ? "וידאו" : "אודיו",
    result.jobId,
    "בעבודה",
    "0/" + result.total,
    "",
    "",
    new Date(),
    source || "טופס",
    sourceRow || ""
  ]);

  return {
    success: true,
    jobId: result.jobId,
    channel: result.channel,
    total: result.total,
    alreadyDownloaded: result.alreadyDownloaded,
    remainingAfter: result.remainingAfter,
    channelOpen: result.channelOpen
  };
}


// ============================================================
// ========= טיפול בשורת טופס שהקישור בה הוא ערוץ =============
// ============================================================
// נקרא מתוך checkFormResponses. מטפל בשורה במלואה (כולל כתיבת
// סטטוס ושליחת מייל במקרה של כשלון), ולכן הלולאה שם רק צריכה
// לעשות continue אחריו.

function handleChannelFormRow(
  responsesSheet,
  sheetRowIndex,
  email,
  channelUrl,
  downloadTypeRaw,
  approvedRow
) {

  // האם המשתמש הזה מוגדר כמשתמש נטפרי (עמודה 11 במאושרים).
  // בקשות מהטופס לא נבדקות כלל אלא אם NETFREE_CHECK_FOR_FORM דלוק.
  const netfree =
    NETFREE_CHECK_FOR_FORM &&
    (approvedRow && approvedRow[10]
      ? approvedRow[10].toString().trim()
      : ""
    ) === "כן";

  let formats = [];

  if (downloadTypeRaw === "וידאו ואודיו") {
    formats = ["video", "audio"];
  } else if (downloadTypeRaw === "וידאו") {
    formats = ["video"];
  } else {
    formats = ["audio"];
  }

  // כששני הפורמטים מבוקשים - מחלקים את התקרה ביניהם,
  // כדי שבקשה אחת לא תבלע 40 קבצים מהמכסה
  const perFormatLimit =
    formats.length > 1
      ? Math.floor(
          MAX_VIDEOS_PER_CHANNEL_REQUEST / 2
        )
      : MAX_VIDEOS_PER_CHANNEL_REQUEST;

  const messages = [];

  let anyStarted = false;

  for (let f = 0; f < formats.length; f++) {

    const result =
      requestChannelDownload(
        email,
        channelUrl,
        formats[f],
        netfree,
        "טופס",
        sheetRowIndex,
        perFormatLimit
      );

    const label =
      formats[f] === "video" ? "וידאו" : "אודיו";

    if (!result.success) {

      if (result.error === "limit_reached") {

        messages.push(
          label + ": ❌ המכסה היומית של המערכת הסתיימה"
        );

        closeFormForDailyLimit();

      } else {

        messages.push(
          label + ": ❌ " + result.error
        );
      }

      continue;
    }

    if (result.nothingNew) {

      messages.push(
        label + ": ℹ️ אין סרטונים חדשים"
      );

      continue;
    }

    anyStarted = true;

    messages.push(
      label + ": 🔄 " + result.total +
      " סרטונים בעבודה (" + result.jobId + ")"
    );
  }

  responsesSheet
    .getRange(sheetRowIndex, 5)
    .setValue(
      messages.join(" | ")
    );

  if (anyStarted) {

    sendStatusEmail(
      email,
      "🔄 הורדת הערוץ החלה",
      "שלום,\n\n" +
      "הבקשה שלך להורדת ערוץ התקבלה והיא מתבצעת עכשיו.\n\n" +
      messages.join("\n") + "\n\n" +
      "ההורדה מתבצעת סרטון אחרי סרטון ולכן היא עשויה " +
      "לקחת זמן. בסיום יישלח אליך מייל נוסף עם קישור " +
      "לתיקייה בדרייב.\n\n" +
      "בכל בקשה מורדים עד " +
      MAX_VIDEOS_PER_CHANNEL_REQUEST +
      " סרטונים. אם נשארו עוד סרטונים בערוץ, " +
      "אפשר לשלוח בקשה נוספת לאותו ערוץ והמערכת תדלג " +
      "אוטומטית על מה שכבר ירד.\n\n" +
      "תודה!"
    );

  } else {

    sendStatusEmail(
      email,
      "❌ הורדת הערוץ לא החלה",
      "שלום,\n\n" +
      "הבקשה שלך להורדת ערוץ לא יצאה לדרך.\n\n" +
      messages.join("\n") + "\n\n" +
      "תודה!"
    );
  }
}


// ============================================================
// ====== הטריגר: בדיקת התקדמות של עבודות פתוחות ==============
// ============================================================
// יש להריץ פעם אחת את installChannelPollTrigger() כדי להתקין
// טריגר שמפעיל את הפונקציה הזו כל 5 דקות.

function pollChannelJobs() {

  // הטריגר רץ כל 5 דקות. אם הרצה קודמת עדיין עובדת (הרבה
  // עבודות פתוחות), שתי הרצות עלולות לסגור את אותה שורה
  // ולשלוח שני מיילים. הנעילה מונעת את זה.
  //
  // נעילה בשם ("channels"), נפרדת מזו של הטופס. כשהשתיים חלקו
  // את נעילת הסקריפט, לולאת הטופס החזיקה אותה לאורך ההורדות
  // והעדכון של הערוצים דילג שוב ושוב.
  if (!acquireNamedLock("channels")) {

    Logger.log(
      "pollChannelJobs כבר רצה כרגע - מדלגים על ההרצה הזו."
    );

    return;
  }

  try {

    // ריפוי עצמי: אם טריגר בדיקת הטופס נעלם - מתקינים אותו
    // מחדש, אחרת שורות טופס חדשות לא יטופלו לעולם.
    ensureFormCheckTrigger();

    // אותו ריפוי עצמי עבור טופס חיפוש הקישורים.
    ensureSearchLinksCheckTrigger();

    pollChannelJobsInner();

  } finally {

    releaseNamedLock("channels");
  }
}


function pollChannelJobsInner() {

  const channelsSheet =
    ensureChannelsSheet();

  const lastRow =
    channelsSheet.getLastRow();

  if (lastRow < 2) {
    return;
  }

  const data =
    channelsSheet
      .getRange(
        2,
        1,
        lastRow - 1,
        CH_COL_SOURCE_ROW
      )
      .getValues();

  for (let i = 0; i < data.length; i++) {

    const rowIndex = i + 2;

    const jobId =
      (data[i][CH_COL_JOB_ID - 1] || "")
        .toString()
        .trim();

    const status =
      (data[i][CH_COL_STATUS - 1] || "")
        .toString()
        .trim();

    if (!jobId) {
      continue;
    }

    if (
      CHANNEL_FINAL_STATUSES.indexOf(status) !== -1
    ) {
      continue;
    }

    const info =
      getChannelJobStatus(jobId);

    if (!info || !info.success) {

      Logger.log(
        "לא הצלחנו לקבל סטטוס לעבודה " +
        jobId +
        ": " +
        (info && info.error)
      );

      // העבודה נעלמה מהשרת (בדרך כלל redeploy) - סוגרים את השורה
      if (info && info.error &&
          info.error.indexOf("לא נמצאה") !== -1) {

        channelsSheet
          .getRange(rowIndex, CH_COL_STATUS)
          .setValue("נכשל");

        channelsSheet
          .getRange(rowIndex, CH_COL_PROGRESS)
          .setValue("העבודה אבדה בעקבות אתחול השרת");

        channelsSheet
          .getRange(rowIndex, CH_COL_LAST_UPDATE)
          .setValue(new Date());
      }

      continue;
    }

    updateChannelRow(
      channelsSheet,
      rowIndex,
      data[i],
      info
    );
  }
}


function updateChannelRow(
  channelsSheet,
  rowIndex,
  rowData,
  info
) {

  const progressText =
    info.processed +
    "/" +
    info.total +
    " (✅ " + info.done +
    " ❌ " + info.failed +
    " ⛔ " + info.blocked + ")";

  channelsSheet
    .getRange(rowIndex, CH_COL_PROGRESS)
    .setValue(progressText);

  channelsSheet
    .getRange(rowIndex, CH_COL_LAST_UPDATE)
    .setValue(new Date());

  if (info.channel) {

    channelsSheet
      .getRange(rowIndex, CH_COL_NAME)
      .setValue(info.channel);
  }

  if (info.folderLink) {

    channelsSheet
      .getRange(rowIndex, CH_COL_FOLDER)
      .setValue(info.folderLink);
  }

  // שמירת המזהים שירדו - זה הלוג שימנע הורדה כפולה בפעם הבאה
  const downloadedIds =
    info.downloadedIds || [];

  channelsSheet
    .getRange(rowIndex, CH_COL_DOWNLOADED_ID)
    .setValue(
      downloadedIds.join(",")
    );

  if (
    info.status !== "done" &&
    info.status !== "error" &&
    info.status !== "cancelled"
  ) {

    channelsSheet
      .getRange(rowIndex, CH_COL_STATUS)
      .setValue("בעבודה");

    return;
  }

  // ---------------- העבודה הסתיימה ----------------

  const finalStatus =
    info.status === "error"
      ? "נכשל"
      : (
          info.status === "cancelled"
            ? "בוטל"
            : (
                info.failed > 0 || info.blocked > 0
                  ? "הושלם עם שגיאות"
                  : "הושלם"
              )
        );

  channelsSheet
    .getRange(rowIndex, CH_COL_STATUS)
    .setValue(finalStatus);

  // עדכון המכסה הגלובלית לפי מספר הקבצים שירדו בפועל
  if (info.done > 0) {

    addSuccessfulDownloads(info.done);
  }

  // עדכון המכסה האישית של המשתמש
  const email =
    (rowData[CH_COL_EMAIL - 1] || "")
      .toString()
      .trim()
      .toLowerCase();

  if (info.done > 0) {

    consumeUserQuota(
      email,
      info.done
    );
  }

  updateSourceResponseRow(
    rowData[CH_COL_SOURCE_ROW - 1],
    finalStatus,
    info
  );

  sendChannelSummaryEmail(
    email,
    info,
    rowData[CH_COL_URL - 1]
  );
}


// מעדכן את השורה המקורית בגיליון התגובות, כדי שמי שמסתכל שם
// יראה את התוצאה הסופית ולא "בעבודה" לנצח.
function updateSourceResponseRow(
  sourceRow,
  finalStatus,
  info
) {

  const rowIndex =
    parseInt(sourceRow, 10);

  if (!rowIndex || rowIndex < 2) {
    return;
  }

  try {

    const responsesSheet =
      SpreadsheetApp
        .getActiveSpreadsheet()
        .getSheetByName(
          RESPONSES_SHEET_NAME
        );

    if (!responsesSheet) {
      return;
    }

    const icon =
      finalStatus === "הושלם"
        ? "✅"
        : (
            finalStatus === "נכשל"
              ? "❌"
              : "⚠️"
          );

    let text =
      icon + " " +
      (info.channel || info.series || "") +
      " - " + (info.done || 0) + " ירדו";

    if (info.failed) {
      text += ", " + info.failed + " נכשלו";
    }

    if (info.blocked) {
      text += ", " + info.blocked + " נחסמו";
    }

    if (info.folderLink) {
      text += " - " + info.folderLink;
    }

    // אותה שורת טופס יכולה להוליד שתי עבודות (וידאו ואודיו).
    // מוסיפים לתוצאה הקיימת במקום לדרוס אותה.
    const cell =
      responsesSheet.getRange(rowIndex, 5);

    const existing =
      (cell.getValue() || "").toString();

    const isPlaceholder =
      existing.indexOf("🔄") !== -1;

    cell.setValue(
      (!existing || isPlaceholder)
        ? text
        : existing + " | " + text
    );

  } catch (e) {

    Logger.log(
      "עדכון שורת התגובה נכשל: " +
      e.toString()
    );
  }
}


// ============================================================
// =============== ניכוי מכסה אישית ============================
// ============================================================
// מחסיר מהמכסה של המשתמש בגיליון "מאושרים" את מספר הקבצים
// שירדו בפועל (ולא את מה שהתבקש).

function consumeUserQuota(email, amount) {

  if (!email || !amount || amount <= 0) {
    return;
  }

  const ss =
    SpreadsheetApp.getActiveSpreadsheet();

  const approvedSheet =
    ss.getSheetByName(
      APPROVED_SHEET_NAME
    );

  if (!approvedSheet) {
    return;
  }

  const lastRow =
    approvedSheet.getLastRow();

  if (lastRow < 2) {
    return;
  }

  const data =
    approvedSheet
      .getRange(2, 1, lastRow - 1, 5)
      .getValues();

  const today =
    getTodayKey();

  for (let i = 0; i < data.length; i++) {

    const rowEmail =
      (data[i][0] || "")
        .toString()
        .trim()
        .toLowerCase();

    if (rowEmail !== email) {
      continue;
    }

    const rowIndex = i + 2;

    const quotaValue = data[i][1];
    const dailyLimitValue = data[i][2];
    let usedToday = data[i][3];
    const lastUpdateDate = data[i][4];

    // מכסה כוללת (מספר)
    if (typeof quotaValue === "number") {

      approvedSheet
        .getRange(rowIndex, 2)
        .setValue(
          Math.max(0, quotaValue - amount)
        );

      return;
    }

    // מכסה יומית
    if (typeof dailyLimitValue === "number") {

      const lastUpdateStr =
        lastUpdateDate
          ? Utilities.formatDate(
              new Date(lastUpdateDate),
              Session.getScriptTimeZone(),
              "yyyy-MM-dd"
            )
          : "";

      if (lastUpdateStr !== today) {
        usedToday = 0;
      }

      approvedSheet
        .getRange(rowIndex, 4)
        .setValue(
          (usedToday || 0) + amount
        );

      approvedSheet
        .getRange(rowIndex, 5)
        .setValue(today);

      return;
    }

    // "ללא הגבלה" - אין מה לנכות
    return;
  }
}


// ============================================================
// =============== מייל סיכום ==================================
// ============================================================

function sendChannelSummaryEmail(
  email,
  info,
  channelUrl
) {

  if (!email) {
    return;
  }

  const succeeded =
    info.done || 0;

  const subject =
    info.status === "cancelled"
      ? "⏹️ הורדת הערוץ בוטלה"
      : info.status === "error"
      ? "❌ הורדת הערוץ נכשלה"
      : (
          succeeded > 0
            ? "✅ הורדת הערוץ הסתיימה: " +
              (info.channel || "")
            : "⚠️ הורדת הערוץ הסתיימה ללא קבצים"
        );

  let body =
    "שלום,\n\n" +
    "הורדת הערוץ הסתיימה.\n\n" +
    "ערוץ: " + (info.channel || channelUrl) + "\n" +
    "ירדו בהצלחה: " + succeeded + "\n" +
    "נכשלו: " + (info.failed || 0) + "\n" +
    "נחסמו / לא נבדקו: " + (info.blocked || 0) + "\n\n";

  if (info.folderLink) {

    body +=
      "התיקייה בדרייב:\n" +
      info.folderLink +
      "\n\n" +
      "בתוך התיקייה נמצא גם קובץ log.txt " +
      "עם פירוט מלא לכל סרטון - מה ירד, מה נכשל ולמה.\n\n";
  }

  body +=
    "שים לב: הקבצים עצמם משותפים אליך ישירות - " +
    "אפשר למצוא אותם בדרייב תחת \"שיתפו איתי\".\n\n";

  if (info.remainingAfter > 0) {

    body +=
      "נשארו עוד " +
      info.remainingAfter +
      " סרטונים בערוץ שלא ירדו (מגבלה של " +
      MAX_VIDEOS_PER_CHANNEL_REQUEST +
      " סרטונים לבקשה).\n" +
      "אפשר לשלוח בקשה נוספת לאותו ערוץ - " +
      "המערכת תדלג אוטומטית על מה שכבר ירד.\n\n";
  }

  if (info.error) {

    body +=
      "הערה: " + info.error + "\n\n";
  }

  body += "תודה!";

  sendStatusEmail(
    email,
    subject,
    body
  );
}


// ============================================================
// =============== התקנת הטריגר ================================
// ============================================================
// להריץ פעם אחת בלבד, ידנית, מתוך העורך.

// מתקין את טריגר הערוצים רק אם הוא חסר. לא מוחק ולא משכפל,
// ולכן בטוח לקרוא לו בכל הרצה של הטופס.
function ensureChannelPollTrigger() {

  try {

    const exists =
      ScriptApp
        .getProjectTriggers()
        .some(function (t) {
          return t.getHandlerFunction() === "pollChannelJobs";
        });

    if (exists) {
      return;
    }

    ScriptApp
      .newTrigger("pollChannelJobs")
      .timeBased()
      .everyMinutes(5)
      .create();

    Logger.log(
      "טריגר הערוצים היה חסר והותקן מחדש."
    );

  } catch (e) {

    Logger.log(
      "לא הצלחנו לוודא את טריגר הערוצים: " + e.toString() +
      " | פעולה נדרשת: להריץ את installChannelPollTrigger מהעורך " +
      "ולאשר את ההרשאות שנשאלות על המסך."
    );
  }
}


function installChannelPollTrigger() {

  const existing =
    ScriptApp.getProjectTriggers();

  for (let i = 0; i < existing.length; i++) {

    if (
      existing[i].getHandlerFunction() ===
      "pollChannelJobs"
    ) {

      ScriptApp.deleteTrigger(
        existing[i]
      );
    }
  }

  ScriptApp
    .newTrigger("pollChannelJobs")
    .timeBased()
    .everyMinutes(5)
    .create();

  Logger.log(
    "הטריגר הותקן: pollChannelJobs ירוץ כל 5 דקות."
  );
}


// ============================================================
// =============== בדיקות ידניות ===============================
// ============================================================

function TEST_ChannelPreview() {

  const result =
    previewChannelJob(
      "https://www.youtube.com/@YouTube",
      [],
      20
    );

  Logger.log(
    JSON.stringify(result, null, 2)
  );
}


// מציג את כל עבודות הערוץ שעדיין פתוחות - שימושי לבדיקה מהירה
function TEST_ShowOpenChannelJobs() {

  const sheet =
    ensureChannelsSheet();

  const lastRow =
    sheet.getLastRow();

  if (lastRow < 2) {
    Logger.log("אין עבודות בגיליון.");
    return;
  }

  const data =
    sheet
      .getRange(2, 1, lastRow - 1, CH_COL_SOURCE_ROW)
      .getValues();

  let open = 0;

  for (let i = 0; i < data.length; i++) {

    const status =
      (data[i][CH_COL_STATUS - 1] || "").toString().trim();

    if (
      CHANNEL_FINAL_STATUSES.indexOf(status) !== -1
    ) {
      continue;
    }

    open++;

    Logger.log(
      "שורה " + (i + 2) +
      " | " + data[i][CH_COL_NAME - 1] +
      " | " + data[i][CH_COL_JOB_ID - 1] +
      " | " + status +
      " | " + data[i][CH_COL_PROGRESS - 1]
    );
  }

  Logger.log("סה\"כ עבודות פתוחות: " + open);
}


function TEST_ChannelUrlDetection() {

  const samples = [
    "https://www.youtube.com/@someone",
    "https://www.youtube.com/@someone/videos",
    "https://www.youtube.com/channel/UC123",
    "https://www.youtube.com/playlist?list=PL123",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  ];

  samples.forEach(function (s) {

    Logger.log(
      (isChannelUrl(s) ? "ערוץ  " : "סרטון ") +
      s
    );
  });
}


// ============================================================
// ====== הורדת עונה שלמה של סדרת מאקו מהטופס =================
// ============================================================

function isMakoSeriesUrl(url) {

  if (!url) {
    return false;
  }

  const text =
    url.toString().trim();

  // עמוד שער של סדרה בלבד: mako-vod-*/שם-הסדרה.
  // קישור VOD (עם VOD-) הוא פרק בודד ומטופל כרגיל.
  if (
    !/mako\.co\.il\/mako-vod-[^\/]+\/[^\/\s]+/i.test(text)
  ) {
    return false;
  }

  return (
    text.indexOf("VOD-") === -1 &&
    text.indexOf(".m3u8") === -1
  );
}


function extractMakoSeasonFromUrl(url) {

  // "…/nutuk_drama 2" -> עונה 2. בלי מספר - עונה 1.
  const m =
    (url || "")
      .toString()
      .trim()
      .match(/^(https?:\/\/\S+?)\s+([0-9]{1,3})$/);

  if (m) {

    const n =
      parseInt(m[2], 10);

    if (n > 0) {
      return { url: m[1], season: n };
    }
  }

  return {
    url: (url || "").toString().trim(),
    season: 1
  };
}


function startSeasonJob(seriesUrl, season, email, fmt) {

  return serverRequest(
    "/download",
    "post",
    {
      url: seriesUrl,
      season: season,
      all_episodes: true,
      email: email,
      format: fmt,
      player_client: ["android"],
      use_cookies: false,
      use_proxy: false
    }
  );
}


function handleSeasonFormRow(
  responsesSheet,
  sheetRowIndex,
  email,
  seriesUrl,
  downloadTypeRaw
) {

  const parsed =
    extractMakoSeasonFromUrl(seriesUrl);

  const seasonUrl =
    parsed.url;

  const season =
    parsed.season;

  const fmt =
    downloadTypeRaw === "וידאו"
      ? "video"
      : "audio";

  const result =
    startSeasonJob(seasonUrl, season, email, fmt);

  if (!result || !result.success) {

    const errorText =
      (result && result.error) ||
      "השרת לא הצליח לפתוח את עבודת העונה";

    responsesSheet
      .getRange(sheetRowIndex, 5)
      .setValue("❌ " + errorText);

    sendStatusEmail(
      email,
      "❌ הורדת העונה לא החלה",
      "שלום,\n\n" +
      "הבקשה להורדת העונה לא יצאה לדרך.\n\n" +
      errorText + "\n\n" +
      "תודה!"
    );

    return;
  }

  // רישום בגיליון הערוצים - pollChannelJobs עוקב אחרי עבודות
  // ערוץ ועונה באותה צורה, כי התשובות מהשרת זהות.
  const channelsSheet =
    ensureChannelsSheet();

  channelsSheet.appendRow([
    new Date(),
    email,
    seasonUrl + " (עונה " + season + ")",
    result.series || "",
    fmt === "video" ? "וידאו" : "אודיו",
    result.jobId,
    "בעבודה",
    "0/" + result.total,
    "",
    "",
    new Date(),
    "טופס-עונה",
    sheetRowIndex
  ]);

  responsesSheet
    .getRange(sheetRowIndex, 5)
    .setValue(
      "🔄 " + result.total +
      " פרקים בעבודה (עונה " + season + ")"
    );

  sendStatusEmail(
    email,
    "🔄 הורדת העונה החלה",
    "שלום,\n\n" +
    "הבקשה להורדת עונה " + season + " של הסדרה התקבלה\n" +
    "והיא מתבצעת עכשיו פרק אחרי פרק.\n\n" +
    "סה\"כ פרקים: " + result.total + "\n\n" +
    "בסיום יישלח מייל נוסף עם קישור לתיקייה בדרייב.\n\n" +
    "תודה!"
  );
}


// ============================================================
// ====== טריגר בדיקת הטופס - ריפוי עצמי ======================
// ============================================================
// הטופס מטופל רק דרך הטריגר של checkFormResponses. אם הטריגר
// נמחק (גוגל מוחק טריגרים של בעלים בתרחישים שונים), השורות
// נשארות בלי סטטוס לנצח. כל הרצה של pollChannelJobs מוודאת
// שהטריגר קיים ומתקינה אותו מחדש אם חסר.

function ensureFormCheckTrigger() {

  try {

    const exists =
      ScriptApp
        .getProjectTriggers()
        .some(function (t) {
          return (
            t.getHandlerFunction() ===
            "checkFormResponses"
          );
        });

    if (exists) {
      return;
    }

    ScriptApp
      .newTrigger("checkFormResponses")
      .timeBased()
      .everyMinutes(5)
      .create();

    Logger.log(
      "טריגר בדיקת הטופס היה חסר והותקן מחדש."
    );

  } catch (e) {

    Logger.log(
      "לא הצלחנו לוודא את טריגר הטופס: " +
      e.toString()
    );
  }
}


// ============================================================
// ====== טופס "חיפוש קישורים" - אותו שירות, כניסה שנייה ======
// ============================================================
// טופס גוגל שני שמוביל לצינור העיבוד הקיים במלואו:
// סדרת מאקו -> עונה שלמה, ערוץ -> עבודת רקע, סרטון -> הורדה מיידית.
//
// המנגנון: כל שורה חדשה בגיליון התשובות של הטופס השני מוזרקת
// לגיליון "תגובות לטופס 1" (אותן עמודות בדיוק), ושם כל הלוגיקה
// הקיימת - רשימת מאושרים, מכסות, נטפרי, עונות וערוצים - ממשיכה
// לעבוד בלי שינוי. הסטטוס הסופי מוחזר לגיליון החיפוש.
//
// התקנה חד-פעמית: להריץ installSearchLinksForm() מעורך הסקריפט.
// הטריגר עצמו מותקן אוטומטית (ומרופא בעצמו אם נעלם).

const SEARCH_LINKS_SHEET_NAME = "חיפוש קישורים";

// עמודות: חותמת זמן | קישור | אימייל | סוג הורדה | סטטוס
const SL_COL_TIME = 1;
const SL_COL_URL = 2;
const SL_COL_EMAIL = 3;
const SL_COL_TYPE = 4;
const SL_COL_STATUS = 5;

// מילת המפתח של שורה שהוזרקה ועדיין לא הסתיימה. המספר בתוך
// הסוגריים הוא השורה בגיליון התגובות הראשי - דרכה מוחזר הסטטוס.
const SL_IN_PROGRESS_PREFIX = "🔄 בטיפול (שורה ";


// יוצר את הטופס עצמו ומחבר אותו לגיליון הזה. מריצים פעם אחת
// מעורך הסקריפט; הכתובות מודפסות בלוג. הגיליון "חיפוש קישורים"
// נוצר לבד כשמגיעה התגובה הראשונה, עם העמודות בסדר הנכון.
function installSearchLinksForm() {

  const ss =
    SpreadsheetApp.getActiveSpreadsheet();

  if (getSearchLinksSheet()) {

    Logger.log(
      "קיים כבר גיליון חיפוש קישורים - כנראה שהטופס כבר מחובר. " +
      "אם צריך טופס חדש, למחוק קודם את הגיליון הישן."
    );

    return;
  }

  const form =
    FormApp.create("חיפוש קישורים");

  form.setDescription(
    "הדביקו כאן קישור והקבצים יורדו לדרייב של האימייל שממלאים.\n" +
    "נתמך: יוטיוב (סרטון, ערוץ, פלייליסט), סדרות ופרקים במאקו, " +
    "וכן כאן 11, n12, 13tv.\n" +
    "לסדרת מאקו: אפשר להוסיף מספר עונה בסוף הקישור (רווח ואז המספר)."
  );

  form.addTextItem()
    .setTitle("קישור")
    .setHelpText("הדבקה של הקישור לסרטון / ערוץ / סדרה")
    .setRequired(true);

  form.addTextItem()
    .setTitle("אימייל")
    .setHelpText("חשבון הגוגל שאליו יישלחו הקישורים להורדה")
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle("סוג הורדה")
    .setChoiceValues(["וידאו ואודיו", "וידאו", "אודיו"])
    .showOtherOption(false);

  form.setDestination(
    FormApp.DestinationType.SPREADSHEET,
    ss.getId()
  );

  Logger.log("הטופס נוצר ומחובר לגיליון הזה.");
  Logger.log("עריכת הטופס: " + form.getEditUrl());
  Logger.log("לשיתוף עם המשתמשים: " + form.getPublishedUrl());
}


// איתור גיליון החיפוש. קודם בשם המדויק, ואז בהתחלה של שם -
// גוגל לפעמים מצמיד סיומת לשם גיליון התשובות של טופס מחובר.
// לא יוצרת גיליון ידנית, כדי שלא תתנגש עם יצירת הגיליון של הטופס.
function getSearchLinksSheet() {

  const sheets =
    SpreadsheetApp
      .getActiveSpreadsheet()
      .getSheets();

  for (let i = 0; i < sheets.length; i++) {

    if (sheets[i].getName() === SEARCH_LINKS_SHEET_NAME) {
      return sheets[i];
    }
  }

  for (let i = 0; i < sheets.length; i++) {

    if (
      sheets[i]
        .getName()
        .indexOf(SEARCH_LINKS_SHEET_NAME) === 0
    ) {
      return sheets[i];
    }
  }

  return null;
}


function checkSearchLinksFormResponses() {

  // אותה נעילה של checkFormResponses - שתי הפונקציות כותבות
  // לאותו גיליון תגובות ולאותם מוני מכסה, ולכן אסור שירוצו יחד.
  // ריצה שמדלגת פשוט תתבצע במחזור הטריגר הבא.
  if (!acquireNamedLock("form")) {

    Logger.log(
      "טיפול בחיפוש קישורים דילג - הטופס הראשי מטופל כרגע."
    );

    return;
  }

  try {

    checkSearchLinksFormResponsesInner();

  } finally {

    releaseNamedLock("form");
  }
}


function checkSearchLinksFormResponsesInner() {

  const searchSheet =
    getSearchLinksSheet();

  if (!searchSheet) {

    // הטופס עוד לא קיבל תגובה ראשונה, ולכן גיליון התשובות
    // שלו עוד לא נוצר. אין מה לעשות.
    return;
  }

  const lastRow =
    searchSheet.getLastRow();

  if (lastRow < 2) {
    return;
  }

  const data =
    searchSheet
      .getRange(2, 1, lastRow - 1, SL_COL_STATUS)
      .getValues();

  const responsesSheet =
    SpreadsheetApp
      .getActiveSpreadsheet()
      .getSheetByName(
        RESPONSES_SHEET_NAME
      );

  if (!responsesSheet) {

    Logger.log(
      "גיליון התגובות הראשי לא נמצא - שורות חיפוש הקישורים לא מוזרקות."
    );

    return;
  }

  // קודם סנכרון סטטוסים של בקשות קודמות, ואז זריקת חדשות.
  syncSearchLinksStatuses(
    searchSheet,
    data,
    responsesSheet
  );

  for (let i = 0; i < data.length; i++) {

    const status =
      (data[i][SL_COL_STATUS - 1] || "")
        .toString()
        .trim();

    // רק שורות בלי סטטוס הן בקשות חדשות.
    if (status) {
      continue;
    }

    const rawUrl =
      (data[i][SL_COL_URL - 1] || "")
        .toString()
        .trim();

    const email =
      (data[i][SL_COL_EMAIL - 1] || "")
        .toString()
        .trim()
        .toLowerCase();

    const downloadTypeRaw =
      (data[i][SL_COL_TYPE - 1] || "")
        .toString()
        .trim() || "וידאו ואודיו";

    if (!rawUrl || !email) {

      searchSheet
        .getRange(i + 2, SL_COL_STATUS)
        .setValue("❌ חסר קישור או אימייל");

      continue;
    }

    // הזרקה לצינור הראשי: אותו גיליון, אותן עמודות, אותו עיבוד.
    // עמודת הסטטוס של הטופס הראשי (עמודה 5) נשארת ריקה -
    // checkFormResponses מזהה שורה ריקה כבקשה חדשה.
    responsesSheet.appendRow([
      new Date(),
      rawUrl,
      email,
      downloadTypeRaw,
      ""
    ]);

    const injectedRow =
      responsesSheet.getLastRow();

    searchSheet
      .getRange(i + 2, SL_COL_STATUS)
      .setValue(
        SL_IN_PROGRESS_PREFIX +
        injectedRow + ")"
      );

    Logger.log(
      "חיפוש קישורים: שורה " + (i + 2) +
      " הוזרקה לצינור הראשי (שורה " + injectedRow + ")."
    );
  }
}


// החזרת סטטוס מהצינור הראשי לגיליון החיפוש. שורה שהוזרקה מסומנת
// "🔄 בטיפול (שורה N)" - כשהעיבוד בגיליון הראשי מסתיים (סטטוס
// מתחיל ב-✅/❌/⚠), הסטטוס הסופי מועתק לכאן והמעקב נעצר.
function syncSearchLinksStatuses(
  searchSheet,
  data,
  responsesSheet
) {

  for (let i = 0; i < data.length; i++) {

    const status =
      (data[i][SL_COL_STATUS - 1] || "")
        .toString()
        .trim();

    if (
      status.indexOf(SL_IN_PROGRESS_PREFIX) !== 0
    ) {
      continue;
    }

    const match =
      status.match(/\(שורה (\d+)\)\s*$/);

    if (!match) {
      continue;
    }

    const mainRow =
      parseInt(match[1], 10);

    let mainStatus = "";

    try {

      mainStatus =
        responsesSheet
          .getRange(mainRow, 5)
          .getValue()
          .toString()
          .trim();

    } catch (e) {
      continue;
    }

    const isFinal =
      mainStatus.indexOf("✅") === 0 ||
      mainStatus.indexOf("❌") === 0 ||
      mainStatus.indexOf("⚠") === 0;

    if (isFinal) {

      searchSheet
        .getRange(i + 2, SL_COL_STATUS)
        .setValue(mainStatus);
    }
  }
}


// ריפוי עצמי - אותו רעיון של ensureFormCheckTrigger.
function ensureSearchLinksCheckTrigger() {

  try {

    const exists =
      ScriptApp
        .getProjectTriggers()
        .some(function (t) {
          return (
            t.getHandlerFunction() ===
            "checkSearchLinksFormResponses"
          );
        });

    if (exists) {
      return;
    }

    ScriptApp
      .newTrigger("checkSearchLinksFormResponses")
      .timeBased()
      .everyMinutes(5)
      .create();

    Logger.log(
      "טריגר חיפוש הקישורים הותקן מחדש (כל 5 דקות)."
    );

  } catch (e) {

    Logger.log(
      "לא הצלחנו לוודא את טריגר חיפוש הקישורים: " +
      e.toString()
    );
  }
}


// בדיקה ידנית מעורך הסקריפט - מטפל מיד בשורות החיפוש הפתוחות.
function TEST_ProcessSearchLinksNow() {
  checkSearchLinksFormResponses();
}


// ============================================================
// ==== שמות הפעלה בעברית — לתפריט הפונקציות של העורך ==========
// ============================================================
// כינויים בעברית לפונקציות ההרצה הידניות. הטריגרים האוטומטיים
// (השעונים הפנימיים של גוגל) נשארים מחוברים לשמות האנגליים
// וממשיכים לעבוד בדיוק כמו קודם.

// מתקין את השעון הפנימי שסורק עבודות ערוץ ועונה כל 5 דקות
// ומעדכן את המשתמשים במייל כשההורדות מוכנות.
// בטוח להריץ גם אם הוא כבר מותקן — מנקה כפילויות ומשאיר אחד.
function __התקן_טריגר_סריקת_ערוצים() {
  installChannelPollTrigger();
}

// יוצר את טופס "חיפוש קישורים" ומחבר אותו לגיליון (פעם אחת).
function __צור_טופס_חיפוש_קישורים() {
  installSearchLinksForm();
}

// מטפל מיד בשורות חיפוש הקישורים שמחכות (במקום לחכות לטריגר).
function __טפל_בחיפושי_קישורים_עכשיו() {
  TEST_ProcessSearchLinksNow();
}

// בדיקת תצוגה מקדימה של ערוץ לדוגמה.
function __בדוק_תצוגה_מקדימה_של_ערוץ() {
  TEST_ChannelPreview();
}

// הצגת כל עבודות הערוצים שעדיין בטיפול.
function __הצג_עבודות_ערוצים_פתוחות() {
  TEST_ShowOpenChannelJobs();
}

// בדיקה שזיהוי כתובות (יוטיוב/מאקו/כאן) עובד.
function __בדוק_זיהוי_כתובות() {
  TEST_ChannelUrlDetection();
}
