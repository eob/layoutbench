# Independent qualitative release gate

Base revision: `80b30a11ca413c8ce240c51c1eba63f92ba972d7` plus the qualitative
implementation. The final corpus contains 292 questions across 250 images and
twenty families. The refreshed manifest and prompt catalog pass the root
integration gate: 107 Python tests in 13.92 seconds.

`baseline/qualitative_validation.py` derives each semantic answer from measured
box coordinates or text line rectangles, without consulting declared answers
or factor annotations. It then checks the independently recovered answer
against the chosen option and declared label. Prompt reconstruction comes from
the canonical question catalog and the full option permutation.

The gate also verifies image hashes, actual PNG dimensions, bundled font bytes
and recorded custom-font use, empty browser overflow evidence, finite geometry,
canvas/parent containment, and visible separation. Box borders are checked in
decoded PNG pixels. Every retained text line's decoded ink edges must be within
three CSS pixels of its browser line rectangle; observed glyph-side-bearing
differences were at most 2.5 pixels over all 522 lines.

Full-corpus requirements include each family's expected count, every answer's
theme/content crossing, balanced answer slots, and the complete parent/child
hierarchy cross. Duplicate PNG content shares one image and group identity;
different questions can share those images. Visible copy stays identical across
answers within each theme/content condition, except when the question itself
counts text columns or cards and therefore changes their number. The lexical
gate excludes answer-bearing layout terms; neutral prose's constant use of
“around” does not vary by answer.

| Gate | Result |
| --- | --- |
| Initial new suite before implementation | Missing validator module, retained in red log |
| Temporary implementation removal | Same missing-module failure; implementation restored |
| Validator suite after implementation and pixel controls | 18 passed |
| Validator plus model inventory/configuration gates | 45 passed |
| Final validator suite with copy-invariance tamper case | 19 passed in 10.54 seconds |
| Expanded nested-wrap position matrix | All 24 parent/alignment/theme/position combinations occur once |
| Root final Python integration gate on refreshed manifest | 107 passed in 13.92 seconds |
| Root deterministic rerender | 253 artifacts identical; 292 questions over 250 images |

Tamper tests reject changed answer labels even when the declared answer changes
with them, changed prompts, image/font hashes, overflow, escaping rectangles,
missing tasks, nuisance crossing, answer words, and neutral copy that varies
with the answer. They also reject replaced PNG pixels despite updated hashes,
falsified rectangle coordinates, and falsified text alignment despite matching
declared labels. Unit cases establish that answer recovery ignores declared
factors and that ambiguous small spatial differences fail closed.

The nested-wrap family includes both first-position and second-position target
sections. Its regression derives that position from section coordinates and
requires the complete parent × alignment × theme × position cross. The
`feat-03-nested-position-red.log` records the twelve missing second-position
combinations before expansion. The validator's joint hierarchy census now
requires 24 parent/child-flow cells and 24 nested-wrap cells.

These are construction and consistency checks. They do not measure human
agreement or establish population-level difficulty. The simplification pass
kept the gate in one module with shared geometry operations and no protocol or
renderer dependency.
