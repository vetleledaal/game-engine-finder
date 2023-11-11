#!/usr/bin/env python
import configparser, sys, os, re, datetime, time, stat, struct, pathlib
from itertools import product
from tkinter import Tk

username = "Placeholder" # PCGamingWiki username to be linked in refcheck

# https://en.wikipedia.org/wiki/List_of_game_engines
#
#
# AGS - Adventure Game Studio (2.72 checked) -- ????
# /ACI version (\d\.[\w\s\-]{1,8}(?:\.[\w\s\-]{1,8})?)[\n\)\[,]/

RE_POSSIBLE_EXE = re.compile(r'game|launch|run|start|begin|open|load|init|exec|\.bin$|app', re.IGNORECASE)

def file_key(entry):
    # First try files with the .exe suffix.
    # Then try files with the executable permission bit (non-Windows only).
    # Then try files that match likely keywords.
    # Finally try anything else, in lexicographic order.
    return (
        not entry.name.endswith('.exe'),
        not bool(entry.stat().st_mode & stat.S_IXUSR),
        not bool(RE_POSSIBLE_EXE.search(entry.name)),
        entry.name,
    )

def detect_folder(path):
    path = pathlib.Path(path)

    # Find all files in directory.
    candidate_entries = [f for f in os.scandir(path) if f.is_file()]

    # Sort to minimize search time.
    candidate_entries.sort(key=file_key)

    # Try each file until we find a match.
    for entry in candidate_entries:
        engine, engine_ver = detect(entry.path)
        if engine is not None:
            return engine, engine_ver

    # No matches found.
    return None, None

