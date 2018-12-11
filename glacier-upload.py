import os
import pprint
import argparse

import humanfriendly
import boto3
import botocore.utils


DEFAULT_CHUNK_SIZE = 67108864  # 64MB


class Upload(object):
    def __init__(self, args):
        self.vault = args.vault
        self.file = args.file
        self.description = args.description
        self.chunk_size = args.chunk_size
        self.verbose = args.verbose
        self.multipart_upload_resource = None
        self.part_checksums = {}

    def get_chunks(self):
        start_byte = 0
        count = 0
        with open(self.file, 'rb') as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    return

                end_byte = start_byte + len(chunk) - 1

                yield chunk, start_byte, end_byte, count

                start_byte += len(chunk)
                count += 1

                if len(chunk) < self.chunk_size:
                    return

    def initiate_upload(self):
        client = boto3.client('glacier')
        initiate_response = client.initiate_multipart_upload(vaultName=self.vault,
                                                             archiveDescription=self.description,
                                                             partSize=str(self.chunk_size))
        pprint.pprint(initiate_response)

        upload_id = initiate_response['uploadId']
        account_id = boto3.client('sts').get_caller_identity()['Account']

        glacier = boto3.resource('glacier')
        self.multipart_upload_resource = glacier.MultipartUpload(account_id, self.vault, upload_id)

    def upload_all_chunks(self):
        for chunk in self.get_chunks():
            chunk_bytes, start_byte, end_byte, count = chunk
            content_range = 'bytes {}-{}/*'.format(start_byte, end_byte)
            print('Uploading chunk {} ({})'.format(count, content_range))

            response = self.multipart_upload_resource.upload_part(range=content_range, body=chunk_bytes)

            self.part_checksums[chunk.count] = response['checksum']

    def complete_upload(self):
        total_size = os.path.getsize(self.file)
        total_checksum = botocore.utils.calculate_tree_hash(open(self.file, 'rb'))

        completion_response = self.multipart_upload_resource.complete(total_size, total_checksum)
        pprint.pprint(completion_response)


def parse_args():
    def parse_chunk_size():
        # Parse the chunk size if supplied as an argument, e.g. ['4MB'] -> 4194304
        # If no argument is supplied, we use the default, and no parsing is needed
        chunk_size = humanfriendly.parse_size(args.chunk_size, binary=True) \
            if isinstance(args.chunk_size, list) \
            else args.chunk_size

        if chunk_size < 1048576 or chunk_size > 4294967296:
            raise ValueError('Illegal chunk size: must be between 1 MiB and 4 GiB ({} b given)'.format(chunk_size))

        # Only chunks that are a megabyte multiplied by a power of 2 are allowed, e.g. 2^4 MiB = 16 MiB
        chunk_megabytes = int(chunk_size / 1048576)
        if chunk_megabytes & (chunk_megabytes - 1):
            raise ValueError('Illegal chunk size: {} is not a power of 2'.format(chunk_megabytes))

        return chunk_size

    parser = argparse.ArgumentParser(description='Upload large files to AWS Glacier easily.')
    parser.add_argument('vault', nargs=1, type=str, help='Glacier vault to upload to')
    parser.add_argument('file', nargs=1, type=str, help='file to upload')
    parser.add_argument('-v', '--verbose', default=False, action='store_true', help='verbose output')
    parser.add_argument('-d', '--description', nargs=1, type=str, metavar='DESC',
                        help='file description - defaults to file name')
    parser.add_argument('-s', '--chunk-size', nargs=1, type=str, dest='chunk_size', default=DEFAULT_CHUNK_SIZE,
                        metavar='SIZE', help='chunk size, specified as number + scale, e.g. "4MB", "2GB" - '
                                             'must be a megabyte multiplied by a power of 2, max 4 GiB, use '
                                             'suffix MB/MiB/GB/GiB, etc. (defaults to 64 MiB)')
    args = parser.parse_args()
    args.vault = args.vault[0]
    args.file = args.file[0]
    args.description = args.description if args.description else os.path.basename(args.file)
    args.chunk_size = parse_chunk_size()
    return args


def main():
    args = parse_args()
    upload = Upload(args)
    upload.initiate_upload()
    upload.upload_all_chunks()
    upload.complete_upload()


if __name__ == '__main__':
    main()
