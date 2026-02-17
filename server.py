#!/usr/bin/env python3
"""Minimal HTTP server with CORS for the Digitize-PID Viewer."""

import http.server
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8106


class CORSHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


http.server.HTTPServer(("", PORT), CORSHandler).serve_forever()
