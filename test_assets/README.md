# Test assets

Small meshes used by the automated tests (`backend/tests/`) and for manual QA of the
viewer and geometry pipeline.

| File | Description | Generator |
|------|-------------|-----------|
| `cube_20mm.stl` | A 20 mm watertight cube. Smallest useful import smoke test. | `make_test_assets.py` |
| `plate_with_hole.stl` | A 40×30×4 mm plate with a 6 mm through-hole. Good for boolean/repair tests. | `make_test_assets.py` |

Regenerate them with:

```bash
cd test_assets
python make_test_assets.py
```

## License

These mesh assets are licensed under **CC BY 4.0** (see [LICENSE-ASSETS.md](../LICENSE-ASSETS.md)),
**not** the MIT license that covers the code. Attribution is required if you reuse them.
