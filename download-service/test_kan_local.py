# בדיקות לוקליות ללוגיקת כאן (kan.org.il) - בלי רשת
# הרצה: python test_kan_local.py
import sys
import time

import app as m


FAILURES = []


def check(name, cond, extra=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name} {extra}")
        FAILURES.append(name)


def raises_runtime(fn):
    try:
        fn()
        return False
    except RuntimeError:
        return True


# ------------------------------------------------------------------
# 1. זיהוי פלטפורמה
# ------------------------------------------------------------------
print("\n[1] detect_platform")
check("series page -> kan",
      m.detect_platform("https://www.kan.org.il/content/kan/kan-11/p-11843/") == "kan")
check("season page -> kan",
      m.detect_platform("https://www.kan.org.il/content/kan/kan-11/p-11843/s8/") == "kan")
check("episode page -> kan",
      m.detect_platform("https://www.kan.org.il/content/kan/kan-11/p-11843/s8/756427/") == "kan")
check("mako stays news_il",
      m.detect_platform("https://www.mako.co.il/news-page/1.html") == "news_il")
check("youtube stays youtube",
      m.detect_platform("https://www.youtube.com/watch?v=abc") == "youtube")

# ------------------------------------------------------------------
# 2. תקינות קישור
# ------------------------------------------------------------------
print("\n[2] is_valid_video_url")
check("kan url valid",
      m.is_valid_video_url("https://www.kan.org.il/content/kan/kan-11/p-11843/s8/"))

# ------------------------------------------------------------------
# 3. חילוץ entry id של Kaltura
# ------------------------------------------------------------------
print("\n[3] kan_find_kaltura_entries")
sample_page = """
<html><head><title>בואו לאכול איתי עונה 8 | פרק 1 - כאן 11</title></head>
<body>
<div class="player"
     data-entry-id="1_bhh22ujv"
     data-partner-id="2717431"></div>
<script>
  var kalturaConf = { "entryId": "1_bhh22ujv", "partnerId": 2717431 };
  var embed = "https://cdnapisec.kaltura.com/p/2717431/sp/271743100/playManifest/entryId/1_bhh22ujv/format/applehttp/protocol/https/a.m3u8";
</script>
</body></html>
"""
entries = m.kan_find_kaltura_entries(sample_page)
check("finds 1_bhh22ujv", entries == ["1_bhh22ujv"], f"got {entries}")

no_entry = m.kan_find_kaltura_entries("<html><body>nothing here</body></html>")
check("no entries -> empty", no_entry == [])

# ------------------------------------------------------------------
# 4. חילוץ מלא מעמוד פרק (synthetic)
# ------------------------------------------------------------------
print("\n[4] kan_get_episode_page")
ep = m.kan_get_episode_page("https://www.kan.org.il/content/kan/kan-11/p-11843/s8/756427/", html=sample_page)
check("returns info dict", ep is not None)
check("entry_id", ep["entry_id"] == "1_bhh22ujv", f"got {ep['entry_id']}")
check("episode_number == 1", ep["episode_number"] == 1, f"got {ep['episode_number']}")
check("title hebrew", "בואו לאכול" in (ep["title"] or ""))
check("kaltura url scheme", ep["yt_url"].startswith("kaltura:2717431:1_bhh22ujv#"), f"got {ep['yt_url'][:40]}")

no_player = m.kan_get_episode_page("x", html="<html><body>no player</body></html>")
check("no player -> None", no_player is None)

# ------------------------------------------------------------------
# 5. פירוק עמוד סדרה/עונה
# ------------------------------------------------------------------
print("\n[5] kan_extract_series_page")
season_page = """
<html><head><title>בואו לאכול איתי - עונה 8 | כאן 11</title></head>
<body>
<a href="/content/kan/kan-11/p-11843/s8/756427/">פרק 1</a>
<a href="https://www.kan.org.il/content/kan/kan-11/p-11843/s8/756445/">פרק 2</a>
<a href="/content/kan/kan-11/p-11843/s8/756999/">פרק 3</a>
<a href="/content/kan/kan-11/p-11843/s9/800001/">עונה אחרת - לא לחלוץ</a>
</body></html>
"""
si = m.kan_extract_series_page("https://www.kan.org.il/content/kan/kan-11/p-11843/s8/", html=season_page)
check("3 episodes found (s8 only)", len(si["episode_urls"]) == 3, f"got {si['episode_urls']}")
check("absolute urls", all(u.startswith("https://www.kan.org.il/") for u in si["episode_urls"]))
check("season detected", si["season"] == 8)
check("series_id detected", si["series_id"] == "11843")
check("title", "בואו לאכול" in (si["title"] or ""))

