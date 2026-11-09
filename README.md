# Cursed Benchy

A 3DBenchy buried under BumpMesh's Square Setts texture: 65 × 36 × 51 mm of cobblestone, 632,345 triangles, one colour, no supports.

- Page: https://ivanifchen.github.io/cursed-benchy/
- STL: [docs/cursed_benchy.stl](docs/cursed_benchy.stl)
- 3MF: [exports/cursed_benchy.3mf](exports/cursed_benchy.3mf)
- Bambu Studio project: [exports/cursed_benchy_plate.3mf](exports/cursed_benchy_plate.3mf)

The 3MF is the BumpMesh export as downloaded: one mesh, no plate or settings. The plate project is centred on the X2D's 256 mm plate, 0.4 nozzle, stock 0.20 mm Standard, Bambu PLA Matte on the main hotend, Textured PEI. It is unsliced: open it, pick the AMS slot, slice. Stock settings came to 25 g and about 1 h 54 min, no supports.

## Source

- Original: [3DBenchy](https://www.3dbenchy.com/) by Daniel Norée, released CC0 1.0 in 2025.
- Texture: [BumpMesh](https://bumpmesh.com/) by CNC Kitchen, Square Setts preset at amplitude 3.00, exported 2026-11-08.
- `src/prepare.py`: converts the BumpMesh 3MF to the download STL and writes the Bambu Studio project. `python3 -I src/prepare.py --check` also slices a copy and prints the estimate.

The displacement leaves 86 non-manifold edges (69 boundary, 17 shared by more than two faces). Bambu Studio slices the mesh without repairs; the estimate above is from that slice.
