# game-engine-finder

Pretty hacky script for easily figuring out the engine used for a game, sets the clipboard for use on [PCGamingWiki](https://pcgamingwiki.com/wiki/Home).
Requires Python 3.5+.

## Installation

### Arch Linux
```bash
makepkg -sri
```

### Other
```bash
pip install --user --editable .
```

## Usage
Before using the `find_engine.py` script, make sure to set your PCGamingWiki username at the top of the file. To use the script, run it with the command `find-engine LocationToExecutable.exe`. Note that the clipboard feature may not work on Linux.

If you prefer not to install the script, you can still run it by executing the command `python find_engine.py` instead of `find-engine`.