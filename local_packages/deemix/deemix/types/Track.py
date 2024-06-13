import re
from datetime import datetime

from deezer.utils import map_track, map_album
from deezer.errors import APIError, GWAPIError
from deemix.errors import NoDataToParse, AlbumDoesntExists

from deemix.utils import removeFeatures, andCommaConcat, removeDuplicateArtists, generateReplayGainString, changeCase

from deemix.types.Album import Album
from deemix.types.Artist import Artist
from deemix.types.Date import Date
from deemix.types.Picture import Picture
from deemix.types.Playlist import Playlist
from deemix.types.Lyrics import Lyrics
from deemix.types import VARIOUS_ARTISTS

from deemix.settings import FeaturesOption

class Track:
    def __init__(self, sng_id="0", name=""):
        self.id = sng_id
        self.title = name
        self.MD5 = ""
        self.mediaVersion = ""
        self.trackToken = ""
        self.trackTokenExpiration = 0
        self.duration = 0
        self.fallbackID = "0"
        self.albumsFallback = []
        self.filesizes = {}
        self.local = False
        self.mainArtist = None
        self.artist = {"Main": []}
        self.artists = []
        self.album = None
        self.trackNumber = "0"
        self.discNumber = "0"
        self.date = Date()
        self.lyrics = None
        self.bpm = 0
        self.contributors = {}
        self.copyright = ""
        self.explicit = False
        self.ISRC = ""
        self.replayGain = ""
        self.rank = 0
        self.playlist = None
        self.position = None
        self.searched = False
        self.selectedFormat = 0
        self.singleDownload = False
        self.dateString = ""
        self.artistsString = ""
        self.mainArtistsString = ""
        self.featArtistsString = ""
        self.urls = {}

    def parseEssentialData(self, trackAPI):
        self.id = str(trackAPI['id'])
        self.duration = trackAPI['duration']
        self.trackToken = trackAPI['track_token']
        self.trackTokenExpiration = trackAPI['track_token_expire']
        self.MD5 = trackAPI.get('md5_origin')
        self.mediaVersion = trackAPI['media_version']
        self.filesizes = trackAPI['filesizes']
        self.fallbackID = "0"
        if 'fallback_id' in trackAPI:
            self.fallbackID = trackAPI['fallback_id']
        self.local = int(self.id) < 0
        self.urls = {}

    def parseData(self, dz, track_id=None, trackAPI=None, albumAPI=None, playlistAPI=None):
        if track_id and (not trackAPI or trackAPI and not trackAPI.get('track_token')):
            trackAPI_new = dz.gw.get_track_with_fallback(track_id)
            trackAPI_new = map_track(trackAPI_new)
            if not trackAPI: trackAPI = {}
            trackAPI_new.update(trackAPI)
            trackAPI = trackAPI_new
        elif not trackAPI: raise NoDataToParse

        self.parseEssentialData(trackAPI)

        # only public api has bpm
        if not trackAPI.get('bpm') and not self.local:
            try:
                trackAPI_new = dz.api.get_track(trackAPI['id'])
                trackAPI_new['release_date'] = trackAPI['release_date']
                trackAPI.update(trackAPI_new)
            except APIError: pass

        if self.local:
            self.parseLocalTrackData(trackAPI)
        else:
            self.parseTrack(trackAPI)

            # Get Lyrics data
            if not trackAPI.get("lyrics") and self.lyrics.id != "0":
                try: trackAPI["lyrics"] = dz.gw.get_track_lyrics(self.id)
                except GWAPIError: self.lyrics.id = "0"
            if self.lyrics.id != "0": self.lyrics.parseLyrics(trackAPI["lyrics"])

            # Parse Album Data
            self.album = Album(
                alb_id = trackAPI['album']['id'],
                title = trackAPI['album']['title'],
                pic_md5 = trackAPI['album'].get('md5_origin')
            )

            # Get album Data
            if not albumAPI:
                try: albumAPI = dz.api.get_album(self.album.id)
                except APIError: albumAPI = None

            # Get album_gw Data
            # Only gw has disk number
            if not albumAPI or albumAPI and not albumAPI.get('nb_disk'):
                try:
                    albumAPI_gw = dz.gw.get_album(self.album.id)
                    albumAPI_gw = map_album(albumAPI_gw)
                except GWAPIError: albumAPI_gw = {}
                if not albumAPI: albumAPI = {}
                albumAPI_gw.update(albumAPI)
                albumAPI = albumAPI_gw

            if not albumAPI: raise AlbumDoesntExists

            self.album.parseAlbum(albumAPI)
            # albumAPI_gw doesn't contain the artist cover
            # Getting artist image ID
            # ex: https://e-cdns-images.dzcdn.net/images/artist/f2bc007e9133c946ac3c3907ddc5d2ea/56x56-000000-80-0-0.jpg
            if not self.album.mainArtist.pic.md5 or self.album.mainArtist.pic.md5 == "":
                artistAPI = dz.api.get_artist(self.album.mainArtist.id)
                self.album.mainArtist.pic.md5 = artistAPI['picture_small'][artistAPI['picture_small'].find('artist/') + 7:-24]

            # Fill missing data
            if self.album.date and not self.date: self.date = self.album.date
            if 'genres' in trackAPI:
                for genre in trackAPI['genres']:
                    if genre not in self.album.genre: self.album.genre.append(genre)

        # Remove unwanted charaters in track name
        # Example: track/127793
        self.title = ' '.join(self.title.split())

        # Make sure there is at least one artist
        if len(self.artist['Main']) == 0:
            self.artist['Main'] = [self.mainArtist.name]

        self.position = trackAPI.get('position')

        # Add playlist data if track is in a playlist
        if playlistAPI: self.playlist = Playlist(playlistAPI)

        self.generateMainFeatStrings()
        return self

    def parseLocalTrackData(self, trackAPI):
        # Local tracks has only the trackAPI_gw page and
        # contains only the tags provided by the file
        self.title = trackAPI['title']
        self.album = Album(title=trackAPI['album']['title'])
        self.album.pic = Picture(
            md5 = trackAPI.get('md5_image', ""),
            pic_type = "cover"
        )
        self.mainArtist = Artist(name=trackAPI['artist']['name'], role="Main")
        self.artists = [trackAPI['artist']['name']]
        self.artist = {
            'Main': [trackAPI['artist']['name']]
        }
        self.album.artist = self.artist
        self.album.artists = self.artists
        self.album.date = self.date
        self.album.mainArtist = self.mainArtist

    def parseTrack(self, trackAPI):
        self.title = trackAPI['title']

        self.discNumber = trackAPI.get('disk_number')
        self.explicit = trackAPI.get('explicit_lyrics', False)
        self.copyright = trackAPI.get('copyright')
        if 'gain' in trackAPI: self.replayGain = generateReplayGainString(trackAPI['gain'])
        self.ISRC = trackAPI.get('isrc')
        self.trackNumber = trackAPI['track_position']
        self.contributors = trackAPI.get('song_contributors')
        self.rank = trackAPI['rank']
        self.bpm = trackAPI['bpm']

        self.lyrics = Lyrics(trackAPI.get('lyrics_id', "0"))

        self.mainArtist = Artist(
            art_id = trackAPI['artist']['id'],
            name = trackAPI['artist']['name'],
            role = "Main",
            pic_md5 = trackAPI['artist'].get('md5_image')
        )

        if trackAPI.get('physical_release_date'):
            self.date.day = trackAPI["physical_release_date"][8:10]
            self.date.month = trackAPI["physical_release_date"][5:7]
            self.date.year = trackAPI["physical_release_date"][0:4]
            self.date.fixDayMonth()

        for artist in trackAPI.get('contributors', []):
            isVariousArtists = str(artist['id']) == VARIOUS_ARTISTS
            isMainArtist = artist['role'] == "Main"

            if len(trackAPI['contributors']) > 1 and isVariousArtists:
                continue

            if artist['name'] not in self.artists:
                self.artists.append(artist['name'])

            if isMainArtist or artist['name'] not in self.artist['Main'] and not isMainArtist:
                if not artist['role'] in self.artist:
                    self.artist[artist['role']] = []
                self.artist[artist['role']].append(artist['name'])

        if trackAPI.get('alternative_albums'):
            for album in trackAPI['alternative_albums']['data']:
                if 'RIGHTS' in album and album['RIGHTS'].get('STREAM_ADS_AVAILABLE') or album['RIGHTS'].get('STREAM_SUB_AVAILABLE'):
                    self.albumsFallback.append(album['ALB_ID'])

    def removeDuplicateArtists(self):
        (self.artist, self.artists) = removeDuplicateArtists(self.artist, self.artists)

    # Removes featuring from the title
    def getCleanTitle(self):
        return removeFeatures(self.title)

    def getFeatTitle(self):
        if self.featArtistsString and "feat." not in self.title.lower():
            return f"{self.title} ({self.featArtistsString})"
        return self.title

    def generateMainFeatStrings(self):
        self.mainArtistsString = andCommaConcat(self.artist['Main'])
        self.featArtistsString = ""
        if 'Featured' in self.artist:
            self.featArtistsString = "feat. "+andCommaConcat(self.artist['Featured'])

    def checkAndRenewTrackToken(self, dz):
        now = datetime.now()
        expiration = datetime.fromtimestamp(self.trackTokenExpiration)
        if now > expiration:
            newTrack = dz.gw.get_track_with_fallback(self.id)
            self.trackToken = newTrack['TRACK_TOKEN']
            self.trackTokenExpiration = newTrack['TRACK_TOKEN_EXPIRE']

    def applySettings(self, settings):

        # Check if should save the playlist as a compilation
        if self.playlist and settings['tags']['savePlaylistAsCompilation']:
            self.trackNumber = self.position
            self.discNumber = "1"
            self.album.makePlaylistCompilation(self.playlist)
        else:
            if self.album.date: self.date = self.album.date

        self.dateString = self.date.format(settings['dateFormat'])
        self.album.dateString = self.album.date.format(settings['dateFormat'])
        if self.playlist: self.playlist.dateString = self.playlist.date.format(settings['dateFormat'])

        # Check various artist option
        if settings['albumVariousArtists'] and self.album.variousArtists:
            artist = self.album.variousArtists
            isMainArtist = artist.role == "Main"

            if artist.name not in self.album.artists:
                self.album.artists.insert(0, artist.name)

            if isMainArtist or artist.name not in self.album.artist['Main'] and not isMainArtist:
                if artist.role not in self.album.artist:
                    self.album.artist[artist.role] = []
                self.album.artist[artist.role].insert(0, artist.name)
        self.album.mainArtist.save = not self.album.mainArtist.isVariousArtists() or settings['albumVariousArtists'] and self.album.mainArtist.isVariousArtists()

        # Check removeDuplicateArtists
        if settings['removeDuplicateArtists']: self.removeDuplicateArtists()

        # Check if user wants the feat in the title
        if str(settings['featuredToTitle']) == FeaturesOption.REMOVE_TITLE:
            self.title = self.getCleanTitle()
        elif str(settings['featuredToTitle']) == FeaturesOption.MOVE_TITLE:
            self.title = self.getFeatTitle()
        elif str(settings['featuredToTitle']) == FeaturesOption.REMOVE_TITLE_ALBUM:
            self.title = self.getCleanTitle()
            self.album.title = self.album.getCleanTitle()

        # Remove (Album Version) from tracks that have that
        if settings['removeAlbumVersion'] and "Album Version" in self.title:
            self.title = re.sub(r' ?\(Album Version\)', "", self.title).strip()

        # Change Title and Artists casing if needed
        if settings['titleCasing'] != "nothing":
            self.title = changeCase(self.title, settings['titleCasing'])
        if settings['artistCasing'] != "nothing":
            self.mainArtist.name = changeCase(self.mainArtist.name, settings['artistCasing'])
            for i, artist in enumerate(self.artists):
                self.artists[i] = changeCase(artist, settings['artistCasing'])
            for art_type in self.artist:
                for i, artist in enumerate(self.artist[art_type]):
                    self.artist[art_type][i] = changeCase(artist, settings['artistCasing'])
            self.generateMainFeatStrings()

        # Generate artist tag
        if settings['tags']['multiArtistSeparator'] == "default":
            if str(settings['featuredToTitle']) == FeaturesOption.MOVE_TITLE:
                self.artistsString = ", ".join(self.artist['Main'])
            else:
                self.artistsString = ", ".join(self.artists)
        elif settings['tags']['multiArtistSeparator'] == "andFeat":
            self.artistsString = self.mainArtistsString
            if self.featArtistsString and str(settings['featuredToTitle']) != FeaturesOption.MOVE_TITLE:
                self.artistsString += " " + self.featArtistsString
        else:
            separator = settings['tags']['multiArtistSeparator']
            if str(settings['featuredToTitle']) == FeaturesOption.MOVE_TITLE:
                self.artistsString = separator.join(self.artist['Main'])
            else:
                self.artistsString = separator.join(self.artists)
