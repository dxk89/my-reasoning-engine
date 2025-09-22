# File: my_framework/app/log_handler.py

import logging
from fastapi import WebSocket
import asyncio

class WebSocketLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.active_connections = []

    def add_socket(self, websocket: WebSocket):
        self.active_connections.append(websocket)

    def remove_socket(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    def emit(self, record):
        async def send_log():
            log_entry = self.format(record)
            for connection in self.active_connections:
                await connection.send_text(log_entry)
        
        asyncio.create_task(send_log())