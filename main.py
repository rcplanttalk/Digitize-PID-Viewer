"""Entry point — forwards to the pid-gen CLI.

Run directly:
    uv run python main.py single
    uv run python main.py generate --n 5
    uv run python main.py --help
"""

from pid_generator.cli import main

if __name__ == "__main__":
    main()
