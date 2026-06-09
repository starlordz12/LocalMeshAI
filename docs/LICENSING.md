# Licensing — code vs. design assets

LocalMeshAI uses **two licenses on purpose**, because a repository can contain both
software and creative/design assets, and those are best covered by different licenses.

## TL;DR

| What | License | File |
|------|---------|------|
| Source code | **MIT** | [LICENSE](../LICENSE) |
| 3D models, STL/OBJ/3MF/PLY, CAD, images, screenshots, diagrams, docs graphics, example assets | **CC BY 4.0** | [LICENSE-ASSETS.md](../LICENSE-ASSETS.md) |

## Why two licenses?

- **Public on GitHub does not automatically mean reuse is allowed.** A license is what
  grants permission to use, copy, modify, fork, and distribute. Without one, default
  copyright applies and others have no rights to reuse the work.
- **MIT** is simple, permissive, and ideal for *software*. It lets anyone use the code in
  personal, commercial, open-source, or closed-source projects, as long as the copyright
  and license notice are preserved.
- **MIT is written for code**, not creative works. For 3D models, images, and documentation
  a content license like **CC BY 4.0** is the better, clearer fit. CC BY 4.0 allows sharing
  and adaptation for any purpose while still requiring **attribution**.

## Practical rules for this repo

- If you reuse the **code**, keep the MIT notice. You do not have to attribute beyond that.
- If you reuse the **models / images / docs**, give attribution per CC BY 4.0.
- If a specific file carries its own license note, that note wins for that file.

This split is intentional and is reflected in the README "License" section, in
[LICENSE-ASSETS.md](../LICENSE-ASSETS.md), and in notes inside `examples/` and
`test_assets/`.
