from deemix.types.Picture import Picture
from deemix.types import VARIOUS_ARTISTS

class Artist:
    def __init__(self, art_id="0", name="", role="", pic_md5=""):
        self.id = str(art_id)
        self.name = name
        self.pic = Picture(md5=pic_md5, pic_type="artist")
        self.role = role
        self.save = True

    def isVariousArtists(self):
        return self.id == VARIOUS_ARTISTS
