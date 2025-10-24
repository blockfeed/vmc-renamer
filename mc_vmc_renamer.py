#!/usr/bin/env python3
"""
VMC Renamer — convert GameCube memory card emulator layouts (MCGCP <-> GCMCE)
Minimal dependencies (stdlib only).

MCGCP layout:
  {sd-root}/MemoryCards/{GAMEID}0100/{GAMEID}0100-1.raw
  e.g., MemoryCards/GAFE0100/GAFE0100-1.raw

GCMCE layout:
  {sd-root}/MemoryCards/GC/DL-DOL-{GAMEID}-{REGION3}/DL-DOL-{GAMEID}-{REGION3}-1.raw
  e.g., MemoryCards/GC/DL-DOL-GAFE-USA/DL-DOL-GAFE-USA-1.raw

Features:
- --rename-to-gcmce OR --rename-to-mcgcp (mutually exclusive)
- In-place (move) or to a different --output-sd-root (copy)
- Optional --backup-dir (copies {sd-root}/MemoryCards there first)
- --dry-run, --force, --verbose
- Optional --region-map-json to override region mappings

Notes:
- Only the slot “-1.raw” is handled (matches provided examples).
- Source directories are removed if emptied after moves.
- Collisions require --force to overwrite.
- All paths anonymized; no user-specific names.

License: GPL-3.0-or-later
"""

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

RE_MCGCP_DIR = re.compile(r"^(?P<gameid>[A-Z0-9]{4})0100$")
RE_GCMCE_DIR = re.compile(r"^DL-DOL-(?P<gameid>[A-Z0-9]{4})-(?P<region3>[A-Z]{3})$")

# Region mapping defaults (override with --region-map-json)
DEFAULT_REGION3_FROM_LETTER = {
    "E": "USA",
    "J": "JPN",
    "P": "EUR",  # PAL
    "K": "KOR",
    "D": "GER",
    "F": "FRA",
    "I": "ITA",
    "S": "ESP",
    "X": "OTH",
    "Y": "OTH",
    "Z": "OTH",
}
DEFAULT_LETTER_FROM_REGION3 = {
    "USA": "E",
    "JPN": "J",
    "EUR": "P",
    "KOR": "K",
    "GER": "D",
    "FRA": "F",
    "ITA": "I",
    "ESP": "S",
    "OTH": "X",
}

@dataclass
class PlanItem:
    src_dir: Path
    src_file: Path
    dst_dir: Path
    dst_file: Path
    action: str  # "move" or "copy"
    reason: str

def log(msg: str, verbose: bool) -> None:
    if verbose:
        print(msg)

def load_region_map(path: Optional[Path]) -> Tuple[Dict[str, str], Dict[str, str]]:
    if not path:
        return DEFAULT_REGION3_FROM_LETTER.copy(), DEFAULT_LETTER_FROM_REGION3.copy()
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    l2r = DEFAULT_REGION3_FROM_LETTER.copy()
    r2l = DEFAULT_LETTER_FROM_REGION3.copy()
    for k, v in (data.get("letter_to_region3") or {}).items():
        l2r[k.upper()] = v.upper()
    for k, v in (data.get("region3_to_letter") or {}).items():
        r2l[k.upper()] = v.upper()
    return l2r, r2l

def scan_mcgcp(memorycards_dir: Path) -> List[Tuple[Path, Path, str]]:
    """Return (dir, file, gameid) for MCGCP entries."""
    results: List[Tuple[Path, Path, str]] = []
    if not memorycards_dir.exists():
        return results
    for entry in memorycards_dir.iterdir():
        if not entry.is_dir():
            continue
        m = RE_MCGCP_DIR.match(entry.name)
        if not m:
            continue
        gameid = m.group("gameid")
        raw = entry / f"{entry.name}-1.raw"
        if raw.exists():
            results.append((entry, raw, gameid))
    return results

def scan_gcmce(gc_dir: Path) -> List[Tuple[Path, Path, str, str]]:
    """Return (dir, file, gameid, region3) for GCMCE entries."""
    results: List[Tuple[Path, Path, str, str]] = []
    if not gc_dir.exists():
        return results
    for entry in gc_dir.iterdir():
        if not entry.is_dir():
            continue
        m = RE_GCMCE_DIR.match(entry.name)
        if not m:
            continue
        gameid = m.group("gameid")
        region3 = m.group("region3")
        raw = entry / f"{entry.name}-1.raw"
        if raw.exists():
            results.append((entry, raw, gameid, region3))
    return results

def plan_mcgcp_to_gcmce(sd_root: Path, out_root: Path, l2r: Dict[str, str], copy_mode: bool) -> List[PlanItem]:
    src_root = sd_root / "MemoryCards"
    dst_root = out_root / "MemoryCards" / "GC"
    plan: List[PlanItem] = []
    for src_dir, src_file, gameid in scan_mcgcp(src_root):
        region_letter = gameid[-1]  # 4th char
        region3 = l2r.get(region_letter.upper(), "OTH")
        dst_dir_name = f"DL-DOL-{gameid}-{region3}"
        dst_dir = dst_root / dst_dir_name
        dst_file = dst_dir / f"{dst_dir_name}-1.raw"
        plan.append(
            PlanItem(
                src_dir=src_dir,
                src_file=src_file,
                dst_dir=dst_dir,
                dst_file=dst_file,
                action="copy" if copy_mode else "move",
                reason=f"MCGCP→GCMCE {gameid} -> {dst_dir_name}",
            )
        )
    return plan

