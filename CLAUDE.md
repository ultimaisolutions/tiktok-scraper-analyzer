# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python-based TikTok video scraper that downloads videos and metadata, organizing them by username and date. Includes video analysis capabilities for brightness, contrast, face/person detection, motion analysis, and more.

## Commands

```bash
# Activate virtual environment (Windows)
python -m venv .venv
.venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# Run with defaults (reads urls.txt, outputs to videos/)
python main.py

# Custom input/output
python main.py -i my_urls.txt -o downloads/

# Use specific browser for cookies (chrome/firefox/edge/opera/brave/chromium)
python main.py -b firefox

# Skip browser authentication (public videos only)
python main.py --no-browser

# Download and analyze videos
python main.py --analyze

# Only analyze existing videos (skip downloading)
python main.py --analyze-only

# Analysis with thoroughness presets
python main.py --analyze --thoroughness quick      # Fast local testing
python main.py --analyze --thoroughness balanced   # Default
python main.py --analyze --thoroughness thorough   # Better accuracy
python main.py --analyze --thoroughness maximum    # High quality with YOLO
python main.py --analyze --thoroughness extreme    # Max GPU usage, all features

# Sample 70% of frames from each video
python main.py --analyze-only --sample-percent 70

# Combine with other options
python main.py --analyze-only --sample-percent 70 --thoroughness extreme

# Sample 50% of frames
python main.py --analyze-only --sample-percent 50


# Custom analysis configuration
python main.py --analyze --sample-frames 100 --color-clusters 12 --workers 8

# Percentage-based frame sampling (samples 70% of all frames)
python main.py --analyze --sample-percent 70

# Enable specific GPU features
python main.py --analyze --scene-detection --full-resolution

# Full help
python main.py --help
```

## Architecture

```
main.py (CLI & orchestration)
    ↓
TikTokScraper (scraper.py)
    ├── Browser cookie initialization via browser-cookie3
    ├── Video download via pyktok library
    └── Metadata extraction & file organization
    ↓
VideoAnalyzer (analyzer.py)
    ├── Frame extraction & sampling
    ├── Visual analysis (brightness, contrast, sharpness, color)
    ├── Content detection (faces, persons, text overlay)
    ├── Motion analysis
    └── Audio analysis
    ↓
AnalysisModels (analysis_models.py)
    ├── MediaPipe face/pose detection (when available)
    ├── OpenCV Haar cascade fallback
    └── Optional YOLO for maximum preset
    ↓
utils.py (helpers: logging, URL parsing, metadata formatting)
```

**Data flow:**
1. `main.py` parses CLI args, reads URLs from input file
2. `TikTokScraper.initialize_browser()` sets up cookies for authentication
3. `TikTokScraper.process_urls()` iterates URLs, calling `download_video()` for each
4. Videos/metadata saved to `videos/{username}/{YYYY-MM-DD}/{video_id}.mp4|.json`
5. If `--analyze`: `VideoAnalyzer.analyze_batch()` processes videos in parallel
6. Analysis results merged into existing `.json` metadata files

## Key Classes & Functions

**TikTokScraper** (scraper.py):
- `initialize_browser(browser, required)` - Setup browser cookies for pyktok
- `download_video(url)` - Download single video + metadata, returns success/failure
- `process_urls(urls)` - Batch process with statistics tracking

**VideoAnalyzer** (analyzer.py):
- `analyze_video(path)` - Analyze single video for all metrics
- `analyze_batch(paths, workers)` - Parallel processing with multiprocessing
- `update_metadata_file(json_path, result)` - Merge analysis into metadata JSON

**AnalysisModels** (analysis_models.py):
- `detect_faces(frame, model_type)` - Face detection (MediaPipe or Haar cascade)
- `detect_persons(frame, use_yolo)` - Person detection with fallback chain
- `get_backend_info()` - Check available detection backends

**utils.py**:
- `extract_video_id(url)` / `extract_username_from_url(url)` - Parse TikTok URLs
- `format_metadata(raw_data)` - Structure TikTok JSON response into clean metadata
- `setup_logging(log_file)` - Dual logging: console (INFO) + file (ERROR)

