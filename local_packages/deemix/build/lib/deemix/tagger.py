from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, ID3NoHeaderError, \
    TXXX, TIT2, TPE1, TALB, TPE2, TRCK, TPOS, TCON, TYER, TDAT, TLEN, TBPM, \
    TPUB, TSRC, USLT, SYLT, APIC, IPLS, TCOM, TCOP, TCMP, Encoding, PictureType, POPM

# Adds tags to a MP3 file
def tagID3(path, track, save):
    # Delete exsisting tags
    try:
        tag = ID3(path)
        tag.delete()
    except ID3NoHeaderError:
        tag = ID3()

    if save['title']:
        tag.add(TIT2(text=track.title))

    if save['artist'] and len(track.artists):
        if save['multiArtistSeparator'] == "default":
            tag.add(TPE1(text=track.artists))
        else:
            if save['multiArtistSeparator'] == "nothing":
                tag.add(TPE1(text=track.mainArtist.name))
            else:
                tag.add(TPE1(text=track.artistsString))
            # Tag ARTISTS is added to keep the multiartist support when using a non standard tagging method
            # https://picard-docs.musicbrainz.org/en/appendices/tag_mapping.html#artists
            if save['artists']:
                tag.add(TXXX(desc="ARTISTS", text=track.artists))

    if save['album']:
        tag.add(TALB(text=track.album.title))

    if save['albumArtist'] and len(track.album.artists):
        if save['singleAlbumArtist'] and track.album.mainArtist.save:
            tag.add(TPE2(text=track.album.mainArtist.name))
        else:
            tag.add(TPE2(text=track.album.artists))

    if save['trackNumber']:
        trackNumber = str(track.trackNumber)
        if save['trackTotal']:
            trackNumber += "/" + str(track.album.trackTotal)
        tag.add(TRCK(text=trackNumber))
    if save['discNumber']:
        discNumber = str(track.discNumber)
        if save['discTotal']:
            discNumber += "/" + str(track.album.discTotal)
        tag.add(TPOS(text=discNumber))

    if save['genre']:
        tag.add(TCON(text=track.album.genre))
    if save['year']:
        tag.add(TYER(text=str(track.date.year)))
    if save['date']:
        # Referencing ID3 standard
        # https://id3.org/id3v2.3.0#TDAT
        # The 'Date' frame is a numeric string in the DDMM format.
        tag.add(TDAT(text=str(track.date.day) + str(track.date.month)))
    if save['length']:
        tag.add(TLEN(text=str(int(track.duration)*1000)))
    if save['bpm'] and track.bpm:
        tag.add(TBPM(text=str(track.bpm)))
    if save['label']:
        tag.add(TPUB(text=track.album.label))
    if save['isrc']:
        tag.add(TSRC(text=track.ISRC))
    if save['barcode']:
        tag.add(TXXX(desc="BARCODE", text=track.album.barcode))
    if save['explicit']:
        tag.add(TXXX(desc="ITUNESADVISORY", text= "1" if track.explicit else "0" ))
    if save['replayGain']:
        tag.add(TXXX(desc="REPLAYGAIN_TRACK_GAIN", text=track.replayGain))
    if track.lyrics.unsync and save['lyrics']:
        tag.add(USLT(text=track.lyrics.unsync))
    if track.lyrics.syncID3 and save['syncedLyrics']:
        # Referencing ID3 standard
        # https://id3.org/id3v2.3.0#sec4.10
        # Type:   1  => is lyrics
        # Format: 2  => Absolute time, 32 bit sized, using milliseconds as unit
        tag.add(SYLT(Encoding.UTF8, type=1, format=2, text=track.lyrics.syncID3))

    involved_people = []
    for role in track.contributors:
        if role in ['author', 'engineer', 'mixer', 'producer', 'writer']:
            for person in track.contributors[role]:
                involved_people.append([role, person])
        elif role == 'composer' and save['composer']:
            tag.add(TCOM(text=track.contributors['composer']))
    if len(involved_people) > 0 and save['involvedPeople']:
        tag.add(IPLS(people=involved_people))

    if save['copyright'] and track.copyright:
        tag.add(TCOP(text=track.copyright))
    if save['savePlaylistAsCompilation'] and track.playlist or track.album.recordType == "compile":
        tag.add(TCMP(text="1"))

    if save['source']:
        tag.add(TXXX(desc="SOURCE", text='Deezer'))
        tag.add(TXXX(desc="SOURCEID", text=str(track.id)))

    if save['rating']:
        rank = round((int(track.rank) / 10000) * 2.55)
        if rank > 255 :
            rank = 255
        else:
            rank = round(rank, 0)

        tag.add(POPM(rating=rank))

    if save['cover'] and track.album.embeddedCoverPath:

        descEncoding = Encoding.LATIN1
        if save['coverDescriptionUTF8']:
            descEncoding = Encoding.UTF8

        mimeType = 'image/jpeg'
        if str(track.album.embeddedCoverPath).endswith('png'):
            mimeType = 'image/png'

        with open(track.album.embeddedCoverPath, 'rb') as f:
            tag.add(APIC(descEncoding, mimeType, PictureType.COVER_FRONT, desc='cover', data=f.read()))

    tag.save( path,
              v1=2 if save['saveID3v1'] else 0,
              v2_version=3,
              v23_sep=None if save['useNullSeparator'] else '/' )

