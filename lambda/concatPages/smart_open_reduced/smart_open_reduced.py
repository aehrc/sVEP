import io

import boto3
import botocore.client
import six


DEFAULT_MIN_PART_SIZE = 50 * 1024**2
"""Default minimum part size for S3 multipart uploads"""
MIN_MIN_PART_SIZE = 5 * 1024**2
"""The absolute minimum permitted by Amazon."""


class BufferedOutputBase(io.BufferedIOBase):
    """Writes bytes to S3.

    Implements the io.BufferedIOBase interface of the standard library."""

    def __init__(self, bucket, key, min_part_size=DEFAULT_MIN_PART_SIZE,
                 s3_upload=None):
        if min_part_size < MIN_MIN_PART_SIZE:
            print("S3 requires minimum part size >= 5MB; \
multipart upload may fail")

        self._object = bucket.Object(key)
        self._min_part_size = min_part_size
        self._mp = self._object.initiate_multipart_upload(**(s3_upload or {}))

        self._buf = io.BytesIO()
        self._total_bytes = 0
        self._total_parts = 0
        self._parts = []

        #
        # This member is part of the io.BufferedIOBase interface.
        #
        self.raw = None

    def flush(self):
        pass

    #
    # Override some methods from io.IOBase.
    #
    def close(self):
        print('closing')
        if self._buf.tell():
            self._upload_next_part()

        if self._total_bytes and self._mp:
            self._mp.complete(MultipartUpload={'Parts': self._parts})
            print("completed multipart upload")
        elif self._mp:
            #
            # AWS complains with "The XML you provided was not well-formed or
            # did not validate against our published schema" when the input is
            # completely empty => abort the upload, no file created.
            #
            # We work around this by creating an empty file explicitly.
            #
            print("empty input, ignoring multipart upload")
            assert self._mp, "no multipart upload in progress"
            self._mp.abort()

            self._object.put(Body=b'')
        self._mp = None
        print("successfully closed")

    @property
    def closed(self):
        return self._mp is None

    def writable(self):
        """Return True if the stream supports writing."""
        return True

    def tell(self):
        """Return the current stream position."""
        return self._total_bytes

    #
    # io.BufferedIOBase methods.
    #
    def detach(self):
        raise io.UnsupportedOperation("detach() not supported")

    def write(self, b):
        """Write the given bytes (binary string) to the S3 file.

        There's buffering happening under the covers, so this may not actually
        do any HTTP transfer right away."""
        if not isinstance(b, six.binary_type):
            raise TypeError("input must be a binary string, got: %r", b)

        self._buf.write(b)
        self._total_bytes += len(b)

        if self._buf.tell() >= self._min_part_size:
            self._upload_next_part()

        return len(b)

    def terminate(self):
        """Cancel the underlying multipart upload."""
        assert self._mp, "no multipart upload in progress"
        self._mp.abort()
        self._mp = None

    #
    # Internal methods.
    #
    def _upload_next_part(self):
        part_num = self._total_parts + 1
        print("uploading part #{}, {} bytes (total {:.3}GB)".format(
            part_num, self._buf.tell(), self._total_bytes / 1024.0 ** 3))
        self._buf.seek(0)
        part = self._mp.Part(part_num)
        upload = part.upload(Body=self._buf)
        self._parts.append({'ETag': upload['ETag'], 'PartNumber': part_num})
        print("upload of part #%i finished" % part_num)

        self._total_parts += 1
        self._buf = io.BytesIO()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.terminate()
        else:
            self.close()
