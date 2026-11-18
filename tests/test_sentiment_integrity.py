import json

import pytest

from src.audit_data import verify_sentiment_files
from src.provenance import sha256_file


@pytest.fixture
def artifacts(tmp_path):
    source = "sentiment_firm_daily.parquet"
    names = ["sentiment_asset_daily.parquet",
             "sentiment_observation_provenance.parquet",
             "sentiment_asset_coverage.csv"]
    for name in [source, *names]:
        (tmp_path / name).write_bytes(b"original data")
    metadata = {"source_file": source, "source_sha256": sha256_file(tmp_path / source),
                "files": {n: {"sha256": sha256_file(tmp_path / n)} for n in names}}
    (tmp_path / "sentiment_asset_metadata.json").write_text(json.dumps(metadata))
    return tmp_path


def test_complete_unchanged_bundle_passes(artifacts):
    verify_sentiment_files(artifacts)


@pytest.mark.parametrize("name", ["sentiment_firm_daily.parquet",
    "sentiment_asset_daily.parquet", "sentiment_observation_provenance.parquet",
    "sentiment_asset_coverage.csv"])
def test_modified_source_or_export_is_rejected(artifacts, name):
    (artifacts / name).write_bytes(b"modified data")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_sentiment_files(artifacts)


def test_legacy_manifest_requires_explicit_rebuild(artifacts):
    path = artifacts / "sentiment_asset_metadata.json"
    metadata = json.loads(path.read_text())
    del metadata["files"]
    path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="rebuild sentiment assets"):
        verify_sentiment_files(artifacts)


def test_missing_export_is_rejected(artifacts):
    (artifacts / "sentiment_asset_daily.parquet").unlink()
    with pytest.raises(FileNotFoundError):
        verify_sentiment_files(artifacts)
