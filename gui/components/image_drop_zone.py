"""图片拖拽上传组件"""
import os
import shutil
from PyQt5.QtWidgets import QApplication, QFrame, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QImage, QPixmap, QFont

from db.database import DATA_DIR


class ImageDropZone(QFrame):
    """支持拖拽 + 点击选择图片"""

    image_added = pyqtSignal(str)  # 图片保存路径

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('ImageDropZone')
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip('单击此区域后可按 Ctrl+V 粘贴截图')
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
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 图标
        self.icon_label = QLabel('+')
        icon_font = QFont()
        icon_font.setPointSize(24)
        icon_font.setBold(True)
        self.icon_label.setFont(icon_font)
        self.icon_label.setStyleSheet('color: #2B7A78;')
        self.icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 提示
        self.hint_label = QLabel('单击这里后按 Ctrl+V，或直接拖放图片')
        self.hint_label.setObjectName('SectionHint')
        self.hint_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
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
        event.acceptProposedAction()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus(Qt.FocusReason.MouseFocusReason)
        super().mousePressEvent(event)

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

    def _add_pixmap(self, pixmap: QPixmap) -> str | None:
        """Persist a clipboard bitmap once and add it to the preview."""
        if pixmap.isNull():
            return None
        images_dir = os.path.join(DATA_DIR, 'images')
        os.makedirs(images_dir, exist_ok=True)
        import uuid
        dest_path = os.path.join(images_dir, f'clipboard_{uuid.uuid4().hex[:10]}.png')
        if not pixmap.save(dest_path, 'PNG'):
            return None
        self._images.append(dest_path)
        self.image_added.emit(dest_path)
        self._update_preview()
        return dest_path

    @staticmethod
    def clipboard_has_image(clipboard=None) -> bool:
        clipboard = clipboard or QApplication.clipboard()
        mime = clipboard.mimeData()
        if mime and mime.hasImage():
            return True
        return bool(mime and mime.hasUrls() and any(
            url.isLocalFile() and ImageDropZone._is_image_path(url.toLocalFile())
            for url in mime.urls()
        ))

    def paste_from_clipboard(self, clipboard=None) -> list[str]:
        """Add image data or image-file URLs currently held by the clipboard."""
        clipboard = clipboard or QApplication.clipboard()
        mime = clipboard.mimeData()
        if mime and mime.hasImage():
            image = clipboard.image()
            if image.isNull():
                image_data = mime.imageData()
                if isinstance(image_data, QPixmap):
                    pixmap = image_data
                elif isinstance(image_data, QImage):
                    pixmap = QPixmap.fromImage(image_data)
                else:
                    pixmap = QPixmap()
            else:
                pixmap = QPixmap.fromImage(image)
            saved = self._add_pixmap(pixmap)
            return [saved] if saved else []

        added = []
        if mime and mime.hasUrls():
            for url in mime.urls():
                path = url.toLocalFile()
                if url.isLocalFile() and self._is_image_path(path):
                    before = len(self._images)
                    self._add_image(path)
                    if len(self._images) > before:
                        added.append(self._images[-1])
        return added

    @staticmethod
    def _is_image_path(path: str) -> bool:
        return os.path.isfile(path) and os.path.splitext(path)[1].lower() in {
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'
        }

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
        self.hint_label.setText(
            f'已添加 {count} 张图片'
            if count else '单击这里后按 Ctrl+V，或直接拖放图片'
        )
        self.clear_btn.setVisible(count > 0)

    def _clear_images(self):
        self._images.clear()
        self._update_preview()

    def get_images(self) -> list[str]:
        return self._images.copy()

    def clear_all(self):
        self._clear_images()
