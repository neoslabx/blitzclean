#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Import libraries
import json
import os
import queue
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import stat
import signal
import time

# Import packages
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtWidgets import QComboBox
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QDialogButtonBox
from PyQt6.QtWidgets import QFormLayout
from PyQt6.QtWidgets import QGroupBox
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtWidgets import QMenuBar
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QProgressBar
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QScrollArea
from PyQt6.QtWidgets import QSpinBox
from PyQt6.QtWidgets import QTableWidget
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtWidgets import QTabWidget
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

# Define 'VERSION'
VERSION = "v4.9.1"

# Define 'WEBSITEURL'
WEBSITEURL = "https://neoslab.com/"

# Define 'CONFIGPATH'
CONFIGPATH = Path.home() / ".config" / "blitzclean"

# Define 'CONFIGFILE'
CONFIGFILE = CONFIGPATH / "config"

# Define 'USERPATH'
USERPATH = [
    ".cache/babl",
    ".cache/discord",
    ".cache/easytag",
    ".cache/fontconfig",
    ".cache/gimp",
    ".cache/JetBrains",
    ".cache/keepassxc",
    ".cache/mesa_shader_cache",
    ".cache/Microsoft",
    ".cache/npm",
    ".cache/obexd",
    ".cache/pip",
    ".cache/pnpm",
    ".cache/shotwell",
    ".cache/shutter",
    ".cache/sublime-text",
    ".cache/thumbnails",
    ".cache/thunderbird",
    ".cache/totem",
    ".cache/tracker3",
    ".cache/ubuntu-report",
    ".cache/vscode",
    ".cache/yarn",
    ".config/Code/Cache",
    ".config/Code/CachedData",
    ".config/Code/logs",
    ".config/discord/Cache",
    ".config/discord/Code Cache",
    ".profile.bak",
    ".shell.pre-oh-my-zsh",
    ".shutter",
    ".thumbnails",
    ".wget-hsts",
    ".zcompdump",
    ".zshrc.bak"
]

# Define 'USERDEEP'
USERDEEP = [
    "snap",
    ".ssh"
]

# Define 'USERPATTERN'
USERPATTERN = [
    ".cache/chromium",
    ".cache/google-chrome",
    ".config/BraveSoftware/Brave-Browser/Default/Cache",
    ".config/BraveSoftware/Brave-Browser/Default/Code Cache",
    ".config/chromium/Default/Cache",
    ".config/chromium/Default/Code Cache",
    ".config/google-chrome",
    ".mozilla/firefox/*/cache2",
    ".mozilla/firefox/*/startupCache",
    ".zcompdump-*",
    "~/.var/app/*/cache"
]

# Define 'USERHISTORY'
USERHISTORY = [
    ".bash_history",
    ".cache/recently-used.xbel",
    ".local/share/RecentDocuments",
    ".local/share/recently-used.xbel",
    ".zsh_history"
]

# Define 'ROOTITEMS'
ROOTITEMS = [
    "/root/.cache",
    "/root/.config",
    "/root/.history",
    "/root/.launchpadlib",
    "/root/.wget-hsts"
]

# Define 'SYSDIRS'
SYSDIRS = [
    "/tmp",
    "/var/cache/fontconfig",
    "/var/cache/man",
    "/var/lib/snapd/cache",
    "/var/lib/systemd/coredump",
    "/var/tmp"
]

# Define 'SYSGLOBS'
SYSGLOBS = [
    ("/var/crash", "*.crash"),
    ("/var/log", "*.gz"),
    ("/var/log", "*.[0-9]")
]

# Define 'FileRowCB'
FileRowCB = Callable[[str, int, str], None]


# Class 'SysUtils'
class SysUtils:
    """
    Collection of static utility helpers for filesystem and system information.
    Provides size formatting, free space queries, mtime formatting, and size calculation.
    Centralized helpers keep logic consistent and reusable across the app.
    """

    # Function 'rootcheck'
    @staticmethod
    def rootcheck() -> bool:
        """
        Determine whether the current process is running as the root user.
        Used to decide if system-wide cleanup operations are permitted.
        Returns True when effective UID is 0; otherwise False.
        """
        return os.geteuid() == 0

    # Function 'unitsize'
    @staticmethod
    def unitsize(numbytes: int) -> str:
        """
        Convert a raw byte count into a human-readable string with units.
        Iteratively scales in powers of 1024 through KB, MB, GB, etc.
        Always returns a string like '12.34 MB' even on invalid input.
        """
        try:
            n = max(0, int(numbytes))
        except (ValueError, TypeError):
            n = 0
        units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
        i = 0
        x = float(n)
        while x >= 1024 and i < len(units) - 1:
            x /= 1024.0
            i += 1
        return f"{x:.2f} {units[i]}"

    # Function 'timestring'
    @staticmethod
    def timestring(p: Path) -> str:
        """
        Format a path's modification time into a YYYY-MM-DD HH:MM:SS string.
        Returns '-' on error or when the timestamp cannot be read.
        Useful for presenting file information in the UI table.
        """
        try:
            return datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except (OSError, ValueError, PermissionError, FileNotFoundError):
            return "-"

    # Function 'filesize'
    @staticmethod
    def filesize(p: Path) -> int:
        """
        Compute size in bytes for a file, or shallow total for a directory.
        For directories it sums direct children file sizes and ignores errors.
        Returns 0 when size cannot be determined or the path is missing.
        """
        try:
            if p.is_file():
                return p.stat().st_size
            if p.is_dir():
                total = 0
                for child in p.iterdir():
                    try:
                        if child.is_file():
                            total += child.stat().st_size
                    except (OSError, PermissionError, FileNotFoundError):
                        pass
                return total
        except (OSError, PermissionError, FileNotFoundError):
            pass
        return 0


