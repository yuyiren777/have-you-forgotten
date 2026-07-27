# 📋 智能日程提醒助手 — 详细设计方案

---

## 一、产品概述

### 1.1 一句话描述
用户可以输入文字、上传图片或粘贴截图，系统调用国产大模型进行 OCR 识别与日程提取，自动对比当天日期，通过 **Windows 通知 + 微信 + 邮件** 三通道提醒用户。

### 1.2 目标用户
普通大众（非技术群体），操作简单直观，无需编程知识。

### 1.3 核心流程

```
输入 → 视觉模型 → 日程解析 → 存储 → 对比今日 → 到期提醒
  │        │          │         │        │           │
文字    智谱GLM    日期理解    SQLite  每天轮询    Win通知
图片    通义千问   时间归一              │        微信推送
截图    百度文心   重复规则             ▼        邮件提醒
        DeepSeek                  日程列表
```

---

## 二、技术选型

| 层面 | 选择 | 理由 |
|------|------|------|
| **语言** | Python 3.11+ | 生态丰富，开发速度快 |
| **GUI 框架** | PyQt6 + qfluentwidgets | 现代美化 UI 组件库（Fluent Design 风格） |
| **数据库** | SQLite | 轻量、零配置、单文件 |
| **定时任务** | APScheduler | 成熟的 Python 定时调度库 |
| **系统通知** | win11toast | Windows 10/11 原生 Toast 通知 |
| **微信推送** | Server酱 (ServerChan) + PushPlus | 国内最主流的微信推送通道 |
| **邮件推送** | smtplib (QQ邮箱/Gmail/163) | Python 标准库，无需额外依赖 |
| **打包分发** | PyInstaller | 打包为单个 .exe 文件 |

---

## 三、国产大模型支持（重点）

### 3.1 模型列表

| 模型 | 提供商 | 优势 | 视觉能力 | API 兼容性 |
|------|--------|------|----------|------------|
| **GLM-4V** | 智谱 AI | 中文识别最强、价格低 | ✅ 多模态 | OpenAI 兼容 |
| **Qwen-VL-Max** | 阿里通义千问 | 文档/表格识别好 | ✅ 多模态 | OpenAI 兼容 |
| **DeepSeek-V3** | 深度求索 | 推理能力强、极便宜 | ❌ 纯文本 | OpenAI 兼容 |
| **ERNIE-4.0** | 百度文心一言 | 综合能力强 | ✅ 多模态 | 独立格式 |
| **Step-1V** | 阶跃星辰 | 新锐模型、性价比高 | ✅ 多模态 | OpenAI 兼容 |
| **Hunyuan-Vision** | 腾讯混元 | 腾讯生态、稳定 | ✅ 多模态 | 独立格式 |

### 3.2 推荐组合

```
推荐方案（按预算）：

主力：智谱 GLM-4V（图 → 文字提取 + 日程理解）
  - 性价比最高，中文 OCR 效果最好
  - 约 0.01 元/次

备选：阿里 Qwen-VL-Max
  - 适合表格类日程（课程表、排班表）
  - 约 0.02 元/次

纯文本增强：DeepSeek-V3
  - 当用户直接输入文字时使用
  - 约 0.001 元/次，几乎免费

兜底方案：用户可手动填写任意兼容 OpenAI 格式的 API
```

### 3.3 API 调用流程

```
用户输入 → 有图片？→ 是 → 视觉模型（GLM-4V）
                    → 否 → 纯文本模型（DeepSeek-V3）
         → 日程解析（本地引擎）
         → 存入数据库
```

### 3.4 API Key 管理

- 在设置界面中，用户可选择模型提供商，填入对应 API Key
- 预置各模型默认 API 地址，用户也可手动修改（兼容代理/中转）
- API Key 使用 AES 加密存储到本地配置文件
- 提供"测试连接"按钮，验证 Key 是否有效

---

## 四、微信 + 邮件提醒方案

### 4.1 微信推送

采用国内成熟的**第三方推送中转服务**：

| 服务 | 免费额度 | 方式 | 推荐 |
|------|---------|------|------|
| **Server酱 (ServerChan)** | 每天 5 条 | 关注公众号获取 SendKey | ⭐ 首选 |
| **PushPlus** | 每天 200 条 | 关注公众号获取 Token | ⭐ 备用 |
| **WxPusher** | 不限量 | 扫码关注应用 | 备选 |

