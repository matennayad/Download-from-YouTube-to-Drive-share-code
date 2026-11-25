# Graph Report - download-from-youtube-to-drive-share-code  (2026-11-25)

## Corpus Check
- 40 files · ~126,651 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 6, .gs 2, .bat 2)

## Summary
- 943 nodes · 1715 edges · 55 communities (40 shown, 15 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 28 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9da5c69a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- telegram_bot.py
- Gemini Images to Drive.user.js
- inputs
- unified-search/קוד.js
- Download from YouTube to Drive.user.js
- מערכת הורדות לדרייב + חיפוש במייל — מדריך הקמה מלא
- download-service/app.py
- build_title
- download
- route
- kan_page_fetch
- steps
- 📚 דוגמאות מלאות לכל סוג הורדה
- _ddg_search_links
- list_episodes
- _extract_hidden_m3u8_once
- push-appsscript.js
- youtube-search/קוד.js
- הורדת ערוצים שלמים
- 🎵 חיבור ערוץ טלגרם לבוט — שירים אוטומטית ל-Drive
- run_season_job
- main_loop
- telegram_songs_to_drive.py
- os
- _kan_get_working_proxy
- steps
- הקמת פרוקסי על המחשב הביתי (10 דקות)
- classify_media
- הקמת פרוקסי ישראלי על VPS (10 דקות)
- 🖼️ תמונות גמיני לדרייב — מדריך הפעלה
- מדריך: פרוקסי ישראלי להורדות כאן (kan.org.il)
- 🎛️ לוח בקרה ופקודות מייל — מדריך הפעלה
- bridge_credentials
- 🤖 בוט טלגרם להורדות ל-Drive — מדריך הפעלה
- 🎵 שירים מטלגרם ל-Drive - אוטומטי
- test_kan_local.py
- downloads/appsscript.json
- unified-search/appsscript.json
- test_telegram_songs.py
- dedupe_filename
- traceback
- youtube-search/appsscript.json
- load_state
- parse_channels
- pick_extension
- _block_check_request
- drive_diag
- upload_gemini_image
- start_health_server
- mako_headless_stream
- start.sh
- PROMPT_FOR_AI.md
- setup.sh
- test.sh
- CLAUDE.md

## God Nodes (most connected - your core abstractions)
1. `send_message()` - 21 edges
2. `handle_update()` - 19 edges
3. `download()` - 19 edges
4. `buildEntry()` - 17 edges
5. `main_loop()` - 17 edges
6. `kan_page_fetch()` - 16 edges
7. `startChannelFlow()` - 16 edges
8. `_extract_hidden_m3u8_once()` - 15 edges
9. `מערכת הורדות לדרייב + חיפוש במייל — מדריך הקמה מלא` - 14 edges
10. `list_episodes()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `הערה על מכסת המיילים` --references--> `checkGmailApi()`  [INFERRED]
  docs/UNIFIED_SEARCH_SETUP.md → apps-script/unified-search/קוד.js
- `שלב 5 — טופס החיפוש המאוחד (מומלץ)` --references--> `checkGmailApi()`  [INFERRED]
  README.md → apps-script/unified-search/קוד.js
- `מגבלות שחשוב להכיר` --references--> `cleanup_stale_jobs()`  [INFERRED]
  docs/CHANNELS.md → download-service/app.py
- `הפעלה (פעם אחת)` --references--> `openDashboard()`  [INFERRED]
  docs/DASHBOARD_AND_EMAIL_COMMANDS.md → apps-script/unified-search/קוד.js
- `פתרון בעיות` --references--> `checkGmailApi()`  [INFERRED]
  docs/UNIFIED_SEARCH_SETUP.md → apps-script/unified-search/קוד.js

## Import Cycles
- None detected.

## Communities (55 total, 15 thin omitted)

### Community 0 - "telegram_bot.py"
Cohesion: 0.05
Nodes (54): api_get(), api_post(), cmd_cancel(), cmd_download(), cmd_help(), cmd_img(), cmd_link(), cmd_record() (+46 more)

### Community 1 - "Gemini Images to Drive.user.js"
Cohesion: 0.11
Nodes (49): addPending(), buildEntry(), buttonStyle(), checkAuthAndContinue(), clearPendingVerification(), closeCurrentOverlay(), composedClosest(), containerHasBrokenGeneratedImage() (+41 more)

### Community 2 - "inputs"
Cohesion: 0.04
Nodes (48): default, description, options, required, type, default, description, options (+40 more)

### Community 3 - "unified-search/קוד.js"
Cohesion: 0.10
Nodes (45): buildEmailDownloadLink(), buildResultsHtml(), buildSeasonCard(), checkSetup(), dashboardGuard_(), dashFetch_(), doGet(), encodeEmailSubject() (+37 more)

### Community 4 - "Download from YouTube to Drive.user.js"
Cohesion: 0.14
Nodes (44): addHoverEffect(), addToChannelLog(), beginWorkingState(), channelLogKey(), checkAuthAndShowOptions(), clearChannelLog(), clearPendingVerification(), closeCurrentOverlay() (+36 more)

### Community 5 - "מערכת הורדות לדרייב + חיפוש במייל — מדריך הקמה מלא"
Cohesion: 0.06
Nodes (34): checkGmailApi(), grantGmailScope(), __אשר_הרשאת_שליחת_מייל(), איך זה עובד (השרשרת המלאה), הערה על מכסת המיילים, 📖 מדריך הקמה — טופס חיפוש מאוחד (יוטיוב + מאקו + כאן 11), מה יש בפועל בכל שכבה, מפתח ה-API (+26 more)

### Community 6 - "download-service/app.py"
Cohesion: 0.09
Nodes (14): _bot_api_probe(), _bot_key_ok(), _bot_log(), bot_restart(), bot_status(), _bot_watchdog(), normalize_channel_url(), _search_cache_get() (+6 more)

### Community 7 - "build_title"
Cohesion: 0.11
Nodes (6): build_title(), extract_channel_username(), sanitize_filename(), TestBuildTitle, TestExtractChannelUsername, TestSanitizeFilename

### Community 8 - "download"
Cohesion: 0.11
Nodes (20): _ascii_header(), detect_platform(), direct_download(), release_slot(), stream_and_cleanup(), _direct_rate_ok(), download(), download_video() (+12 more)

### Community 9 - "route"
Cohesion: 0.10
Nodes (19): build_channel_plan(), channel_download(), channel_listing_candidates(), channel_preview(), expand_channel(), extract_channel_identifier(), get_job(), health() (+11 more)

### Community 10 - "kan_page_fetch"
Cohesion: 0.13
Nodes (16): debug_kan(), kan_diag(), kan_episode_stream_candidates(), kan_extract_kaltura_entry(), kan_extract_m3u8_urls(), kan_extract_series_page(), _kan_fetch_impersonated(), _kan_fetch_via_jina() (+8 more)

### Community 11 - "steps"
Cohesion: 0.08
Nodes (23): API_KEY, jobs, unit-tests, name, on, pull_request, push, workflow_dispatch (+15 more)

### Community 12 - "📚 דוגמאות מלאות לכל סוג הורדה"
Cohesion: 0.09
Nodes (22): 1️⃣ כאן (kan.org.il) — עונה שלמה, 2️⃣ כאן — פרק בודד, 3️⃣ מעקב אחרי עבודה (בלי מפתח!), 4️⃣ מאקו — פרק בודד, 5️⃣ מאקו — עונה שלמה, 6️⃣ יוטיוב / אינסטגרם / טיקטוק, 7️⃣ ערוץ יוטיוב שלם, 8️⃣ /direct — מפתח נפרד (+14 more)

### Community 13 - "_ddg_search_links"
Cohesion: 0.11
Nodes (10): _ddg_search_links(), _parse_bing(), _parse_series_query(), _search_kan_multi(), _search_kan_site(), _search_mako_multi(), _search_mako_site(), _search_youtube_via_ytdlp() (+2 more)

### Community 14 - "list_episodes"
Cohesion: 0.12
Nodes (13): kan_episode_slug(), kan_extract_hub_season_nums(), kan_pick_episode_urls(), kan_resolve_series_url(), list_episodes(), mako_episode_map(), mako_extract_season_dirs(), mako_fetch_hub_html_via_jina() (+5 more)

### Community 15 - "_extract_hidden_m3u8_once"
Cohesion: 0.14
Nodes (12): _extract_hidden_m3u8_once(), add_candidate(), inspect_response(), mako_direct_playlist(), mako_scrape_diag(), mako_ticket_candidates(), try_validate_candidates(), validate_hls_in_context() (+4 more)

### Community 16 - "push-appsscript.js"
Cohesion: 0.11
Nodes (14): fs, https, body, bodyBuffer, dir, files, fs, https (+6 more)

### Community 17 - "youtube-search/קוד.js"
Cohesion: 0.23
Nodes (17): buildEmailDownloadLink(), buildResultsHtml(), checkSetup(), escapeHtml(), extractVideoId(), fetchInlineThumbnails(), formatDuration(), getApiKey() (+9 more)

### Community 18 - "הורדת ערוצים שלמים"
Cohesion: 0.11
Nodes (16): `GET /job/<id>`, `POST /channel/download`, `POST /channel/preview`, `POST /job/<id>/cancel`, איפה הקבצים נשמרים, בדיקת חסימה (נטפרי), הורדת ערוצים שלמים, התקנה חד-פעמית (+8 more)

### Community 19 - "🎵 חיבור ערוץ טלגרם לבוט — שירים אוטומטית ל-Drive"
Cohesion: 0.11
Nodes (17): איך זה עובד (מהיר), איך מכבים את זה, בשפה פשוטה — 5 צעדים, דרך א' (מומלצת, עובדת היום): להעביר אותם לבוט, דרך ב': דימון השירים עם backfill, 🎵 חיבור ערוץ טלגרם לבוט — שירים אוטומטית ל-Drive, להוריד גם שירים *ישנים* מהערוץ (100 האחרונים), למה שיר לא ירד? טבלת אבחון (+9 more)

### Community 20 - "run_season_job"
Cohesion: 0.15
Nodes (12): build_log_text(), build_season_log_text(), ensure_drive_folder(), flush_log(), get_drive_service(), record_start(), _record_worker_app(), run_channel_job() (+4 more)

### Community 21 - "main_loop"
Cohesion: 0.16
Nodes (8): interactive_login(), main(), main_loop(), message_key(), process_one_message(), scan_channel(), status_channel(), status_update()

### Community 22 - "telegram_songs_to_drive.py"
Cohesion: 0.13
Nodes (3): _drive_find_taken_names(), get_drive_service(), upload_to_drive()

### Community 23 - "os"
Cohesion: 0.21
Nodes (5): make_client(), save_state(), api_key(), main(), main()

### Community 24 - "_kan_get_working_proxy"
Cohesion: 0.13
Nodes (11): build_ytdlp_options(), download_m3u8_with_ffmpeg(), find_downloaded_file(), il_site_profile(), _kan_fetch_proxy_candidates(), kan_get_episode_page(), _kan_get_working_proxy(), _kan_proxy_works() (+3 more)

### Community 25 - "steps"
Cohesion: 0.13
Nodes (14): runs-on, steps, timeout-minutes, jobs, check, name, on, pull_request (+6 more)

### Community 26 - "הקמת פרוקסי על המחשב הביתי (10 דקות)"
Cohesion: 0.15
Nodes (12): הקמת פרוקסי על המחשב הביתי (10 דקות), מה צריך, פתרון בעיות, שלב 1: הורדת 3proxy, שלב 2: הגדרת סיסמה, שלב 3: הרצה ובדיקה מקומית, שלב 4: פתיחת הפורט בנתב, שלב 5: חשיפה לחומת האש של Windows (+4 more)

### Community 27 - "classify_media"
Cohesion: 0.33
Nodes (3): classify_media(), make_message(), TestClassifyMedia

### Community 28 - "הקמת פרוקסי ישראלי על VPS (10 דקות)"
Cohesion: 0.17
Nodes (11): אחזקה (מינימלית), הקמת פרוקסי ישראלי על VPS (10 דקות), עלות סופית, פתרון בעיות, שלב 1: קניית ה-VPS (5-10$ לחודש), שלב 2: התחברות לשרת, שלב 3: התקנת הפרוקסי (שורה אחת!), שלב 4: פתיחת הפורט בחומת האש (+3 more)

### Community 29 - "🖼️ תמונות גמיני לדרייב — מדריך הפעלה"
Cohesion: 0.18
Nodes (10): 1. השרת (Railway/Render), 2. Apps Script, 3. התוסף בדפדפן, 🔗 איך זה עובד, 🚀 הפעלה (3 צעדים), 🛡️ מה מוגן, 📦 מה נוסף בריפו, ⚙️ מצבי הפעלה (+2 more)

### Community 30 - "מדריך: פרוקסי ישראלי להורדות כאן (kan.org.il)"
Cohesion: 0.18
Nodes (10): איך השירות משתמש בפרוקסי, אימות שהפרוקסי עובד, למה זה נדרש, מדריך: פרוקסי ישראלי להורדות כאן (kan.org.il), סיכום הארכיטקטורה, על Railway, על המחשב הביתי (Linux / Raspberry Pi), על המחשב הביתי (Windows) (+2 more)

### Community 31 - "🎛️ לוח בקרה ופקודות מייל — מדריך הפעלה"
Cohesion: 0.20
Nodes (9): openDashboard(), הפעלה (פעם אחת), הפעלה (פעם אחת), כללים, 🎛️ לוח בקרה ופקודות מייל — מדריך הפעלה, לוח הבקרה (אפשרות 12), מה השרת קיבל בשביל זה, פקודות במייל (+1 more)

### Community 33 - "🤖 בוט טלגרם להורדות ל-Drive — מדריך הפעלה"
Cohesion: 0.20
Nodes (9): איך משתמשים, 🤖 בוט טלגרם להורדות ל-Drive — מדריך הפעלה, הקלטות — גבולות, מי רשאי להשתמש?, פתרון בעיות, שלב 1: יצירת הבוט ב-BotFather (2 דקות), שלב 2: מזהה הטלגרם שלך (30 שניות), שלב 3: משתני סביבה ב-Railway (+1 more)

### Community 34 - "🎵 שירים מטלגרם ל-Drive - אוטומטי"
Cohesion: 0.20
Nodes (9): איך זה עובד (מהיר), מה מורידים (ברירות מחדל), ניטור, שאלות נפוצות, 🎵 שירים מטלגרם ל-Drive - אוטומטי, שלב 1: מקבלים api_id ו-api_hash (פעם אחת בחיים), שלב 2: יוצרים את הסשן (פעם אחת, מהמחשב שלך), שלב 3: Secrets בריוולי (+1 more)

### Community 36 - "downloads/appsscript.json"
Cohesion: 0.25
Nodes (7): dependencies, exceptionLogging, runtimeVersion, timeZone, webapp, access, executeAs

### Community 37 - "unified-search/appsscript.json"
Cohesion: 0.25
Nodes (7): dependencies, exceptionLogging, runtimeVersion, timeZone, webapp, access, executeAs

### Community 41 - "youtube-search/appsscript.json"
Cohesion: 0.33
Nodes (5): dependencies, exceptionLogging, oauthScopes, runtimeVersion, timeZone

### Community 45 - "_block_check_request"
Cohesion: 0.40
Nodes (3): _block_check_request(), check_channel_open(), check_video_open()

### Community 46 - "drive_diag"
Cohesion: 0.40
Nodes (3): drive_diag(), _drive_error_hint(), bridge_url()

### Community 47 - "upload_gemini_image"
Cohesion: 0.40
Nodes (3): gemini_image_upload(), _get_or_create_gemini_folder(), upload_gemini_image()

## Knowledge Gaps
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `cleanup_stale_jobs()` connect `הורדת ערוצים שלמים` to `download-service/app.py`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `handle_update()` (e.g. with `handle_forwarded_media()` and `handle_songs_post()`) actually correct?**
  _`handle_update()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `telegram_bot.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05292702485966319 - nodes in this community are weakly interconnected._
- **Should `Gemini Images to Drive.user.js` be split into smaller, more focused modules?**
  _Cohesion score 0.11236802413273002 - nodes in this community are weakly interconnected._
- **Should `inputs` be split into smaller, more focused modules?**
  _Cohesion score 0.04081632653061224 - nodes in this community are weakly interconnected._
- **Should `unified-search/קוד.js` be split into smaller, more focused modules?**
  _Cohesion score 0.10434782608695652 - nodes in this community are weakly interconnected._
- **Should `Download from YouTube to Drive.user.js` be split into smaller, more focused modules?**
  _Cohesion score 0.1393939393939394 - nodes in this community are weakly interconnected._