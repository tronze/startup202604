"""Allow running `python -m solar_mvp` as the pipeline CLI."""
from solar_mvp.pipeline import run_pipeline
import sys

if __name__ == "__main__":
    # Re-invoke via pipeline's argparse
    import runpy
    runpy.run_module("solar_mvp.pipeline", run_name="__main__", alter_sys=True)
