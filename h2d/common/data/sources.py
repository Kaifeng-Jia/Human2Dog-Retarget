"""Dataset sources shared by the profile and candidate scripts: list files, load a clip with its object mesh
and dataset-specific extras, record data versions. Both return the same z-up ``Clip``."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from h2d.common.data.omomo_new import NAME_RE, load_clip
from h2d.common.data.omomo_objects import load_object
from h2d.common.runinfo import _git
from h2d.paths import data_path, load_config


def mesh_low(c, mesh):
    return mesh.lowest_z(c.obj_pos, c.obj_rot_xyzw)


class OmomoSource:
    name, needs, title = "omomo_new", ("hoi_retarget",), "OMOMO_new"

    def __init__(self, root: Path, args):
        self.root = root
        self.files = sorted(root.rglob("*.pt"))

    def object_of(self, f: Path) -> str | None:
        m = NAME_RE.match(f.stem)
        return m["object"] if m else None

    def load(self, f: Path):
        c = load_clip(f)
        return c, load_object(c.obj), {}

    def mesh(self, obj: str):
        return load_object(obj)

    def versions(self) -> dict:
        return {}


class ForceSource:
    name, needs, title = "force", (), "FORCE"

    def __init__(self, root: Path, args):
        from h2d.common.data import force as fo

        self.fo, self.root = fo, root
        self.ann = fo.annotations(root)
        self.files = [f for f in fo.sequences(root) if f.stem in self.ann]
        self.betas, gender = fo.load_betas(root)
        smplh_root = Path(args.smplh_root).expanduser() if args.smplh_root else data_path("smplh_models")
        self.model_path = fo.smplh_path(smplh_root, gender)
        self.model = fo.load_smplh(str(self.model_path))

    def object_of(self, f: Path) -> str | None:
        return self.ann[f.stem]["object"]

    def load(self, f: Path):
        c, ex = self.fo.load_sequence(f, self.root, self.model, self.betas)
        lc = float((ex.hand_min_dist[:, 0] < ex.contact_thr_m).mean())
        rc = float((ex.hand_min_dist[:, 1] < ex.contact_thr_m).mean())
        p10 = np.percentile(ex.hand_min_dist, 10, axis=0)
        h = ex.annotation["hands"]
        ann_p10 = p10[0] if h == "L" else p10[1] if h == "R" else float(p10.max())
        extra = {"ann_hands": ex.annotation["hands"], "ann_dir": ex.annotation["dir"],
                 "ann_weight_kg": ex.annotation["weight_kg"], "ann_success": ex.annotation["success_code"],
                 "frac_left_hand_contact": lc, "frac_right_hand_contact": rc,
                 "derived_more_touching_hand": "L" if lc > rc else "R" if rc > lc else "",
                 "hand_dist_p10_left_m": float(p10[0]), "hand_dist_p10_right_m": float(p10[1]),
                 "annotated_hand_dist_p10_m": float(ann_p10),
                 "obj_lowest_z_median_m": float(np.median(mesh_low(c, self.fo.load_force_object(str(self.root), c.obj)))),
                 "floor_raw_m": ex.floor_raw_m, "step_hz": self.fo.step_frequency_hz(c),
                 "src_frames": len(np.load(f)["smpl_trans"])}
        return c, self.fo.load_force_object(str(self.root), c.obj), extra

    def mesh(self, obj: str):
        return self.fo.load_force_object(str(self.root), obj)

    def versions(self) -> dict:
        spec = load_config("data.yaml")["force"]
        head = _git(["rev-parse", "HEAD"], self.root)
        return {"force_commit": head, "force_commit_pinned": spec.get("commit"),
                "force_commit_match": head == spec.get("commit"),
                "smplh_file": self.model_path.name, "smplh_bytes": self.model_path.stat().st_size,
                "smplh_sha256_16": hashlib.sha256(self.model_path.read_bytes()).hexdigest()[:16],
                "smplh_joints": self.model.n_joints, "smplh_vertices": int(len(self.model.v_template)),
                "src_fps_assumed": self.fo.SRC_FPS}


SOURCES = {"omomo_new": OmomoSource, "force": ForceSource}
