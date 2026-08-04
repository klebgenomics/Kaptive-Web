"""Parser test module."""

import gzip
import io
from typing import IO, cast

from fastapi import UploadFile
from kaptive.core.genome import GenomeAssembly

compressed_data = gzip.compress(b">seq1\nATGC\n")
upload_file = UploadFile(filename="test.fasta.gz", file=io.BytesIO(compressed_data))


def _parse(u_file: UploadFile, fname: str) -> GenomeAssembly:
    """Parse genome from upload file."""
    import bz2
    import gzip
    import lzma

    file_obj = u_file.file
    if fname.endswith(".gz"):
        file_obj = gzip.GzipFile(fileobj=u_file.file, mode="rb")
    elif fname.endswith(".bz2"):
        file_obj = bz2.BZ2File(u_file.file, mode="rb")
    elif fname.endswith(".xz"):
        file_obj = lzma.LZMAFile(u_file.file, mode="rb")

    return GenomeAssembly.from_stream(cast(IO[bytes], file_obj), id_=fname)


asm = _parse(upload_file, "test.fasta.gz")
print(asm.id, len(asm.contigs.seqs))
