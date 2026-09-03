"""Run alzheimers-gene-network-biomarkers' own real_run pipeline on real STRING v12 data.

Uses the repository's committed pipeline unchanged (data_pipeline.real_run.run), on the
real endpoints its README and docs/data_sources.md specify:
  - protein.links.v12.0  (9606, confidence >= 700)
  - protein.info.v12.0   (STRING protein id -> gene symbol)

Nothing is synthesised: the pipeline itself aborts if fewer than 5 AD seed genes survive
ID translation, so a mis-mapped run fails loudly instead of reporting a meaningless number.

Run: modal run train_alz.py
"""
import modal

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "numpy==1.26.4", "scipy==1.14.1", "scikit-learn==1.5.2",
        "networkx==3.3", "pandas==2.2.3", "pyarrow==17.0.0", "requests==2.32.3",
    )
)

app = modal.App("alz-gene-network-real-run", image=image)
vol = modal.Volume.from_name("alz-artifacts", create_if_missing=True)

REPO = "https://github.com/Anamitra-Sarkar/alzheimers-gene-network-biomarkers.git"
LINKS = "https://stringdb-downloads.org/download/protein.links.v12.0/9606.protein.links.v12.0.txt.gz"
INFO = "https://stringdb-downloads.org/download/protein.info.v12.0/9606.protein.info.v12.0.txt.gz"


@app.function(timeout=7200, cpu=8.0, memory=32768, volumes={"/art": vol})
def train() -> dict:
    import json
    import subprocess
    import sys
    from pathlib import Path
    import requests

    subprocess.run(["git", "clone", "--depth", "1", REPO, "/repo"], check=True)
    sys.path.insert(0, "/repo")

    data = Path("/data"); data.mkdir(exist_ok=True)
    for url, name in ((LINKS, "links.txt.gz"), (INFO, "info.txt.gz")):
        dest = data / name
        print(f"downloading {url}", flush=True)
        with requests.get(url, stream=True, timeout=1800) as r:
            r.raise_for_status()
            with dest.open("wb") as fh:
                for chunk in r.iter_content(1 << 20):
                    fh.write(chunk)
        print(f"  {dest} {dest.stat().st_size} bytes", flush=True)

    from data_pipeline.real_run import run

    out_dir = "/art/real-run-1"
    result = run(
        string_path=str(data / "links.txt.gz"),
        string_info_path=str(data / "info.txt.gz"),
        out_dir=out_dir,
        threshold=700,
        model_type="logistic",
        betweenness_k=200,
    )
    vol.commit()

    produced = sorted(p.name for p in Path(out_dir).glob("*"))
    print("ARTIFACTS:", produced, flush=True)
    print("RESULT:", json.dumps(result, indent=2, default=str)[:3000], flush=True)
    return {"result": result, "artifacts": produced}


@app.local_entrypoint()
def main():
    import json
    print(json.dumps(train.remote(), indent=2, default=str))
