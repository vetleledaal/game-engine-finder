#!/usr/bin/env python
from __future__ import annotations

import configparser
import datetime as dt
import os
import platform
import re
import shutil
import stat
import struct
import subprocess  # noqa: S404
import sys
from contextlib import suppress
from enum import Enum
from itertools import product
from pathlib import Path
from tkinter import Tk
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Iterator

username = "Placeholder"  # PCGamingWiki username to be linked in refcheck


if sys.version_info < (3, 9):
    print("Python 3.8 is EOL since 2024-10-07", file=sys.stderr)
    print("Using Python", sys.version, file=sys.stderr)


# https://en.wikipedia.org/wiki/List_of_game_engines
#
#
# AGS - Adventure Game Studio (2.72 checked) -- ????
# /ACI version (\d\.[\w\s\-]{1,8}(?:\.[\w\s\-]{1,8})?)[\n\)\[,]/

RE_POSSIBLE_EXE = re.compile(r"game|launch|run|start|begin|open|load|init|exec|\.bin$|app", re.IGNORECASE)
RENPY_PYTHON2_VER = 7


class MkxpVersion(Enum):
    XP = 1
    VX = 2
    VX_ACE = 3

    @property
    def display_name(self) -> str:
        if self == MkxpVersion.VX_ACE:
            return "VX Ace"
        return self.name


def file_key(entry: os.DirEntry[str]) -> tuple[bool, bool, bool, str]:
    # First try files with the .exe suffix.
    # Then try files with the executable permission bit (non-Windows only).
    # Then try files that match likely keywords.
    # Finally try anything else, in lexicographic order.
    return (
        not entry.name.endswith(".exe"),
        not bool(entry.stat().st_mode & stat.S_IXUSR),
        not bool(RE_POSSIBLE_EXE.search(entry.name)),
        entry.name,
    )


def detect_folder(path_str: Path | str) -> tuple[str | None, str | None]:
    path = Path(path_str)

    # Find all files in directory.
    candidate_entries = [f for f in os.scandir(path) if f.is_file()]

    # Sort to minimize search time.
    candidate_entries.sort(key=file_key)

    # Try each file until we find a match.
    for entry in candidate_entries:
        engine, engine_ver = detect(entry.path)
        if engine:
            return engine, engine_ver

    # No matches found.
    return None, None


