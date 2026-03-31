from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image


IMAGE_EXTS = {".jpg", ".jpeg", ".bmp", ".gif", ".png", ".webp", ".tif", ".tiff"}
JPEG_EXTS = {".jpg", ".jpeg"}


@dataclass
class DuplicateGroup:
    digest: str
    files: list[Path]
    size_each: int

    @property
    def redundant_bytes(self) -> int:
        return self.size_each * (len(self.files) - 1)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def enumerate_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file()]


def analyze_tree(root: Path) -> dict:
    files = enumerate_files(root)
    ext_counter = Counter()
    ext_bytes: Counter[str] = Counter()
    for path in files:
        ext = path.suffix.lower()
        ext_counter[ext] += 1
        ext_bytes[ext] += path.stat().st_size

    image_files = [p for p in files if p.suffix.lower() in IMAGE_EXTS]
    top_files = sorted(files, key=lambda p: p.stat().st_size, reverse=True)[:25]

    return {
        "root": str(root),
        "files_total": len(files),
        "images_total": len(image_files),
        "size_bytes_total": sum(p.stat().st_size for p in files),
        "extensions": [
            {
                "extension": ext or "<sem_ext>",
                "count": ext_counter[ext],
                "size_bytes": ext_bytes[ext],
            }
            for ext in sorted(ext_counter, key=lambda e: (-ext_counter[e], e))
        ],
        "largest_files": [
            {
                "path": str(path),
                "size_bytes": path.stat().st_size,
            }
            for path in top_files
        ],
    }


def find_exact_duplicates(root: Path) -> list[DuplicateGroup]:
    files = enumerate_files(root)
    by_size: dict[int, list[Path]] = defaultdict(list)
    for path in files:
        by_size[path.stat().st_size].append(path)

    dup_groups: list[DuplicateGroup] = []
    for size, same_size in by_size.items():
        if len(same_size) < 2:
            continue
        by_hash: dict[str, list[Path]] = defaultdict(list)
        for path in same_size:
            by_hash[sha256_file(path)].append(path)
        for digest, dupes in by_hash.items():
            if len(dupes) > 1:
                dup_groups.append(DuplicateGroup(digest=digest, files=sorted(dupes), size_each=size))

    dup_groups.sort(key=lambda g: (g.redundant_bytes, len(g.files)), reverse=True)
    return dup_groups


def choose_keeper(paths: list[Path], root: Path) -> Path:
    def score(path: Path) -> tuple[int, int, int, str]:
        rel = path.relative_to(root)
        nested_penalty = 1 if rel.parts and rel.parts[0].lower() == root.name.lower() else 0
        copy_penalty = 1 if "copia" in path.name.lower() or "copy" in path.name.lower() else 0
        return (nested_penalty, copy_penalty, len(rel.parts), str(rel).lower())

    return sorted(paths, key=score)[0]


def quarantine_duplicates(root: Path, groups: list[DuplicateGroup], quarantine_root: Path) -> dict:
    quarantine_root.mkdir(parents=True, exist_ok=True)
    moved = []
    bytes_moved = 0

    for group in groups:
        keeper = choose_keeper(group.files, root)
        for path in group.files:
            if path == keeper:
                continue
            rel = path.relative_to(root)
            target = quarantine_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(target))
            moved.append({"from": str(path), "to": str(target), "keeper": str(keeper)})
            bytes_moved += group.size_each

    return {"files_moved": len(moved), "bytes_moved": bytes_moved, "items": moved}


def optimize_jpegs(root: Path, min_size_kb: int = 150) -> dict:
    jpeg_files = [
        p
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in JPEG_EXTS and p.stat().st_size >= min_size_kb * 1024
    ]

    optimized = 0
    bytes_before = 0
    bytes_after = 0
    failures = []

    for path in jpeg_files:
        original_size = path.stat().st_size
        bytes_before += original_size

        try:
            with Image.open(path) as img:
                img.load()
                params = {
                    "format": "JPEG",
                    "optimize": True,
                    "progressive": True,
                    "quality": "keep",
                }
                if "exif" in img.info:
                    params["exif"] = img.info["exif"]
                if "icc_profile" in img.info:
                    params["icc_profile"] = img.info["icc_profile"]

                with NamedTemporaryFile(delete=False, suffix=path.suffix) as tmp:
                    tmp_path = Path(tmp.name)

                try:
                    img.save(tmp_path, **params)
                    new_size = tmp_path.stat().st_size
                    if new_size < original_size:
                        shutil.move(str(tmp_path), str(path))
                        optimized += 1
                        bytes_after += new_size
                    else:
                        bytes_after += original_size
                        tmp_path.unlink(missing_ok=True)
                except Exception:
                    tmp_path.unlink(missing_ok=True)
                    raise
        except Exception as exc:
            failures.append({"path": str(path), "error": str(exc)})
            bytes_after += original_size

    return {
        "jpeg_candidates": len(jpeg_files),
        "optimized_files": optimized,
        "bytes_before": bytes_before,
        "bytes_after": bytes_after,
        "bytes_saved": max(bytes_before - bytes_after, 0),
        "failures": failures[:100],
    }


def write_report(report_path: Path, payload: dict) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--quarantine", type=Path)
    parser.add_argument("--dedupe", action="store_true")
    parser.add_argument("--optimize-jpegs", action="store_true")
    parser.add_argument("--jpeg-min-kb", type=int, default=150)
    args = parser.parse_args()

    root = args.root
    if not root.exists():
        print(f"Root not found: {root}", file=sys.stderr)
        return 2

    payload: dict = {
        "generated_at": datetime.now().isoformat(),
        "root": str(root),
        "analysis": analyze_tree(root),
    }

    duplicates = find_exact_duplicates(root)
    payload["duplicates"] = {
        "groups": len(duplicates),
        "redundant_bytes": sum(g.redundant_bytes for g in duplicates),
        "top_groups": [
            {
                "digest": g.digest,
                "size_each": g.size_each,
                "files": [str(p) for p in g.files[:10]],
                "count": len(g.files),
            }
            for g in duplicates[:50]
        ],
    }

    if args.dedupe:
        if not args.quarantine:
            print("--dedupe requires --quarantine", file=sys.stderr)
            return 2
        payload["dedupe_action"] = quarantine_duplicates(root, duplicates, args.quarantine)

    if args.optimize_jpegs:
        payload["jpeg_optimization"] = optimize_jpegs(root, min_size_kb=args.jpeg_min_kb)

    write_report(args.report, payload)
    print(str(args.report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
