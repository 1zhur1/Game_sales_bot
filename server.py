"""
Сервер для Render.com — только health check.
Реальный бот запускается через bot.py.
Health server уже встроен в bot.py, этот файл — на случай
если Render требует отдельный файл для web сервиса.
"""

import os
import sys
import time
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Используем другой порт, чтобы не конфликтовать с bot.py
HEALTH_PORT = int(os.getenv("HEALTH_PORT", os.getenv("PORT", 8000)))


class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass


def run_health_server():
    try:
        server = HTTPServer(("0.0.0.0", HEALTH_PORT), HealthHandler)
        server.serve_forever()
    except OSError as e:
        print(f"Health server port {HEALTH_PORT} already in use, skipping")


def start_health_server():
    t = Thread(target=run_health_server, daemon=True)
    t.start()


if __name__ == "__main__":
    print("Starting health server on port", HEALTH_PORT)
    run_health_server()