#!/usr/bin/env python3
"""Tiny MJPEG web server for a Raspberry Pi camera."""

import argparse
import signal
import subprocess
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class CameraStream:
    def __init__(self, width: int, height: int, framerate: int, camera: int):
        self.width = width
        self.height = height
        self.framerate = framerate
        self.camera = camera
        self.process: subprocess.Popen[bytes] | None = None
        self.latest_frame: bytes | None = None
        self.condition = threading.Condition()
        self.reader_thread: threading.Thread | None = None
        self.running = False

    def start(self) -> None:
        command = [
            "rpicam-vid",
            "-t",
            "0",
            "--codec",
            "mjpeg",
            "--nopreview",
            "--flush",
            "--camera",
            str(self.camera),
            "--width",
            str(self.width),
            "--height",
            str(self.height),
            "--framerate",
            str(self.framerate),
            "-o",
            "-",
        ]
        self.process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self.running = True
        self.reader_thread = threading.Thread(target=self._read_frames, daemon=True)
        self.reader_thread.start()

    def stop(self) -> None:
        self.running = False
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def _read_frames(self) -> None:
        if not self.process or not self.process.stdout:
            return

        buffer = b""
        while self.running:
            chunk = self.process.stdout.read(4096)
            if not chunk:
                break
            buffer += chunk

            while True:
                start = buffer.find(b"\xff\xd8")
                end = buffer.find(b"\xff\xd9", start + 2)
                if start == -1:
                    buffer = buffer[-1:]
                    break
                if end == -1:
                    buffer = buffer[start:]
                    break

                frame = buffer[start : end + 2]
                buffer = buffer[end + 2 :]
                with self.condition:
                    self.latest_frame = frame
                    self.condition.notify_all()

    def wait_for_frame(self, timeout: float = 2.0) -> bytes | None:
        deadline = time.monotonic() + timeout
        with self.condition:
            while self.latest_frame is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self.condition.wait(remaining)
            return self.latest_frame


def make_handler(camera_stream: CameraStream) -> type[BaseHTTPRequestHandler]:
    class CameraHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: object) -> None:
            print(f"{self.address_string()} - {fmt % args}")

        def do_GET(self) -> None:
            if self.path in ("/", "/index.html"):
                self._send_index()
            elif self.path == "/stream.mjpg":
                self._send_stream()
            elif self.path == "/snapshot.jpg":
                self._send_snapshot()
            elif self.path == "/health":
                self._send_text("ok\n")
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def _send_index(self) -> None:
            html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pi Camera Stream</title>
  <style>
    :root { color-scheme: dark; font-family: system-ui, sans-serif; }
    body { margin: 0; min-height: 100vh; background: #101114; color: #f3f4f6; display: grid; place-items: center; }
    main { width: min(100vw, 1280px); }
    img { display: block; width: 100%; height: auto; background: #050506; }
  </style>
</head>
<body>
  <main><img src="/stream.mjpg" alt="Raspberry Pi camera stream"></main>
</body>
</html>
"""
            body = html.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_snapshot(self) -> None:
            frame = camera_stream.wait_for_frame()
            if frame is None:
                self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "No camera frame available")
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(frame)))
            self.end_headers()
            self.wfile.write(frame)

        def _send_stream(self) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Age", "0")
            self.send_header("Cache-Control", "no-cache, private")
            self.send_header("Pragma", "no-cache")
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()

            while True:
                frame = camera_stream.wait_for_frame()
                if frame is None:
                    continue
                try:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii"))
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
                except (BrokenPipeError, ConnectionResetError):
                    break

        def _send_text(self, text: str) -> None:
            body = text.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return CameraHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve Raspberry Pi camera MJPEG over HTTP.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--framerate", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    camera_stream = CameraStream(args.width, args.height, args.framerate, args.camera)
    camera_stream.start()

    server = ThreadingHTTPServer((args.host, args.port), make_handler(camera_stream))

    def shutdown(_signum: int, _frame: object) -> None:
        server.shutdown()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    print(f"Serving camera stream on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    finally:
        camera_stream.stop()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
