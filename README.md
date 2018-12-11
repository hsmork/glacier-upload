# glacier-upload

Utility to simplify multipart uploads to AWS Glacier. 
Useful since the AWS CLI command `aws glacier upload-archive` handles a maximum file size of 4 GB, beyond which 
multipart uploads are required, and managing multipart uploads manually is tedious.

Basically a wrapper around the `MultipartUpload` resource from boto3.

## Prerequisites
- An AWS account where you have already created the Glacier vaults you will use
- Python 3
- Some other dependencies, install with `pip install -r requirements.txt`

## Usage
`python glacier-upload.py [-h] [-v] [-d DESC] [-s SIZE] vault file`

Argument | Optional | Usage
--- | --- | ---
`-h`, `--help` | Yes | Print help message and exit.
`-v`, `--verbose` | Yes | More detailed output.
`-d DESC`, `--description DESC` | Yes | Apply the description `DESC` to the archive. Defaults to the filename.
`-s SIZE`, `--chunk-size SIZE` | Yes | Upload the archive in chunks of size `SIZE`. Defaults to `64MB`.
`vault` | No | Name of the Glacier vault to which the archive will be uploaded.
`file` | No | Full path to the archive to be uploaded.

Examples (assuming `big_archive.zip` is in your working directory):
- `python glacier-upload.py my_backup_vault big_archive.zip`
- `python glacier-upload.py --chunk-size 256MB --description 'Family photos 2012-2015' my_backup_vault big_archive.zip`

## Tips
- You must already have AWS credentials that boto3 can use. Logging in is not handled.
- Chunk size is supplied in human-readable format, e.g. `4MB`, `1GB`, etc. 
Both `MB` and `MiB`-style suffixes are supported, and both are taken to be powers of 1024, since this behaviour is required by boto3. 
- The chunk size value must be `1MB` times a power of 2 - e.g. `8MB` and `1GB` are acceptable since 8 and 1024 
are powers of 2, whereas `3MB` is not acceptable. The value must be between `1MB` and `4GB`, inclusive.

## Todo
- Parallel uploading
- Upload several files in one go
- More robust error handling (e.g. should formally cancel the upload in case of error)
- Better code structure

## Licence
MIT
