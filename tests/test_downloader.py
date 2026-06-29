import io
import os
import tempfile
import unittest
import zipfile
from datetime import date
from unittest import mock

import requests

import downloader


def zip_bytes(filename="media.txt", content=b"media"):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(filename, content)
    return output.getvalue()


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, body=b"", headers=None):
        self.status_code = status_code
        self._json_data = json_data
        self._body = body
        self.headers = headers or {}
        self.text = body.decode("utf-8", errors="replace")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def json(self):
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data

    def iter_content(self, chunk_size):
        for offset in range(0, len(self._body), chunk_size):
            yield self._body[offset:offset + chunk_size]


class InterruptedResponse(FakeResponse):
    def iter_content(self, chunk_size):
        yield b"partial"
        raise KeyboardInterrupt


class DownloaderTests(unittest.TestCase):
    def setUp(self):
        self.client = downloader.GoProPlus("token", "user")
        self.addCleanup(self.client.session.close)

    def test_parse_date_range_rejects_reversed_dates(self):
        with self.assertRaises(ValueError):
            downloader.parse_date_range("2026-06-02", "2026-06-01")

    def test_filter_media_by_date_is_inclusive(self):
        media = [
            {"id": "1", "filename": "before", "created_at": "2026-05-31T23:59:59Z"},
            {"id": "2", "filename": "first", "created_at": "2026-06-01T00:00:00Z"},
            {"id": "3", "filename": "last", "created_at": "2026-06-02T23:59:59Z"},
            {"id": "4", "filename": "after", "created_at": "2026-06-03T00:00:00Z"},
        ]

        result = self.client.filter_media_by_date(
            media, date(2026, 6, 1), date(2026, 6, 2)
        )

        self.assertEqual(["2", "3"], [item["id"] for item in result])

    def test_get_media_honors_start_page_and_page_count(self):
        responses = [
            FakeResponse(json_data={
                "_embedded": {"media": [{"id": "3"}]},
                "_pages": {"total_pages": 8},
            }),
            FakeResponse(json_data={
                "_embedded": {"media": [{"id": "4"}]},
                "_pages": {"total_pages": 8},
            }),
        ]
        self.client.session.get = mock.Mock(side_effect=responses)

        result = self.client.get_media(start_page=3, pages=2)

        self.assertEqual({3: [{"id": "3"}], 4: [{"id": "4"}]}, result)
        requested_pages = [
            call.kwargs["params"]["page"]
            for call in self.client.session.get.call_args_list
        ]
        self.assertEqual([3, 4], requested_pages)

    def test_get_media_handles_malformed_response(self):
        self.client.session.get = mock.Mock(return_value=FakeResponse(
            json_data={"unexpected": "response"}
        ))

        self.assertEqual([], self.client.get_media(pages=1))

    def test_download_replaces_destination_only_after_valid_zip(self):
        body = zip_bytes()
        self.client.session.get = mock.Mock(return_value=FakeResponse(
            body=body, headers={"Content-Length": str(len(body))}
        ))

        with tempfile.TemporaryDirectory() as directory:
            destination = os.path.join(directory, "page.zip")
            with open(destination, "wb") as existing:
                existing.write(b"old")

            result = self.client.download_media_ids(
                ["one"], destination, progress_mode="noline"
            )

            self.assertTrue(result)
            self.assertTrue(zipfile.is_zipfile(destination))
            self.assertFalse(os.path.exists(destination + ".part"))

    def test_download_retries_stream_failure(self):
        body = zip_bytes()
        self.client.session.get = mock.Mock(side_effect=[
            requests.ConnectionError("temporary failure"),
            FakeResponse(body=body),
        ])

        with tempfile.TemporaryDirectory() as directory:
            destination = os.path.join(directory, "page.zip")
            result = self.client.download_media_ids(
                ["one"], destination, progress_mode="noline"
            )

            self.assertTrue(result)
            self.assertEqual(2, self.client.session.get.call_count)

    def test_failed_download_preserves_existing_destination(self):
        self.client.session.get = mock.Mock(return_value=FakeResponse(body=b"not a zip"))

        with tempfile.TemporaryDirectory() as directory:
            destination = os.path.join(directory, "page.zip")
            with open(destination, "wb") as existing:
                existing.write(b"old")

            result = self.client.download_media_ids(
                ["one"], destination, progress_mode="noline"
            )

            self.assertFalse(result)
            with open(destination, "rb") as existing:
                self.assertEqual(b"old", existing.read())
            self.assertFalse(os.path.exists(destination + ".part"))

    def test_interrupted_download_removes_partial_file(self):
        self.client.session.get = mock.Mock(return_value=InterruptedResponse())

        with tempfile.TemporaryDirectory() as directory:
            destination = os.path.join(directory, "page.zip")
            with self.assertRaises(KeyboardInterrupt):
                self.client.download_media_ids(
                    ["one"], destination, progress_mode="noline"
                )

            self.assertFalse(os.path.exists(destination))
            self.assertFalse(os.path.exists(destination + ".part"))

    def test_extract_zip_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = os.path.join(directory, "unsafe.zip")
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../outside.txt", "unsafe")

            with self.assertRaises(ValueError):
                downloader.extract_zip_safely(
                    archive_path, os.path.join(directory, "output")
                )


if __name__ == "__main__":
    unittest.main()
