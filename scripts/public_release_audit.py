"""Fail closed on private files and common credential patterns; never print matches."""
import argparse
import json
from pathlib import Path
import re
import subprocess

RULES = {
    "github-token": rb"(?<![A-Za-z0-9_])(?:gh[pousr]_[A-Za-z0-9]{36}(?![A-Za-z0-9_])|github_pat_[A-Za-z0-9_]{40,}(?![A-Za-z0-9_]))",
    "aws-access-id": rb"(?:AKIA|ASIA)[A-Z0-9]{16}",
    "service-api-key": rb"sk-(?:proj-)?[A-Za-z0-9_-]{32,}|AIza[A-Za-z0-9_-]{35}|xox[baprs]-[A-Za-z0-9-]{20,}",
    "private-key": rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----\s+[A-Za-z0-9+/=\r\n]{64,}",
    "credential-assignment": rb"(?i)(?:api_key|api_secret|access_token|client_secret|password)[\"']?\s*[=:]\s*[\"']([A-Za-z0-9_+/=-]{24,})[\"']",
}
PRIVATE_DIRS={".git", ".aws", ".ssh", ".codex", ".venv", "projects", "__pycache__", ".pytest_cache", ".tmp"}
PRIVATE_SUFFIXES={".kgraph", ".pfx", ".p12", ".p8", ".key", ".keystore", ".log", ".db", ".sqlite", ".sqlite3", ".parquet", ".docx", ".pdf"}


def inspect_bytes(data, name):
    return [{"path":name,"rule":rule} for rule,pattern in RULES.items() if re.search(pattern,data)]


def private_path(name, package=False):
    path=Path(name)
    parts={part.lower() for part in path.parts}
    if parts & PRIVATE_DIRS:return True
    if path.name.lower() in {".netrc",".npmrc",".pypirc",".git-credentials",".gitconfig","id_rsa","id_ed25519"}:return True
    if path.suffix.lower()==".env":return True
    if not package and path.suffix.lower()==".pem":return True
    if path.name.lower().startswith(".env") and path.name!=".env.example":return True
    if path.suffix.lower() in PRIVATE_SUFFIXES:return True
    if path.name.lower().startswith(("credentials", "service-account")) and path.suffix==".json":return True
    if package and path.suffix.lower() in {".csv", ".xlsx", ".xls", ".tsv"}:
        # These are public upstream demonstration files, not application user data.
        return "matplotlib/mpl-data/sample_data/" not in path.as_posix().lower()
    return False


def audit_source(root):
    paths=subprocess.check_output(["git","ls-files","-z"],cwd=root).decode().split("\0")
    findings=[]
    for name in filter(None,paths):
        if (root/name).is_symlink():
            findings.append({"path":name,"rule":"source-symlink"})
            continue
        if private_path(name):findings.append({"path":name,"rule":"private-file"})
        findings+=inspect_bytes((root/name).read_bytes(),name)
    return findings,len(list(filter(None,paths)))


def audit_package(root):
    findings=[];count=0
    for path in root.rglob("*"):
        if path.is_symlink():
            if not path.resolve().is_relative_to(root.resolve()):
                findings.append({"path":str(path.relative_to(root)),"rule":"external-symlink"})
            continue
        if not path.is_file():continue
        count+=1;name=path.relative_to(root).as_posix()
        if private_path(name,True):findings.append({"path":name,"rule":"private-file"})
        findings+=inspect_bytes(path.read_bytes(),name)
    # PyInstaller stores app strings inside compressed code, not plain files.
    from PyInstaller.archive.readers import CArchiveReader
    import types
    executables=list(root.rglob("Graffy.exe"))+[p for p in root.rglob("Graffy") if p.is_file() and p.parent.name=="MacOS"]
    def inspect_code(code,name):
        if not isinstance(code,types.CodeType):return
        if re.search(r"(?i)(?:[a-z]:[/\\]Users[/\\]|/Users/)",code.co_filename):
            findings.append({"path":name,"rule":"personal-build-path"})
        for constant in code.co_consts:
            if isinstance(constant,types.CodeType):inspect_code(constant,name)
            elif isinstance(constant,(str,bytes)):
                findings.extend(inspect_bytes(constant.encode() if isinstance(constant,str) else constant,name))
    for executable in executables:
        try:
            archive=CArchiveReader(str(executable)).open_embedded_archive("PYZ.pyz")
            for name in archive.toc:
                if name.startswith("omnigraph"):
                    inspect_code(archive.extract(name),name)
        except Exception:
            findings.append({"path":str(executable.relative_to(root)),"rule":"cannot-inspect-app-archive"})
    for required in ("LICENSE","PRIVACY.md","SECURITY.md","THIRD_PARTY_NOTICES.md","LICENSES/DEPENDENCIES.json"):
        if not any(p.as_posix().endswith(required) for p in root.rglob(Path(required).name)):
            findings.append({"path":required,"rule":"missing-distribution-notice"})
    return findings,count


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package",type=Path)
    parser.add_argument("--report",type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    findings,count=audit_package(args.package) if args.package else audit_source(root)
    result={"scope":"package" if args.package else "tracked-source","files":count,"findings":findings}
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
    raise SystemExit(1 if findings else 0)

if __name__=="__main__":main()
