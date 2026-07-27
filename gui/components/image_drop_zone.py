"""图片拖拽上传组件"""
import os
import shutil
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QFont

from db.database import DATA_DIR


class ImageDropZone(QFrame):
    """支持拖拽 + 点击选择图片"""

    image_added = pyqtSignal(str)  # 图片保存路径

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('ImageDropZone')
        self.setAcceptDrops(True)
        self.setMinimumHeight(148)
        self.setMaximumHeight(190)
        self._images: list[str] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 标题
        self.title_label = QLabel('图片与截图')
        self.title_label.setObjectName('SectionTitle')
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 图标
        self.icon_label = QLabel('+')
        icon_font = QFont()
        icon_font.setPointSize(24)
        icon_font.setBold(True)
        self.icon_label.setFont(icon_font)
        self.icon_label.setStyleSheet('color: #2B7A78;')
        layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 提示
        self.hint_label = QLabel('拖放图片到这里，或按 Ctrl+V 粘贴截图')
        self.hint_label.setObjectName('SectionHint')
        layout.addWidget(self.hint_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.select_btn = QPushButton('浏览图片')
        self.select_btn.setObjectName('SecondaryButton')
        self.select_btn.clicked.connect(self._select_images)

        self.clear_btn = QPushButton('移除全部')
        self.clear_btn.setObjectName('GhostButton')
        self.clear_btn.clicked.connect(self._clear_images)
        self.clear_btn.setVisible(False)

        btn_layout.addWidget(self.select_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 已添加图片预览行
        self.preview_layout = QHBoxLayout()
        self.preview_layout.setSpacing(4)
        layout.addLayout(self.preview_layout)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self.styleSheet() + 'border: 2px dashed #4A90D9;')

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.styleSheet().replace('border: 2px dashed #4A90D9;', ''))

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet(self.styleSheet().replace('border: 2px dashed #4A90D9;', ''))
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                self._add_image(path)

    def _select_images(self):
        from PyQt5.QtWidgets import QFileDialog
        files, _ = QFileDialog.getOpenFileNames(
            self, '选择图片', '',
            '图片文件 (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;所有文件 (*.*)'
        )
        for f in files:
            self._add_image(f)

    def _add_image(self, source_path: str):
        """添加图片：复制到 data/images/ 目录"""
        images_dir = os.path.join(DATA_DIR, 'images')
        os.makedirs(images_dir, exist_ok=True)

        ext = os.path.splitext(source_path)[1] or '.png'
        import uuid
        dest_name = f'{uuid.uuid4().hex}{ext}'
        dest_path = os.path.join(images_dir, dest_name)
        shutil.copy2(source_path, dest_path)

        self._images.append(dest_path)
        self.image_added.emit(dest_path)
        self._update_preview()

    def _update_preview(self):
        # 清除旧预览
        for i in reversed(range(self.preview_layout.count())):
            widget = self.preview_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # 显示预览（最多 5 张）
        for path in self._images[:5]:
            lbl = QLabel()
            pixmap = QPixmap(path)
            pixmap = pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl.setPixmap(pixmap)
            lbl.setToolTip(os.path.basename(path))
            self.preview_layout.addWidget(lbl)

        if len(self._images) > 5:
            more = QLabel(f'+{len(self._images) - 5}')
            more.setStyleSheet('color: #6F7D87; font-size: 11pt;')
            self.preview_layout.addWidget(more)

        count = len(self._images)
        self.hint_label.setText(f'已添加 {count} 张图片' if count else '拖放图片到这里，或按 Ctrl+V 粘贴截图')
        self.clear_btn.setVisible(count > 0)

    def _clear_images(self):
        self._images.clear()
        self._update_preview()

    def get_images(self) -> list[str]:
        return self._images.copy()

    def clear_all(self):
        self._clear_images()
