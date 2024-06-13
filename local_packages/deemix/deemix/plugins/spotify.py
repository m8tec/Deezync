from concurrent.futures import ThreadPoolExecutor
import json
from copy import deepcopy
from pathlib import Path
import re
from urllib.request import urlopen
from deezer.errors import DataException
from deemix.plugins import Plugin
from deemix.utils.localpaths import getConfigFolder
from deemix.itemgen import generateTrackItem, generateAlbumItem
from deemix.errors import GenerationError, TrackNotOnDeezer, AlbumNotOnDeezer
from deemix.types.DownloadObjects import Convertable, Collection

import spotipy
SpotifyClientCredentials = spotipy.oauth2.SpotifyClientCredentials
CacheFileHandler = spotipy.cache_handler.CacheFileHandler

class Spotify(Plugin):
    def __init__(self, configFolder=None):
        super().__init__()
        self.credentials = {'clientId': "", 'clientSecret': ""}
        self.settings = {
            'fallbackSearch': False
        }
        self.enabled = False
        self.sp = None
        self.configFolder = Path(configFolder or getConfigFolder())
        self.configFolder /= 'spotify'

    def setup(self):
        if not self.configFolder.is_dir(): self.configFolder.mkdir()

        self.loadSettings()
        return self

    @classmethod
    def parseLink(cls, link):
        if 'link.tospotify.com' in link: link = urlopen(link).url
        # Remove extra stuff
        if '?' in link: link = link[:link.find('?')]
        if '&' in link: link = link[:link.find('&')]
        if link.endswith('/'): link = link[:-1] #  Remove last slash if present

        link_type = None
        link_id = None

        if not 'spotify' in link: return (link, link_type, link_id) # return if not a spotify link

        if re.search(r"[/:]track[/:](.+)", link):
            link_type = 'track'
            link_id = re.search(r"[/:]track[/:](.+)", link).group(1)
        elif re.search(r"[/:]album[/:](.+)", link):
            link_type = 'album'
            link_id = re.search(r"[/:]album[/:](.+)", link).group(1)
        elif re.search(r"[/:]playlist[/:](.+)", link):
            link_type = 'playlist'
            link_id = re.search(r"[/:]playlist[/:](.+)", link).group(1)

        return (link, link_type, link_id)

    def generateDownloadObject(self, dz, link, bitrate, listener):
        (link, link_type, link_id) = self.parseLink(link)

        if link_type is None or link_id is None: return None

        if link_type == "track":
            return self.generateTrackItem(dz, link_id, bitrate)
        if link_type == "album":
            return self.generateAlbumItem(dz, link_id, bitrate)
        if link_type == "playlist":
            return self.generatePlaylistItem(dz, link_id, bitrate)
        return None

    def generateTrackItem(self, dz, link_id, bitrate):
        cache = self.loadCache()

        if link_id in cache['tracks']:
            cachedTrack = cache['tracks'][link_id]
        else:
            cachedTrack = self.getTrack(link_id)
            cache['tracks'][link_id] = cachedTrack
            self.saveCache(cache)

        if 'isrc' in cachedTrack:
            try: return generateTrackItem(dz, f"isrc:{cachedTrack['isrc']}", bitrate)
            except GenerationError: pass
        if self.settings['fallbackSearch']:
            if 'id' not in cachedTrack or cachedTrack['id'] == "0":
                trackID = dz.api.get_track_id_from_metadata(
                    cachedTrack['data']['artist'],
                    cachedTrack['data']['title'],
                    cachedTrack['data']['album'],
                )
                if trackID != "0":
                    cachedTrack['id'] = trackID
                    cache['tracks'][link_id] = cachedTrack
                    self.saveCache(cache)

            if cachedTrack.get('id', "0") != "0":
                return generateTrackItem(dz, cachedTrack['id'], bitrate)

        raise TrackNotOnDeezer(f"https://open.spotify.com/track/{link_id}")

    def generateAlbumItem(self, dz, link_id, bitrate):
        cache = self.loadCache()

        if link_id in cache['albums']:
            cachedAlbum = cache['albums'][link_id]
        else:
            cachedAlbum = self.getAlbum(link_id)
            cache['albums'][link_id] = cachedAlbum
            self.saveCache(cache)

        try: return generateAlbumItem(dz, f"upc:{cachedAlbum['upc']}", bitrate)
        except GenerationError as e: raise AlbumNotOnDeezer(f"https://open.spotify.com/album/{link_id}") from e

    def generatePlaylistItem(self, dz, link_id, bitrate):
        if not self.enabled: raise Exception("Spotify plugin not enabled")
        spotifyPlaylist = self.sp.playlist(link_id)

        playlistAPI = self._convertPlaylistStructure(spotifyPlaylist)
        playlistAPI['various_artist'] = dz.api.get_artist(5080) # Useful for save as compilation

        tracklistTemp = spotifyPlaylist['tracks']['items']
        while spotifyPlaylist['tracks']['next']:
            spotifyPlaylist['tracks'] = self.sp.next(spotifyPlaylist['tracks'])
            tracklistTemp += spotifyPlaylist['tracks']['items']

        tracklist = []
        for item in tracklistTemp:
            if item['track']:
                if item['track']['explicit']:
                    playlistAPI['explicit'] = True
                tracklist.append(item['track'])
        if 'explicit' not in playlistAPI: playlistAPI['explicit'] = False

        return Convertable({
            'type': 'spotify_playlist',
            'id': link_id,
            'bitrate': bitrate,
            'title': spotifyPlaylist['name'],
            'artist': spotifyPlaylist['owner']['display_name'],
            'cover': playlistAPI['picture_thumbnail'],
            'explicit': playlistAPI['explicit'],
            'size': len(tracklist),
            'collection': {
                'tracks': [],
                'playlistAPI': playlistAPI
            },
            'plugin': 'spotify',
            'conversion_data': tracklist
        })

    def getTrack(self, track_id, spotifyTrack=None):
        if not self.enabled: raise Exception("Spotify plugin not enabled")
        cachedTrack = {
            'isrc': None,
            'data': None
        }

        if not spotifyTrack:
            spotifyTrack = self.sp.track(track_id)
        if 'isrc' in spotifyTrack.get('external_ids', {}):
            cachedTrack['isrc'] = spotifyTrack['external_ids']['isrc']
        cachedTrack['data'] = {
            'title': spotifyTrack['name'],
            'artist': spotifyTrack['artists'][0]['name'],
            'album': spotifyTrack['album']['name']
        }
        return cachedTrack

    def getAlbum(self, album_id, spotifyAlbum=None):
        if not self.enabled: raise Exception("Spotify plugin not enabled")
        cachedAlbum = {
            'upc': None,
            'data': None
        }

        if not spotifyAlbum:
            spotifyAlbum = self.sp.album(album_id)
        if 'upc' in spotifyAlbum.get('external_ids', {}):
            cachedAlbum['upc'] = spotifyAlbum['external_ids']['upc']
        cachedAlbum['data'] = {
            'title': spotifyAlbum['name'],
            'artist': spotifyAlbum['artists'][0]['name']
        }
        return cachedAlbum

    def convertTrack(self, dz, downloadObject, track, pos, conversion, cache, listener):
        if downloadObject.isCanceled: return
        trackAPI = None
        cachedTrack = None

        if track['id'] in cache['tracks']:
            cachedTrack = cache['tracks'][track['id']]
        else:
            cachedTrack = self.getTrack(track['id'], track)
            cache['tracks'][track['id']] = cachedTrack
            self.saveCache(cache)

        if 'isrc' in cachedTrack:
            try:
                trackAPI = dz.api.get_track_by_ISRC(cachedTrack['isrc'])
                if 'id' not in trackAPI or 'title' not in trackAPI: trackAPI = None
            except DataException: pass
        if self.settings['fallbackSearch'] and not trackAPI:
            if 'id' not in cachedTrack or cachedTrack['id'] == "0":
                trackID = dz.api.get_track_id_from_metadata(
                    cachedTrack['data']['artist'],
                    cachedTrack['data']['title'],
                    cachedTrack['data']['album'],
                )
                if trackID != "0":
                    cachedTrack['id'] = trackID
                    cache['tracks'][track['id']] = cachedTrack
                    self.saveCache(cache)

            if cachedTrack.get('id', "0") != "0":
                trackAPI = dz.api.get_track(cachedTrack['id'])

        if not trackAPI:
            trackAPI = {
                'id': "0",
                'title': track['name'],
                'duration': 0,
                'md5_origin': 0,
                'media_version': 0,
                'filesizes': {},
                'album': {
                    'title': track['album']['name'],
                    'md5_image': ""
                },
                'artist': {
                    'id': 0,
                    'name': track['artists'][0]['name']
                }
            }
        trackAPI['position'] = pos+1

        conversion['next'] += (1 / downloadObject.size) * 100
        if round(conversion['next']) != conversion['now'] and round(conversion['next']) % 2 == 0:
            conversion['now'] = round(conversion['next'])
            if listener: listener.send("updateQueue", {'uuid': downloadObject.uuid, 'conversion': conversion['now']})

        return trackAPI

    def convert(self, dz, downloadObject, settings, listener=None):
        cache = self.loadCache()

        conversion = { 'now': 0, 'next': 0 }

        collection = [None] * len(downloadObject.conversion_data)
        if listener: listener.send("startConversion", downloadObject.uuid)
        with ThreadPoolExecutor(settings['queueConcurrency']) as executor:
            for pos, track in enumerate(downloadObject.conversion_data, start=0):
                collection[pos] = executor.submit(self.convertTrack,
                    dz, downloadObject,
                    track, pos,
                    conversion,
                    cache, listener
                ).result()

        downloadObject.collection['tracks'] = collection
        downloadObject.size = len(collection)
        downloadObject = Collection(downloadObject.toDict())
        if listener: listener.send("finishConversion", downloadObject.getSlimmedDict())

        self.saveCache(cache)
        return downloadObject

    @classmethod
    def _convertPlaylistStructure(cls, spotifyPlaylist):
        cover = None
        if len(spotifyPlaylist['images']): cover = spotifyPlaylist['images'][0]['url']

        deezerPlaylist = {
            'checksum': spotifyPlaylist['snapshot_id'],
            'collaborative': spotifyPlaylist['collaborative'],
            'creation_date': "XXXX-00-00",
            'creator': {
                'id': spotifyPlaylist['owner']['id'],
                'name': spotifyPlaylist['owner']['display_name'],
                'tracklist': spotifyPlaylist['owner']['href'],
                'type': "user"
            },
            'description': spotifyPlaylist['description'],
            'duration': 0,
            'fans': spotifyPlaylist['followers']['total'] if 'followers' in spotifyPlaylist else 0,
            'id': spotifyPlaylist['id'],
            'is_loved_track': False,
            'link': spotifyPlaylist['external_urls']['spotify'],
            'nb_tracks': spotifyPlaylist['tracks']['total'],
            'picture': cover,
            'picture_small': cover or "https://e-cdns-images.dzcdn.net/images/cover/d41d8cd98f00b204e9800998ecf8427e/56x56-000000-80-0-0.jpg",
            'picture_medium': cover or "https://e-cdns-images.dzcdn.net/images/cover/d41d8cd98f00b204e9800998ecf8427e/250x250-000000-80-0-0.jpg",
            'picture_big': cover or "https://e-cdns-images.dzcdn.net/images/cover/d41d8cd98f00b204e9800998ecf8427e/500x500-000000-80-0-0.jpg",
            'picture_xl': cover or "https://e-cdns-images.dzcdn.net/images/cover/d41d8cd98f00b204e9800998ecf8427e/1000x1000-000000-80-0-0.jpg",
            'picture_thumbnail': cover or "https://e-cdns-images.dzcdn.net/images/cover/d41d8cd98f00b204e9800998ecf8427e/75x75-000000-80-0-0.jpg",
            'public': spotifyPlaylist['public'],
            'share': spotifyPlaylist['external_urls']['spotify'],
            'title': spotifyPlaylist['name'],
            'tracklist': spotifyPlaylist['tracks']['href'],
            'type': "playlist"
        }
        return deezerPlaylist

    def loadSettings(self):
        if not (self.configFolder / 'config.json').is_file():
            with open(self.configFolder / 'config.json', 'w', encoding="utf-8") as f:
                json.dump({**self.credentials, **self.settings}, f, indent=2)

        with open(self.configFolder / 'config.json', 'r', encoding="utf-8") as settingsFile:
            try:
                settings = json.load(settingsFile)
            except json.decoder.JSONDecodeError:
                with open(self.configFolder / 'config.json', 'w', encoding="utf-8") as f:
                    json.dump({**self.credentials, **self.settings}, f, indent=2)
                settings = deepcopy({**self.credentials, **self.settings})
            except Exception:
                settings = deepcopy({**self.credentials, **self.settings})

        self.setSettings(settings)
        self.checkCredentials()

    def saveSettings(self, newSettings=None):
        if newSettings: self.setSettings(newSettings)
        self.checkCredentials()
        with open(self.configFolder / 'config.json', 'w', encoding="utf-8") as f:
            json.dump({**self.credentials, **self.settings}, f, indent=2)

    def getSettings(self):
        return {**self.credentials, **self.settings}

    def setSettings(self, newSettings):
        self.credentials = { 'clientId': newSettings['clientId'], 'clientSecret': newSettings['clientSecret'] }
        settings = {**newSettings}
        del settings['clientId']
        del settings['clientSecret']
        self.settings = settings

    def loadCache(self):
        cache = None
        if (self.configFolder / 'cache.json').is_file():
            with open(self.configFolder / 'cache.json', 'r', encoding="utf-8") as f:
                try:
                    cache = json.load(f)
                except json.decoder.JSONDecodeError:
                    self.saveCache({'tracks': {}, 'albums': {}})
                    cache = None
                except Exception:
                    cache = None
        if not cache: cache = {'tracks': {}, 'albums': {}}
        return cache

    def saveCache(self, newCache):
        with open(self.configFolder / 'cache.json', 'w', encoding="utf-8") as spotifyCache:
            json.dump(newCache, spotifyCache)

    def checkCredentials(self):
        if self.credentials['clientId'] == "" or self.credentials['clientSecret'] == "":
            self.enabled = False
            return

        try:
            cache_handler = CacheFileHandler(self.configFolder / ".auth-cache")
            client_credentials_manager = SpotifyClientCredentials(client_id=self.credentials['clientId'],
                                                                  client_secret=self.credentials['clientSecret'],
                                                                  cache_handler=cache_handler)
            self.sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
            self.sp.user_playlists('spotify')
            self.enabled = True
        except Exception:
            self.enabled = False

    def getCredentials(self):
        return self.credentials

    def setCredentials(self, clientId, clientSecret):
        # Remove extra spaces, just to be sure
        clientId = clientId.strip()
        clientSecret = clientSecret.strip()

        # Save them to disk
        self.credentials = { 'clientId': clientId, 'clientSecret': clientSecret}
        self.saveSettings()
