"""Qt local-socket support for the Windows single-window application."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QIODevice, QTimer
from PySide6.QtNetwork import QLocalServer, QLocalSocket


SERVER_NAME = "org.mdpeek.MDPeek.single-instance.v1"


def forward_path(path: Path | None, timeout_ms: int = 5000) -> bool:
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME, QIODevice.OpenModeFlag.WriteOnly)
    if not socket.waitForConnected(timeout_ms):
        return False
    payload = json.dumps({"path": str(path.resolve()) if path else None}, ensure_ascii=False).encode("utf-8") + b"\n"
    socket.write(payload)
    socket.flush()
    socket.waitForBytesWritten(timeout_ms)
    socket.disconnectFromServer()
    return True


class InstanceServer(QLocalServer):
    def __init__(self, receive: Callable[[Path | None], None], parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self._receive = receive
        self.newConnection.connect(self._accept)

    def start(self) -> bool:
        if self.listen(SERVER_NAME):
            return True
        # Remove only a stale endpoint; a live server was already checked by
        # the caller before this method is used.
        QLocalServer.removeServer(SERVER_NAME)
        return self.listen(SERVER_NAME)

    def _accept(self) -> None:
        while self.hasPendingConnections():
            socket = self.nextPendingConnection()
            socket.readyRead.connect(lambda socket=socket: self._read(socket))
            QTimer.singleShot(5000, socket.deleteLater)

    def _read(self, socket: QLocalSocket) -> None:
        try:
            data = json.loads(bytes(socket.readAll()).decode("utf-8"))
            value = data.get("path")
            self._receive(Path(value) if isinstance(value, str) and value else None)
        except (UnicodeError, ValueError, AttributeError):
            pass
        socket.disconnectFromServer()
