import re
from os.path import sep as pathSep
from pathlib import Path
from unicodedata import normalize
from deezer import TrackFormats

bitrateLabels = {
    TrackFormats.MP4_RA3: "360 HQ",
    TrackFormats.MP4_RA2: "360 MQ",
    TrackFormats.MP4_RA1: "360 LQ",
    TrackFormats.FLAC   : "FLAC",
    TrackFormats.MP3_320: "320",
    TrackFormats.MP3_128: "128",
    TrackFormats.DEFAULT: "128",
    TrackFormats.LOCAL  : "MP3"
}

def fixName(txt, char='_'):
    txt = str(txt)
    txt = re.sub(r'[\0\/\\:*?"<>|]', char, txt)
    txt = normalize("NFC", txt)
    return txt

def fixLongName(name):
    def fixEndOfData(bString):
        try:
            bString.decode()
            return True
        except Exception:
            return False
    if pathSep in name:
        sepName = name.split(pathSep)
        name = ""
        for txt in sepName:
            txt = fixLongName(txt)
            name += txt + pathSep
        name = name[:-1]
    else:
        name = name.encode('utf-8')[:200]
        while not fixEndOfData(name):
            name = name[:-1]
        name = name.decode()
    return name


def antiDot(string):
    while string[-1:] == "." or string[-1:] == " " or string[-1:] == "\n":
        string = string[:-1]
    if len(string) < 1:
        string = "dot"
    return string


def pad(num, max_val, settings):
    if int(settings['paddingSize']) == 0:
        paddingSize = len(str(max_val))
    else:
        paddingSize = len(str(10 ** (int(settings['paddingSize']) - 1)))
    if paddingSize == 1:
        paddingSize = 2
    if settings['padTracks']:
        return str(num).zfill(paddingSize)
    return str(num)

def generatePath(track, downloadObject, settings):
    filenameTemplate = "%artist% - %title%"
    singleTrack = False
    if downloadObject.type == "track":
        if settings['createSingleFolder']:
            filenameTemplate = settings['albumTracknameTemplate']
        else:
            filenameTemplate = settings['tracknameTemplate']
        singleTrack = True
    elif downloadObject.type == "album":
        filenameTemplate = settings['albumTracknameTemplate']
    else:
        filenameTemplate = settings['playlistTracknameTemplate']

    filename = generateTrackName(filenameTemplate, track, settings)

    filepath = Path(settings['downloadLocation'] or '.')
    artistPath = None
    coverPath = None
    extrasPath = None

    if settings['createPlaylistFolder'] and track.playlist and not settings['tags']['savePlaylistAsCompilation']:
        filepath = filepath / generatePlaylistName(settings['playlistNameTemplate'], track.playlist, settings)

    if track.playlist and not settings['tags']['savePlaylistAsCompilation']:
        extrasPath = filepath

    if (
        (settings['createArtistFolder'] and not track.playlist) or
        (settings['createArtistFolder'] and track.playlist and settings['tags']['savePlaylistAsCompilation']) or
        (settings['createArtistFolder'] and track.playlist and settings['createStructurePlaylist'])
    ):
        filepath = filepath / generateArtistName(settings['artistNameTemplate'], track.album.mainArtist, settings, rootArtist=track.album.rootArtist)
        artistPath = filepath

    if (settings['createAlbumFolder'] and
            (not singleTrack or (singleTrack and settings['createSingleFolder'])) and
            (not track.playlist or
                (track.playlist and settings['tags']['savePlaylistAsCompilation']) or
                (track.playlist and settings['createStructurePlaylist'])
            )
    ):
        filepath = filepath / generateAlbumName(settings['albumNameTemplate'], track.album, settings, track.playlist)
        coverPath = filepath

    if not extrasPath: extrasPath = filepath

    if (
        int(track.album.discTotal) > 1 and (
            (settings['createAlbumFolder'] and settings['createCDFolder']) and
            (not singleTrack or (singleTrack and settings['createSingleFolder'])) and
            (not track.playlist or
                (track.playlist and settings['tags']['savePlaylistAsCompilation']) or
                (track.playlist and settings['createStructurePlaylist'])
        )
    )):
        filepath = filepath / f'CD{track.discNumber}'

    # Remove subfolders from filename and add it to filepath
    if pathSep in filename:
        tempPath = filename[:filename.rfind(pathSep)]
        filepath = filepath / tempPath
        filename = filename[filename.rfind(pathSep) + len(pathSep):]

    return (filename, filepath, artistPath, coverPath, extrasPath)


