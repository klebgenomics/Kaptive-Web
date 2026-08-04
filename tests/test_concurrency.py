"""Concurrency test module."""

import asyncio

from rammappy import Aligner, Index

idx = Index.build([(b"target1", b"ATGCGTACGATCGATC" * 10)])
aligner = Aligner(idx)


async def worker(i: int) -> None:
    """Worker function."""
    res = await asyncio.to_thread(aligner.map, b"query", b"ATGCGTACGATCGATC" * 10)
    res = list(res)
    print(f"Worker {i} got {len(res)} results")


async def main() -> None:
    """Main execution function."""
    await asyncio.gather(*(worker(i) for i in range(10)))


asyncio.run(main())