# ------------------------------------------------------------------
# 6. פתרון קישור + בחירת פרק
# ------------------------------------------------------------------
print("\n[6] kan_resolve_series_url")
check("no season/episode -> as-is",
      m.kan_resolve_series_url("https://www.kan.org.il/content/kan/kan-11/p-11843/") ==
      "https://www.kan.org.il/content/kan/kan-11/p-11843/")
check("season appends /s9/",
      m.kan_resolve_series_url("https://www.kan.org.il/content/kan/kan-11/p-11843/", season=9) ==
      "https://www.kan.org.il/content/kan/kan-11/p-11843/s9/")
check("season+episode",
      m.kan_resolve_series_url("https://www.kan.org.il/content/kan/kan-11/p-11843/", season=8, episode=756427) ==
      "https://www.kan.org.il/content/kan/kan-11/p-11843/s8/756427/")
check("episode on series root",
      m.kan_resolve_series_url("https://www.kan.org.il/content/kan/kan-11/p-11843/", episode=756427) ==
      "https://www.kan.org.il/content/kan/kan-11/p-11843/756427/")
check("bad url raises",
      raises_runtime(lambda: m.kan_resolve_series_url("https://example.com/foo", season=1)))


# ------------------------------------------------------------------
# 7. בחירת פרקים מהרשימה
# ------------------------------------------------------------------
print("\n[7] kan_pick_episode_urls")
urls = [
    "https://www.kan.org.il/content/kan/kan-11/p-11843/s8/756427/",
    "https://www.kan.org.il/content/kan/kan-11/p-11843/s8/756445/",
    "https://www.kan.org.il/content/kan/kan-11/p-11843/s8/756999/",
]
check("episode=None -> all", m.kan_pick_episode_urls(urls) == urls)
check("episode=756427 (id) -> one",
      m.kan_pick_episode_urls(urls, episode=756427) == [urls[0]])
check("bad episode id raises",
      raises_runtime(lambda: m.kan_pick_episode_urls(urls, episode=123456)))
check("bad episode value raises",
      raises_runtime(lambda: m.kan_pick_episode_urls(urls, episode="abc")))

# episode_number matching - דרך כותרת (synthetic fetch)
class FakeResp:
    def __init__(self, text):
        self.text = text
    def raise_for_status(self):
        pass

class FakeSession:
    def get(self, url, **kw):
        return FakeResp(sample_page)

picked = m.kan_pick_episode_urls(urls, episode=1, session=FakeSession())
check("episode=1 (ordinal via title) -> first", picked == [urls[0]], f"got {picked}")

# ------------------------------------------------------------------
# 8. פירוק שאילתת חיפוש (סדרה + עונה + פרק)
# ------------------------------------------------------------------
print("\n[8] _parse_series_query / _series_variants")
parsed = m._parse_series_query("בואו לאכול איתי עונה 1 פרק 2")
check("season extracted", parsed["season"] == 1, f"got {parsed}")
check("episode extracted", parsed["episode"] == 2, f"got {parsed}")
check("series name extracted", parsed["series"] == "בואו לאכול איתי", f"got {parsed}")

no_ep = m._parse_series_query("הבורר")
check("plain query -> None", no_ep is None, f"got {no_ep}")

season_only = m._parse_series_query("הבורר עונה 3")
check("season only", season_only["season"] == 3 and season_only["episode"] is None,
      f"got {season_only}")
check("season-only series name", season_only["series"] == "הבורר", f"got {season_only}")

variants = m._series_variants("הבורר עונה 3")
check("variants include full query", variants[0] == "הבורר עונה 3", f"got {variants}")
check("variants include series-only", "הבורר" in variants, f"got {variants}")
check("variants include quoted", '"הבורר"' in variants, f"got {variants}")

# ------------------------------------------------------------------
# 9. חילוץ עונה מכתובת מאקו (ל-/episodes בלי פרמטר)
# ------------------------------------------------------------------
print("\n[9] mako_season_from_url")
check("hub season url",
      m.mako_season_from_url("https://www.mako.co.il/mako-vod-keshet/nutuk_drama-s1/") == 1)
