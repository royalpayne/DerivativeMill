"""
Cross-platform utilities for DerivativeMill
Handles platform-specific operations (file opening, folders, etc.)
"""

import sys
import os
import subprocess
import platform
from pathlib import Path


class PlatformInfo:
    """Detect and provide information about the current platform"""

    @staticmethod
    def get_platform():
        """Return current platform: 'windows', 'macos', or 'linux'"""
        if sys.platform == 'win32':
            return 'windows'
        elif sys.platform == 'darwin':
            return 'macos'
        else:
            return 'linux'

    @staticmethod
    def is_windows():
        """Check if running on Windows"""
        return sys.platform == 'win32'

    @staticmethod
    def is_macos():
        """Check if running on macOS"""
        return sys.platform == 'darwin'

    @staticmethod
    def is_linux():
        """Check if running on Linux"""
        return sys.platform not in ('win32', 'darwin')

    @staticmethod
    def get_platform_name():
        """Get human-readable platform name"""
        return platform.system()  # Returns: 'Windows', 'Darwin', 'Linux'


class FileOperations:
    """Cross-platform file and folder operations"""

    @staticmethod
    def open_file_with_default_app(file_path):
        """Open a file with the default application"""
        file_path = str(file_path)

        try:
            if PlatformInfo.is_windows():
                os.startfile(file_path)
            elif PlatformInfo.is_macos():
                subprocess.run(['open', file_path], check=False)
            else:  # Linux
                subprocess.run(['xdg-open', file_path], check=False)
            return True
        except Exception as e:
            print(f"Error opening file: {e}")
            return False

    @staticmethod
    def open_folder_in_explorer(folder_path):
        """Open a folder in the file manager"""
        folder_path = str(folder_path)

        try:
            if PlatformInfo.is_windows():
                subprocess.run(['explorer', folder_path], check=False)
            elif PlatformInfo.is_macos():
                subprocess.run(['open', folder_path], check=False)
            else:  # Linux
                subprocess.run(['xdg-open', folder_path], check=False)
            return True
        except Exception as e:
            print(f"Error opening folder: {e}")
            return False


class AppDirs:
    """Cross-platform application directories"""

    @staticmethod
    def get_data_dir(app_name="DerivativeMill"):
        """
        Get platform-appropriate data directory
        Windows: %APPDATA%/app_name
        macOS: ~/Library/Application Support/app_name
        Linux: ~/.local/share/app_name (XDG compliant)
        """
        if PlatformInfo.is_windows():
            base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        elif PlatformInfo.is_macos():
            base = Path.home() / 'Library' / 'Application Support'
        else:  # Linux
            base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))

        data_dir = base / app_name
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    @staticmethod
    def get_config_dir(app_name="DerivativeMill"):
        """
        Get platform-appropriate config directory
        Windows: %APPDATA%/app_name
        macOS: ~/Library/Preferences/app_name
        Linux: ~/.config/app_name (XDG compliant)
        """
        if PlatformInfo.is_windows():
            base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        elif PlatformInfo.is_macos():
            base = Path.home() / 'Library' / 'Preferences'
        else:  # Linux
            base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))

        config_dir = base / app_name
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    @staticmethod
    def get_cache_dir(app_name="DerivativeMill"):
        """
        Get platform-appropriate cache directory
        Windows: %LOCALAPPDATA%/app_name/cache
        macOS: ~/Library/Caches/app_name
        Linux: ~/.cache/app_name (XDG compliant)
        """
        if PlatformInfo.is_windows():
            base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
            cache_dir = base / app_name / 'cache'
        elif PlatformInfo.is_macos():
            cache_dir = Path.home() / 'Library' / 'Caches' / app_name
        else:  # Linux
            base = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache'))
            cache_dir = base / app_name

        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir


class PlatformConfig:
    """Centralized platform configuration"""

    def __init__(self, app_name="DerivativeMill"):
        self.app_name = app_name
        self.platform = PlatformInfo.get_platform()
        self.platform_name = PlatformInfo.get_platform_name()

    def get_config(self):
        """Return platform configuration dictionary"""
        return {
            'platform': self.platform,
            'platform_name': self.platform_name,
            'is_windows': PlatformInfo.is_windows(),
            'is_macos': PlatformInfo.is_macos(),
            'is_linux': PlatformInfo.is_linux(),
            'data_dir': AppDirs.get_data_dir(self.app_name),
            'config_dir': AppDirs.get_config_dir(self.app_name),
            'cache_dir': AppDirs.get_cache_dir(self.app_name),
        }

    def get_supported_themes(self):
        """Get platform-appropriate theme options"""
        themes = ["System Default", "Fusion (Light)", "Fusion (Dark)", "Ocean", "Teal Professional"]

        # Platform-specific themes
        if PlatformInfo.is_windows():
            themes.append("Windows")

        return themes

    def get_supported_excel_viewers(self):
        """Get platform-appropriate Excel viewer options"""
        viewers = ["System Default"]

        if PlatformInfo.is_linux():
            viewers.extend(["Gnumeric", "LibreOffice"])

        return viewers