# Class 'ShellExec'
class ShellExec:
    """
    Thin wrapper around subprocess helpers for executing shell commands.
    Provides streaming run and capture utilities with simple error handling.
    Keeps command execution details isolated from the business logic.
    """

    # Function 'cmdrun'
    @staticmethod
    def cmdrun(cmd: str, dryrun: bool) -> int:
        """
        Execute a shell command, optionally skipping when in dry-run mode.
        Streams stdout lines to avoid buffering, returning the exit code.
        Any subprocess errors produce a non-zero (1) return value.
        """
        if dryrun:
            return 0
        try:
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for _ in iter(proc.stdout.readline, ""):
                pass
            proc.wait()
            return proc.returncode
        except (OSError, subprocess.SubprocessError):
            return 1

    # Function 'capture'
    @staticmethod
    def capture(cmd: str) -> Tuple[int, str]:
        """
        Run a command and capture combined stdout/stderr as text.
        Returns a tuple of (exit_code, output) for downstream parsing.
        On failure, exit_code is non-zero and output contains the error.
        """
        try:
            out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
            return 0, out
        except subprocess.CalledProcessError as e:
            return e.returncode, e.output
        except (OSError, subprocess.SubprocessError) as e:
            return 1, str(e)

    # Function 'userexec'
    @staticmethod
    def userexec(username: str, home: str, cmd: str, dryrun: bool) -> int:
        """
        Execute a command as a specific user (used for 'trash-empty').
        Tries runuser/sudo/su fallbacks. Ensures HOME is set for the target.
        Returns the exit code (0 on success). In dry-run, returns 0.
        """
        if dryrun:
            return 0
        env_prefix = f"HOME={shlex.quote(home)} XDG_DATA_HOME={shlex.quote(os.path.join(home, '.local/share'))} "
        try:
            current = os.environ.get("SUDO_USER") or os.environ.get("USER") or ""
            if os.geteuid() != 0 or current == username:
                return ShellExec.cmdrun(env_prefix + cmd, dryrun=False)
        except (OSError, AttributeError):
            pass

        attempts = [
            f"runuser -u {shlex.quote(username)} -- sh -lc {shlex.quote(env_prefix + cmd)}",
            f"sudo -u {shlex.quote(username)} sh -lc {shlex.quote(env_prefix + cmd)}",
            f"su -s /bin/sh -c {shlex.quote(env_prefix + cmd)} {shlex.quote(username)}",
        ]

        for c in attempts:
            rc = ShellExec.cmdrun(c, dryrun=False)
            if rc == 0:
                return 0
        return 1


