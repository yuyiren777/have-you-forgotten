import os
import uuid

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QCoreApplication
from PyQt5.QtTest import QTest

from utils.single_instance import SingleInstanceGuard


def test_second_instance_notifies_the_primary_instance():
    app = QCoreApplication.instance() or QCoreApplication([])
    name = f"HaveYouForgotten.test.{uuid.uuid4().hex}"
    primary = SingleInstanceGuard(server_name=name)
    activated = []
    primary.activation_requested.connect(lambda: activated.append(True))

    try:
        secondary = SingleInstanceGuard(server_name=name)
        assert primary.is_primary is True
        assert secondary.is_primary is False
        QTest.qWait(50)
        app.processEvents()
        assert activated == [True]
    finally:
        primary.close()
