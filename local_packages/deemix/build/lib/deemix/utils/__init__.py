import string
import re
from deezer import TrackFormats
import os
from deemix.errors import ErrorMessages

USER_AGENT_HEADER = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) " \
                    "Chrome/79.0.3945.130 Safari/537.36"

def canWrite(folder):
    return os.access(folder, os.W_OK)

def generateReplayGainString(trackGain):
    return "{0:.2f} dB".format((float(trackGain) + 18.4) * -1)

def getBitrateNumberFromText(txt):
    txt = str(txt).lower()
    if txt in ['flac', 'lossless', '9']:
        return TrackFormats.FLAC
    if txt in ['mp3', '320', '3']:
        return TrackFormats.MP3_320
    if txt in ['128', '1']:
        return TrackFormats.MP3_128
    if txt in ['360', '360_hq', '15']:
        return TrackFormats.MP4_RA3
    if txt in ['360_mq', '14']:
        return TrackFormats.MP4_RA2
    if txt in ['360_lq', '13']:
        return TrackFormats.MP4_RA1
    return None

def changeCase(txt, case_type):
    if case_type == "lower":
        return txt.lower()
    if case_type == "upper":
        return txt.upper()
    if case_type == "start":
        txt = txt.strip().split(" ")
        for i, word in enumerate(txt):
            if word[0] in ['(', '{', '[', "'", '"']:
                txt[i] = word[0] + word[1:].capitalize()
            else:
                txt[i] = word.capitalize()
        return " ".join(txt)
    if case_type == "sentence":
        return txt.capitalize()
    return str

def removeFeatures(title):
    clean = title
    found = False
    pos = -1
    if re.search(r"[\s(]\(?\s?feat\.?\s", clean):
        pos = re.search(r"[\s(]\(?\s?feat\.?\s", clean).start(0)
        found = True
    if re.search(r"[\s(]\(?\s?ft\.?\s", clean):
        pos = re.search(r"[\s(]\(?\s?ft\.?\s", clean).start(0)
        found = True
    openBracket = clean[pos] == '(' or clean[pos+1] == '('
    otherBracket = clean.find('(', pos+2)
    if found:
        tempTrack = clean[:pos]
        if ")" in clean and openBracket:
            tempTrack += clean[clean.find(")", pos+2) + 1:]
        if not openBracket and otherBracket != -1:
            tempTrack += f" {clean[otherBracket:]}"
        clean = tempTrack.strip()
        clean = ' '.join(clean.split())
    return clean

def andCommaConcat(lst):
    tot = len(lst)
    result = ""
    for i, art in enumerate(lst):
        result += art
        if tot != i + 1:
            if tot - 1 == i + 1:
                result += " & "
            else:
                result += ", "
    return result

def uniqueArray(arr):
    for iPrinc, namePrinc  in enumerate(arr):
        for iRest, nRest in enumerate(arr):
            if iPrinc!=iRest and namePrinc.lower() in nRest.lower():
                del arr[iRest]
    return arr

def removeDuplicateArtists(artist, artists):
    artists = uniqueArray(artists)
    for role in artist.keys():
        artist[role] = uniqueArray(artist[role])
    return (artist, artists)

def formatListener(key, data=None):
    if key == "startAddingArtist":
        return f"Started gathering {data['name']}'s albums ({data['id']})"
    if key == "finishAddingArtist":
        return f"Finished gathering {data['name']}'s albums ({data['id']})"
    if key == "updateQueue":
        uuid = f"[{data['uuid']}]"
        if data.get('downloaded'):
            shortFilepath = data['downloadPath'][len(data['extrasPath']):]
            return f"{uuid} Completed download of {shortFilepath}"
        if data.get('failed'):
            return f"{uuid} {data['data']['artist']} - {data['data']['title']} :: {data['error']}"
        if data.get('progress'):
            return f"{uuid} Download at {data['progress']}%"
        if data.get('conversion'):
            return f"{uuid} Conversion at {data['conversion']}%"
        return uuid
    if key == "downloadInfo":
        message = data['state']
        if data['state'] == "getTags": message = "Getting tags."
        elif data['state'] == "gotTags": message = "Tags got."
        elif data['state'] == "getBitrate": message = "Getting download URL."
        elif data['state'] == "bitrateFallback": message = "Desired bitrate not found, falling back to lower bitrate."
        elif data['state'] == "searchFallback": message = "This track has been searched for, result might not be 100% exact."
        elif data['state'] == "gotBitrate": message = "Download URL got."
        elif data['state'] == "getAlbumArt": message = "Downloading album art."
        elif data['state'] == "gotAlbumArt": message = "Album art downloaded."
        elif data['state'] == "downloading":
            message = "Downloading track."
            if data['alreadyStarted']:
                message += f" Recovering download from {data['value']}."
            else:
                message += f" Downloading {data['value']} bytes."
        elif data['state'] == "downloaded": message = "Track downloaded."
        elif data['state'] == "alreadyDownloaded": message = "Track already downloaded."
        elif data['state'] == "tagging": message = "Tagging track."
        elif data['state'] == "tagged": message = "Track tagged."
        return f"[{data['uuid']}] {data['data']['artist']} - {data['data']['title']} :: {message}"
    if key == "downloadWarn":
        errorMessage = ErrorMessages[data['state']]
        solutionMessage = ""
        if data['solution'] == 'fallback': solutionMessage = "Using fallback id."
        if data['solution'] == 'search': solutionMessage = "Searching for alternative."
        return f"[{data['uuid']}] {data['data']['artist']} - {data['data']['title']} :: {errorMessage} {solutionMessage}"
    if key == "currentItemCancelled":
        return f"Current item cancelled ({data})"
    if key == "removedFromQueue":
        return f"[{data}] Removed from the queue"
    if key == "finishDownload":
        return f"[{data}] Finished downloading"
    if key == "startConversion":
        return f"[{data}] Started converting"
    if key == "finishConversion":
        return f"[{data['uuid']}] Finished converting"
    return ""
