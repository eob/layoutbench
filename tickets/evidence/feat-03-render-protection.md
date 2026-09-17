# Protect frozen inputs during reproduction

Review base: `c6ec8eb`. The documented `bun run render` command previously
selected `dataset/layoutbench-v0.3`, overwrote its manifest/font/images, and
removed unmatched PNGs. That made a reproduction command capable of changing
frozen inputs when the rendering environment changed.

The qualitative renderer now defaults to `dataset/candidate-rendered`. Before
writing any file, it rejects output paths overlapping a registered release's
dataset directory or the two archived unregistered dataset paths. Checks cover
parents, descendants, and symlink aliases; similar filename prefixes remain
valid destinations. The README validates the separate candidate explicitly.

| Gate | Result |
| --- | --- |
| New protection suite before helper existed | Missing-module red retained |
| Temporary helper removal | Same red reproduced; helper restored |
| Focused protection suite | 6 passed, 15 assertions |
| Real qualitative CLI targeting 0.3.0 | Refused; manifest bytes unchanged |
| TypeScript check | Passed |
| Frozen protocol identity | Current code, release, and active run remain `deed0698dca65b5e24f3b06766d2d5344bbf0964e871167cebfc5e4aaba554fa` |

No renderer was allowed to regenerate images and no dataset, configuration,
baseline implementation, or active run record was modified. The guard is
outside the evaluation protocol fingerprint. The simplification pass retained
one small path guard and focused boundary tests.
