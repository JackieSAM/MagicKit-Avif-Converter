# Building MagicKit as a standalone executable

## The one thing to know up front

A Windows **`.exe`** has to be built **on Windows**. PyInstaller (and every
other Python packager) bundles the actual interpreter and native libraries
for whatever OS it's running on - it doesn't cross-compile. So:

| You want...            | Build on...      | Script              |
|-------------------------|------------------|----------------------|
| `MagicKit.exe` (Windows)| a Windows PC     | `build_windows.bat`  |
| macOS app/binary        | a Mac            | `build_unix.sh`      |
| Linux binary            | a Linux machine  | `build_unix.sh`      |

This isn't a limitation of this project specifically - it's true for every
PyInstaller/Nuitka/cx_Freeze build of any Python app. There are flaky
Docker/Wine-based workarounds for "cross-building" a .exe from Linux, but
they're unreliable and not worth the trouble for a GUI app like this one.

If you don't have a Windows PC handy: a free GitHub Actions runner (Windows)
can build it for you on every push - see the optional workflow file at
`.github/workflows/build-exe.yml`.

## Steps (Windows)

1. Install Python 3.9+ from [python.org](https://www.python.org/downloads/)
   - On the install screen, tick **"Add python.exe to PATH"**.
2. Double-click **`build_windows.bat`** in this folder.
   - It creates an isolated virtual environment, installs everything in
     `requirements.txt` (including PyInstaller), and runs the build.
3. When it finishes, your app is at:
   ```
   dist\MagicKit\MagicKit.exe
   ```
4. To share it, zip the **entire `dist\MagicKit` folder** (not just the
   .exe) - the executable needs the supporting files PyInstaller placed
   next to it.

## Steps (macOS / Linux)

```bash
chmod +x build_unix.sh   # first time only
./build_unix.sh
```
Output lands in `dist/MagicKit/`.

## Why a `.spec` file instead of `pyinstaller converter.py`

Two real issues show up if you skip it:

- **customtkinter** ships theme/font data files PyInstaller won't find on
  its own → the packaged app launches with a broken/blank UI.
- **pillow-avif-plugin** registers itself with Pillow as a side effect of
  being imported. PyInstaller's static import scanner can miss that →
  AVIF conversion works when you run `python converter.py` but silently
  fails in the packaged build.

`MagicKit.spec` explicitly collects both, so the built executable behaves
the same as running it from source.

## Antivirus false positives

PyInstaller executables occasionally get flagged by Windows
Defender/antivirus as suspicious - this is a well-known false positive
caused by how PyInstaller bundles the interpreter, not anything in this
codebase. If it happens: build it yourself from source (don't download a
prebuilt .exe from a stranger), or submit it to Microsoft as a false
positive at https://www.microsoft.com/wdsi/filesubmission.

## Troubleshooting

- **"pyinstaller not found"** → the venv wasn't activated; rerun the build
  script from scratch rather than calling `pyinstaller` directly.
- **App opens then instantly closes** → run the .exe from a terminal
  (`cmd.exe`, not double-click) so you can see the error instead of a
  flashing window. The hardened `converter.py` in this repo also pops up a
  message box on startup failure instead of vanishing silently.
- **AVIF checkbox is greyed out** → `pillow-avif-plugin` failed to import.
  Reinstall with `pip install --force-reinstall pillow-avif-plugin`.
