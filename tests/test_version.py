from packaging.version import Version

from usansemble import __version__


def test_version():
    assert isinstance(__version__, str)
    assert __version__

    if __version__ != "unknown":
        Version(__version__)
