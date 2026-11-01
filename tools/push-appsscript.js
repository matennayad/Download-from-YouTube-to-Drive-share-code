// ============================================================
// העלאת קוד Apps Script לגוגל דרך ה-API הרשמי
//
// שימוש:
//   APPS_SCRIPT_TOKEN="ya29...." SCRIPT_ID="...." node scripts/push-appsscript.js
//
// הטוקן מגיע מ-OAuth Playground (scope: script.projects) ותקף כשעה.
// הקבצים נלקחים מתיקיית APPS_SCRIPT_DIR (ברירת מחדל: apps-script/): appsscript.json + כל קובצי .js
// (שם הקובץ בלי סיומת הוא שם הקובץ בפרויקט בגוגל)
// ============================================================

const fs = require("fs");
const path = require("path");
const https = require("https");

const scriptId = process.env.SCRIPT_ID;
const token = process.env.APPS_SCRIPT_TOKEN;

if (!scriptId || !token) {
  console.error("Missing SCRIPT_ID or APPS_SCRIPT_TOKEN env vars");
  process.exit(1);
}

const dir = path.join(__dirname, "..", process.env.APPS_SCRIPT_DIR || "apps-script");

const files = [];

// Manifest
const manifest = fs.readFileSync(path.join(dir, "appsscript.json"), "utf8");
files.push({ name: "appsscript", type: "JSON", source: manifest });

// All .js files in apps-script/ except *.original.js backups.
// Fixed, deterministic order (files are loaded by Google in this array's order):
// manifest first, then ASCII-named files, then Hebrew-named files last — so a
// base config file like קוד.js always lands after its satellite modules, and
// file-level code never runs before its dependencies are in place.
const jsFiles = fs
  .readdirSync(dir)
  .filter((f) => f.endsWith(".js") && !f.endsWith(".original.js"))
  .sort((a, b) => {
    const ascii = (s) => (/^[\x00-\x7F]+$/.test(s) ? 0 : 1);
    return ascii(a) - ascii(b) || a.localeCompare(b);
  });

for (const f of jsFiles) {
  const name = f.slice(0, -3); // strip .js
  const source = fs.readFileSync(path.join(dir, f), "utf8");
  files.push({ name: name, type: "SERVER_JS", source: source });
}

console.log("Pushing files in order:", files.map((f) => f.name).join(", "));

const body = JSON.stringify({ files: files });
// חשוב: שליחה כ-Buffer שלם (ולא מחרוזת) כדי שתווי UTF-8 לא יישברו בין chunks
const bodyBuffer = Buffer.from(body, "utf8");

const req = https.request(
  {
    hostname: "script.googleapis.com",
    path: "/v1/projects/" + scriptId + "/content",
    method: "PUT",
    headers: {
      Authorization: "Bearer " + token,
      "Content-Type": "application/json; charset=utf-8",
      "Content-Length": bodyBuffer.length,
    },
  },
  (res) => {
    let data = "";
    res.on("data", (chunk) => (data += chunk));
    res.on("end", () => {
      console.log("HTTP " + res.statusCode);
      console.log(data);
      process.exit(res.statusCode >= 200 && res.statusCode < 300 ? 0 : 1);
    });
  }
);

req.on("error", (err) => {
  console.error("Request failed:", err.message);
  process.exit(1);
});

req.write(bodyBuffer);
req.end();
