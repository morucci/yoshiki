#!/usr/bin/env python

# MIT License
# Copyright (c) 2020 YoShiKi

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import datetime
import http.server
import time
import threading
from typing import List, Tuple


def github_mock(responses: List[str], port: int = 8080) -> Tuple[http.server.HTTPServer, threading.Thread]:
    class handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(bytes(responses.pop(0), 'utf-8'))
    httpd = http.server.HTTPServer(('127.0.0.1', port), handler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.start()
    return httpd, thread


def timestamp(delta: int) -> str:
    return datetime.datetime.fromtimestamp(time.time() + delta, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == '__main__':
    github_mock(['data-test\n'])[1].join()
