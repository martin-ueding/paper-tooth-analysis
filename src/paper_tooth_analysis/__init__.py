import sys

from .cli import run


def main() -> None:
    sys.exit(run(sys.argv[1:]))