# Class 'ProcessManager'
class ProcessManager:
    """
    Best-effort helper to gracefully close user applications before cleaning.
    It sends SIGTERM to most user processes (excluding this app and a small
    safeguard list) and, after a grace period, SIGKILL to stubborn ones.
    """

    # Function 'closeprograms'
    @staticmethod
    def closeprograms(username: str, excludepids: Optional[set] = None, gracesecs: int = 5) -> None:
        """
        Attempt to close all processes for 'username' except those in excludepids
        and a conservative skiplist. Uses 'ps' to enumerate processes and 'os.kill'
        for signaling. Errors are tolerated to avoid crashing the GUI.
        """
        if not username:
            return

        skipnames = {
            "dbus-daemon",
            "gnome-shell",
            "kwin_wayland",
            "kwin_x11",
            "loginctl",
            "pipewire",
            "pipewire-media-session",
            "plasmashell",
            "pulseaudio",
            "python",
            "python3",
            "systemd",
            "wireplumber",
            "Xorg",
            "Xwayland"
        }
        if excludepids is None:
            excludepids = set()
        excludepids.add(os.getpid())
        ec, out = ShellExec.capture(f"ps -u {shlex.quote(username)} -o pid=,comm=")
        if ec != 0 or not out.strip():
            return

        candidates: List[int] = []
        for line in out.splitlines():
            try:
                pstr, comm = line.strip().split(None, 1)
                pid = int(pstr)
                comm = os.path.basename(comm)
            except (ValueError, IndexError):
                continue
            if pid in excludepids:
                continue
            if comm in skipnames:
                continue
            if pid == os.getppid():
                continue
            candidates.append(pid)

        for pid in candidates:
            try:
                os.kill(pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass

        time.sleep(max(0, int(gracesecs)))
        for pid in candidates:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                continue
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass


# Class 'ExecOpts'
@dataclass
class ExecOpts:
    """
    Execution options controlling behavior of cleanup operations.
    Encapsulates dry-run, browser/kernel flags, journal limits, and targets.
    Instances serialize to/from dict for config persistence and IPC.
    """

    # Define 'dryrun'
    dryrun: bool = False

    # Define 'clearbrowsers'
    clearbrowsers: bool = False

    # Define 'clearkernels'
    clearkernels: bool = False

    # Define 'vacuumdays'
    vacuumdays: int = 7

    # Define 'vacuumsize'
    vacuumsize: str = "100M"

    # Define 'keepsnaps'
    keepsnaps: int = 2

    # Define 'shutafter'
    shutafter: bool = False

    # Define 'username'
    username: str = ""

    # Define 'userhome'
    userhome: str = ""

    # Define 'aggressive'
    aggressive: bool = False

    # Function 'todict'
    def todict(self) -> dict:
        """
        Convert this ExecOpts instance into a plain serializable dict.
        Used for saving preferences and passing to elevated workers.
        Returns a dict with primitive types suitable for JSON.
        """
        return {
            "dryrun": self.dryrun,
            "clearbrowsers": self.clearbrowsers,
            "clearkernels": self.clearkernels,
            "vacuumdays": self.vacuumdays,
            "vacuumsize": self.vacuumsize,
            "keepsnaps": self.keepsnaps,
            "shutafter": self.shutafter,
            "username": self.username,
            "userhome": self.userhome,
            "aggressive": self.aggressive,
        }

    # Function 'fromdict'
    @staticmethod
    def fromdict(d: dict) -> "ExecOpts":
        """
        Build an ExecOpts instance from a dictionary of values.
        Applies sensible defaults and coerces types for robustness.
        Returns a new ExecOpts configured by the provided mapping.
        """
        return ExecOpts(
            dryrun=bool(d.get("dryrun", False)),
            clearbrowsers=bool(d.get("clearbrowsers", False)),
            clearkernels=bool(d.get("clearkernels", False)),
            vacuumdays=int(d.get("vacuumdays", 7)),
            vacuumsize=str(d.get("vacuumsize", "100M")),
            keepsnaps=int(d.get("keepsnaps", 2)),
            shutafter=bool(d.get("shutafter", False)),
            username=str(d.get("username", "")),
            userhome=str(d.get("userhome", "")),
            aggressive=bool(d.get("aggressive", False)),
        )


# Class 'ConfigManager'
class ConfigManager:
    """
    Read/write helper for the simple key=value configuration file.
    Loads user preferences on startup and persists updates when changed.
    Hides filesystem details and error handling behind a clean API.
    """

    # Function 'load'
    @staticmethod
    def load() -> dict:
        """
        Load configuration from CONFIGFILE into a dict of strings.
        Ignores comments/blank lines and safely handles decoding errors.
        Returns an empty dict when no config exists or on failure.
        """
        data: Dict[str, str] = {}
        try:
            if CONFIGFILE.is_file():
                for line in CONFIGFILE.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    data[k.strip()] = v.strip()
        except (OSError, UnicodeDecodeError):
            pass
        return data

    # Function 'save'
    @staticmethod
    def save(opts: ExecOpts, runbootstart: bool, runshutdown: bool, pathopts: Dict[str, bool]):
        """
        Persist ExecOpts, scheduler flags, and per-path options to disk.
        Writes a simple key=value file under ~/.config/blitzclean/config.
        Silently ignores filesystem errors to avoid crashing the UI.
        """
        try:
            CONFIGPATH.mkdir(parents=True, exist_ok=True)
            lines = [
                f"dryrun={'1' if opts.dryrun else '0'}",
                f"clearbrowsers={'1' if opts.clearbrowsers else '0'}",
                f"clearkernels={'1' if opts.clearkernels else '0'}",
                f"vacuumdays={opts.vacuumdays}",
                f"vacuumsize={opts.vacuumsize}",
                f"keepsnaps={opts.keepsnaps}",
                f"shutafter={'1' if opts.shutafter else '0'}",
                f"username={opts.username}",
                f"userhome={opts.userhome}",
                f"runbootstart={'1' if runbootstart else '0'}",
                f"runshutdown={'1' if runshutdown else '0'}",
                f"aggressive={'1' if opts.aggressive else '0'}",
            ]

            for k, v in sorted(pathopts.items()):
                lines.append(f"options.{k}={'1' if v else '0'}")
            CONFIGFILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

        except OSError:
            pass


# Class 'UserDiscovery'
class UserDiscovery:
    """
    Utilities to discover local users and their home directories.
    Enumerates /root and /home/*, prioritizing the current user first.
    Used to populate the target user selector in the GUI.
    """

    # Function 'listusers'
    @staticmethod
    def listusers() -> List[Tuple[str, str]]:
        """
        Return a list of (username, home_path) tuples available on the system.
        Includes 'root' if /root exists and all subdirectories under /home.
        Sorts with the current user first to improve default selection.
        """
        users: List[Tuple[str, str]] = []
        if os.path.isdir("/root"):
            users.append(("root", "/root"))
        homedir = Path("/home")

        if homedir.is_dir():
            for child in sorted(homedir.iterdir()):
                if child.is_dir():
                    users.append((child.name, str(child)))

        current = os.environ.get("SUDO_USER") or os.environ.get("USER") or ""
        users.sort(key=lambda t: (t[0] != current, t[0]))
        return users


# Class 'FileOps'
class FileOps:
    """
    Filesystem operations for deleting, wiping, and enumerating paths.
    Emits rows through a callback so the UI can display progress.
    Provides safe, error-tolerant helpers for recursive operations.
    """

    # Function 'emitrow'
    @staticmethod
    def emitrow(cb: FileRowCB, p: Path):
        """
        Produce a single table row for the given path via callback.
        Computes size and mtime string before invoking the callback.
        Keeps UI updates decoupled from filesystem traversal logic.
        """
        size = SysUtils.filesize(p)
        mtime = SysUtils.timestring(p)
        cb(str(p), size, mtime)

    # Function 'removefile'
    @staticmethod
    def removefile(path: Path, dryrun: bool, cb: FileRowCB) -> int:
        """
        Delete a file or directory path and report reclaimed bytes.
        Honors dry-run mode and emits a row before removal attempts.
        Returns the estimated size removed; errors are swallowed safely.
        """
        try:
            if not path.exists():
                return 0
            FileOps.emitrow(cb, path)
            size = path.stat().st_size if path.is_file() else 0

            if dryrun:
                return size
            try:
                if path.is_file() or stat.S_ISLNK(path.stat().st_mode):
                    path.unlink(missing_ok=True)
                else:
                    shutil.rmtree(path, ignore_errors=True)
                    size = 0

            except IsADirectoryError:
                shutil.rmtree(path, ignore_errors=True)
                size = 0
            except PermissionError:
                ShellExec.cmdrun(f"rm -f {shlex.quote(str(path))}", dryrun=False)
            return size
        except (OSError, PermissionError, FileNotFoundError):
            return 0

    # Function 'removetree'
    @staticmethod
    def removetree(path: Path, dryrun: bool, cb: FileRowCB) -> int:
        """
        Recursively remove a directory tree and sum contained file sizes.
        Emits rows for the parent and all children to show detailed progress.
        Returns the total size estimate; respects dry-run mode.
        """
        try:
            if not path.exists():
                return 0
            total = 0

            for p in path.rglob("*"):
                try:
                    if p.is_file():
                        total += p.stat().st_size
                except (OSError, PermissionError, FileNotFoundError):
                    pass

            FileOps.emitrow(cb, path)
            for p in path.rglob("*"):
                FileOps.emitrow(cb, p)
            if dryrun:
                return total
            shutil.rmtree(path, ignore_errors=True)
            return total
        except (OSError, PermissionError, FileNotFoundError):
            return 0

    # Function 'wipedir'
    @staticmethod
    def wipedir(path: Path, dryrun: bool, cb: FileRowCB) -> int:
        """
        Remove all children of a directory without deleting the directory itself.
        Iterates files and subfolders, using removefile/removetree as needed.
        Returns total estimated bytes affected; tolerates filesystem errors.
        """
        if not path.exists() or not path.is_dir():
            return 0
        total = 0
        try:
            for item in path.iterdir():
                if item.is_dir():
                    total += FileOps.removetree(item, dryrun, cb)
                else:
                    total += FileOps.removefile(item, dryrun, cb)
            return total
        except (OSError, PermissionError, FileNotFoundError):
            return 0

    # Function 'globdel'
    @staticmethod
    def globdel(dirpath: Path, pattern: str, dryrun: bool, cb: FileRowCB) -> int:
        """
        Delete files matching a glob-like pattern under a base directory.
        Emits rows for matched paths and honors dry-run for safety.
        Returns the total estimated bytes removed or 0 on failure.
        """
        if not dirpath.exists() or not dirpath.is_dir():
            return 0
        total = 0
        try:
            for p in dirpath.rglob(pattern):
                if p.is_file():
                    total += FileOps.removefile(p, dryrun, cb)
                elif dryrun and p.is_dir():
                    FileOps.emitrow(cb, p)
            return total
        except (OSError, PermissionError, FileNotFoundError):
            return 0


# Class 'SysCleaner'
class SysCleaner:
    """
    Core cleanup engine orchestrating user and system deletions.
    Walks configured paths, honors options, and reports progress via callback.
    Supports cancellation and tallies total reclaimed bytes.
    """

    # Function '__init__'
    def __init__(self, opts: ExecOpts, filecb: FileRowCB, pathopts: Dict[str, bool]):
        """
        Initialize a SysCleaner with execution options and UI callback.
        Stores path enable/disable map and prepares byte counters/state.
        Does not start work until run() is invoked.
        """
        self.opts = opts
        self.filecb = filecb
        self.pathopts = pathopts
        self.totalbytes = 0
        self.frontroot = 0
        self.fronthome = 0
        self.backroot = 0
        self.backhome = 0
        self.stopflag = False

    # Function 'loadstop'
    def loadstop(self):
        """
        Request that the running cleanup operation be cancelled.
        Sets an internal flag checked periodically during traversal.
        Long-running operations exit gracefully by raising at checkpoints.
        """
        self.stopflag = True

    # Function 'checkstop'
    def checkstop(self):
        """
        Guard method to abort work when a stop request has been made.
        Raises RuntimeError to unwind current operation safely.
        Call frequently inside loops to keep UI responsive.
        """
        if self.stopflag:
            raise RuntimeError("Operation cancelled by user.")

    # Function 'addbytes'
    def addbytes(self, n: int):
        """
        Add a byte count to the running total with defensive casting.
        Ignores invalid or overflow inputs to keep counters robust.
        Used by file operations to accumulate reclaimed sizes.
        """
        try:
            self.totalbytes += int(n)
        except (ValueError, TypeError, OverflowError):
            pass

    # Function 'enabled'
    def enabled(self, key: str) -> bool:
        """
        Check if a given logical path key is enabled for cleaning.
        Reads from the per-path options map provided by preferences.
        Returns True when enabled or missing (defaults to enabled).
        """
        return self.pathopts.get(key, True)

    # Function 'sumtree'
    @staticmethod
    def sumtree(p: Path) -> int:
        """
        Recursively sum file sizes under path p without emitting rows.
        Returns total bytes; tolerates permission/file-not-found errors.
        Does not follow directory symlinks during traversal.
        """
        total = 0
        try:
            if p.is_file():
                return p.stat().st_size
            if p.is_dir():
                for root, _, files in os.walk(p, onerror=lambda e: None):
                    for fn in files:
                        try:
                            total += Path(root, fn).stat().st_size
                        except (OSError, PermissionError, FileNotFoundError):
                            pass
        except (OSError, PermissionError, FileNotFoundError):
            pass
        return total

    # Function 'trashlist'
    def trashlist(self, username: str, home: str):
        """
        List items in user's Trash and then empty it using 'trash-empty'.
        This emits a row per top-level trash item and adds their sizes
        to the reclaimed bytes counter before actually emptying.
        """
        trash_dir = Path(home) / ".local/share/Trash/files"
        if trash_dir.is_dir():
            try:
                for child in sorted(trash_dir.iterdir()):
                    self.checkstop()
                    size = self.sumtree(child)
                    mtime = SysUtils.timestring(child)
                    self.filecb(str(child), size, mtime)  # list it
                    self.addbytes(size)
            except (OSError, PermissionError, FileNotFoundError):
                pass

        ShellExec.userexec(username=username, home=home, cmd="trash-empty", dryrun=self.opts.dryrun)

    # Function 'useritem'
    def useritem(self, uh: Path, rel: str):
        """
        Clean a user-relative path (file or directory) if enabled.
        Expands and dispatches to wipe or remove operations as needed.
        Accumulates reclaimed bytes and emits progress rows.
        """
        if not self.enabled(rel):
            return
        p = (uh / rel).expanduser()
        if p.is_dir():
            if rel in USERDEEP or rel.startswith(".cache/"):
                self.addbytes(FileOps.removetree(p, self.opts.dryrun, self.filecb))
            else:
                self.addbytes(FileOps.wipedir(p, self.opts.dryrun, self.filecb))
        else:
            self.addbytes(FileOps.removefile(p, self.opts.dryrun, self.filecb))

    # Function 'userpattern'
    def userpattern(self, uh: Path, pat: str):
        """
        Resolve and clean pattern-based user paths (including wildcards).
        Supports '*', '/*/' segments, and '~' home expansion cases.
        Applies appropriate remove/wipe semantics and sums reclaimed bytes.
        """
        if not self.enabled(pat):
            return
        if pat.startswith("~"):
            base = Path(os.path.expanduser("~"))
            pattern = pat.replace("~/", "")
        else:
            base = uh
            pattern = pat

        if "/*/" in pattern:
            pre, post = pattern.split("/*/", 1)
            basedir = base / pre
            if basedir.is_dir():
                for child in basedir.iterdir():
                    if child.is_dir():
                        tpath = child / post
                        if tpath.exists():
                            if tpath.is_dir():
                                self.addbytes(FileOps.wipedir(tpath, self.opts.dryrun, self.filecb))
                            else:
                                self.addbytes(FileOps.removefile(tpath, self.opts.dryrun, self.filecb))
        elif "*" in pattern:
            prefix, suffix = pattern.split("*", 1)
            dirpart = Path(prefix).parent
            namepre = Path(prefix).name
            basedir = base / dirpart
            if basedir.is_dir():
                for child in basedir.iterdir():
                    if child.name.startswith(namepre) and child.name.endswith(suffix):
                        self.addbytes(FileOps.removefile(child, self.opts.dryrun, self.filecb))
        else:
            t = base / pattern
            if t.exists():
                if t.is_dir():
                    self.addbytes(FileOps.wipedir(t, self.opts.dryrun, self.filecb))
                else:
                    self.addbytes(FileOps.removefile(t, self.opts.dryrun, self.filecb))

    # Function 'cleanupuser'
    def cleanupuser(self, uh: Path):
        """
        Perform all configured user-space cleanup operations for a home path.
        Iterates USERPATH, USERHISTORY, USERPATTERN, and USERDEEP.
        Periodically checks for cancellation and updates byte totals.
        Also lists and empties the user's Trash using 'trash-empty'.
        """
        username = Path(uh).name if str(uh) != "/root" else "root"
        self.trashlist(username=username, home=str(uh))

        for rel in USERPATH:
            self.checkstop()
            self.useritem(uh, rel)
        for rel in USERHISTORY:
            self.checkstop()
            self.useritem(uh, rel)
        for pat in USERPATTERN:
            self.checkstop()
            self.userpattern(uh, pat)
        for rel in USERDEEP:
            self.checkstop()
            self.useritem(uh, rel)

    # Function 'cleanupsystem'
    def cleanupsystem(self):
        """
        Perform system-wide cleanup tasks requiring root when available.
        Wipes caches, trims logs, removes snaps, and prunes old kernels.
        Respects dry-run and per-path enablement; emits progress rows.
        """
        if not SysUtils.rootcheck():
            return

        for d in SYSDIRS:
            if not self.enabled(d):
                continue
            self.checkstop()
            self.addbytes(FileOps.wipedir(Path(d), self.opts.dryrun, self.filecb))

        for base, pat in SYSGLOBS:
            key = f"{base}::{pat}"
            if not self.enabled(key):
                continue
            self.checkstop()
            self.addbytes(FileOps.globdel(Path(base), pat, self.opts.dryrun, self.filecb))

        ShellExec.cmdrun(f"journalctl --vacuum-time={self.opts.vacuumdays}d", self.opts.dryrun)
        ShellExec.cmdrun(f"journalctl --vacuum-size={self.opts.vacuumsize}", self.opts.dryrun)
        ShellExec.cmdrun(f"snap set system refresh.retain={self.opts.keepsnaps}", self.opts.dryrun)
        ShellExec.cmdrun("apt-get -y autoremove --purge", self.opts.dryrun)
        ShellExec.cmdrun("apt-get -y autoclean", self.opts.dryrun)
        ShellExec.cmdrun("apt-get -y clean", self.opts.dryrun)
        ShellExec.cmdrun("flatpak uninstall --unused -y", self.opts.dryrun)

        if not self.opts.dryrun:
            cmd = r"snap list --all 2>/dev/null | awk '/disabled/ {print $1, $3}'"
            ec, out = ShellExec.capture(cmd)
            if ec == 0 and out.strip():
                for line in out.strip().splitlines():
                    parts = line.split()
                    if len(parts) == 2:
                        name, rev = parts
                        ShellExec.cmdrun(f"snap remove --revision={shlex.quote(rev)} {shlex.quote(name)} --purge", False)

        if self.opts.clearkernels:
            currentkernel = self.kernelused()
            pkgs = self.kernelold(currentkernel)
            for pkg in pkgs:
                ShellExec.cmdrun(f"apt-get remove --purge -y {shlex.quote(pkg)}", self.opts.dryrun)
            ShellExec.cmdrun("update-grub", self.opts.dryrun)

        for p in ROOTITEMS:
            if not self.enabled(p):
                continue
            self.checkstop()
            rp = Path(p)
            if rp.is_dir():
                self.addbytes(FileOps.wipedir(rp, self.opts.dryrun, self.filecb))
            else:
                self.addbytes(FileOps.removefile(rp, self.opts.dryrun, self.filecb))

    # Function 'kernelused'
    @staticmethod
    def kernelused() -> str:
        """
        Return the current kernel version string without the '-generic' suffix.
        Used to identify which linux-image packages must be preserved.
        Falls back to empty string on execution or parsing errors.
        """
        ec, out = ShellExec.capture("uname -r | sed 's/-generic//'")
        return out.strip() if ec == 0 else ""

    # Function 'kernelold'
    @staticmethod
    def kernelold(basekernel: str) -> List[str]:
        """
        List installed linux-image packages excluding the active kernel.
        Parses dpkg output and filters by the provided current version.
        Returns a list of package names safe to purge if desired.
        """
        ec, out = ShellExec.capture("dpkg -l | awk '/^ii\\s+linux-image-[0-9]/{print $2}'")
        pkgs: List[str] = []
        if ec == 0:
            for line in out.strip().splitlines():
                if basekernel and basekernel in line:
                    continue
                pkgs.append(line.strip())
        return pkgs

    # Function 'run'
    def run(self):
        """
        Execute the full cleanup routine according to options and privileges.
        Cleans each user's home (or selected home) and then system locations.
        Honors cancellation and shutdown request; swallows non-fatal errors.
        """
        try:
            if SysUtils.rootcheck():
                homes = [("root", "/root")]
                homes.extend(UserDiscovery.listusers())
                seen = set()
                for _, home in homes:
                    if home in seen:
                        continue
                    seen.add(home)
                    self.checkstop()
                    self.cleanupuser(Path(home))
                self.checkstop()
                self.cleanupsystem()
            else:
                self.cleanupuser(Path(self.opts.userhome))
                self.checkstop()
                self.cleanupsystem()
        except RuntimeError:
            pass
        except (OSError, PermissionError, subprocess.SubprocessError, ValueError):
            pass

        if self.opts.shutafter and not self.opts.dryrun:
            ShellExec.cmdrun("shutdown now", False)


# Custom About dialog
class AboutDialog(QDialog):
    """
    Custom About dialog with app logo, version, and a clickable link.
    Sized larger than QMessageBox and uses rich text for the website.
    Falls back gracefully if the logo cannot be found on disk.
    """

    # Function '__init__'
    def __init__(self, parent: Optional[QWidget], version: str, website: str):
        """
        Initialize the About dialog with branding and metadata.
        Sets up logo, title, version, description, and a clickable website link.
        Uses /usr/share/pixmaps/blitzclean.png as the primary logo path with fallbacks.
        """
        super().__init__(parent)
        self.setWindowTitle("About BlitzClean")
        self.setModal(True)
        self.setMinimumSize(520, 360)

        logolabel = QLabel()
        logolabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        candidate_paths = [
            Path("/usr/share/pixmaps/blitzclean.png"),
            Path(__file__).resolve().parent / "logo.png",
            CONFIGPATH / "logo.png",
        ]
        pix: Optional[QPixmap] = None
        for pth in candidate_paths:
            if pth.is_file():
                tmp = QPixmap(str(pth))
                if not tmp.isNull():
                    pix = tmp
                    break

        if pix:
            logolabel.setPixmap(
                pix.scaled(
                    128, 128,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
        else:
            logolabel.setText("🧹")

        title = QLabel(f"<b>BlitzClean</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px;")

        ver = QLabel(f"Version: {version}")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)

        link = QLabel(f'<a href="{website}">{website}</a>')
        link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        link.setTextFormat(Qt.TextFormat.RichText)
        link.setOpenExternalLinks(True)

        msg = QLabel("Ubuntu Cleanup GUI to reclaim space and tidy caches/logs.")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #aaa;")

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, parent=self)
        btns.accepted.connect(self.accept)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(12)
        lay.addWidget(logolabel)
        lay.addWidget(title)
        lay.addWidget(ver)
        lay.addWidget(msg)
        lay.addWidget(link)
        lay.addStretch(1)
        lay.addWidget(btns)


# Class 'PrefsDialog'
class PrefsDialog(QDialog):
    """
    Modal preferences dialog for tuning cleanup behavior and scope.
    Lets users configure journal limits, snap retention, and path toggles.
    Produces updated ExecOpts and path option maps on acceptance.
    """

    # Function '__init__'
    def __init__(self, parent: QWidget, opts: ExecOpts, runbootstart: bool, runshutdown: bool, pathopts: Dict[str, bool]):
        """
        Construct the preferences dialog with the current settings snapshot.
        Builds tabs for general options and per-path enablement checkboxes.
        Values are staged locally until the dialog is accepted.
        """
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setModal(True)
        self.resize(780, 620)

        self.opts = ExecOpts.fromdict(opts.todict())
        self.execbootstart = bool(runbootstart)
        self.execshutdown = bool(runshutdown)
        self.pathopts = pathopts.copy()
        tabs = QTabWidget(self)

        # --- General
        w_general = QWidget()
        g = QFormLayout(w_general)
        self.cbshutdown = QCheckBox("Shutdown after cleanup")
        self.cbrunboot = QCheckBox("Run at boot")
        self.cbrunshutdown = QCheckBox("Run at shutdown")
        self.spindays = QSpinBox()
        self.spindays.setRange(0, 3650)
        self.editsize = QLineEdit()
        self.spinkeep = QSpinBox()
        self.spinkeep.setRange(1, 10)

        self.cbshutdown.setChecked(self.opts.shutafter)
        self.cbrunboot.setChecked(self.execbootstart)
        self.cbrunshutdown.setChecked(self.execshutdown)
        self.spindays.setValue(self.opts.vacuumdays)
        self.editsize.setText(self.opts.vacuumsize)
        self.spinkeep.setValue(self.opts.keepsnaps)

        g.addRow(self.cbshutdown)
        g.addRow(self.cbrunboot)
        g.addRow(self.cbrunshutdown)
        g.addRow(QLabel("Vacuum days:"), self.spindays)
        g.addRow(QLabel("Vacuum size:"), self.editsize)
        g.addRow(QLabel("Keep Snap revisions:"), self.spinkeep)
        loadopts = QWidget()
        v = QVBoxLayout(loadopts)
        self.chk_map: Dict[str, QCheckBox] = {}

        # Function 'addsection'
        def addsection(title: str, keys: List[str]):
            """
            Helper to add a titled group of checkboxes for a set of keys.
            Initializes each checkbox from the current path options map.
            Adds the completed group box into the Options tab layout.
            """
            box = QGroupBox(title)
            inner = QVBoxLayout(box)
            for k in keys:
                cb = QCheckBox(k)
                cb.setChecked(self.pathopts.get(k, True))
                self.chk_map[k] = cb
                inner.addWidget(cb)
            v.addWidget(box)

        addsection("User: Paths", USERPATH)
        addsection("User: Recent & Histories", USERHISTORY)
        addsection("User: Patterns (Firefox/Chromium/Brave/Flatpak etc.)", USERPATTERN)
        addsection("User: Aggressive (DANGEROUS)", USERDEEP)
        addsection("Root: Items", ROOTITEMS)
        addsection("System: Directories", SYSDIRS)
        addsection("System: Log & Crash Globs", [f"{base}::{pat}" for base, pat in SYSGLOBS])

        scroll = QScrollArea()
        container = QWidget()
        container.setLayout(v)
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        tabs.addTab(w_general, "General")
        tabs.addTab(scroll, "Options")

        btns = QDialogButtonBox(parent=self)
        btnvalid = QPushButton("OK", self)
        btncancel = QPushButton("Cancel", self)
        btns.addButton(btnvalid, QDialogButtonBox.ButtonRole.AcceptRole)
        btns.addButton(btncancel, QDialogButtonBox.ButtonRole.RejectRole)

        btnvalid.clicked.connect(self.accept)
        btncancel.clicked.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addWidget(tabs)
        lay.addWidget(btns)

    # Function 'addvalues'
    def addvalues(self) -> Tuple[ExecOpts, bool, bool, Dict[str, bool]]:
        """
        Pull current widget state back into domain objects and flags.
        Updates ExecOpts, boot/shutdown toggles, and per-path selections.
        Returns a tuple (opts, runboot, runshutdown, pathopts).
        """
        self.opts.shutafter = self.cbshutdown.isChecked()
        self.execbootstart = self.cbrunboot.isChecked()
        self.execshutdown = self.cbrunshutdown.isChecked()
        self.opts.vacuumdays = self.spindays.value()
        self.opts.vacuumsize = self.editsize.text().strip() or "100M"
        self.opts.keepsnaps = self.spinkeep.value()
        for k, cb in self.chk_map.items():
            self.pathopts[k] = cb.isChecked()
        return self.opts, self.execbootstart, self.execshutdown, self.pathopts


# Class 'BlitzClean'
class BlitzClean(QWidget):
    """
    Main GUI window for BlitzClean, an Ubuntu cleanup tool.
    Provides run/dry-run controls, live progress table, and preferences.
    Delegates cleanup work to a background thread for responsiveness.
    """

    # Function '__init__'
    def __init__(self):
        """
        Initialize the main window, menus, widgets, and signals.
        Sets up periodic queue flushing to stream file rows to the table.
        Loads persisted configuration and primes default execution options.
        """
        super().__init__()
        self.setWindowTitle(f"BlitzClean {VERSION} - Ubuntu Cleanup GUI")
        self.resize(1000, 720)

        self.worker_thread = None
        self.cleaner: Optional[SysCleaner] = None
        self.file_queue: "queue.Queue[Tuple[str,int,str]]" = queue.Queue()

        menubar = QMenuBar(self)
        mfile = menubar.addMenu("File")
        actquit = QAction("Quit", self)
        actquit.triggered.connect(QApplication.quit)
        mfile.addAction(actquit)

        medit = menubar.addMenu("Edit")
        actprefs = QAction("Preferences", self)
        actprefs.triggered.connect(self.onprefs)
        medit.addAction(actprefs)

        mhelp = menubar.addMenu("Help")
        actabout = QAction("About", self)
        actabout.triggered.connect(self.onabout)
        mhelp.addAction(actabout)

        self.cmb_user = QComboBox()
        self.users = UserDiscovery.listusers()
        for u, home in self.users:
            self.cmb_user.addItem(f"{u}  —  {home}", (u, home))

        self.lbl_total = QLabel("Cleared Space\n0.00 MB")
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_total.setStyleSheet("font-weight: 600;")

        userrow = QHBoxLayout()
        userrow.addWidget(QLabel("User to clean:"))
        userrow.addWidget(self.cmb_user)
        userrow.addStretch()
        userrow.addWidget(self.lbl_total)

        self.btndry = QPushButton("Dry-Run")
        self.btnrun = QPushButton("Run")
        self.btnstop = QPushButton("Stop")
        self.btnstop.setEnabled(False)
        btns = QHBoxLayout()
        btns.addWidget(self.btndry)
        btns.addWidget(self.btnrun)
        btns.addWidget(self.btnstop)
        btns.addStretch()

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Filepath", "Size", "Modified"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setShowGrid(True)

        root = QVBoxLayout()
        root.setMenuBar(menubar)
        root.addLayout(userrow)
        root.addLayout(btns)
        root.addWidget(self.table, stretch=1)
        root.addWidget(self.progress)
        self.setLayout(root)

        self.btndry.clicked.connect(lambda: self.onrun(dry=True))
        self.btnrun.clicked.connect(lambda: self.onrun(dry=False))
        self.btnstop.clicked.connect(self.onstop)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.flushrows)
        self.timer.start(100)

        self.opts = ExecOpts()
        self.prefsexecbootstart = False
        self.prefsexecshutdown = False
        self.pathopts: Dict[str, bool] = {}
        self.showbytes = 0
        self.confloader()

    # Function 'confloader'
    def confloader(self):
        """
        Load persisted configuration values and apply them to controls.
        Reads key=value config, coerces types, and restores check states.
        Also restores saved user selection if present.
        """
        cfg = ConfigManager.load()

        # Function 'b'
        def b(key: str, default: bool = False) -> bool:
            """
            Convert a config truthy string into a boolean with default.
            Accepts '1/true/True/yes' as True; everything else is False.
            Helps keep config parsing concise and consistent.
            """
            return cfg.get(key, "1" if default else "0") in ("1", "true", "True", "yes")

        # Function 's'
        def s(key: str, default: str = "") -> str:
            """
            Fetch a string value from config or return the provided default.
            Keeps missing keys from raising exceptions or returning None.
            Used for simple text fields like vacuum size and username.
            """
            return cfg.get(key, default)

        try:
            self.opts.vacuumdays = int(cfg.get("vacuumdays", "7") or 7)
        except (ValueError, TypeError):
            self.opts.vacuumdays = 7
        self.opts.vacuumsize = s("vacuumsize", "100M")
        try:
            self.opts.keepsnaps = int(cfg.get("keepsnaps", "2") or 2)
        except (ValueError, TypeError):
            self.opts.keepsnaps = 2

        self.opts.shutafter = b("shutafter", False)
        self.opts.clearkernels = b("clearkernels", False)
        self.prefsexecbootstart = b("runbootstart", False)
        self.prefsexecshutdown = b("runshutdown", False)

        all_keys = (
            USERPATH
            + USERHISTORY
            + USERPATTERN
            + USERDEEP
            + ROOTITEMS
            + SYSDIRS
            + [f"{base}::{pat}" for base, pat in SYSGLOBS]
        )

        for k in all_keys:
            self.pathopts[k] = b(f"options.{k}", True)

        saved_user = s("username", "")
        for i in range(self.cmb_user.count()):
            u, _ = self.cmb_user.itemData(i)
            if u == saved_user:
                self.cmb_user.setCurrentIndex(i)
                break

    # Function 'confpersist'
    def confpersist(self):
        """
        Persist current options and selections back to the config file.
        Captures username, home, and all per-path enablement flags.
        Keeps preferences in sync between sessions and worker runs.
        """
        user, home = self.cmb_user.currentData()
        self.opts.username = user
        self.opts.userhome = home
        ConfigManager.save(self.opts, self.prefsexecbootstart, self.prefsexecshutdown, self.pathopts)

    # Function 'filerow'
    def filerow(self, path: str, size_bytes: int, mtime: str):
        """
        Enqueue a file row for the GUI table from background threads.
        Transfers data through a thread-safe queue to avoid UI races.
        Actual insertion is performed during periodic flushes.
        """
        self.file_queue.put((path, size_bytes, mtime))

    # Function 'flushrows'
    def flushrows(self):
        """
        Periodically drain queued rows and append them to the table widget.
        Converts byte counts to human-readable units before display.
        Keeps the UI responsive by avoiding heavy work in the main loop.
        Also increments the live 'Cleared Space' counter.
        """
        updated = False
        try:
            while True:
                path, size_b, mtime = self.file_queue.get_nowait()
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(path))
                self.table.setItem(r, 1, QTableWidgetItem(SysUtils.unitsize(size_b)))
                self.table.setItem(r, 2, QTableWidgetItem(mtime))
                try:
                    self.showbytes += int(size_b)
                    updated = True
                except (ValueError, TypeError, OverflowError):
                    pass
        except queue.Empty:
            if updated:
                self.lbl_total.setText(f"Cleared Space\n{SysUtils.unitsize(self.showbytes)}")

    # Function 'onabout'
    def onabout(self):
        """
        Display a larger About dialog with logo and website link.
        Uses a custom QDialog for layout control and clickable links.
        Provides application metadata in a visually centered layout.
        """
        dlg = AboutDialog(self, VERSION, WEBSITEURL)
        dlg.exec()

    # Function 'onprefs'
    def onprefs(self):
        """
        Open the preferences dialog and apply any accepted changes.
        Updates in-memory options and persists them to disk immediately.
        Also refreshes the path options map for the next run.
        """
        dlg = PrefsDialog(self, self.opts, self.prefsexecbootstart, self.prefsexecshutdown, self.pathopts)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_opts, boot, shut, popts = dlg.addvalues()
            self.opts = new_opts
            self.prefsexecbootstart = boot
            self.prefsexecshutdown = shut
            self.pathopts = popts
            self.confpersist()

    # Function 'onstop'
    def onstop(self):
        """
        Signal the running cleaner to cancel and disable the Stop button.
        Has no effect when no worker is active or already stopping.
        UI state is updated to reflect that cancellation is in progress.
        """
        if self.cleaner:
            self.cleaner.loadstop()
            self.btnstop.setEnabled(False)

    # Function 'onrun'
    def onrun(self, dry: bool):
        """
        Start a cleanup task (dry-run or live) in a background thread.
        Handles privilege elevation via pkexec when 'root' is selected.
        Manages UI state, progress indicator, and row streaming lifecycle.
        Also attempts to close user programs automatically before cleaning.
        """
        self.table.setRowCount(0)
        self.showbytes = 0
        self.lbl_total.setText("Cleared Space\n0.00 MB")

        user, home = self.cmb_user.currentData()
        self.opts.username = user
        self.opts.userhome = home
        self.opts.dryrun = dry

        if self.worker_thread and self.worker_thread.is_alive():
            QMessageBox.warning(self, "Busy", "A cleanup task is already running.")
            return

        self.confpersist()
        if not self.opts.dryrun and self.opts.username and SysUtils.rootcheck():
            try:
                ProcessManager.closeprograms(self.opts.username, excludepids={os.getpid()}, gracesecs=5)
            except (OSError, PermissionError, subprocess.SubprocessError, ValueError):
                pass

        self.progress.setVisible(True)
        self.btnstop.setEnabled(True)
        self.btnrun.setEnabled(False)
        self.btndry.setEnabled(False)

        rootneed = (self.opts.username == "root") and not SysUtils.rootcheck()

        # Function 'workload'
        def workload():
            """
            Worker function executed on a background thread.
            Runs cleanup locally or via pkexec, streaming rows back to UI.
            Restores UI controls when work completes or is cancelled.
            """
            try:
                if rootneed:
                    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tf:
                        tf.write(json.dumps(self.opts.todict()))
                        tf.flush()
                        optsfile = tf.name
                    try:
                        cmd = ["pkexec", sys.executable, sys.argv[0], "--worker", optsfile]
                        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

                        for line in iter(proc.stdout.readline, ""):
                            if not line:
                                break
                            line = line.rstrip("\n")
                            if line.startswith("ROW\t"):
                                parts = line.split("\t", 3)
                                if len(parts) == 4:
                                    _, path, size_str, mtime = parts
                                    try:
                                        size_b = int(size_str)
                                    except ValueError:
                                        size_b = 0
                                    self.filerow(path, size_b, mtime)
                            elif line.startswith("TOTAL\t"):
                                parts = line.split("\t", 2)
                                if len(parts) >= 2:
                                    try:
                                        total_b = int(parts[1])
                                        self.showbytes = total_b
                                        self.lbl_total.setText(f"Cleared Space\n{SysUtils.unitsize(total_b)}")
                                    except (ValueError, TypeError, OverflowError):
                                        pass
                        proc.wait()
                    finally:
                        try:
                            os.unlink(optsfile)
                        except OSError:
                            pass
                else:
                    self.cleaner = SysCleaner(self.opts, self.filerow, self.pathopts)
                    self.cleaner.run()
                    self.showbytes = getattr(self.cleaner, "totalbytes", self.showbytes)
                    self.lbl_total.setText(f"Cleared Space\n{SysUtils.unitsize(self.showbytes)}")
            finally:
                self.progress.setVisible(False)
                self.btnstop.setEnabled(False)
                self.btnrun.setEnabled(True)
                self.btndry.setEnabled(True)

        self.worker_thread = threading.Thread(target=workload, daemon=True)
        self.worker_thread.start()


