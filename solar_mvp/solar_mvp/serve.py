"""Local HTTP server for SolarFit MVP output files."""
import http.server
import socketserver
import os
from pathlib import Path
from datetime import datetime

DEFAULT_PORT = 8888
OUTPUT_DIR = Path(__file__).parent.parent / "output"

INDEX_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>SolarFit MVP — Local Dev Server</title>
  <style>
    body {{ font-family: sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; background: #f5f5f5; }}
    h1 {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin: 0 0 20px; }}
    .section {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.1); }}
    h2 {{ margin: 0 0 12px; color: #2c3e50; font-size: 1.1em; border-bottom: 2px solid #3498db; padding-bottom: 6px; }}
    a {{ display: block; padding: 8px 12px; margin: 4px 0; background: #ecf0f1; border-radius: 4px; text-decoration: none; color: #2980b9; font-size: 0.95em; }}
    a:hover {{ background: #d0e8f5; }}
    .size {{ color: #888; font-size: 0.8em; float: right; }}
    .empty {{ color: #aaa; font-style: italic; font-size: 0.9em; padding: 8px; }}
    .badge {{ display: inline-block; background: #27ae60; color: white; border-radius: 3px; padding: 2px 6px; font-size: 0.75em; margin-right: 6px; }}
  </style>
</head>
<body>
  <h1>🌞 SolarFit MVP — 해남군 태양광 적합지역 탐지</h1>

  <div class="section">
    <h2>📍 지도 (Maps)</h2>
    {map_links}
  </div>

  <div class="section">
    <h2>📊 분석 리포트 (Reports)</h2>
    {report_links}
  </div>

  <div class="section">
    <h2>📋 후보 목록 (Candidate Lists)</h2>
    {csv_links}
  </div>

  <div class="section">
    <h2>🖼 이미지 (Images)</h2>
    {img_links}
  </div>

  <div class="section" style="font-size:0.85em; color:#888;">
    Generated: {timestamp} | Output dir: {output_dir}
  </div>
</body>
</html>
"""


class SolarFitHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(OUTPUT_DIR), **kwargs)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._serve_index()
        else:
            # Serve files from output/ directly
            super().do_GET()

    def _serve_index(self):
        html = self._build_index()
        encoded = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _build_index(self) -> str:
        """Build the index HTML page."""
        def file_link(f: Path, label: str = None) -> str:
            size = f.stat().st_size
            size_str = f"{size / 1024:.0f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"
            name = label or f.name
            return f'<a href="/{f.name}" target="_blank">{name}<span class="size">{size_str}</span></a>'

        html_files = sorted(OUTPUT_DIR.glob("*.html"))
        csv_files = sorted(OUTPUT_DIR.glob("top_pnu_list*.csv"))
        png_files = sorted(OUTPUT_DIR.glob("*.png"))

        # Report links (subset of HTML)
        report_names = {"validation_report.html", "score_comparison.html"}
        report_files = [f for f in html_files if f.name in report_names]

        # Map links — all HTML files
        map_links = "\n    ".join(file_link(f) for f in html_files) or '<p class="empty">아직 생성된 지도 없음 — dev_run.py를 실행하세요</p>'

        # Report links
        report_links = "\n    ".join(file_link(f) for f in report_files) or '<p class="empty">리포트 없음</p>'

        # CSV links
        csv_links = "\n    ".join(file_link(f) for f in csv_files) or '<p class="empty">CSV 없음</p>'

        # Image links — embed as img tags
        img_parts = []
        for f in png_files:
            img_parts.append(
                f'<div style="margin:8px 0">'
                f'<p style="margin:4px 0;font-weight:bold">{f.name}</p>'
                f'<img src="/{f.name}" style="max-width:100%;border-radius:4px">'
                f'</div>'
            )
        img_links = "\n    ".join(img_parts) if img_parts else '<p class="empty">이미지 없음</p>'

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return INDEX_HTML_TEMPLATE.format(
            map_links=map_links,
            report_links=report_links,
            csv_links=csv_links,
            img_links=img_links,
            timestamp=timestamp,
            output_dir=str(OUTPUT_DIR),
        )

    def log_message(self, format, *args):
        pass  # suppress request logs for cleaner output


def serve(port: int = DEFAULT_PORT) -> None:
    """Start the local development server."""
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), SolarFitHandler) as httpd:
        print(f"\n  SolarFit MVP dev server running at:")
        print(f"  -> http://localhost:{port}")
        print(f"\n  Serving output files from: {OUTPUT_DIR}")
        print(f"  Press Ctrl+C to stop.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  Server stopped.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SolarFit MVP local dev server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    serve(port=args.port)
