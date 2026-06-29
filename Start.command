#!/usr/bin/env bash

# Keep the window open when this file is opened by double-clicking.
finish() {
    status=$?
    echo
    if [ "$status" -eq 0 ]; then
        echo "PaninoTL Cloud Sync has finished."
    else
        echo "PaninoTL Cloud Sync stopped because of an error (code $status)."
    fi
    echo
    printf '\033[1;36m%s\033[0m\n' "NEXT TIME YOU WANT TO RUN PANINOTL CLOUD SYNC:"
    printf '\033[1;36m%s\033[0m\n' "Open the \"PaninoTL Cloud Sync\" folder and double-click Start.command."
    printf '\033[1;36m%s\033[0m\n' "Keep this folder; you do not need to repeat the installation command."
    echo
    read -r -p "Press Return to close this window..."
}
trap finish EXIT

cd "$(dirname "$0")" || exit 1

create_macos_shortcut() {
    [ "$(uname -s)" = "Darwin" ] || return

    SHORTCUT="$HOME/Desktop/PaninoTL Cloud Sync.app"
    [ -f "$PWD/icons/icon.icns" ] || return

    if [ -d "$SHORTCUT" ]; then
        # Keep shortcuts made by the native applet version. Replace only the
        # incompatible shell-based bundle created by older releases.
        if [ -x "$SHORTCUT/Contents/MacOS/applet" ]; then
            return
        elif [ -x "$SHORTCUT/Contents/MacOS/launcher" ]; then
            rm -rf "$SHORTCUT"
        else
            echo "A different item named PaninoTL Cloud Sync.app already exists on the Desktop."
            return
        fi
    fi

    read -r -p "Create a PaninoTL Cloud Sync shortcut on your Desktop? [Y/n]: " answer
    case "$answer" in
        n|N|no|NO) return ;;
    esac

    osacompile -o "$SHORTCUT" \
        -e 'on run' \
        -e 'set projectPathFile to path to resource "project-path"' \
        -e 'set projectDir to do shell script "/bin/cat " & quoted form of POSIX path of projectPathFile' \
        -e 'do shell script "/usr/bin/open " & quoted form of (projectDir & "/Start.command")' \
        -e 'end run' || return

    CONTENTS="$SHORTCUT/Contents"
    cp "$PWD/icons/icon.icns" "$CONTENTS/Resources/AppIcon.icns" || return
    printf '%s\n' "$PWD" > "$CONTENTS/Resources/project-path"
    plutil -replace CFBundleName -string "PaninoTL Cloud Sync" "$CONTENTS/Info.plist"
    plutil -insert CFBundleDisplayName -string "PaninoTL Cloud Sync" "$CONTENTS/Info.plist"
    plutil -insert CFBundleIdentifier -string "com.paninotl.cloudsync.launcher" "$CONTENTS/Info.plist"
    plutil -replace CFBundleIconFile -string "AppIcon" "$CONTENTS/Info.plist"
    codesign --force --deep --sign - "$SHORTCUT" >/dev/null 2>&1 || return
    touch "$SHORTCUT"
    echo "Desktop shortcut created."
    echo
}

create_macos_shortcut

if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    echo "Python 3 was not found."
    echo "Install it from https://www.python.org/downloads/ and try again."
    exit 1
fi

echo "Checking Python..."
"$PYTHON" -c 'import sys; print("Python {}.{}.{}".format(*sys.version_info[:3]))'

"$PYTHON" main.py
