@echo off
chcp 65001 >nul
title KAN Proxy - בדיקה
set /p PASS="הזן את הסיסמה שהגדרת ב-3proxy.cfg: "

echo.
echo [1/3] בדיקת הפרוקסי עצמו (IP ציבורי דרך הפרוקסי)...
curl -x http://admin:%PASS%@127.0.0.1:3128 -s https://api.ipify.org --max-time 15
echo.
echo   -- אמור להופיע ה-IP הציבורי של הבית (מתחיל ב-8x ישראלי) --
echo.

echo [2/3] בדיקת גישה לאתר כאן...
curl -x http://admin:%PASS%@127.0.0.1:3128 -o nul -s -w "HTTP: %%{http_code}\n" --max-time 20 -A "Mozilla/5.0" https://www.kan.org.il/
echo   -- מצופה 200 --
echo.

echo [3/3] בדיקת גישה ל-CDN הווידאו...
curl -x http://admin:%PASS%@127.0.0.1:3128 -o nul -s -w "HTTP: %%{http_code}\n" --max-time 20 -A "Mozilla/5.0" -H "Referer: https://www.kan.org.il/" "https://r.il.cdn-redge.media/webcache/gorigin/hls/oil/kancdn/vod/1_bhh22ujv/LIBCODER_SMOOTH_1080_KAN/Manifest.ism/playlist.m3u8?fmp4"
echo   -- מצופה 200 (או 302) --
echo.
pause
