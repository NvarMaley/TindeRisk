"""Recreate the research report from the pinned private CHF catalogue."""

from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import tempfile

from .catalogue import instrument_panel, load_catalogue
from .reference import study


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as temp:
        json.dump(data, temp, indent=2, ensure_ascii=False, allow_nan=False)
        temp.write("\n")
    Path(temp.name).replace(path)


def main():
    config = Path("config/references-1.4.json")
    settings = json.loads(config.read_bytes())
    version = settings["catalogue"]
    catalogue = Path("data/local/1.3") / version / "returns.csv"
    coverage = json.loads(Path("reports/01-3-import-marche/coverage.json").read_bytes())
    digest = sha256(catalogue.read_bytes()).hexdigest()
    if version != coverage["version"] or digest != coverage["catalogue_sha256"]:
        raise ValueError("Catalogue different from the validated vintage")
    panel = instrument_panel(load_catalogue(catalogue), date.fromisoformat(max(coverage["common_month_ends"])))
    summaries, ledger = study(panel, settings)
    sensitivity = {}
    for rate in settings["sensitivity_bps"]:
        variants, _ = study(panel, settings | {"cost_bps": rate})
        sensitivity[str(rate)] = [{k: row[k] for k in ("mode", "start", "end", "cagr", "fees_chf")}
                                  for row in variants if row["mode"] != "cash"]
    write_json(Path("data/local/1.4/registre.json"), ledger)
    write_json(Path("reports/01-4-references/resultats.json"),
               dict(catalogue_sha256=digest, config_sha256=sha256(config.read_bytes()).hexdigest(),
                    version=settings["version"], periods=summaries, sensitivity_bps=sensitivity))
    print(f"{len(ledger)} lines of the register, {len(summaries)} period results")


if __name__ == "__main__":
    main()
