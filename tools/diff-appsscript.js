const fs = require("fs");
const https = require("https");

const scriptId = process.env.SCRIPT_ID;
const token = process.env.APPS_SCRIPT_TOKEN;

https.get(
  {
    hostname: "script.googleapis.com",
    path: "/v1/projects/" + scriptId + "/content",
    headers: { Authorization: "Bearer " + token },
  },
  (res) => {
    let data = "";
    res.on("data", (chunk) => (data += chunk));
    res.on("end", () => {
      const json = JSON.parse(data);
      const codeFile = json.files.find((f) => f.name === "קוד" && f.type === "SERVER_JS");
      const local = fs.readFileSync("apps-script/קוד.js", "utf8");
      const remote = codeFile.source;
      const a = Buffer.from(local, "utf8");
      const b = Buffer.from(remote, "utf8");
      let i = 0;
      while (i < Math.min(a.length, b.length) && a[i] === b[i]) i++;
      console.log("first diff at byte", i);
      console.log("local around:", JSON.stringify(a.slice(Math.max(0, i - 40), i + 40).toString("utf8")));
      console.log("remote around:", JSON.stringify(b.slice(Math.max(0, i - 40), i + 40).toString("utf8")));
    });
  }
).on("error", (e) => {
  console.error("Request failed:", e.message);
  process.exit(1);
});
