# Large local data files

All local research data are included in this repository. Four inputs exceed GitHub's ordinary per-file limit. Their exact bytes are stored in independently compressed chunks under `data/archive_parts/`; `manifest.json` records original paths, byte counts, SHA-256 hashes and ordered parts.

After cloning, reconstruct the four original files with Python (standard library only):

```sh
python3 research/restore_large_data.py
```

Keep about 6.6 GB of additional free space for the reconstructed originals. To check every chunk and original SHA-256 without writing the originals:

```sh
python3 research/restore_large_data.py --verify-only
```

The restored files are ignored by Git to avoid committing duplicates. All other data retain their original paths. `Theory/`, Python environments, credentials and operating-system metadata are excluded.
