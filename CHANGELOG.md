# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-05

### Added
- Two-project split: `admin/` (port 5001) for generation, `client/` (port 5000) for athlete lookup
- Three-step coordinate picker (name / time / bib) in the admin web UI
- Batch certificate generation from xlsx (`name | bib | time`)
- Mobile-first athlete lookup UI (responsive, vanilla JS)
- `certificates/index.json` sidecar for O(1) client-side lookup
- Performance optimizations:
  - Template image decoded once and copied per record
  - Atomic `index.json` writes via temp-file + `os.replace`
  - mtime-based index cache on the client
  - 500ms debounce + `AbortController` for athlete queries
- Hardening:
  - xlsx row count limit (`MAX_XLSX_ROWS = 10000`)
  - Path-traversal guard (`_is_safe_key`) on the client
- Bilingual README (Chinese + English)
- `.gitignore` excluding runtime outputs and user-supplied assets
- CLI tools: `admin/pick_coords.py`, `admin/inject.py`

### Notes
- User must supply: `admin/msyhbd.ttc` (Chinese font), `admin/template.jpg` (template image), `admin/参赛成绩.xlsx` (results).
- See `README.md` for the full quick-start and architecture diagram.
