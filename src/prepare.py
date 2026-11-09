"""Rebuild the download STL and the Bambu Studio project from the BumpMesh 3MF.

The BumpMesh export is a single mesh object in a plain 3MF: no plate, no settings.
- docs/cursed_benchy.stl: the same mesh as binary STL, for the download link.
- exports/cursed_benchy_plate.3mf: X2D 0.4 nozzle, stock 0.20mm Standard, Bambu PLA
  Matte on the main (left) hotend, Textured PEI. Unsliced: open it, pick the AMS slot,
  slice.

Run with --check to slice a copy in a temporary folder and print the estimate.
"""

import json
import re
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

BAMBU = Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")
PROFILES = Path("/Applications/BambuStudio.app/Contents/Resources/profiles/BBL")
PRESETS = {
    "machine": "Bambu Lab X2D 0.4 nozzle",
    "process": "0.20mm Standard @BBL X2D",
    "filament": "Bambu PLA Matte @BBL X2D 0.4 nozzle",
}
OVERRIDES = {
    "machine": {"curr_bed_type": "Textured PEI Plate"},
    "process": {"filament_map_mode": "Manual", "filament_map": ["1"]},  # 1 = main hotend
    "filament": {},
}

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "exports" / "cursed_benchy.3mf"
STL = ROOT / "docs" / "cursed_benchy.stl"
PLATE = ROOT / "exports" / "cursed_benchy_plate.3mf"
BED = 256.0

VERTEX = re.compile(rb'<vertex x="([-0-9.eE+]+)" y="([-0-9.eE+]+)" z="([-0-9.eE+]+)"')
TRIANGLE = re.compile(rb'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"')


def read_mesh(path):
    """Vertices and triangles from the 3MF's core model part."""
    with zipfile.ZipFile(path) as archive:
        name = next(n for n in archive.namelist() if n == "3D/3dmodel.model")
        data = archive.read(name)
    vertices, triangles = [], []
    for line in data.splitlines():
        match = VERTEX.search(line)
        if match:
            vertices.append(tuple(float(v) for v in match.groups()))
            continue
        match = TRIANGLE.search(line)
        if match:
            triangles.append(tuple(int(v) for v in match.groups()))
    return vertices, triangles


def write_stl(vertices, triangles, path, dx=0.0, dy=0.0):
    with open(path, "wb") as out:
        out.write(b"\0" * 80)
        out.write(struct.pack("<I", len(triangles)))
        for i, j, k in triangles:
            a = (vertices[i][0] + dx, vertices[i][1] + dy, vertices[i][2])
            b = (vertices[j][0] + dx, vertices[j][1] + dy, vertices[j][2])
            c = (vertices[k][0] + dx, vertices[k][1] + dy, vertices[k][2])
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            wx, wy, wz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            nx, ny, nz = uy * wz - uz * wy, uz * wx - ux * wz, ux * wy - uy * wx
            length = (nx * nx + ny * ny + nz * nz) ** 0.5 or 1.0
            out.write(struct.pack("<12fH", nx / length, ny / length, nz / length,
                                  *a, *b, *c, 0))


def flat_preset(kind, name):
    """A system preset with its `inherits` chain merged in; the CLI does not resolve it."""
    data = json.loads((PROFILES / kind / f"{name}.json").read_text())
    if data.get("inherits"):
        merged = flat_preset(kind, data["inherits"])
        merged.update(data)
        data = merged
    data.pop("inherits", None)
    data["name"] = name
    return data


def bambu_command(tmp):
    files = {}
    for kind, name in PRESETS.items():
        data = flat_preset(kind, name)
        data.update(OVERRIDES[kind])
        files[kind] = tmp / f"{kind}.json"
        files[kind].write_text(json.dumps(data))
    return [str(BAMBU), "--load-settings", f"{files['machine']};{files['process']}",
            "--load-filaments", str(files["filament"]), "--arrange", "0", "--orient", "0"]


def write_plate(stl, path):
    """Write the unsliced Bambu Studio project."""
    path = Path(path).resolve()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        command = bambu_command(tmp)
        # --outputdir keeps result.json out of the working folder; it also prefixes
        # --export-3mf, so pass the bare file name.
        subprocess.run(command + ["--outputdir", str(path.parent),
                                  "--export-3mf", path.name, str(stl)],
                       check=True, capture_output=True, text=True)
        (path.parent / "result.json").unlink(missing_ok=True)
    assert path.exists(), "Bambu Studio wrote no 3MF"


def check(stl):
    """Slice a copy and return the CLI's estimate."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        command = bambu_command(tmp)
        sliced = tmp / "sliced.gcode.3mf"
        run = subprocess.run(command + ["--slice", "0", "--outputdir", str(tmp),
                                        "--export-3mf", sliced.name, str(stl)],
                             capture_output=True, text=True)
        assert sliced.exists(), run.stdout[-2000:] + run.stderr[-2000:]
        with zipfile.ZipFile(sliced) as archive:
            info = archive.read("Metadata/slice_info.config").decode()
        return info


def main():
    vertices, triangles = read_mesh(SOURCE)
    print(f"mesh: {len(vertices)} vertices, {len(triangles)} triangles")
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    # The download STL is centred on the origin; the plate copy sits at the bed centre.
    write_stl(vertices, triangles, STL, -cx, -cy)
    print(f"wrote {STL.relative_to(ROOT)} ({STL.stat().st_size / 1e6:.1f} MB)")
    with tempfile.TemporaryDirectory() as tmp:
        plate_stl = Path(tmp) / "cursed_benchy.stl"
        write_stl(vertices, triangles, plate_stl, BED / 2 - cx, BED / 2 - cy)
        write_plate(plate_stl, PLATE)
        print(f"wrote {PLATE.relative_to(ROOT)} ({PLATE.stat().st_size / 1e6:.1f} MB)")
        if "--check" in sys.argv:
            info = check(plate_stl)
            for key in ("prediction", "weight", "support_used"):
                match = re.search(rf'key="{key}" value="([^"]*)"', info)
                print(f"{key}: {match.group(1) if match else '?'}")


if __name__ == "__main__":
    main()
