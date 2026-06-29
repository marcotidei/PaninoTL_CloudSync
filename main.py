"""Interactive entry point for authentication and GoPro Cloud downloads."""

import argparse
import importlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import date


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_FILE = os.path.join(PROJECT_DIR, ".gopro_auth.json")
DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.dirname(PROJECT_DIR), "PaninoTL_Downloads")
REQUIRED_MODULES = {
    "playwright": "playwright",
    "requests": "requests",
    "urllib3": "urllib3",
}


def ask_permission(message):
    try:
        return input("{} [y/N]: ".format(message)).strip().lower() in ("y", "yes")
    except EOFError:
        return False


def install_python_requirements():
    print("Installing packages from requirements.txt…")
    result = subprocess.run([
        sys.executable, "-m", "pip", "install", "--user", "-r",
        os.path.join(PROJECT_DIR, "requirements.txt"),
    ])
    importlib.invalidate_caches()
    return result.returncode == 0


def chromium_is_installed():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            return os.path.isfile(playwright.chromium.executable_path)
    except Exception:
        return False


def ensure_requirements():
    missing = [
        package for module, package in REQUIRED_MODULES.items()
        if importlib.util.find_spec(module) is None
    ]
    if missing:
        print("Missing Python packages: {}".format(", ".join(missing)))
        if not ask_permission("Install the missing project requirements now?"):
            print("Dependencies were not installed.", file=sys.stderr)
            return False
        if not install_python_requirements():
            print("Python package installation failed.", file=sys.stderr)
            return False

    if not chromium_is_installed():
        print("Playwright Chromium is not installed.")
        if not ask_permission("Download and install Playwright Chromium now?"):
            print("Chromium is required for GoPro authentication.", file=sys.stderr)
            return False
        result = subprocess.run([
            sys.executable, "-m", "playwright", "install", "chromium",
        ])
        if not chromium_is_installed():
            print("Chromium installation failed.", file=sys.stderr)
            return False
        if result.returncode != 0:
            print(
                "Playwright reported an installation warning, but Chromium "
                "was installed successfully."
            )
    return True


def load_auth():
    try:
        with open(AUTH_FILE, encoding="utf-8") as auth_file:
            auth = json.load(auth_file)
        if auth.get("AUTH_TOKEN") and auth.get("USER_ID"):
            return auth
    except (OSError, ValueError, TypeError):
        pass
    return None


def auth_needs_refresh(auth):
    import requests

    try:
        response = requests.get(
            "https://api.gopro.com/media/user",
            headers={
                "Accept": "application/vnd.gopro.jk.media+json; version=2.0.0",
                "User-Agent": "PaninoTL Cloud Sync",
            },
            cookies={
                "gp_access_token": auth["AUTH_TOKEN"],
                "gp_user_id": auth["USER_ID"],
            },
            timeout=30,
        )
    except requests.RequestException as error:
        print("Could not check saved authentication: {}".format(error))
        return False
    return response.status_code in (401, 403)


def capture_auth():
    print("Opening GoPro authentication…")
    result = subprocess.run([
        sys.executable, os.path.join(PROJECT_DIR, "capture_auth.py"),
        "--output", AUTH_FILE,
    ])
    return load_auth() if result.returncode == 0 else None


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("use YYYY-MM-DD") from error


def main():
    parser = argparse.ArgumentParser(description="Authenticate and download GoPro Cloud media.")
    parser.add_argument("--action", choices=("list", "download"))
    parser.add_argument("--from-date", type=parse_date, metavar="YYYY-MM-DD")
    parser.add_argument("--to-date", type=parse_date, metavar="YYYY-MM-DD")
    parser.add_argument("--destination")
    parser.add_argument("--pages", type=int)
    extract_group = parser.add_mutually_exclusive_group()
    extract_group.add_argument("--extract", dest="extract", action="store_true")
    extract_group.add_argument("--no-extract", dest="extract", action="store_false")
    parser.set_defaults(extract=None)
    parser.add_argument("--delete-zip", action="store_true",
                        help="delete ZIP files after successful extraction")
    parser.add_argument("--reauth", action="store_true",
                        help="capture fresh authentication")
    args = parser.parse_args()

    if args.from_date and args.to_date and args.from_date > args.to_date:
        parser.error("--from-date cannot be later than --to-date")
    if args.pages is not None and args.pages < 1:
        parser.error("--pages must be positive")
    if args.delete_zip and args.extract is False:
        parser.error("--delete-zip cannot be combined with --no-extract")

    if sys.version_info < (3, 9):
        print(
            "Python 3.9 or newer is required; found {}.{}. "
            "Please install Python manually.".format(
                sys.version_info.major, sys.version_info.minor
            ),
            file=sys.stderr,
        )
        return 1

    if not ensure_requirements():
        return 1

    auth = None if args.reauth else load_auth()
    if auth and auth_needs_refresh(auth):
        print("Saved GoPro authentication has expired.")
        auth = None
    if not auth:
        auth = capture_auth()
    if not auth:
        print("Authentication was not captured.", file=sys.stderr)
        return 1

    action = args.action or (input("Action [download/list] (download): ").strip().lower() or "download")
    if action not in ("download", "list"):
        print("Action must be 'download' or 'list'.", file=sys.stderr)
        return 1
    if args.delete_zip and action != "download":
        print("--delete-zip is only valid with the download action.", file=sys.stderr)
        return 1

    from_text = args.from_date.isoformat() if args.from_date else input(
        "From date [YYYY-MM-DD] (optional): "
    ).strip()
    to_text = args.to_date.isoformat() if args.to_date else input(
        "To date [YYYY-MM-DD] (optional): "
    ).strip()
    try:
        from_value = date.fromisoformat(from_text) if from_text else None
        to_value = date.fromisoformat(to_text) if to_text else None
        if from_value and to_value and from_value > to_value:
            raise ValueError
    except ValueError:
        print("Enter a valid date range in YYYY-MM-DD format.", file=sys.stderr)
        return 1

    pages = args.pages
    if pages is None:
        pages_text = input("Number of metadata pages (all): ").strip()
        try:
            pages = int(pages_text) if pages_text else None
            if pages is not None and pages < 1:
                raise ValueError
        except ValueError:
            print("Pages must be a positive integer.", file=sys.stderr)
            return 1

    destination = args.destination or (
        input("Download folder ({}): ".format(DEFAULT_DOWNLOAD_DIR)).strip()
        or DEFAULT_DOWNLOAD_DIR
    )
    extract = False
    delete_zip = args.delete_zip
    if action == "download":
        if args.delete_zip:
            extract = True
        elif args.extract is None:
            extract_answer = input("Extract downloaded ZIP files? [Y/n]: ").strip().lower()
            extract = extract_answer not in ("n", "no")
        else:
            extract = args.extract
        if extract and not args.delete_zip:
            delete_answer = input(
                "Delete each ZIP after successful extraction? [Y/n]: "
            ).strip().lower()
            delete_zip = delete_answer not in ("n", "no")

    command = [
        sys.executable, os.path.join(PROJECT_DIR, "downloader.py"),
        "--action", action, "--download-path", destination,
    ]
    if from_text:
        command.extend(("--from-date", from_text))
    if to_text:
        command.extend(("--to-date", to_text))
    if pages is not None:
        command.extend(("--pages", str(pages)))
    if extract:
        command.append("--extract")
    if delete_zip:
        command.append("--delete-zip")

    environment = os.environ.copy()
    environment.update(auth)
    return subprocess.run(command, env=environment).returncode


if __name__ == "__main__":
    sys.exit(main())
