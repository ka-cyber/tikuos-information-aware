from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
# The original archives are not redistributed; this records their content hashes
# when the artifact is generated. Replace values only when changing the source set.
paths={
"tikuOS-main.zip":ROOT.parent/"tikuOS-main.zip",
"pir_framework.zip":ROOT.parent/"pir_framework.zip",
"CardioFusion-AI-main.zip":ROOT.parent/"CardioFusion-AI-main.zip",
"apc-rlnc-main (2).zip":ROOT.parent/"apc-rlnc-main (2).zip",
}
out={}
for name,p in paths.items():
    if p.exists():
        h=hashlib.sha256();
        with p.open("rb") as f:
            for chunk in iter(lambda:f.read(1<<20),b""): h.update(chunk)
        out[name]=h.hexdigest()
Path(ROOT/"docs"/"input-provenance.json").write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps(out,indent=2))
