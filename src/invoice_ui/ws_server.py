"""
WebSocket server for broadcasting Genie AI status updates.

Adds WebSocket support to the Dash/Flask application using flask-sock,
allowing real-time status updates during AI-powered searches without
additional infrastructure.

Architecture:
- Single /ws/genie endpoint on the same port as the HTTP server
- Connected clients stored in a thread-safe set
- Status updates broadcast to all connected clients
- Automatic cleanup on client disconnect

Usage:
    # In app.py
    from invoice_ui.ws_server import init_websocket, broadcast_genie_status

    init_websocket(app.server)

    # In service code
    broadcast_genie_status({"active": True, "status": "Processing..."})
"""

import json
from collections.abc import Set
from threading import Lock

from flask import Flask
from flask_sock import Sock
from invoice_ui.lib import logs
from simple_websocket import Server as WebSocketServer

LOG = logs.logger(__file__)

# WebSocket state
_sock: Sock | None = None
_clients: Set[WebSocketServer] = set()
_clients_lock = Lock()


def init_websocket(flask_app: Flask) -> None:
    """
    Initialize WebSocket support on the Flask server.

    Args:
        flask_app: The Flask app instance (from Dash's app.server).
    """
    global _sock
    _sock = Sock(flask_app)

    @_sock.route("/ws/genie")
    def genie_ws(ws: WebSocketServer) -> None:
        """Handle WebSocket connections for Genie status updates."""
        with _clients_lock:
            _clients.add(ws)
        LOG.info("WebSocket client connected")

        try:
            while True:
                try:
                    ws.receive(timeout=30)
                except Exception:
                    break
        finally:
            with _clients_lock:
                _clients.discard(ws)
            LOG.info("WebSocket client disconnected")


def broadcast_genie_status(status_dict: dict) -> None:
    """
    Broadcast Genie status to all connected WebSocket clients.

    Thread-safe. Can be called from any thread.

    Args:
        status_dict: Serialized GenieStatusMessage dictionary.
    """
    with _clients_lock:
        if not _clients:
            return

        message = json.dumps(status_dict)
        disconnected = []

        for client in _clients:
            try:
                client.send(message)
            except Exception:
                disconnected.append(client)

        for client in disconnected:
            _clients.discard(client)
