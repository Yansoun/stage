import os
import re
import json
import argparse
import numpy as np
import pandas as pd

from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer


# -----------------------
# Text normalization
# -----------------------
TOKEN_SYNONYMS = {
    "qty": "quantity",
    "quant": "quantity",
    "num": "number",
    "no": "number",
    "amt": "amount",
    "val": "value",
    "dt": "date",
    "ts": "timestamp",
    "time": "timestamp",
    "len": "length",
    "wid": "width",
    "ht": "height",
    "wt": "weight",
    "descr": "description",
}

STOP_TOKENS = {"dataset", "table", "csv", "data"}


def normalize_colname(name: str) -> str:
    name = str(name).strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name


def tokenize(name: str) -> list[str]:
    n = normalize_colname(name)
    toks = [t for t in n.split("_") if t and t not in STOP_TOKENS]
    toks = [TOKEN_SYNONYMS.get(t, t) for t in toks]
    return toks


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# -----------------------
# Semantic typing / grouping
# -----------------------
ID_HINTS = {"id", "key", "uuid"}
PRICE_HINTS = {"price", "unitprice", "unit", "cost", "amount", "total", "value"}
WEIGHT_HINTS = {"weight", "g", "kg", "gram"}
DIM_HINTS = {"length", "width", "height", "cm", "mm", "meter"}
COUNT_HINTS = {"qty", "quantity", "count", "number", "n", "photos"}
DATE_HINTS = {"date", "timestamp", "time", "created", "updated", "purchase"}


def keyword_group(tokens: set[str]) -> str:
    # assign a rough "meaning group" based on tokens
    if tokens & ID_HINTS or any(t.endswith("id") for t in tokens):
        return "id"
    if tokens & DATE_HINTS:
        return "datetime"
    if tokens & PRICE_HINTS:
        return "price"
    if tokens & WEIGHT_HINTS:
        return "weight"
    if tokens & DIM_HINTS:
        return "dimension"
    if tokens & COUNT_HINTS:
        return "count"
    return "other"


def infer_semantic_type(series: pd.Series, col_tokens: set[str]) -> str:
    # Use BOTH: column name hints + dtype stats
    if col_tokens & DATE_HINTS:
        return "datetime"

    # ID hint by name
    if (col_tokens & ID_HINTS) or ("id" in col_tokens) or any(t.endswith("id") for t in col_tokens):
        return "id"

    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    return "text"


def type_compat(src_type: str, tgt_type: str) -> float:
    if src_type == tgt_type:
        return 1.0
    # allow numeric<->id somewhat, but penalize
    if (src_type in {"id", "numeric"}) and (tgt_type in {"id", "numeric"}):
        return 0.6
    # text mixed with numeric is usually wrong
    if (src_type == "text" and tgt_type in {"numeric", "id"}) or (tgt_type == "text" and src_type in {"numeric", "id"}):
        return 0.1
    return 0.3


def group_compat(src_group: str, tgt_group: str) -> float:
    if src_group == tgt_group:
        return 1.0
    # if one side is "other", don't punish too much
    if src_group == "other" or tgt_group == "other":
        return 0.7
    # strong mismatch (id vs dimension/weight/price)
    if src_group == "id" and tgt_group in {"dimension", "weight", "price", "count"}:
        return 0.1
    if tgt_group == "id" and src_group in {"dimension", "weight", "price", "count"}:
        return 0.1
    # different measurement groups
    if src_group in {"dimension", "weight", "price", "count"} and tgt_group in {"dimension", "weight", "price", "count"}:
        return 0.3
    return 0.5


# -----------------------
# Loading / profiling
# -----------------------
def load_csv_sample(path: str, nrows: int = 2000) -> pd.DataFrame:
    # keep it simple and fast for MVP
    return pd.read_csv(path, nrows=nrows)


def build_schema(df: pd.DataFrame) -> dict:
    schema = {}
    for col in df.columns:
        toks = set(tokenize(col))
        sem_type = infer_semantic_type(df[col], toks)
        grp = keyword_group(toks)
        schema[col] = {
            "normalized": normalize_colname(col),
            "tokens": sorted(toks),
            "semantic_type": sem_type,
            "group": grp
        }
    return schema


