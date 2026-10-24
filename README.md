# 工作日提醒器 · WorkdayReminder

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-6.5%2B-41CD52?logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

> 屏幕右上角的一小块提示，告诉你**现在到底能不能联系客户**。
> 它把「工作日 / 周末 / 法定节假日 / 调休上班 / 午休 / 下班」这些判断全部算好，你扫一眼就行，不用再翻日历。

<img src="docs/images/floating-panel.png" width="300" alt="悬浮窗的三种状态">

## 它解决什么问题

做大客户、外贸、政务、教育或任何"对面按国家节假日休息"的业务时，最容易犯的错就两种：

- **假期打扰**——客户正在过年，你发过去一条"方案确认一下"；
- **调休漏掉**——日历上明明写着上班，你以为是周末，结果客户在等你电话。

程序按**国务院办公厅的放假安排**（含调休上班日）计算每天的性质，再叠加你自己的上下班、午休时间，用一个半透明悬浮小窗给出结论。节前最后一个工作日下午提示你收尾，假期结束第一天早上提示你恢复跟进。

## 三种状态

| 指示灯 | 主文字 | 什么情况 |
| :---: | --- | --- |
| 🟢 绿 | **可以联系客户** | 工作日、在客户工作时间内、不在午休；今天不是法定节假日 |
| 🟡 黄 | **还没上班 / 午休中 / 已下班** | 今天是工作日，但当前不在可联系的时间段 |
| 🔴 红 | **别联系客户** | 今天休息：周末、法定节假日，或你自己标注的休假 |

悬浮窗第二行给出原因和"下次可联系的时间"，第三行给出倒计时或提醒（例如 `明天起国庆节 7 天，今天收尾`）。托盘图标的颜色同步变化，图标上的字分别是 **班 / 等 / 休**。

## 功能特性

