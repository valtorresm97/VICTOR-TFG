from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _normalize_diagnosis(text: str) -> str:
    pattern = re.compile(r"\| Diagnostico \| `(\{.*?\})` \|")

    def repl(match: re.Match[str]) -> str:
        raw = match.group(1)
        try:
            data = ast.literal_eval(raw)
        except Exception:
            return match.group(0)
        state = data.get("state", "n/a") if isinstance(data, dict) else "n/a"
        reasons = data.get("reasons", []) if isinstance(data, dict) else []
        if reasons:
            return f"| Diagnostico | `{state}` - {', '.join(map(str, reasons))} |"
        return f"| Diagnostico | `{state}` |"

    return pattern.sub(repl, text)


def fix_markdown_file(path: Path, docs_dir: Path, figures_dir: Path) -> bool:
    original = path.read_text(encoding="utf-8", errors="replace")
    text = original

    # Remove local absolute paths generated on Windows.
    text = text.replace("\\", "/")
    text = re.sub(
        r"[A-Za-z]:/Users/[^`\n]*/VICTOR-TFG/captures/capturas finales/",
        "captures/capturas finales/",
        text,
    )
    text = re.sub(
        r"[A-Za-z]:/Users/[^`\n]*/VICTOR-TFG/captures/capturas finales",
        "captures/capturas finales",
        text,
    )

    # Convert repository-root figure paths into paths relative to docs_dir.
    repo_fig_prefix = "docs/validacion_tfg/figures/capturas_finales_s01_20260528_matplotlib"
    rel_fig_prefix = "../figures/capturas_finales_s01_20260528_matplotlib"
    text = text.replace(repo_fig_prefix, rel_fig_prefix)

    # Convert paths accidentally prefixed from the repository root.
    text = text.replace(
        "../docs/validacion_tfg/figures/capturas_finales_s01_20260528_matplotlib",
        rel_fig_prefix,
    )

    text = _normalize_diagnosis(text)

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix portable Markdown links for final capture docs.")
    parser.add_argument(
        "--docs-dir",
        default="docs/validacion_tfg/capturas_finales_s01_20260528_matplotlib",
        help="Directory containing generated per-capture Markdown files.",
    )
    parser.add_argument(
        "--figures-dir",
        default="docs/validacion_tfg/figures/capturas_finales_s01_20260528_matplotlib",
    )
    args = parser.parse_args()

    docs_dir = PROJECT_ROOT / args.docs_dir
    figures_dir = PROJECT_ROOT / args.figures_dir
    if not docs_dir.exists():
        raise SystemExit(f"Docs directory not found: {docs_dir}")

    changed = 0
    for md in sorted(docs_dir.glob("*.md")):
        if fix_markdown_file(md, docs_dir, figures_dir):
            changed += 1
            print(f"fixed: {md}")

    print(f"[fix-links] changed={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
