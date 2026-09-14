# review-02-publication: Repair and publish LayoutBench

- Status: Completed
- Date: 2026-09-14
- Assignee: Edward Benson
- Branch: review-02-publication
- PR: https://github.com/eob/layoutbench/pull/1
- Harness: codex
- Machine: shared benchmark workspace
- Session: /root/review_layoutbench
- Authorization: user requested thorough review, revisions, reruns, commits, pushes, publication, and no questions.

Review source, frozen corpus, request/scoring protocol, reproducibility, and result reporting. Record evidence and decisions in `docs/reviews/2026-09-14-publication-review.md`. Preserve 0.1.0 unchanged; publish revised 0.2.0 using all 208 tasks and 11 configurations after clean gates. The repository initially had no remote; root confirmed eob/layoutbench absent and authorized creation as public source for the benchmark publication.

Plan: prove findings; repair option-order leakage, visible header boundaries and flow count imbalance; clarify prompts; rerender and freeze a new release; execute full campaign; independently recompute raw results; seal source evidence; create and push public repository; send source inputs to site publication owner.

Outcome: 0.2.0 frozen and fully rerun (2,288 responses), source checkpoint4b13617 sealed and independently audited. 76 Python/9 TypeScript tests, typechecking, repeated rendering and release/finalization verification passed. The public repository is https://github.com/eob/layoutbench and the delivery PR is #1.