- **法定节假日 + 调休**：内置 2025、2026 年国务院放假安排；联网时自动从 [holiday-cn](https://github.com/NateScarlet/holiday-cn) 拉取当年和次年的数据，次年安排公布后无需升级程序。
- **精确到时间**：区分"还没上班 / 午休中 / 已下班"，午休时段可以单独关掉。
- **节前收尾提醒**：放假前最后一个工作日的指定时间，提醒你把需要客户确认的事处理完；可选让普通周五也提醒。
- **节后恢复提醒**：假期结束第一个工作日早上提醒你恢复跟进；调休上班日提醒你"别当成周末"。
- **自定义日期**：自己请的年假、客户公司的特殊安排、项目上线的周末加班，按 `日期 休/班 说明` 写一行即可，覆盖内置判断。
- **放假日历**：设置里有一整年的日历视图和假期清单，节假日深红、调休上班浅橙、自定义休假紫色。
- **开机自启**：Windows 写注册表、macOS 写 LaunchAgent、Linux 写 autostart；程序被移动位置后会自动修正启动项。
- **单实例**：重复启动不会出现第二个悬浮窗，只会打开已运行实例的设置窗口。
- **轻量**：只有一个 Python 文件（约 1100 行）+ PySide6，无后台服务、无数据库、无账号。

## 快速开始

### 方式一：直接下载可执行文件（Windows，免安装）

1. 直接下载 [WorkdayReminder.exe](https://github.com/Delusionx1/WorkdayReminder/releases/latest/download/WorkdayReminder.exe)（约 43 MB，Windows 免安装），或到 [Releases](https://github.com/Delusionx1/WorkdayReminder/releases) 查看全部版本；
2. 把它放到一个**固定且不会被清理**的目录（例如 `D:\Tools\WorkdayReminder\`），不要放在"下载"文件夹里；
3. 双击运行，屏幕右上角出现悬浮窗，任务栏托盘出现一个圆形的 **班 / 等 / 休** 图标；
4. 双击悬浮窗 → 设置里调整你的上下班时间，需要的话勾上 **开机自动启动**。

> Windows 首次运行可能出现 SmartScreen 蓝色提示，点"更多信息 → 仍要运行"即可（未做代码签名，属正常现象）。

### 方式二：从源码运行

```powershell
git clone https://github.com/Delusionx1/WorkdayReminder.git
cd WorkdayReminder
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

macOS / Linux 把激活命令换成 `source .venv/bin/activate`，其余相同。

### 方式三：自己编译成 exe

仓库提供两种打包方式，都是双击脚本即可，零基础步骤见[部署与编译指南](docs/deployment.md)：

| 方式 | 一键脚本 | 特点 |
| --- | --- | --- |
| **PyInstaller** | `build_windows.bat` | 1–3 分钟出结果，单文件约 43 MB，启动稍慢、偶被杀软误报 |
| **Nuitka** | `build_windows_nuitka.bat` | 首次 5–20 分钟（自动下载 MinGW），启动更快、误报更少 |

## 文档

| 文档 | 内容 |
| --- | --- |
| [用户使用文档](docs/user-guide.md) | 悬浮窗怎么读、每个设置项什么意思、自定义日期怎么写、提醒什么时候弹、常见问题 |
| [部署与编译指南](docs/deployment.md) | **零基础**装 Python、跑源码、PyInstaller 与 Nuitka 两种打包方式、开机自启原理、批量与离线部署、CI 自动构建、故障排查 |

## 数据来源

| 数据 | 来源 | 说明 |
| --- | --- | --- |
| 法定节假日、调休上班日 | 国务院办公厅历年放假安排通知 | 2025、2026 年已内置在程序中 |
| 后续年份 | [NateScarlet/holiday-cn](https://github.com/NateScarlet/holiday-cn) | 启动后自动请求当年与次年，成功后缓存到本地 |

请求依次尝试 `cdn.jsdelivr.net` → `fastly.jsdelivr.net` → `raw.githubusercontent.com`，单次超时 8 秒；全部失败时继续使用内置数据与本地缓存，功能不受影响。**程序不收集任何用户数据**，除上述 JSON 之外没有其他网络请求。

## 本机文件

程序只在你自己的用户目录下写两个东西，删掉即可完全重置：

```text
~/.workday_reminder/            # Windows: %USERPROFILE%\.workday_reminder
├── settings.ini                # 所有设置（工作时间、午休、自定义日期、窗口位置…）
└── holiday_cn_2026.json        # 联网获取到的年度放假安排缓存
```

## 系统要求

| 项目 | 要求 |
| --- | --- |
| 操作系统 | Windows 10 / 11（主要验证环境）、macOS 12+、常见桌面 Linux |
| 运行时 | 免安装版无需 Python；源码运行需 Python 3.9+ |
| 依赖 | PySide6 ≥ 6.5 |
| 编译 | PyInstaller ≥ 6.0，或 Nuitka（首次编译自动下载 MinGW，无需手动装 C 编译器） |
| 磁盘 | 源码不足 1 MB；单文件 exe 约 43 MB |

## 项目结构

```text
WorkdayReminder/
├── main.py                    # 全部程序逻辑（界面、日历计算、提醒、自启、单实例）
├── requirements.txt           # 运行依赖
├── WorkdayReminder.spec       # PyInstaller 打包配置
├── build_windows.bat          # 一键打包：PyInstaller（双击即可）
├── build_windows_nuitka.bat   # 一键打包：Nuitka（双击即可）
├── docs/
│   ├── user-guide.md          # 用户使用文档
│   ├── deployment.md          # 部署与编译指南（零基础）
│   ├── promo.md               # 分享用的宣传文案
│   └── images/                # 文档截图
└── .github/workflows/         # GitHub Actions 自动构建（PyInstaller / Nuitka）
```

## 常见问题（速查）

| 现象 | 处理 |
| --- | --- |
| 悬浮窗不见了 | 单击托盘图标，或右键托盘图标 → 显示悬浮窗 |
| 公司/客户没按国家标准放假 | 设置 → 自定义日期，按 `2026-11-11 休 年假` 写一行 |
| 明年安排没加载 | 次年安排通常 11 月前后公布；联网后自动获取，也可手动点"更新节假日数据" |
| 电脑在国外时时间不对 | 程序固定按**北京时间（UTC+8）**判断，这是有意设计 |
| 开机没有自动启动 | 确认设置里"开机自动启动"已勾选；exe 移动过位置的话，手动运行一次即可自动修正 |

更多问题见[用户使用文档的常见问题一节](docs/user-guide.md#10-常见问题)。

## 许可证

[MIT](LICENSE)。节假日数据来自 [holiday-cn](https://github.com/NateScarlet/holiday-cn)（MIT），放假安排以国务院办公厅公告为准。
