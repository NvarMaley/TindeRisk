"""Create the public Pages artifact from an explicit source allowlist."""
from pathlib import Path
from shutil import copyfile
import sys

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent.parent / "src"
FILES = {
    HERE / "pages/index.html": "index.html",
    HERE / "pages/launch.js": "launch.js",
    HERE / "model.py": "model.py",
    HERE / "streamlit_app.py": "streamlit_app.py",
    SOURCE / "riskmatch/__init__.py": "riskmatch/__init__.py",
    SOURCE / "riskmatch/optimization/__init__.py": "riskmatch/optimization/__init__.py",
    SOURCE / "riskmatch/optimization/mean_variance.py": "riskmatch/optimization/mean_variance.py",
}


def package(output):
    for source, relative in FILES.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        copyfile(source, target)
    (output / ".nojekyll").touch()


if __name__ == "__main__":
    package(Path(sys.argv[1]))
