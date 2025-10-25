# VMC Renamer (GameCube) — Memcard Pro GC ⇆ GCMCE / FlipperMCE

Convert Virtual Memory Card (VMC) directory/file names **in place** or **to another SD card** between two hard GameCube memory‑card emulators:

- **MCGCP layout**  
  `{sd-root}/MemoryCards/{GAMEID}0100/{GAMEID}0100-1.raw`  
  Example: `MemoryCards/GAFE0100/GAFE0100-1.raw`

- **GCMCE layout**  
  `{sd-root}/MemoryCards/GC/DL-DOL-{GAMEID}-{REGION3}/DL-DOL-{GAMEID}-{REGION3}-1.raw`  
  Example: `MemoryCards/GC/DL-DOL-GAFE-USA/DL-DOL-GAFE-USA-1.raw`

This tool renames/copies only the **slot `-1.raw`** as present in the examples. All paths and examples are anonymized for public release.

For reference and device documentation:

- **GCMCE (FlipperMCE project)** — [https://flippermce.github.io/gcmce/](https://flippermce.github.io/gcmce/)
- **Memcard Pro GC (8BitMods)** — [https://www.8bitmods.wiki/memcard-pro-gc](https://www.8bitmods.wiki/memcard-pro-gc)

## Motivation

While the [Memcard Pro GC](https://www.8bitmods.wiki/memcard-pro-gc) is a capable and well-engineered product, it remains a closed-source design.
This project was created out of appreciation for its functionality — but also from a desire to support **open-source alternatives** such as the [GCMCE](https://flippermce.github.io/gcmce/) by the FlipperMCE community.


---

## Features

- Convert **MCGCP → GCMCE** and **GCMCE → MCGCP**
- **In‑place move/rename** or **copy to a different SD root**
- Optional **backup** of the source `MemoryCards/` tree before changes
- **Dry‑run** mode prints a full plan (no changes)
- **Force** overwrite handling for collisions
- Region code mapping (`E→USA`, `J→JPN`, `P→EUR`, etc.) with optional overrides via JSON

Minimal dependencies: **standard library only** 

---

## Quick start

```bash
# Linux, Python 3.8+
python vmc_renamer.py --help
```

**Dry‑run (plan only), convert MCGCP → GCMCE in place:**
```bash
python vmc_renamer.py --sd-root /mnt/SD --rename-to-gcmce --dry-run --verbose
```

**Actually convert MCGCP → GCMCE in place (moves/renames):**
```bash
python vmc_renamer.py --sd-root /mnt/SD --rename-to-gcmce --force
```

**Copy from one SD to another (no changes to source):**
```bash
python vmc_renamer.py \
  --sd-root /media/sourceSD \
  --output-sd-root /media/targetSD \
  --rename-to-mcgcp \
  --force --verbose
```

**Create a backup first:**
```bash
python vmc_renamer.py \
  --sd-root /media/MCGCP \
  --rename-to-gcmce \
  --backup-dir /tmp/vmc_backup \
  --force
```

**Override region mapping (optional):**
```bash
cat > region_map.json <<'JSON'
{
  "letter_to_region3": { "U": "USA" },
  "region3_to_letter": { "USA": "E", "AUS": "P" }
}
JSON

python vmc_renamer.py --sd-root /media/GCMCE --rename-to-mcgcp \
  --region-map-json ./region_map.json --dry-run
```

---

## How it works (mapping rules)

- **MCGCP → GCMCE**
  - Parse `{GAMEID}` from `MemoryCards/{GAMEID}0100/`.
  - Derive `{REGION3}` by mapping the **4th character** of `{GAMEID}` (e.g., `GAFE → E → USA`).
  - Create: `MemoryCards/GC/DL-DOL-{GAMEID}-{REGION3}/DL-DOL-{GAMEID}-{REGION3}-1.raw`.

- **GCMCE → MCGCP**
  - Parse `{GAMEID}` and `{REGION3}` from `MemoryCards/GC/DL-DOL-{GAMEID}-{REGION3}/`.
  - Trust `{GAMEID}` as authoritative and create `{GAMEID}0100/{GAMEID}0100-1.raw`.

> Note: Only `*-1.raw` is processed. If you need multi‑slot support, open an issue or PR.

---

## Safety & idempotence

- **No deletes of source files** in copy mode. In move mode, source dirs are removed *only if empty*.
- Use `--dry-run` to preview all operations before changing anything.
- Use `--force` to overwrite existing destinations. Without it, collisions abort the run.

---

## CLI reference

```text
--sd-root PATH            Path to SD root (must contain MemoryCards/)
--rename-to-gcmce         Convert MCGCP → GCMCE
--rename-to-mcgcp         Convert GCMCE → MCGCP
--output-sd-root PATH     If set, write to this root (copy mode). Omit for in‑place (move).
--backup-dir PATH         If set, copy {sd-root}/MemoryCards to this path first.
--region-map-json PATH    JSON overrides for region mappings.
--force                   Overwrite destination files/dirs on collision.
--dry-run                 Plan only; do not modify filesystem.
--verbose                 Extra logging.
```

---

## Acknowledgments

Thanks to the broader GC tooling community and authors of the MCGCP/GCMCE devices for prior art and documentation. All trademarks are property of their respective owners.

References:
- [FlipperMCE GCMCE documentation](https://flippermce.github.io/gcmce/)
- [8BitMods Memcard Pro GC documentation](https://www.8bitmods.wiki/memcard-pro-gc)

