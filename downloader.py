"""
Downloader code adapted from itsankoff/gopro-plus:
https://github.com/itsankoff/gopro-plus

Copyright (c) 2023 Ivaylo Tsankov
Licensed under the MIT License. See LICENSE for details.

Modified for PaninoTL Cloud Sync.
"""

import os
import sys
import argparse
import zipfile
from datetime import date

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


sys.stdout = open(1, "w", encoding="utf-8", closefd=False)
REQUEST_TIMEOUT = 30
DOWNLOAD_ATTEMPTS = 3
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.dirname(PROJECT_DIR), "PaninoTL_Downloads")


def parse_date_range(from_text="", to_text=""):
    from_value = date.fromisoformat(from_text) if from_text else None
    to_value = date.fromisoformat(to_text) if to_text else None
    if from_value and to_value and from_value > to_value:
        raise ValueError("from date cannot be later than to date")
    return from_value, to_value


def extract_zip_safely(zip_path, destination):
    destination = os.path.abspath(destination)
    os.makedirs(destination, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            member_path = os.path.abspath(os.path.join(destination, member.filename))
            if os.path.commonpath((destination, member_path)) != destination:
                raise ValueError("unsafe ZIP path: {}".format(member.filename))
        archive.extractall(destination)


class GoProPlus:
    def __init__(self, auth_token, user_id):
        self.base = "api.gopro.com"
        self.host = "https://{}".format(self.base)
        self.auth_token = auth_token
        self.user_id = user_id
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            status=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(("GET",)),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        self.session = requests.Session()
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def default_headers(self):
        return {
            "Accept": "application/vnd.gopro.jk.media+json; version=2.0.0",
            "Accept-Language": "en-US,en;q=0.9,bg;q=0.8,es;q=0.7",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }

    def default_cookies(self):
        return {
            "gp_access_token": self.auth_token,
            "gp_user_id": self.user_id,
        }

    def validate(self):
        url = f"{self.host}/media/user"
        resp = self.session.get(
            url,
            headers=self.default_headers(),
            cookies=self.default_cookies(),
            timeout=REQUEST_TIMEOUT,
        )

        if resp.status_code != 200:
            print("Failed to validate auth token. Issue a new one.")
            print(f"Status code: {resp.status_code}")
            return False

        return True

    def parse_error(self, resp):
        try:
            return resp.json()
        except (requests.exceptions.JSONDecodeError, ValueError):
            return resp.text

    def get_ids_from_media(self, media):
        return [x["id"] for x in media]

    def get_filenames_from_media(self, media):
        return [x["filename"] for x in media]

    def filter_media_by_date(self, media, from_date=None, to_date=None):
        filtered = []
        for item in media:
            created_at = item.get("created_at")
            if not created_at:
                print("Skipping media without created_at: {}".format(item.get("filename", item.get("id"))))
                continue

            try:
                created_date = date.fromisoformat(created_at[:10])
            except (TypeError, ValueError):
                print("Skipping media with invalid created_at '{}': {}".format(
                    created_at, item.get("filename", item.get("id"))
                ))
                continue

            if from_date and created_date < from_date:
                continue
            if to_date and created_date > to_date:
                continue
            filtered.append(item)

        return filtered

    def get_media(self, start_page=1, pages=sys.maxsize, per_page=30):
        url= "{}/media/search".format(self.host)

        output_media = {}
        total_pages = 0
        current_page = start_page
        while True:
            params = {
                # for all fields check some requests on GoProPlus website requests
                "per_page": per_page,
                "page": current_page,
                "fields": "id,created_at,content_title,filename,file_extension",
            }

            resp = self.session.get(
                url,
                params=params,
                headers=self.default_headers(),
                cookies=self.default_cookies(),
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code != 200:
                err = self.parse_error(resp)
                print("failed to get media for page {}: {}. try renewing the auth token".format(current_page, err))
                return []

            try:
                content = resp.json()
                media = content["_embedded"]["media"]
                response_total_pages = int(content["_pages"]["total_pages"])
                if not isinstance(media, list) or response_total_pages < 1:
                    raise ValueError
            except (KeyError, TypeError, ValueError, requests.exceptions.JSONDecodeError) as error:
                print("unexpected media response for page {}: {}".format(current_page, error))
                return []

            output_media[current_page] = media
            if total_pages == 0:
                total_pages = response_total_pages
            print("page parsed ({}/{})".format(current_page, total_pages))

            if current_page >= total_pages or current_page >= (start_page + pages) - 1:
                break

            current_page += 1

        return output_media


    def download_media_ids(self, ids, filepath, progress_mode="inline"):
        url = "{}/media/x/zip/source".format(self.host)
        params = {
            "ids": ",".join(ids),
            "access_token": self.auth_token,
        }

        partial_path = "{}.part".format(filepath)
        try:
            os.remove(partial_path)
        except FileNotFoundError:
            pass
        print("downloading to {}".format(filepath))

        for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
            downloaded_size = 0
            try:
                with self.session.get(
                    url,
                    params=params,
                    headers=self.default_headers(),
                    cookies=self.default_cookies(),
                    stream=True,
                    timeout=REQUEST_TIMEOUT,
                ) as resp:
                    if resp.status_code != 200:
                        print("request failed with status code: {} and error: {}".format(
                            resp.status_code, self.parse_error(resp)
                        ))
                        return False

                    expected_size = resp.headers.get("Content-Length")
                    expected_size = int(expected_size) if expected_size else None
                    with open(partial_path, "wb") as file:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if not chunk:
                                continue
                            file.write(chunk)
                            downloaded_size += len(chunk)
                            progress = downloaded_size / (1024 * 1024)

                            if progress_mode == "inline":
                                print(
                                    "\rdownloaded: {:.2f}MB ({}) bytes".format(
                                        progress, downloaded_size
                                    ),
                                    end="",
                                )
                            elif progress_mode == "newline":
                                print("downloaded: {:.2f}MB ({}) bytes".format(
                                    progress, downloaded_size
                                ))

                if expected_size is not None and downloaded_size != expected_size:
                    raise IOError(
                        "expected {} bytes but received {}".format(expected_size, downloaded_size)
                    )
                if not zipfile.is_zipfile(partial_path):
                    raise zipfile.BadZipFile("server response is not a valid ZIP archive")

                os.replace(partial_path, filepath)
                print("\ndownload completed!")
                return True
            except KeyboardInterrupt:
                try:
                    os.remove(partial_path)
                except FileNotFoundError:
                    pass
                raise
            except (
                OSError,
                ValueError,
                requests.RequestException,
                zipfile.BadZipFile,
            ) as error:
                try:
                    os.remove(partial_path)
                except FileNotFoundError:
                    pass
                if attempt == DOWNLOAD_ATTEMPTS:
                    print("\ndownload failed after {} attempts: {}".format(attempt, error))
                    return False
                print("\ndownload attempt {} failed: {}. Retrying…".format(attempt, error))

        return False


def main():
    actions = ["list", "download"]
    progress_modes = ["inline", "newline", "noline"]

    parser = argparse.ArgumentParser(prog="gopro")
    parser.add_argument("--action", choices=actions, help="action to execute", default="download")
    parser.add_argument("--pages", nargs="?", help="number of pages to iterate over", type=int, default=sys.maxsize)
    parser.add_argument("--per-page", nargs="?", help="number of items per page", type=int, default=30)
    parser.add_argument("--start-page", nargs="?", help="starting page", type=int, default=1)
    parser.add_argument("--from-date", type=date.fromisoformat, metavar="YYYY-MM-DD",
                        help="include media created on or after this date")
    parser.add_argument("--to-date", type=date.fromisoformat, metavar="YYYY-MM-DD",
                        help="include media created on or before this date")
    parser.add_argument(
        "--download-path",
        help="path to store the download zip",
        default=DEFAULT_DOWNLOAD_DIR,
    )
    parser.add_argument("--extract", action="store_true",
                        help="extract each downloaded ZIP into a separate folder")
    parser.add_argument("--delete-zip", action="store_true",
                        help="delete each ZIP after successful extraction")
    parser.add_argument("--progress-mode", choices=progress_modes, help="showing download progress", default=progress_modes[0])

    args = parser.parse_args()

    if args.pages < 1 or args.per_page < 1 or args.start_page < 1:
        parser.error("--pages, --per-page, and --start-page must be positive integers")
    if args.delete_zip and not args.extract:
        parser.error("--delete-zip requires --extract")
    try:
        parse_date_range(
            args.from_date.isoformat() if args.from_date else "",
            args.to_date.isoformat() if args.to_date else "",
        )
    except ValueError as error:
        parser.error(str(error))

    if "AUTH_TOKEN" not in os.environ:
        print("Missing AUTH_TOKEN environment variable.")
        return 1

    if "USER_ID" not in os.environ:
        print("Missing USER_ID environment variable.")
        return 1

    auth_token = os.environ["AUTH_TOKEN"]
    user_id = os.environ["USER_ID"]
    gpp = GoProPlus(auth_token, user_id)
    try:
        if not gpp.validate():
            return 1

        media_pages = gpp.get_media(start_page=args.start_page, pages=args.pages, per_page=args.per_page)
        if not media_pages:
            print('failed to get media')
            return 1

        if args.action == "download":
            os.makedirs(args.download_path, exist_ok=True)

        for page, media in media_pages.items():
            media = gpp.filter_media_by_date(media, args.from_date, args.to_date)
            if not media:
                print("page {} has no media in the selected date range".format(page))
                continue

            filenames = gpp.get_filenames_from_media(media)
            print("listing page({}) media({})".format(page, filenames))

            if args.action == "download":
                filepath = os.path.join(args.download_path, "{}_page.zip".format(page))
                ids = gpp.get_ids_from_media(media)
                if not gpp.download_media_ids(ids, filepath, progress_mode=args.progress_mode):
                    return 1
                if args.extract:
                    extract_path = os.path.join(args.download_path, "{}_page".format(page))
                    print("extracting to {}".format(extract_path))
                    try:
                        extract_zip_safely(filepath, extract_path)
                    except (OSError, ValueError, zipfile.BadZipFile) as error:
                        print("failed to extract {}: {}".format(filepath, error))
                        return 1
                    print("extraction completed!")
                    if args.delete_zip:
                        try:
                            os.remove(filepath)
                        except OSError as error:
                            print("extracted successfully, but failed to delete ZIP: {}".format(error))
                            return 1
                        print("deleted {}".format(filepath))
    except requests.RequestException as error:
        print("Network request failed: {}".format(error))
        return 1
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
