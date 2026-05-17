"""Stage 4.6: ML weight tuning with leakage guards and spatial block CV."""
import logging
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.impute import SimpleImputer
from imblearn.over_sampling import SMOTE

from solar_mvp.config import (
    FEATURES_V2, FORBIDDEN_FEATURES, OUTPUT_DIR,
    N_SPATIAL_FOLDS, TRAIN_YEAR_MAX, TEST_YEAR_MIN,
    SPATIAL_FOLD_COLUMN, ENSEMBLE_RULE_WEIGHT, ENSEMBLE_ML_WEIGHT,
)
from solar_mvp.models import LOGISTIC_REGRESSION, XGBOOST, get_lr_weights

logger = logging.getLogger(__name__)


def check_no_leakage(feature_names: list[str]) -> None:
    """Raise ValueError if any forbidden feature is in the feature list."""
    leakers = set(feature_names) & FORBIDDEN_FEATURES
    if leakers:
        raise ValueError(f"DATA LEAKAGE: forbidden features in training: {leakers}")


def make_spatial_folds(parcels: pd.DataFrame, n_folds: int = N_SPATIAL_FOLDS) -> np.ndarray:
    """
    Assign each row a fold index (0..n_folds-1) based on eup_myeon.
    Unique eup_myeon values sorted alphabetically → round-robin into n_folds.
    Returns np.ndarray of int, shape (len(parcels),).
    """
    if SPATIAL_FOLD_COLUMN not in parcels.columns:
        # fallback: random folds
        rng = np.random.default_rng(42)
        return rng.integers(0, n_folds, size=len(parcels))
    eup_list = sorted(parcels[SPATIAL_FOLD_COLUMN].fillna("unknown").unique())
    eup_to_fold = {e: i % n_folds for i, e in enumerate(eup_list)}
    return parcels[SPATIAL_FOLD_COLUMN].fillna("unknown").map(eup_to_fold).to_numpy()


def recall_at_k(y_true: np.ndarray, y_score: np.ndarray, k: int) -> float:
    """Fraction of positives found in top-k ranked by y_score."""
    n_pos = y_true.sum()
    if n_pos == 0:
        return 0.0
    top_k_idx = np.argsort(y_score)[::-1][:k]
    return y_true[top_k_idx].sum() / n_pos


def train_and_evaluate(parcels: pd.DataFrame) -> dict:
    """
    Train LogReg and XGBoost on passing hard-filter parcels with spatial block CV.

    Minimum label check: if fewer than 10 positives pass hard filter,
    return {'insufficient_data': True, 'logreg': None, 'xgb': None, 'weights_ml': None}

    Returns dict with keys:
      logreg, xgb, weights_ml, imputer,
      logreg_cv_prauc (list), xgb_cv_prauc (list),
      logreg_cv_recall100 (list), xgb_cv_recall100 (list),
      insufficient_data (bool)
    """
    import copy

    check_no_leakage(FEATURES_V2)

    passing = parcels[parcels["passes_hard_filter"] == True].copy()
    X_all = passing[FEATURES_V2].copy()
    y_all = passing["is_installed"].fillna(False).astype(int)

    n_pos = int(y_all.sum())
    if n_pos < 10:
        logger.warning(
            "Only %d positive examples — skipping ML, using rule-based fallback", n_pos
        )
        return {
            "insufficient_data": True,
            "logreg": None,
            "xgb": None,
            "weights_ml": None,
            "imputer": None,
        }

    # Impute NaN with column medians
    imputer = SimpleImputer(strategy="median")
    X_imp = imputer.fit_transform(X_all)

    folds = make_spatial_folds(passing)
    n_folds = folds.max() + 1

    lr_prauc, xgb_prauc, lr_r100, xgb_r100 = [], [], [], []

    for fold_id in range(n_folds):
        val_mask = folds == fold_id
        tr_mask = ~val_mask
        if val_mask.sum() == 0 or tr_mask.sum() == 0:
            continue
        X_tr, X_val = X_imp[tr_mask], X_imp[val_mask]
        y_tr, y_val = y_all.values[tr_mask], y_all.values[val_mask]
        if y_tr.sum() == 0 or y_val.sum() == 0:
            continue

        # SMOTE on train fold only
        try:
            sm = SMOTE(random_state=42, k_neighbors=min(5, y_tr.sum() - 1))
            X_tr_res, y_tr_res = sm.fit_resample(X_tr, y_tr)
        except Exception:
            X_tr_res, y_tr_res = X_tr, y_tr

        # LogReg
        lr = copy.deepcopy(LOGISTIC_REGRESSION.model)
        lr.fit(X_tr_res, y_tr_res)
        lr_prob = lr.predict_proba(X_val)[:, 1]
        if y_val.sum() > 0:
            lr_prauc.append(average_precision_score(y_val, lr_prob))
            lr_r100.append(recall_at_k(y_val, lr_prob, min(100, len(y_val))))

        # XGBoost
        scale_pw = (y_tr == 0).sum() / max((y_tr == 1).sum(), 1)
        xgb_cfg = copy.deepcopy(XGBOOST.model)
        xgb_cfg.set_params(scale_pos_weight=scale_pw)
        xgb_cfg.fit(X_tr_res, y_tr_res)
        xgb_prob = xgb_cfg.predict_proba(X_val)[:, 1]
        if y_val.sum() > 0:
            xgb_prauc.append(average_precision_score(y_val, xgb_prob))
            xgb_r100.append(recall_at_k(y_val, xgb_prob, min(100, len(y_val))))

    # Final models fit on all data
    logreg_final = copy.deepcopy(LOGISTIC_REGRESSION.model)
    try:
        sm_final = SMOTE(random_state=42, k_neighbors=min(5, n_pos - 1))
        X_res, y_res = sm_final.fit_resample(X_imp, y_all.values)
    except Exception:
        X_res, y_res = X_imp, y_all.values
    logreg_final.fit(X_res, y_res)

    scale_pw_all = (y_all == 0).sum() / max(n_pos, 1)
    xgb_final = copy.deepcopy(XGBOOST.model)
    xgb_final.set_params(scale_pos_weight=scale_pw_all)
    xgb_final.fit(X_res, y_res)

    weights_ml = get_lr_weights(logreg_final, FEATURES_V2)

    return {
        "insufficient_data": False,
        "logreg": logreg_final,
        "xgb": xgb_final,
        "weights_ml": weights_ml,
        "imputer": imputer,
        "logreg_cv_prauc": lr_prauc,
        "xgb_cv_prauc": xgb_prauc,
        "logreg_cv_recall100": lr_r100,
        "xgb_cv_recall100": xgb_r100,
    }


