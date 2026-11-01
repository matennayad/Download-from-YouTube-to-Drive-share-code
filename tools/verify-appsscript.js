// בדיקת תקינות: משווה את הקוד שנשמר בגוגל מול הקובץ המקומי
// חשוב: מחברים Buffers גולמיים ולא מחרוזות, כדי שתו UTF-8 שנחתך בין chunks לא יישבר
const fs = require("fs");
const https = require("https");

const scriptId = process.env.SCRIPT_ID;
const token = process.env.APPS_SCRIPT_TOKEN;
const dir = process.env.APPS_SCRIPT_DIR || "apps-script";

if (!scriptId || !token) {
  console.error("Missing SCRIPT_ID or APPS_SCRIPT_TOKEN");
  process.exit(1);
}

https.get(
  {
    hostname: "script.googleapis.com",
    path: "/v1/projects/" + scriptId + "/content",
    headers: { Authorization: "Bearer " + token },
  },
  (res) => {
    const chunks = [];
    res.on("data", (chunk) => chunks.push(chunk));
    res.on("end", () => {
      const data = Buffer.concat(chunks).toString("utf8");
      const json = JSON.parse(data);
      const codeFile = json.files.find((f) => f.name === "קוד" && f.type === "SERVER_JS");
      if (!codeFile) {
        console.log("FAIL: file 'קוד' not found on Google");
        process.exit(1);
      }
      const local = fs.readFileSync(dir + "/קוד.js", "utf8");
      if (local === codeFile.source) {
        console.log("OK: Google copy is byte-identical to local file (" + Buffer.byteLength(local) + " bytes)");
        process.exit(0);
      } else {
        console.log("MISMATCH! google=" + Buffer.byteLength(codeFile.source) + " local=" + Buffer.byteLength(local));
        process.exit(1);
      }
    });
  }
).on("error", (e) => {
  console.error("Request failed:", e.message);
  process.exit(1);
});
