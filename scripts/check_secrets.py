from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_NAMES = {
    "DEEPSEEK_API_KEY",
    "MYSQL_PASSWORD",
    "JWT_SECRET",
    "INITIAL_ADMIN_PASSWORD",
}
GENERIC_KEY = re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}")


def local_secret_values() -> set[str]:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return set()
    values: set[str] = set()
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        name, value = line.split("=", 1)
        if name.strip() in SECRET_NAMES and len(value.strip()) >= 8:
            values.add(value.strip())
    return values


def publishable_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / item.decode() for item in result.stdout.split(b"\0") if item]


def main() -> None:
    local_values = local_secret_values()
    findings: list[tuple[str, str]] = []
    checked = 0
    for path in publishable_files():
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        checked += 1
        relative = str(path.relative_to(ROOT))
        if GENERIC_KEY.search(text):
            findings.append((relative, "generic-api-key-pattern"))
        if any(value in text for value in local_values):
            findings.append((relative, "matches-local-secret"))

    if findings:
        for filename, rule in sorted(set(findings)):
            print(f"potential_secret file={filename} rule={rule}")
        raise SystemExit(1)
    print(f"secret_scan=ok files={checked}")


if __name__ == "__main__":
    main()
