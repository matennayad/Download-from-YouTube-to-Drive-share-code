"""
בדיקות יחידה לפונקציות הטהורות של telegram_songs_to_drive.py.

הרצה:  python3 -m unittest test_telegram_songs -v
"""

import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

from telethon.tl.types import (
    DocumentAttributeAudio,
    DocumentAttributeFilename,
    DocumentAttributeVideo,
)

import telegram_songs_to_drive as tgd


def make_message(attributes, mime="audio/mpeg", size=1024 * 1024):
    """מבנה דמו הודעה: מספיק ל-classify_media."""

    document = SimpleNamespace(
        mime_type=mime,
        attributes=attributes,
        size=size,
    )

    return SimpleNamespace(
        media=SimpleNamespace(document=document),
        id=123,
    )


class TestSanitizeFilename(unittest.TestCase):

    def test_keeps_hebrew_and_spaces(self):
        self.assertEqual(
            tgd.sanitize_filename("עמיר בניון - שיר אהבה"),
            "עמיר בניון - שיר אהבה",
        )

    def test_replaces_forbidden_chars(self):
        self.assertEqual(
            tgd.sanitize_filename('a/b\\c:d*e?f"g<h>i|j'),
            "a b c d e f g h i j",
        )

    def test_collapses_whitespace(self):
        self.assertEqual(
            tgd.sanitize_filename("  a\n\nb\tc  "),
            "a b c",
        )

    def test_strips_trailing_dots(self):
        self.assertEqual(
            tgd.sanitize_filename("song name..."),
            "song name",
        )

    def test_strips_leading_dot(self):
        self.assertEqual(
            tgd.sanitize_filename(".hidden"),
            "hidden",
        )

    def test_truncates_long_names(self):
        long_name = "x" * 500
        result = tgd.sanitize_filename(long_name)
        self.assertEqual(len(result), tgd.MAX_FILENAME_LEN)

    def test_empty_gives_empty(self):
        self.assertEqual(tgd.sanitize_filename(""), "")
        self.assertEqual(tgd.sanitize_filename(None), "")


class TestExtractChannelUsername(unittest.TestCase):

    def test_at_handle(self):
        self.assertEqual(tgd.extract_channel_username("@songs"), "songs")

    def test_bare_name(self):
        self.assertEqual(tgd.extract_channel_username("songs"), "songs")

    def test_tme_url(self):
        self.assertEqual(
            tgd.extract_channel_username("https://t.me/songs"),
            "songs",
        )

    def test_tme_s_url(self):
        self.assertEqual(
            tgd.extract_channel_username("https://t.me/s/songs"),
            "songs",
        )

    def test_invalid_chars_rejected(self):
        self.assertIsNone(tgd.extract_channel_username("no spaces allowed"))

    def test_too_short_rejected(self):
        self.assertIsNone(tgd.extract_channel_username("ab"))

    def test_empty_rejected(self):
        self.assertIsNone(tgd.extract_channel_username(""))
        self.assertIsNone(tgd.extract_channel_username(None))


class TestParseChannels(unittest.TestCase):

    def test_mixed_forms(self):
        self.assertEqual(
            tgd.parse_channels("@songs, https://t.me/s/hebrew, newmusic"),
            ["songs", "hebrew", "newmusic"],
        )

    def test_dedupes(self):
        self.assertEqual(
            tgd.parse_channels("@songs, songs, t.me/songs"),
            ["songs"],
        )

    def test_skips_invalid(self):
        self.assertEqual(
            tgd.parse_channels("@good,,no no,@also_good"),
            ["good", "also_good"],
        )


class TestDedupeFilename(unittest.TestCase):

    def test_free_name_passes(self):
        taken = set()
        self.assertEqual(tgd.dedupe_filename("song.mp3", taken), "song.mp3")
        self.assertIn("song.mp3", taken)

    def test_collision_with_extension(self):
        taken = {"song.mp3"}
        self.assertEqual(
            tgd.dedupe_filename("song.mp3", taken),
            "song (2).mp3",
        )

    def test_double_collision(self):
        taken = {"song.mp3", "song (2).mp3"}
        self.assertEqual(
            tgd.dedupe_filename("song.mp3", taken),
            "song (3).mp3",
        )

    def test_collision_without_extension(self):
        taken = {"song"}
        self.assertEqual(tgd.dedupe_filename("song", taken), "song (2)")


