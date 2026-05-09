# core/window_interaction/window_info_provider.py
"""窗口信息提供者 - 封装 Win32 API 调用"""
import os
from dataclasses import dataclass
from typing import Optional, List, Tuple

try:
    import win32gui
    import win32con
    import win32process
    import psutil
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


@dataclass
class WindowInfo:
    """窗口信息"""
    hwnd: int
    title: str
    rect: Tuple[int, int, int, int]  # (x, y, width, height)
    process_path: str = ""  # 进程路径
    project_name: str = ""  # 项目名称（从进程路径提取）

    # 浏览器标题清理模式
    _BROWSER_MULTI_TAB_PATTERNS = [
        r'\s*-\s*和另外\s*\d+\s*个页面\s*$',  # "和另外 11 个页面"
        r'\s*-\s*and\s+\d+\s+other\s+pages?\s*$',  # "and 11 other pages"
        r'\s*-\s*\d+\s+tabs?\s*$',  # " - 12 tabs" or " - 12 tab"
    ]

    # IP 地址前缀模式（形如 "192.168.1.1 - " 或 "147.0.3912.86 - "）
    _IP_PREFIX_PATTERN = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s*-\s*'

    # 网站名称提取规则（标题前缀 -> 显示名称）
    _SITE_RULES = [
        # 国内网站
        (r'^知乎', '知乎'),
        (r'^Bilibili|^(?!.*b站).*bili', 'Bilibili'),
        (r'^简书', '简书'),
        (r'^CSDN|^(?!.*csdn).*csdn', 'CSDN'),
        (r'^博客园', '博客园'),
        (r'^掘金', '掘金'),
        (r'^微信公众号', '微信公众号'),
        (r'^小红书', '小红书'),
        (r'^微信公众号', '微信公众号'),
        (r'^语雀', '语雀'),
        (r'^飞书', '飞书'),
        (r'^Notion', 'Notion'),
        # 国外网站
        (r'^GitHub', 'GitHub'),
        (r'^Stack Overflow', 'Stack Overflow'),
        (r'^YouTube', 'YouTube'),
        (r'^Twitter|X\.com', 'Twitter/X'),
        (r'^Reddit', 'Reddit'),
        (r'^Medium', 'Medium'),
        (r'^Google', 'Google'),
    ]

    # 浏览器进程名（用于识别浏览器窗口）
    _BROWSER_PROCESSES = {
        'chrome': 'Chrome',
        'msedge': 'Edge',
        'firefox': 'Firefox',
        'brave': 'Brave',
        'opera': 'Opera',
        '360se': '360安全浏览器',
        'liebao': '猎豹浏览器',
    }

    # IDE 进程名
    _IDE_PROCESSES = {
        'pycharm64': 'PyCharm',
        'pycharm': 'PyCharm',
        'idea64': 'IntelliJ IDEA',
        'idea': 'IntelliJ IDEA',
        'code': 'VS Code',
        'code': 'VS Code',
        'cursor': 'Cursor',
        'claude': 'Claude',
    }

    # 笔记软件进程名
    _NOTE_PROCESSES = {
        'obsidian': 'Obsidian',
        'notion': 'Notion',
        'typora': 'Typora',
        'joplin': 'Joplin',
        'logseq': 'Logseq',
    }

    @property
    def x(self) -> int:
        return self.rect[0]

    @property
    def y(self) -> int:
        return self.rect[1]

    @property
    def width(self) -> int:
        return self.rect[2]

    @property
    def height(self) -> int:
        return self.rect[3]

    @property
    def clean_title(self) -> str:
        """清理后的标题，去除浏览器多标签和IP前缀等干扰信息"""
        title = self.title

        # 1. 移除 IP 前缀（如 "147.0.3912.86 - "）
        import re
        title = re.sub(self._IP_PREFIX_PATTERN, '', title)

        # 2. 移除浏览器多标签后缀
        for pattern in self._BROWSER_MULTI_TAB_PATTERNS:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)

        return title.strip()

    def _get_site_name(self) -> str:
        """从标题中提取网站名称（用于浏览器窗口分组）"""
        clean = self.clean_title
        for pattern, site_name in self._SITE_RULES:
            if re.match(pattern, clean, re.IGNORECASE):
                return site_name
        return ""

    def _is_browser(self) -> bool:
        """判断是否为浏览器窗口"""
        if not self.process_path:
            return False
        proc_name = os.path.basename(self.process_path).lower()
        # 移除 .exe 后缀
        proc_name = proc_name.replace('.exe', '')
        return proc_name in self._BROWSER_PROCESSES

    @property
    def display_name(self) -> str:
        """用于显示的名称"""
        clean = self.clean_title

        # 有项目名的（如 IDE 窗口）
        if self.project_name:
            return f"{self.project_name} - {clean}"

        # 浏览器窗口：提取网站名称作为分组标识
        if self._is_browser():
            site = self._get_site_name()
            if site:
                return f"[{site}] {clean}"
            return f"[浏览器] {clean}"

        return clean

    @property
    def group_key(self) -> str:
        """用于分组的键，相同窗口类型会被合并"""
        clean = self.clean_title

        # 有项目名的按项目分组
        if self.project_name:
            return f"project:{self.project_name}"

        # Obsidian: 按保险库(vault)分组
        if self._is_obsidian():
            vault = self._extract_obsidian_vault(clean)
            if vault:
                return f"vault:{vault}"
            return "vault:默认"

        # PyCharm: 按项目分组
        if self._is_pycharm():
            pycharm_project = self._extract_pycharm_project(clean)
            if pycharm_project:
                return f"project:{pycharm_project}"
            return "project:PyCharm"

        # VS Code: 按文件夹/工作区分组
        if self._is_vscode():
            workspace = self._extract_vscode_workspace(clean)
            if workspace:
                return f"workspace:{workspace}"
            return "workspace:默认"

        # 浏览器窗口按网站分组
        if self._is_browser():
            site = self._get_site_name()
            if site:
                return f"site:{site}"
            return "site:other"

        # 其他窗口按清理后的标题分组
        return f"window:{clean}"

    def _is_pycharm(self) -> bool:
        """判断是否为 PyCharm 窗口"""
        if not self.process_path:
            return False
        proc_name = os.path.basename(self.process_path).lower()
        proc_name = proc_name.replace('.exe', '')
        return 'pycharm' in proc_name

    def _is_obsidian(self) -> bool:
        """判断是否为 Obsidian 窗口"""
        if not self.process_path:
            return False
        proc_name = os.path.basename(self.process_path).lower()
        proc_name = proc_name.replace('.exe', '')
        return 'obsidian' in proc_name

    def _is_vscode(self) -> bool:
        """判断是否为 VS Code 窗口"""
        if not self.process_path:
            return False
        proc_name = os.path.basename(self.process_path).lower()
        proc_name = proc_name.replace('.exe', '')
        return 'code' in proc_name and 'cursor' not in proc_name

    def _extract_pycharm_project(self, title: str) -> str:
        """从 PyCharm 标题提取项目名"""
        import re
        # 格式: "文件名.py - 项目名 - PyCharm" 或 "文件名.py - 项目名 - PyCharm Community Edition"
        match = re.match(r'.+\.py\s*-\s*(.+?)\s*-\s*PyCharm', title)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_obsidian_vault(self, title: str) -> str:
        """从 Obsidian 标题提取保险库名"""
        import re
        # 格式: "文件名.md - 保险库名 - Obsidian" 或 "文件名.md - 保险库名"
        match = re.match(r'.+\.md(?:\s*-\s*(.+?))?(?:\s*-\s*Obsidian)?$', title)
        if match and match.group(1):
            return match.group(1).strip()
        return ""

    def _extract_vscode_workspace(self, title: str) -> str:
        """从 VS Code 标题提取工作区名"""
        import re
        # 格式: "文件名 - 工作区名 - VS Code"
        match = re.match(r'.+\s*-\s*(.+?)\s*-\s*VS Code', title)
        if match:
            return match.group(1).strip()
        return ""


