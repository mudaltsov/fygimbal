#!/usr/bin/env python3

from Crypto.Cipher import AES
import binascii, struct

key = binascii.a2b_hex('d81c99faa2f8f6689cfdd2b5ebae63b4');  # Left over in RAM after boot
iv = binascii.a2b_hex('7dc823ce45679e93c2b5681a53a9d051');   # Based on known-plaintext zero blocks

firmwares = [open('mcu%d.bin' % i, 'rb').read() for i in range(3)]

BLOCK = 1024

def numBlocks(img):
	nBlocks = len(img)//1024
	if len(img) != nBlocks*1024:
		raise ValueError("Image size not a block multiple")
	return nBlocks

def encryptBlocks(img):
	cyphertext = []
	for i in range(numBlocks(img)):
		block = img[i*1024:(i+1)*1024]
		cyphertext.append(AES.new(key, AES.MODE_CBC, iv).encrypt(block))
	return b''.join(cyphertext)

sizes = struct.pack('<HHH', *map(numBlocks, firmwares))
body = sizes + b''.join(map(encryptBlocks, firmwares))
calc_crc16 = binascii.crc_hqx(body, 0xffff)
crc_header = struct.pack('<H', calc_crc16)

open('assembled.bin', 'wb').write(crc_header + body)