def generateTrackName(filename, track, settings):
    c = settings['illegalCharacterReplacer']
    filename = filename.replace("%title%", fixName(track.title, c))
    filename = filename.replace("%artist%", fixName(track.mainArtist.name, c))
    filename = filename.replace("%artists%", fixName(", ".join(track.artists), c))
    filename = filename.replace("%allartists%", fixName(track.artistsString, c))
    filename = filename.replace("%mainartists%", fixName(track.mainArtistsString, c))
    if track.featArtistsString:
        filename = filename.replace("%featartists%", fixName('('+track.featArtistsString+')', c))
    else:
        filename = filename.replace("%featartists%", '')
    filename = filename.replace("%album%", fixName(track.album.title, c))
    filename = filename.replace("%albumartist%", fixName(track.album.mainArtist.name, c))
    filename = filename.replace("%tracknumber%", pad(track.trackNumber, track.album.trackTotal, settings))
    filename = filename.replace("%tracktotal%", str(track.album.trackTotal))
    filename = filename.replace("%discnumber%", str(track.discNumber))
    filename = filename.replace("%disctotal%", str(track.album.discTotal))
    if len(track.album.genre) > 0:
        filename = filename.replace("%genre%", fixName(track.album.genre[0], c))
    else:
        filename = filename.replace("%genre%", "Unknown")
    filename = filename.replace("%year%", str(track.date.year))
    filename = filename.replace("%date%", track.dateString)
    filename = filename.replace("%bpm%", str(track.bpm))
    filename = filename.replace("%label%", fixName(track.album.label, c))
    filename = filename.replace("%isrc%", track.ISRC)
    if (track.album.barcode):
        filename = filename.replace("%upc%", track.album.barcode)
    filename = filename.replace("%explicit%", "(Explicit)" if track.explicit else "")

    filename = filename.replace("%track_id%", str(track.id))
    filename = filename.replace("%album_id%", str(track.album.id))
    filename = filename.replace("%artist_id%", str(track.mainArtist.id))
    if track.playlist:
        filename = filename.replace("%playlist_id%", str(track.playlist.playlistID))
        filename = filename.replace("%position%", pad(track.position, track.playlist.trackTotal, settings))
    else:
        filename = filename.replace("%playlist_id%", '')
        filename = filename.replace("%position%", pad(track.position, track.album.trackTotal, settings))
    filename = filename.replace('\\', pathSep).replace('/', pathSep)
    return antiDot(fixLongName(filename))


def generateAlbumName(foldername, album, settings, playlist=None):
    c = settings['illegalCharacterReplacer']
    if playlist and settings['tags']['savePlaylistAsCompilation']:
        foldername = foldername.replace("%album_id%", "pl_" + str(playlist.playlistID))
        foldername = foldername.replace("%genre%", "Compile")
    else:
        foldername = foldername.replace("%album_id%", str(album.id))
        if len(album.genre) > 0:
            foldername = foldername.replace("%genre%", fixName(album.genre[0], c))
        else:
            foldername = foldername.replace("%genre%", "Unknown")
    foldername = foldername.replace("%album%", fixName(album.title, c))
    foldername = foldername.replace("%artist%", fixName(album.mainArtist.name, c))
    foldername = foldername.replace("%artist_id%", str(album.mainArtist.id))
    if album.rootArtist:
        foldername = foldername.replace("%root_artist%", fixName(album.rootArtist.name, c))
        foldername = foldername.replace("%root_artist_id%", str(album.rootArtist.id))
    else:
        foldername = foldername.replace("%root_artist%", fixName(album.mainArtist.name, c))
        foldername = foldername.replace("%root_artist_id%", str(album.mainArtist.id))
    foldername = foldername.replace("%tracktotal%", str(album.trackTotal))
    foldername = foldername.replace("%disctotal%", str(album.discTotal))
    if album.recordType:
        foldername = foldername.replace("%type%", fixName(album.recordType.capitalize(), c))
    if album.barcode:
        foldername = foldername.replace("%upc%", album.barcode)
    foldername = foldername.replace("%explicit%", "(Explicit)" if album.explicit else "")
    foldername = foldername.replace("%label%", fixName(album.label, c))
    foldername = foldername.replace("%year%", str(album.date.year))
    foldername = foldername.replace("%date%", album.dateString)
    foldername = foldername.replace("%bitrate%", bitrateLabels[int(album.bitrate)])

    foldername = foldername.replace('\\', pathSep).replace('/', pathSep)
    return antiDot(fixLongName(foldername))


def generateArtistName(foldername, artist, settings, rootArtist=None):
    c = settings['illegalCharacterReplacer']
    foldername = foldername.replace("%artist%", fixName(artist.name, c))
    foldername = foldername.replace("%artist_id%", str(artist.id))
    if rootArtist:
        foldername = foldername.replace("%root_artist%", fixName(rootArtist.name, c))
        foldername = foldername.replace("%root_artist_id%", str(rootArtist.id))
    else:
        foldername = foldername.replace("%root_artist%", fixName(artist.name, c))
        foldername = foldername.replace("%root_artist_id%", str(artist.id))
    foldername = foldername.replace('\\', pathSep).replace('/', pathSep)
    return antiDot(fixLongName(foldername))


def generatePlaylistName(foldername, playlist, settings):
    c = settings['illegalCharacterReplacer']
    foldername = foldername.replace("%playlist%", fixName(playlist.title, c))
    foldername = foldername.replace("%playlist_id%", fixName(playlist.playlistID, c))
    foldername = foldername.replace("%owner%", fixName(playlist.owner['name'], c))
    foldername = foldername.replace("%owner_id%", str(playlist.owner['id']))
    foldername = foldername.replace("%year%", str(playlist.date.year))
    foldername = foldername.replace("%date%", str(playlist.dateString))
    foldername = foldername.replace("%explicit%", "(Explicit)" if playlist.explicit else "")
    foldername = foldername.replace('\\', pathSep).replace('/', pathSep)
    return antiDot(fixLongName(foldername))

def generateDownloadObjectName(foldername, queueItem, settings):
    c = settings['illegalCharacterReplacer']
    foldername = foldername.replace("%title%", fixName(queueItem.title, c))
    foldername = foldername.replace("%artist%", fixName(queueItem.artist, c))
    foldername = foldername.replace("%size%", str(queueItem.size))
    foldername = foldername.replace("%type%", fixName(queueItem.type, c))
    foldername = foldername.replace("%id%", fixName(queueItem.id, c))
    foldername = foldername.replace("%bitrate%", bitrateLabels[int(queueItem.bitrate)])
    foldername = foldername.replace('\\', pathSep).replace('/', pathSep).replace(pathSep, c)
    return antiDot(fixLongName(foldername))
