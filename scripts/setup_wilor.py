"""One-time WiLoR setup on the GPU laptop: python scripts/setup_wilor.py
Builds a separate environment (WiLoR needs older torch and numpy than the team's), outside the repo,
and fetches the weights from the official WiLoR sources. MANO_RIGHT.pkl is not fetched: its licence
needs your own registration at https://mano.is.tue.mpg.de. Then run the job with the printed python."""
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = Path.home() / ".egovision" / "gpu-venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
WEIGHTS = ROOT / "models" / "wilor" / "pretrained_models"
WILOR_MINI = "git+https://github.com/warmshao/WiLoR-mini@ebec42f94c389070cdd7dda6fd1bf0b4a659c960"
CHUMPY = "chumpy @ git+https://github.com/mattloper/chumpy"
FILES = {
    "wilor_final.ckpt": "https://huggingface.co/spaces/rolpotamias/WiLoR/resolve/main/pretrained_models/wilor_final.ckpt",
    "mano_mean_params.npz": "https://raw.githubusercontent.com/rolpotamias/WiLoR/fcb911312a38fa8badd30d9656a167485d61b8f9/mano_data/mano_mean_params.npz",
}


def pip(*args: str) -> None:
    subprocess.run([str(PY), "-m", "pip", "install", "-q", *args], check=True)


def main() -> None:
    if not PY.exists():
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    pip("torch==2.5.1", "torchvision==0.20.1", "--index-url", "https://download.pytorch.org/whl/cu121")
    pip("numpy==1.23.5", "opencv-python<4.10", "smplx==0.1.28", "timm", "einops", "roma", "scipy", "scikit-image", "tqdm")
    pip("setuptools<70", "wheel")
    pip("--no-build-isolation", CHUMPY)
    pip("--no-deps", WILOR_MINI)
    pip("--no-deps", "-e", str(ROOT))
    WEIGHTS.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        if not (WEIGHTS / name).exists():
            print(f"downloading {name}")
            urllib.request.urlretrieve(url, WEIGHTS / name)
    subprocess.run([str(PY), "-c", "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"],
                   check=True)
    subprocess.run([str(PY), "-c", "from wilor_mini.models.wilor import WiLor; print('WiLoR imports OK')"], check=True)
    if not (WEIGHTS / "MANO_RIGHT.pkl").exists():
        print(f"Still needed: copy your registered MANO_RIGHT.pkl to {WEIGHTS}")
    print(f"Run: {PY} -m egovision.hands.wilor --clip <clip>")


if __name__ == "__main__":
    main()
