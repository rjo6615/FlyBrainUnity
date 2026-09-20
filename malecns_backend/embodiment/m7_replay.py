"""Offline, read-only kinematic replay of recorded M7 body/joint telemetry.

No scientific runtime is imported or initialized.  The default Tk renderer
draws recorded body position and joint-coordinate bars; optional MP4 export
uses the same recorded samples via imageio/ffmpeg.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from .m7_postrun_analysis import CANONICAL_SHA256, CHANNELS, CONDITIONS, EvidenceError, _sha


def load_replay(raw: Path, *, expected_sha256: str = CANONICAL_SHA256) -> dict[str, np.ndarray]:
    """Read a verified NPZ without pickle; never opens it in a writable mode."""
    if not raw.is_file() or _sha(raw) != expected_sha256:
        raise EvidenceError("replay raw SHA256 mismatch")
    try:
        archive = np.load(raw, allow_pickle=False)
        required = {f"{c}__{f}" for c in CONDITIONS for f in
                    ("physics_time_ms", "physics_body_position", "physics_body_orientation", "physics_joint_position")}
        if not required.issubset(archive.files): raise EvidenceError("replay arrays missing")
        arrays = {name: archive[name] for name in required}
        archive.close()
    except (OSError, ValueError, TypeError) as exc:
        raise EvidenceError(f"unsafe/unreadable replay archive: {exc}") from exc
    if any(a.dtype.hasobject or not np.all(np.isfinite(a)) for a in arrays.values()):
        raise EvidenceError("replay data must be finite numeric arrays")
    return arrays


def _frame_rgb(arrays: dict[str, np.ndarray], index: int, side_by_side: bool) -> np.ndarray:
    """Dependency-free schematic frame made solely from recorded coordinates."""
    height, width = 480, (960 if side_by_side else 480)
    frame = np.full((height, width, 3), 248, np.uint8)
    conditions = CONDITIONS if side_by_side else CONDITIONS[:1]
    idx = [c[4] for c in CHANNELS]
    for panel, condition in enumerate(conditions):
        x0 = panel * 480; pos = arrays[f"{condition}__physics_body_position"][index]
        joints = arrays[f"{condition}__physics_joint_position"][index, idx]
        cx = x0 + 240 + int(60*np.tanh(pos[0])); cy = 170-int(60*np.tanh(pos[2]))
        yy, xx = np.ogrid[:height,:width]; mask=(xx-cx)**2+(yy-cy)**2 <= 18**2; frame[mask]=[25,90,160]
        for j,value in enumerate(joints):
            y=245+j*18; length=int(70*np.tanh(value)); a,b=sorted((x0+240,x0+240+length)); frame[y:y+7,a:b+1]=[190,45,45]
        # fall threshold and rollover state are visually marked from frozen criteria.
        initial_z=arrays[f"{condition}__physics_body_position"][0,2]
        quat=arrays[f"{condition}__physics_body_orientation"][index]
        if pos[2] < .5*initial_z: frame[8:18,x0+10:x0+80]=[220,120,0]
        if 1-2*(quat[1]**2+quat[2]**2) <= 0: frame[22:32,x0+10:x0+80]=[150,40,160]
    return frame


def export_video(arrays: dict[str, np.ndarray], path: Path, *, speed: float, fps: int,
                 side_by_side: bool) -> None:
    try: import imageio.v2 as imageio
    except ImportError as exc: raise RuntimeError("video export requires imageio and an ffmpeg backend") from exc
    count=len(arrays[f"{CONDITIONS[0]}__physics_time_ms"]); stride=max(1,int(10/(fps*speed*.1)))
    with imageio.get_writer(path, fps=fps) as writer:
        for i in range(0,count,stride): writer.append_data(_frame_rgb(arrays,i,side_by_side))


def replay_gui(arrays: dict[str, np.ndarray], *, condition: str, speed: float,
               side_by_side: bool) -> None:
    import tkinter as tk
    root=tk.Tk(); root.title("M7 offline recorded-state replay")
    canvas=tk.Canvas(root,width=960 if side_by_side else 480,height=480,bg="white"); canvas.pack()
    controls=tk.Frame(root); controls.pack(fill="x"); playing={"value":True}; index={"value":0}; rate={"value":speed}
    tk.Button(controls,text="Play / Pause",command=lambda:playing.update(value=not playing["value"])).pack(side="left")
    tk.Scale(controls,from_=.1,to=8,resolution=.1,orient="horizontal",label="speed",variable=tk.DoubleVar(value=speed),command=lambda v:rate.update(value=float(v))).pack(side="left")
    label=tk.Label(controls); label.pack(side="left")
    conds=CONDITIONS if side_by_side else (condition,)
    def tick():
        if playing["value"]: index["value"]=(index["value"]+max(1,int(rate["value"]*10)))%50001
        i=index["value"]; canvas.delete("all")
        for p,c in enumerate(conds):
            x0=p*480; pos=arrays[f"{c}__physics_body_position"][i]; joints=arrays[f"{c}__physics_joint_position"][i,[x[4] for x in CHANNELS]]
            canvas.create_text(x0+240,20,text=c); canvas.create_oval(x0+220+60*np.tanh(pos[0]),130-60*np.tanh(pos[2]),x0+260+60*np.tanh(pos[0]),170-60*np.tanh(pos[2]),fill="#195aa0")
            for j,v in enumerate(joints): canvas.create_line(x0+240,225+j*20,x0+240+70*np.tanh(v),225+j*20,width=6,fill="#be2d2d")
        label.config(text=f" recorded simulation time: {arrays[f'{CONDITIONS[0]}__physics_time_ms'][i]:.1f} ms")
        root.after(33,tick)
    tick(); root.mainloop()


def main(argv: Sequence[str] | None=None) -> int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--raw",type=Path,required=True)
    p.add_argument("--condition",choices=CONDITIONS,default=CONDITIONS[0]); p.add_argument("--side-by-side",action="store_true")
    p.add_argument("--speed",type=float,default=1); p.add_argument("--export-video",type=Path); p.add_argument("--fps",type=int,default=30)
    args=p.parse_args(argv)
    if args.speed<=0 or args.fps<=0: p.error("speed and fps must be positive")
    arrays=load_replay(args.raw)
    if args.export_video: export_video(arrays,args.export_video,speed=args.speed,fps=args.fps,side_by_side=args.side_by_side)
    else: replay_gui(arrays,condition=args.condition,speed=args.speed,side_by_side=args.side_by_side)
    return 0


if __name__ == "__main__": raise SystemExit(main())
