# game-engine-finder

Pretty hacky script for easily figuring out the engine used for a game, sets the clipboard for use on [PCGamingWiki](https://pcgamingwiki.com/wiki/Home).
Requires Python 3.5+.

## Installation

You can either use the `PKGBUILD` or run:

`pip install --user .`

## Usage

To use, run the script as `find-engine LocationToExecutable.exe` – should work with both Windows and Linux OSes for identifying supported game engines. Copy to clipboard function seems not to work properly under Linux. To run without installing, you can use `python ./find_engine.py` instead of `find-engine`.
