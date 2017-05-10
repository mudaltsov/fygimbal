#!/usr/bin/env python3

import argparse
import binascii
import collections
import itertools
import struct


# Block size used by Feiyu Tech gimbal firmware.
FW_BLOCK_SIZE = 1024

# Not a technical limit, just something practical for human-readable output.
# If the limit is increased, the output formatting may need to change.
MAX_FILES = 10


def parse_args():
    epilog = '\n'.join([
        'output format for data comparison:',
        '  F[I]:L   file index F, image index I with column label L',
        '',
        '  OOOOOO   probably empty value',
        '  ######   unique value',
        '  =====C   duplicate value at this offset only',
        '  +NHHHC   duplicate value at multiple offsets',
        '  +++++C   last duplicate value at multiple offsets',
        '',
        '  C is the column with distinct duplicate values in each row',
        '  N is the column of the next duplicate value below',
        '  0xHHH00 is a hex offset to the next duplicate value below',
    ])

    p = argparse.ArgumentParser(
        description='Compare encrypted firmware data for Feiyu Tech gimbals',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog)
    p.add_argument('-g', '--group-by-file',
                   action='store_true',
                   help='group columns by file instead of axis')
    p.add_argument('-p', '--per-axis',
                   action='store_true',
                   help='perform separate comparison for each axis')
    p.add_argument('--chunk-size',
                   type=int,
                   default=16,  # Appears to be the cipher block size.
                   choices=[2 ** n for n in range(2, 11)],  # 4 to 1024.
                   metavar='SIZE',
                   help='split data into SIZE-byte chunks for matching')
    p.add_argument('--empty-count',
                   type=int,
                   default=10,
                   metavar='NUM',
                   help='mark 1 KB blocks as empty if used NUM times per file')
    p.add_argument('files',
                   nargs='+',
                   metavar='<fw.bin>',
                   help='gimbal firmware files')

    args = p.parse_args()

    if len(args.files) > MAX_FILES:
        raise ValueError('Too many files! (max %d)' % MAX_FILES)

    return args


def main():
    args = parse_args()

    # All firmware data indexed by [file_idx][image_idx][chunk_idx].
    all_chunks = []

    # Map of unique chunks to list of (file_idx, image_idx, chunk_idx),
    # used to locate duplicated data between all firmware images.
    #
    # Note: this approach will only find duplicated data that perfectly aligns
    # on the chunk boundaries. This works for data encrypted by block ciphers,
    # and is much easier than searching for arbitrary lengths and offsets.
    unique_chunk_refs = {}

    # Counter for unique 1 KB blocks, used to find data that's probably empty.
    unique_block_counter = collections.Counter()
    empty_chunks = set()

    for file_idx, filename in enumerate(args.files):
        all_chunks.append([])
        fw_images = read_firmware_images(filename)

        print('File %d: %d-axis, firmware images: %s KB in %s' % (
                file_idx,
                len(fw_images),
                ', '.join('%d' % (len(i) / FW_BLOCK_SIZE) for i in fw_images),
                repr(filename)))

        for image_idx, image in enumerate(fw_images):
            unique_block_counter.update(split_data(image, FW_BLOCK_SIZE))
            chunks = split_data(image, args.chunk_size)
            all_chunks[file_idx].append(chunks)

            for chunk_idx, chunk in enumerate(chunks):
                ref = unique_chunk_refs.setdefault(chunk, [])
                ref.append((file_idx, image_idx, chunk_idx))

    # Report block statistics and determine empty blocks.
    print('\nFound %d unique / %d total %d-byte blocks.' % (
            len(unique_block_counter),
            sum(unique_block_counter.values()),
            FW_BLOCK_SIZE))
    for block, count in unique_block_counter.items():
        if count >= args.empty_count * len(args.files):
            empty_chunks.update(split_data(block, args.chunk_size))
            print('Probably empty block used %d times:  [%s ... %s]' % (
                    count,
                    binascii.b2a_hex(block[:8]).decode(),
                    binascii.b2a_hex(block[-8:]).decode()))

    # Report chunk statistics.
    use_counter = collections.Counter(map(len, unique_chunk_refs.values()))
    print('\nFound %d unique / %d total %d-byte chunks.' % (
            len(unique_chunk_refs),
            sum(used * chunks for used, chunks in use_counter.items()),
            args.chunk_size))
    print('\nNumer of times each chunk was used:')
    used_chunks = sorted(use_counter.items())
    for item in [('used', 'chunks')] + used_chunks:
        print('%4s%8s' % item)

    print('\nData comparison:')
    for loop_idx in range(3 if args.per_axis else 1):
        print('')
        file_range = range(len(all_chunks))
        image_range = [loop_idx] if args.per_axis else range(3)
        fi_indices = list(filter(lambda fi: len(all_chunks[fi[0]]) > fi[1],
                                 itertools.product(file_range, image_range)))

        if not args.group_by_file:
            fi_indices.sort(key=lambda fi: (fi[1], fi[0]))

        compare(fi_indices, all_chunks, unique_chunk_refs, empty_chunks, args)


