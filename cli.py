#!/usr/bin/env python3
"""CLI for DanceDB operations."""
import logging
import sys

import config

logging.basicConfig(
    level=config.loglevel,
    format="%(asctime)s: %(levelname)s: %(message)s",
    datefmt="%H:%M"
)
sys.path.insert(0, str(__file__).rsplit("/", 1)[0])

COMMANDS = {
    "DANSLOGEN": [
        ("scrape-danslogen", "Fetch danslogen event rows"),
        ("scrape-danslogen-artists", "Fetch artists from danslogen"),
        ("ensure-danslogen-venues", "Ensure danslogen venues exist in DanceDB"),
        ("upload-danslogen-events", "Upload danslogen events to DanceDB"),
        ("ensure-event-venues", "Ensure event venues exist in DanceDB"),
    ],
    "VENUES": [
        ("scrape-bygdegardarna", "Fetch bygdegardarna venues with coordinates"),
        ("scrape-dancedb-venues", "Fetch existing venues from DanceDB"),
        ("match-bygdegardarna-venues", "Match bygdegardarna venues to DanceDB"),
        ("find-duplicate-venues", "Find venues within 100m of each other"),
    ],
    "ONBEAT": [
        ("scrape-onbeat", "Fetch events"),
        ("ensure-venues-onbeat", "Ensure venues exist"),
        ("upload-onbeat", "Upload to DanceDB"),
    ],
    "COGWORK": [
        ("scrape-cogwork", "Fetch cogwork events from ALL sources"),
        ("upload-cogwork", "Upload cogwork events to DanceDB"),
    ],
    "FOLKETSHUS": [
        ("scrape-folketshus", "Fetch folketshus och parker venues"),
    ],
    "WIKIDATA": [
        ("scrape-wikidata-artists", "Fetch artists from Wikidata"),
        ("match-wikidata-artists", "Match DanceDB artists to Wikidata"),
        ("sync-wikidata-artists", "Create missing artists from danslogen"),
    ],
    "SYNC (FULL WORKFLOWS)": [
        ("sync-danslogen", "bygdegardarna → folketshus → scrape → match → ensure-venues → upload"),
        ("sync-bygdegardarna", "scrape → fetch-dancedb → match-bygdegardarna-venues"),
        ("sync-onbeat", "scrape + upload"),
        ("sync-cogwork", "scrape + upload"),
        ("sync-folketshus", "scrape + match"),
        ("sync-all", "Sync all sources in sequence"),
        ("scrape-all", "Scrape all data sources at once"),
    ],
}


def print_commands():
    print("DanceDB CLI Commands\n")
    for category, commands in COMMANDS.items():
        print(f"{category}:")
        for cmd, desc in commands:
            print(f"  {cmd:<30} {desc}")
        print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="DanceDB CLI")
    parser.add_argument("-l", "--list", action="store_true", help="List available commands")
    parser.add_argument("command", nargs="?", default=None)

    args, unknown = parser.parse_known_args()

    if args.list:
        print_commands()
        return
    if args.command is None:
        print_commands()
        return

    valid_commands = set()
    for commands in COMMANDS.values():
        for cmd, _ in commands:
            valid_commands.add(cmd)

    if args.command not in valid_commands:
        print(f"Unknown command: {args.command}\n")
        print_commands()
        return

    sub = parser.add_subparsers(dest="command")
    
    from src.cli.danslogen import add_danslogen_subparsers
    from src.cli.cogwork import add_cogwork_subparsers
    from src.cli.onbeat import add_onbeat_subparsers
    from src.cli.sync import add_sync_subparsers
    
    handlers = {}
    handlers.update(add_danslogen_subparsers(sub))
    handlers.update(add_cogwork_subparsers(sub))
    handlers.update(add_onbeat_subparsers(sub))
    handlers.update(add_sync_subparsers(sub))

    args = parser.parse_args()

    if args.command in handlers:
        handlers[args.command](args)


if __name__ == "__main__":
    main()
