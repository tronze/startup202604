#!/usr/bin/env python3
"""
SolarFit MVP — One-command local dev runner.

Usage:
    python dev_run.py           # generate data + run pipeline + open browser
    python dev_run.py --no-open # don't open browser automatically
    python dev_run.py --force   # regenerate even if outputs exist
    python dev_run.py --serve-only  # just start server (skip pipeline)
    python dev_run.py --port 9999   # custom port
"""
import subprocess
import sys
import time
import webbrowser
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"


def run_step(description: str, cmd: list) -> bool:
    """Run a subprocess step. Returns True on success."""
    print(f"\n{'─'*50}")
    print(f"  {description}")
    print(f"{'─'*50}")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(f"\n  FAILED: {description}")
        return False
    print(f"  Done")
    return True


def main():
    parser = argparse.ArgumentParser(description="SolarFit MVP local dev runner")
    parser.add_argument("--force", action="store_true", help="Regenerate all outputs")
    parser.add_argument("--no-open", action="store_true", help="Don't open browser")
    parser.add_argument("--serve-only", action="store_true", help="Skip pipeline, just serve")
    parser.add_argument("--port", type=int, default=8888)
    args = parser.parse_args()

    python = sys.executable
    force_flag = ["--force"] if args.force else []

    print("\n" + "=" * 50)
    print("  SolarFit MVP — Local Dev Runner")
    print("=" * 50)

    if not args.serve_only:
        steps = [
            (
                "1/4 합성 데이터 생성",
                [python, "-m", "solar_mvp.make_test_data"] + force_flag,
            ),
            (
                "2/4 Stage 5 검증 (recall@K, 지도 레이어용)",
                [python, "-m", "solar_mvp.pipeline", "--start-from", "5", "--end-at", "5"] + force_flag,
            ),
            (
                "3/4 Stage 6 ML 튜닝",
                [python, "-m", "solar_mvp.pipeline", "--start-from", "6", "--end-at", "6"] + force_flag,
            ),
            (
                "4/4 Stage 7 지도 생성",
                [python, "-m", "solar_mvp.pipeline", "--start-from", "7", "--end-at", "7"] + force_flag,
            ),
        ]

        for desc, cmd in steps:
            if not run_step(desc, cmd):
                print(f"\nPipeline failed. Fix the error above and re-run.")
                sys.exit(1)

    # List generated outputs
    print("\n" + "=" * 50)
    print("  생성된 파일:")
    output_files = (
        sorted(OUTPUT_DIR.glob("*.html"))
        + sorted(OUTPUT_DIR.glob("*.csv"))
        + sorted(OUTPUT_DIR.glob("*.png"))
    )
    if output_files:
        for f in output_files:
            size_kb = f.stat().st_size / 1024
            print(f"    {f.name:45s} {size_kb:6.0f} KB")
    else:
        print("    (출력 파일 없음)")

    # Open browser then start server
    dashboard = OUTPUT_DIR / "dashboard.html"
    url = f"http://localhost:{args.port}" + ("/dashboard.html" if dashboard.exists() else "")
    if not args.no_open:
        print(f"\n  브라우저 열기: {url}")
        time.sleep(0.5)
        webbrowser.open(url)

    # Start server (blocking)
    print()
    subprocess.run(
        [python, "-m", "solar_mvp.serve", "--port", str(args.port)],
        cwd=str(PROJECT_ROOT),
    )


if __name__ == "__main__":
    main()
