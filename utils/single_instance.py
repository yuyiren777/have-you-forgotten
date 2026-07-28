"""Prevent duplicate reminder-service processes on the same Windows account."""
import os

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtNetwork import QLocalServer, QLocalSocket
from PyQt5.QtCore import QLockFile, QStandardPaths
from PyQt5.QtNetwork import QLocalServer, QLocalSocket


SERVER_NAME = "HaveYouForgotten.ScheduleAssistant"


class SingleInstanceGuard(QObject):
    """Own a local server, or notify the already-running application."""

    activation_requested = pyqtSignal()

    def __init__(self, parent=None, server_name=SERVER_NAME):
        super().__init__(parent)
        self._server_name = server_name
        data_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation
        )
        os.makedirs(data_dir, exist_ok=True)
        self._lock = QLockFile(os.path.join(data_dir, f"{server_name}.lock"))
        # A taskkill during uninstall leaves a stale lock file. PID validation
        # still protects live instances, while a very short threshold allows
        # the next install to start immediately.
        self._lock.setStaleLockTime(1)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._handle_connection)
        self.is_primary = self._listen_or_notify_existing()

    def _listen_or_notify_existing(self) -> bool:
        if self._lock.tryLock(100):
            QLocalServer.removeServer(self._server_name)
            if self._server.listen(self._server_name):
                return True
            self._lock.unlock()
            return False

        client = QLocalSocket(self)
        client.connectToServer(self._server_name)
        if client.waitForConnected(800):
            client.write(b"show")
            client.waitForBytesWritten(300)
            client.disconnectFromServer()
            return False

        # A previous crash can leave a stale lock and server name behind.
        if self._lock.removeStaleLockFile() and self._lock.tryLock(100):
            QLocalServer.removeServer(self._server_name)
            if self._server.listen(self._server_name):
                return True
            self._lock.unlock()
        return False

    def _handle_connection(self):
        while self._server.hasPendingConnections():
            client = self._server.nextPendingConnection()
            client.readyRead.connect(lambda socket=client: self._read_request(socket))
            client.disconnected.connect(client.deleteLater)

    def _read_request(self, client: QLocalSocket):
        if client.readAll().data() == b"show":
            self.activation_requested.emit()
        client.disconnectFromServer()

    def close(self):
        self._server.close()
        QLocalServer.removeServer(self._server_name)
        if self._lock.isLocked():
            self._lock.unlock()
