# Ubuntu setup (RTX 5070)

All official runs happen on the Ubuntu machine. The Mac is only used to look at results.

## 1. Environment

```bash
conda create -n h2d python=3.10 -y
conda activate h2d
```

RTX 5070 is a Blackwell GPU (sm_120). It needs a **CUDA 12.8** build of PyTorch (2.7 or newer);
older wheels fail with "no kernel image is available for execution on the device".

```bash
pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu128
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

## 2. External repositories at pinned commits

```bash
cd Human2Dog-Retarget
mkdir -p external
git clone https://github.com/Maker-Rat/morph external/morph
git -C external/morph checkout a9f4a7713ac9e593a1e40f77851ba5ba44c92d78
pip install -e external/morph
```

If you already have an X-Morph checkout, you can reuse it instead: check
`git -C <path> rev-parse HEAD` equals the commit above and set `XMORPH_ROOT=<path>`.

GMR (needed from the X-Morph prior step on; pinned `25f56db79ac411258b377b6d4ccba0c8ff3372ac`) will be
added to this page together with that step.

## 3. This package

```bash
pip install -e ".[dev]"
export XMORPH_ROOT=$PWD/external/morph
pytest -q
```

## 4. Running a step and sending results back

Run on a clean checkout of the commit named in the run ticket. Every script writes one self-contained
folder `outputs/<run-id>/` (`summary.json` with provenance, `report.md`, figures) and refuses to run on a
dirty tree or an unpinned X-Morph (see `docs/versioning.md`).

```bash
git status                      # must be clean
python scripts/common/b01_check_tool_geometry.py --run-id R001_b01
```

Then copy the small files to the `reports` branch (`R001_b01/`), push, and comment on the ticket
(details in `CLAUDE.md`). Large files go to Google Drive `Human2Dog/runs/<run-id>/`.