def compare(fi_indices, all_chunks, unique_chunk_refs, empty_chunks, args):
    """Print a detailed comparison of the firmware data for each chunk offset.

    Repeated results are merged together to cover the longest possible spans
    of data on each printed line.
    """
    prev_data = []
    labels = {}

    # Assign a letter to each column, always ending with X, Y, Z.
    # Note: this may break if MAX_FILES is increased.
    letters = 'ghijklmnopqrstuvwxyzGHIJKLMNOPQRSTUVWXYZ'
    for n, fi in enumerate(fi_indices):
        if (args.group_by_file and fi[1] == 0) or \
           (not args.group_by_file and fi[0] == 0):
            prev_data.append(' ')

        label = letters[n - len(fi_indices)]
        labels[fi] = label
        prev_data.append('%d[%d]:%s' % (fi + (label,)))

    print_columns('offset  ', 'length ', prev_data, ' bytes + KB')

    chunk_idx = 0
    offset = 0
    length = 0

    while any(not column.isspace() for column in prev_data):
        data = []

        for file_idx, image_idx in fi_indices:
            chunks = all_chunks[file_idx][image_idx]

            if (args.group_by_file and image_idx == 0) or \
               (not args.group_by_file and file_idx == 0):
                data.append(' ')

            if chunk_idx >= len(chunks):
                data.append(' ' * 6)  # not present in file/image
                continue

            chunk = chunks[chunk_idx]
            if chunk in empty_chunks:
                data.append('O' * 6)  # empty value
                continue

            # List of (file_idx, image_idx, chunk_idx) where the chunk is used.
            refs = unique_chunk_refs[chunk]
            if args.per_axis:
                refs = list(filter(lambda fic: fic[1] == image_idx, refs))

            if len(refs) == 1:
                data.append('#' * 6)  # unique value
                continue

            # Determine if the duplicate value is used at multiple offsets.
            dup_key = None
            next_dist_keys = []

            for (file_ref, image_ref, chunk_ref) in refs:
                key = (file_ref, image_ref)
                dist = chunk_ref - chunk_idx
                if dist == 0:
                    dup_key = key if not dup_key else min(dup_key, key)
                else:
                    next_dist_keys.append(((args.chunk_size * dist), key))

            dup_label = labels.get(dup_key, '?')

            if len(next_dist_keys) == 0:
                dup_str = '=' * 5  # duplicate value at this offset only
            elif max(next_dist_keys)[0] < 0:
                dup_str = '+' * 5  # last duplicate value at multiple offsets
            else:
                dist, key = min(n for n in next_dist_keys if n[0] > 0)
                if dist % FW_BLOCK_SIZE == 0:
                    # Duplicate value at multiple offsets. Since it's aligned
                    # to 1024 bytes (0x400), we can truncate two hex zeroes.
                    dup_str = '+%s%03x' % (labels.get(key, '?'), dist >> 8)
                else:
                    # Not expected to happen due to encrypted block size.
                    print('*** Unexpected data collision! (%d, %d, %d, %d)' % (
                            file_idx, image_idx, chunk_idx, next))
                    dup_str = '?' * 5

            data.append(dup_str + dup_label)

        # Remove unnecessary labels if all duplicate values are identical
        if len(set([d for d in data if d[0] == '='])) == 1:
            data = ['=' * 6 if d[0] == '=' else d for d in data]

        if data != prev_data:
            if chunk_idx > 0:
                print_data_columns(offset, length, prev_data)
            prev_data = data
            offset += length
            length = 0

        chunk_idx += 1
        length += args.chunk_size


def print_data_columns(offset, length, data):
    kb, b = divmod(length, FW_BLOCK_SIZE)
    kb_label = 'k' if kb else ' '
    plus = '+' if (b and kb) else ' '
    byte_kb = '%6s %s %2s%s' % (b or '', plus, kb or '', kb_label)

    print_columns('0x%05x ' % offset, '0x%05x' % length, data, byte_kb)


def print_columns(offset, length, data, byte_kb):
    print('  '.join([offset, length] + data + [byte_kb]))


def split_data(data, chunk_size):
    return [data[c:c+chunk_size] for c in range(0, len(data), chunk_size)]


def read_firmware_images(filename):
    """Read Feiyu Tech gimbal firmware images from the specified file.

    Feiyu Tech gimbal firmware .bin files have an 8-byte header followed by
    firmware image data for each axis MCU. The firmware is encrypted in 1 KB
    blocks, which are individually sent from the update utility to the gimbal.

    The header contains four 16-bit little-endian values. The first value is
    a CRC of the remaining header and data bytes. The other 3 values specify
    the number of 1 KB blocks for each firmware image. There is a special case
    for 2-axis gimbals, which specify 0xA55A as the number of blocks but don't
    have any data for the third firmware image.
    """
    with open(filename, 'rb') as file:
        data = file.read()

    header_crc = struct.unpack('<H', data[:2])[0]

    crc = binascii.crc_hqx(data[2:], 0xffff)
    if header_crc != crc:
        raise ValueError('Header CRC 0x%04x != computed CRC 0x%04x for %s' % (
                            header_crc, crc, repr(filename)))

    offset = 8
    result = []

    for num_blocks in struct.unpack('<HHH', data[2:8]):
        if num_blocks == 0xA55A:
            continue

        end = offset + num_blocks * FW_BLOCK_SIZE

        if end > len(data):
            raise ValueError('Firmware image [%d] needs %d KB of data at '
                             'offset %d, which exceeds the size (%d) of %s' % (
                                len(result), num_blocks, offset, len(data),
                                repr(filename)))

        result.append(data[offset:end])
        offset = end

    if offset != len(data):
        raise ValueError('Unused data (%d bytes) at the end of %s' % (
                            len(data) - offset, repr(filename)))

    return result


if __name__ == '__main__':
    main()
