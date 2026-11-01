#!/bin/bash
# בדיקת פרוקסי ה-VPS - הרצה על השרת עצמו:
#   bash test.sh "הסיסמה"

PASS="$1"

if [ -z "$PASS" ]; then
    echo "שימוש: bash test.sh \"הסיסמה\""
    exit 1
fi

PROXY="http://admin:$PASS@127.0.0.1:3128"

echo "=== [1/3] IP ציבורי של השרת (דרך הפרוקסי) ==="
curl -x "$PROXY" -s https://api.ipify.org --max-time 15
echo ""
echo "    (אמור להופיע IP ישראלי - מתחיל ב-8x / 31. / 82. / 84. / 87. / 89. / 192.115)"
echo ""

echo "=== [2/3] גישה לאתר כאן ==="
CODE=$(curl -x "$PROXY" -o /dev/null -s -w "%{http_code}" --max-time 20 -A "Mozilla/5.0" https://www.kan.org.il/)
echo "    HTTP: $CODE   (מצופה 200)"
echo ""

echo "=== [3/3] גישה ל-CDN הווידאו ==="
CODE=$(curl -x "$PROXY" -o /dev/null -s -w "%{http_code}" --max-time 20 -A "Mozilla/5.0" -H "Referer: https://www.kan.org.il/" "https://r.il.cdn-redge.media/webcache/gorigin/hls/oil/kancdn/vod/1_bhh22ujv/LIBCODER_SMOOTH_1080_KAN/Manifest.ism/playlist.m3u8?fmp4")
echo "    HTTP: $CODE   (מצופה 200 או 302)"
echo ""

if [ "$CODE" = "200" ] || [ "$CODE" = "302" ]; then
    echo "✅ הפרוקסי עובד מלא! אפשר לחבר ל-Railway."
else
    echo "❌ ה-CDN לא נגיש דרך הפרוקסי - בדוק שה-IP של השרת באמת ישראלי"
fi
