"""输入卡片组件 — 文字输入区域"""
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont


class InputCard(QFrame):
    """文字输入卡片"""

    submit_text = pyqtSignal(str)  # 提交文字内容

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('InputCard')
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title_label = QLabel('文字内容')
        title_label.setObjectName('SectionTitle')
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # 提示文字
        hint = QLabel('支持自然语言，一次可识别多条安排')
        hint.setObjectName('SectionHint')
        layout.addWidget(hint)

        # 文本框
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText('例如：\n明天下午 3 点产品评审，会议室 A\n每周一上午 9 点参加站会')
        self.text_edit.setMinimumHeight(132)
        self.text_edit.setMaximumHeight(180)
        layout.addWidget(self.text_edit)

        # 按钮行
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.clear_btn = QPushButton('清空内容')
        self.clear_btn.setObjectName('GhostButton')
        self.clear_btn.clicked.connect(self._on_clear)

        self.submit_btn = QPushButton('识别文字')
        self.submit_btn.setObjectName('PrimaryButton')
        self.submit_btn.clicked.connect(self._on_submit)

        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(self.submit_btn)
        layout.addLayout(btn_layout)

    def _on_clear(self):
        self.text_edit.clear()

    def _on_submit(self):
        text = self.text_edit.toPlainText().strip()
        if text:
            self.submit_text.emit(text)

    def set_disabled(self, disabled: bool):
        self.text_edit.setDisabled(disabled)
        self.submit_btn.setDisabled(disabled)
