"""
Helper functions for dummy file I/O operations to disable writing or deleting
blacklisted files during tests.
"""

from collections.abc import Callable
from io import BytesIO
from io import StringIO
from pathlib import Path
from typing import Any
from typing import cast


def is_blacklisted_file(path: Path) -> bool:
    """
    Check if a file is blacklisted from file I/O during tests.

    Blacklisted files: 'test_config.yml' or any file whose name starts with 'data'
    and ends with '.json'.

    Args:
        path (Path): The file path to check.

    Returns:
        bool: True if the file is blacklisted, False otherwise.
    """
    return (path.name == "test_config.yml") or (
        path.name.startswith("data") and path.name.endswith(".json")
    )


def create_dummy_write_text(
    original_write_text: Callable[[Path, str, str], Any],
) -> Callable[[Path, str, str], None]:
    """
    Return a dummy write_text function that prevents writing to blacklisted files.

    Args:
        original_write_text (Callable[[Path, str, str], Any]): The original write_text function.

    Returns:
        Callable[[Path, str, str], None]: The dummy write_text function.
    """

    def dummy_write_text(self: Path, data: str, encoding: str = "utf-8") -> None:
        if is_blacklisted_file(self):
            return
        original_write_text(self, data, encoding)

    return dummy_write_text


def create_dummy_unlink(original_unlink: Callable[[Path], None]) -> Callable[[Path], None]:
    """
    Return a dummy unlink function that prevents deletion of blacklisted files.

    Args:
        original_unlink (Callable[[Path], None]): The original unlink function.

    Returns:
        Callable[[Path], None]: The dummy unlink function.
    """

    def dummy_unlink(self: Path) -> None:
        if is_blacklisted_file(self):
            return
        original_unlink(self)

    return dummy_unlink


def create_dummy_open(original_open: Callable[..., Any]) -> Callable[..., StringIO | BytesIO]:
    """
    Return a dummy open function that, for blacklisted files in write or append mode,
    returns an in-memory file object. For other operations, if the file is blacklisted
    and opened in read mode, it reads the content and returns an in-memory file with that content.
    For non-blacklisted files, it delegates to the original open function.

    Args:
        original_open (Callable[..., Any]): The original open function.

    Returns:
        Callable[..., Union[StringIO, BytesIO]]: The dummy open function.
    """

    def dummy_open(
        self: Path,
        mode: str = "r",
        *args: object,
        **kwargs: object,
    ) -> StringIO | BytesIO:
        if is_blacklisted_file(self):
            if "w" in mode or "a" in mode:
                result = StringIO() if "b" not in mode else BytesIO()
                result.seek(0)
                return result
            with original_open.__get__(self, type(self))(mode, *args, **kwargs) as f:
                content = f.read()
            result = StringIO(content) if "b" not in mode else BytesIO(content)
            result.seek(0)
            return result
        # For non-blacklisted files, we need to handle the case where the file
        # is opened in binary mode or text mode, and return the appropriate type.
        # Since we can't know the exact type at runtime, we use a cast to tell
        # mypy that we're returning the correct type.
        if "b" in mode:
            return cast(BytesIO, original_open.__get__(self, type(self))(mode, *args, **kwargs))
        return cast(StringIO, original_open.__get__(self, type(self))(mode, *args, **kwargs))

    return dummy_open


def create_dummy_exists(original_exists: Callable[[Path], bool]) -> Callable[[Path], bool]:
    """
    Return a dummy exists function that always returns False for blacklisted files,
    except for files named 'test.mp4' which are considered to exist.

    Args:
        original_exists (Callable[[Path], bool]): The original exists function.

    Returns:
        Callable[[Path], bool]: The dummy exists function.
    """

    def dummy_exists(self: Path) -> bool:
        if is_blacklisted_file(self):
            return False
        if self.name == "test.mp4":
            return True
        return bool(original_exists(self))

    return dummy_exists


def cleanup_blacklisted_files() -> None:
    """
    Remove all blacklisted files from the current working directory.
    """
    for file in Path.cwd().glob("data*.json"):
        if file.exists():
            file.unlink()
    if Path("test_config.yml").exists():
        Path("test_config.yml").unlink()
