from deemix.types.Artist import Artist
from deemix.types.Date import Date
from deemix.types.Picture import Picture, StaticPicture

class Playlist:
    def __init__(self, playlistAPI):
        self.id = "pl_" + str(playlistAPI['id'])
        self.title = playlistAPI['title']
        self.rootArtist = None
        self.artist = {"Main": []}
        self.artists = []
        self.trackTotal = playlistAPI['nb_tracks']
        self.recordType = "compile"
        self.barcode = ""
        self.label = ""
        self.explicit = playlistAPI['explicit']
        self.genre = ["Compilation", ]

        year = playlistAPI["creation_date"][0:4]
        month = playlistAPI["creation_date"][5:7]
        day = playlistAPI["creation_date"][8:10]
        self.date = Date(day, month, year)

        self.discTotal = "1"
        self.playlistID = playlistAPI['id']
        self.owner = playlistAPI['creator']

        if 'dzcdn.net' in playlistAPI['picture_small']:
            url = playlistAPI['picture_small']
            picType = url[url.find('images/')+7:]
            picType = picType[:picType.find('/')]
            md5 = url[url.find(picType+'/') + len(picType)+1:-24]
            self.pic = Picture(md5, picType)
        else:
            self.pic = StaticPicture(playlistAPI['picture_xl'])

        if 'various_artist' in playlistAPI:
            pic_md5 = playlistAPI['various_artist']['picture_small']
            pic_md5 = pic_md5[pic_md5.find('artist/') + 7:-24]
            self.variousArtists = Artist(
                playlistAPI['various_artist']['id'],
                playlistAPI['various_artist']['name'],
                "Main",
                pic_md5
            )
            self.mainArtist = self.variousArtists