def detect(exe_str: Path | str) -> tuple[str | None, str | None]:
    exe = Path(exe_str)

    if exe.is_dir():
        return detect_folder(exe)

    # Check dir struct
    exe_path = exe.parent

    path = exe_path / "Adobe AIR"
    if path.exists():
        # Probably Adobe AIR (not tested)
        return "Adobe AIR", None

    path = exe_path / "renpy"
    if path.exists():
        # Probably renpy project
        # Get version from files...
        init_file = path / "__init__.pyo"
        init_src_file = path / "__init__.py"
        vc_version_file = path / "vc_version.pyo"
        vc_version_src_file = path / "vc_version.py"
        init_exists = init_file.exists() or init_src_file.exists()
        vc_version_exists = vc_version_file.exists() or vc_version_src_file.exists()
        match1: str | None = None
        match2: str | None = None
        if init_exists and vc_version_exists:
            if init_file.exists():
                file_data = init_file.read_bytes()
                match1_m = re.search(re.compile(rb"vc_versioni\x00{4}((?:i.{4}){3,5})s", re.DOTALL), file_data)
                if match1_m:
                    g = match1_m.group(1)
                    if g:
                        unpacked_iter = cast("Iterator[tuple[bytes, int]]", struct.iter_unpack("<cI", g))
                        match1 = ".".join(str(v) for _, v in unpacked_iter)
            if not match1 and init_src_file.exists():
                # Parsing init binary failed, fall back to parsing init source
                file_data_str = init_src_file.read_text(encoding="utf-8")
                match1_candidates = re.finditer(
                    re.compile(r"version_tuple = \(([0-9]+, [0-9]+, [0-9]+), vc_version\)", re.DOTALL),
                    file_data_str,
                )
                for match1_candidate in match1_candidates:
                    g = match1_candidate.group(1)
                    if isinstance(g, str):
                        g2 = g.replace(", ", ".")
                        libpath = exe_path / "lib"
                        if int(g2[:1]) <= RENPY_PYTHON2_VER:
                            # RenPy 7.x or lower, if Python 2
                            pythonpaths = libpath.glob("python2.*")
                            if next(pythonpaths, None):
                                match1 = g2
                        else:
                            # RenPy 8.x or higher, if Python 3
                            pythonpaths = libpath.glob("python3.*")
                            if next(pythonpaths, None):
                                match1 = g2
            if vc_version_file.exists():
                file_data = vc_version_file.read_bytes()
                match2_m = re.search(re.compile(rb"\x00{3}(i.{4})", re.DOTALL), file_data)
                if match2_m:
                    g = match2_m.group(1)
                    if g:
                        unpacked_iter = cast("Iterator[tuple[bytes, int]]", struct.iter_unpack("<cI", g))
                        match2 = ".".join(str(v) for _, v in unpacked_iter)
            if not match2 and vc_version_src_file.exists():
                # Parsing vc_version binary failed, fall back to parsing vc_version source
                file_data_str = vc_version_src_file.read_text(encoding="utf-8")
                match2_m_str = re.search(re.compile(r"vc_version = ([0-9]+)", re.DOTALL), file_data_str)
                if match2_m_str:
                    g = match2_m_str.group(1)
                    if g:
                        match2 = g
        if match1 and match2:
            ver = f"{match1}.{match2}"
            return "Ren'Py", ver
        print("Found Ren'Py, no ver")
        print(match1 is not None)
        print(match2 is not None)

    file_data = exe.read_bytes()
    match = re.search(rb"\x00UnityPlayer\/([^\x20]+)", file_data)

    if not match:
        player_file = exe_path / "UnityPlayer.dll"
        if player_file.exists():
            file_data2 = player_file.read_bytes()
            match = re.search(rb"\x00UnityPlayer\/([^\x20]+)", file_data2)

    if match:
        g = match.group(1)
        if isinstance(g, bytes) and g.decode("utf-8") == "%s":
            # There can be multiple "*_Data" folders if there are multiple
            # Unity .exe files, so we have to pick the folder corresponding
            # to this .exe.
            ggm_file = exe_path / (exe.stem + "_Data") / "globalgamemanagers"
            if ggm_file.exists():
                file_data2 = ggm_file.read_bytes()
                match = re.search(rb"\x00(\d{1,4}\.\d+\.\d+[a-z]+\d+)\x00", file_data2)

    if match:
        g = match.group(1)
        if isinstance(g, bytes):
            return "Unity", g.decode("utf-8")

    match = re.search(rb"Made with GameMaker: Studio\x00", file_data)
    if match:
        return "GameMaker", None
    # Fallback, Windows only
    match = re.search(rb'name="YoYoGames.GameMaker.Runner"', file_data)
    if match:
        return "GameMaker", None

    match = re.search(rb"Unreal Engine 3 Licensee\x00{4}Unreal Engine 3", file_data)
    if match:
        return "Unreal Engine 3", None

    # \UE4PrereqSetup (UNICODE)
    match = re.search(
        rb"\x5C\x00\x55\x00\x45\x00\x34\x00\x50\x00\x72\x00\x65\x00\x72\x00\x65\x00\x71\x00\x53\x00\x65\x00\x74\x00\x75\x00\x70\x00",
        file_data,
    )
    if match:
        return "Unreal Engine 4", None

    match = re.search(rb"org\/lwjgl\/LWJGL", file_data)
    if match:
        return "LWJGL", None

    match = re.search(rb"com\/badlogic\/gdx", file_data)
    # NW.js 29 includes this false positive string
    decoy_match = re.search(rb"Heavily inspired by LibGDX's CanvasGraphicsRenderer:", file_data)
    if match and not decoy_match:
        return "LibGDX", None

    match = re.search(rb"\r\nKirikiri Z Project Contributors\r\nW.Dee, casper", file_data)
    if match:
        return "KiriKiri Z", None

    match = re.search(rb"\x00__ZL17mkxpDataDirectoryiPmm\x00", file_data)
    if not match:
        # This string shows up in the Falcon-mkxp and mkxp-z forks.
        match = re.search(rb"\x00_mkxp_kernel_caller_alias\x00", file_data)
    if match:
        # Try to detect which RGSS version is being used by mkxp.
        # First we try mkxp.conf, which takes highest priority.
        # TODO: also try mkxp.json, which is used by the mkxp-z fork.
        mkxp_conf_path = exe_path / "mkxp.conf"
        if mkxp_conf_path.exists():
            mkxp_conf_content = mkxp_conf_path.read_text(encoding="utf-8")
            mkxp_conf = configparser.ConfigParser()
            with suppress(Exception):
                # Workaround missing section header in mkxp.conf.
                mkxp_conf.read_string("[top]\n" + mkxp_conf_content)
                if "rgssVersion" in mkxp_conf["top"]:
                    mkxp_version = mkxp_conf["top"]["rgssVersion"]
                    mkxp_version_int = int(mkxp_version)
                    if mkxp_version_int in MkxpVersion:
                        ver = MkxpVersion(mkxp_version_int).display_name
                        return "mkxp", ver

        # If mkxp.conf doesn't list an RGSS version, or if it's 0, then fallback to Game.ini.
        ini_paths = exe_path.glob("*.ini")
        for i in ini_paths:
            game_ini = configparser.ConfigParser()
            try:
                game_ini.read(i)
            except UnicodeDecodeError:
                # Workaround for Japanese games
                game_ini.read(i, encoding="shift_jis")

            # Each RGSS version uses a different Scripts archive extension.
            if "Game" in game_ini and "Scripts" in game_ini["Game"]:
                mkxp_scripts = game_ini["Game"]["Scripts"]
                if mkxp_scripts.endswith(".rxdata"):
                    return "mkxp", "XP"
                if mkxp_scripts.endswith(".rvdata"):
                    return "mkxp", "VX"
                if mkxp_scripts.endswith(".rvdata2"):
                    return "mkxp", "VX Ace"

        # If Game.ini didn't list a Scripts path, then fallback to detecting the archive file directly.
        scripts_path = exe_path / "Data" / "Scripts.rxdata"
        if scripts_path.exists():
            return "mkxp", "XP"
        scripts_path = exe_path / "Data" / "Scripts.rvdata"
        if scripts_path.exists():
            return "mkxp", "VX"
        scripts_path = exe_path / "Data" / "Scripts.rvdata2"
        if scripts_path.exists():
            return "mkxp", "VX Ace"

        # We couldn't find the RGSS version.
        return "mkxp", None

    match = re.search(rb"\x00Software\\(KADOKAWA|Enterbrain)\\RPG2000\x00", file_data)
    if match:
        return "RPG Maker", "2000"

    match = re.search(rb"\x00Software\\(KADOKAWA|Enterbrain)\\RPG2003\x00", file_data)
    if match:
        return "RPG Maker", "2003"

    # Cocos2d (and Cocos2d-x)
    patterns = (
        re.compile(rb"\xFF{3}\x00([\d.]+)\x00{3}Jan\x00Feb"),
        re.compile(rb"</set>\x0A\x00\xFF{3}\x00cocos2d-x ([\d.]+)\x00"),
    )

    datas = [file_data]
    cocos2d_path = path / "libcocos2d.dll"
    if cocos2d_path.exists():
        datas.append(cocos2d_path.read_bytes())

    for pattern, data in product(patterns, datas):
        match = pattern.search(data)
        if match:
            g = match.group(1)
            if g:
                return "Cocos2d", str(g)

    # RGSS3 Player (UNICODE)
    match = re.search(
        rb"\x52\x00\x47\x00\x53\x00\x53\x00\x33\x00\x20\x00\x50\x00\x6C\x00\x61\x00\x79\x00\x65\x00\x72\x00",
        file_data,
    )
    if match:
        return "RPG Maker", "VX Ace"

    # Software\Enterbrain\RGSS3\RTP (UNICODE)
    match = re.search(
        rb"\x53\x00\x6F\x00\x66\x00\x74\x00\x77\x00\x61\x00\x72\x00\x65\x00\x5C\x00\x45\x00\x6E\x00\x74\x00\x65\x00\x72\x00\x62\x00\x72\x00\x61\x00\x69\x00\x6E\x00\x5C\x00\x52\x00\x47\x00\x53\x00\x53\x00\x33\x00\x5C\x00\x52\x00\x54\x00\x50\x00",
        file_data,
    )
    if match:
        return "RPG Maker", "VX Ace"

    # RGSS2 Player (UNICODE)
    match = re.search(
        rb"\x52\x00\x47\x00\x53\x00\x53\x00\x32\x00\x20\x00\x50\x00\x6C\x00\x61\x00\x79\x00\x65\x00\x72\x00",
        file_data,
    )
    if match:
        return "RPG Maker", "VX"

    # RGSS Player (UNICODE)
    match = re.search(
        rb"\x52\x00\x47\x00\x53\x00\x53\x00\x20\x00\x50\x00\x6C\x00\x61\x00\x79\x00\x65\x00\x72\x00",
        file_data,
    )
    if match:
        return "RPG Maker", "XP"

    # This string shows up in NW.js used by RPG Maker MV
    match = re.search(rb"\\node-webkit\\src\\[a-z]+\\nw\\", file_data)
    if not match:
        # This string shows up in NW.js used by RPG Maker MZ
        match = re.search(rb"nw\.exe\.pdb", file_data)
    if match:
        # NW.js; might or might not be RPG Maker
        js_files = exe_path.rglob("*.js")
        match_name: str | None = None
        match_version: str | None = None
        for js in js_files:
            js_data = js.read_bytes()
            if not match_name:
                # MV and MZ use different quote marks
                match_name_b = re.search(rb"Utils\.RPGMAKER_NAME = ['\"]([A-Za-z]+)['\"];", js_data)
                if match_name_b:
                    g = match_name_b.group(1)
                    if g:
                        match_name = g.decode(encoding="utf-8")
            if not match_version:
                # MV and MZ use different quote marks
                match_version_m = re.search(rb"Utils\.RPGMAKER_VERSION = ['\"]([0-9\.]+)['\"];", js_data)
                if match_version_m:
                    g = match_version_m.group(1)
                    if g:
                        match_version = g.decode(encoding="utf-8")
            if match_name and match_version:
                break
        if match_name and match_version:
            combined_version = match_name + " " + match_version
            return "RPG Maker", combined_version
        return "NW.js", None

    match = re.search(rb"ShiVa 3D Standalone Engine ([^\x20]+)", file_data)
    if match:
        g = match.group(1)
        if isinstance(g, bytes):
            return "ShiVa Engine", g.decode("utf-8")

    match = re.search(rb"\x00WOLF_FileReadText", file_data)
    if match:
        return "WOLF RPG Editor", None

    return None, None


