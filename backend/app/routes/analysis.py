"""
CSV Analysis Engine — SparqAI
Accepts a CSV upload, runs statistical analysis, and returns
chart-ready JSON + summary stats. No file storage — everything
is processed in-memory and returned immediately.
"""

import io
import json
import logging
from typing import Optional

import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from ..database import get_db
from ..middleware.auth import get_current_user
from .. import models

logger = logging.getLogger(__name__)
router = APIRouter()


def _safe_json(obj):
    """Convert numpy/pandas types to plain Python for JSON serialisation."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


@router.post("/csv")
async def analyze_csv(
    file: UploadFile = File(...),
    analysis_type: str = Form("auto"),   # auto | revenue | decisions | custom
    current_user: models.User = Depends(get_current_user),
):
    """
    Upload any CSV and get back:
    - summary stats (rows, columns, dtypes, nulls)
    - detected numeric columns with distributions
    - time-series data if a date column is found
    - bar / line / pie chart data ready for the frontend
    - top-level insights (anomalies, trends, highlights)
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10 MB hard limit
        raise HTTPException(status_code=400, detail="File too large (max 10 MB).")

    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV is empty.")

    df.columns = [c.strip() for c in df.columns]

    # -----------------------------------------------------------------------
    # 1. Basic info
    # -----------------------------------------------------------------------
    rows, cols = df.shape
    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
    null_counts = df.isnull().sum().to_dict()
    null_counts = {k: int(v) for k, v in null_counts.items()}

    # -----------------------------------------------------------------------
    # 2. Detect column roles
    # -----------------------------------------------------------------------
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    text_cols = df.select_dtypes(include=["object"]).columns.tolist()

    # Date detection
    date_col = None
    for col in text_cols:
        try:
            parsed = pd.to_datetime(df[col], infer_datetime_format=True, errors="coerce")
            if parsed.notna().sum() > rows * 0.5:
                df[col] = parsed
                date_col = col
                text_cols.remove(col)
                break
        except Exception:
            pass

    # Revenue / amount column heuristic
    amount_col = None
    for candidate in ["amount", "revenue", "value", "total", "sales", "deal_value", "price"]:
        matches = [c for c in numeric_cols if candidate in c.lower()]
        if matches:
            amount_col = matches[0]
            break
    if not amount_col and numeric_cols:
        amount_col = numeric_cols[0]

    # Category column heuristic (for pie/bar charts)
    category_col = None
    for candidate in ["category", "type", "stage", "status", "source", "channel", "region", "owner"]:
        matches = [c for c in text_cols if candidate in c.lower()]
        if matches:
            category_col = matches[0]
            break
    if not category_col and text_cols:
        # pick lowest cardinality text col
        cardinalities = {c: df[c].nunique() for c in text_cols}
        category_col = min(cardinalities, key=cardinalities.get)

    # -----------------------------------------------------------------------
    # 3. Summary statistics for all numeric columns
    # -----------------------------------------------------------------------
    summary_stats = {}
    for col in numeric_cols:
        s = df[col].dropna()
        if len(s) == 0:
            continue
        summary_stats[col] = {
            "count": int(s.count()),
            "mean": round(float(s.mean()), 2),
            "median": round(float(s.median()), 2),
            "std": round(float(s.std()), 2) if len(s) > 1 else 0,
            "min": round(float(s.min()), 2),
            "max": round(float(s.max()), 2),
            "sum": round(float(s.sum()), 2),
            "q25": round(float(s.quantile(0.25)), 2),
            "q75": round(float(s.quantile(0.75)), 2),
        }

    # -----------------------------------------------------------------------
    # 4. Charts
    # -----------------------------------------------------------------------
    charts = []

    # --- Chart A: Time series (line chart) ---
    if date_col and amount_col:
        ts = df[[date_col, amount_col]].dropna()
        ts = ts.sort_values(date_col)
        # Resample to monthly if > 60 rows
        if len(ts) > 60:
            ts = ts.set_index(date_col).resample("ME")[amount_col].sum().reset_index()
        charts.append({
            "id": "timeseries",
            "type": "line",
            "title": f"{amount_col} Over Time",
            "x_label": date_col,
            "y_label": amount_col,
            "data": [
                {"x": str(row[date_col])[:10], "y": round(float(row[amount_col]), 2)}
                for _, row in ts.iterrows()
                if pd.notna(row[amount_col])
            ],
        })

    # --- Chart B: Category breakdown (bar chart) ---
    if category_col and amount_col:
        grouped = (
            df.groupby(category_col)[amount_col]
            .sum()
            .sort_values(ascending=False)
            .head(12)
        )
        charts.append({
            "id": "by_category",
            "type": "bar",
            "title": f"{amount_col} by {category_col}",
            "x_label": category_col,
            "y_label": amount_col,
            "data": [
                {"x": str(k), "y": round(float(v), 2)}
                for k, v in grouped.items()
                if pd.notna(v)
            ],
        })

    # --- Chart C: Category distribution (pie chart) ---
    if category_col:
        value_counts = df[category_col].value_counts().head(8)
        charts.append({
            "id": "distribution",
            "type": "pie",
            "title": f"Distribution by {category_col}",
            "data": [
                {"label": str(k), "value": int(v)}
                for k, v in value_counts.items()
            ],
        })

    # --- Chart D: Histogram of primary numeric column ---
    if amount_col:
        col_data = df[amount_col].dropna()
        hist, bin_edges = np.histogram(col_data, bins=min(20, len(col_data) // 2 + 1))
        charts.append({
            "id": "histogram",
            "type": "histogram",
            "title": f"Distribution of {amount_col}",
            "x_label": amount_col,
            "y_label": "Count",
            "data": [
                {
                    "range": f"{round(float(bin_edges[i]),1)}–{round(float(bin_edges[i+1]),1)}",
                    "count": int(hist[i]),
                    "x": round(float((bin_edges[i] + bin_edges[i+1]) / 2), 2),
                }
                for i in range(len(hist))
                if hist[i] > 0
            ],
        })

    # --- Chart E: Correlation heatmap data (if multiple numeric cols) ---
    if len(numeric_cols) >= 2:
        corr = df[numeric_cols].corr().round(2)
        corr_data = []
        for r in numeric_cols:
            for c in numeric_cols:
                val = corr.loc[r, c]
                if pd.notna(val):
                    corr_data.append({"x": r, "y": c, "value": round(float(val), 2)})
        charts.append({
            "id": "correlation",
            "type": "heatmap",
            "title": "Correlation Matrix",
            "data": corr_data,
            "columns": numeric_cols,
        })

    # -----------------------------------------------------------------------
    # 5. AI-style insights (rule-based, no LLM required)
    # -----------------------------------------------------------------------
    insights = []

    if amount_col and amount_col in summary_stats:
        s = summary_stats[amount_col]
        insights.append(f"Total {amount_col}: {s['sum']:,.2f} across {s['count']} rows.")
        if s["std"] > s["mean"] * 0.5:
            insights.append(
                f"{amount_col} shows high variability (std={s['std']:,.2f}), "
                f"suggesting outliers or distinct segments."
            )

    if date_col and amount_col and charts:
        ts_chart = next((c for c in charts if c["id"] == "timeseries"), None)
        if ts_chart and len(ts_chart["data"]) >= 2:
            first_val = ts_chart["data"][0]["y"]
            last_val = ts_chart["data"][-1]["y"]
            if first_val and last_val:
                pct = ((last_val - first_val) / abs(first_val)) * 100 if first_val != 0 else 0
                direction = "grew" if pct > 0 else "declined"
                insights.append(
                    f"{amount_col} {direction} {abs(pct):.1f}% from the first to last period."
                )

    if category_col and amount_col:
        bar_chart = next((c for c in charts if c["id"] == "by_category"), None)
        if bar_chart and bar_chart["data"]:
            top = bar_chart["data"][0]
            insights.append(
                f"Top {category_col}: '{top['x']}' contributes "
                f"{top['y']:,.2f} in {amount_col}."
            )

    if null_counts:
        high_null = {k: v for k, v in null_counts.items() if v > rows * 0.2}
        if high_null:
            cols_str = ", ".join(f"{k} ({v} missing)" for k, v in high_null.items())
            insights.append(f"Data quality warning: high null rates in: {cols_str}.")

    # -----------------------------------------------------------------------
    # 6. Preview rows (first 10)
    # -----------------------------------------------------------------------
    preview = json.loads(df.head(10).to_json(orient="records", date_format="iso", default_handler=str))

    return {
        "filename": file.filename,
        "rows": rows,
        "columns": cols,
        "column_names": list(df.columns),
        "dtypes": dtypes,
        "null_counts": null_counts,
        "detected": {
            "date_column": date_col,
            "amount_column": amount_col,
            "category_column": category_col,
            "numeric_columns": numeric_cols,
            "text_columns": text_cols,
        },
        "summary_stats": summary_stats,
        "charts": charts,
        "insights": insights,
        "preview": preview,
    }


@router.post("/csv/compare")
async def compare_csvs(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
):
    """Compare two CSVs side-by-side — useful for period-over-period analysis."""
    async def _read_df(f: UploadFile) -> pd.DataFrame:
        content = await f.read()
        return pd.read_csv(io.BytesIO(content))

    try:
        df_a = await _read_df(file_a)
        df_b = await _read_df(file_b)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    numeric_a = df_a.select_dtypes(include=[np.number]).columns.tolist()
    numeric_b = df_b.select_dtypes(include=[np.number]).columns.tolist()
    common = list(set(numeric_a) & set(numeric_b))

    comparison = {}
    for col in common:
        a_val = float(df_a[col].sum())
        b_val = float(df_b[col].sum())
        pct = ((b_val - a_val) / abs(a_val) * 100) if a_val != 0 else 0
        comparison[col] = {
            "file_a": round(a_val, 2),
            "file_b": round(b_val, 2),
            "change": round(b_val - a_val, 2),
            "change_pct": round(pct, 1),
            "direction": "up" if pct > 0 else "down" if pct < 0 else "flat",
        }

    return {
        "file_a": {"name": file_a.filename, "rows": len(df_a), "cols": len(df_a.columns)},
        "file_b": {"name": file_b.filename, "rows": len(df_b), "cols": len(df_b.columns)},
        "common_numeric_columns": common,
        "comparison": comparison,
    }