### 4.2 邮件推送

采用 Python 内置 `smtplib` 发送，**无需第三方依赖**：

| 邮箱 | SMTP 服务器 | 端口 | 说明 |
|------|------------|------|------|
| **QQ邮箱** | smtp.qq.com | 465 (SSL) | ⭐ 首选，国内用户最多 |
| **163邮箱** | smtp.163.com | 465 (SSL) | 备用 |
| **Gmail** | smtp.gmail.com | 587 (TLS) | 需开启应用专用密码 |
| **自定义** | 用户自填 | 用户自填 | 企业邮箱等 |

配置步骤（以 QQ 邮箱为例）：
1. 登录 QQ 邮箱 → 设置 → 账户 → 开启 SMTP 服务
2. 获取**授权码**（不是邮箱密码）
3. 在应用中填入：邮箱地址 + 授权码

### 4.3 工作流程

日程到期 → 检查提醒配置 → 同时触发微信 + 邮件 + Win通知

示例推送内容：
```
⏰ 日程提醒
📌 明天下午3点开会
📅 2026-07-12 (周日)
📍 3楼会议室
⏳ 还有 1 天
—— 来自"日程助手"
```

### 4.4 示例推送内容

微信推送示例：
```
⏰ 日程提醒
📌 明天下午3点开会
📅 2026-07-12 (周日)
📍 3楼会议室
⏳ 还有 1 天
—— 来自"日程助手"
```

邮件推送示例（HTML 格式）：
```
主题：⏰ 日程提醒 — 明天下午3点开会

📅 时间：2026-07-12 (周日) 15:00
📍 地点：3楼会议室
⏳ 剩余：还有 1 天
📝 备注：请提前准备发言材料

—— 智能日程提醒助手
```

### 4.5 设置界面
- **微信部分**：提供 Server酱 / PushPlus 的注册引导链接，用户填入 SendKey 或 Token 即可
- **邮件部分**：选择邮箱类型（QQ/163/Gmail/自定义），填入邮箱地址和授权码
- 两者均支持"测试推送"按钮，点击后发送一条测试消息验证配置是否正确

---

## 五、UI 设计（现代美化风格）

### 5.1 整体风格
- **设计语言**：Microsoft Fluent Design（Win11 风格）
- **组件库**：qfluentwidgets（PyQt6 的 Fluent UI 组件）
- **配色**：浅色/深色主题可切换，默认跟随系统
- **圆角**：8-12px 圆角卡片
- **动效**：页面切换有平滑过渡

### 5.2 页面结构

```
┌──────────────────────────────────────────────────┐
│  [≡]  智能日程助手                    [⚙] [🌙]  │  ← 导航栏
├─────────────────────┬────────────────────────────┤
│                     │                            │
│   ┌───────────────┐ │  今天                      │
│   │  📝 文字输入  │ │  ┌────────────────────┐   │
│   │               │ │  │ 📌 下午3点开会      │   │
│   │               │ │  │    还有2小时        │   │
│   └───────────────┘ │  └────────────────────┘   │
│                     │                            │
│   ┌───────────────┐ │  明天                      │
│   │  🖼️ 图片拖入  │ │  ┌────────────────────┐   │
│   │               │ │  │ 📌 体检 (空腹)      │   │
│   │  [点击或拖拽] │ │  │    明早8:00         │   │
│   │               │ │  └────────────────────┘   │
│   └───────────────┘ │                            │
│                     │  7月15日 (周三)              │
│   ┌───────────────┐ │  ┌────────────────────┐   │
│   │  [识别日程]   │ │  │ 📌 提交报告         │   │
│   │               │ │  │    3天后            │   │
│   └───────────────┘ │  └────────────────────┘   │
│                     │                            │
│   状态栏：已添加 12 条日程  │  上次识别：10分钟前  │
├─────────────────────┴────────────────────────────┤
│  🔔 下一条提醒：明天 8:00 — 体检 (空腹)           │  ← 底部状态条
└──────────────────────────────────────────────────┘
```

### 5.3 页面路由

