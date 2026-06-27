# Changelog

## v1.1.0 — Hardening pass (packaging release)

Fixes found while preparing this for standalone distribution:

- **Fixed: AVIF never actually worked.** `pillow-avif-plugin` was listed in
  `requirements.txt` but never imported, so Pillow had no AVIF encoder
  registered — every AVIF conversion failed. Now imported at startup; the
  AVIF checkbox is automatically disabled (with an explanation) if the
  plugin truly isn't installed, instead of failing per-file at conversion
  time.
- **Fixed: silent file overwrites in bulk mode.** Converting a folder with
  subfolders containing same-named files (e.g. `vacation/photo.jpg` and
  `work/photo.jpg`) flattened everything into one output folder and the
  second file silently clobbered the first. Output now mirrors the source
  subfolder structure, and any remaining name collision gets an auto
  `_1`, `_2`, … suffix instead of overwriting.
- **Fixed: crash on 100% failure.** If every single conversion failed, the
  summary line divided by zero, which silently killed the worker thread and
  left the UI stuck on "Converting…" forever with no error shown.
- **Fixed: unguarded output-folder creation.** Picking a destination without
  write permission (or an invalid path) threw an unhandled exception before
  conversion even started. Now shows a clear error dialog.
- **Added:** confirmation prompt if you try to close the window mid-conversion.
- **Added:** a global Tk exception handler + startup error dialog, so a
  packaged `.exe` (which has no visible console) shows *something* on
  screen if it hits an unexpected error, instead of just vanishing.

## v1.0.0

Initial version.
