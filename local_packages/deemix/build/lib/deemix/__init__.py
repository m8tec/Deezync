#!/usr/bin/env python3
import re
from urllib.request import urlopen

from deemix.itemgen import generateTrackItem, \
    generateAlbumItem, \
    generatePlaylistItem, \
    generateArtistItem, \
    generateArtistDiscographyItem, \
    generateArtistTopItem
from deemix.errors import LinkNotRecognized, LinkNotSupported

__version__ = "3.6.6"

# Returns the Resolved URL, the Type and the ID
def parseLink(link):
    if 'deezer.page.link' in link: link = urlopen(link).url # Resolve URL shortner
    # Remove extra stuff
    if '?' in link: link = link[:link.find('?')]
    if '&' in link: link = link[:link.find('&')]
    if link.endswith('/'): link = link[:-1] #  Remove last slash if present

    link_type = None
    link_id = None

    if not 'deezer' in link: return (link, link_type, link_id) # return if not a deezer link

    if '/track' in link:
        link_type = 'track'
        link_id = re.search(r"/track/(.+)", link).group(1)
    elif '/playlist' in link:
        link_type = 'playlist'
        link_id = re.search(r"/playlist/(\d+)", link).group(1)
    elif '/album' in link:
        link_type = 'album'
        link_id = re.search(r"/album/(.+)", link).group(1)
    elif re.search(r"/artist/(\d+)/top_track", link):
        link_type = 'artist_top'
        link_id = re.search(r"/artist/(\d+)/top_track", link).group(1)
    elif re.search(r"/artist/(\d+)/discography", link):
        link_type = 'artist_discography'
        link_id = re.search(r"/artist/(\d+)/discography", link).group(1)
    elif '/artist' in link:
        link_type = 'artist'
        link_id = re.search(r"/artist/(\d+)", link).group(1)

    return (link, link_type, link_id)

def generateDownloadObject(dz, link, bitrate, plugins=None, listener=None):
    (link, link_type, link_id) = parseLink(link)

    if link_type is None or link_id is None:
        if plugins is None: plugins = {}
        plugin_names = plugins.keys()
        current_plugin = None
        item = None
        for plugin in plugin_names:
            current_plugin = plugins[plugin]
            item = current_plugin.generateDownloadObject(dz, link, bitrate, listener)
            if item: return item
        raise LinkNotRecognized(link)

    if link_type == "track":
        return generateTrackItem(dz, link_id, bitrate)
    if link_type == "album":
        return generateAlbumItem(dz, link_id, bitrate)
    if link_type == "playlist":
        return generatePlaylistItem(dz, link_id, bitrate)
    if link_type == "artist":
        return generateArtistItem(dz, link_id, bitrate, listener)
    if link_type == "artist_discography":
        return generateArtistDiscographyItem(dz, link_id, bitrate, listener)
    if link_type == "artist_top":
        return generateArtistTopItem(dz, link_id, bitrate)

    raise LinkNotSupported(link)