## Analysis Features

| Feature | Method | Output |
|---------|--------|--------|
| Brightness | Grayscale mean | mean, std, min, max |
| Contrast | Grayscale std dev | mean, std |
| Sharpness | Laplacian variance | mean, std |
| Face detection | MediaPipe/Haar | detected, count, avg |
| Person detection | MediaPipe/YOLO/Haar | detected, count, avg |
| Text overlay | Contour analysis | detected, frequency |
| Motion level | Frame differencing | score (0-100), level |
| Color palette | K-means clustering | dominant colors, temperature |
| Scene detection | Histogram comparison | scene count, cuts/min, durations |
| Audio | moviepy RMS | volume dB, speech detection |

## Thoroughness Presets

Optimized for modern GPUs (RTX 4060Ti or better):

| Preset | Frames | Color K | Motion Res | YOLO | Scene Detect | Full Res | Use Case |
|--------|--------|---------|------------|------|--------------|----------|----------|
| `quick` | 15 | 4 | 120 | No | No | No | Fast testing |
| `balanced` | 30 | 6 | 240 | No | No | No | Default |
| `thorough` | 50 | 8 | 360 | No | No | No | Better accuracy |
| `maximum` | 80 | 12 | 640 | Yes | No | No | High quality |
| `extreme` | 150 | 16 | 720 | Yes | Yes | Yes | Max GPU usage |

Frame coverage for 3-min video at 30fps (~5400 frames):
- `quick`: ~0.3% coverage
- `balanced`: ~0.6% coverage
- `thorough`: ~1% coverage
- `maximum`: ~1.5% coverage
- `extreme`: ~2.8% coverage

### Percentage-Based Sampling
Use `--sample-percent` to sample a percentage of total frames instead of a fixed count:
- `--sample-percent 70` samples 70% of all frames in the video
- Overrides `--sample-frames` when specified
- Minimum 5 frames, maximum is total frame count

### GPU-Heavy Features (extreme preset)
- **YOLO person detection**: Multi-person tracking using YOLOv8 (CUDA accelerated)
- **Scene detection**: Finds cuts/transitions using histogram comparison
- **Full resolution**: Analyzes frames without downsampling

## Output Structure

```
videos/
└── {username}/
    └── {YYYY-MM-DD}/
        ├── {video_id}.mp4
        └── {video_id}.json  (metadata + analysis results)
```

**Analysis JSON schema** (added to existing metadata):
```json
{
  "analysis": {
    "version": "1.1.0",
    "settings": { "thoroughness": "extreme", "sample_frames": 150, "scene_detection": true, ... },
    "video_quality": { "resolution": {...}, "fps": 30, "duration_seconds": 21, "frames_analyzed": 150 },
    "visual_metrics": { "brightness": {...}, "contrast": {...}, "sharpness": {...} },
    "content_detection": { "face_detected": true, "person_detected": true, ... },
    "motion_analysis": { "motion_score": 56.5, "motion_level": "high" },
    "color_analysis": { "dominant_colors": [...], "color_temperature": "warm" },
    "scene_analysis": { "scene_count": 5, "cuts_per_minute": 12.3, "avg_scene_duration": 4.2, ... },
    "audio_metrics": { "has_audio": true, "avg_volume_db": -16.6, ... }
  }
}
```

## Dependencies

**Core:** `pyktok`, `playwright`, `browser-cookie3`, `beautifulsoup4`, `requests`, `pandas`, `numpy`

**Video Analysis:** `opencv-python-headless`, `moviepy`, `scikit-image`

**GPU Acceleration:** `ultralytics` (YOLO for maximum/extreme presets)

**Optional:** `mediapipe` (Python <3.13 only)

## Known Issues

- Browser cookie extraction may fail with "Unable to get key for cookie decryption" - use `--no-browser` flag as workaround for public videos
- Requires browser to be closed when extracting cookies
- MediaPipe requires Python <3.13; falls back to Haar cascades on newer Python versions
