# Changelog

All notable changes to this project are documented below.

### ⚡ Package Manager & Performance
- **Migrated to `uv` (Rust):** Replaced `pip` with Astral's `uv` in `Dockerfile` for ~10–100x faster dependency resolution and Docker builds.

### 📱 Mini App
- **Discontinued Mini App:** Removed backend health checks, Go/Fiber diagnostics, and related SSL tests from `/diagnostico`.

### 📦 Dependency Updates
- **OpenCV 5 Migration:** Upgraded `opencv-python-headless` to `5.0.0.93` and adapted code to breaking changes (`cv2.CASCADE_SCALE_IMAGE` removed, `VideoCapture.get()` property return handling).
- **Core Library Upgrades:** Bumped `rembg` (2.0.84), `pillow-heif` (1.7.0), and `numpy` (2.5.3).