class WindowInfoProvider:
    """窗口信息提供者"""

    @staticmethod
    def _extract_project_name(process_path: str, title: str = "") -> str:
        """从进程路径或窗口标题提取项目名称

        常见项目目录模式：
        - W:/a_study/... → a_study
        - C:/Users/.../project/... → project
        - D:/work/xxx-project/... → xxx-project

        窗口标题模式（如 Claude Code）：
        - "项目名 - Claude Code" → 项目名
        """
        # 先尝试从进程路径提取
        if process_path:
            project_name = WindowInfoProvider._extract_from_path(process_path)
            if project_name:
                return project_name

        # 从窗口标题提取（格式如 "项目名 - AppName"）
        if title:
            # 常见应用标题格式："项目名 - 应用名"
            common_suffixes = [
                " - Claude Code",
                " - Cursor",
                " - VS Code",
                " - PyCharm",
                " - 终端",
                " - Windows Terminal",
                " - PowerShell",
                " - cmd",
            ]
            for suffix in common_suffixes:
                if title.endswith(suffix):
                    project = title[:-len(suffix)].strip()
                    # 去掉可能的路径前缀
                    if "/" in project or "\\" in project:
                        project = os.path.basename(project)
                    if project:
                        return project

        return ""

    @staticmethod
    def _extract_from_path(process_path: str) -> str:
        """从进程路径提取项目名称"""
        if not process_path:
            return ""

        # 统一路径分隔符
        normalized = process_path.replace("\\", "/")

        # 系统目录（包含空格的目录名需要完整匹配）
        system_dirs_space = ["program files", "program files (x86)", "onedrive", "icloud", "dropbox"]
        system_dirs_single = ["appdata", "programs", "windows", "system", "system32",
                              "users", "user", "microsoft", "home", "programdata"]

        # 跳过工具/构建目录
        skip_dirs = ["node_modules", ".git", "venv", "env", "__pycache__", "dist", "build",
                     "bin", "obj", "lib", "site-packages", "scripts", "tools",
                     "miniconda", "anaconda", ".venv", "vendor", "target", "include"]

        # 通用目录（返回上一级）
        parent_fallback = {
            "study": True, "study2": True, "学习": True,
            "work": True, "工作": True, "working": True,
            "other": True, "others": True, "repo": True, "repos": True,
            "code": True, "codes": True, "projects": True,
        }

        # 项目特征目录（直接使用）
        project_indicators = ["project", "workspace", "develop", "development"]

        # 分割路径
        parts = normalized.split("/")
        parts = [p for p in parts if p]

        # 检查是否以驱动器名结尾
        def is_drive(name):
            return len(name) <= 2 and name[-1] == ':'

        # 从后往前遍历
        for i in range(len(parts) - 1, -1, -1):
            part = parts[i]
            part_lower = part.lower()

            # 跳过系统目录（完整匹配）
            if any(part_lower == sd for sd in system_dirs_space):
                continue
            if any(sd in part_lower for sd in system_dirs_single):
                continue

            # 跳过工具目录
            if any(sd in part_lower for sd in skip_dirs):
                continue

            # 如果是直接可执行文件，跳过
            ext = part.rsplit('.', 1)[-1].lower() if '.' in part else ''
            if ext in ['exe', 'dll', 'bat', 'cmd', 'msi']:
                continue

            # 检查项目特征目录
            if any(pi in part_lower for pi in project_indicators):
                return part

            # 检查是否需要返回上一级（仅当父目录存在且有意义时）
            if part_lower in parent_fallback and i > 0:
                parent = parts[i - 1]
                parent_lower = parent.lower()
                # 确保父目录不是系统目录或跳过目录
                if not any(parent_lower == sd for sd in system_dirs_space):
                    if not any(sd in parent_lower for sd in system_dirs_single + skip_dirs):
                        # 再次检查祖父目录是否也需要返回上一级
                        if parent_lower in parent_fallback and i > 1:
                            grandparent = parts[i - 2]
                            gp_lower = grandparent.lower()
                            if not any(gp_lower == sd for sd in system_dirs_space):
                                if not any(sd in gp_lower for sd in system_dirs_single + skip_dirs):
                                    return grandparent
                            return grandparent if not any(gp_lower == sd or sd in gp_lower for sd in system_dirs_single + skip_dirs + list(parent_fallback.keys())) else parent
                        return parent

            # 如果是 src/common/lib/include 目录，返回上一级
            if part_lower in ["src", "common", "lib", "include"] and i > 0:
                parent = parts[i - 1]
                parent_lower = parent.lower()
                if not any(parent_lower == sd for sd in system_dirs_space):
                    if not any(sd in parent_lower for sd in system_dirs_single + skip_dirs):
                        return parent

            # 找到第一个有意义的目录（不是驱动器名）
            if not is_drive(part):
                return part

        return ""

    @staticmethod
    def _get_process_info(hwnd: int) -> Tuple[str, str]:
        """获取进程路径和项目名称

        Returns:
            (process_path, project_name)
        """
        try:
            # 获取进程 ID
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            # 使用 psutil 获取进程信息
            try:
                process = psutil.Process(pid)
                process_path = process.exe()
                process_name = os.path.basename(process_path).lower()

                # 方法1: 从进程命令行参数提取项目路径
                # 支持多种终端应用：Windows Terminal, VS Code, Claude Code CLI 等
                try:
                    cmdline = process.cmdline()
                    # 检查是否是 Windows Terminal
                    if 'windowsterminal' in process_name or 'wt.exe' in process_name:
                        # Windows Terminal 使用 -d 参数指定目录
                        for i, arg in enumerate(cmdline):
                            if arg == '-d' and i + 1 < len(cmdline):
                                project_dir = cmdline[i + 1]
                                project_name = WindowInfoProvider._extract_from_path(project_dir)
                                if project_name:
                                    return process_path, project_name
                            # 也支持 --startingDirectory
                            elif arg.startswith('--startingDirectory='):
                                project_dir = arg.split('=', 1)[1]
                                project_name = WindowInfoProvider._extract_from_path(project_dir)
                                if project_name:
                                    return process_path, project_name
                    # Claude Code CLI
                    elif 'claude' in process_name and '.exe' in process_name:
                        for arg in cmdline[1:]:
                            if arg and os.path.isdir(arg):
                                project_name = WindowInfoProvider._extract_from_path(arg)
                                if project_name:
                                    return process_path, project_name
                    # VS Code
                    elif 'code.exe' in process_name.lower():
                        for arg in cmdline[1:]:
                            if arg and os.path.isdir(arg):
                                project_name = WindowInfoProvider._extract_from_path(arg)
                                if project_name:
                                    return process_path, project_name
                    # 其他进程：检查是否是有效目录
                    else:
                        for arg in cmdline[1:]:
                            if arg and os.path.isdir(arg):
                                project_name = WindowInfoProvider._extract_from_path(arg)
                                if project_name:
                                    return process_path, project_name
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass

                # 方法2: 从工作目录提取项目名
                try:
                    cwd = process.cwd()
                    if cwd and os.path.isdir(cwd):
                        project_name = WindowInfoProvider._extract_from_path(cwd)
                        if project_name:
                            return process_path, project_name
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass

                # 方法3: 从进程路径提取项目名称
                project_name = WindowInfoProvider._extract_project_name(process_path)

                return process_path, project_name
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return "", ""
        except Exception:
            return "", ""

    @staticmethod
    def get_foreground_window() -> Optional[WindowInfo]:
        """获取前台窗口信息"""
        if not WIN32_AVAILABLE:
            return None

        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            # 检查窗口有效性
            if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
                return None
            if win32gui.IsIconic(hwnd):  # 最小化窗口
                return None

            # 获取客户区尺寸
            client_rect = win32gui.GetClientRect(hwnd)
            client_w, client_h = client_rect[2], client_rect[3]

            # 最小窗口尺寸限制
            if client_w < 100 or client_h < 100:
                return None

            # 使用 ClientToScreen 获取客户区左上角的屏幕坐标
            client_top_left = win32gui.ClientToScreen(hwnd, (0, 0))
            client_x, client_y = client_top_left[0], client_top_left[1]

            try:
                title = win32gui.GetWindowText(hwnd)
                # 确保 title 是有效的 Unicode 字符串，处理编码问题
                if isinstance(title, bytes):
                    title = title.decode('gbk', errors='replace')
                else:
                    title = str(title)
            except Exception:
                title = ""

            if not title:
                return None

            # 获取进程信息和项目名称（优先从路径提取，再从标题提取）
            process_path, project_name = WindowInfoProvider._get_process_info(hwnd)
            if not project_name:
                project_name = WindowInfoProvider._extract_project_name("", title)

            return WindowInfo(
                hwnd=hwnd,
                title=title,
                rect=(client_x, client_y, client_w, client_h),
                process_path=process_path,
                project_name=project_name
            )

        except Exception:
            return None

    @staticmethod
    def get_all_windows() -> List[WindowInfo]:
        """获取所有可见窗口"""
        if not WIN32_AVAILABLE:
            return []

        windows = []

        def enum_cb(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            try:
                title = win32gui.GetWindowText(hwnd)
                if isinstance(title, bytes):
                    title = title.decode('gbk', errors='replace')
                else:
                    title = str(title)
            except Exception:
                title = ""
            if not title:
                return True
            rect = win32gui.GetWindowRect(hwnd)
            w, h = rect[2] - rect[0], rect[3] - rect[1]
            if w < 50 or h < 50:
                return True
            windows.append(WindowInfo(hwnd=hwnd, title=title, rect=(rect[0], rect[1], w, h)))
            return True

        win32gui.EnumWindows(enum_cb, None)
        return windows

    @staticmethod
    def get_taskbar_rect() -> Optional[Tuple[int, int, int, int]]:
        """获取任务栏区域"""
        if not WIN32_AVAILABLE:
            return None

        try:
            hwnd = win32gui.FindWindow("Shell_TrayWnd", None)
            if not hwnd:
                return None

            rect = win32gui.GetWindowRect(hwnd)
            return (rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
        except Exception:
            return None

    @staticmethod
    def get_title_bar_rect(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
        """获取标题栏区域"""
        if not WIN32_AVAILABLE:
            return None

        try:
            if not win32gui.IsWindow(hwnd):
                return None

            # 获取窗口矩形
            window_rect = win32gui.GetWindowRect(hwnd)
            wx, wy, wx2, wy2 = window_rect
            ww, wh = wx2 - wx, wy2 - wy

            # 获取客户区矩形
            client_rect = win32gui.GetClientRect(hwnd)
            cw, ch = client_rect[2], client_rect[3]

            # 获取客户区左上角在屏幕上的坐标
            client_top_left = win32gui.ClientToScreen(hwnd, (0, 0))
            cx, cy = client_top_left[0], client_top_left[1]

            # 标题栏高度 = (窗口顶部到客户区顶部) + (窗口左边到客户区左边)
            # 这里使用窗口高度减去客户区高度估算
            border_height = cy - wy

            # 标题栏区域: 从窗口顶部到客户区顶部
            title_x = wx
            title_y = wy
            title_w = ww
            title_h = border_height + 5  # 加上一点边框

            return (title_x, title_y, title_w, title_h)
        except Exception:
            return None

    @staticmethod
    def is_fullscreen_window(hwnd: int) -> bool:
        """检测是否为全屏窗口"""
        if not WIN32_AVAILABLE:
            return False

        try:
            if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
                return False

            # 获取窗口矩形
            window_rect = win32gui.GetWindowRect(hwnd)
            wx, wy, wx2, wy2 = window_rect

            # 获取屏幕大小
            screen_x = win32gui.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
            screen_y = win32gui.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
            screen_w = win32gui.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
            screen_h = win32gui.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)

            # 检查窗口是否占满整个屏幕（允许小误差）
            tolerance = 5
            return (
                abs(wx - screen_x) < tolerance and
                abs(wy - screen_y) < tolerance and
                abs(wx2 - (screen_x + screen_w)) < tolerance and
                abs(wy2 - (screen_y + screen_h)) < tolerance
            )
        except Exception:
            return False