# -----------------------
# Mapping engine v2
# -----------------------
def suggest_mappings_v2(
    src_path: str,
    tgt_path: str,
    top_k: int = 5,
    sample_rows: int = 2000,
    model_name: str = "all-MiniLM-L6-v2",
    threshold: float = 0.72,
    output_dir: str = "data/processed/mappings_v2",
):
    os.makedirs(output_dir, exist_ok=True)

    src_df = load_csv_sample(src_path, nrows=sample_rows)
    tgt_df = load_csv_sample(tgt_path, nrows=sample_rows)

    src_schema = build_schema(src_df)
    tgt_schema = build_schema(tgt_df)

    src_cols = list(src_df.columns)
    tgt_cols = list(tgt_df.columns)

    # Embeddings on normalized names only (fixes the "numeric matches numeric" issue)
    model = SentenceTransformer(model_name)
    src_texts = [src_schema[c]["normalized"].replace("_", " ") for c in src_cols]
    tgt_texts = [tgt_schema[c]["normalized"].replace("_", " ") for c in tgt_cols]

    src_emb = model.encode(src_texts, normalize_embeddings=True)
    tgt_emb = model.encode(tgt_texts, normalize_embeddings=True)

    name_sim = cosine_similarity(src_emb, tgt_emb)  # (n_src x n_tgt)

    # Build final scores with rules + compatibility
    final_scores = np.zeros_like(name_sim)

    for i, s in enumerate(src_cols):
        s_norm = src_schema[s]["normalized"]
        s_tokens = set(src_schema[s]["tokens"])
        s_type = src_schema[s]["semantic_type"]
        s_group = src_schema[s]["group"]

        for j, t in enumerate(tgt_cols):
            t_norm = tgt_schema[t]["normalized"]
            t_tokens = set(tgt_schema[t]["tokens"])
            t_type = tgt_schema[t]["semantic_type"]
            t_group = tgt_schema[t]["group"]

            # Rule 1: exact normalized match -> perfect
            if s_norm == t_norm:
                final_scores[i, j] = 1.0
                continue

            # Token overlap
            tok_sim = jaccard(s_tokens, t_tokens)

            # Compatibility
            tc = type_compat(s_type, t_type)
            gc = group_compat(s_group, t_group)

            # Weighted score
            # (name similarity is helpful but not sufficient; compat prevents nonsense)
            score = (
                0.60 * float(name_sim[i, j]) +
                0.20 * float(tok_sim) +
                0.12 * float(tc) +
                0.08 * float(gc)
            )

            final_scores[i, j] = score

    # Build suggestions output
    suggestions = []
    flat_rows = []

    for i, s in enumerate(src_cols):
        idx = np.argsort(final_scores[i])[::-1]
        top_idx = idx[:top_k]

        best_j = int(top_idx[0])
        best_score = float(final_scores[i, best_j])
        best_target = tgt_cols[best_j] if best_score >= threshold else "UNMAPPED"

        candidates = []
        for j in top_idx:
            candidates.append({
                "target_column": tgt_cols[int(j)],
                "confidence": float(final_scores[i, int(j)]),
                "target_info": tgt_schema[tgt_cols[int(j)]],
            })
            flat_rows.append({
                "source_column": s,
                "target_column": tgt_cols[int(j)],
                "confidence": float(final_scores[i, int(j)]),
            })

        suggestions.append({
            "source_column": s,
            "source_info": src_schema[s],
            "best_target": best_target,
            "best_confidence": best_score,
            "candidates": candidates
        })

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
            "threshold": threshold,
            "suggestions": suggestions,
        }, f, ensure_ascii=False, indent=2)

    pd.DataFrame(flat_rows).sort_values(["source_column", "confidence"], ascending=[True, False]).to_csv(out_csv, index=False)

    print("✅ Saved JSON:", out_json)
    print("✅ Saved CSV :", out_csv)
    return out_json, out_csv


def main():
    parser = argparse.ArgumentParser(description="Smart schema mapping engine (v2).")
    parser.add_argument("--src", required=True, help="Source CSV path")
    parser.add_argument("--tgt", required=True, help="Target CSV path")
    parser.add_argument("--top_k", type=int, default=5)
    parser.add_argument("--sample_rows", type=int, default=2000)
    parser.add_argument("--model", type=str, default="all-MiniLM-L6-v2")
    parser.add_argument("--threshold", type=float, default=0.72)
    parser.add_argument("--output_dir", type=str, default="data/processed/mappings_v2")
    args = parser.parse_args()

    suggest_mappings_v2(
        src_path=args.src,
        tgt_path=args.tgt,
        top_k=args.top_k,
        sample_rows=args.sample_rows,
        model_name=args.model,
        threshold=args.threshold,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()