"""SolarFit MVP v2 — full pipeline orchestrator."""
import logging
import time
from pathlib import Path

from solar_mvp.config import OUTPUT_DIR

logger = logging.getLogger(__name__)

STAGE_NAMES = {
    1: "Data Collection (VWorld API)",
    2: "Geometry Processing (DEM terrain)",
    3: "Feature Enrichment",
    4: "Rule-Based Scoring (hard_filter_v2)",
    5: "Ground Truth Validation (recall@K)",
    6: "ML Weight Tuning",
    7: "Visualization (folium map)",
}


def run_stage(stage_num: int, force: bool = False) -> bool:
    """
    Run a single pipeline stage. Returns True on success, False on error.
    Imports stage module lazily to avoid loading all deps at startup.
    """
    try:
        if stage_num == 1:
            from solar_mvp.stage1_collect import collect_parcels
            collect_parcels(force=force)
        elif stage_num == 2:
            from solar_mvp.stage2_geom import process_geometry
            process_geometry(force=force)
        elif stage_num == 3:
            from solar_mvp.stage3_enrich import enrich_parcels
            enrich_parcels(force=force)
        elif stage_num == 4:
            from solar_mvp.stage4_score import score_parcels
            score_parcels(force=force)
        elif stage_num == 5:
            from solar_mvp.stage4_5_validate import validate_ground_truth
            validate_ground_truth(force=force)
        elif stage_num == 6:
            from solar_mvp.stage4_6_ml_tune import tune_ml_weights
            tune_ml_weights(force=force)
        elif stage_num == 7:
            from solar_mvp.stage5_viz import generate_map
            generate_map(force=force)
        else:
            logger.error("Unknown stage: %d", stage_num)
            return False
        return True
    except Exception as exc:
        logger.error("Stage %d failed: %s", stage_num, exc, exc_info=True)
        return False


def run_pipeline(start_from: int = 1, end_at: int = 7, force: bool = False) -> dict:
    """
    Run pipeline stages start_from..end_at inclusive.

    Returns dict: {
        "stages_run": list[int],
        "stages_succeeded": list[int],
        "stages_failed": list[int],
        "total_time_s": float,
    }
    """
    results = {"stages_run": [], "stages_succeeded": [], "stages_failed": [], "total_time_s": 0.0}
    pipeline_start = time.time()

    print(f"\n{'='*60}")
    print(f"  SolarFit MVP v2 Pipeline")
    print(f"  Stages: {start_from} → {end_at}  |  force={force}")
    print(f"{'='*60}\n")

    for stage_num in range(start_from, end_at + 1):
        stage_name = STAGE_NAMES.get(stage_num, f"Stage {stage_num}")
        print(f"[{stage_num}/{end_at}] Starting: {stage_name}")
        stage_start = time.time()

        success = run_stage(stage_num, force=force)
        elapsed = time.time() - stage_start

        results["stages_run"].append(stage_num)
        if success:
            results["stages_succeeded"].append(stage_num)
            print(f"  ✓ {stage_name} completed in {elapsed:.1f}s\n")
        else:
            results["stages_failed"].append(stage_num)
            print(f"  ✗ {stage_name} FAILED after {elapsed:.1f}s\n")
            # Stop on failure (stages are sequential)
            print(f"Pipeline halted at stage {stage_num}. Fix the error and rerun with --start-from {stage_num}")
            break

    results["total_time_s"] = time.time() - pipeline_start

    n_ok = len(results["stages_succeeded"])
    n_fail = len(results["stages_failed"])
    print(f"\n{'='*60}")
    print(f"  Pipeline done: {n_ok} succeeded, {n_fail} failed")
    print(f"  Total time: {results['total_time_s']:.1f}s")
    if n_fail == 0:
        print(f"\n  Outputs:")
        for f in sorted(OUTPUT_DIR.glob("*.csv")) + sorted(OUTPUT_DIR.glob("*.html")) + sorted(OUTPUT_DIR.glob("*.parquet")) + sorted(OUTPUT_DIR.glob("*.pkl")) + sorted(OUTPUT_DIR.glob("*.png")):
            size_kb = f.stat().st_size / 1024
            print(f"    {f.name} ({size_kb:.0f} KB)")
    print(f"{'='*60}\n")

    return results


if __name__ == "__main__":
    import argparse
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="SolarFit MVP v2 — Solar Site Detection Pipeline (해남군)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m solar_mvp.pipeline              # run all stages
  python -m solar_mvp.pipeline --start-from 4  # resume from scoring
  python -m solar_mvp.pipeline --stage 6    # run only stage 6
  python -m solar_mvp.pipeline --force      # re-run ignoring cached outputs
        """
    )
    parser.add_argument(
        "--start-from", type=int, default=1, metavar="N",
        help="Start from stage N (1-7, default: 1)"
    )
    parser.add_argument(
        "--end-at", type=int, default=7, metavar="N",
        help="End at stage N inclusive (default: 7)"
    )
    parser.add_argument(
        "--stage", type=int, metavar="N",
        help="Run only stage N (overrides --start-from and --end-at)"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force re-run even if outputs already exist"
    )
    parser.add_argument(
        "--list-stages", action="store_true",
        help="List available stages and exit"
    )
    parser.add_argument(
        "--check-data", action="store_true",
        help="Show data requirements status and exit"
    )

    args = parser.parse_args()

    if args.check_data:
        from solar_mvp.data_requirements import print_requirements
        print_requirements()
        raise SystemExit(0)

    if args.list_stages:
        print("\nAvailable stages:")
        for n, name in STAGE_NAMES.items():
            print(f"  {n}: {name}")
        print()
        raise SystemExit(0)

    start = args.stage if args.stage else args.start_from
    end = args.stage if args.stage else args.end_at

    run_pipeline(start_from=start, end_at=end, force=args.force)
