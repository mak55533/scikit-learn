# PLAN.md — plan of record for scikit-learn/scikit-learn#26385

> **Source:** PR #26385 "ENH Add `HDBSCAN` as a new estimator in
> `sklearn.cluster`" (merged 2023-05-31, +3,297/−10, 19 files) plus its linked
> tracker issue #24686 "Path to HDBSCAN Inclusion". This file is the plan the
> review measures the diff against — both directions: (a) requirements the diff
> omits/weakens/contradicts, and (b) changes no requirement sanctions.

## PR description (verbatim)

#### Reference Issues/PRs
Towards https://github.com/scikit-learn/scikit-learn/issues/24686

#### What does this implement/fix?
Each change has been separately reviewed (see issue #24686 for details).

Due to git shenanigans, some changes needed to be made within this PR. The novel
changes included with this PR are:
1. Replaced `cnp.*_t` typing with `*_t` from `_typedefs.pxd`.
2. Replaced `*.shape[0]` pattern with `len(*)` for `ndarray` objects.
3. Trimmed unused variables (thanks to Cython linting pre-commit).

## Linked tracker issue #24686 "Path to HDBSCAN Inclusion" (verbatim excerpt)

The HDBSCAN estimator implementation from `scikit-learn-contrib/hdbscan` has been
adopted, modified and refactored to conform to the scikit-learn API and merged
into the `hdbscan` feature branch. This PR merges `hdbscan` → `main`.

Mandatory work completed before merger (all checked off): cleaning
`_hdbscan/_tree.pyx`, the `_tree.pyx` overhaul (#26011, #26096, #26101),
and PRs #24857, #24701, #25768, #25826, #25827, #24698, #25538, #25134.
Follow-up work tracked separately in #26801.

## Effective feature contract (what a reviewer should hold the diff to)

Because the tracker issue delegates specifics to sub-PRs, the operative
requirements for THIS merge are:

### R1 — New public estimator `HDBSCAN` in `sklearn.cluster`
- A new `HDBSCAN` clustering estimator is added under
  `sklearn/cluster/_hdbscan/` and **exported** from `sklearn.cluster`
  (`sklearn/cluster/__init__.py` must add it to imports and `__all__`).
- Follows the scikit-learn estimator API: `fit(X, y=None)`, `fit_predict`,
  `get_params`/`set_params`, fitted attributes end in `_`
  (`labels_`, `probabilities_`, and centroid/medoid attrs when requested).

### R2 — Parameters and their contracts
Constructor parameters (with documented defaults):
`min_cluster_size=5`, `min_samples=None`, `cluster_selection_epsilon=0.0`,
`max_cluster_size=None`, `metric="euclidean"`, `metric_params`, `alpha=1.0`,
`algorithm="auto"`, `leaf_size=40`, `n_jobs=4`, `cluster_selection_method="eom"`,
`allow_single_cluster=False`, `store_centers=None`, `copy=False`.
- Each parameter must be declared in `_parameter_constraints` and validated
  (via `@validate_params` / `_validate_params`), and each must be documented in
  the class docstring with a type and meaning that matches the code.
- Invalid parameter values must raise informative errors, not silently misbehave.

### R3 — Core algorithm (Cython + Python)
- Mutual-reachability transform (`_reachability.pyx`), boruvka/prims-style MST
  and linkage (`_linkage.pyx`), and condensed-tree construction + cluster
  extraction (`_tree.pyx` / `_tree.pxd`) implement HDBSCAN* correctly.
- Noise points are labelled `-1`; `probabilities_` in [0, 1]; results are
  deterministic for a given input.
- Edge cases handled: fewer samples than `min_cluster_size`, duplicate points
  (zero distances), single cluster (`allow_single_cluster`), non-finite inputs
  rejected or handled explicitly.

### R4 — Build/packaging wiring
- The three Cython extensions (`_linkage`, `_reachability`, `_tree`) and the new
  `_hierarchical_fast.pxd` are registered in the build (`setup.py`) so the
  package compiles and installs the new submodule.

### R5 — Documentation
- User guide entry in `doc/modules/clustering.rst`; API reference entry in
  `doc/modules/classes.rst`; a changelog entry in `doc/whats_new/v1.3.rst`;
  a gallery example `examples/cluster/plot_hdbscan.py`; and inclusion in the
  `plot_cluster_comparison.py` gallery.

### R6 — Tests
- `sklearn/cluster/tests/test_hdbscan.py` and
  `sklearn/cluster/_hdbscan/tests/test_reachibility.py` exercise the estimator
  and the reachability core, and the estimator passes sklearn's common estimator
  checks (`sklearn/utils/estimator_checks.py` updated as needed).

### R7 — Novel changes in THIS PR (from the description)
1. `cnp.*_t` typing replaced with `*_t` from `_typedefs.pxd` — the two must not
   drift; no stale `cnp` typedefs left behind that change semantics.
2. `*.shape[0]` replaced with `len(*)` for ndarray objects — must be
   behavior-preserving (equal for 1-D/2-D leading axis).
3. Unused variables trimmed — removals must be genuinely unused (no lost
   side effects).

### Non-goals / out of scope for this merge
- Follow-up work in #26801 is explicitly deferred; its absence is NOT a defect.
- No changes outside enabling and documenting the HDBSCAN estimator are
  sanctioned; unrelated edits are scope creep.
