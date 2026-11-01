import os
import traceback

from flask import Flask, request, jsonify
import yt_dlp


app = Flask(__name__)


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

API_KEY = os.environ.get("API_KEY", "")


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/", methods=["GET"])
def health():

    return jsonify({
        "status": "ok",
        "service": "yt-search-service"
    })


# ============================================================
# YOUTUBE SEARCH
# ============================================================
# מקבל מילות חיפוש (למשל "מוטי שטיינמץ הנשמה בקרבי"),
# מחפש ביוטיוב ומחזיר את כמה התוצאות הראשונות - שם + קישור,
# בלי להוריד כלום.

@app.route("/search", methods=["POST", "GET"])
def search_youtube():

    provided_key = request.headers.get("X-API-KEY", "")

    if not API_KEY or provided_key != API_KEY:

        return jsonify({
            "success": False,
            "error": "unauthorized"
        }), 401

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        query = data.get("query", "")
        limit = data.get("limit", 5)
    else:
        query = request.args.get("query", "")
        limit = request.args.get("limit", 5)

    query = (query or "").strip()

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 5

    limit = max(1, min(limit, 10))

    if not query:

        return jsonify({
            "success": False,
            "error": "missing 'query'"
        }), 400

    search_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android"]
            }
        }
    }

    search_term = f"ytsearch{limit}:{query}"

    print("SEARCH REQUEST:", {"query": query, "limit": limit})

    try:

        with yt_dlp.YoutubeDL(search_opts) as ydl:
            info = ydl.extract_info(search_term, download=False)

        entries = (info or {}).get("entries", []) or []

        results = []

        for entry in entries:

            if not entry:
                continue

            video_id = entry.get("id")

            url = (
                entry.get("url")
                or (
                    f"https://www.youtube.com/watch?v={video_id}"
                    if video_id
                    else None
                )
            )

            if not url:
                continue

            results.append({
                "title": entry.get("title", "ללא כותרת"),
                "url": url,
                "channel": entry.get("channel") or entry.get("uploader"),
                "duration": entry.get("duration"),
            })

        return jsonify({
            "success": True,
            "query": query,
            "results": results
        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080))
    )
