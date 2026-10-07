"""Run the existing Boris launcher from the repository root."""
import pathlib
import runpy


if __name__ == "__main__":
    runpy.run_path(str(pathlib.Path(__file__).resolve().parent / "boris/run_boris.py"),
                   run_name="__main__")
