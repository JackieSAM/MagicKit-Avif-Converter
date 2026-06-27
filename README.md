# MagicKit Image Converter ⚡

**JPG → WebP & AVIF** converter with a sleek dark-mode GUI.
Lossless mode, quality slider, bulk folder conversion, live stats log.

---

## Get it running — pick one

### Option A: Download the prebuilt Windows .exe (easiest)

1. Go to the **[Actions tab](../../actions)** of this repo → latest **"Build
   Windows EXE"** run → download the `MagicKit-windows` artifact (zip).
2. Unzip it anywhere.
3. Double-click **`MagicKit.exe`** inside the unzipped folder. No Python
   install required.

   *(This .exe is built automatically by GitHub on a real Windows machine
   every time this repo is updated — see `.github/workflows/build-exe.yml`.
   You can also build it yourself locally; see [BUILD.md](BUILD.md).)*

### Option B: Run from source (Windows / macOS / Linux)

```bash
git clone https://github.com/YOUR-USERNAME/magickit-image-converter.git
cd magickit-image-converter
pip install -r requirements.txt
python converter.py
```

Requires Python 3.9+.

---

## Features

| Feature | Details |
|---|---|
| Formats | WebP + AVIF (toggle each independently) |
| Quality | 1–100 slider + quick-preset buttons (70 / 85 / 92 / 100) |
| Lossless | True lossless encoding for both formats |
| Bulk mode | Select **source folder** (scans subdirs, mirrors structure in output) + **output folder** |
| Single file | Pick individual files via the file picker |
| Live log | Per-file size, ratio, and timing |
| Stats bar | Total / Done / Failed / KB saved / Elapsed time |
| Threading | Non-blocking UI during conversion |
| Safety | Output collisions auto-renamed instead of silently overwritten; clear error dialogs instead of silent failures/freezes |

## Compression tips

- **WebP at 85%** → typically 50–70% smaller than JPG, excellent quality
- **AVIF at 80%** → 30–50% smaller than WebP at equal perceptual quality
- **Lossless** → pixel-perfect, no data loss — great for screenshots/UI assets
- `method=6` (WebP) and `speed=4` (AVIF) are used for best compression ratios

## Requirements (for running from source)

- Python 3.9+
- Pillow ≥ 10
- pillow-avif-plugin (provides AVIF encode/decode — the app detects and
  greys out the AVIF option if this isn't installed, instead of failing
  silently)
- customtkinter (dark-mode UI; falls back to plain Tkinter if missing)

## Building your own .exe / app bundle

See **[BUILD.md](BUILD.md)** — covers Windows, macOS, and Linux builds, and
explains why a `.exe` has to be built on Windows (PyInstaller doesn't
cross-compile).

## Project layout

```
converter.py               the app
requirements.txt           runtime + build dependencies
MagicKit.spec               PyInstaller build spec (handles customtkinter
                             assets + AVIF plugin registration correctly)
build_windows.bat           one-click Windows build
build_unix.sh               one-click macOS/Linux build
.github/workflows/
  build-exe.yml              CI: builds MagicKit.exe automatically on GitHub
BUILD.md                    detailed packaging instructions
CHANGELOG.md                what's changed between versions
```

## License

MIT — see [LICENSE](LICENSE).
