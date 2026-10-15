"""Tiny local receiver: GET /?i=<n>&d=<urlencoded chunk> -> appended to file. Used to move browser-held CSV to disk."""
import http.server, sys, urllib.parse
out = sys.argv[1]; open(out, "wb").close()
chunks = {}
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "i" in q:
            chunks[int(q["i"][0])] = q["d"][0]
            with open(out, "w", encoding="utf-8", newline="") as f:
                f.write("".join(chunks[k] for k in sorted(chunks)))
        self.send_response(200); self.send_header("Content-Type", "image/gif"); self.end_headers(); self.wfile.write(b"GIF89a")
    def log_message(self, *a): pass
http.server.HTTPServer(("127.0.0.1", 8765), H).serve_forever()
