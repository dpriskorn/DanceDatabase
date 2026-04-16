from src.cli.danslogen import add_danslogen_subparsers
from src.cli.cogwork import add_cogwork_subparsers
from src.cli.onbeat import add_onbeat_subparsers
from src.cli.sync import add_sync_subparsers

__all__ = [
    "add_danslogen_subparsers",
    "add_cogwork_subparsers", 
    "add_onbeat_subparsers",
    "add_sync_subparsers",
]
