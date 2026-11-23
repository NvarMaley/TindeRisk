import argparse
from datetime import date
import json
from pathlib import Path

from .catalogue import describe, equal_weight_reference, instrument_panel, load_catalogue


def main() -> None:
    parser = argparse.ArgumentParser(description="RiskMatch V2 catalogue diagnostics")
    parser.add_argument("--catalogue", type=Path)
    parser.add_argument("--as-of", type=date.fromisoformat)
    args = parser.parse_args()
    try:
        rows = load_catalogue(args.catalogue)
        latest = max((row.date for row in rows if row.role == "instrument"), default=None)
        if latest is None:
            raise ValueError("No instruments available")
        as_of = args.as_of or latest
        instruments = instrument_panel(rows, as_of)
        reference = equal_weight_reference(instruments)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps({
        "data_mode": "demo" if args.catalogue is None else "user_supplied",
        "as_of": as_of.isoformat(),
        "instruments": {asset: describe(list(values.values()))
                        for asset, values in instruments.items()},
        "equal_weight_reference_gross": describe(list(reference.values())),
    }, indent=2))


if __name__ == "__main__":
    main()
