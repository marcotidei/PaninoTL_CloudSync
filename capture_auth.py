"""Capture GoPro Cloud authentication values from an interactive login."""

import argparse
import json
import os
import shlex
import sys
import tempfile
import time

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


COOKIE_NAMES = {
    "gp_access_token": "AUTH_TOKEN",
    "gp_user_id": "USER_ID",
}


def find_auth_cookies(context):
    values = {}
    for cookie in context.cookies():
        environment_name = COOKIE_NAMES.get(cookie["name"])
        if environment_name and cookie["value"]:
            values[environment_name] = cookie["value"]
    return values


def main():
    parser = argparse.ArgumentParser(
        description="Open GoPro login and capture gp_access_token and gp_user_id cookies."
    )
    parser.add_argument(
        "--login-url",
        default="https://gopro.com/login",
        help="GoPro page to open (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="seconds to wait for login (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        help="securely save authentication as JSON instead of printing exports",
    )
    args = parser.parse_args()

    if args.timeout < 1:
        parser.error("--timeout must be a positive integer")

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            page.goto(args.login_url, wait_until="domcontentloaded")

            print("Complete the GoPro login in the browser window.")
            print("After login, open the GoPro media library if it is not opened automatically.")

            deadline = time.monotonic() + args.timeout
            auth = {}
            while time.monotonic() < deadline and not page.is_closed():
                auth = find_auth_cookies(context)
                if all(name in auth for name in COOKIE_NAMES.values()):
                    break
                page.wait_for_timeout(1000)

            browser.close()
    except PlaywrightError as error:
        print("Unable to start or use Chromium: {}".format(error), file=sys.stderr)
        print("Run: python3 -m playwright install chromium", file=sys.stderr)
        return 1

    if not all(name in auth for name in COOKIE_NAMES.values()):
        missing = sorted(set(COOKIE_NAMES.values()) - set(auth))
        print("Authentication values were not detected. Missing: {}".format(", ".join(missing)))
        print("Make sure login completed and the GoPro media library was opened.")
        return 1

    if args.output:
        output_path = os.path.abspath(os.path.expanduser(args.output))
        output_directory = os.path.dirname(output_path)
        os.makedirs(output_directory, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=".gopro_auth.", dir=output_directory, text=True
        )
        try:
            os.chmod(temporary_path, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as output_file:
                json.dump(auth, output_file)
                output_file.write("\n")
                output_file.flush()
                os.fsync(output_file.fileno())
            os.replace(temporary_path, output_path)
            os.chmod(output_path, 0o600)
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            try:
                os.remove(temporary_path)
            except FileNotFoundError:
                pass
            raise
        print("\nAuthentication saved securely to {}.".format(output_path))
    else:
        print("\nAuthentication captured. Run these commands in your terminal:")
        print("export AUTH_TOKEN={}".format(shlex.quote(auth["AUTH_TOKEN"])))
        print("export USER_ID={}".format(shlex.quote(auth["USER_ID"])))
        print("\nTreat these values like a password and do not commit or share them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
