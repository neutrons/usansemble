"""usansemble: a NiceGUI web app to assemble usansred JSON reduction configs."""

try:
    from usansemble._version import __version__  # noqa: F401
except (ModuleNotFoundError, ImportError):
    __version__ = "0.0.1"
