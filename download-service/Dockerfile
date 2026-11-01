FROM node:22-bookworm-slim

# ============================================================
# SYSTEM PACKAGES
# ============================================================
# גרסת Node עולה ל-22 (דרישת המנוע של bgutil; עד עכשיו הריצה הייתה
# על 20 עם אזהרת EBADENGINE בלבד). git נפל מהרשימה - כל ההתקנות
# עוברות עכשיו דרך tarball ישיר, וכך נחסך גם נפח וגם זמן.
# ffmpeg נשאר: גם yt-dlp וגם פורמטי האודיו תלויים בו.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ffmpeg \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# PO TOKEN PROVIDER
# ============================================================
# yt-dlp מקבל מיוטיוב "Sign in to confirm you're not a bot" כשאין
# לו PO Token - אסימון שמוכיח שהבקשה הגיעה מדפדפן. השירות הזה
# מייצר אותו מקומית בכל בקשה, ובכך מייתר את העוגיות שפגות.
#
# app.py כבר מפנה את yt-dlp ל-http://127.0.0.1:4416, ולכן אין
# צורך בשום שינוי בקוד האפליקציה.
#
# הורדה דרך tarball במקום git clone (קטן יותר, בלי תלות ב-git),
# והכל בשכבה אחת: קימפול ה-TypeScript נדרש לפני שניתן לקצץ
# את node_modules, ובתוך שכבה אחת שני הצדדים נמחקים יחד.
# אם הגרסאות של התוסף (pip) ושרת ה-Node מתפצלות האסימונים נדחים
# בשקט - הגרסה נעולה בשני הצדדים עם אותו BGUTIL_VERSION.
ARG BGUTIL_VERSION=2.0.0

RUN curl -fsSL \
      "https://codeload.github.com/Brainicism/bgutil-ytdlp-pot-provider/tar.gz/refs/tags/${BGUTIL_VERSION}" \
      | tar -xz -C /tmp \
    && mv "/tmp/bgutil-ytdlp-pot-provider-${BGUTIL_VERSION}" /opt/bgutil \
    && rm -rf /tmp/* \
    && cd /opt/bgutil/server \
    && npm ci \
    && npx tsc \
    # מה שנשאר לריצה הוא build/ ו-node_modules של ייצור. הטיפוסים,
    # הקלט ה-TypeScript וה-tooling של הפיתוח נמחקים - מאות MB.
    && npm prune --omit=dev \
    && rm -rf /opt/bgutil/src /opt/bgutil/.github \
    && npm cache clean --force

# התלויות של האפליקציה + התוסף של yt-dlp (אותה גרסה נעולה) -
# שתי ההתקנות בשכבה אחת כדי לחסוך שלב בנייה.
WORKDIR /app
COPY requirements.txt ./
RUN pip3 install --no-cache-dir --break-system-packages \
    -r requirements.txt \
    "bgutil-ytdlp-pot-provider==${BGUTIL_VERSION}"

# ============================================================
# VIRTUAL BROWSER (Playwright)
# ============================================================
# headless=True ב-app.py משתמש רק ב-Headless Shell, ולכן הכרום
# המלא (186MB) לא נדרש - מקביל ל-flag --only-shell של playwright.
# --with-deps מתקין את מערכות התלויות של הדפדפן דרך apt.
RUN pip3 install --no-cache-dir --break-system-packages playwright \
    && playwright install --with-deps --only-shell chromium \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# COPY FLASK APP
# ============================================================
COPY app.py start.sh telegram_bot.py telegram_songs_to_drive.py drive_bridge.py ./
RUN chmod +x start.sh

# ============================================================
# PORT
# ============================================================
ENV PORT=8080
EXPOSE 8080

# ============================================================
# START
# ============================================================
# שירות ה-PO Token ואחריו האפליקציה. אם השירות לא עולה,
# האפליקציה רצה בכל זאת ומתנהגת כמו קודם.
CMD ["./start.sh"]