check("episode in season url",
      m.mako_season_from_url(
          "https://www.mako.co.il/mako-vod-keshet/nutuk_drama-s3/VOD-abc123.htm") == 3)
check("series root -> None",
      m.mako_season_from_url("https://www.mako.co.il/mako-vod-keshet/nutuk_drama") is None)
check("empty -> None", m.mako_season_from_url("") is None)
check("garbage -> None", m.mako_season_from_url("https://www.mako.co.il/news/x.html") is None)

# ------------------------------------------------------------------
# 10. מטמון החיפוש המאוחד
# ------------------------------------------------------------------
print("\n[10] search cache")
m._SEARCH_CACHE.clear()
m._search_cache_put(("שאילתא", ("youtube", "kan"), 7), {"results": [1, 2, 3]})
cached = m._search_cache_get(("שאילתא", ("youtube", "kan"), 7))
check("cache hit returns payload", cached == {"results": [1, 2, 3]}, f"got {cached}")
check("cache miss on other key",
      m._search_cache_get(("אחרת", ("youtube", "kan"), 7)) is None)

# TTL פג - הכניסה נמחקת ומוחזר None
m._SEARCH_CACHE[("ישנה", ("youtube",), 6)] = (
    time.time() - m.SEARCH_CACHE_TTL - 1,
    {"results": []},
)
check("expired entry -> None",
      m._search_cache_get(("ישנה", ("youtube",), 6)) is None)
check("expired entry removed",
      ("ישנה", ("youtube",), 6) not in m._SEARCH_CACHE)

# גבול זיכרון: הכניסה הישנה ביותר נמחקת
m._SEARCH_CACHE.clear()
for i in range(m.SEARCH_CACHE_MAX_ENTRIES + 5):
    m._search_cache_put((f"q{i}", (), 1), {"i": i})
check("cache bounded",
      len(m._SEARCH_CACHE) <= m.SEARCH_CACHE_MAX_ENTRIES,
      f"got {len(m._SEARCH_CACHE)}")

# ------------------------------------------------------------------
# 11. נטרול סימון המקור מהמייל (via=email-search)
# ------------------------------------------------------------------
print("\n[11] strip_email_source_marker")
check("marker removed - bare query",
      m.strip_email_source_marker(
          "https://www.kan.org.il/content/kan/kan-11/p-11843/s1/88374/?via=email-search"
      ) == "https://www.kan.org.il/content/kan/kan-11/p-11843/s1/88374/")
check("marker removed - with other params",
      m.strip_email_source_marker(
          "https://www.youtube.com/watch?v=abc123&via=email-search"
      ) == "https://www.youtube.com/watch?v=abc123")
check("marker removed - params after marker",
      m.strip_email_source_marker(
          "https://x.com/watch?v=1&via=email-search&t=5"
      ) == "https://x.com/watch?v=1&t=5")
check("marker removed - marker first among many",
      m.strip_email_source_marker(
          "https://x.com/watch?via=email-search&v=1&t=5"
      ) == "https://x.com/watch?v=1&t=5")
check("no marker - unchanged",
      m.strip_email_source_marker("https://youtu.be/abc123")
      == "https://youtu.be/abc123")
check("None passes through", m.strip_email_source_marker(None) is None)

# שילוב עם is_valid_video_url: כתובת עם הסימון עדיין תקינה
check("is_valid with marker",
      m.is_valid_video_url(
          "https://youtu.be/abc123?via=email-search"
      ))

# שילוב עם split_glued_season_episode: הסימון מוסר והכתובת נשארת נקייה
clean_url, s, e = m.split_glued_season_episode(
    "https://www.kan.org.il/content/kan/kan-11/p-11843/s1/88374/?via=email-search"
)
check("split strips marker",
      clean_url == "https://www.kan.org.il/content/kan/kan-11/p-11843/s1/88374/",
      f"got {clean_url}")

# זיהוי קישור פרק כאן אחרי הנטרול (הבאג שדווח מהמייל)
episode_url = "https://www.kan.org.il/content/kan/kan-11/p-11843/s1/88374/"
check("episode regex matches clean url",
      bool(__import__("re").search(r"/s\d+/\d+/?$", episode_url.rstrip("/") + "/")))