# Adds tags to a FLAC file
def tagFLAC(path, track, save):
    # Delete exsisting tags
    tag = FLAC(path)
    tag.delete()
    tag.clear_pictures()

    if save['title']:
        tag["TITLE"] = track.title

    if save['artist'] and len(track.artists):
        if save['multiArtistSeparator'] == "default":
            tag["ARTIST"] = track.artists
        else:
            if save['multiArtistSeparator'] == "nothing":
                tag["ARTIST"] = track.mainArtist.name
            else:
                tag["ARTIST"] = track.artistsString
            # Tag ARTISTS is added to keep the multiartist support when using a non standard tagging method
            # https://picard-docs.musicbrainz.org/en/technical/tag_mapping.html#artists
            if save['artists']:
                tag["ARTISTS"] = track.artists

    if save['album']:
        tag["ALBUM"] = track.album.title

    if save['albumArtist'] and len(track.album.artists):
        if save['singleAlbumArtist'] and track.album.mainArtist.save:
            tag["ALBUMARTIST"] = track.album.mainArtist.name
        else:
            tag["ALBUMARTIST"] = track.album.artists

    if save['trackNumber']:
        tag["TRACKNUMBER"] = str(track.trackNumber)
    if save['trackTotal']:
        tag["TRACKTOTAL"] = str(track.album.trackTotal)
    if save['discNumber']:
        tag["DISCNUMBER"] = str(track.discNumber)
    if save['discTotal']:
        tag["DISCTOTAL"] = str(track.album.discTotal)
    if save['genre']:
        tag["GENRE"] = track.album.genre

    # YEAR tag is not suggested as a standard tag
    # Being YEAR already contained in DATE will only use DATE instead
    # Reference: https://www.xiph.org/vorbis/doc/v-comment.html#fieldnames
    if save['date']:
        tag["DATE"] = track.dateString
    elif save['year']:
        tag["DATE"] = str(track.date.year)

    if save['length']:
        tag["LENGTH"] = str(int(track.duration)*1000)
    if save['bpm'] and track.bpm:
        tag["BPM"] = str(track.bpm)
    if save['label']:
        tag["PUBLISHER"] = track.album.label
    if save['isrc']:
        tag["ISRC"] = track.ISRC
    if save['barcode']:
        tag["BARCODE"] = track.album.barcode
    if save['explicit']:
        tag["ITUNESADVISORY"] = "1" if track.explicit else "0"
    if save['replayGain']:
        tag["REPLAYGAIN_TRACK_GAIN"] = track.replayGain
    if track.lyrics.unsync and save['lyrics']:
        tag["LYRICS"] = track.lyrics.unsync

    for role in track.contributors:
        if role in ['author', 'engineer', 'mixer', 'producer', 'writer', 'composer']:
            if save['involvedPeople'] and role != 'composer' or save['composer'] and role == 'composer':
                tag[role] = track.contributors[role]
        elif role == 'musicpublisher' and save['involvedPeople']:
            tag["ORGANIZATION"] = track.contributors['musicpublisher']

    if save['copyright'] and track.copyright:
        tag["COPYRIGHT"] = track.copyright
    if save['savePlaylistAsCompilation'] and track.playlist or track.album.recordType == "compile":
        tag["COMPILATION"] = "1"

    if save['source']:
        tag["SOURCE"] = 'Deezer'
        tag["SOURCEID"] = str(track.id)

    if save['rating']:
        rank = round((int(track.rank) / 10000))
        tag['RATING'] = str(rank)

    if save['cover'] and track.album.embeddedCoverPath:
        image = Picture()
        image.type = PictureType.COVER_FRONT
        image.mime = 'image/jpeg'
        if str(track.album.embeddedCoverPath).endswith('png'):
            image.mime = 'image/png'
        with open(track.album.embeddedCoverPath, 'rb') as f:
            image.data = f.read()
        tag.add_picture(image)

    tag.save(deleteid3=True)
