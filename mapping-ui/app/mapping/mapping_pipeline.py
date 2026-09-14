import os
import json
import re
import argparse
import numpy as np
import pandas as pd

from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer


# -----------------------
# Utils
# -----------------------
def normalize_colname(name: str) -> str:
    name = str(name).strip().lower()
    name = re.sub(r"[^a-z0-9]+", " ", name)  # keep alnum, replace others with space
    name = re.sub(r"\s+", " ", name).strip()
    return name


def infer_semantic_type(series: pd.Series) -> str:
    dt = str(series.dtype)

    if "datetime" in dt:
        return "datetime"

    if pd.api.types.is_bool_dtype(series):
        return "boolean"

    if pd.api.types.is_numeric_dtype(series):
        # heuristic: id-like if many unique and integer-ish
        non_null = series.dropna()
        if len(non_null) == 0:
            return "numeric"
        uniq_ratio = non_null.nunique() / len(non_null)
        if uniq_ratio > 0.9:
            return "id_or_measure"
        return "numeric"

    # object/string
    non_null = series.dropna().astype(str)
    if len(non_null) == 0:
        return "text"
    avg_len = non_null.str.len().mean()
    if avg_len < 5:
        return "code_or_short_text"
    return "text"


def sample_value_summary(series: pd.Series, max_values: int = 6) -> str:
    s = series.dropna()
    if len(s) == 0:
        return "samples: []"

    if pd.api.types.is_numeric_dtype(s):
        return f"stats: min={s.min():.4g}, mean={s.mean():.4g}, max={s.max():.4g}"

    # strings
    s = s.astype(str)
    vals = s.unique()[:max_values]
    vals = [v[:40] for v in vals]  # trim long strings
    return "samples: [" + ", ".join(vals) + "]"


def build_column_profile(df: pd.DataFrame, col: str) -> str:
    series = df[col]
    normalized = normalize_colname(col)
    sem_type = infer_semantic_type(series)
    summary = sample_value_summary(series)

    # This “profile text” is what we embed:
    # it includes meaning from the name + hints from values
    profile = f"column: {col} | normalized: {normalized} | type: {sem_type} | {summary}"
    return profile


def load_csv_sample(path: str, nrows: int = 2000) -> pd.DataFrame:
    # Read small sample (fast) while keeping column names
    return pd.read_csv(path, nrows=nrows)


# -----------------------
# Mapping Engine
# -----------------------
def suggest_mappings(
    src_path: str,
    tgt_path: str,
    top_k: int = 5,
    sample_rows: int = 2000,
    model_name: str = "all-MiniLM-L6-v2",
    output_dir: str = "data/processed/mappings",
):
    os.makedirs(output_dir, exist_ok=True)

    src_df = load_csv_sample(src_path, nrows=sample_rows)
    tgt_df = load_csv_sample(tgt_path, nrows=sample_rows)

    src_cols = list(src_df.columns)
    tgt_cols = list(tgt_df.columns)

    # Build profiles
    src_profiles = [build_column_profile(src_df, c) for c in src_cols]
    tgt_profiles = [build_column_profile(tgt_df, c) for c in tgt_cols]

    # Embeddings
    model = SentenceTransformer(model_name)
    src_emb = model.encode(src_profiles, normalize_embeddings=True)
    tgt_emb = model.encode(tgt_profiles, normalize_embeddings=True)

    # Similarity matrix: (n_src x n_tgt)
    sim = cosine_similarity(src_emb, tgt_emb)

    # Build suggestions
    suggestions = []
    for i, src_col in enumerate(src_cols):
        # top k target indices
        top_idx = np.argsort(sim[i])[::-1][:top_k]
        candidates = []
        for j in top_idx:
            candidates.append({
                "target_column": tgt_cols[j],
                "confidence": float(sim[i, j]),
                "target_profile": tgt_profiles[j],
            })

        suggestions.append({
            "source_column": src_col,
            "source_profile": src_profiles[i],
            "candidates": candidates
        })

    # Save outputs
    base_name = f"{os.path.splitext(os.path.basename(src_path))[0]}__TO__{os.path.splitext(os.path.basename(tgt_path))[0]}"
    out_json = os.path.join(output_dir, f"{base_name}_mapping_suggestions.json")
    out_csv = os.path.join(output_dir, f"{base_name}_mapping_suggestions_flat.csv")

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "source_file": src_path,
            "target_file": tgt_path,
            "model": model_name,
            "top_k": top_k,
            "sample_rows": sample_rows,
            "suggestions": suggestions
        }, f, ensure_ascii=False, indent=2)

    # Flatten to CSV for quick view
    flat_rows = []
    for row in suggestions:
        src = row["source_column"]
        for cand in row["candidates"]:
            flat_rows.append({
                "source_column": src,
                "target_column": cand["target_column"],
                "confidence": cand["confidence"],
            })
    pd.DataFrame(flat_rows).to_csv(out_csv, index=False)

    return out_json, out_csv


# -----------------------
# CLI
# -----------------------
def main():
    parser = argparse.ArgumentParser(description="Smart schema mapping suggestions between two CSV files.")
    parser.add_argument("--src", required=True, help="Source CSV path")
    parser.add_argument("--tgt", required=True, help="Target CSV path")
    parser.add_argument("--top_k", type=int, default=5)
    parser.add_argument("--sample_rows", type=int, default=2000)
    parser.add_argument("--model", type=str, default="all-MiniLM-L6-v2")
    parser.add_argument("--output_dir", type=str, default="data/processed/mappings")
    args = parser.parse_args()

    out_json, out_csv = suggest_mappings(
        src_path=args.src,
        tgt_path=args.tgt,
        top_k=args.top_k,
        sample_rows=args.sample_rows,
        model_name=args.model,
        output_dir=args.output_dir
    )

    print("✅ Saved JSON:", out_json)
    print("✅ Saved CSV :", out_csv)


if __name__ == "__main__":
    main()