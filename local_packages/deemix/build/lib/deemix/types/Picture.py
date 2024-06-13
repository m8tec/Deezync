class Picture:
    def __init__(self, md5="", pic_type=""):
        self.md5 = md5
        self.type = pic_type

    def getURL(self, size, pic_format):
        url = "https://e-cdns-images.dzcdn.net/images/{}/{}/{size}x{size}".format(
            self.type,
            self.md5,
            size=size
        )

        if pic_format.startswith("jpg"):
            quality = 80
            if '-' in pic_format:
                quality = pic_format[4:]
            pic_format = 'jpg'
            return url + f'-000000-{quality}-0-0.jpg'
        if pic_format == 'png':
            return url + '-none-100-0-0.png'

        return url+'.jpg'

class StaticPicture:
    def __init__(self, url):
        self.staticURL = url

    def getURL(self, _, __):
        return self.staticURL
