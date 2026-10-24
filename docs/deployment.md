# 工作日提醒器 · 部署文档

本文面向**部署、打包、分发**这个程序的人：从源码跑起来、打包成 Windows exe / macOS .app、配置开机自启、批量部署到同事电脑、离线内网环境、CI 自动构建，以及出问题怎么排查。

日常使用说明见[用户使用文档](user-guide.md)。

---

## 目录

1. [环境要求](#1-环境要求)
2. [获取代码](#2-获取代码)
3. [从源码运行](#3-从源码运行)
4. [打包 Windows 单文件 exe](#4-打包-windows-单文件-exe)
5. [打包 macOS / Linux](#5-打包-macos--linux)
6. [产物说明与验证](#6-产物说明与验证)
7. [开机自启的实现](#7-开机自启的实现)
8. [配置键参考](#8-配置键参考)
9. [预配置与批量部署](#9-预配置与批量部署)
10. [离线与内网部署](#10-离线与内网部署)
11. [用 GitHub Actions 自动构建](#11-用-github-actions-自动构建)
12. [故障排查](#12-故障排查)
13. [升级与回滚](#13-升级与回滚)

---

## 1. 环境要求

| 项目 | 要求 | 说明 |
| --- | --- | --- |
| 操作系统 | Windows 10 / 11 | 主要验证环境，打包与自启逻辑都在 Windows 上完整跑通 |
| | macOS 12+、Linux（X11 或支持托盘协议的 Wayland） | 代码已适配三平台的自启，但托盘行为取决于桌面环境 |
| Python | 3.9 – 3.13 | 推荐 3.11 / 3.12；代码用了 `from __future__ import annotations`，低版本也能跑 |
| PySide6 | ≥ 6.5 | `requirements.txt` 里已限定 `< 7` |
| PyInstaller | ≥ 6.0 | 仅打包时需要 |
| 磁盘 | 源码 < 1 MB；单文件 exe ≈ 43 MB | 单文件模式运行时还要把 Qt 等依赖解压到临时目录，占用一百多 MB |

> ⚠️ 不建议在 **Anaconda base 环境**里直接 `pip install PySide6` 后打包：conda 的 Qt 与 pip 的 PySide6 容易互相抢 DLL，而且 base 环境里常存在 `pathlib` 这类废弃 backport 包，会让 PyInstaller 直接报错退出。用独立虚拟环境最省事。

## 2. 获取代码

```powershell
git clone https://github.com/Delusionx1/WorkdayReminder.git
cd WorkdayReminder
```

只想要最新代码不要历史，也可以直接下载 ZIP 解压。

## 3. 从源码运行

### 3.1 创建虚拟环境

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

如果 PowerShell 提示禁止运行脚本，先执行一次：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 3.2 启动

```powershell
python main.py            # 带控制台，方便看报错
pythonw main.py           # 不带控制台窗口（Windows）
```

macOS / Linux 直接 `python main.py &` 放后台，或写成 shell 脚本。

启动成功的标志：右上角出现悬浮窗、托盘出现圆形图标、用户目录下生成 `~/.workday_reminder/settings.ini`。若在无桌面环境（SSH、纯命令行）中运行，会因为找不到显示器而报 `qt.qpa.plugin` 类错误，这是正常的。

## 4. 打包 Windows 单文件 exe

### 4.1 一条命令

```powershell
pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name WorkdayReminder main.py
```

产物在 `dist\WorkdayReminder.exe`。仓库里还提供了两个等价入口：

- **`build_windows.bat`**：双击即可执行上面这条命令并暂停显示结果，适合给不熟悉命令行的同事；
- **`WorkdayReminder.spec`**：`pyinstaller WorkdayReminder.spec`，适合需要在打包配置里长期加参数（图标、隐藏导入、排除模块）的场景。

### 4.2 参数说明

| 参数 | 作用 |
| --- | --- |
| `--onefile` | 打成单个 exe。分发方便，但每次启动都要解压到临时目录，冷启动 1–3 秒 |
| `--windowed`（同 `--noconsole`） | 不弹出黑色命令行窗口。**调试期建议先不加**，这样报错能直接看到 |
| `--name WorkdayReminder` | exe 文件名。开机自启的注册表值名固定是 `WorkdayReminder`，与文件名无关，改文件名不影响自启 |
| `--clean` | 清掉旧的构建缓存，避免改了代码却打包出旧结果 |
| `--noconfirm` | 覆盖 `dist` 时不交互确认，方便脚本化 |
| `--icon app.ico` | 可选，替换默认图标（需 `.ico` 格式） |
| `--add-data` | 本程序**不需要**：节假日数据内置在代码里，其余数据运行时下载 |

### 4.3 想更快启动？用目录模式

单文件模式每次启动都要解压，对老机器不友好。改成目录模式：

```powershell
python -m PyInstaller --noconfirm --clean --onedir --windowed --name WorkdayReminder main.py
```

产物是 `dist\WorkdayReminder\WorkdayReminder.exe`（整个文件夹一起分发）。两种模式都支持开机自启和单实例，程序内部用 `sys.frozen` 判断自己是不是被打包过。

### 4.4 代码签名（可选）

未签名的 exe 会触发 SmartScreen 提示。有企业证书时用 `signtool` 签：

```powershell
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a dist\WorkdayReminder.exe
```

没有证书就接受提示，或在文档里告知用户"更多信息 → 仍要运行"。

## 5. 打包 macOS / Linux

### 5.1 macOS

```bash
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name WorkdayReminder --osx-bundle-identifier com.workday.reminder main.py
```

产物为 `dist/WorkdayReminder.app`。

- 未签名的 app 在别人机器上会被 Gatekeeper 拦住，可让对方执行 `xattr -dr com.apple.quarantine /Applications/WorkdayReminder.app`，或自己用开发者证书签名并公证；
- 开机自启写的是 `~/Library/LaunchAgents/com.workday.reminder.plist`，**只在用户登录后生效**；
- 打包成 .app 后，自启命令记录的是 app 内的可执行文件路径，把 app 移动到 `/Applications` 后需要**手动运行一次**，让程序自动刷新启动项路径。

### 5.2 Linux

```bash
sudo apt install -y python3-venv libxcb-cursor0 libxkbcommon-x11-0   # Debian/Ubuntu 常见缺库
pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name WorkdayReminder main.py
```

- 开机自启写 `~/.config/autostart/workday-reminder.desktop`；
- Wayland 下托盘图标需要桌面支持 StatusNotifierItem（KDE、GNOME + 扩展）；不支持的桌面会退化为"只有悬浮窗 + 普通弹窗通知"；
- Qt 6 的 xcb 插件依赖 `libxcb-cursor0`，缺了会报 `Could not load the Qt platform plugin "xcb"`。

## 6. 产物说明与验证

打包完成后的自检清单：

1. 双击 exe，右上角出现悬浮窗、托盘出现图标；
2. 双击悬浮窗能打开设置，改时间保存后悬浮窗立即变化；
3. 右键托盘菜单里的「退出」能真正退出进程（任务管理器里不残留）；
4. 首次运行后 `%USERPROFILE%\.workday_reminder\settings.ini` 已生成；
5. 再次双击 exe：不出现第二个悬浮窗，而是弹出已有实例的设置窗口（单实例生效）；
6. 勾选「开机自动启动」后，注册表出现对应值（见下一节），重启验证一次。

**调试打包产物**：`--windowed` 模式下崩溃是"静默"的（没有控制台输出）。排查时临时打成控制台版本：

```powershell
python -m PyInstaller --noconfirm --clean --onefile --console --name WorkdayReminder_debug main.py
```

然后在 PowerShell 里运行 `.\dist\WorkdayReminder_debug.exe`，异常会打印在控制台。

## 7. 开机自启的实现

「常规」页勾选「开机自动启动」后，程序会按平台写入启动项。命令内容取决于运行方式：

| 运行方式 | 写入的命令 |
| --- | --- |
| 打包后的 exe | 直接写 exe 的绝对路径 |
| 源码运行（Windows） | `pythonw.exe` + `main.py` 的绝对路径（优先用 `pythonw` 避免黑框） |
| 源码运行（macOS / Linux） | 当前 Python 解释器 + `main.py` 的绝对路径 |

各平台写入位置：

| 平台 | 位置 | 备注 |
| --- | --- | --- |
| Windows | `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`，值名 `WorkdayReminder` | 当前用户级，**不需要管理员权限**；命令带空格的路径会自动加引号 |
| macOS | `~/Library/LaunchAgents/com.workday.reminder.plist` | `RunAtLoad = true`；写入后下次登录生效，立即生效用 `launchctl load -w` |
| Linux | `~/.config/autostart/workday-reminder.desktop` | 带 `X-GNOME-Autostart-enabled=true` |

查看 / 手动管理（Windows）：

```powershell
# 查看
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" | Select-Object WorkdayReminder

# 手动添加（指向固定目录）
Set-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name WorkdayReminder `
  -Value '"D:\Tools\WorkdayReminder\WorkdayReminder.exe"'

# 删除
Remove-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name WorkdayReminder
```

两个容易踩的点：

- **移动 exe 后自启失效**：程序每次启动都会检查"自启是否开启"，开启状态下会按当前路径重写一遍启动项，所以移动后**手动运行一次**即可自愈；
- **安全软件禁用启动项**：部分安全软件会把注册表启动项标记为"禁用"，需要在它的启动项管理里手动恢复。企业环境若用组策略统一清理 Run 键，自启会被反复删掉，这时改用"启动"文件夹快捷方式或登录脚本。

## 8. 配置键参考

配置文件：`~/.workday_reminder/settings.ini`（Windows：`%USERPROFILE%\.workday_reminder\settings.ini`），标准 INI，全部在 `[General]` 段。**修改前先退出程序**，因为程序退出时也会回写。

| 键 | 类型 | 默认值 | 含义 |
| --- | --- | --- | --- |
| `work_start` | `HH:MM` | `09:00` | 客户上班时间；早间提醒也以此为触发点 |
| `work_end` | `HH:MM` | `18:00` | 客户下班时间；到点显示"已下班" |
| `lunch_enabled` | `true/false` | `true` | 是否启用午休判断 |
| `lunch_start` | `HH:MM` | `12:00` | 午休开始 |
| `lunch_end` | `HH:MM` | `13:30` | 午休结束 |
| `eve_time` | `HH:MM` | `16:00` | 节前收尾提醒的时刻 |
| `remind_weekend_eve` | `true/false` | `false` | 普通周五是否也做"节前收尾"提醒 |
| `custom_days` | 多行文本 | 空 | 自定义日期，格式见[用户文档](user-guide.md#52-自定义日期)；换行会被 QSettings 转义 |
| `opacity` | 30–100 | `85` | 悬浮窗不透明度百分比 |
| `pos` | `"x,y"` | 空 | 悬浮窗坐标；空表示使用右上角默认位置 |
| `locked` | `true/false` | `false` | 是否锁定悬浮窗位置 |
| `welcomed` | `true/false` | `false` | 是否已展示过首次启动的欢迎通知，置 `true` 可跳过 |

示例（企业统一预置，把客户作息定死为 09:30–18:30、午休 12:00–13:00、节前 15:30）：

```ini
[General]
work_start=09:30
work_end=18:30
lunch_enabled=true
lunch_start=12:00
lunch_end=13:00
eve_time=15:30
remind_weekend_eve=false
custom_days=
opacity=90
pos=
locked=false
welcomed=true
```

## 9. 预配置与批量部署

给一个部门（10–100 台 Windows）铺开时，按下面做最省事：

**1）准备一个固定目录**

```text
D:\Tools\WorkdayReminder\
└── WorkdayReminder.exe        # 打包产物
```

**2）准备预置配置**

在自己机器上运行一次、配好参数，然后把 `C:\Users\<你>\.workday_reminder\settings.ini` 复制出来，作为下发模板。注意 `welcomed=true` 可以省掉每个人的首启欢迎弹窗，`pos=` 留空让每人按自己的屏幕定位。

**3）用登录脚本分发**

把 exe 和 `.workday_reminder\settings.ini` 一起放到每台机器的用户目录，再写注册表启动项：

```powershell
$dst = "$env:USERPROFILE\.workday_reminder"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item "\\server\share\WorkdayReminder\settings.ini" "$dst\settings.ini" -Force

$exe = 'D:\Tools\WorkdayReminder\WorkdayReminder.exe'
Set-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name WorkdayReminder -Value "`"$exe`""
Start-Process $exe
```

**4）不写注册表也可以**

把 `WorkdayReminder.exe` 的快捷方式放进 `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`，效果等同。区别是程序里的"开机自动启动"勾选框只认注册表，用快捷方式时那个勾选框会显示为未勾选——功能仍然正常，不会重复启动（有单实例保护）。

**5）每用户独立**

程序的数据目录和单实例名都按当前用户区分（`~/.workday_reminder`，单实例名 `WorkdayReminder-<用户名>`），所以同一台机器多个用户各自登录互不干扰。

## 10. 离线与内网部署

程序**不依赖网络也能工作**：内置 2025、2026 年数据，其余年份缺数据只会让悬浮窗显示"⚠ 20XX 年放假安排未加载"，不影响"今年是不是工作日"的判断。

内网完全断网时，按以下方式补齐后续年份：

**1）拿到数据**：在有网的机器上访问

```text
https://cdn.jsdelivr.net/gh/NateScarlet/holiday-cn@master/2027.json
```

**2）放到数据目录**，文件名必须是 `holiday_cn_2027.json`（`holiday_cn_*.json` 会在启动时被自动扫描加载）：

```text
%USERPROFILE%\.workday_reminder\holiday_cn_2027.json
```

**3）数据格式**（holiday-cn 的标准结构，`isOffDay: true` 表示放假，`false` 表示调休上班）：

```json
{
  "year": 2027,
  "days": [
    { "name": "元旦", "date": "2027-01-01", "isOffDay": true },
    { "name": "元旦", "date": "2027-01-04", "isOffDay": false }
  ]
}
```

放好后重启程序，设置页顶部会显示"已加载官方放假安排：2025、2026、2027 年"。

其它离线相关：

- 程序启动约 2 秒后会尝试联网，失败只是追加一条"网络获取失败（继续使用已有数据）"，不会弹窗打扰；
- 需要走代理时，Qt 默认读取系统代理设置（Windows 的 IE/系统代理、环境变量 `HTTP_PROXY`/`HTTPS_PROXY`），不需要改代码；
- 若企业强制所有外联走白名单，加白 `cdn.jsdelivr.net`、`fastly.jsdelivr.net`、`raw.githubusercontent.com` 即可，三者有一个可用就够。

## 11. 用 GitHub Actions 自动构建

仓库自带 `.github/workflows/build-windows.yml`：在 GitHub 的 **Actions** 页手动运行 **Run workflow**，或推送 `v*` 标签时自动构建，产物以 artifact 形式提供下载。

```yaml
name: Build Windows exe

on:
  workflow_dispatch:
  push:
    tags: ["v*"]

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt pyinstaller
      - name: Build
        run: python -m PyInstaller --noconfirm --clean --onefile --windowed --name WorkdayReminder main.py
      - uses: actions/upload-artifact@v4
        with:
          name: WorkdayReminder-windows
          path: dist/WorkdayReminder.exe
```

下载流程：Actions → 选一次成功的运行 → 页面底部 **Artifacts** → `WorkdayReminder-windows.zip`。把 exe 挂到 Release 上作为正式下载入口即可。

> CI 里不需要 `--add-data`，程序没有外部资源文件；也不需要签名证书（除非你配置了 secrets）。

## 12. 故障排查

### 12.1 源码运行阶段

| 报错 / 现象 | 原因 | 处理 |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'PySide6'` | 没装依赖，或没激活虚拟环境 | 激活 `.venv` 后 `pip install -r requirements.txt` |
| `ImportError: DLL load failed while importing QtCore` | PySide6 与系统里的另一套 Qt DLL 冲突（conda 的 `qt6-main` 与 pip 的 PySide6 混装最常见），或缺少 VC++ 运行库 | 换干净虚拟环境重装；`pip install --force-reinstall PySide6`；安装 Microsoft Visual C++ 2015–2022 运行库；检查 `PATH` 里是否残留其他 `Qt6Core.dll` |
| `Could not load the Qt platform plugin "xcb"`（Linux） | 缺 xcb 相关系统库 | `apt install libxcb-cursor0 libxkbcommon-x11-0` |
| `qt.qpa.plugin: could not connect to display` | 没有图形界面（SSH / 无桌面） | 该程序必须有桌面会话才能运行 |
| 启动后立刻退出，无任何界面 | 上一次实例还在（单实例机制），或异常发生在 `QApplication` 之前 | 任务管理器结束残留进程；用 `python main.py`（带控制台）看报错 |
| 悬浮窗在，但托盘图标没有 | 系统托盘不可用 / 图标被折叠 | 检查 Windows"其他系统托盘图标"设置；Linux 需桌面支持 SNI |

### 12.2 打包阶段

| 报错 / 现象 | 原因 | 处理 |
| --- | --- | --- |
| `ERROR: The 'pathlib' package is an obsolete backport ... incompatible with PyInstaller` | 环境里装了废弃的 `pathlib` backport 包（Anaconda 环境常见） | `pip uninstall -y pathlib`，conda 环境用 `conda remove pathlib`，然后重新打包 |
| 打包报错找不到 PySide6 插件 | 依赖没装进当前解释器 | 确认 `pip show pyinstaller` 和 `pip show PySide6` 指向同一个 Python |
| `RecursionError` / 体积异常巨大 | 环境里装了过多无关包，或用了 base 环境 | 在干净 venv 里打包 |
| exe 双击无反应 | `--windowed` 模式吞掉了异常 | 临时用 `--console` 重新打包，看控制台输出 |
| 杀毒软件报毒 / 删除 exe | PyInstaller 单文件自解压行为被启发式拦截 | 加白名单、改用 `--onedir`、或对 exe 做代码签名 |
| PyInstaller 版本过旧导致 Qt6 插件收集失败 | 老版本不识别 PySide6 6.x 的钩子 | `pip install -U pyinstaller`（≥ 6.0） |

### 12.3 运行阶段

| 现象 | 排查方向 |
| --- | --- |
| 开机没有自启 | ① 设置里勾选状态是否被保存；② `HKCU\...\Run` 里是否有 `WorkdayReminder` 值、路径是否正确；③ 任务管理器→启动应用里是否被禁用；④ 是否用了快捷方式启动（那样程序内勾选框不会显示已勾选） |
| 自启后找不到窗口 | 悬浮窗位置保存在 `pos`，换显示器后可能落在屏幕外；程序启动时校验坐标，但仍可能落在"存在但不可见"的区域——设置里点「回到右上角」 |
| 时间判断全错 | 系统时间不对；程序用北京时间计算，与系统时区无关，但要保证**系统时钟**准确 |
| 放假数据没更新 | 看设置页底部提示；手动点"更新节假日数据"看返回信息；检查代理/防火墙；确认数据目录可写 |
| 多人共用电脑互相影响 | 不应发生：数据目录和单实例名都按用户区分；若确有问题，检查是否用了同一个用户账户运行 |
| 设置改完没生效 | 点了"取消"不会保存；透明度是实时预览，其它项保存后才生效；`settings.ini` 只读或被杀软锁定时保存会失败 |

### 12.4 日志

程序本身不写日志文件。排查打包产物的启动问题，用 `--console` 版本临时替换即可看到所有 traceback；设置相关的问题直接看 `%USERPROFILE%\.workday_reminder\settings.ini` 是否按预期写入。

## 13. 升级与回滚

- **升级**：`git pull` 后重新打包，用新 exe 覆盖旧 exe（**保持路径不变**，自启项才不用改）。配置文件向前兼容，新版本只会在缺键时使用默认值，不会覆盖已有设置。
- **回滚**：换回旧 exe 即可。若新版本改过 `settings.ini` 的结构，旧版本读到未知键会忽略，不会崩溃；想彻底干净就删掉 `settings.ini` 重新配置。
- **发布建议**：用 `v1.0.0` 这样的标签（tag）触发 [GitHub Actions](#11-用-github-actions-自动构建)，把构建产物挂到 Release 上；版本说明里写清"是否需要重新配置"。
- **兼容性注意**：`--onefile` 升级时不要直接覆盖正在运行的 exe（Windows 会拒绝写入），先退出程序再替换。

---

[← 返回 README](../README.md)　·　[用户使用文档 →](user-guide.md)
