"""Progressive settings wizard for model, reminder, and notification options."""
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from core.api_client import test_connection
from db.database import get_db
from db.models import Config
from utils.crypto import decrypt, encrypt


class ConnectionTestThread(QThread):
    """Run the model network check outside Qt's UI thread."""

    completed = pyqtSignal(bool, str)

    def run(self):
        try:
            ok, message = test_connection()
        except Exception as error:
            ok, message = False, f'连接测试异常：{error}'
        self.completed.emit(ok, message)


class SettingsPage(QWidget):
    """Four-step settings wizard that reveals one task at a time."""

    setup_completed = pyqtSignal()
    theme_changed = pyqtSignal(str)

    STEP_TITLES = ("AI 模型", "提醒规则", "微信通知", "邮件通知")
    STEP_DESCRIPTIONS = (
        "选择识别日程所使用的模型，并填写访问凭证。",
        "设置日程开始前多久发送提醒。",
        "微信通知是可选项，不需要时可直接进入下一步。",
        "邮件通知是可选项，完成后统一保存全部设置。",
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsPage")
        self._current_step = 0
        self._step_indicators = []
        self._setup_ui()
        self._load_config()
        self._show_step(0)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(4)
        title = QLabel("设置")
        title.setObjectName("PageTitle")
        header_text.addWidget(title)

        subtitle = QLabel("按步骤完成配置，每次只处理一组设置")
        subtitle.setObjectName("PageSubtitle")
        header_text.addWidget(subtitle)
        header_row.addLayout(header_text)
        header_row.addStretch()

        theme_label = QLabel("界面主题")
        theme_label.setObjectName("ThemeLabel")
        header_row.addWidget(theme_label)
        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("ThemeCombo")
        self.theme_combo.addItem("浅色主题", "light")
        self.theme_combo.addItem("夜间主题", "dark")
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        header_row.addWidget(self.theme_combo)
        layout.addLayout(header_row)
        layout.addSpacing(8)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)
        for index, step_title in enumerate(self.STEP_TITLES):
            indicator = QLabel(f"{index + 1}  {step_title}")
            indicator.setObjectName("StepIndicator")
            indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
            indicator.setMinimumHeight(38)
            progress_row.addWidget(indicator, 1)
            self._step_indicators.append(indicator)
        layout.addLayout(progress_row)

        self.step_position = QLabel()
        self.step_position.setObjectName("StepPosition")
        layout.addWidget(self.step_position)

        self.step_stack = QStackedWidget()
        self.step_stack.addWidget(self._build_model_step())
        self.step_stack.addWidget(self._build_reminder_step())
        self.step_stack.addWidget(self._build_wechat_step())
        self.step_stack.addWidget(self._build_email_step())
        layout.addWidget(self.step_stack, 1)

        navigation = QHBoxLayout()
        navigation.setSpacing(10)

        self.back_btn = QPushButton("上一步")
        self.back_btn.setObjectName("SecondaryButton")
        self.back_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self.back_btn.clicked.connect(self._previous_step)
        navigation.addWidget(self.back_btn)

        navigation.addStretch()

        self.next_hint = QLabel()
        self.next_hint.setObjectName("MutedLabel")
        navigation.addWidget(self.next_hint)

        self.next_btn = QPushButton("下一步")
        self.next_btn.setObjectName("PrimaryButton")
        self.next_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowForward))
        self.next_btn.setMinimumWidth(124)
        self.next_btn.clicked.connect(self._next_step)
        navigation.addWidget(self.next_btn)

        layout.addLayout(navigation)

    def _build_step(self, title: str, description: str) -> tuple[QWidget, QFormLayout]:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 4, 0, 4)
        page_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        card = QFrame()
        card.setObjectName("SettingsCard")
        card.setMaximumWidth(760)
        card.setMinimumWidth(560)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 26, 28, 28)
        card_layout.setSpacing(10)

        heading = QLabel(title)
        heading.setObjectName("SettingsStepTitle")
        card_layout.addWidget(heading)

        hint = QLabel(description)
        hint.setObjectName("SettingsStepHint")
        hint.setWordWrap(True)
        card_layout.addWidget(hint)
        card_layout.addSpacing(12)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(14)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        card_layout.addLayout(form)

        page_layout.addWidget(card)
        return page, form

    def _build_model_step(self) -> QWidget:
        page, form = self._build_step(
            "连接 AI 模型", "API Key 为必填项，用于识别文字和图片中的日程。API 地址和模型名称均可留空，填上自定义配置会更灵活。"
        )

        self.provider_combo = QComboBox()
        self.provider_combo.addItem("zhipu - 智谱 GLM-4.6V-Flash")
        self.provider_combo.setEnabled(False)
        form.addRow("模型提供商", self.provider_combo)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("必填：输入 API Key")
        form.addRow("API Key（必填）", self.api_key_input)

        self.api_base_input = QLineEdit()
        self.api_base_input.setPlaceholderText("选填：留空使用默认地址")
        form.addRow("API 地址（选填）", self.api_base_input)

        self.model_name_input = QLineEdit()
        self.model_name_input.setPlaceholderText("选填：留空使用默认模型")
        form.addRow("模型名称（选填）", self.model_name_input)

        self.connection_test_btn = QPushButton("测试连接")
        self.connection_test_btn.setObjectName("SecondaryButton")
        self.connection_test_btn.clicked.connect(self._test_connection)
        form.addRow("", self.connection_test_btn)
        return page

    def _build_reminder_step(self) -> QWidget:
        page, form = self._build_step(
            "设置提醒时间", "选填，不设置也不影响日程识别和使用；设置后可获得更合适的本地提醒。"
        )
        self.advance_spin = QSpinBox()
        self.advance_spin.setRange(5, 1440)
        self.advance_spin.setValue(30)
        self.advance_spin.setSuffix(" 分钟")
        self.advance_spin.setToolTip("日程开始前多少分钟提醒")
        form.addRow("提前提醒", self.advance_spin)
        return page

    def _build_wechat_step(self) -> QWidget:
        page, form = self._build_step(
            "设置微信通知", "选填，不填不影响使用；填写后可将提醒推送到微信。"
        )
        self.wechat_service_combo = QComboBox()
        self.wechat_service_combo.addItems(
            [
                "none - 不使用微信推送",
                "serverchan - Server酱 (推荐)",
                "pushplus - PushPlus",
                "wxpusher - WxPusher",
            ]
        )
        self.wechat_service_combo.currentTextChanged.connect(self._on_wechat_service_changed)
        form.addRow("推送服务", self.wechat_service_combo)

        self.wechat_guide_label = QLabel(
            '<a href="https://sct.ftqq.com/">注册 Server酱</a>　'
            '<a href="https://www.pushplus.plus/">注册 PushPlus</a>'
        )
        self.wechat_guide_label.setOpenExternalLinks(True)
        form.addRow("服务入口", self.wechat_guide_label)

        self.wechat_token_input = QLineEdit()
        self.wechat_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.wechat_token_input.setPlaceholderText("选填：输入 SendKey / Token")
        form.addRow("Token（选填）", self.wechat_token_input)

        test_btn = QPushButton("测试推送")
        test_btn.setObjectName("SecondaryButton")
        test_btn.clicked.connect(self._test_wechat)
        form.addRow("", test_btn)
        return page

    def _build_email_step(self) -> QWidget:
        page, form = self._build_step(
            "设置邮件通知", "选填，不填不影响使用；填写后可接收邮件提醒。QQ 邮箱请填写授权码，而不是登录密码。注意：邮箱格式请设置为qq号@qq.com。"
        )
        self.email_form = form
        self.email_service_combo = QComboBox()
        self.email_service_combo.addItems(
            [
                "none - 不使用邮件推送",
                "qq - QQ邮箱 (推荐)",
                "163 - 163邮箱",
                "gmail - Gmail",
                "custom - 自定义 SMTP",
            ]
        )
        self.email_service_combo.currentTextChanged.connect(self._on_email_service_changed)
        form.addRow("邮箱类型", self.email_service_combo)

        self.email_address_input = QLineEdit()
        self.email_address_input.setPlaceholderText("your_email@example.com")
        self.email_address_input.setToolTip("QQ 邮箱格式：QQ号@qq.com，例如 123456@qq.com")
        form.addRow("邮箱地址（选填）", self.email_address_input)

        self.email_password_input = QLineEdit()
        self.email_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.email_password_input.setPlaceholderText("选填：填写邮箱授权码")
        form.addRow("授权码（选填）", self.email_password_input)

        self.email_smtp_host_input = QLineEdit()
        self.email_smtp_host_input.setPlaceholderText("smtp.example.com")
        form.addRow("SMTP 服务器（选填）", self.email_smtp_host_input)

        self.email_smtp_port_input = QSpinBox()
        self.email_smtp_port_input.setRange(1, 65535)
        self.email_smtp_port_input.setValue(465)
        form.addRow("SMTP 端口（选填）", self.email_smtp_port_input)

        test_btn = QPushButton("测试发送")
        test_btn.setObjectName("SecondaryButton")
        test_btn.clicked.connect(self._test_email)
        form.addRow("", test_btn)
        return page

    def _show_step(self, index: int):
        self._current_step = max(0, min(index, len(self.STEP_TITLES) - 1))
        self.step_stack.setCurrentIndex(self._current_step)
        self.step_position.setText(
            f"第 {self._current_step + 1} / {len(self.STEP_TITLES)} 步　"
            f"{self.STEP_DESCRIPTIONS[self._current_step]}"
        )

        for step_index, indicator in enumerate(self._step_indicators):
            state = "complete" if step_index < self._current_step else "active" if step_index == self._current_step else "pending"
            prefix = "已" if state == "complete" else str(step_index + 1)
            indicator.setText(f"{prefix}  {self.STEP_TITLES[step_index]}")
            indicator.setProperty("stepState", state)
            indicator.style().unpolish(indicator)
            indicator.style().polish(indicator)

        self.back_btn.setVisible(self._current_step > 0)
        is_last = self._current_step == len(self.STEP_TITLES) - 1
        self.next_btn.setText("保存设置" if is_last else "下一步")
        self.next_btn.setIcon(
            self.style().standardIcon(QStyle.SP_DialogSaveButton if is_last else QStyle.SP_ArrowForward)
        )
        self.next_hint.setText("完成并保存" if is_last else f"下一项：{self.STEP_TITLES[self._current_step + 1]}")

    def _next_step(self):
        if not self._validate_step(self._current_step):
            return
        if self._current_step == len(self.STEP_TITLES) - 1:
            self._save_config()
            return
        self._show_step(self._current_step + 1)

    def _previous_step(self):
        self._show_step(self._current_step - 1)

    def _validate_step(self, step: int) -> bool:
        if step == 0:
            if not self.api_key_input.text().strip():
                return self._show_required("请先填写 API Key，再进入下一步。", self.api_key_input)
        return True

    def _show_required(self, message: str, field: QWidget) -> bool:
        QMessageBox.warning(self, "还差一项", message)
        field.setFocus()
        return False

    def _on_wechat_service_changed(self, text: str):
        enabled = not text.startswith("none")
        self.wechat_token_input.setEnabled(enabled)
        self.wechat_guide_label.setEnabled(enabled)

    def _on_email_service_changed(self, text: str):
        enabled = not text.startswith("none")
        self.email_address_input.setEnabled(enabled)
        self.email_password_input.setEnabled(enabled)
        is_qq = text.startswith("qq")
        self.email_address_input.setPlaceholderText(
            "例如：123456@qq.com" if is_qq else "your_email@example.com"
        )
        is_custom = text.startswith("custom")
        for field in (self.email_smtp_host_input, self.email_smtp_port_input):
            field.setVisible(is_custom)
            label = self.email_form.labelForField(field)
            if label:
                label.setVisible(is_custom)

    def _on_theme_changed(self):
        theme = self.theme_combo.currentData()
        if theme not in {'light', 'dark'}:
            return
        get_db()
        Config.replace(key='theme', value=theme).execute()
        self.theme_changed.emit(theme)

    def _load_config(self):
        configs = {
            "model_provider": "zhipu",
            "model_api_key": "",
            "model_api_base": "",
            "model_name": "",
            "wechat_service": "none",
            "wechat_token": "",
            "email_service": "none",
            "email_address": "",
            "email_password": "",
            "email_smtp_host": "",
            "email_smtp_port": "",
            "reminder_advance": "30",
            "theme": "light",
        }
        get_db()
        for row in Config.select():
            if row.key in configs:
                value = row.value
                if row.key in ("model_api_key", "wechat_token", "email_address", "email_password"):
                    value = decrypt(value)
                configs[row.key] = value

        self.provider_combo.setCurrentIndex(0)
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentIndex(
            max(0, self.theme_combo.findData(configs["theme"]))
        )
        self.theme_combo.blockSignals(False)
        self.api_key_input.setText(configs["model_api_key"])
        self.api_base_input.setText(configs["model_api_base"])
        self.model_name_input.setText(configs["model_name"])

        wechat_map = {"none": 0, "serverchan": 1, "pushplus": 2, "wxpusher": 3}
        self.wechat_service_combo.setCurrentIndex(wechat_map.get(configs["wechat_service"], 0))
        self.wechat_token_input.setText(configs["wechat_token"])

        email_map = {"none": 0, "qq": 1, "163": 2, "gmail": 3, "custom": 4}
        self.email_service_combo.setCurrentIndex(email_map.get(configs["email_service"], 0))
        self.email_address_input.setText(configs["email_address"])
        self.email_password_input.setText(configs["email_password"])
        self.email_smtp_host_input.setText(configs["email_smtp_host"])
        if configs["email_smtp_port"]:
            self.email_smtp_port_input.setValue(int(configs["email_smtp_port"]))
        self.advance_spin.setValue(int(configs["reminder_advance"]))

        self._on_wechat_service_changed(self.wechat_service_combo.currentText())
        self._on_email_service_changed(self.email_service_combo.currentText())

    def _config_data(self) -> dict:
        return {
            "model_provider": self.provider_combo.currentText().split(" - ")[0],
            "model_api_key": encrypt(self.api_key_input.text().strip()),
            "model_api_base": self.api_base_input.text().strip(),
            "model_name": self.model_name_input.text().strip(),
            "wechat_service": self.wechat_service_combo.currentText().split(" - ")[0],
            "wechat_token": encrypt(self.wechat_token_input.text().strip()),
            "email_service": self.email_service_combo.currentText().split(" - ")[0],
            "email_address": encrypt(self.email_address_input.text().strip()),
            "email_password": encrypt(self.email_password_input.text().strip()),
            "email_smtp_host": self.email_smtp_host_input.text().strip(),
            "email_smtp_port": str(self.email_smtp_port_input.value()),
            "reminder_advance": str(self.advance_spin.value()),
            "theme": self.theme_combo.currentData(),
        }

    def _persist_config(self, mark_complete: bool = False):
        get_db()
        data = self._config_data()
        if mark_complete:
            data["setup_completed"] = "1"
        for key, value in data.items():
            Config.replace(key=key, value=value).execute()

    def _save_config(self):
        self._persist_config(mark_complete=True)
        QMessageBox.information(self, "保存成功", "全部设置已保存。")
        self.setup_completed.emit()

    def _test_connection(self):
        if not self._validate_step(0):
            return
        self._persist_config()
        self.connection_test_btn.setEnabled(False)
        self.connection_test_btn.setText('正在连接...')
        self._connection_test_thread = ConnectionTestThread(self)
        self._connection_test_thread.completed.connect(self._on_connection_test_finished)
        self._connection_test_thread.finished.connect(self._connection_test_thread.deleteLater)
        self._connection_test_thread.start()

    def _on_connection_test_finished(self, ok: bool, message: str):
        self.connection_test_btn.setEnabled(True)
        self.connection_test_btn.setText('测试连接')
        self._connection_test_thread = None
        dialog = QMessageBox.information if ok else QMessageBox.warning
        dialog(self, "连接测试", message)

    def _test_wechat(self):
        if not self._validate_step(2):
            return
        self._persist_config()
        from core.api_client import get_push_config

        config = get_push_config()
        service = config.get("wechat_service", "none")
        if service == "serverchan":
            from push.serverchan import send
            ok, message = send(config.get("wechat_token", ""), "测试消息", "微信推送配置成功")
        elif service == "pushplus":
            from push.pushplus import send
            ok, message = send(config.get("wechat_token", ""), "测试消息", "微信推送配置成功")
        elif service == "wxpusher":
            from push.wxpusher import send
            ok, message = send(config.get("wechat_app_token", ""), config.get("wechat_token", ""), "测试消息", "微信推送配置成功")
        else:
            QMessageBox.warning(self, "推送测试", "请先选择推送服务")
            return
        dialog = QMessageBox.information if ok else QMessageBox.warning
        dialog(self, "推送测试", message)

    def _test_email(self):
        if not self._validate_step(3):
            return
        if self.email_service_combo.currentText().startswith("qq"):
            address = self.email_address_input.text().strip()
            if not address or not self._is_qq_email_address(address):
                self._show_required(
                    "QQ 邮箱请填写为 QQ号@qq.com，例如 123456@qq.com。",
                    self.email_address_input,
                )
                return
        self._persist_config()
        from core.api_client import get_push_config
        from push.email_sender import build_schedule_email, send

        config = get_push_config()
        service = config.get("email_service", "none")
        if service == "none":
            QMessageBox.warning(self, "邮件测试", "请先选择邮箱类型")
            return
        html = build_schedule_email("测试邮件", "2026-07-23", "", "邮件配置成功", "立即")
        ok, message = send(
            service=service,
            email_address=config.get("email_address", ""),
            email_password=config.get("email_password", ""),
            to_address=config.get("email_address", ""),
            subject="日程助手邮件测试",
            html_content=html,
            custom_host=config.get("email_smtp_host", ""),
            custom_port=int(config.get("email_smtp_port", "0")),
        )
        dialog = QMessageBox.information if ok else QMessageBox.warning
        dialog(self, "邮件测试", message)

    @staticmethod
    def _is_qq_email_address(address: str) -> bool:
        local, separator, domain = address.partition("@")
        return bool(local) and local.isdigit() and separator == "@" and domain.lower() == "qq.com"
