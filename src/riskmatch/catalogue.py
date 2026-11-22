"""Verify the educational catalogue signature and enforce exact version and scope."""

from datetime import date
import json
from pathlib import Path
import subprocess

CAT = Path(__file__).resolve().parents[2] / "research/catalogue"


def approved(entry, as_of, currency, mandate, permission, directory=CAT):
    path = directory / "catalogue.json"
    payload = path.read_bytes()
    check = subprocess.run(
        [
            "openssl",
            "dgst",
            "-sha256",
            "-verify",
            str(directory / "signer.pem"),
            "-signature",
            str(directory / "catalogue.sig"),
        ],
        input=payload,
        capture_output=True,
    )
    if check.returncode:
        raise ValueError("Catalogue signature mismatch")
    matches = [
        r
        for r in json.loads(payload)["records"]
        if r["id"] == entry
        and r["approved"]
        and date.fromisoformat(r["as_of"]) <= as_of < date.fromisoformat(r["expires"])
        and r["currency"] == currency
        and r["mandate"] == mandate
        and r["permission"] == permission
    ]
    return matches[0] if len(matches) == 1 else None
