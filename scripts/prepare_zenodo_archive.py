"""Build a Zenodo-ready zip of qrfl-artifacts (excludes venv, caches, secrets)."""

from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "dist"
EXCLUDE_DIR_NAMES = {
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "dist",
}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}
EXCLUDE_NAME_FRAGMENTS = {"priv_sk", ".env"}


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDE_DIR_NAMES:
        return True
    if path.suffix in EXCLUDE_SUFFIXES:
        return True
    name = path.name.lower()
    if any(frag in name for frag in EXCLUDE_NAME_FRAGMENTS):
        # Keep Fabric crypto material structure but skip private keys in public Zenodo dump
        if "priv_sk" in name or name.endswith(".env"):
            return True
    return False


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    zip_path = OUT_DIR / f"qrfl-artifacts-zenodo-{stamp}.zip"
    count = 0
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if should_skip(path.relative_to(ROOT)):
                continue
            arcname = Path("qrfl-artifacts") / path.relative_to(ROOT)
            zf.write(path, arcname.as_posix())
            count += 1
        readme = (
            "QRFL artifacts Zenodo package\n"
            f"Built: {stamp} UTC\n"
            "Source: https://github.com/abhishekeb211/qrfl-artifacts\n"
            "See REPRODUCIBILITY.md for run instructions.\n"
            "Private Fabric keystore files (priv_sk) are excluded; regenerate with blockchain/scripts/generate_crypto.*\n"
        )
        zf.writestr("qrfl-artifacts/ZENODO_README.txt", readme)
    print(f"Wrote {zip_path} ({count} files)")


if __name__ == "__main__":
    main()
