# -*- coding: utf-8 -*-
import sys, os, re, datetime, time, struct
try:
	from tkinter import Tk
except ImportError:
	from Tkinter import Tk  # PY2

username = "Vetle" # PCGamingWiki username to be linked in refcheck

# https://en.wikipedia.org/wiki/List_of_game_engines
#
#
# AGS - Adventure Game Studio (2.72 checked) -- ????
# /ACI version (\d\.[\w\s\-]{1,8}(?:\.[\w\s\-]{1,8})?)[\n\)\[,]/

def main():
	set_clip("QUIT PREMATURELY");
	found = False
	# Check dir struct
	exe_path = os.path.dirname(sys.argv[1])

	path = os.path.join(exe_path, "Adobe AIR")
	if(not found and os.path.exists(path)):
		# Probably Adobe AIR (not tested)
		print('Found Adobe AIR')
		set_clip_v("Adobe AIR")
		found = True

	path = os.path.join(exe_path, "renpy")
	if(not found and os.path.exists(path)):
		# Probably renpy project
		# Get version from files...
		init_file = os.path.join(path, "__init__.pyo")
		vc_version_file = os.path.join(path, "vc_version.pyo")
		if(os.path.exists(init_file) and os.path.exists(vc_version_file)):
			match1 = None
			match2 = None
			with open(init_file, 'rb') as file:
				file_data = file.read()
				match1 = re.search(re.compile(br'vc_versioni\x00{4}((?:i.{4}){3,5})s', re.DOTALL), file_data)
				if(match1):
					match1 = struct.unpack("<" + ("cI" * (len(match1.group(1))//5)), match1.group(1))
			with open(vc_version_file, 'rb') as file:
				file_data = file.read()
				match2 = re.search(re.compile(br'\x00{3}(i.{4})', re.DOTALL), file_data)
				if(match2):
					match2 = struct.unpack("<cI", match2.group(1))
		if(match1 is not None and match2 is not None):
			found = True
			ver = ".".join(map(str, match1[1::2] + match2[1::2]))
			print("Found Ren'Py version: " + ver)
			set_clip_v("Ren'Py", ver)
		else:
			print("Found Ren'Py, no ver")
			print(match1 is not None)
			print(match2 is not None)

	if(not found):
		with open(sys.argv[1], 'rb') as file:
			file_data = file.read()

			match = re.search(br'\x00UnityPlayer\/([^\x20]+)', file_data)

			if(match is None):
				player_file = os.path.join(exe_path, "UnityPlayer.dll")
				if(os.path.exists(player_file)):
					with(open(player_file, 'rb')) as file2:
						file_data2 = file2.read()
						match = re.search(br'\x00UnityPlayer\/([^\x20]+)', file_data2)
			if(not found and match is not None):
				found = True
				print("Found Unity version: " + match.group(1).decode('utf-8'))
				set_clip_v("Unity", match.group(1).decode('utf-8'))

			match = re.search(br'name="YoYoGames.GameMaker.Runner"', file_data)
			if(not found and match is not None):
				found = True
				print("Found GameMaker")
				set_clip_v("GameMaker")

			match = re.search(br'Unreal Engine 3 Licensee\x00{4}Unreal Engine 3', file_data)
			if(not found and match is not None):
				found = True
				print("Found Unreal Engine version: 3")
				set_clip_v("Unreal Engine 3")

			# \UE4PrereqSetup (UNICODE)
			match = re.search(br'\x5C\x00\x55\x00\x45\x00\x34\x00\x50\x00\x72\x00\x65\x00\x72\x00\x65\x00\x71\x00\x53\x00\x65\x00\x74\x00\x75\x00\x70\x00', file_data)
			if(not found and match is not None):
				found = True
				print("Found Unreal Engine version: 4")
				set_clip_v("Unreal Engine 4")

			match = re.search(br'\r\nKirikiri Z Project Contributors\r\nW.Dee, casper', file_data)
			if(not found and match is not None):
				found = True
				print("Found KiriKiri Z")
				set_clip_v("KiriKiri Z")

			match = re.search(br'\x00__ZL17mkxpDataDirectoryiPmm\x00', file_data)
			if(not found and match is not None):
				found = True
				print("Found mkxp")
				set_clip_v("mkxp")

			match = re.search(br'\x00Software\\(KADOKAWA|Enterbrain)\\RPG2000\x00', file_data)
			if(not found and match is not None):
				found = True
				print("Found RPG Maker version: 2000")
				set_clip_v("RPG Maker", "2000")

			match = re.search(br'\x00Software\\(KADOKAWA|Enterbrain)\\RPG2003\x00', file_data)
			if(not found and match is not None):
				found = True
				print("Found RPG Maker version: 2003")
				set_clip_v("RPG Maker", "2003")



			# RGSS3 Player (UNICODE)
			match = re.search(br'\x52\x00\x47\x00\x53\x00\x53\x00\x33\x00\x20\x00\x50\x00\x6C\x00\x61\x00\x79\x00\x65\x00\x72\x00', file_data)
			if(not found and match is not None):
				found = True
				print("Found RPG Maker version: VX Ace")
				set_clip_v("RPG Maker", "VX Ace")

			# Software\Enterbrain\RGSS3\RTP (UNICODE)
			match = re.search(br'\x53\x00\x6F\x00\x66\x00\x74\x00\x77\x00\x61\x00\x72\x00\x65\x00\x5C\x00\x45\x00\x6E\x00\x74\x00\x65\x00\x72\x00\x62\x00\x72\x00\x61\x00\x69\x00\x6E\x00\x5C\x00\x52\x00\x47\x00\x53\x00\x53\x00\x33\x00\x5C\x00\x52\x00\x54\x00\x50\x00', file_data)
			if(not found and match is not None):
				found = True
				print("Found RPG Maker version: VX Ace")
				set_clip_v("RPG Maker", "VX Ace")

			# RGSS2 Player (UNICODE)
			match = re.search(br'\x52\x00\x47\x00\x53\x00\x53\x00\x32\x00\x20\x00\x50\x00\x6C\x00\x61\x00\x79\x00\x65\x00\x72\x00', file_data)
			if(not found and match is not None):
				found = True
				print("Found RPG Maker version: VX")
				set_clip_v("RPG Maker", "VX")

			#RGSS Player (UNICODE)
			match = re.search(br'\x52\x00\x47\x00\x53\x00\x53\x00\x20\x00\x50\x00\x6C\x00\x61\x00\x79\x00\x65\x00\x72\x00', file_data)
			if(not found and match is not None):
				found = True
				print("Found RPG Maker version: XP")
				set_clip_v("RPG Maker", "XP")

			match = re.search(br'd:\\slave\\win32_nw12\\node-webkit\\src\\content\\nw\\src\\shell_main\.cc', file_data)
			if(not found and match is not None):
				found = True
				print("Found RPG Maker version: MV")
				set_clip_v("RPG Maker", "MV")

			match = re.search(br'ShiVa 3D Standalone Engine ([^\x20]+)', file_data)
			if(not found and match is not None):
				found = True
				print("Found ShiVa Engine version: " + match.group(1).decode('utf-8'))
				set_clip_v("ShiVa Engine", match.group(1).decode('utf-8'))

			match = re.search(br'\x00WOLF_FileReadText', file_data)
			if(not found and match is not None):
				found = True
				print("Found WOLF RPG Editor")
				set_clip_wolf()
				set_clip_v("WOLF RPG Editor")

			if(found is False):
				print("Version not found !!!")
				set_clip_v("!!!")
				time.sleep(2)
			file.close()
 
def set_clip(text):
	r = Tk()
	r.withdraw()
	r.clipboard_clear()
	r.clipboard_append(text)
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
	main()
