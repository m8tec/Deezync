from pathlib import Path
import sys
import os
import re
from deemix.utils import canWrite

homedata = Path.home()
userdata = ""
musicdata = ""

def checkPath(path):
    if path == "": return ""
    if not path.is_dir(): return ""
    if not canWrite(path): return ""
    return path

def getConfigFolder():
    global userdata
    if userdata != "": return userdata
    if os.getenv("XDG_CONFIG_HOME") and userdata == "":
        userdata = Path(os.getenv("XDG_CONFIG_HOME"))
        userdata = checkPath(userdata)
    if os.getenv("APPDATA") and userdata == "":
        userdata = Path(os.getenv("APPDATA"))
        userdata = checkPath(userdata)
    if sys.platform.startswith('darwin') and userdata == "":
        userdata = homedata / 'Library' / 'Application Support'
        userdata = checkPath(userdata)
    if userdata == "":
        userdata = homedata / '.config'
        userdata = checkPath(userdata)

    if userdata == "": userdata = Path(os.getcwd()) / 'config'
    else: userdata = userdata / 'deemix'

    if os.getenv("DEEMIX_DATA_DIR"):
        userdata = Path(os.getenv("DEEMIX_DATA_DIR"))
    return userdata

def getMusicFolder():
    global musicdata
    if musicdata != "": return musicdata
    if os.getenv("XDG_MUSIC_DIR") and musicdata == "":
        musicdata = Path(os.getenv("XDG_MUSIC_DIR"))
        musicdata = checkPath(musicdata)
    if (homedata / '.config' / 'user-dirs.dirs').is_file() and musicdata == "":
        with open(homedata / '.config' / 'user-dirs.dirs', 'r', encoding="utf-8") as f:
            userDirs = f.read()
        musicdata_search = re.search(r"XDG_MUSIC_DIR=\"(.*)\"", userDirs)
        if musicdata_search:
            musicdata = musicdata_search.group(1)
            musicdata = Path(os.path.expandvars(musicdata))
            musicdata = checkPath(musicdata)
    if os.name == 'nt' and musicdata == "":
        try:
            musicKeys = ['My Music', '{4BD8D571-6D19-48D3-BE97-422220080E43}']
            regData = os.popen(r'reg.exe query "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"').read().split('\r\n')
            for i, line in enumerate(regData):
                if line == "": continue
                if i == 1: continue
                line = line.split('    ')
                if line[1] in musicKeys:
                    musicdata = Path(line[3])
                    break
            musicdata = checkPath(musicdata)
        except Exception:
            musicdata = ""
    if musicdata == "":
        musicdata = homedata / 'Music'
        musicdata = checkPath(musicdata)

    if musicdata == "": musicdata = Path(os.getcwd()) / 'music'
    else: musicdata = musicdata / 'deemix Music'

    if os.getenv("DEEMIX_MUSIC_DIR"):
        musicdata = Path(os.getenv("DEEMIX_MUSIC_DIR"))
    return musicdata
