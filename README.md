# PaninoTL Cloud Sync

A standalone Python script that lists or downloads media from a GoPro Media Library.

## How to use it

The first start takes a few minutes because PaninoTL Cloud Sync checks its own requirements and asks before installing anything.

### 1. Install Python

**Python 3.9 or newer is required. PaninoTL Cloud Sync cannot run without it.**

**Mac:** Python 3 may already be installed. Open Terminal and run:

```bash
python3 --version
```

If that prints Python 3.9 or newer, continue to step 2. If the command is not
found or the version is older, download and run the
[official macOS installer](https://www.python.org/downloads/macos/).

**Windows:**

1. Download Python from the
   [official Windows download page](https://www.python.org/downloads/windows/).
2. Open the downloaded installer.
3. If the installer shows **Add Python to PATH** or
   **Add python.exe to PATH**, select that option.
4. Choose **Install Now** or **Install**, then wait for installation to finish.
5. Close and reopen PowerShell before continuing to step 2.

### 2. Download PaninoTL Cloud Sync

Open the terminal for your computer:

- **Mac:** press `Command + Space`, type `Terminal`, and press Return.
- **Windows:** open the Start menu, type `PowerShell`, and press Enter.
- **Linux:** open the app named Terminal.

Copy the entire matching line below, paste it into the terminal, and press
Return. Repeating the installation removes the previous `PaninoTL Cloud Sync`
folder so stale hidden files cannot survive. Downloads are stored separately in
`PaninoTL_Downloads` and are not removed during reinstalling.

**Mac:**

```bash
cd ~/Downloads && rm -rf "PaninoTL Cloud Sync" PaninoTL_CloudSync-main && curl -L https://github.com/marcotidei/PaninoTL_CloudSync/archive/refs/heads/main.zip -o "PaninoTL Cloud Sync.zip" && ditto -xk "PaninoTL Cloud Sync.zip" . && mv PaninoTL_CloudSync-main "PaninoTL Cloud Sync" && cd "PaninoTL Cloud Sync" && chmod +x Start.command && ./Start.command
```

**Windows (PowerShell):**

```powershell
cd $HOME\Downloads; Remove-Item "PaninoTL Cloud Sync", "PaninoTL_CloudSync-main" -Recurse -Force -ErrorAction SilentlyContinue; Invoke-WebRequest https://github.com/marcotidei/PaninoTL_CloudSync/archive/refs/heads/main.zip -OutFile "PaninoTL Cloud Sync.zip"; Expand-Archive "PaninoTL Cloud Sync.zip" -DestinationPath . -Force; Rename-Item PaninoTL_CloudSync-main "PaninoTL Cloud Sync"; cd "PaninoTL Cloud Sync"; .\Start.bat
```

**Linux:**

```bash
cd ~/Downloads && rm -rf "PaninoTL Cloud Sync" PaninoTL_CloudSync-main && curl -L https://github.com/marcotidei/PaninoTL_CloudSync/archive/refs/heads/main.zip -o "PaninoTL Cloud Sync.zip" && unzip -o "PaninoTL Cloud Sync.zip" && mv PaninoTL_CloudSync-main "PaninoTL Cloud Sync" && cd "PaninoTL Cloud Sync" && chmod +x Start.command && ./Start.command
```

If the computer says that `curl` or `unzip` is missing, install that named
program with the computer's software manager and repeat the line.

### 3. Answer the questions

On the first run:

1. Press Return to create a PaninoTL Cloud Sync shortcut on the desktop, or
   type `n` to skip it.
2. Type `y` and press Return when PaninoTL Cloud Sync asks to install its requirements.
3. Type `y` again when it asks to install Chromium.
4. A browser window opens. Sign in to GoPro and open the media library if asked.
5. Return to the terminal and follow each question shown there. Pressing Return
   without typing anything accepts the choice shown in parentheses.

Your GoPro password is never saved. Authentication is saved only on this
computer in `.gopro_auth.json`. The browser opens again only when that
authentication is missing or has expired.

### Next time

Open the `Downloads` folder, then open `PaninoTL Cloud Sync`.

- If you created the desktop shortcut, double-click **PaninoTL Cloud Sync** on
  the desktop.
- On Mac, double-click `Start.command`.
- On Windows, double-click `Start.bat`.
- On Linux, open a terminal in that folder and run `./Start.command`.

If macOS blocks `Start.command`, Control-click it, choose **Open**, then choose
**Open** again.

## Troubleshooting

- **"Python was not found":** install Python using step 1, close the terminal,
  and try again.
- **Sign-in stopped working:** start PaninoTL Cloud Sync from a terminal with
  `python3 main.py --reauth` (Mac/Linux) or `py -3 main.py --reauth` (Windows).
- **Reinstalling:** the installation command removes the previous
  `PaninoTL Cloud Sync` folder first, including its saved authentication.
  Downloads in the neighboring `PaninoTL_Downloads` folder are preserved.
- **A red error appears:** do not close the window. Copy the complete error
  message; it is the most useful information when asking for help.

## Capture authentication

Authentication is normally handled automatically by `main.py`. On the first run, it opens a temporary Chromium window. Log in to GoPro there and open the media library if necessary. The captured values are saved to `.gopro_auth.json` with permissions restricted to your user; this file is ignored by Git.

Capture or replace authentication manually:

```bash
python3 capture_auth.py --output .gopro_auth.json
```

Your GoPro password is never saved. Normal app launches reuse valid saved
authentication and capture fresh authentication when needed.

## Advanced terminal usage

Normally, use `Start.command` or `Start.bat`. The commands below are for people
who want more control.

Start the guided workflow:

```bash
python3 main.py
```

It authenticates when needed, then asks for the action, date range, page count, and destination folder.

List the first page without downloading:

```bash
python3 main.py --action list --pages 1
```

Download the first page into `PaninoTL_Downloads`:

```bash
python3 main.py --action download --pages 1 --destination ../PaninoTL_Downloads
```

By default, the guided workflow asks whether downloaded ZIP archives should be extracted and whether successfully extracted archives should be deleted.
Each archive is unpacked into a separate folder such as
`PaninoTL_Downloads/1_page/`.
A ZIP is never deleted when extraction fails. For automated runs, use `--extract`,`--no-extract`, or `--delete-zip`:

```bash
python3 main.py --action download --pages 1 --destination ../PaninoTL_Downloads \
  --extract --delete-zip
```

Download media created from June 1 through June 15, inclusive:

```bash
python3 main.py --action download --from-date 2026-06-01 --to-date 2026-06-15
```

You can use either date option by itself. The script reads each item's `created_at` metadata before downloading and only sends matching media to the download endpoint. Unless `--pages` is specified, it scans all metadata pages.

See every option:

```bash
python3 main.py --help
```

The lower-level downloader remains available for direct use with `python3 downloader.py --help`; it expects `AUTH_TOKEN` and `USER_ID` environment variables.

Install the requirements manually:

```bash
python3 -m pip install --user -r requirements.txt
python3 -m playwright install chromium
```

Run the automated downloader tests:

```bash
python3 -m unittest discover -s tests -v
```

## Inspect available metadata

Print complete API metadata for three media items without downloading them:

```bash
python3 inspect_metadata.py
```

Choose a different number of records or metadata page:

```bash
python3 inspect_metadata.py --count 5 --page 2
```

The count is limited to 10 to keep terminal output manageable. Metadata may contain account or media identifiers, so review it before sharing. Signed media tokens are automatically redacted from the printed output.

## Acknowledgments

The GoPro downloading implementation is adapted from
[itsankoff/gopro-plus](https://github.com/itsankoff/gopro-plus), created by
Ivaylo Tsankov and distributed under the MIT License. See [LICENSE](LICENSE)
for license details.