def plan_gcmce_to_mcgcp(sd_root: Path, out_root: Path, r2l: Dict[str, str], copy_mode: bool) -> List[PlanItem]:
    src_root = sd_root / "MemoryCards" / "GC"
    dst_root = out_root / "MemoryCards"
    plan: List[PlanItem] = []
    for src_dir, src_file, gameid, region3 in scan_gcmce(src_root):
        # Trust GAMEID as-is; MCGCP just uses {GAMEID}0100
        mcgcp_dirname = f"{gameid}0100"
        dst_dir = dst_root / mcgcp_dirname
        dst_file = dst_dir / f"{mcgcp_dirname}-1.raw"
        plan.append(
            PlanItem(
                src_dir=src_dir,
                src_file=src_file,
                dst_dir=dst_dir,
                dst_file=dst_file,
                action="copy" if copy_mode else "move",
                reason=f"GCMCE→MCGCP DL-DOL-{gameid}-{region3} -> {mcgcp_dirname}",
            )
        )
    return plan

def print_plan(plan: List[PlanItem]) -> None:
    print("Planned operations:")
    for p in plan:
        print(f"  {p.action.upper()}: {p.src_file}  ->  {p.dst_file}   ({p.reason})")
    print(f"Total items: {len(plan)}")

def safe_copy(src: Path, dst: Path, overwrite: bool) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if overwrite:
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        else:
            raise FileExistsError(f"Destination exists: {dst}")
    shutil.copy2(src, dst)

def safe_move(src: Path, dst: Path, overwrite: bool) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if overwrite:
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        else:
            raise FileExistsError(f"Destination exists: {dst}")
    src.replace(dst)

def execute_plan(plan: List[PlanItem], overwrite: bool, dry_run: bool, verbose: bool) -> None:
    for p in plan:
        if dry_run:
            print(f"[DRY-RUN] {p.action.upper()} {p.src_file} -> {p.dst_file}")
            continue
        if p.action == "move":
            safe_move(p.src_file, p.dst_file, overwrite=overwrite)
            # remove empty source dir
            try:
                next(p.src_dir.iterdir())
            except StopIteration:
                try:
                    p.src_dir.rmdir()
                except OSError:
                    pass
        else:
            safe_copy(p.src_file, p.dst_file, overwrite=overwrite)
        log(f"OK: {p.action} {p.src_file} -> {p.dst_file}", verbose)

def do_backup(sd_root: Path, backup_dir: Path, overwrite: bool, dry_run: bool) -> None:
    src = sd_root / "MemoryCards"
    dst = backup_dir / "MemoryCards.backup"
    if dry_run:
        print(f"[DRY-RUN] Would backup {src} -> {dst}")
        return
    if dst.exists() and overwrite:
        if dst.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    print(f"Backing up {src} -> {dst}")
    shutil.copytree(src, dst)

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Convert GameCube VMC naming between MCGCP and GCMCE."
    )
    ap.add_argument("--sd-root", required=True, help="Path to SD root (containing MemoryCards/)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--rename-to-gcmce", action="store_true", help="Convert MCGCP -> GCMCE")
    mode.add_argument("--rename-to-mcgcp", action="store_true", help="Convert GCMCE -> MCGCP")
    ap.add_argument("--output-sd-root", help="If set, write to this root (copy mode). If omitted, operate in-place (move).")
    ap.add_argument("--backup-dir", help="If set, back up {sd-root}/MemoryCards to this directory first.")
    ap.add_argument("--region-map-json", help="JSON file with {letter_to_region3, region3_to_letter} overrides.")
    ap.add_argument("--force", action="store_true", help="Overwrite existing destination files/dirs.")
    ap.add_argument("--dry-run", action="store_true", help="Plan only; do not modify filesystem.")
    ap.add_argument("--verbose", action="store_true", help="Verbose output.")
    return ap.parse_args()

def main() -> int:
    args = parse_args()
    sd_root = Path(args.sd_root).resolve()
    if not (sd_root / "MemoryCards").exists():
        print(f"ERROR: {sd_root}/MemoryCards not found", file=sys.stderr)
        return 1

    out_root = Path(args.output_sd_root).resolve() if args.output_sd_root else sd_root
    copy_mode = out_root != sd_root

    region_json = Path(args.region_map_json) if args.region_map_json else None
    l2r, r2l = load_region_map(region_json)

    # Optional backup
    if args.backup_dir:
        backup_dir = Path(args.backup_dir).resolve()
        backup_dir.mkdir(parents=True, exist_ok=True)
        do_backup(sd_root, backup_dir, overwrite=args.force, dry_run=args.dry_run)

    # Build plan
    if args.rename_to_gcmce:
        plan = plan_mcgcp_to_gcmce(sd_root, out_root, l2r, copy_mode=copy_mode)
    else:
        plan = plan_gcmce_to_mcgcp(sd_root, out_root, r2l, copy_mode=copy_mode)

    if not plan:
        print("No convertible entries found. Check source layout and flags.")
        return 0

    print_plan(plan)
    if args.verbose:
        print(f"Execute: overwrite={args.force} dry_run={args.dry_run} mode={'COPY' if copy_mode else 'MOVE'}")

    execute_plan(plan, overwrite=args.force, dry_run=args.dry_run, verbose=args.verbose)
    print("Done.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

