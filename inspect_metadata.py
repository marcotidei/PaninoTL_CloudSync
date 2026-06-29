"""Print complete GoPro Cloud metadata records without downloading media."""

import argparse
import json
import os
import sys

import requests

from downloader import GoProPlus, REQUEST_TIMEOUT


def main():
    parser = argparse.ArgumentParser(
        description="Inspect complete metadata for a few GoPro Cloud media items."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=3,
        help="number of records to print (default: %(default)s, maximum: 10)",
    )
    parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="metadata page to inspect (default: %(default)s)",
    )
    args = parser.parse_args()

    if not 1 <= args.count <= 10:
        parser.error("--count must be between 1 and 10")
    if args.page < 1:
        parser.error("--page must be a positive integer")

    auth_token = os.environ.get("AUTH_TOKEN")
    user_id = os.environ.get("USER_ID")
    if not auth_token or not user_id:
        print("Set AUTH_TOKEN and USER_ID before running this script.", file=sys.stderr)
        return 1

    gopro = GoProPlus(auth_token, user_id)

    try:
        if not gopro.validate():
            return 1

        response = gopro.session.get(
            "{}/media/search".format(gopro.host),
            params={
                "page": args.page,
                "per_page": args.count,
            },
            headers=gopro.default_headers(),
            cookies=gopro.default_cookies(),
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code != 200:
            print(
                "Metadata request failed with status {}: {}".format(
                    response.status_code, gopro.parse_error(response)
                ),
                file=sys.stderr,
            )
            return 1

        content = response.json()
        media = content.get("_embedded", {}).get("media", [])
        print("Received {} metadata record(s) from page {}.\n".format(len(media), args.page))

        for index, item in enumerate(media, start=1):
            print("===== Record {} =====".format(index))
            safe_item = dict(item)
            if safe_item.get("token"):
                safe_item["token"] = "<redacted>"
            print(json.dumps(safe_item, indent=2, sort_keys=True, ensure_ascii=False))
            print()

        if not media:
            print("No media records were returned.")
        return 0
    except requests.RequestException as error:
        print("Network request failed: {}".format(error), file=sys.stderr)
        return 1
    except (KeyError, TypeError, ValueError) as error:
        print("Unexpected API response: {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
