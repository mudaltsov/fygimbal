#!/usr/bin/env python3

from Crypto.Cipher import AES
import binascii

key = binascii.a2b_hex('d81c99faa2f8f6689cfdd2b5ebae63b4');  # Left over in RAM after boot
iv = binascii.a2b_hex('7dc823ce45679e93c2b5681a53a9d051');   # Based on known-plaintext zero blocks

infile = open('MINI3D Firmware V1.15 - Rocker Position Mode.bin', 'rb')
outfile = open('plain.bin', 'wb')

header = infile.read(8)

while True:
    block = infile.read(1024)
    if not block:
        break
    outfile.write(AES.new(key, AES.MODE_CBC, iv).decrypt(block))
