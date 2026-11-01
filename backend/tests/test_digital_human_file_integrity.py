from __future__ import annotations

import hashlib
import tracemalloc

import pytest

from digital_human.assurance import sha256_file


def test_sha256_file_preserves_empty_multichunk_tail_and_appended_bytes(tmp_path):
    artifact = tmp_path / "artifact.bin"
    artifact.touch()
    expected = hashlib.sha256()
    assert sha256_file(artifact) == expected.hexdigest()

    block = bytes(range(256)) * 4096
    tail = b"final partial chunk\x00\xff"
    with artifact.open("wb") as stream:
        for _ in range(3):
            stream.write(block)
            expected.update(block)
        stream.write(tail)
        expected.update(tail)
    assert sha256_file(artifact) == expected.hexdigest()

    appended = b"additional evidence bytes"
    with artifact.open("ab") as stream:
        stream.write(appended)
    expected.update(appended)
    assert sha256_file(artifact) == expected.hexdigest()


def test_sha256_file_has_bounded_peak_allocation_for_large_artifact(tmp_path):
    artifact = tmp_path / "large-artifact.bin"
    block = bytes(range(256)) * 4096
    expected = hashlib.sha256()
    with artifact.open("wb") as stream:
        for _ in range(32):
            stream.write(block)
            expected.update(block)

    tracemalloc.start()
    try:
        actual = sha256_file(artifact)
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert actual == expected.hexdigest()
    assert peak_bytes < 4 * 1024 * 1024


def test_sha256_file_propagates_missing_artifact(tmp_path):
    with pytest.raises(FileNotFoundError):
        sha256_file(tmp_path / "missing.bin")
