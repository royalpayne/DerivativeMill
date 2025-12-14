"""
Version management for DerivativeMill

Version is automatically derived from git tags.
To release a new version:
    git tag v0.90.2
    git push origin v0.90.2

Version format: vMAJOR.MINOR.PATCH (e.g., v0.90.1)

Semantic Versioning:
- MAJOR: Large feature releases or breaking changes
- MINOR: New features and enhancements (0.90, 0.91, etc.)
- PATCH: Bug fixes and minor updates (0.90.1, 0.90.2, etc.)
"""

import subprocess
import os

# Fallback version if git is not available
__fallback_version__ = "v0.90.2"

def get_version():
    """
    Get version from git tags.
    Returns the most recent tag, or fallback if git is unavailable.
    """
    try:
        # Get the directory where this file is located
        file_dir = os.path.dirname(os.path.abspath(__file__))

        # Try to get version from git describe
        version = subprocess.check_output(
            ['git', 'describe', '--tags', '--always'],
            cwd=file_dir,
            stderr=subprocess.DEVNULL
        ).decode().strip()

        # Ensure it starts with 'v'
        if not version.startswith('v'):
            version = f"v{version}"

        return version
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        # Git not available or not a git repo - use fallback
        return __fallback_version__

def get_version_info():
    """
    Get detailed version information including commit count since last tag.
    Returns a dict with version details.
    """
    try:
        file_dir = os.path.dirname(os.path.abspath(__file__))

        # Get full describe output (e.g., v0.90.1-5-g1234abc)
        full_version = subprocess.check_output(
            ['git', 'describe', '--tags', '--long', '--always'],
            cwd=file_dir,
            stderr=subprocess.DEVNULL
        ).decode().strip()

        # Get current branch
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=file_dir,
            stderr=subprocess.DEVNULL
        ).decode().strip()

        # Parse version components
        if '-' in full_version:
            parts = full_version.rsplit('-', 2)
            if len(parts) == 3:
                tag, commits_ahead, commit_hash = parts
                return {
                    'version': get_version(),
                    'tag': tag,
                    'commits_ahead': int(commits_ahead),
                    'commit': commit_hash,
                    'branch': branch,
                    'is_release': int(commits_ahead) == 0
                }

        return {
            'version': get_version(),
            'tag': full_version,
            'commits_ahead': 0,
            'commit': '',
            'branch': branch,
            'is_release': True
        }
    except:
        return {
            'version': __fallback_version__,
            'tag': __fallback_version__,
            'commits_ahead': 0,
            'commit': '',
            'branch': 'unknown',
            'is_release': True
        }

# For backwards compatibility
__version__ = get_version()