def score_with_ml(parcels: gpd.GeoDataFrame, result: dict) -> gpd.GeoDataFrame:
    """
    Add score_ml column to all parcels.
    score_ml = XGBoost predicted probability of is_installed==1.
    NaN for parcels that failed hard filter, or if insufficient_data.
    """
    parcels = parcels.copy()
    parcels["score_ml"] = np.nan

    if result.get("insufficient_data"):
        # Fallback: use score_rule as score_ml
        logger.warning("Insufficient data — using score_rule as score_ml fallback")
        parcels["score_ml"] = parcels["score_rule"]
        return parcels

    xgb = result["xgb"]
    imputer = result["imputer"]
    passing_mask = parcels["passes_hard_filter"] == True
    X = parcels.loc[passing_mask, FEATURES_V2].copy()
    X_imp = imputer.transform(X)
    probs = xgb.predict_proba(X_imp)[:, 1]
    parcels.loc[passing_mask, "score_ml"] = probs
    return parcels


def add_ensemble_score(parcels: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    score_ensemble = 0.5 * norm(score_rule) + 0.5 * norm(score_ml)
    Normalize each score to [0,1] over non-NaN values.
    Result is NaN if either component is NaN.
    """
    parcels = parcels.copy()

    def _norm(s: pd.Series) -> pd.Series:
        lo, hi = s.min(), s.max()
        if hi == lo:
            return pd.Series(0.5, index=s.index)
        return (s - lo) / (hi - lo)

    rule_non_nan = parcels["score_rule"].dropna()
    ml_non_nan = parcels["score_ml"].dropna()

    rule_norm_vals = _norm(rule_non_nan)
    ml_norm_vals = _norm(ml_non_nan)

    rule_norm = parcels["score_rule"].map(rule_norm_vals).where(
        parcels["score_rule"].notna(), other=np.nan
    )
    ml_norm = parcels["score_ml"].map(ml_norm_vals).where(
        parcels["score_ml"].notna(), other=np.nan
    )

    parcels["score_ensemble"] = (
        ENSEMBLE_RULE_WEIGHT * rule_norm + ENSEMBLE_ML_WEIGHT * ml_norm
    )
    return parcels


def save_shap_plot(xgb_model, X: pd.DataFrame, output_path: Path) -> None:
    """Compute SHAP values and save summary plot."""
    try:
        import shap
        explainer = shap.TreeExplainer(xgb_model)
        sv = explainer.shap_values(X)
        if isinstance(sv, list):
            sv = sv[1]
        fig, ax = plt.subplots(figsize=(10, 7))
        shap.summary_plot(sv, X, show=False)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("SHAP plot saved → %s", output_path)
    except Exception as exc:
        logger.warning("SHAP plot failed: %s", exc)


def save_top_pnu_lists(parcels: gpd.GeoDataFrame, n: int = 100) -> None:
    """Save top_pnu_list_rule/ml/ensemble.csv with exact schema from spec."""
    p = parcels.copy()

    # Compute ranks
    p["rank_rule"] = p["score_rule"].rank(ascending=False, method="min", na_option="bottom")
    p["rank_ml"] = p["score_ml"].rank(ascending=False, method="min", na_option="bottom")

    # Compute centroids for lat/lon (geometry may be WGS84 or EPSG:5179)
    try:
        geom_wgs = p.geometry.to_crs("EPSG:4326")
    except Exception:
        geom_wgs = p.geometry
    centroids = geom_wgs.centroid
    p["lat"] = centroids.y
    p["lon"] = centroids.x

    # Ensure jibun_address col exists
    if "jibun_address" not in p.columns:
        p["jibun_address"] = ""

    SCHEMA = [
        "pnu", "jibun_address", "lat", "lon", "score_rule", "score_ml",
        "score_ensemble", "rank_rule", "rank_ml", "area_m2", "slope_mean",
        "jimok", "dropout_reason",
    ]
    for col in SCHEMA:
        if col not in p.columns:
            p[col] = np.nan

    for score_col, rank_col, fname in [
        ("score_rule",     "rank_rule", "top_pnu_list_rule.csv"),
        ("score_ml",       "rank_ml",   "top_pnu_list_ml.csv"),
        ("score_ensemble", None,        "top_pnu_list_ensemble.csv"),
    ]:
        if score_col == "score_ensemble":
            p["_ens_rank"] = p["score_ensemble"].rank(
                ascending=False, method="min", na_option="bottom"
            )
            top = p.nsmallest(n, "_ens_rank")[SCHEMA].reset_index(drop=True)
            p.drop(columns=["_ens_rank"], inplace=True)
        else:
            top = p.nsmallest(n, rank_col)[SCHEMA].reset_index(drop=True)
        top.to_csv(OUTPUT_DIR / fname, index=False, encoding="utf-8-sig")
        logger.info("Saved %s (%d rows)", fname, len(top))


def generate_score_comparison_html(
    parcels: gpd.GeoDataFrame, result: dict, output_path: Path
) -> None:
    """Generate self-contained HTML comparing rule vs ML scoring."""
    import base64
    import io
    from solar_mvp.config import WEIGHTS_RULE

    weights_ml = result.get("weights_ml") or {}
    cv_prauc = result.get("xgb_cv_prauc", [])
    cv_r100 = result.get("xgb_cv_recall100", [])

    # Weight comparison table
    weight_rows = ""
    for feat in FEATURES_V2:
        rw = WEIGHTS_RULE.get(feat, 0.0)
        mw = weights_ml.get(feat, float("nan"))
        agree = "✅" if (rw > 0) == (mw > 0) else "⚠️"
        weight_rows += (
            f"<tr><td>{feat}</td><td>{rw:+.3f}</td><td>{mw:+.3f}</td>"
            f"<td>{agree}</td></tr>"
        )

    # Top-100 overlap
    rule_top = (
        set(parcels.nlargest(100, "score_rule")["pnu"].tolist())
        if "score_rule" in parcels.columns
        else set()
    )
    ml_top = (
        set(parcels.nlargest(100, "score_ml")["pnu"].tolist())
        if "score_ml" in parcels.columns
        else set()
    )
    overlap = len(rule_top & ml_top)

    # Scatter plot
    scatter_b64 = ""
    try:
        fig, ax = plt.subplots(figsize=(6, 5))
        passing = parcels[parcels["passes_hard_filter"] == True]
        ax.scatter(passing["score_rule"], passing["score_ml"], alpha=0.3, s=10)
        ax.set_xlabel("score_rule")
        ax.set_ylabel("score_ml")
        ax.set_title("Rule vs ML Score")
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        scatter_b64 = base64.b64encode(buf.getvalue()).decode()
        plt.close(fig)
    except Exception:
        pass

    # CV metrics
    mean_prauc = float(np.mean(cv_prauc)) if cv_prauc else float("nan")
    mean_r100 = float(np.mean(cv_r100)) if cv_r100 else float("nan")

    insufficient = result.get("insufficient_data", False)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>SolarFit Score Comparison</title>
<style>body{{font-family:sans-serif;max-width:1000px;margin:0 auto;padding:20px}}
h1{{background:#2c3e50;color:white;padding:15px;border-radius:5px}}
h2{{color:#2c3e50;border-bottom:2px solid #3498db}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ddd;padding:8px;text-align:left}}
th{{background:#3498db;color:white}}tr:nth-child(even){{background:#f9f9f9}}
.warn{{color:#e67e22;font-weight:bold}}.ok{{color:#27ae60}}
</style></head><body>
<h1>SolarFit MVP — Score Comparison Report</h1>
{"<p class='warn'>⚠️ INSUFFICIENT POSITIVE EXAMPLES — ML fallback to rule-based scores</p>" if insufficient else ""}
<h2>CV Metrics (XGBoost)</h2>
<table><tr><th>Metric</th><th>Mean</th><th>Values per fold</th></tr>
<tr><td>PR-AUC</td><td>{mean_prauc:.3f}</td><td>{[f"{v:.3f}" for v in cv_prauc]}</td></tr>
<tr><td>Recall@100</td><td>{mean_r100:.3f}</td><td>{[f"{v:.3f}" for v in cv_r100]}</td></tr>
</table>
<h2>Top-100 Overlap: {overlap}/100 parcels appear in both rule-top-100 and ml-top-100</h2>
<p class="{'ok' if 40<=overlap<=70 else 'warn'}">
{'Healthy agreement (40–70%)' if 40<=overlap<=70 else 'Check: overlap outside expected 40–70% range'}
</p>
<h2>Weight Comparison (Rule vs ML)</h2>
<table><tr><th>Feature</th><th>Rule weight</th><th>ML weight</th><th>Direction agree?</th></tr>
{weight_rows}</table>
<h2>Score Scatter Plot</h2>
{"<img src='data:image/png;base64," + scatter_b64 + "' width='600'>" if scatter_b64 else "<p>Plot unavailable</p>"}
</body></html>"""

    output_path.write_text(html, encoding="utf-8")
    logger.info("Score comparison report → %s", output_path)


def tune_ml_weights(force: bool = False) -> gpd.GeoDataFrame:
    """Stage 4.6: Train ML, generate scores, save all outputs."""
    input_path = OUTPUT_DIR / "parcels_validated.parquet"
    output_parquet = OUTPUT_DIR / "parcels_final.parquet"

    if output_parquet.exists() and not force:
        logger.info("parcels_final.parquet exists — skipping (use --force to rerun)")
        return gpd.read_parquet(output_parquet)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input not found: {input_path}\n"
            "Run stage4_5_validate.py first."
        )

    logger.info("Loading parcels_validated.parquet...")
    parcels = gpd.read_parquet(input_path)

    # Train
    logger.info("Training ML models...")
    result = train_and_evaluate(parcels)

    # Score
    parcels = score_with_ml(parcels, result)
    parcels = add_ensemble_score(parcels)

    # Save parquet
    parcels.to_parquet(output_parquet)
    logger.info("Saved parcels_final.parquet (%d rows)", len(parcels))

    # Save model pkl
    model_path = OUTPUT_DIR / "ml_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(
            {
                "logreg": result.get("logreg"),
                "xgb": result.get("xgb"),
                "imputer": result.get("imputer"),
            },
            f,
        )
    logger.info("Saved ml_model.pkl")

    # SHAP
    if not result.get("insufficient_data") and result["xgb"] is not None:
        passing = parcels[parcels["passes_hard_filter"] == True]
        X_imp_df = pd.DataFrame(
            result["imputer"].transform(passing[FEATURES_V2]),
            columns=FEATURES_V2,
        )
        save_shap_plot(result["xgb"], X_imp_df, OUTPUT_DIR / "shap_summary.png")

    # Score comparison report
    generate_score_comparison_html(parcels, result, OUTPUT_DIR / "score_comparison.html")

    # Top PNU lists
    save_top_pnu_lists(parcels)

    # Print summary
    n_pass = int((parcels["passes_hard_filter"] == True).sum())
    n_installed = (
        int(parcels["is_installed"].sum())
        if "is_installed" in parcels.columns
        else 0
    )
    cv_prauc = result.get("xgb_cv_prauc", [])
    cv_r100 = result.get("xgb_cv_recall100", [])
    print(f"\n=== Stage 4.6 ML Tuning Summary ===")
    print(f"Passing hard filter: {n_pass}")
    print(f"Installed (ground truth): {n_installed}")
    if cv_prauc:
        print(f"XGBoost CV PR-AUC: {np.mean(cv_prauc):.3f} ± {np.std(cv_prauc):.3f}")
    if cv_r100:
        print(f"XGBoost CV Recall@100: {np.mean(cv_r100):.3f} ± {np.std(cv_r100):.3f}")
    if result.get("insufficient_data"):
        print("⚠️  Insufficient positives — ML fallback used (score_ml = score_rule)")

    return parcels


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    tune_ml_weights(force=args.force)
