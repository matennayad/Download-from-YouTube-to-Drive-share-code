#!/usr/bin/env python3
"""
בונה את guide.html מתוך tools/guide-template.html.

המדריך מכיל עותק של קבצי הקוד (Apps Script ותוספי הדפדפן), כדי שיוכל
לייצר מהם "קבצים מוכנים" עם הערכים של המשתמש. לכן אחרי כל שינוי
באחד הקבצים האלה מריצים מחדש:

    python3 tools/build-guide.py
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FILES = [
    "apps-script/downloads/Code.gs",
    "apps-script/downloads/channels.gs",
    "apps-script/downloads/appsscript.json",
    "apps-script/unified-search/קוד.js",
    "apps-script/unified-search/admin_dashboard.html",
    "apps-script/unified-search/appsscript.json",
    "userscripts/Download from YouTube to Drive.user.js",
    "userscripts/Gemini Images to Drive.user.js",
]

MARKER = "<!--__EMBEDDED_FILES__-->"


def main():
    data = {}
    for rel in FILES:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            data[rel] = f.read()

    payload = json.dumps(data, ensure_ascii=False)
    # מונע סגירה מוקדמת של תגית script ושבירת HTML
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

    with open(os.path.join(ROOT, "tools", "guide-template.html"), encoding="utf-8") as f:
        template = f.read()

    if MARKER not in template:
        raise SystemExit("marker not found in template")

    block = '<script id="files-data" type="application/json">' + payload + "</script>"
    out = template.replace(MARKER, block)

    with open(os.path.join(ROOT, "guide.html"), "w", encoding="utf-8") as f:
        f.write(out)

    print("guide.html built (%d KB, %d files)" % (len(out.encode("utf-8")) // 1024, len(FILES)))


if __name__ == "__main__":
    main()