def detect(exe):
    exe = pathlib.Path(exe)

    if exe.is_dir():
        return detect_folder(exe)

    found = False
    # Check dir struct
    exe_path = exe.parent

    path = exe_path / "Adobe AIR"
    if not found and path.exists():
        # Probably Adobe AIR (not tested)
        print('Found Adobe AIR')
        return "Adobe AIR", None

    path = exe_path / "renpy"
    if not found and path.exists():
        # Probably renpy project
        # Get version from files...
        init_file = path / "__init__.pyo"
        init_src_file = path / "__init__.py"
        vc_version_file = path / "vc_version.pyo"
        vc_version_src_file = path / "vc_version.py"
        init_exists = init_file.exists() or init_src_file.exists()
        vc_version_exists = vc_version_file.exists() or vc_version_src_file.exists()
        match1 = None
        match2 = None
        if init_exists and vc_version_exists:
            if init_file.exists():
                with open(init_file, 'rb') as file:
                    file_data = file.read()
                    match1 = re.search(re.compile(br'vc_versioni\x00{4}((?:i.{4}){3,5})s', re.DOTALL), file_data)
                    if match1:
                        match1 = struct.unpack("<" + ("cI" * (len(match1.group(1))//5)), match1.group(1))
                        match1 = ".".join(map(str, match1[1::2]))
            if match1 is None:
                # Parsing init binary failed, fall back to parsing init source
                if init_src_file.exists():
                    with open(init_src_file, 'r') as file:
                        file_data = file.read()
                        match1_candidates = re.finditer(re.compile(r'version_tuple = \(([0-9]+, [0-9]+, [0-9]+), vc_version\)', re.DOTALL), file_data)
                        for match1_candidate in match1_candidates:
                            match1_candidate = match1_candidate.group(1)
                            match1_candidate = match1_candidate.replace(', ', '.')
                            libpath = exe_path / "lib"
                            if int(match1_candidate[:1]) <= 7:
                                # RenPy 7.x or lower, if Python 2
                                pythonpaths = libpath.glob("python2.*")
                                if next(pythonpaths, None) is not None:
                                    match1 = match1_candidate
                            else:
                                # RenPy 8.x or higher, if Python 3
                                pythonpaths = libpath.glob("python3.*")
                                if next(pythonpaths, None) is not None:
                                    match1 = match1_candidate
            if vc_version_file.exists():
                with open(vc_version_file, 'rb') as file:
                    file_data = file.read()
                    match2 = re.search(re.compile(br'\x00{3}(i.{4})', re.DOTALL), file_data)
                    if match2:
                        match2 = struct.unpack("<cI", match2.group(1))
                        match2 = ".".join(map(str, match2[1::2]))
            if match2 is None:
                # Parsing vc_version binary failed, fall back to parsing vc_version source
                if vc_version_src_file.exists():
                    with open(vc_version_src_file, 'r') as file:
                        file_data = file.read()
                        match2 = re.search(re.compile(r'vc_version = ([0-9]+)', re.DOTALL), file_data)
                        if match2:
                            match2 = match2.group(1)
        if match1 is not None and match2 is not None:
            found = True
            ver = ".".join([match1, match2])
            print("Found Ren'Py version: " + ver)
            return "Ren'Py", ver
        else:
            print("Found Ren'Py, no ver")
            print(match1 is not None)
            print(match2 is not None)

    if not found:
        with open(exe, 'rb') as file:
            file_data = file.read()

            match = re.search(br'\x00UnityPlayer\/([^\x20]+)', file_data)

            if match is None:
                player_file = exe_path / "UnityPlayer.dll"
                if player_file.exists():
                    with(open(player_file, 'rb')) as file2:
                        file_data2 = file2.read()
                        match = re.search(br'\x00UnityPlayer\/([^\x20]+)', file_data2)

            if match and match.group(1).decode('utf-8') == '%s':
                # There can be multiple "*_Data" folders if there are multiple
                # Unity .exe files, so we have to pick the folder corresponding
                # to this .exe.
                ggm_file = exe_path / (exe.stem + '_Data') / 'globalgamemanagers'
                if ggm_file.exists():
                    file_data2 = open(ggm_file, 'rb').read()
                    match = re.search(br'\x00(\d{1,4}\.\d+\.\d+[a-z]+\d+)\x00', file_data2)

            if not found and match is not None:
                found = True
                print("Found Unity version: " + match.group(1).decode('utf-8'))
                return "Unity", match.group(1).decode('utf-8')

            match = re.search(br'Made with GameMaker: Studio\x00', file_data)
            if not found and match is not None:
                found = True
                print("Found GameMaker")
                return "GameMaker", None
            else: # Fallback, Windows only
                match = re.search(br'name="YoYoGames.GameMaker.Runner"', file_data)
                if not found and match is not None:
                    found = True
                    print("Found GameMaker")
                    return "GameMaker", None

            match = re.search(br'Unreal Engine 3 Licensee\x00{4}Unreal Engine 3', file_data)
            if not found and match is not None:
                found = True
                print("Found Unreal Engine version: 3")
                return "Unreal Engine 3", None

            # \UE4PrereqSetup (UNICODE)
            match = re.search(br'\x5C\x00\x55\x00\x45\x00\x34\x00\x50\x00\x72\x00\x65\x00\x72\x00\x65\x00\x71\x00\x53\x00\x65\x00\x74\x00\x75\x00\x70\x00', file_data)
            if not found and match is not None:
                found = True
                print("Found Unreal Engine version: 4")
                return "Unreal Engine 4", None

            match = re.search(br'org\/lwjgl\/LWJGL', file_data)
            if not found and match is not None:
                found = True
                print("Found LWJGL")
                return "LWJGL", None

            match = re.search(br'com\/badlogic\/gdx', file_data)
            # NW.js 29 includes this false positive string
            decoy_match = re.search(br"Heavily inspired by LibGDX's CanvasGraphicsRenderer:", file_data)
            if not found and match is not None and decoy_match is None:
                found = True
                print("Found LibGDX")
                return "LibGDX", None

            match = re.search(br'\r\nKirikiri Z Project Contributors\r\nW.Dee, casper', file_data)
            if not found and match is not None:
                found = True
                print("Found KiriKiri Z")
                return "KiriKiri Z", None

            match = re.search(br'\x00__ZL17mkxpDataDirectoryiPmm\x00', file_data)
            if match is None:
                # This string shows up in the Falcon-mkxp and mkxp-z forks.
                match = re.search(br'\x00_mkxp_kernel_caller_alias\x00', file_data)
            if not found and match is not None:
                # Try to detect which RGSS version is being used by mkxp.
                # First we try mkxp.conf, which takes highest priority.
                # TODO: also try mkxp.json, which is used by the mkxp-z fork.
                mkxp_conf_path = exe_path / "mkxp.conf"
                if mkxp_conf_path.exists():
                    with open(mkxp_conf_path) as mkxp_conf_file:
                        mkxp_conf = configparser.ConfigParser()
                        try:
                            # Workaround missing section header in mkxp.conf.
                            mkxp_conf.read_string('[top]\n' + mkxp_conf_file.read())
                            if 'rgssVersion' in mkxp_conf['top']:
                                mkxp_version = mkxp_conf['top']['rgssVersion']
                                mkxp_version = int(mkxp_version)
                                if mkxp_version == 1:
                                    found = True
                                    print("Found mkxp version: XP")
                                    return "mkxp", "XP"
                                if mkxp_version == 2:
                                    found = True
                                    print("Found mkxp version: VX")
                                    return "mkxp", "VX"
                                if mkxp_version == 3:
                                    found = True
                                    print("Found mkxp version: VX Ace")
                                    return "mkxp", "VX Ace"
                        except:
                            pass

                # If mkxp.conf doesn't list an RGSS version, or if it's 0, then fallback to Game.ini.
                ini_paths = exe_path.glob("*.ini")
                for i in ini_paths:
                    game_ini = configparser.ConfigParser()
                    try:
                        game_ini.read(i)
                    except UnicodeDecodeError:
                        # Workaround for Japanese games
                        game_ini.read(i, encoding='shift_jis')

                    # Each RGSS version uses a different Scripts archive extension.
                    if 'Game' in game_ini and 'Scripts' in game_ini['Game']:
                        mkxp_scripts = game_ini['Game']['Scripts']
                        if mkxp_scripts.endswith('.rxdata'):
                            found = True
                            print("Found mkxp version: XP")
                            return "mkxp", "XP"
                        if mkxp_scripts.endswith('.rvdata'):
                            found = True
                            print("Found mkxp version: VX")
                            return "mkxp", "VX"
                        if mkxp_scripts.endswith('.rvdata2'):
                            found = True
                            print("Found mkxp version: VX Ace")
                            return "mkxp", "VX Ace"

                # If Game.ini didn't list a Scripts path, then fallback to detecting the archive file directly.
                scripts_path = exe_path / "Data" / "Scripts.rxdata"
                if scripts_path.exists():
                    found = True
                    print("Found mkxp version: XP")
                    return "mkxp", "XP"
                scripts_path = exe_path / "Data" / "Scripts.rvdata"
                if scripts_path.exists():
                    found = True
                    print("Found mkxp version: VX")
                    return "mkxp", "VX"
                scripts_path = exe_path / "Data" / "Scripts.rvdata2"
                if scripts_path.exists():
                    found = True
                    print("Found mkxp version: VX Ace")
                    return "mkxp", "VX Ace"

                # We couldn't find the RGSS version.
                found = True
                print("Found mkxp")
                return "mkxp", None

            match = re.search(br'\x00Software\\(KADOKAWA|Enterbrain)\\RPG2000\x00', file_data)
            if not found and match is not None:
                found = True
                print("Found RPG Maker version: 2000")
                return "RPG Maker", "2000"

            match = re.search(br'\x00Software\\(KADOKAWA|Enterbrain)\\RPG2003\x00', file_data)
            if not found and match is not None:
                found = True
                print("Found RPG Maker version: 2003")
                return "RPG Maker", "2003"

            # Cocos2d (and Cocos2d-x)
            if not found:
                patterns = (
                    re.compile(br'\xFF{3}\x00([\d.]+)\x00{3}Jan\x00Feb'),
                    re.compile(br'</set>\x0A\x00\xFF{3}\x00cocos2d-x ([\d.]+)\x00'),
                )

                datas = [file_data]
                cocos2d_path = path / "libcocos2d.dll"
                if cocos2d_path.exists():
                    with open(cocos2d_path, 'rb') as f:
                        datas.append(f.read())

                for pattern, data in product(patterns, datas):
                        match = pattern.search(data)
                        if match:
                            return "Cocos2d", match.group(1)

            # RGSS3 Player (UNICODE)
            match = re.search(br'\x52\x00\x47\x00\x53\x00\x53\x00\x33\x00\x20\x00\x50\x00\x6C\x00\x61\x00\x79\x00\x65\x00\x72\x00', file_data)
            if not found and match is not None:
                found = True
                print("Found RPG Maker version: VX Ace")
                return "RPG Maker", "VX Ace"

            # Software\Enterbrain\RGSS3\RTP (UNICODE)
            match = re.search(br'\x53\x00\x6F\x00\x66\x00\x74\x00\x77\x00\x61\x00\x72\x00\x65\x00\x5C\x00\x45\x00\x6E\x00\x74\x00\x65\x00\x72\x00\x62\x00\x72\x00\x61\x00\x69\x00\x6E\x00\x5C\x00\x52\x00\x47\x00\x53\x00\x53\x00\x33\x00\x5C\x00\x52\x00\x54\x00\x50\x00', file_data)
            if not found and match is not None:
                found = True
                print("Found RPG Maker version: VX Ace")
                return "RPG Maker", "VX Ace"

            # RGSS2 Player (UNICODE)
            match = re.search(br'\x52\x00\x47\x00\x53\x00\x53\x00\x32\x00\x20\x00\x50\x00\x6C\x00\x61\x00\x79\x00\x65\x00\x72\x00', file_data)
            if not found and match is not None:
                found = True
                print("Found RPG Maker version: VX")
                return "RPG Maker", "VX"

            #RGSS Player (UNICODE)
            match = re.search(br'\x52\x00\x47\x00\x53\x00\x53\x00\x20\x00\x50\x00\x6C\x00\x61\x00\x79\x00\x65\x00\x72\x00', file_data)
            if not found and match is not None:
                found = True
                print("Found RPG Maker version: XP")
                return "RPG Maker", "XP"

            # This string shows up in NW.js used by RPG Maker MV
            match = re.search(br'\\node-webkit\\src\\[a-z]+\\nw\\', file_data)
            if match is None:
                # This string shows up in NW.js used by RPG Maker MZ
                match = re.search(br'nw\.exe\.pdb', file_data)
            if not found and match is not None:
                # NW.js; might or might not be RPG Maker
                js_files = exe_path.rglob('*.js')
                match_name = None
                match_version = None
                for js in js_files:
                    with open(js, 'rb') as js_file:
                        js_data = js_file.read()
                        if match_name is None:
                            # MV and MZ use different quote marks
                            match_name = re.search(br"Utils\.RPGMAKER_NAME = ['\"]([A-Za-z]+)['\"];", js_data)
                            if match_name is not None:
                                match_name = match_name.group(1).decode()
                        if match_version is None:
                            # MV and MZ use different quote marks
                            match_version = re.search(br"Utils\.RPGMAKER_VERSION = ['\"]([0-9\.]+)['\"];", js_data)
                            if match_version is not None:
                                match_version = match_version.group(1).decode()
                        if match_name is not None and match_version is not None:
                            break
                if match_name is not None and match_version is not None:
                    found = True
                    combined_version = match_name + ' ' + match_version
                    print("Found RPG Maker version: " + combined_version)
                    return "RPG Maker", combined_version
                else:
                    found = True
                    print("Found NW.js")
                    return "NW.js", None

            match = re.search(br'ShiVa 3D Standalone Engine ([^\x20]+)', file_data)
            if not found and match is not None:
                found = True
                print("Found ShiVa Engine version: " + match.group(1).decode('utf-8'))
                return "ShiVa Engine", match.group(1).decode('utf-8')

            match = re.search(br'\x00WOLF_FileReadText', file_data)
            if not found and match is not None:
                found = True
                print("Found WOLF RPG Editor")
                return "WOLF RPG Editor", None

            if found is False:
                print("Version not found !!!")
                return None, None
 
def set_clip_detect():
    set_clip("QUIT PREMATURELY");
    name, version = detect(sys.argv[1])
    if name is None:
        name = '!!!'
    set_clip_v(name, version)

def set_clip(text):
    r = Tk()
    r.withdraw()
    r.clipboard_clear()
    r.clipboard_append(text)
    print(r.clipboard_get())
    r.destroy()

def set_clip_v(name, version=None):
    build_major_string = ""
    build_full_string = ""
    if version is not None:
        m = re.search(r'^([^\.]+)', version)
        build_major_string = "|name=" + name + " " + m.group(0)
        if m.group(0) != version:
            build_full_string = "|build=" + version
    out_string = "{{Infobox game/row/engine|" + name + build_major_string \
    + "|ref=<ref name=\"engineversion\">{{Refcheck|user=" + username + "|date=" \
    + datetime.datetime.utcnow().isoformat()[:10] + "}}</ref>" + build_full_string + "}}"
    set_clip(out_string)

if __name__ == "__main__":
    set_clip_detect()
