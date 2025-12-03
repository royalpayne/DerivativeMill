"""
Version management for DerivativeMill

This file maintains the current version of the application.
Version format: vMAJOR.MINOR.PATCH (e.g., v0.60.1)

Semantic Versioning:
- MAJOR: Large feature releases or breaking changes
- MINOR: New features and enhancements (0.60, 0.61, etc.)
- PATCH: Bug fixes and minor updates (0.60.1, 0.60.2, etc.)
"""

__version__ = "v0.60.1"

def get_version():
    """Get the current version"""
    return __version__

def increment_patch():
    """
    Increment the patch version (e.g., v0.60.1 -> v0.60.2)
    Call this when making a patch release (bug fixes, small updates)
    """
    global __version__
    parts = __version__[1:].split('.')  # Remove 'v' and split
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    patch += 1
    __version__ = f"v{major}.{minor}.{patch}"
    return __version__

def increment_minor():
    """
    Increment the minor version (e.g., v0.60.1 -> v0.61.0)
    Call this when making a feature release
    """
    global __version__
    parts = __version__[1:].split('.')  # Remove 'v' and split
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    minor += 1
    patch = 0
    __version__ = f"v{major}.{minor}.{patch}"
    return __version__

def increment_major():
    """
    Increment the major version (e.g., v0.60.1 -> v1.0.0)
    Call this when making a major release with breaking changes
    """
    global __version__
    parts = __version__[1:].split('.')  # Remove 'v' and split
    major = int(parts[0])
    major += 1
    __version__ = f"v{major}.0.0"
    return __version__
