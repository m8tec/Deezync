from pathlib import Path

class IDownloadObject:
    """DownloadObject Interface"""
    def __init__(self, obj):
        self.type = obj['type']
        self.id = obj['id']
        self.bitrate = obj['bitrate']
        self.title = obj['title']
        self.artist = obj['artist']
        self.cover = obj['cover']
        self.explicit = obj.get('explicit', False)
        self.size = obj.get('size', 0)
        self.downloaded = obj.get('downloaded', 0)
        self.failed = obj.get('failed', 0)
        self.progress = obj.get('progress', 0)
        self.errors = obj.get('errors', [])
        self.files = obj.get('files', [])
        self.extrasPath = obj.get('extrasPath', "")
        if self.extrasPath: self.extrasPath = Path(self.extrasPath)
        self.progressNext = 0
        self.uuid = f"{self.type}_{self.id}_{self.bitrate}"
        self.isCanceled = False
        self.__type__ = None

    def toDict(self):
        return {
            'type': self.type,
            'id': self.id,
            'bitrate': self.bitrate,
            'uuid': self.uuid,
            'title': self.title,
            'artist': self.artist,
            'cover': self.cover,
            'explicit': self.explicit,
            'size': self.size,
            'downloaded': self.downloaded,
            'failed': self.failed,
            'progress': self.progress,
            'errors': self.errors,
            'files': self.files,
            'extrasPath': str(self.extrasPath),
            '__type__': self.__type__
        }

    def getResettedDict(self):
        item = self.toDict()
        item['downloaded'] = 0
        item['failed'] = 0
        item['progress'] = 0
        item['errors'] = []
        item['files'] = []
        return item

    def getSlimmedDict(self):
        light = self.toDict()
        propertiesToDelete = ['single', 'collection', 'plugin', 'conversion_data']
        for prop in propertiesToDelete:
            if prop in light:
                del light[prop]
        return light

    def getEssentialDict(self):
        return {
            'type': self.type,
            'id': self.id,
            'bitrate': self.bitrate,
            'uuid': self.uuid,
            'title': self.title,
            'artist': self.artist,
            'cover': self.cover,
            'explicit': self.explicit,
            'size': self.size,
            'extrasPath': str(self.extrasPath)
        }

    def updateProgress(self, listener=None):
        if round(self.progressNext) != self.progress and round(self.progressNext) % 2 == 0:
            self.progress = round(self.progressNext)
            if listener: listener.send("updateQueue", {'uuid': self.uuid, 'progress': self.progress})

class Single(IDownloadObject):
    def __init__(self, obj):
        super().__init__(obj)
        self.size = 1
        self.single = obj['single']
        self.__type__ = "Single"

    def toDict(self):
        item = super().toDict()
        item['single'] = self.single
        return item

    def completeTrackProgress(self, listener=None):
        self.progressNext = 100
        self.updateProgress(listener)

    def removeTrackProgress(self, listener=None):
        self.progressNext = 0
        self.updateProgress(listener)

class Collection(IDownloadObject):
    def __init__(self, obj):
        super().__init__(obj)
        self.collection = obj['collection']
        self.__type__ = "Collection"

    def toDict(self):
        item = super().toDict()
        item['collection'] = self.collection
        return item

    def completeTrackProgress(self, listener=None):
        self.progressNext += (1 / self.size) * 100
        self.updateProgress(listener)

    def removeTrackProgress(self, listener=None):
        self.progressNext -= (1 / self.size) * 100
        self.updateProgress(listener)

class Convertable(Collection):
    def __init__(self, obj):
        super().__init__(obj)
        self.plugin = obj['plugin']
        self.conversion_data = obj['conversion_data']
        self.__type__ = "Convertable"

    def toDict(self):
        item = super().toDict()
        item['plugin'] = self.plugin
        item['conversion_data'] = self.conversion_data
        return item
