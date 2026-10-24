# 工作日提醒器 · 部署与编译指南（零基础版）

这份文档假设你**从没写过代码、也没编译过程序**。跟着做，你能做到四件事：

1. 在自己电脑上把程序跑起来；
2. 用 **PyInstaller** 把它打包成一个 exe；
3. 用 **Nuitka** 再打包一次，对比两者的区别；
4. 把成品装到自己和同事的电脑上，设置开机自启。

每一步都写了"你会看到什么"和"报错了怎么办"。命令可以直接复制粘贴，路径按你自己的情况改。

日常使用说明见[用户使用文档](user-guide.md)。

---

## 目录

- [0. 先读这一段](#0-先读这一段)
- [1. 第一步：装好环境](#1-第一步装好环境)
- [2. 编译方式一：PyInstaller](#2-编译方式一pyinstaller)
- [3. 编译方式二：Nuitka](#3-编译方式二nuitka)
- [4. 部署：装到自己和别人的电脑上](#4-部署装到自己和别人的电脑上)
- [5. 开机自启的实现](#5-开机自启的实现)
- [6. 配置键参考](#6-配置键参考)
- [7. 离线与内网部署](#7-离线与内网部署)
- [8. 用 GitHub Actions 自动编译](#8-用-github-actions-自动编译)
- [9. 故障排查](#9-故障排查)
- [10. 升级与回滚](#10-升级与回滚)

---

## 0. 先读这一段

### 0.1 你要选哪条路

| 你的情况 | 建议做法 | 花多久 |
| --- | --- | --- |
| 只想用，不想碰代码 | 直接下载 [Releases](https://github.com/Delusionx1/WorkdayReminder/releases) 里的 `WorkdayReminder.exe`，双击运行 | 1 分钟 |
| 想改点东西（时间、界面、逻辑） | 从源码运行：装 Python → 下载代码 → `python main.py` | 20 分钟 |
| 想发给同事 / 放到自己电脑长期用 | 源码运行 + 编译成 exe（第 2 或第 3 章） | 40 分钟 |
| 在意启动速度、杀毒软件误报 | 用 Nuitka 编译（第 3 章） | 20–40 分钟（首次编译慢） |

**最快的体验路径**：直接下 exe，跳到[第 4 章部署](#4-部署装到自己和别人的电脑上)。

### 0.2 几个词先说明白

| 词 | 大白话 |
| --- | --- |
| 命令行 / 终端 | 一个黑底白字的窗口，你输入命令、电脑执行。Windows 里叫 `cmd` 或 `PowerShell` |
| Python | 这个程序是用 Python 语言写的，所以要装一个"能运行 Python 的程序" |
| 依赖 | 程序运行需要别人写好的零件（比如画界面的 PySide6），要用 `pip` 装 |
| 虚拟环境 | 给这个项目单独圈出来的一个文件夹，装的零件不污染电脑其他地方。删掉文件夹就等于卸载干净 |
| 编译 / 打包 | 把"Python 代码 + 零件 + 解释器"捆成一个 exe，让别人不用装 Python 也能双击运行 |
| PyInstaller / Nuitka | 两种打包工具。前者打包快、体积大；后者把代码编译成 C 再编译，启动快、误报少，但编译慢 |

### 0.3 需要准备什么

- Windows 10 或 11（64 位），**不需要管理员权限**；
- 至少 3 GB 空闲磁盘（Nuitka 要下载编译器，占得多一些）；
- 能上网（第一次装依赖、第一次编译需要；之后编译可离线）；
- 一个放代码的文件夹，**建议路径简单**，例如 `D:\code\WorkdayReminder`。中文路径通常没问题，但少数工具对中文、空格、超长路径敏感，用英文路径最省事。

> 命令里的 `>` 是提示符，不用输入。比如看到 `C:\Users\you>`，你只需要输入后面的内容。

## 1. 第一步：装好环境

### 1.1 安装 Python

1. 打开 <https://www.python.org/downloads/>；
2. 点黄色按钮 **Download Python 3.12.x**（3.11 / 3.13 也可以，本文以 3.12 为例）；
3. 双击下载好的 `python-3.12.x-amd64.exe`；
4. **最关键的一步**：安装向导第一页底部，把 **Add python.exe to PATH** 勾上（不勾后面会一直提示"找不到 python"）；
5. 点 **Install Now**，等进度条走完，点 Close。

> 已经有 Python 了？跳过这步。装过 Anaconda 也可以，但**不要**用 Anaconda base 环境装本项目依赖（见[第 9.1 节](#91-装环境--运行常见问题)）。

### 1.2 验证 Python 装好了

按 `Win + R`，输入 `cmd`，回车。在黑窗口里输入：

```bat
python --version
```

**你会看到**类似：

```text
Python 3.12.10
```

有版本号就成功了。再确认一下 pip：

```bat
python -m pip --version
```

能看到 `pip 24.x` 之类即可。

**如果报错**：

| 提示 | 原因 | 处理 |
| --- | --- | --- |
| `'python' 不是内部或外部命令` | 安装时没勾 Add to PATH | 重新运行安装包 → Modify → 勾上 PATH；或干脆重装一次 |
| 打开了微软商店 | Windows 的"应用执行别名"抢了 `python` 命令 | 设置 → 应用 → 高级应用设置 → 应用执行别名 → 关闭 `python.exe` / `python3.exe` |
| `Python was not found; run without arguments to install...` | 同上，别名问题 | 同上 |

> 关掉旧窗口再开新窗口才会生效——PATH 是打开窗口时读取的。

### 1.3 拿到代码

**方式 A：装 Git 克隆（推荐，方便以后更新）**

1. 下载并安装 Git：<https://git-scm.com/download/win>，一路"下一步"即可；
2. 新开一个 `cmd`，执行：

```bat
D:
mkdir code
cd code
git clone https://github.com/Delusionx1/WorkdayReminder.git
cd WorkdayReminder
```

（没有 D 盘就把 `D:` 换成 `C:`，路径自定。）

**方式 B：不装 Git，下压缩包**

1. 打开 <https://github.com/Delusionx1/WorkdayReminder>；
2. 绿色按钮 **Code → Download ZIP**；
3. 解压到 `D:\code\WorkdayReminder`（解压后确认 `main.py` 就在这个文件夹里）。

### 1.4 打开命令行并进入项目文件夹

最简单的办法：

1. 打开文件资源管理器，进入项目文件夹（能看到 `main.py` 那一层）；
2. 点一下顶部的**地址栏**，把里面的路径删掉，输入 `cmd`，回车。

**你会看到**一个黑窗口，提示符已经是项目路径，例如：

```text
D:\code\WorkdayReminder>
```

以后每次要做操作，都在这个窗口里输入命令。**不要关掉它**。

### 1.5 创建虚拟环境并安装依赖

依次输入（一行回车一次）：

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**每步你会看到**：

| 命令 | 现象 |
| --- | --- |
| `python -m venv .venv` | 等几秒，文件夹里多出一个 `.venv` 目录，无输出就是成功 |
| `.venv\Scripts\activate.bat` | 提示符前面多了 `(.venv)`，表示已在虚拟环境里 |
| `pip install --upgrade pip` | 下载一小段，最后显示 `Successfully installed pip-...` |
| `pip install -r requirements.txt` | 下载 PySide6（约 150 MB），最后显示 `Successfully installed PySide6-...` |

> 提示符变成 `(.venv) D:\code\WorkdayReminder>` 就对了。如果关掉了窗口，下次要先重新执行 `.venv\Scripts\activate.bat`。

**下载很慢或超时**？换国内镜像重试：

```bat
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**PowerShell 用户**（提示符是 `PS D:\...>`）：激活命令换成 `.venv\Scripts\Activate.ps1`；若提示"禁止运行脚本"，先执行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

**报错对照**：

| 提示 | 处理 |
| --- | --- |
| `'pip' 不是内部或外部命令` | 虚拟环境没激活（看不到 `(.venv)`）就执行了 pip |
| `ERROR: Could not find a version that satisfies the requirement PySide6` | Python 版本太新或太旧；换 3.12；或加 `-i` 镜像 |
| `SSLError` / `ProxyError` | 公司网络代理问题：设置 `set HTTPS_PROXY=http://代理地址:端口` 后重试 |
| `No module named venv` | Python 精简版安装；用官方安装包重装 |

### 1.6 第一次运行

```bat
python main.py
```

**你会看到**：

- 屏幕右上角出现半透明小窗；
- 任务栏右下角（可能在"隐藏的图标"里）出现一个圆形图标；
- 这个黑窗口会一直开着——**关掉它程序就退出了**，这是正常的。想让它安静地在后台跑，用：

```bat
pythonw main.py
```

- 用户目录下生成 `C:\Users\你的用户名\.workday_reminder\settings.ini`。

第一次启动会弹一条欢迎通知，双击悬浮窗就能进设置。

> 想退出：右键托盘图标 → **退出**。

### 1.7 装环境阶段最常见的三个报错

| 报错 | 含义 | 解决 |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'PySide6'` | 依赖没装上，或没用对虚拟环境 | 确认提示符有 `(.venv)`，重新 `pip install -r requirements.txt` |
| `ImportError: DLL load failed while importing QtCore` | 系统里有多套 Qt 打架，或缺 C++ 运行库 | 见[第 9.1 节](#91-装环境--运行常见问题) |
| 双击 `python main.py` 一闪而过 | 你在资源管理器里双击了 .py，报错来不及看 | 在命令行里运行，别双击 |

到这里程序能跑了，剩下的都是"打包"。

## 2. 编译方式一：PyInstaller

### 2.1 它是什么

PyInstaller 把 Python 解释器、你的代码、PySide6 的 DLL 全部塞进一个 exe。运行时 exe 会先把自己解压到临时目录再启动，所以：

- ✅ 别人不用装 Python，双击就能用；
- ✅ 打包只要一条命令，1–3 分钟；
- ❌ 体积大（本项目约 43 MB），每次启动要解压（1–3 秒）；
- ❌ 自解压行为容易被杀毒软件误判。

### 2.2 安装

确认在项目目录、虚拟环境已激活（提示符有 `(.venv)`）：

```bat
pip install pyinstaller
```

**你会看到** `Successfully installed pyinstaller-6.x ...`。

### 2.3 编译命令

```bat
python -m PyInstaller --noconfirm --clean --onefile --windowed --name WorkdayReminder main.py
```

**参数在干什么**（照抄即可，了解意思就行）：

| 参数 | 作用 |
| --- | --- |
| `--onefile` | 打成一个 exe 文件，方便发人 |
| `--windowed` | 运行时**不弹黑色命令行窗口** |
| `--name WorkdayReminder` | 生成的 exe 叫这个名字 |
| `--clean` | 清掉上次的缓存，避免改了代码却打出旧版本 |
| `--noconfirm` | 覆盖旧文件时不再问"是否继续" |

**你会看到**满屏日志，最后一行的附近是：

```text
INFO: Building EXE from EXE-00.toc completed successfully.
```

**时间**：第一次 1–3 分钟，之后通常更快。

### 2.4 一键脚本（推荐新手用这个）

项目里已经放好了 `build_windows.bat`，**双击它**就行，效果和上面那条命令完全一样。

如果双击后窗口一闪而过，说明出错了。在命令行里执行它，才能看到错误：

```bat
build_windows.bat
```

### 2.5 检查产物

编译完成后，项目目录里会多出：

```text
dist\
└── WorkdayReminder.exe        ← 这个就是要分发的东西
build\                          ← 中间文件，可以删
```

验证方法：

1. 双击 `dist\WorkdayReminder.exe`，悬浮窗和托盘图标应该出现；
2. 关掉窗口、把 exe 剪切到 `D:\Tools\` 再双击，仍然正常；
3. 首次运行后确认 `%USERPROFILE%\.workday_reminder\settings.ini` 有生成；
4. 再双击一次 exe：不应出现第二个悬浮窗，而是弹出已有实例的设置窗口。

### 2.6 进阶：让启动更快、加个图标

**启动太慢？改成目录模式**（体积略大，但启动快很多）：

```bat
python -m PyInstaller --noconfirm --clean --onedir --windowed --name WorkdayReminder main.py
```

产物是 `dist\WorkdayReminder\` 整个文件夹，**要连同文件夹一起发**，exe 在文件夹里。

**换图标**：准备一个 `.ico` 文件（比如 `app.ico`），加参数：

```bat
python -m PyInstaller --noconfirm --clean --onefile --windowed --icon app.ico --name WorkdayReminder main.py
```

### 2.7 PyInstaller 常见问题

| 现象 | 原因 / 处理 |
| --- | --- |
| `ERROR: The 'pathlib' package is an obsolete backport ... incompatible with PyInstaller` | 环境里装了废弃的 `pathlib` 包（Anaconda 常见）。`pip uninstall -y pathlib` 后重新打包 |
| 打包后双击没反应 | `--windowed` 把报错藏了。临时改成 `--console` 打包，在命令行里运行看报错 |
| 被杀毒软件删掉 / 报毒 | 单文件自解压被误判。加白名单、改用 `--onedir`、或给 exe 做代码签名 |
| `ModuleNotFoundError` 但源码能跑 | 打包时用的不是同一个 Python/环境。确认 `pip show pyinstaller` 和 `pip show PySide6` 指向同一位置 |
| 体积异常大 / 打包特别慢 | 在 base 环境或装了太多无关包。用本项目的 `.venv` 重新装依赖再打包 |
| 首次运行要等 2–3 秒 | 单文件模式的正常现象，换 `--onedir` 可解决 |

## 3. 编译方式二：Nuitka

### 3.1 它是什么、和 PyInstaller 有什么不同

Nuitka 走的是另一条路：先把你的 Python 代码**翻译成 C 代码**，再用 C 编译器编译成本地程序，最后把依赖一起打包。

| 对比项 | PyInstaller | Nuitka |
| --- | --- | --- |
| 原理 | 打包解释器 + 代码，运行时解释执行 | 代码 → C → 编译成本地机器码 |
| 准备工作 | `pip install pyinstaller` | 还要有 C 编译器（首次会自动下载 MinGW） |
| 首次编译时间 | 1–3 分钟 | 本机实测约 3 分钟；首次要下编译器、或 CPU 较老时 5–15 分钟 |
| 启动速度 | 较慢（每次解压） | 较快 |
| 被杀软误报 | 较常见 | 相对少 |
| 体积（单文件） | 约 43 MB | 约 19 MB（本机实测 19.1 MB） |
| 排错难度 | 低，资料多 | 中等，编译报错偏"硬核" |

> 结论：**自己用、想快出结果 → PyInstaller；要发给很多人、在意启动速度和误报 → Nuitka**。两个都装也不冲突，产物目录不同。

### 3.2 安装 Nuitka

确认在项目目录、虚拟环境已激活：

```bat
pip install nuitka zstandard
```

- `nuitka` 是编译器本体；
- `zstandard` 用来压缩单文件产物，Nuitka 打 onefile 时需要。

**你会看到** `Successfully installed nuitka-... zstandard-...`。

> 不要装成 `Nuitka` 之外的山寨包；命令统一用 `python -m nuitka`，避免 PATH 里找不到。

### 3.3 准备 C 编译器（二选一）

**路线 A：让 Nuitka 自己下载（推荐，最省事）**

在编译命令里加 `--mingw64 --assume-yes-for-downloads`，Nuitka 发现没有编译器时会自动下载一套 MinGW64（约 100–200 MB）并装到它自己的缓存目录，**不需要你手动装任何东西**，也不需要管理员权限。

代价：第一次编译要等下载，网络慢的话会久一点。

**路线 B：用 Visual Studio 的 MSVC（体积大、但更"正规"）**

1. 下载 [Visual Studio 2022 Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)；
2. 安装时勾选 **使用 C++ 的桌面开发**（约 3–5 GB）；
3. 装完后把命令里的 `--mingw64` 换成 `--msvc=latest`。

> 机器上已经装过 Visual Studio 的，Nuitka 会自动找到 MSVC，可以不加任何编译器参数。

### 3.4 编译命令

```bat
python -m nuitka --mode=onefile --enable-plugin=pyside6 --windows-console-mode=disable --mingw64 --assume-yes-for-downloads --remove-output --output-dir=dist-nuitka --output-filename=WorkdayReminder.exe main.py
```

**参数在干什么**：

| 参数 | 作用 |
| --- | --- |
| `--mode=onefile` | 打成一个 exe（Nuitka 4.x 的写法） |
| `--enable-plugin=pyside6` | 让 Nuitka 正确处理 PySide6 / Qt 的插件和 DLL，**不能省** |
| `--windows-console-mode=disable` | 运行时不弹黑色命令行窗口 |
| `--mingw64` | 用 MinGW（配 `--assume-yes-for-downloads` 会自动下载） |
| `--assume-yes-for-downloads` | 自动同意下载编译器/组件，不用手动按 y |
| `--remove-output` | 编译完清掉中间文件，省磁盘 |
| `--output-dir=dist-nuitka` | 产物放到 `dist-nuitka` 文件夹，不和 PyInstaller 的 `dist` 混淆 |
| `--output-filename=WorkdayReminder.exe` | 生成的 exe 名 |

> **版本差异**：Nuitka 4.x 用 `--mode=onefile`。如果你的 Nuitka 是 3.x 或更早，把 `--mode=onefile` 换成 `--standalone --onefile`；`--windows-console-mode=disable` 换成 `--windows-disable-console`。
> 用 `python -m nuitka --version` 可以看自己装的是哪个版本。

**你会看到**：先是一堆 `Nuitka-Options`、`Nuitka:INFO` 开头的日志，然后进入编译阶段，不断刷 `Compiling ...` 之类的行。**几十分钟没动静也可能是正常的**——它在编译几百个 C 文件。

**时间**：本机实测约 3 分钟（编译器已就绪）；第一次要下载编译器、CPU 较老时会到 5–15 分钟。内存建议 8 GB 以上。

### 3.5 一键脚本

项目里同样放好了 `build_windows_nuitka.bat`，**双击运行**即可，内含上面那条命令。

出错时不要双击，改在命令行里执行，才能看到完整报错：

```bat
build_windows_nuitka.bat
```

> 脚本里会先 `pip install nuitka zstandard`，所以就算忘了装也能跑。

### 3.6 检查产物

```text
dist-nuitka\
└── WorkdayReminder.exe        ← Nuitka 打出来的 exe，本机实测 19.1 MB
```

单文件产物用压缩存放，体积明显小于 PyInstaller（本机 43 MB），代价是首次启动要解压到临时目录，之后启动比 PyInstaller 快。

验证方法和 PyInstaller 完全一样：双击 → 看悬浮窗 → 看托盘 → 再双击验证单实例。

**注意**：如果编译完没有 exe，只有 `main.dist` / `main.build` 目录，说明 `--mode` 没生效（多见于版本差异），看[第 9.3 节](#93-nuitka-常见问题)。

### 3.7 进阶：图标、版本信息、关闭单文件

**加图标**：

```bat
python -m nuitka --mode=onefile --enable-plugin=pyside6 --windows-console-mode=disable --mingw64 --assume-yes-for-downloads --windows-icon-from-ico=app.ico main.py
```

**写进 exe 属性里的版本信息**（右键 exe → 属性 → 详细信息能看到）：

```bat
python -m nuitka --mode=onefile --enable-plugin=pyside6 --windows-console-mode=disable --mingw64 --assume-yes-for-downloads --company-name="Delusionx1" --product-name="工作日提醒器" --file-version=1.0.0.0 --product-version=1.0.0.0 main.py
```

**觉得单文件启动慢 / 被杀软反复扫描**，改成目录模式，分发整个文件夹：

```bat
python -m nuitka --mode=standalone --enable-plugin=pyside6 --windows-console-mode=disable --mingw64 --assume-yes-for-downloads --output-dir=dist-nuitka main.py
```

产物在 `dist-nuitka\main.dist\WorkdayReminder.exe`，**要连同整个 `main.dist` 文件夹一起发**。

**想要更小更快的成品**（编译时间会明显变长）：

```bat
... --lto=yes
```

### 3.8 Nuitka 常见问题

| 现象 | 处理 |
| --- | --- |
| `no such option: --mode` | Nuitka 版本旧：改用 `--standalone --onefile` |
| `no such option: --windows-console-mode` | 版本旧：改用 `--windows-disable-console` |
| `Nuitka-Scons:WARNING: Windows SDK must be installed in Visual Studio` | 用 MinGW 路线可以忽略；用 MSVC 路线则需在 VS Installer 里补装 Windows SDK |
| `No C compiler found` / `gcc not found` | 命令里加 `--mingw64 --assume-yes-for-downloads` |
| 卡在 `Downloading ...` 很久 | 在下载 MinGW（100–200 MB），耐心等；公司网络限制时改用路线 B |
| 编译到一半失败并提示 `cl.exe` 找不到 | 用了 `--msvc` 但没装 VS；卸掉 `--msvc` 改 `--mingw64` |
| 运行报 `Could not find the Qt platform plugin "windows"` | Qt 插件没带全：命令里加 `--include-qt-plugins=sensible,styles` 重新编译 |
| 内存占用飙高 / 电脑很卡 | 关掉浏览器等大程序；Nuitka 编译确实吃内存，8 GB 以下建议只用 PyInstaller |
| 编译中断后磁盘越来越大 | 手动删 `main.build`、`main.dist`、`main.onefile-build`，或每次加 `--remove-output` |
| 项目路径含中文/空格导致奇怪报错 | 把项目移到 `D:\code\WorkdayReminder` 这种纯英文短路径再编译 |

### 3.9 两种方式怎么选

| 你想要 | 选它 |
| --- | --- |
| 5 分钟出结果，先跑起来 | PyInstaller |
| 发给同事，启动别卡 | Nuitka |
| 公司杀软很严，exe 老被删 | Nuitka（相对少误报），并考虑代码签名 |
| 电脑内存小、CPU 老 | PyInstaller |
| 以后想加功能、频繁重新打包 | PyInstaller（编译快，迭代快）；发版时再用 Nuitka |

## 4. 部署：装到自己和别人的电脑上

### 4.1 部署前检查清单

- [ ] 有一份能双击运行的 exe（`dist\WorkdayReminder.exe` 或 `dist-nuitka\WorkdayReminder.exe`）；
- [ ] 在自己电脑上跑通过：悬浮窗正常、托盘正常、设置能保存；
- [ ] 记录版本：`v1.0.0` 之类，便于以后更新；
- [ ] 知道它在用户目录写的两个文件（`settings.ini`、`holiday_cn_*.json`）。

### 4.2 装到自己电脑

1. 建一个**固定目录**，例如 `D:\Tools\WorkdayReminder\`，把 exe 放进去；
2. 双击运行；
3. 双击悬浮窗 → 设置客户工作时间 → 需要的话勾上 **开机自动启动** → 保存；
4. 右键托盘 → 退出，然后重启一次电脑，验证自启是否生效（或者直接看[第 5 章](#5-开机自启的实现)的注册表位置）。

> ⚠️ 不要把 exe 放在"下载"文件夹、桌面或同步盘的临时目录里。换位置后自启项里还是旧路径，虽然程序启动时会自动修正，但需要你手动运行一次。

### 4.3 发给同事

**方式一：压缩包（最稳妥）**

把 exe 压成 zip，里面再放一份简短的说明：

```text
WorkdayReminder-v1.0.0.zip
├── WorkdayReminder.exe
└── 使用说明.txt
```

`使用说明.txt` 可以照抄这段：

```text
工作日提醒器 v1.0.0

1. 把 WorkdayReminder.exe 解压到固定目录（例如 D:\Tools\WorkdayReminder\），不要放"下载"文件夹。
2. 双击运行，屏幕右上角会出现悬浮窗，任务栏托盘会出现圆形图标（可能在"隐藏的图标"里）。
3. 双击悬浮窗可以打开设置：填你自己的客户工作时间，勾上"开机自动启动"，点保存。
4. 首次运行如果出现蓝色 SmartScreen 提示，点"更多信息 → 仍要运行"。
5. 退出：右键托盘图标 → 退出。

绿色软件，不写注册表（除了开机自启），卸载直接删 exe 和 %USERPROFILE%\.workday_reminder 文件夹即可。
```

**方式二：直接发 exe**

微信、邮箱、企业 IM 经常拦截 `.exe`。三个办法：

- 压成 `.zip` 再发；
- 改名为 `WorkdayReminder.exe.zip`；
- 放到网盘 / 内网共享盘，把链接发给对方。

**方式三：内网共享 / 文件服务器**

把 exe 放到共享目录，同事直接从 `\\服务器\软件\WorkdayReminder\` 双击运行也可以（但更推荐复制到本地运行，避免共享盘断线）。

**顺手给个校验值**，让对方确认文件没被改坏：

```bat
certutil -hashfile WorkdayReminder.exe SHA256
```

把这串哈希值一起发给对方，对方在同一个目录执行同一条命令，值一样就说明文件完整。

### 4.4 批量部署（给整个部门装）

思路：**exe 放公共位置 + 配置文件预置到每个用户目录 + 写启动项**。

**1）准备一个固定的安装目录**

```text
D:\Tools\WorkdayReminder\WorkdayReminder.exe
```

**2）准备预置配置**

在自己电脑配好参数，把 `C:\Users\<你>\.workday_reminder\settings.ini` 复制出来作为模板（建议把 `welcomed=true`，省掉每个人的首启弹窗；`pos=` 留空让他们按自己的屏幕定位）。

**3）用登录脚本分发**（PowerShell，普通用户权限即可）

```powershell
$dst = "$env:USERPROFILE\.workday_reminder"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item "\\server\share\WorkdayReminder\settings.ini" "$dst\settings.ini" -Force

$exe = 'D:\Tools\WorkdayReminder\WorkdayReminder.exe'
Set-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name WorkdayReminder -Value "`"$exe`""
Start-Process $exe
```

逐行说明：

| 行 | 作用 |
| --- | --- |
| `$dst = ...` | 目标配置目录 |
| `New-Item ... -Force` | 没有就建，有就跳过 |
| `Copy-Item ...` | 把模板配置拷过去 |
| `$exe = ...` | 你的安装路径 |
| `Set-ItemProperty ... Run` | 写开机自启（当前用户，不需要管理员） |
| `Start-Process $exe` | 立刻启动一次 |

**4）不想写注册表也可以**

把 exe 的快捷方式放到 `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup` 文件夹里，效果一样。区别是程序里的"开机自动启动"勾选框会显示未勾选（它只认注册表），但功能正常，也不会重复启动。

### 4.5 多用户、权限与公司策略

- **多用户互不影响**：配置目录和单实例名都按用户区分（`WorkdayReminder-<用户名>`），同一台电脑几个账号各自独立；
- **不需要管理员权限**：exe 运行、写注册表启动项、写用户目录，全是当前用户范围；
- **公司统一清理启动项**：组策略可能会反复删掉 `Run` 键。这种情况改用"启动"文件夹快捷方式，或做进登录脚本；
- **软件白名单**：如果公司只允许特定程序运行，需要把 exe 加入白名单，或干脆从源码运行（`pythonw main.py` + 计划任务）。

## 5. 开机自启的实现

「常规」页勾选「开机自动启动」后，程序按平台写启动项。命令内容取决于运行方式：

| 运行方式 | 写入的命令 |
| --- | --- |
| 打包后的 exe | exe 的绝对路径 |
| 源码运行（Windows） | `pythonw.exe` + `main.py` 的绝对路径（优先 pythonw，避免黑框） |
| 源码运行（macOS / Linux） | 当前 Python 解释器 + `main.py` 的绝对路径 |

各平台写入位置：

| 平台 | 位置 | 备注 |
| --- | --- | --- |
| Windows | `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`，值名 `WorkdayReminder` | 当前用户级，**不需要管理员权限**；带空格的路径自动加引号 |
| macOS | `~/Library/LaunchAgents/com.workday.reminder.plist` | `RunAtLoad = true`；下次登录生效，立即生效用 `launchctl load -w` |
| Linux | `~/.config/autostart/workday-reminder.desktop` | 带 `X-GNOME-Autostart-enabled=true` |

查看 / 手动管理（Windows）：

```powershell
# 查看
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" | Select-Object WorkdayReminder

# 手动添加
Set-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name WorkdayReminder `
  -Value '"D:\Tools\WorkdayReminder\WorkdayReminder.exe"'

# 删除
Remove-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name WorkdayReminder
```

两个容易踩的点：

- **移动 exe 后自启失效**：程序每次启动都会检查并重写启动项，所以移动后**手动运行一次**即可自愈；
- **安全软件禁用启动项**：任务管理器 → 启动应用里如果显示"已禁用"，需要手动启用；部分安全软件也会拦截注册表写入，需要加白。

## 6. 配置键参考

配置文件：`~/.workday_reminder/settings.ini`（Windows：`%USERPROFILE%\.workday_reminder\settings.ini`），标准 INI，全部在 `[General]` 段。**修改前先退出程序**，否则程序可能回写覆盖。

| 键 | 类型 | 默认值 | 含义 |
| --- | --- | --- | --- |
| `work_start` | `HH:MM` | `09:00` | 客户上班时间；早间提醒也以此为触发点 |
| `work_end` | `HH:MM` | `18:00` | 客户下班时间；到点显示"已下班" |
| `lunch_enabled` | `true/false` | `true` | 是否启用午休判断 |
| `lunch_start` | `HH:MM` | `12:00` | 午休开始 |
| `lunch_end` | `HH:MM` | `13:30` | 午休结束 |
| `eve_time` | `HH:MM` | `16:00` | 节前收尾提醒的时刻 |
| `remind_weekend_eve` | `true/false` | `false` | 普通周五是否也做"节前收尾"提醒 |
| `custom_days` | 多行文本 | 空 | 自定义日期，格式见[用户文档](user-guide.md#52-自定义日期) |
| `opacity` | 30–100 | `85` | 悬浮窗不透明度百分比 |
| `pos` | `"x,y"` | 空 | 悬浮窗坐标；空表示使用右上角默认位置 |
| `locked` | `true/false` | `false` | 是否锁定悬浮窗位置 |
| `welcomed` | `true/false` | `false` | 是否已展示过首次启动的欢迎通知，置 `true` 可跳过 |

企业统一预置示例（09:30 上班、18:30 下班、午休 12:00–13:00、节前 15:30）：

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

## 7. 离线与内网部署

程序**不依赖网络也能工作**：内置 2025、2026 年数据；其余年份缺数据只影响"那一年是不是工作日"的判断，悬浮窗会提示"⚠ 20XX 年放假安排未加载"。

内网完全断网时，按下面补齐后续年份。

**1）拿到数据**：在有网的机器上访问

```text
https://cdn.jsdelivr.net/gh/NateScarlet/holiday-cn@master/2027.json
```

**2）放到数据目录**，文件名必须是 `holiday_cn_2027.json`（启动时自动扫描 `holiday_cn_*.json`）：

```text
%USERPROFILE%\.workday_reminder\holiday_cn_2027.json
```

**3）数据格式**（holiday-cn 标准结构，`isOffDay: true` 放假，`false` 调休上班）：

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

其它离线要点：

- 启动约 2 秒后会尝试联网，失败只追加一条"网络获取失败（继续使用已有数据）"，不弹窗打扰；
- 需要代理时，Qt 默认读取系统代理（Windows 的 IE/系统代理、`HTTP_PROXY`/`HTTPS_PROXY`），不用改代码；
- 企业强制白名单的话，放行 `cdn.jsdelivr.net`、`fastly.jsdelivr.net`、`raw.githubusercontent.com` 任意一个即可。

## 8. 用 GitHub Actions 自动编译

仓库里有两个工作流，都在 GitHub 的 **Actions** 页面：

| 工作流 | 触发方式 | 用途 |
| --- | --- | --- |
| **Build Windows exe** | 推送 `v*` 标签时自动；也可手动 | PyInstaller 打包，约 2 分钟 |
| **Build Windows exe (Nuitka)** | 只能手动触发 | Nuitka 打包，比 PyInstaller 久得多（十几分钟起），产物更小、启动更快 |

**怎么手动跑一次**：

1. 打开 <https://github.com/Delusionx1/WorkdayReminder/actions>；
2. 左边选工作流名；
3. 右侧 **Run workflow → Run workflow**；
4. 等圆圈变绿，点进这次运行，页面底部 **Artifacts** 下载 zip。

**PyInstaller 工作流内容**（`.github/workflows/build-windows.yml`）：

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
      - run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt pyinstaller
      - run: >
          python -m PyInstaller --noconfirm --clean --onefile --windowed
          --name WorkdayReminder main.py
      - uses: actions/upload-artifact@v4
        with:
          name: WorkdayReminder-windows
          path: dist/WorkdayReminder.exe
```

**Nuitka 工作流**（`.github/workflows/build-windows-nuitka.yml`）只有在你手动点运行时才会跑，避免每次打标签都等十几分钟：

```yaml
name: Build Windows exe (Nuitka)

on:
  workflow_dispatch:

jobs:
  build:
    runs-on: windows-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt nuitka zstandard
      - run: >
          python -m nuitka --mode=onefile --enable-plugin=pyside6
          --windows-console-mode=disable --mingw64 --assume-yes-for-downloads
          --remove-output --output-dir=dist-nuitka
          --output-filename=WorkdayReminder.exe main.py
      - uses: actions/upload-artifact@v4
        with:
          name: WorkdayReminder-windows-nuitka
          path: dist-nuitka/WorkdayReminder.exe
```

> 云端跑不需要你本地有编译器：GitHub 的 Windows runner 自带 Visual Studio，Nuitka 也可以自己下 MinGW。构建产物默认保留 90 天。

## 9. 故障排查

### 9.1 装环境 / 运行常见问题

| 报错 / 现象 | 原因 | 处理 |
| --- | --- | --- |
| `'python' 不是内部或外部命令` | 没勾 Add to PATH | 重装 Python 勾上；或用 `py -3` 代替 `python` |
| 弹出微软商店 | 应用执行别名抢占 | 设置 → 应用 → 高级应用设置 → 应用执行别名 → 关掉 python |
| `ModuleNotFoundError: No module named 'PySide6'` | 没装依赖 / 没激活虚拟环境 | 看到 `(.venv)` 再 `pip install -r requirements.txt` |
| `ImportError: DLL load failed while importing QtCore` | conda 的 Qt 与 pip 的 PySide6 冲突，或缺 VC++ 运行库 | 换干净虚拟环境重装；装 [VC++ 2015–2022 运行库](https://aka.ms/vs/17/release/vc_redist.x64.exe)；`pip install --force-reinstall PySide6` |
| `qt.qpa.plugin: Could not load the Qt platform plugin "xcb"`（Linux） | 缺 xcb 系统库 | `apt install libxcb-cursor0 libxkbcommon-x11-0` |
| 启动后无界面、进程却没了 | 已有实例在跑（单实例机制） | 任务管理器结束残留进程；用 `python main.py` 看报错 |
| 程序能跑但托盘没图标 | 托盘不可用 / 图标被折叠 | 检查 Windows"其他系统托盘图标"；Linux 需桌面支持 SNI |
| 装了 Anaconda，`pip` 装的东西找不到 | 混用了 conda 的 base 环境 | 用 `python -m venv .venv` 新建独立环境，别在 base 里装 |

### 9.2 PyInstaller 常见问题

| 现象 | 处理 |
| --- | --- |
| `The 'pathlib' package is an obsolete backport` | `pip uninstall -y pathlib`，再打包 |
| 打包成功但双击没反应 | 临时用 `--console` 打包，命令行运行看报错 |
| 杀软报毒 / exe 被删 | 加白名单；改 `--onedir`；或做代码签名 |
| 打包很慢 / 体积异常大 | 在干净的 `.venv` 里打包，别用 base 环境 |
| 打包后提示缺少模块 | 确认打包和运行用的是同一个虚拟环境；必要时 `--hidden-import=模块名` |

### 9.3 Nuitka 常见问题

| 现象 | 处理 |
| --- | --- |
| `no such option: --mode` | 版本旧，改用 `--standalone --onefile` |
| `no such option: --windows-console-mode` | 版本旧，改用 `--windows-disable-console` |
| `No C compiler found` | 加 `--mingw64 --assume-yes-for-downloads` |
| 编译数十分钟没动静 | 正常，看任务管理器 CPU 是否在跑；首次还要下编译器 |
| `Could not find the Qt platform plugin "windows"` | 加 `--include-qt-plugins=sensible,styles` 重编译 |
| 编译中断、磁盘暴涨 | 删 `main.build` / `main.dist` / `main.onefile-build`，或加 `--remove-output` |
| 成品启动仍很慢 | 单文件每次解压；改 `--mode=standalone` 分发文件夹 |
| 中文乱码或路径报错 | 项目移到纯英文短路径；`cmd` 里先执行 `chcp 65001` |

### 9.4 部署运行问题

| 现象 | 排查方向 |
| --- | --- |
| 开机没有自启 | ① 设置里勾选是否保存；② `HKCU\...\Run` 是否有 `WorkdayReminder` 且路径正确；③ 任务管理器→启动应用是否被禁用；④ 是否用快捷方式启动（程序里的勾选框只认注册表） |
| 自启后找不到窗口 | 悬浮窗位置保存在 `pos`，换显示器后可能落在看不见的区域 → 设置里点「回到右上角」 |
| 时间判断不对 | 系统时钟不准；程序固定按北京时间（UTC+8）判断，与系统时区无关 |
| 放假数据没更新 | 设置页底部提示；手动「更新节假日数据」；检查代理/防火墙；确认数据目录可写 |
| 同事那边打不开 | 对方是不是把 exe 放进了受限目录；是不是 32 位系统（本项目 64 位）；杀软是否拦截 |
| 多人共用一台电脑互相影响 | 不应发生：数据目录和单实例名按用户区分 |

> 程序本身不写日志。排查打包产物启动问题，用 `--console`（PyInstaller）或 `--windows-console-mode=force`（Nuitka）临时重编译一次，所有报错都会打在控制台。

## 10. 升级与回滚

- **升级**：`git pull` 拉代码（或重新下载 ZIP）→ 重新 `pip install -r requirements.txt` → 重新编译 → 用新 exe 覆盖旧 exe。**保持路径不变**，自启项才不用改。
- **覆盖前先退出程序**：单文件 exe 正在运行时 Windows 不允许覆盖。
- **配置兼容**：新版只会在缺键时使用默认值，不会覆盖你已有的设置；跨大版本升级前可以备份 `settings.ini`。
- **回滚**：换回旧 exe 即可。旧版读到新增的配置键会忽略，不会崩溃；想彻底干净就删 `settings.ini` 重新配置。
- **发布建议**：打 `v1.0.1` 这样的标签 → 自动触发 PyInstaller 构建 → 把产物挂到 Release；需要 Nuitka 版就手动跑一次 Nuitka 工作流，下载 artifact 一起挂上去。

---

[← 返回 README](../README.md)　·　[用户使用文档 →](user-guide.md)
