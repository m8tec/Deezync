from ssl import SSLError
from time import sleep
import logging

from requests import get
from requests.exceptions import ConnectionError as RequestsConnectionError, ReadTimeout, ChunkedEncodingError
from urllib3.exceptions import SSLError as u3SSLError

from deemix.utils.crypto import _md5, _ecbCrypt, _ecbDecrypt, generateBlowfishKey, decryptChunk

from deemix.utils import USER_AGENT_HEADER
from deemix.types.DownloadObjects import Single
from deemix.errors import DownloadCanceled, DownloadEmpty

logger = logging.getLogger('deemix')

def generateStreamPath(sng_id, md5, media_version, media_format):
    urlPart = b'\xa4'.join(
        [md5.encode(), str(media_format).encode(), str(sng_id).encode(), str(media_version).encode()])
    md5val = _md5(urlPart)
    step2 = md5val.encode() + b'\xa4' + urlPart + b'\xa4'
    step2 = step2 + (b'.' * (16 - (len(step2) % 16)))
    urlPart = _ecbCrypt('jo6aey6haid2Teih', step2)
    return urlPart.decode("utf-8")

def reverseStreamPath(urlPart):
    step2 = _ecbDecrypt('jo6aey6haid2Teih', urlPart)
    (_, md5, media_format, sng_id, media_version, _) = step2.split(b'\xa4')
    return (sng_id.decode('utf-8'), md5.decode('utf-8'), media_version.decode('utf-8'), media_format.decode('utf-8'))

def generateCryptedStreamURL(sng_id, md5, media_version, media_format):
    urlPart = generateStreamPath(sng_id, md5, media_version, media_format)
    return "https://e-cdns-proxy-" + md5[0] + ".dzcdn.net/mobile/1/" + urlPart

def generateStreamURL(sng_id, md5, media_version, media_format):
    urlPart = generateStreamPath(sng_id, md5, media_version, media_format)
    return "https://e-cdns-proxy-" + md5[0] + ".dzcdn.net/api/1/" + urlPart

def reverseStreamURL(url):
    urlPart = url[url.find("/1/")+3:]
    return reverseStreamPath(urlPart)

def streamTrack(outputStream, track, start=0, downloadObject=None, listener=None):
    if downloadObject and downloadObject.isCanceled: raise DownloadCanceled
    headers= {'User-Agent': USER_AGENT_HEADER}
    chunkLength = start
    isCryptedStream = "/mobile/" in track.downloadURL or "/media/" in track.downloadURL

    itemData = {
        'id': track.id,
        'title': track.title,
        'artist': track.mainArtist.name
    }

    try:
        with get(track.downloadURL, headers=headers, stream=True, timeout=10) as request:
            request.raise_for_status()
            if isCryptedStream:
                blowfish_key = generateBlowfishKey(str(track.id))

            complete = int(request.headers["Content-Length"])
            if complete == 0: raise DownloadEmpty
            if start != 0:
                responseRange = request.headers["Content-Range"]
                if listener:
                    listener.send('downloadInfo', {
                        'uuid': downloadObject.uuid,
                        'data': itemData,
                        'state': "downloading",
                        'alreadyStarted': True,
                        'value': responseRange
                    })
            else:
                if listener:
                    listener.send('downloadInfo', {
                        'uuid': downloadObject.uuid,
                        'data': itemData,
                        'state': "downloading",
                        'alreadyStarted': False,
                        'value': complete
                    })

            isStart = True
            for chunk in request.iter_content(2048 * 3):
                if isCryptedStream:
                    if len(chunk) >= 2048:
                        chunk = decryptChunk(blowfish_key, chunk[0:2048]) + chunk[2048:]

                if isStart and chunk[0] == 0 and chunk[4:8].decode('utf-8') != "ftyp":
                    for i, byte in enumerate(chunk):
                        if byte != 0: break
                    chunk = chunk[i:]
                isStart = False

                outputStream.write(chunk)
                chunkLength += len(chunk)

                if downloadObject:
                    if isinstance(downloadObject, Single):
                        chunkProgres = (chunkLength / (complete + start)) * 100
                        downloadObject.progressNext = chunkProgres
                    else:
                        chunkProgres = (len(chunk) / (complete + start)) / downloadObject.size * 100
                        downloadObject.progressNext += chunkProgres
                    downloadObject.updateProgress(listener)

    except (SSLError, u3SSLError):
        streamTrack(outputStream, track, chunkLength, downloadObject, listener)
    except (RequestsConnectionError, ReadTimeout, ChunkedEncodingError):
        sleep(2)
        streamTrack(outputStream, track, start, downloadObject, listener)
