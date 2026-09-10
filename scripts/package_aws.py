"""Build a locked Linux ARM64 archive shared by Lambda and AgentCore."""

import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "work" / "aws-package"
TARGET.mkdir(parents=True, exist_ok=True)
requirements = ROOT / "work" / "aws-requirements.txt"
subprocess.run(
    ["uv", "export", "--frozen", "--no-dev", "--no-emit-project", "--output-file", str(requirements)],
    cwd=ROOT,
    check=True,
    stdout=subprocess.DEVNULL,
)
subprocess.run(
    [
        "uv",
        "pip",
        "install",
        "--python-platform",
        "aarch64-manylinux2014",
        "--python-version",
        "3.13",
        "--only-binary=:all:",
        "--target",
        str(TARGET),
        "-r",
        str(requirements),
    ],
    check=True,
)
archive = ROOT / "work" / "society-relay-aws.zip"
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as out:
    for path in TARGET.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            out.write(path, path.relative_to(TARGET))
    for path in (ROOT / "relay").rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            out.write(path, path.relative_to(ROOT))
    out.write(ROOT / "aws_main.py", "aws_main.py")
print(f"Created {archive.name}: {archive.stat().st_size} bytes")