# Class 'App'
class App:
    """
    Minimal application bootstrapper for the BlitzClean GUI/worker.
    Runs the GUI normally or a worker process when invoked with --worker.
    Encapsulates QApplication lifecycle and exit handling.
    """

    # Function 'main'
    @staticmethod
    def main():
        """
        Entry point that dispatches between GUI and privileged worker mode.
        In worker mode, loads ExecOpts and path options, then runs SysCleaner.
        Otherwise, starts the Qt application and shows the main window.
        """
        if len(sys.argv) == 3 and sys.argv[1] == "--worker":
            opts_path = Path(sys.argv[2])
            data = json.loads(opts_path.read_text(encoding="utf-8"))
            opts = ExecOpts.fromdict(data)

            cfg = ConfigManager.load()
            pathopts: Dict[str, bool] = {}
            all_keys = (
                USERPATH
                + USERHISTORY
                + USERPATTERN
                + USERDEEP
                + ROOTITEMS
                + SYSDIRS
                + [f"{base}::{pat}" for base, pat in SYSGLOBS]
            )
            for k in all_keys:
                pathopts[k] = cfg.get(f"options.{k}", "1") in ("1", "true", "True", "yes")

            # Function 'rowcheckbox'
            def rowcheckbox(path: str, size_b: int, mtime: str):
                """
                Worker-side row emitter that prints TSV lines to stdout.
                The GUI parses these lines to populate its progress table.
                Keeps IPC simple and robust across privilege boundaries.
                """
                print(f"ROW\t{path}\t{size_b}\t{mtime}", flush=True)

            cleaner = SysCleaner(opts, rowcheckbox, pathopts)
            cleaner.run()
            try:
                print(f"TOTAL\t{int(cleaner.totalbytes)}", flush=True)
            except (ValueError, TypeError, OverflowError):
                print("TOTAL\t0", flush=True)
            return 0

        app = QApplication(sys.argv)
        win = BlitzClean()
        win.show()
        sys.exit(app.exec())


# Callback
if __name__ == "__main__":
    App.main()
