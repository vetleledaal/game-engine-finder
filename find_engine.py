#!/usr/bin/env python
import sys, os, re, datetime, time, struct, glob
from itertools import product
from tkinter import Tk

username = "Vetle" # PCGamingWiki username to be linked in refcheck

# https://en.wikipedia.org/wiki/List_of_game_engines
#
#
# AGS - Adventure Game Studio (2.72 checked) -- ????
# /ACI version (\d\.[\w\s\-]{1,8}(?:\.[\w\s\-]{1,8})?)[\n\)\[,]/

def detect(exe):
	found = False
	# Check dir struct
	exe_path = os.path.dirname(exe)

	path = os.path.join(exe_path, "Adobe AIR")
	if(not found and os.path.exists(path)):
		# Probably Adobe AIR (not tested)
		print('Found Adobe AIR')
		return "Adobe AIR", None

	path = os.path.join(exe_path, "renpy")
	if(not found and os.path.exists(path)):
		# Probably renpy project
		# Get version from files...
		init_file = os.path.join(path, "__init__.pyo")
		vc_version_file = os.path.join(path, "vc_version.pyo")
		match1 = None
		match2 = None
		if(os.path.exists(init_file) and os.path.exists(vc_version_file)):
			with open(init_file, 'rb') as file:
				file_data = file.read()
				match1 = re.search(re.compile(br'vc_versioni\x00{4}((?:i.{4}){3,5})s', re.DOTALL), file_data)
				if(match1):
					match1 = struct.unpack("<" + ("cI" * (len(match1.group(1))//5)), match1.group(1))
					match1 = ".".join(map(str, match1[1::2]))
			if match1 is None:
				# Parsing init binary failed, fall back to parsing init source
				init_src_file = os.path.join(path, "__init__.py")
				if(os.path.exists(init_src_file)):
					with open(init_src_file, 'r') as file:
						file_data = file.read()
						match1_candidates = re.finditer(re.compile(r'version_tuple = \(([0-9]+, [0-9]+, [0-9]+), vc_version\)', re.DOTALL), file_data)
						for match1_candidate in match1_candidates:
							match1_candidate = match1_candidate.group(1)
							match1_candidate = match1_candidate.replace(', ', '.')
							if int(match1_candidate[:1]) <= 7:
								# RenPy 7.x or lower, if Python 2
								pythonpath = os.path.join(exe_path, "lib", "python2.*")
								pythonglob = glob.glob(pythonpath)
								if len(pythonglob) > 0:
								    match1 = match1_candidate
							else:
								# RenPy 8.x or higher, if Python 3
								pythonpath = os.path.join(exe_path, "lib", "python3.*")
								pythonglob = glob.glob(pythonpath)
								if len(pythonglob) > 0:
								    match1 = match1_candidate
			with open(vc_version_file, 'rb') as file:
				file_data = file.read()
				match2 = re.search(re.compile(br'\x00{3}(i.{4})', re.DOTALL), file_data)
				if(match2):
					match2 = struct.unpack("<cI", match2.group(1))
					match2 = ".".join(map(str, match2[1::2]))
		if(match1 is not None and match2 is not None):
			found = True
			ver = ".".join([match1, match2])
			print("Found Ren'Py version: " + ver)
			return "Ren'Py", ver
		else:
			print("Found Ren'Py, no ver")
			print(match1 is not None)
			print(match2 is not None)

	if(not found):
		with open(exe, 'rb') as file:
			file_data = file.read()

			match = re.search(br'\x00UnityPlayer\/([^\x20]+)', file_data)

			if(match is None):
				player_file = os.path.join(exe_path, "UnityPlayer.dll")
				if(os.path.exists(player_file)):
					with(open(player_file, 'rb')) as file2:
						file_data2 = file2.read()
						match = re.search(br'\x00UnityPlayer\/([^\x20]+)', file_data2)

			if match and match.group(1).decode('utf-8') == '%s':
				ggm_files = glob.glob(os.path.join(exe_path, '*Data', 'globalgamemanagers'))
				if ggm_files:
					file_data2 = open(ggm_files[0], 'rb').read()
					match = re.search(br'\x00(\d{1,4}\.\d+\.\d+[a-z]+\d+)\x00', file_data2)

			if(not found and match is not None):
				found = True
				print("Found Unity version: " + match.group(1).decode('utf-8'))
				return "Unity", match.group(1).decode('utf-8')

			match = re.search(br'Made with GameMaker: Studio\x00', file_data)
			if(not found and match is not None):
				found = True
				print("Found GameMaker")
				return "GameMaker", None
			else: # Fallback, Windows only
				match = re.search(br'name="YoYoGames.GameMaker.Runner"', file_data)
				if(not found and match is not None):
					found = True
					print("Found GameMaker")
					return "GameMaker", None

			match = re.search(br'Unreal Engine 3 Licensee\x00{4}Unreal Engine 3', file_data)
			if(not found and match is not None):
				found = True
				print("Found Unreal Engine version: 3")
				return "Unreal Engine 3", None

			# \UE4PrereqSetup (UNICODE)
			match = re.search(br'\x5C\x00\x55\x00\x45\x00\x34\x00\x50\x00\x72\x00\x65\x00\x72\x00\x65\x00\x71\x00\x53\x00\x65\x00\x74\x00\x75\x00\x70\x00', file_data)
			if(not found and match is not None):
				found = True
				print("Found Unreal Engine version: 4")
				return "Unreal Engine 4", None

			match = re.search(br'org\/lwjgl\/LWJGL', file_data)
			if(not found and match is not None):
				found = True
				print("Found LWJGL")
				return "LWJGL", None

			match = re.search(br'com\/badlogic\/gdx', file_data)
			# NW.js 29 includes this false positive string
			decoy_match = re.search(br"Heavily inspired by LibGDX's CanvasGraphicsRenderer:", file_data)
			if(not found and match is not None and decoy_match is None):
				found = True
				print("Found LibGDX")
				return "LibGDX", None

			match = re.search(br'\r\nKirikiri Z Project Contributors\r\nW.Dee, casper', file_data)
			if(not found and match is not None):
				found = True
				print("Found KiriKiri Z")
				return "KiriKiri Z", None

			match = re.search(br'\x00__ZL17mkxpDataDirectoryiPmm\x00', file_data)
			if match is None:
				# This string shows up in the Falcon-mkxp and mkxp-z forks.
				match = re.search(br'\x00_mkxp_kernel_caller_alias\x00', file_data)
			if(not found and match is not None):
				found = True
				print("Found mkxp")
				return "mkxp", None

			match = re.search(br'\x00Software\\(KADOKAWA|Enterbrain)\\RPG2000\x00', file_data)
			if(not found and match is not None):
				found = True
				print("Found RPG Maker version: 2000")
				return "RPG Maker", "2000"

			match = re.search(br'\x00Software\\(KADOKAWA|Enterbrain)\\RPG2003\x00', file_data)
			if(not found and match is not None):
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
				cocos2d_path = os.path.join(path, "libcocos2d.dll")
				if os.path.exists(cocos2d_path):
					with open(cocos2d_path, 'rb') as f:
						datas.append(f.read())

				for pattern, data in product(patterns, datas):
						match = pattern.search(data)
						if match:
							return "Cocos2d", match.group(1)

			# RGSS3 Player (UNICODE)
			match = re.search(br'\x52\x00\x47\x00\x53\x00\x53\x00\x33\x00\x20\x00\x50\x00\x6C\x00\x61\x00\x79\x00\x65\x00\x72\x00', file_data)
			if(not found and match is not None):
				found = True
				print("Found RPG Maker version: VX Ace")
				return "RPG Maker", "VX Ace"

			# Software\Enterbrain\RGSS3\RTP (UNICODE)
			match = re.search(br'\x53\x00\x6F\x00\x66\x00\x74\x00\x77\x00\x61\x00\x72\x00\x65\x00\x5C\x00\x45\x00\x6E\x00\x74\x00\x65\x00\x72\x00\x62\x00\x72\x00\x61\x00\x69\x00\x6E\x00\x5C\x00\x52\x00\x47\x00\x53\x00\x53\x00\x33\x00\x5C\x00\x52\x00\x54\x00\x50\x00', file_data)
			if(not found and match is not None):
				found = True
				print("Found RPG Maker version: VX Ace")
				return "RPG Maker", "VX Ace"

			# RGSS2 Player (UNICODE)
			match = re.search(br'\x52\x00\x47\x00\x53\x00\x53\x00\x32\x00\x20\x00\x50\x00\x6C\x00\x61\x00\x79\x00\x65\x00\x72\x00', file_data)
			if(not found and match is not None):
				found = True
				print("Found RPG Maker version: VX")
				return "RPG Maker", "VX"

			#RGSS Player (UNICODE)
			match = re.search(br'\x52\x00\x47\x00\x53\x00\x53\x00\x20\x00\x50\x00\x6C\x00\x61\x00\x79\x00\x65\x00\x72\x00', file_data)
			if(not found and match is not None):
				found = True
				print("Found RPG Maker version: XP")
				return "RPG Maker", "XP"

			# This string shows up in NW.js used by RPG Maker MV
			match = re.search(br'\\node-webkit\\src\\[a-z]+\\nw\\', file_data)
			if match is None:
				# This string shows up in NW.js used by RPG Maker MZ
				match = re.search(br'nw\.exe\.pdb', file_data)
			if(not found and match is not None):
				# NW.js; might or might not be RPG Maker
				js_path = os.path.join(exe_path, '**', '*.js')
				js_glob = glob.glob(js_path, recursive=True)
				match_name = None
				match_version = None
				for js in js_glob:
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
			if(not found and match is not None):
				found = True
				print("Found ShiVa Engine version: " + match.group(1).decode('utf-8'))
				return "ShiVa Engine", match.group(1).decode('utf-8')

			match = re.search(br'\x00WOLF_FileReadText', file_data)
			if(not found and match is not None):
				found = True
				print("Found WOLF RPG Editor")
				return "WOLF RPG Editor", None

			if(found is False):
				print("Version not found !!!")
				return "!!!", None
			file.close()
 
def set_clip_detect():
	set_clip("QUIT PREMATURELY");
	name, version = detect(sys.argv[1])
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
	if(version is not None):
		m = re.search(r'^([^\.]+)', version)
		build_major_string = "|name=" + name + " " + m.group(0)
		if(m.group(0) != version):
			build_full_string = "|build=" + version
	out_string = "{{Infobox game/row/engine|" + name + build_major_string \
	+ "|ref=<ref name=\"engineversion\">{{Refcheck|user=" + username + "|date=" \
	+ datetime.datetime.utcnow().isoformat()[:10] + "}}</ref>" + build_full_string + "}}"
	set_clip(out_string)

if __name__ == "__main__":
	set_clip_detect()
