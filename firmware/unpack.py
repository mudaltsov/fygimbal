#!/usr/bin/env python3

from Crypto.Cipher import AES
import binascii, struct

key = binascii.a2b_hex('d81c99faa2f8f6689cfdd2b5ebae63b4');  # Left over in RAM after boot
iv = binascii.a2b_hex('7dc823ce45679e93c2b5681a53a9d051');   # Based on known-plaintext zero blocks

infile = open('MINI3D Firmware V1.15 - Rocker Position Mode.bin', 'rb').read()

stored_crc16, size0, size1, size2 = struct.unpack('<HHHH', infile[:8])
calc_crc16 = binascii.crc_hqx(infile[2:], 0xffff)
if calc_crc16 != stored_crc16:
    raise ValueError("Unexpected CRC, found %04X but calculated %04X" % (stored_crc16, calc_crc16))

def decryptBlocks(offset, count, outfile):
    for i in range(count):
        block = infile[8+(offset+i)*1024:8+(offset+i+1)*1024]
        outfile.write(AES.new(key, AES.MODE_CBC, iv).decrypt(block))

decryptBlocks(0, size0, open('mcu0.bin', 'wb'))
decryptBlocks(size0, size1, open('mcu1.bin', 'wb'))
decryptBlocks(size0+size1, size2, open('mcu2.bin', 'wb'))