def notice(message: str) -> None:
    r = Tk()
    r.withdraw()
    r.bell()
    r.destroy()
    print(message)


def set_clip(text: str) -> bool:
    os_name = platform.system()

    if os_name == "Windows":
        cmd = ["clip"]
    elif os_name == "Darwin":
        cmd = ["pbcopy"]
    elif os_name in {"Linux", "FreeBSD"}:
        if shutil.which("xclip"):
            cmd = ["xclip", "-selection", "clipboard"]
        elif shutil.which("xsel"):
            cmd = ["xsel", "--clipboard", "--input"]

    if not cmd:
        return _try_tk(text)

    with suppress(Exception):
        sp = subprocess.run(cmd, input=text, check=True, text=True)  # noqa: S603
        return sp.returncode == 0
    return _try_tk(text)


def _try_tk(text: str) -> bool:
    with suppress(Exception):
        root = Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    return False


def set_clip_v(name: str, version: str | None = None) -> None:
    out_name = ""
    out_build = ""

    if version:
        major_version = version.split(".")[0]
        out_name = f"|name={name} {major_version}"
        if major_version != version:
            out_build = "|build=" + version

    iso8601_today = dt.datetime.now(tz=dt.timezone.utc).strftime("%Y-%m-%d")

    out_string = (
        "{{Infobox game/row/engine|"
        + name
        + out_name
        + '|ref=<ref name="engineversion">{{Refcheck|user='
        + username
        + "|date="
        + iso8601_today
        + "}}</ref>"
        + out_build
        + "}}"
    )
    print(out_string)
    set_clip(out_string)


def set_clip_detect() -> None:
    name, version = detect(sys.argv[1])

    if not name:
        notice("Not found !!!")
        return

    print(f"Found {name=}, {version=}")
    set_clip_v(name, version)


if __name__ == "__main__":
    set_clip_detect()
