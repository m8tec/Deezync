class DeemixError(Exception):
    """Base exception for this module"""

class GenerationError(DeemixError):
    """Generation related errors"""
    def __init__(self, link, message, errid=None):
        super().__init__()
        self.link = link
        self.message = message
        self.errid = errid

    def toDict(self):
        return {
            'link': self.link,
            'error': self.message,
            'errid': self.errid
        }

class ISRCnotOnDeezer(GenerationError):
    def __init__(self, link):
        super().__init__(link, "Track ISRC is not available on deezer", "ISRCnotOnDeezer")

class NotYourPrivatePlaylist(GenerationError):
    def __init__(self, link):
        super().__init__(link, "You can't download others private playlists.", "notYourPrivatePlaylist")

class TrackNotOnDeezer(GenerationError):
    def __init__(self, link):
        super().__init__(link, "Track not found on deezer!", "trackNotOnDeezer")

class AlbumNotOnDeezer(GenerationError):
    def __init__(self, link):
        super().__init__(link, "Album not found on deezer!", "albumNotOnDeezer")

class InvalidID(GenerationError):
    def __init__(self, link):
        super().__init__(link, "Link ID is invalid!", "invalidID")

class LinkNotSupported(GenerationError):
    def __init__(self, link):
        super().__init__(link, "Link is not supported.", "unsupportedURL")

class LinkNotRecognized(GenerationError):
    def __init__(self, link):
        super().__init__(link, "Link is not recognized.", "invalidURL")

class DownloadError(DeemixError):
    """Download related errors"""

ErrorMessages = {
    'notOnDeezer': "Track not available on Deezer!",
    'notEncoded': "Track not yet encoded!",
    'notEncodedNoAlternative': "Track not yet encoded and no alternative found!",
    'wrongBitrate': "Track not found at desired bitrate.",
    'wrongBitrateNoAlternative': "Track not found at desired bitrate and no alternative found!",
    'wrongLicense': "Your account can't stream the track at the desired bitrate.",
    'no360RA': "Track is not available in Reality Audio 360.",
    'notAvailable': "Track not available on deezer's servers!",
    'notAvailableNoAlternative': "Track not available on deezer's servers and no alternative found!",
    'noSpaceLeft': "No space left on target drive, clean up some space for the tracks",
    'albumDoesntExists': "Track's album does not exsist, failed to gather info.",
    'notLoggedIn': "You need to login to download tracks.",
    'wrongGeolocation': "Your account can't stream the track from your current country.",
    'wrongGeolocationNoAlternative': "Your account can't stream the track from your current country and no alternative found."
}

class DownloadFailed(DownloadError):
    def __init__(self, errid, track=None):
        super().__init__()
        self.errid = errid
        self.message = ErrorMessages[self.errid]
        self.track = track

class PreferredBitrateNotFound(DownloadError):
    pass

class TrackNot360(DownloadError):
    pass

class DownloadCanceled(DownloadError):
    pass

class DownloadEmpty(DownloadError):
    pass

class TrackError(DeemixError):
    """Track generation related errors"""

class AlbumDoesntExists(TrackError):
    pass

class MD5NotFound(TrackError):
    pass

class NoDataToParse(TrackError):
    pass
