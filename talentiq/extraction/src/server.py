"""Local API and static server for the Talent IQ extraction prototype."""

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from extract import extract


ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "test"), **kwargs)

    def _json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/candidates":
            candidates = []
            for folder in sorted(SAMPLES.iterdir()):
                if not folder.is_dir():
                    continue
                try:
                    meta = json.loads((folder / "candidate.json").read_text(encoding="utf-8"))
                    candidates.append(meta)
                except (OSError, json.JSONDecodeError):
                    continue
            return self._json(candidates)
        if parsed.path == "/api/sample":
            from urllib.parse import parse_qs
            candidate_id = parse_qs(parsed.query).get("id", [""])[0]
            if not candidate_id or Path(candidate_id).name != candidate_id:
                return self._json({"error": "Invalid candidate id"}, 400)
            folder = SAMPLES / candidate_id
            try:
                files = {
                    name: (folder / filename).read_text(encoding="utf-8")
                    for name, filename in (
                        ("resume", "resume.md"),
                        ("conversation", "conversation.md"),
                        ("notes", "notes.md"),
                    )
                }
            except OSError:
                return self._json({"error": "Candidate sample not found"}, 404)
            return self._json(files)
        return super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != "/api/extract":
            return self._json({"error": "Not found"}, 404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 100_000:
                return self._json({"error": "Request must be between 1 byte and 100 KB"}, 400)
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            inputs = [payload.get(name) for name in ("resume", "conversation", "notes")]
            if not all(isinstance(value, str) and value.strip() for value in inputs):
                return self._json({"error": "Provide non-empty resume, conversation, and notes text"}, 400)
            return self._json(extract(*inputs))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._json({"error": "Request body must be valid JSON"}, 400)
        except Exception as exc:
            return self._json({"error": str(exc)}, 502)


if __name__ == "__main__":
    print("Talent IQ test page: http://localhost:1341")
    ThreadingHTTPServer(("127.0.0.1", 1341), Handler).serve_forever()
