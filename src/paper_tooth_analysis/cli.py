"""CLI for paper texture analysis."""

import argparse
import pathlib
import sys

from .analysis import PATCH_DEFAULT, analyze_patch, load_patch


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Paper texture analysis: depth and coarseness from shaded scans.")
    parser.add_argument(
        "input",
        type=pathlib.Path,
        default=pathlib.Path("papers"),
        nargs="?",
        help="Directory containing PNG images (default: papers)",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=PATCH_DEFAULT,
        metavar="N",
        help=f"Center-crop patch size in pixels (default: {PATCH_DEFAULT})",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=pathlib.Path,
        default=None,
        help="Write summary table to CSV",
    )
    args = parser.parse_args(argv)

    if not args.input.is_dir():
        print(f"Error: not a directory: {args.input}", file=sys.stderr)
        return 1

    paths = sorted(args.input.glob("*.png"))
    if not paths:
        print(f"Error: no PNG files in {args.input}", file=sys.stderr)
        return 1

    rows = []
    for path in paths:
        try:
            patch = load_patch(str(path), size=args.size)
        except Exception as e:
            print(f"Error loading {path}: {e}", file=sys.stderr)
            return 1
        metrics = analyze_patch(patch)
        rows.append({"paper": path.stem, **metrics})

    try:
        import pandas as pd
    except ImportError:
        pd = None

    if pd is not None:
        df = pd.DataFrame(rows)
        print(df.to_string(index=False))
        if args.output is not None:
            df.to_csv(args.output, index=False)
    else:
        if rows:
            col_width = max(len(str(v)) for r in rows for v in r.values()) + 2
            fmt = "  ".join([f"{{:{col_width}}}" for _ in rows[0]])
            print(fmt.format(*rows[0].keys()))
            for r in rows:
                print(fmt.format(*r.values()))
        if args.output is not None:
            import csv
            with args.output.open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else [])
                w.writeheader()
                w.writerows(rows)

    return 0