```
MainWindow (NavigationInterface)
  ├── 首页 (HomePage)
  │     ├── 输入区（文字 + 图片拖拽）
  │     ├── 今日日程卡片
  │     └── 近期日程时间线
  │
  ├── 所有日程 (ScheduleListPage)
  │     ├── 搜索框 + 筛选器
  │     ├── 日程卡片列表
  │     └── 右键菜单（编辑/删除/完成）
  │
  ├── 提醒记录 (ReminderHistoryPage)
  │     ├── 已提醒列表
  │     └── 已过期列表
  │
  └── 设置 (SettingsPage)
        ├── API 配置区
        ├── 微信推送配置区
        ├── 邮件推送配置区
        └── 提醒规则配置区
```

### 5.4 交互细节

- **拖拽上传**：图片可直接拖入窗口，出现虚线边框高亮
- **粘贴截图**：任意界面截图后 Ctrl+V 直接粘贴
- **批量处理**：一次可上传多张图片，逐张识别
- **识别中动效**：卡片显示 shimmer 加载动画
- **提醒弹窗**：右下角弹出圆角通知卡片，带"知道了"/"10分钟后提醒"
- **系统托盘**：最小化到托盘，后台运行，有新提醒时托盘图标闪烁
- **开机自启**：设置中可开启

---

## 六、数据库设计

```sql
-- 用户配置表
CREATE TABLE config (
    key   TEXT PRIMARY KEY,   -- 配置键
    value TEXT                -- 配置值（加密存储敏感字段）
);

-- 原始输入表
CREATE TABLE inputs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    type       TEXT NOT NULL,       -- text | image
    content    TEXT,                -- 文字内容
    image_path TEXT,                -- 图片本地存储路径
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 提取的日程表（核心）
CREATE TABLE schedules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    input_id    INTEGER,
    title       TEXT NOT NULL,
    description TEXT,
    date        DATE,
    start_time  TIME,
    end_time    TIME,
    location    TEXT,
    notes       TEXT,
    repeat_rule TEXT,
    urgency     INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'pending',
    reminded_at DATETIME,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (input_id) REFERENCES inputs(id)
);

-- 提醒记录表
CREATE TABLE reminder_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER,
    method      TEXT,               -- windows | wechat | email
    status      TEXT,
    message     TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (schedule_id) REFERENCES schedules(id)
);
```

---

## 七、日程解析引擎

### 7.1 大模型 Prompt 设计

发给视觉模型的 System Prompt：
> 你是一个日程提取助手。请仔细查看图片中的所有文字，提取其中包含的日程、会议、约会、截止日期、活动等信息。对于每条日程，请以严格 JSON 数组格式输出。日期理解规则："明天"=明天日期，"下周三"=下一个周三，"每周一"= repeat weekly:1，"每月15号"= repeat monthly:15。如果只提到时间没提到日期，date 填 null。请只返回 JSON 数组，不要包含其他内容。

### 7.2 本地后处理

```
模型返回 JSON → 解析验证 → 日期归一化 → 查重合并 → 入库
                   │              │            │
              JSON Schema    dateparser    与已有日程
              格式校验       日期换算       去重
```

- **日期归一化**：相对日期（"明天""下周"）→ 绝对日期；用 `python-dateutil` 解析中文日期
- **查重合并**：同一天、同一标题、时间相差 < 30 分钟的视为重复，自动合并
- **异常处理**：解析失败的内容保留在 `notes` 字段，标记为 `pending` 待用户手动处理

---

## 八、提醒规则

### 8.1 提醒时间策略

| 场景 | 提醒时机 |
|------|---------|
| 当天有具体时间的日程 | 提前 N 分钟（用户可设，默认 30 分钟） |
| 当天全天事件 | 前一天晚上 20:00 |
| 明天日程 | 前一天晚上 20:00 |
| 3 天后的日程 | 提前 1 天提醒 |
| 1 周后的日程 | 提前 1 天提醒 |
| 紧急日程 (urgency=urgent) | 提前 2 小时 + 提前 1 天，双重提醒 |
| 重复日程 | 每次到期前按规则提醒 |

### 8.2 提醒通道优先级

```
1. Windows Toast 通知（即时，无需网络，电脑端必达）
2. 微信推送（需网络，手机端即时可见）
3. 邮件提醒（需网络，可作为记录留存，重要日程双重保险）
```

- 三条通道同时发送，用户可在设置中单独开启/关闭任意通道
- 微信和邮件作为兜底，确保用户出门在外也能收到
- 邮件适合发送详细日程内容（支持 HTML 格式，包含地点、备注等）

### 8.3 后台调度