class TestBuildTitle(unittest.TestCase):

    def test_performer_and_title(self):
        self.assertEqual(
            tgd.build_title("שיר", "אמן", "orig.mp3", "", "fb"),
            "אמן - שיר",
        )

    def test_title_only(self):
        self.assertEqual(
            tgd.build_title("שיר", None, "orig.mp3", "", "fb"),
            "שיר",
        )

    def test_original_name(self):
        self.assertEqual(
            tgd.build_title(None, None, "orig.mp3", "", "fb"),
            "orig.mp3",
        )

    def test_caption_first_line(self):
        self.assertEqual(
            tgd.build_title(None, None, None, "שורה ראשונה\nשורה שנייה", "fb"),
            "שורה ראשונה",
        )

    def test_caption_strips_channel_mention(self):
        self.assertEqual(
            tgd.build_title(None, None, None, "@songs השיר הטוב", "fb"),
            "השיר הטוב",
        )

    def test_fallback_key(self):
        self.assertEqual(
            tgd.build_title(None, None, None, "", "chan_20260930"),
            "chan_20260930",
        )

    def test_sanitizes_result(self):
        self.assertEqual(
            tgd.build_title('a/b', None, None, "", "fb"),
            "a b",
        )


class TestClassifyMedia(unittest.TestCase):

    def test_audio_document(self):
        msg = make_message(
            [
                DocumentAttributeAudio(
                    duration=200,
                    title="השיר",
                    performer="האמן",
                    voice=False,
                ),
                DocumentAttributeFilename(file_name="track.mp3"),
            ]
        )

        info = tgd.classify_media(msg)

        self.assertIsNotNone(info)
        self.assertEqual(info["kind"], "audio")
        self.assertEqual(info["audio_title"], "השיר")
        self.assertEqual(info["performer"], "האמן")
        self.assertEqual(info["original_name"], "track.mp3")

    def test_voice_excluded_by_default(self):
        msg = make_message(
            [DocumentAttributeAudio(duration=30, voice=True)]
        )

        self.assertIsNone(tgd.classify_media(msg))

    def test_voice_included_with_flag(self):
        msg = make_message(
            [DocumentAttributeAudio(duration=30, voice=True)]
        )

        info = tgd.classify_media(msg, include_voice=True)

        self.assertIsNotNone(info)
        self.assertEqual(info["kind"], "voice")

    def test_video_excluded_by_default(self):
        msg = make_message(
            [DocumentAttributeVideo(w=100, h=100, duration=60)],
            mime="video/mp4",
        )

        self.assertIsNone(tgd.classify_media(msg))

    def test_video_included_with_flag(self):
        msg = make_message(
            [DocumentAttributeVideo(w=100, h=100, duration=60)],
            mime="video/mp4",
        )

        info = tgd.classify_media(msg, include_video=True)

        self.assertIsNotNone(info)
        self.assertEqual(info["kind"], "video")

    def test_no_document_rejected(self):
        msg = SimpleNamespace(media=SimpleNamespace(photo=object()))
        self.assertIsNone(tgd.classify_media(msg))

    def test_random_document_rejected(self):
        msg = make_message(
            [DocumentAttributeFilename(file_name="book.pdf")],
            mime="application/pdf",
        )

        self.assertIsNone(tgd.classify_media(msg))


class TestPickExtension(unittest.TestCase):

    def test_from_original_name(self):
        info = {"original_name": "a.FLAC", "mime": "audio/ogg"}
        self.assertEqual(tgd.pick_extension(info), ".flac")

    def test_from_mime(self):
        info = {"original_name": None, "mime": "audio/mp4"}
        self.assertEqual(tgd.pick_extension(info), ".m4a")

    def test_fallback(self):
        info = {"original_name": None, "mime": "audio/x-unknown"}
        self.assertEqual(tgd.pick_extension(info), ".mp3")


class TestStateFile(unittest.TestCase):

    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.json")

            state = {
                "channels": {"songs": {"min_id": 42}},
                "done": {"songs:7": {"name": "x.mp3"}},
            }

            tgd.save_state(path, state)
            loaded = tgd.load_state(path)

            self.assertEqual(loaded["channels"]["songs"]["min_id"], 42)
            self.assertIn("songs:7", loaded["done"])

    def test_missing_file_gives_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            loaded = tgd.load_state(os.path.join(tmp, "nope.json"))

            self.assertEqual(loaded, {"channels": {}, "done": {}})

    def test_corrupt_file_gives_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.json")

            with open(path, "w") as f:
                f.write("{not json")

            loaded = tgd.load_state(path)

            self.assertEqual(loaded, {"channels": {}, "done": {}})


class TestMessageKey(unittest.TestCase):

    def test_format(self):
        self.assertEqual(tgd.message_key("songs", 123), "songs:123")


if __name__ == "__main__":
    unittest.main(verbosity=2)
