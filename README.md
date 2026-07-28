# 📅 智能日程提醒助手

> 输入文字 / 上传图片 / 粘贴截图 → AI 提取日程 → 自动提醒

## ✨ 功能

- **📝 文字输入**：直接输入日程文字，AI 自动提取
- **🖼️ 图片识别**：拖入或粘贴截图，调用视觉大模型识别
- **🤖 AI 模型**：智谱 GLM-4.6V-Flash
- **🧭 LangGraph 工作流**：统一编排文字/图片路由、结构化校验与日程归一化
- **🕐 本地日期基准**：将系统日期、星期和时区传给模型，并用同一日期解析相对时间
- **🧩 分步设置向导**：按模型、提醒和通知逐项配置，提供清晰的完成进度
- **🚦 首次使用引导**：未完成模型配置时先进入设置，保存后再开放日程识别
- **🔔 三通道提醒**：Windows Toast + 微信推送 + 邮件提醒
- **🎨 现代 UI**：Win11 Fluent Design 风格，深色模式支持

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 获取 API Key

推荐 [智谱 AI](https://open.bigmodel.cn/) — 新用户有免费额度，中文识别效果好。

### 3. 启动应用

```bash
python main.py
```

### 4. 配置

在设置页面填入 API Key，可选配微信推送和邮件提醒。

## 📦 打包为 EXE

```bash
pyinstaller --noconfirm --clean --windowed --onedir --name AI-Memo --add-data "gui/styles.qss;gui" --add-data "gui/dark_styles.qss;gui" main.py
```

## 🧭 制作安装包

将应用图标保存为 `resources/app-icon.png` 后，安装 Inno Setup 6，并运行：

```powershell
winget install JRSoftware.InnoSetup
.\installer\build_release.ps1
```

生成的 `release\AI-Memo-Installer.zip` 内含安装向导。用户解压后运行该向导即可安装应用并创建桌面快捷方式。

## 🗂 项目结构

```
Have you forgotten?/
├── main.py              # 入口
├── gui/                 # 界面层
│   ├── main_window.py
│   ├── home_page.py
│   ├── schedule_list.py
│   ├── reminder_history.py
│   ├── settings_page.py
│   ├── components/      # 可复用组件
│   └── styles.qss       # 样式表
├── core/                # 核心逻辑
│   ├── api_client.py    # 统一 API 调用
│   ├── ocr_engine.py    # 识别引擎
│   ├── workflow.py      # LangGraph 输入处理工作流
│   ├── parser.py        # 日程解析
│   ├── deduplicator.py  # 去重
│   ├── reminder.py      # 提醒服务
│   └── providers/       # 模型适配层
├── push/                # 推送模块
│   ├── serverchan.py
│   ├── pushplus.py
│   ├── wxpusher.py
│   └── email_sender.py
├── db/                  # 数据层
│   ├── database.py
│   └── models.py
├── utils/               # 工具
│   ├── crypto.py
│   ├── date_parser.py
│   └── system_tray.py
├── data/                # 运行时数据（自动创建）
│   ├── app.db
│   └── images/
├── requirements.txt
├── DESIGN.md            # 详细设计文档
└── README.md
```

## 🔑 支持的模型

| 模型 | 提供商 | 视觉 | 价格 |
|------|--------|------|------|
| GLM-4.6V-Flash | 智谱 AI | ✅ | 免费 |

## 📱 推送通道

- **微信**：Server酱 / PushPlus / WxPusher
- **邮件**：QQ邮箱 / 163 / Gmail / 自定义 SMTP

## ⚠️ 注意事项

- QQ邮箱需开启 SMTP 服务并使用**授权码**（非登录密码）
- API Key 使用 AES 加密存储在本地，不会上传到任何服务器
- 所有日程数据保存在本地 `data/app.db`

---

Made with ❤️ by Claude Code