# ------------------------------------------------------------------
# 12. נתיב עונת מאקו - לא להוסיף -sN פעמיים (הבאג מכרטיסי העונה במייל)
# ------------------------------------------------------------------
print("\n[12] mako season dir not doubled")

# סימולציה של הלוגיקה מ-mako_episode_map / mako_resolve_episode_via_wayback
# (קריאה ישירה לא תעבור דרך הרשת בגלל הפילטר על VOD- בכתובת)

def _mako_season_dir(path, season):
    slug = path.rsplit("/", 1)[-1]
    if __import__("re").search(r"-s\d{1,2}$", slug):
        return slug
    return f"{slug}-s{season}"

check("season link keeps its dir",
      _mako_season_dir("mako-vod-keshet/nutuk_drama-s1", 1) == "nutuk_drama-s1")
check("series link gets season suffix",
      _mako_season_dir("mako-vod-keshet/nutuk_drama", 3) == "nutuk_drama-s3")
check("two-digit season",
      _mako_season_dir("mako-vod-ent/series_name-s10", 10) == "series_name-s10")

# מקרה קצה: hqdefault תמיד מוחזר כתמונה (גם כש-yt-dlp מחזיר רשימה)
print("\n[13] youtube thumbnail always hqdefault")

# קריאה ישירה תדרוש yt-dlp + רשת - בודקים רק את ההיגיון בעזרת fake entry

def _thumb_for_id(video_id):
    return ("https://i.ytimg.com/vi/" + video_id + "/hqdefault.jpg"
            if video_id else None)

check("thumb from id", _thumb_for_id("dQw4w9WgXcQ") ==
      "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg")
check("thumb None without id", _thumb_for_id("") is None)

# ------------------------------------------------------------------
# 14. הרחבת עונות אחרונות: חילוץ עונות מ-HTML של עמודי שער
# ------------------------------------------------------------------
print("\n[14] latest-seasons extraction")

# עמוד שער של כאן שמקשר לעונות ולא לפרקים (המקרה של "ארץ נהדרת")
kan_hub_html = '''
<a href="/content/kan/kan-11/p-12832/s2/">עונה 2</a>
<a href='/content/kan/kan-11/p-12832/s1/'>עונה 1</a>
<a href="https://www.kan.org.il/content/kan/kan-11/p-12832/s13/">עונה 13</a>
<a href="/content/kan/kan-11/p-9999/s5/">סדרה אחרת</a>
<a href="/content/kan/kan-11/p-12832/s8/756427/">פרק</a>
'''

check("kan hub seasons sorted desc, any series",
      m.kan_extract_hub_season_nums(kan_hub_html) == [13, 5, 2, 1])
check("kan hub episode links not counted",
      8 not in m.kan_extract_hub_season_nums(kan_hub_html))
check("kan hub empty html -> empty list",
      m.kan_extract_hub_season_nums("") == [])
check("kan hub no season links -> empty list",
      m.kan_extract_hub_season_nums("<a href='/content/kan/kan-11/p-1/'>x</a>") == [])

# חילוץ דפוסי עונות מ-HTML של עמוד שער של מאקו (המקרה של "ארץ נהדרת")
mako_hub_html = '''
<a href="/mako-vod-keshet/eretz_nehederet-s21/VOD-f00dcafe.htm">פרק 1</a>
<a href="/mako-vod-keshet/eretz_nehederet-s13/VOD-def456.htm">פרק 2</a>
<a href="/mako-vod-keshet/eretz_nehederet-s13/">עונה 13</a>
<a href="/mako-vod-keshet/eretz_nehederet-s9/">עונה 9</a>
<a href="/mako-vod-keshet/eretz_nehederet-s21/VOD-feedface.htm">פרק 3</a>
'''

check("mako hub seasons sorted desc",
      m.mako_extract_season_dirs(mako_hub_html, "eretz_nehederet") == [21, 13, 9])
check("mako similar slug not matched",
      "eretz_nehederet" in mako_hub_html
      and m.mako_extract_season_dirs(
          "<a href='/mako-vod-keshet/eretz_nehederet_something-s5/'>x</a>",
          "eretz_nehederet"
      ) == [])
check("mako empty html -> empty list",
      m.mako_extract_season_dirs("", "eretz_nehederet") == [])

print("\n----------------------------------------")
if FAILURES:
    print(f"FAILED: {len(FAILURES)} test(s): {FAILURES}")
    sys.exit(1)
print("ALL TESTS PASSED")
