"""
TikTok Video Scraper - Main Entry Point

Downloads TikTok videos from URLs in a text file,
extracts metadata, and organizes them by username and date.
Optionally analyzes videos for visual and audio features.

Usage:
    python main.py                          # Uses default urls.txt and videos/ folder
    python main.py -i my_urls.txt           # Custom input file
    python main.py -o downloads/            # Custom output folder
    python main.py -b firefox               # Use Firefox instead of Chrome
    python main.py --no-browser             # Skip browser auth (public videos only)
    python main.py --analyze                # Download and analyze videos
    python main.py --analyze-only           # Only analyze existing videos
    python main.py --thoroughness maximum   # Use maximum analysis quality
"""

import argparse
import sys
import time
from pathlib import Path

from scraper import TikTokScraper
from utils import read_urls_from_file, setup_logging


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Download TikTok videos from URLs and organize by user/date.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                        Download from urls.txt to videos/
  python main.py -i links.txt           Use custom input file
  python main.py -o downloads/          Use custom output directory
  python main.py -b firefox             Use Firefox browser cookies
  python main.py --analyze              Download and analyze videos
  python main.py --analyze-only         Only analyze existing videos
  python main.py --thoroughness maximum GPU instance, best quality
        """
    )

    parser.add_argument(
        "-i", "--input",
        default="urls.txt",
        help="Input file containing TikTok URLs (default: urls.txt)"
    )

    parser.add_argument(
        "-o", "--output",
        default="videos",
        help="Output directory for downloaded videos (default: videos)"
    )

    parser.add_argument(
        "-b", "--browser",
        default="chrome",
        choices=["chrome", "firefox", "edge", "opera", "brave", "chromium"],
        help="Browser to use for cookies (default: chrome)"
    )

    parser.add_argument(
        "-l", "--log",
        default="errors.log",
        help="Error log file path (default: errors.log)"
    )

    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Skip browser cookie initialization (for public videos only)"
    )

    # Analysis options
    analysis_group = parser.add_argument_group("Analysis Options")

    analysis_group.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze downloaded videos after scraping completes"
    )

    analysis_group.add_argument(
        "--analyze-only",
        action="store_true",
        help="Skip downloading, only analyze existing videos in output directory"
    )

    analysis_group.add_argument(
        "--thoroughness",
        choices=["quick", "balanced", "thorough", "maximum", "extreme"],
        default="balanced",
        help="Analysis thoroughness preset (default: balanced). 'extreme' uses GPU heavily."
    )

    analysis_group.add_argument(
        "--sample-frames",
        type=int,
        default=None,
        help="Number of frames to sample per video (1-300, overrides preset)"
    )

    analysis_group.add_argument(
        "--sample-percent",
        type=int,
        default=None,
        help="Percentage of frames to sample (1-100, overrides --sample-frames)"
    )

    analysis_group.add_argument(
        "--color-clusters",
        type=int,
        default=None,
        help="Number of color clusters for k-means (3-20, overrides preset)"
    )

    analysis_group.add_argument(
        "--motion-res",
        type=int,
        default=None,
        help="Motion analysis resolution width in pixels (80-1080, overrides preset)"
    )

    analysis_group.add_argument(
        "--face-model",
        choices=["short", "full"],
        default=None,
        help="MediaPipe face detection model (short=fast, full=accurate)"
    )

    analysis_group.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel workers for analysis (default: CPU count - 1)"
    )

    analysis_group.add_argument(
        "--skip-audio",
        action="store_true",
        help="Skip audio analysis (faster but less complete)"
    )

    analysis_group.add_argument(
        "--scene-detection",
        action="store_true",
        help="Enable scene/cut detection (GPU intensive, auto-enabled for extreme preset)"
    )

    analysis_group.add_argument(
        "--full-resolution",
        action="store_true",
        help="Analyze at full resolution without downsampling (more accurate, slower)"
    )

    return parser.parse_args()


def print_banner():
    """Print application banner."""
    print("\n" + "=" * 50)
    print("  TikTok Video Scraper")
    print("=" * 50)


def print_summary(results: dict):
    """Print download summary."""
    print("\n" + "=" * 50)
    print("  DOWNLOAD SUMMARY")
    print("=" * 50)
    print(f"  Total URLs:    {results['total']}")
    print(f"  Successful:    {results['success']}")
    print(f"  Failed:        {results['failed']}")
    print("=" * 50)

    if results["failed"] > 0:
        print("\nFailed URLs:")
        for item in results["failed_urls"]:
            print(f"  - {item['url']}")
            print(f"    Error: {item['error']}")

    print()


def print_analysis_summary(summary: dict):
    """Print analysis results summary."""
    print("\n" + "=" * 50)
    print("  ANALYSIS SUMMARY")
    print("=" * 50)
    print(f"  Analyzed:      {summary['analyzed']}")
    print(f"  Failed:        {summary['failed']}")
    print(f"  Time:          {summary['elapsed_seconds']}s")
    print(f"  Speed:         {summary['videos_per_second']} videos/sec")
    print("=" * 50 + "\n")


def run_analysis(args, logger) -> dict:
    """
    Run batch video analysis.

    Args:
        args: Parsed command line arguments
        logger: Logger instance

    Returns:
        Analysis summary dict
    """
    from analyzer import VideoAnalyzer, get_config, find_videos_to_analyze

    # Find videos to analyze
    videos = find_videos_to_analyze(args.output)

    if not videos:
        logger.warning("No videos found to analyze")
        print(f"\nNo videos found in {args.output}")
        return {"analyzed": 0, "failed": 0, "elapsed_seconds": 0, "videos_per_second": 0}

    # Build configuration from args
    config = get_config(
        preset=args.thoroughness,
        sample_frames=args.sample_frames,
        sample_percentage=args.sample_percent,
        color_clusters=args.color_clusters,
        motion_resolution=args.motion_res,
        face_model=args.face_model,
        enable_audio=not args.skip_audio,
        workers=args.workers,
        scene_detection=args.scene_detection if args.scene_detection else None,
        full_resolution=args.full_resolution if args.full_resolution else None,
    )

    print(f"\n{'=' * 50}")
    print("  VIDEO ANALYSIS")
    print("=" * 50)
    print(f"  Videos found:  {len(videos)}")
    print(f"  Thoroughness:  {config.thoroughness}")
    # Show percentage or frame count
    if config.sample_percentage is not None:
        print(f"  Frame sample:  {int(config.sample_percentage * 100)}% of video")
    else:
        print(f"  Frames/video:  {config.sample_frames}")
    print(f"  Color clusters:{config.color_clusters}")
    print(f"  Motion res:    {config.motion_resolution}px")
    print(f"  Workers:       {config.workers or 'auto'}")
    print(f"  YOLO:          {'enabled' if config.use_yolo else 'disabled'}")
    print(f"  Scene detect:  {'enabled' if config.scene_detection else 'disabled'}")
    print(f"  Full res:      {'enabled' if config.full_resolution else 'disabled'}")
    print(f"  Audio:         {'enabled' if config.enable_audio else 'disabled'}")
    print("=" * 50)

    # Create analyzer
    analyzer = VideoAnalyzer(config, logger)

    start_time = time.time()

    # Progress callback
    def on_progress(completed, total):
        pct = completed * 100 // total
        bar_len = 30
        filled = int(bar_len * completed / total)
        bar = "=" * filled + "-" * (bar_len - filled)
        print(f"\r  Progress: [{bar}] {completed}/{total} ({pct}%)", end="", flush=True)

    print("\n  Starting analysis...\n")

    # Run batch analysis
    video_paths = [v[0] for v in videos]
    results = analyzer.analyze_batch(
        video_paths,
        workers=config.workers,
        progress_callback=on_progress
    )

    print()  # Newline after progress bar

    # Update JSON files with results
    success_count = 0
    fail_count = 0

    for video_path, json_path in videos:
        if video_path in results:
            result = results[video_path]
            if not result.errors or len(result.errors) == 0:
                if analyzer.update_metadata_file(json_path, result):
                    success_count += 1
                else:
                    fail_count += 1
            else:
                # Still save results even with errors
                analyzer.update_metadata_file(json_path, result)
                if result.video_quality:  # Has some valid data
                    success_count += 1
                else:
                    fail_count += 1
                    logger.error(f"Analysis errors for {video_path}: {result.errors}")
        else:
            fail_count += 1

    elapsed = time.time() - start_time

    return {
        "analyzed": success_count,
        "failed": fail_count,
        "elapsed_seconds": round(elapsed, 2),
        "videos_per_second": round(len(videos) / elapsed, 2) if elapsed > 0 else 0
    }


def main():
    """Main entry point."""
    args = parse_arguments()

    print_banner()

    # Setup logging
    logger = setup_logging(args.log)

    # Handle --analyze-only mode
    if args.analyze_only:
        print("\nAnalyze-only mode: skipping downloads")
        summary = run_analysis(args, logger)
        print_analysis_summary(summary)
        if summary["failed"] > 0:
            sys.exit(1)
        return

    # Check input file exists
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"\nError: Input file not found: {args.input}")
        print("Create the file and add TikTok URLs (one per line).")
        sys.exit(1)

    # Read URLs from file
    urls = read_urls_from_file(args.input)

    if not urls:
        print(f"\nNo URLs found in {args.input}")
        print("Add TikTok URLs to the file (one per line).")
        sys.exit(1)

    print(f"\nInput file:  {args.input}")
    print(f"Output dir:  {args.output}")
    print(f"Browser:     {args.browser}")
    print(f"URLs found:  {len(urls)}")

    # Initialize scraper
    scraper = TikTokScraper(args.output, logger)

    # Initialize browser (optional - will try but continue if it fails)
    if args.no_browser:
        print("\nSkipping browser initialization (--no-browser flag)")
        print("Note: Only public videos will be accessible")
    else:
        print(f"\nAttempting to initialize {args.browser} browser cookies...")
        scraper.initialize_browser(args.browser, required=False)
        if not scraper._browser_initialized:
            print("Warning: Browser cookies unavailable - continuing without authentication")
            print("Public videos should still work. Private videos may fail.")

    # Process URLs
    print("\nStarting downloads...\n")
    results = scraper.process_urls(urls)

    # Print summary
    print_summary(results)

    # Run analysis if requested
    if args.analyze:
        summary = run_analysis(args, logger)
        print_analysis_summary(summary)

    # Exit with error code if any failures
    if results["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
