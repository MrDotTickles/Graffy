"""Collect installed dependency license texts without copying local configuration."""
from importlib import metadata
from pathlib import Path
import json
import re
import shutil
import ssl
import sys


def collect(destination):
    destination=Path(destination)
    root=Path(__file__).resolve().parents[1]
    expected=root.resolve()/"build"/"licenses"
    if destination.resolve()!=expected or destination.is_symlink():
        raise ValueError("License staging must be the project's build/licenses directory.")
    if destination.exists():
        if any(p.is_symlink() or getattr(p,"is_junction",lambda:False)() for p in destination.rglob("*")):
            raise ValueError("Refusing to clean reparse points in license staging.")
        shutil.rmtree(destination)
    destination.mkdir(parents=True,exist_ok=True)
    distributions=[]
    for distribution in sorted(metadata.distributions(),key=lambda d:d.metadata["Name"].lower()):
        name=distribution.metadata["Name"]
        distributions.append({"name":name,"version":distribution.version})
        safe_name=re.sub(r"[^A-Za-z0-9._-]","_",name)
        for item in distribution.files or []:
            parts=item.as_posix().lower()
            if ".dist-info/" not in parts:continue
            base=Path(item).name.lower()
            if not ("/licenses/" in parts or base.startswith(("license","licence","copying","notice"))):continue
            source=Path(distribution.locate_file(item))
            if not source.is_file():continue
            target=destination/safe_name/Path(item).name
            # Retain distinct nested notices with the same basename.
            if target.exists():target=destination/safe_name/str(item).replace("/","_").replace("\\","_")
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
    python_license=Path(sys.base_prefix)/"LICENSE.txt"
    if python_license.is_file():shutil.copyfile(python_license,destination/"Python-LICENSE.txt")
    (destination/"DEPENDENCIES.json").write_text(json.dumps({"python":sys.version.split()[0],"openssl":ssl.OPENSSL_VERSION,"packages":distributions},indent=2),encoding="utf-8")
    return destination

if __name__=="__main__":collect(Path(__file__).resolve().parents[1]/"build"/"licenses")
