"""Re-exports for backwards compatibility and console-script entry points."""

from .append import append_to_commit_msg, main as append_main
from .archive import archive, main as archive_main
from .common import PROMPTS_DIRECTORY, _repo_root
from .prepare_repository import main as prepare_repository_main
from .prepare_repository import prepare_repository
from .unstage import main as unstage_main
from .unstage import unstage

__all__ = [
    "PROMPTS_DIRECTORY",
    "_repo_root",
    "prepare_repository",
    "prepare_repository_main",
    "unstage",
    "unstage_main",
    "append_to_commit_msg",
    "append_main",
    "archive",
    "archive_main",
]
