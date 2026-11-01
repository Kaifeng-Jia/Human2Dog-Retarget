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

## 2. This package (with X-Morph runtime deps and the full-optimization solver)

```bash
cd Human2Dog-Retarget
pip install -e ".[dev,xmorph,fullopt]" -c constraints.txt
python -c "import mujoco; print(mujoco.__version__)"   # must print 3.11.0
python -c "import cvxpy; print(cvxpy.__version__, 'CLARABEL' in cvxpy.installed_solvers())"   # 1.7.5 True
```

The full-optimization line solves its per-frame QPs with cvxpy and Clarabel. cvxpy is pinned to **1.7.5**, the newest
release for Python 3.10 with numpy 1.x (1.8 needs Python 3.11 and numpy 2). Its videos need `ffmpeg` with libx264
(`sudo apt install ffmpeg`) and offscreen OpenGL (`MUJOCO_GL=egl` on this machine).

MuJoCo is pinned to **3.11.0**: it is the newest release that `pytorch-kinematics 0.10.0` (used inside
X-Morph inference) can parse; 3.12 and later break X-Morph's FK loader. If another version is installed,
`pip install mujoco==3.11.0`.

## 3. Third-party repositories at pinned commits (`configs/external.yaml`)

**X-Morph** is used read-only through `PYTHONPATH`; it is never pip-installed, so an existing checkout is
not modified.

```bash
# reuse an existing checkout if `git -C <path> rev-parse HEAD` equals the pinned commit
export XMORPH_ROOT=/home/kevin/CS6758Project/morph
# otherwise:
#   git clone https://github.com/Maker-Rat/morph external/morph
#   git -C external/morph checkout a9f4a7713ac9e593a1e40f77851ba5ba44c92d78
#   export XMORPH_ROOT=$PWD/external/morph
```

**GMR** is cloned into `external/GMR` and installed editable (it pulls `mink`, `smplx`, `qpsolvers`,
`opencv-python`). Always pass `-c constraints.txt`: without it pip installs opencv-python 5.x, which
upgrades numpy to 2.x and breaks this project.

```bash
git clone https://github.com/YanjieZe/GMR external/GMR
git -C external/GMR checkout 25f56db79ac411258b377b6d4ccba0c8ff3372ac
pip install -e external/GMR -c constraints.txt
pip check                      # must report no broken requirements
export GMR_ROOT=$PWD/external/GMR
```

**HOI-Retarget** is cloned into `external/hoi-retarget` only for its 13 OMOMO object meshes
(`assets/objects/`, MIT, redistributed from InterMimic). It is not installed and none of its code runs.

```bash
git clone https://github.com/leggedrobotics/hoi-retarget external/hoi-retarget
git -C external/hoi-retarget checkout b341dadde3fc745ef5ea606eaacbde9a0cbb916f
export HOI_RETARGET_ROOT=$PWD/external/hoi-retarget
ls external/hoi-retarget/assets/objects/objects     # 13 object folders, each <name>.obj + sample_points.npy
```

## 4. Data locations (`configs/data.yaml`)

Data never enters git. Point the project at the datasets with symlinks (or the env vars below):

```bash
mkdir -p ~/CS6758Project/data
ln -s /home/kevin/holosoma/data       ~/CS6758Project/data/omomo_raw    # OMOMO_RAW_ROOT
ln -s /home/kevin/holosoma/OMOMO_new  ~/CS6758Project/data/omomo_new    # OMOMO_NEW_ROOT
# SMPL-X model files (licensed download): ~/CS6758Project/data/smplx_models  (SMPLX_MODEL_ROOT)
# SMPL-H model files (licensed, MANO "Models & Code", mano_v1_2/models/SMPLH_{male,female}.pkl):
#   ~/CS6758Project/data/smplh_models  (SMPLH_MODEL_ROOT)
```

**FORCE** (Zhang et al., 3DV 2025) is a public git repository with the data inside (~560 MB). It has no
licence file: research use only, never commit or redistribute it. Clone it at the pinned commit:

```bash
git clone https://github.com/xz6014/FORCE_dataset ~/CS6758Project/data/force          # FORCE_ROOT
git -C ~/CS6758Project/data/force checkout 695c8b8616f0915dd61658862751e40ec658b81c
```

The SMPL-H pickles store some arrays as chumpy objects; chumpy is **not** needed (it does not install with
numpy >= 1.24): `h2d/common/body/smplh.py` unpickles them without it.

Only data files are read from those folders; no code from them is used.

## 5. Running a step and sending results back

Run on a clean checkout of the commit named in the run ticket. Every script writes one self-contained
folder `outputs/<run-id>/` (`summary.json` with provenance, `report.md`, figures) and refuses to run on a
dirty tree or an unpinned X-Morph (see `docs/versioning.md`).

```bash
git status                      # must be clean
pytest -q
```

Then copy the small files to the `reports` branch (`<run-id>/`), push, and comment on the ticket
(details in `CLAUDE.md`). Large files go to Google Drive `Human2Dog/runs/<run-id>/`.
