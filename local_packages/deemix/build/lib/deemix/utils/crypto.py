import binascii

from Cryptodome.Cipher import Blowfish, AES
from Cryptodome.Hash import MD5

def _md5(data):
    h = MD5.new()
    h.update(data.encode() if isinstance(data, str) else data)
    return h.hexdigest()

def _ecbCrypt(key, data):
    return binascii.hexlify(AES.new(key.encode(), AES.MODE_ECB).encrypt(data))

def _ecbDecrypt(key, data):
    return AES.new(key.encode(), AES.MODE_ECB).decrypt(binascii.unhexlify(data.encode("utf-8")))

def generateBlowfishKey(trackId):
    SECRET = 'g4el58wc0zvf9na1'
    idMd5 = _md5(trackId)
    bfKey = ""
    for i in range(16):
        bfKey += chr(ord(idMd5[i]) ^ ord(idMd5[i + 16]) ^ ord(SECRET[i]))
    return str.encode(bfKey)

def decryptChunk(key, data):
    return Blowfish.new(key, Blowfish.MODE_CBC, b"\x00\x01\x02\x03\x04\x05\x06\x07").decrypt(data)
