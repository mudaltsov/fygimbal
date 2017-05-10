#!/usr/bin/env python3

from Crypto.Cipher import AES
import binascii, struct

key = binascii.a2b_hex('d81c99faa2f8f6689cfdd2b5ebae63b4');  # Left over in RAM after boot
iv = binascii.a2b_hex('7dc823ce45679e93c2b5681a53a9d051');   # Based on known-plaintext zero blocks

infile = open('MINI3D Firmware V1.15 - Rocker Position Mode.bin', 'rb')

crc16, size0, size1, size2 = struct.unpack('<HHHH', infile.read(8))

def decryptBlocks(count, outfile):
	for i in range(count):
   		outfile.write(AES.new(key, AES.MODE_CBC, iv).decrypt(infile.read(1024)))

decryptBlocks(size0, open('mcu0.bin', 'wb'))
decryptBlocks(size1, open('mcu1.bin', 'wb'))
decryptBlocks(size2, open('mcu2.bin', 'wb'))
