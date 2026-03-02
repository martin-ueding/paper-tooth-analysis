"""CLI for paper texture analysis."""

import argparse
import pathlib
import sys

import matplotlib.pyplot as plt

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
        help="Write summary table (CSV or ODS by extension)",
    )
    parser.add_argument(
        "--plots",
        type=pathlib.Path,
        default=None,
        metavar="DIR",
        help="Write one combined horizontal bar plot PDF (facets per measure) into this directory",
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

    import pandas as pd

    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    if args.output is not None:
        if args.output.suffix.lower() == ".ods":
            df.to_excel(args.output, engine="odf", index=False)
        else:
            df.to_csv(args.output, index=False)

    if args.plots is not None:
        args.plots.mkdir(parents=True, exist_ok=True)
        measure_cols = [c for c in df.columns if c != "paper"]
        n = len(df)
        figheight = max(6, n * 0.5)
        fig, axes = plt.subplots(2, 3, sharey=True, figsize=(12, figheight))
        for ax, col in zip(axes.flat, measure_cols):
            ax.barh(df["paper"], df[col], height=0.7)
            ax.invert_yaxis()
            ax.set_xlabel(col)
            if ax.get_subplotspec().colspan.start > 0:
                ax.set_ylabel("")
                ax.tick_params(axis="y", labelleft=False)
        axes[0, 0].set_ylabel("paper")
        fig.tight_layout()
        fig.savefig(args.plots / "measures.pdf", format="pdf")
        plt.close(fig)

    return 0
