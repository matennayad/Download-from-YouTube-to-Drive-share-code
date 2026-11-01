#!/bin/bash
# ============================================================
# התקנת פרוקסי Squid ישראלי להורדות כאן - בהרצה אחת
# הרצה על VPS אובונטו (20.04/22.04/24.04) כ-root:
#   bash setup.sh "הסיסמה_שתבחר"
# ============================================================

set -e

PASS="$1"

if [ -z "$PASS" ]; then
    echo "שימוש: bash setup.sh \"הסיסמה\""
    echo "דוגמה: bash setup.sh \"MyStr0ngPass!2026\""
    exit 1
fi

echo "==> מתקין Squid וכלי עזר..."
apt-get update -qq
apt-get install -y -qq squid apache2-utils

echo "==> יוצר משתמש וסיסמה..."
htpasswd -cb /etc/squid/passwd admin "$PASS"

echo "==> כותב קונפיגורציה..."
# גיבוי הקונפיג המקורי
cp -n /etc/squid/squid.conf /etc/squid/squid.conf.orig 2>/dev/null || true

cat > /etc/squid/squid.conf <<EOF
# פרוקסי ישראלי להורדות כאן - נוצר אוטומטית
auth_param basic program /usr/lib/squid/basic_ncsa_auth /etc/squid/passwd
auth_param basic realm KAN Proxy
acl authenticated proxy_auth REQUIRED
http_access allow authenticated
http_access deny all
http_port 3128

# גודל בופר להורדות וידאו גדולות
tcp_recv_bufsize 64 KB
read_timeout 15 minutes
request_timeout 5 minutes
connect_timeout 60 seconds

# לא לשמור לוגים של תוכן - פרטיות
access_log none
cache deny all
EOF

echo "==> מפעיל את השירות..."
systemctl restart squid
systemctl enable squid

echo ""
echo "============================================================"
echo "  ההתקנה הושלמה!"
echo "============================================================"
echo ""
echo "  בדיקה מקומית (על השרת):"
echo "    curl -x http://admin:$PASS@127.0.0.1:3128 \\"
echo "         https://www.kan.org.il/ -o /dev/null -w '%{http_code}\n'"
echo ""
echo "  ההגדרה ל-Railway (החלף SERVER_IP בכתובת הציבורית של השרת):"
echo ""
echo "    KAN_PROXY_URL = http://admin:$PASS@SERVER_IP:3128"
echo ""
echo "  אל תשכח לפתוח את פורט 3128 בחומת האש של הספק!"
echo "============================================================"
