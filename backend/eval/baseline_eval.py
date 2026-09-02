#!/usr/bin/env python3
"""Read-only baseline evaluation for the current tile retrieval pipeline.

This script intentionally does not modify embeddings, rankings, or model code.
It measures the existing system as-is using SKU-level ground truth from the
training dataset folders.

Important:
- An image is treated as a query against the existing `search_tile` pipeline.
- Ground truth is the tile's SKU derived from the folder name.
- Confidence is treated as the raw similarity score currently returned by the
  application, not as a calibrated probability.
- The low-confidence threshold defaults to the same gate used in the current
  search logic: 0.60 raw similarity.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import all model modules so the SQLAlchemy registry is configured before queries.
from app.database import SessionLocal
from app.models.admin import Admin  # noqa: F401
from app.models.categories import (  # noqa: F401
    Application,
    ColorFamily,
    Finish,
    Material,
    Origin,
    SizeFormat,
    Style,
)
from app.models.inventory import Inventory, WarehouseLocation  # noqa: F401
from app.models.search_log import SearchLog  # noqa: F401
from app.models.tile import Tile  # noqa: F401
from app.models.tile_image import TileEmbedding, TileImage  # noqa: F401
from ai.search import search_tile

DATASET_ROOT = ROOT / "dataset" / "train"
REPORT_DIR = ROOT / "eval" / "reports"
LOW_CONFIDENCE_THRESHOLD = 0.60
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
TRANSFORMATION_ORDER = [
    "orig", "rotated", "blurred", "bright", "dim", "warm", "cool",
    "zoomed", "combo", "cracked", "noisy", "other",
]


@dataclass
class QueryRecord:
    query_image: str
    tile_folder: str
    ground_truth_sku: str
    transformation: str
    predicted_skus_top5: str
    top1_correct: bool
    top3_correct: bool
    top5_correct: bool
    top1_rank: int | None
    top_result_score: float | None
    latency_ms: float
    failed: bool
    low_confidence: bool


def infer_folder_sku(folder_name: str) -> str:
    try:
        tile_number = folder_name.split("_")[1]
        return f"MRB-{int(tile_number):03d}"
    except Exception:
        return folder_name


def infer_transformation(file_name: str) -> str:
    lowered = file_name.lower()
    stem = Path(file_name).stem.lower()

    markers = {
        "orig": ["orig"],
        "rotated": ["rot", "flip"],
        "blurred": ["blur"],
        "bright": ["bright", "light"],
        "dim": ["dim", "dark"],
        "warm": ["warm"],
        "cool": ["cool"],
        "zoomed": ["zoom"],
        "noisy": ["noise"],
        "cracked": ["crack"],
        "combo": ["combo"],
    }

    for label, tokens in markers.items():
        if any(token in stem for token in tokens):
            return label
    return "other"


def tile_folders(dataset_root: Path) -> List[Path]:
    def folder_key(folder: Path) -> tuple[int, str]:
        suffix = folder.name.rsplit("_", 1)[-1]
        return (int(suffix), folder.name) if suffix.isdigit() else (sys.maxsize, folder.name)

    return sorted(
        [
            folder
            for folder in dataset_root.iterdir()
            if folder.is_dir() and folder.name.startswith("tile_")
        ],
        key=folder_key,
    )


def available_images(dataset_root: Path) -> Dict[Path, Dict[str, List[Path]]]:
    images_by_tile: Dict[Path, Dict[str, List[Path]]] = {}
    for folder in tile_folders(dataset_root):
        groups: Dict[str, List[Path]] = defaultdict(list)
        for image in sorted(folder.iterdir()):
            if image.is_file() and image.suffix.lower() in VALID_EXTENSIONS:
                groups[infer_transformation(image.name)].append(image)
        images_by_tile[folder] = dict(groups)
    return images_by_tile


def select_query_paths(
    images_by_tile: Dict[Path, Dict[str, List[Path]]],
    sample_per_tile: int,
    max_queries: int | None,
    requested_transformations: List[str] | None,
) -> List[Path]:
    observed = {
        transformation
        for groups in images_by_tile.values()
        for transformation in groups
    }
    if requested_transformations:
        transformation_order = [
            transformation
            for transformation in TRANSFORMATION_ORDER
            if transformation in requested_transformations and transformation in observed
        ]
        transformation_order.extend(
            sorted(set(requested_transformations) & observed - set(transformation_order))
        )
    else:
        transformation_order = [
            transformation for transformation in TRANSFORMATION_ORDER if transformation in observed
        ]
        transformation_order.extend(sorted(observed - set(transformation_order)))

    selected_by_tile: Dict[Path, List[Path]] = {}
    for tile_index, (folder, groups) in enumerate(images_by_tile.items()):
        selected: List[Path] = []
        for offset in range(sample_per_tile):
            start = (tile_index + offset) % max(1, len(transformation_order))
            for step in range(len(transformation_order)):
                transformation = transformation_order[(start + step) % len(transformation_order)]
                candidates = groups.get(transformation, [])
                candidate_index = offset // max(1, len(transformation_order))
                if candidates and candidate_index < len(candidates):
                    selected.append(candidates[candidate_index])
                    break
            if len(selected) >= sample_per_tile:
                break
        selected_by_tile[folder] = selected

    # Round-robin tiles so a query cap cannot become a filesystem-prefix sample.
    selected_paths: List[Path] = []
    for offset in range(sample_per_tile):
        for folder in images_by_tile:
            tile_paths = selected_by_tile[folder]
            if offset < len(tile_paths):
                selected_paths.append(tile_paths[offset])
                if max_queries is not None and len(selected_paths) >= max_queries:
                    return selected_paths
    return selected_paths


def iter_query_paths(
    dataset_root: Path,
    sample_per_tile: int = 1,
    max_queries: int | None = None,
    transformations: List[str] | None = None,
) -> Iterable[Path]:
    if sample_per_tile < 1:
        raise ValueError("sample_per_tile must be at least 1")
    yield from select_query_paths(
        available_images(dataset_root), sample_per_tile, max_queries, transformations
    )


def evaluate_single_query(db, image_path: Path, ground_truth_sku: str) -> Dict[str, Any]:
    with image_path.open("rb") as f:
        image_bytes = f.read()

    start = time.perf_counter()
    response = search_tile(
        image_input=image_bytes,
        db=db,
        top_k=5,
        min_confidence=0.0,
        material_id=None,
        color_family_id=None,
        validate_tile=False,
    )
    latency_ms = (time.perf_counter() - start) * 1000.0

    results = response.get("results", [])
    predicted_skus = [str(item.get("sku", "")) for item in results[:5]]
    top_result = results[0] if results else {}
    top_score = float(top_result.get("confidence", 0.0)) / 100.0 if top_result else None

    predicted_rank = None
    for idx, sku in enumerate(predicted_skus, start=1):
        if sku == ground_truth_sku:
            predicted_rank = idx
            break

    top1_correct = predicted_rank == 1
    top3_correct = predicted_rank is not None and predicted_rank <= 3
    top5_correct = predicted_rank is not None and predicted_rank <= 5
    failed = len(results) == 0
    low_confidence = (top_score is not None and top_score < LOW_CONFIDENCE_THRESHOLD) or failed

    return {
        "query_image": str(image_path.relative_to(ROOT)),
        "tile_folder": image_path.parent.name,
        "ground_truth_sku": ground_truth_sku,
        "transformation": infer_transformation(image_path.name),
        "predicted_skus_top5": json.dumps(predicted_skus),
        "top1_correct": top1_correct,
        "top3_correct": top3_correct,
        "top5_correct": top5_correct,
        "top1_rank": predicted_rank,
        "top_result_score": top_score,
        "latency_ms": latency_ms,
        "failed": failed,
        "low_confidence": low_confidence,
    }


def summarize_records(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {
            "queries": 0,
            "top1_accuracy": 0.0,
            "top3_accuracy": 0.0,
            "top5_accuracy": 0.0,
            "recall_at_1": 0.0,
            "recall_at_3": 0.0,
            "recall_at_5": 0.0,
            "average_latency_ms": 0.0,
            "median_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "average_top1_similarity": 0.0,
            "median_top1_similarity": 0.0,
            "failed_searches": 0,
            "failed_percentage": 0.0,
            "low_confidence_searches": 0,
            "low_confidence_percentage": 0.0,
        }

    total = len(records)
    top1_accuracy = sum(1 for r in records if r["top1_correct"]) / total
    top3_accuracy = sum(1 for r in records if r["top3_correct"]) / total
    top5_accuracy = sum(1 for r in records if r["top5_correct"]) / total
    recall_at_1 = sum(1 for r in records if r["top1_rank"] == 1) / total
    recall_at_3 = sum(1 for r in records if r["top1_rank"] is not None and r["top1_rank"] <= 3) / total
    recall_at_5 = sum(1 for r in records if r["top1_rank"] is not None and r["top1_rank"] <= 5) / total

    latencies = [float(r["latency_ms"]) for r in records]
    sorted_latencies = sorted(latencies)
    p95_index = min(len(sorted_latencies) - 1, max(0, int(len(sorted_latencies) * 0.95) - 1))
    similarities = [
        float(r["top_result_score"])
        for r in records
        if r["top_result_score"] is not None
    ]
    failed_count = sum(1 for r in records if r["failed"])
    low_conf_count = sum(1 for r in records if r["low_confidence"])

    return {
        "queries": total,
        "top1_accuracy": top1_accuracy,
        "top3_accuracy": top3_accuracy,
        "top5_accuracy": top5_accuracy,
        "recall_at_1": recall_at_1,
        "recall_at_3": recall_at_3,
        "recall_at_5": recall_at_5,
        "average_latency_ms": statistics.fmean(latencies),
        "median_latency_ms": statistics.median(latencies),
        "p95_latency_ms": sorted_latencies[p95_index],
        "average_top1_similarity": statistics.fmean(similarities) if similarities else 0.0,
        "median_top1_similarity": statistics.median(similarities) if similarities else 0.0,
        "failed_searches": failed_count,
        "failed_percentage": (failed_count / total) * 100.0,
        "low_confidence_searches": low_conf_count,
        "low_confidence_percentage": (low_conf_count / total) * 100.0,
    }


def summarize_by_transformation(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["transformation"]].append(record)

    summary: Dict[str, Any] = {}
    for transformation, subset in sorted(grouped.items()):
        summary[transformation] = summarize_records(subset)
    return summary


def write_csv(report_path: Path, records: List[Dict[str, Any]]) -> None:
    fieldnames = [
        "query_image",
        "tile_folder",
        "ground_truth_sku",
        "transformation",
        "predicted_skus_top5",
        "top1_correct",
        "top3_correct",
        "top5_correct",
        "top1_rank",
        "top_result_score",
        "latency_ms",
        "failed",
        "low_confidence",
    ]
    with report_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            writer.writerow({key: row.get(key) for key in fieldnames})


def write_markdown(
    report_path: Path,
    records: List[Dict[str, Any]],
    summary: Dict[str, Any],
    by_transformation: Dict[str, Any],
    metadata: Dict[str, Any],
) -> None:
    lines = []
    lines.append("# Baseline Retrieval Evaluation Report")
    lines.append("")
    lines.append(f"- Dataset root: `{DATASET_ROOT}`")
    lines.append(f"- Unique tiles evaluated: {metadata['unique_tiles_evaluated']}")
    lines.append(f"- Unique tiles available: {metadata['unique_tiles_available']}")
    lines.append(f"- Total images available: {metadata['total_images_available']}")
    lines.append(f"- Total queries evaluated: {summary['queries']}")
    lines.append(f"- Sample per tile: {metadata['sample_per_tile']}")
    lines.append(f"- Transformations requested: {', '.join(metadata['transformations_requested'])}")
    lines.append(f"- Runtime: {metadata['runtime_seconds']:.2f} seconds")
    lines.append("- Low-confidence uses the existing `search_tile` 0.60 raw-similarity gate; raw similarity is not a probability.")
    lines.append("")
    lines.append("## Dataset coverage")
    lines.append("")
    lines.append("| Transformation | Queries | Unique tiles |")
    lines.append("|---|---:|---:|")
    for transformation, count in metadata["queries_per_transformation"].items():
        lines.append(f"| {transformation} | {count} | {metadata['tiles_per_transformation'][transformation]} |")
    lines.append("")
    lines.append("## Overall summary")
    lines.append("")
    lines.append(f"- Top-1 accuracy: {summary['top1_accuracy'] * 100:.2f}%")
    lines.append(f"- Top-3 accuracy: {summary['top3_accuracy'] * 100:.2f}%")
    lines.append(f"- Top-5 accuracy: {summary['top5_accuracy'] * 100:.2f}%")
    lines.append(f"- Recall@1: {summary['recall_at_1'] * 100:.2f}%")
    lines.append(f"- Recall@3: {summary['recall_at_3'] * 100:.2f}%")
    lines.append(f"- Recall@5: {summary['recall_at_5'] * 100:.2f}%")
    lines.append(f"- Average latency: {summary['average_latency_ms']:.2f} ms")
    lines.append(f"- Median latency: {summary['median_latency_ms']:.2f} ms")
    lines.append(f"- P95 latency: {summary['p95_latency_ms']:.2f} ms")
    lines.append(f"- Failed searches: {summary['failed_searches']} ({summary['failed_percentage']:.2f}%)")
    lines.append(f"- Low-confidence searches: {summary['low_confidence_searches']} ({summary['low_confidence_percentage']:.2f}%)")
    lines.append(f"- Average top-1 similarity: {summary['average_top1_similarity']:.4f}")
    lines.append(f"- Median top-1 similarity: {summary['median_top1_similarity']:.4f}")
    lines.append("")
    lines.append("## Per transformation")
    lines.append("")
    for transformation, stats in by_transformation.items():
        lines.append(f"### {transformation}")
        lines.append(f"- Top-1 accuracy: {stats['top1_accuracy'] * 100:.2f}%")
        lines.append(f"- Top-3 accuracy: {stats['top3_accuracy'] * 100:.2f}%")
        lines.append(f"- Top-5 accuracy: {stats['top5_accuracy'] * 100:.2f}%")
        lines.append(f"- Failed: {stats['failed_searches']} ({stats['failed_percentage']:.2f}%)")
        lines.append(f"- Low confidence: {stats['low_confidence_searches']} ({stats['low_confidence_percentage']:.2f}%)")
        lines.append("")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-per-tile", type=int, default=1)
    parser.add_argument("--max-queries", type=int, default=None)
    parser.add_argument(
        "--transformations",
        nargs="+",
        default=None,
        help="Transformation labels to include; defaults to all observed labels.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    started_at = time.perf_counter()
    try:
        image_inventory = available_images(DATASET_ROOT)
        total_images_available = sum(
            len(images)
            for groups in image_inventory.values()
            for images in groups.values()
        )
        if db.query(TileEmbedding).count() == 0:
            raise RuntimeError(
                "No stored embeddings found; refusing to invoke search fallback because evaluation is read-only."
            )

        query_paths = select_query_paths(
            image_inventory,
            args.sample_per_tile,
            args.max_queries,
            args.transformations,
        )
        records: List[Dict[str, Any]] = []

        for image_path in query_paths:
            folder_name = image_path.parent.name
            ground_truth_sku = infer_folder_sku(folder_name)
            if not ground_truth_sku:
                continue
            records.append(evaluate_single_query(db, image_path, ground_truth_sku))

        summary = summarize_records(records)
        by_transformation = summarize_by_transformation(records)
        queries_per_transformation: Dict[str, int] = defaultdict(int)
        tiles_per_transformation: Dict[str, set[str]] = defaultdict(set)
        for record in records:
            queries_per_transformation[record["transformation"]] += 1
            tiles_per_transformation[record["transformation"]].add(record["tile_folder"])
        metadata = {
            "unique_tiles_evaluated": len({record["tile_folder"] for record in records}),
            "unique_tiles_available": len(image_inventory),
            "total_images_available": total_images_available,
            "sample_per_tile": args.sample_per_tile,
            "transformations_requested": args.transformations or sorted({
                transformation
                for groups in image_inventory.values()
                for transformation in groups
            }),
            "queries_per_transformation": dict(sorted(queries_per_transformation.items())),
            "tiles_per_transformation": {
                transformation: len(tile_folders)
                for transformation, tile_folders in sorted(tiles_per_transformation.items())
            },
            "runtime_seconds": time.perf_counter() - started_at,
        }

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        csv_path = REPORT_DIR / f"baseline_eval_{timestamp}.csv"
        md_path = REPORT_DIR / f"baseline_eval_{timestamp}.md"

        write_csv(csv_path, records)
        write_markdown(md_path, records, summary, by_transformation, metadata)

        print(f"Unique tiles evaluated: {metadata['unique_tiles_evaluated']}")
        print(f"Unique tiles available: {metadata['unique_tiles_available']}")
        print(f"Total images available: {metadata['total_images_available']}")
        print(f"Queries evaluated: {summary['queries']}")
        print(f"Queries per transformation: {metadata['queries_per_transformation']}")
        print(f"Top-1 accuracy: {summary['top1_accuracy'] * 100:.2f}%")
        print(f"Top-3 accuracy: {summary['top3_accuracy'] * 100:.2f}%")
        print(f"Top-5 accuracy: {summary['top5_accuracy'] * 100:.2f}%")
        print(f"Recall@1: {summary['recall_at_1'] * 100:.2f}%")
        print(f"Recall@3: {summary['recall_at_3'] * 100:.2f}%")
        print(f"Recall@5: {summary['recall_at_5'] * 100:.2f}%")
        print(f"Average latency: {summary['average_latency_ms']:.2f} ms")
        print(f"Median latency: {summary['median_latency_ms']:.2f} ms")
        print(f"P95 latency: {summary['p95_latency_ms']:.2f} ms")
        print(f"Failed searches: {summary['failed_searches']} ({summary['failed_percentage']:.2f}%)")
        print(f"Low-confidence searches: {summary['low_confidence_searches']} ({summary['low_confidence_percentage']:.2f}%)")
        print(f"Average top-1 similarity: {summary['average_top1_similarity']:.4f}")
        print(f"Median top-1 similarity: {summary['median_top1_similarity']:.4f}")
        print(f"Runtime: {metadata['runtime_seconds']:.2f} seconds")
        print(f"CSV report: {csv_path}")
        print(f"Markdown report: {md_path}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