- APScheduler 每 60 秒扫描一次数据库
- 检查是否有需要提醒的日程
- 已提醒过的日程不重复提醒（除非是重复事件的新周期）

---

## 九、文件结构

```
d:\VS\Have you forgotten?\
├── main.py                  # 应用入口
├── gui/
│   ├── __init__.py
│   ├── main_window.py       # 主窗口 + 导航
│   ├── home_page.py         # 首页（输入+今日日程）
│   ├── schedule_list.py     # 所有日程列表页
│   ├── reminder_history.py  # 提醒记录页
│   ├── settings_page.py     # 设置页
│   ├── components/
│   │   ├── __init__.py
│   │   ├── input_card.py        # 输入卡片组件
│   │   ├── image_drop_zone.py   # 图片拖拽区组件
│   │   ├── schedule_card.py     # 日程卡片组件
│   │   ├── shimmer_loader.py    # 骨架屏加载动画
│   │   └── toast_notification.py# 弹出通知组件
│   └── resources/
│       ├── icon.ico
│       └── styles.qss       # QSS 样式表
├── core/
│   ├── __init__.py
│   ├── api_client.py        # 多模型 API 统一调用
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── zhipu.py         # 智谱 GLM-4V
│   │   ├── qwen.py          # 通义千问
│   │   ├── deepseek.py      # DeepSeek
│   │   ├── ernie.py         # 百度文心
│   │   └── custom.py        # 自定义 OpenAI 兼容接口
│   ├── ocr_engine.py        # 视觉识别调度
│   ├── parser.py            # 日程解析引擎
│   ├── deduplicator.py      # 日程查重合并
│   └── reminder.py          # 提醒调度服务
├── push/
│   ├── __init__.py
│   ├── serverchan.py        # Server酱推送
│   ├── pushplus.py          # PushPlus 推送
│   ├── wxpusher.py          # WxPusher 推送
│   └── email_sender.py      # 邮件推送（smtplib）
├── db/
│   ├── __init__.py
│   ├── database.py          # 数据库连接管理
│   └── models.py            # ORM 模型 (peewee)
├── utils/
│   ├── __init__.py
│   ├── crypto.py            # AES 加密/解密
│   ├── date_parser.py       # 中文日期解析
│   └── system_tray.py       # 系统托盘管理
├── requirements.txt
├── DESIGN.md                # 本文档
└── README.md                # 用户使用说明
```

---

## 十、开发计划

| 阶段 | 内容 | 预计文件数 |
|------|------|-----------|
| **1. 项目初始化** | 目录结构、requirements.txt、数据库初始化 | 5 |
| **2. GUI 骨架** | 主窗口、导航、4 个页面框架、Fluent UI 主题 | 8 |
| **3. 输入模块** | 文字输入、图片拖拽、截图粘贴、base64 处理 | 4 |
| **4. API 模块** | 5 个模型 provider + 统一 client + Key 加密存储 | 8 |
| **5. 识别引擎** | OCR 调度、Prompt 模板、响应解析 | 3 |
| **6. 日程解析** | 中文日期归一化、查重合并、入库 | 4 |
| **7. 提醒服务** | APScheduler 调度、Windows Toast、系统托盘 | 3 |
| **8. 推送服务** | 微信推送(Server酱/PushPlus) + 邮件推送(smtplib) + Win通知 | 4 |
| **9. 设置页面** | API 配置表单、微信/邮件推送配置、提醒规则 | 3 |
| **10. 日程管理** | 列表/搜索/筛选/右键菜单/编辑删除 | 3 |
| **11. 打包测试** | PyInstaller 配置、图标、测试 | 2 |

---

## 十一、依赖清单 (requirements.txt)

```
# GUI
PyQt6>=6.6
PyQt6-Fluent-Widgets>=1.5
qfluentwidgets>=1.5

# 数据库
peewee>=3.17

# HTTP 请求
httpx>=0.27
openai>=1.30

# 定时任务
APScheduler>=3.10

# 日期处理
python-dateutil>=2.9
dateparser>=1.2

# 系统通知
win11toast>=0.4

# 图像处理
Pillow>=10.3

# 加密
pycryptodome>=3.20

# 打包
pyinstaller>=6.5
```

---

> 📅 本文档版本：v1.2 | 更新日期：2026-07-11
>
> ⏭️ 下一步：确认方案后开始编码实现
