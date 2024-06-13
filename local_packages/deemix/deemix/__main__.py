#!/usr/bin/env python3
import click
from pathlib import Path

from deezer import Deezer
from deezer import TrackFormats

from deemix import generateDownloadObject
from deemix.settings import load as loadSettings
from deemix.utils import getBitrateNumberFromText, formatListener
import deemix.utils.localpaths as localpaths
from deemix.downloader import Downloader
from deemix.itemgen import GenerationError
try:
    from deemix.plugins.spotify import Spotify
except ImportError:
    Spotify = None

class LogListener:
    @classmethod
    def send(cls, key, value=None):
        logString = formatListener(key, value)
        if logString: print(logString)


@click.command()
@click.option('--portable', is_flag=True, help='Creates the config folder in the same directory where the script is launched')
@click.option('-b', '--bitrate', default=None, help='Overwrites the default bitrate selected')
@click.option('-p', '--path', type=str, help='Downloads in the given folder')
@click.argument('url', nargs=-1, required=True)
def download(url, bitrate, portable, path):
    # Check for local configFolder
    localpath = Path('.')
    configFolder = localpath / 'config' if portable else localpaths.getConfigFolder()

    settings = loadSettings(configFolder)
    dz = Deezer()
    listener = LogListener()

    def requestValidArl():
        while True:
            arl = input("Paste here your arl:")
            if dz.login_via_arl(arl.strip()): break
        return arl

    if (configFolder / '.arl').is_file():
        with open(configFolder / '.arl', 'r', encoding="utf-8") as f:
            arl = f.readline().rstrip("\n").strip()
        if not dz.login_via_arl(arl): arl = requestValidArl()
    else: arl = requestValidArl()
    with open(configFolder / '.arl', 'w', encoding="utf-8") as f:
        f.write(arl)

    plugins = {}
    if Spotify:
        plugins = {
            "spotify": Spotify(configFolder=configFolder)
        }
        plugins["spotify"].setup()

    def downloadLinks(url, bitrate=None):
        if not bitrate: bitrate = settings.get("maxBitrate", TrackFormats.MP3_320)
        links = []
        for link in url:
            if ';' in link:
                for l in link.split(";"):
                    links.append(l)
            else:
                links.append(link)

        downloadObjects = []

        for link in links:
            try:
                downloadObject = generateDownloadObject(dz, link, bitrate, plugins, listener)
            except GenerationError as e:
                print(f"{e.link}: {e.message}")
                continue
            if isinstance(downloadObject, list):
                downloadObjects += downloadObject
            else:
                downloadObjects.append(downloadObject)

        for obj in downloadObjects:
            if obj.__type__ == "Convertable":
                obj = plugins[obj.plugin].convert(dz, obj, settings, listener)
            Downloader(dz, obj, settings, listener).start()


    if path is not None:
        if path == '': path = '.'
        path = Path(path)
        settings['downloadLocation'] = str(path)
    url = list(url)
    if bitrate: bitrate = getBitrateNumberFromText(bitrate)

    # If first url is filepath readfile and use them as URLs
    try:
        isfile = Path(url[0]).is_file()
    except Exception:
        isfile = False
    if isfile:
        filename = url[0]
        with open(filename, encoding="utf-8") as f:
            url = f.readlines()

    downloadLinks(url, bitrate)
    click.echo("All done!")

if __name__ == '__main__':
    download() # pylint: disable=E1120
