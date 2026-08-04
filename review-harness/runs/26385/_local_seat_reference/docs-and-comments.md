### F1 — `n_jobs` docstring default contradicts the constructor signature
severity: medium
evidence: `sklearn/cluster/_hdbscan/hdbscan.py:486` documents `n_jobs : int, default=None` and lines 487-489 say "``None`` means 1 ...", but the constructor at `sklearn/cluster/_hdbscan/hdbscan.py:658` declares `n_jobs=4`.
scenario: "A user reads the docstring, expects the default to be `None` (single-threaded unless in a parallel_backend), and instead gets 4 parallel jobs by default → unexpected CPU/thread usage and confusion about reproducible defaults."
contract: Change the `n_jobs` docstring default to `default=4` (matching the signature and PLAN R2), and drop or correct the "`None` means 1" wording so it describes the actual default.
instances: single-instance

### F2 — `centroids_`/`medoids_` docstrings claim label -3 is excluded, but the code only excludes -1 and -2
severity: medium
evidence: `sklearn/cluster/_hdbscan/hdbscan.py:561-562` and `:572-573` state "the `-1, -2, -3` labels for the outlier clusters are excluded" from `n_clusters`, but `_weighted_cluster_center` computes `n_clusters = len(set(self.labels_) - {-1, -2})` at `sklearn/cluster/_hdbscan/hdbscan.py:895`, which does not remove `-3` (missing-data) labels.
scenario: "Fit with `store_centers` set on data containing NaN rows (label -3) present alongside clusters → the `-3` label inflates `n_clusters` by one, so `centroids_`/`medoids_` gets an extra all-uninitialized/garbage row, directly contradicting the documented invariant that `-3` is excluded."
contract: Make the code match the documented invariant by excluding `-3` as well: `n_clusters = len(set(self.labels_) - {-1, -2, -3})`.
instances: [sklearn/cluster/_hdbscan/hdbscan.py:895, sklearn/cluster/_hdbscan/hdbscan.py:561, sklearn/cluster/_hdbscan/hdbscan.py:572]

### F3 — `_hdbscan_prims` docstrings a `copy` parameter that the function does not accept
severity: low
evidence: `sklearn/cluster/_hdbscan/hdbscan.py:313-318` documents a `copy : bool, default=False` parameter, but the `_hdbscan_prims` signature (`sklearn/cluster/_hdbscan/hdbscan.py:269-278`) has no `copy` parameter (it was copied from `_hdbscan_brute`).
scenario: "A developer reading `_hdbscan_prims` sees `copy` documented and tries to pass `copy=...` through the prims path → the argument is silently swallowed into `**metric_params` and mis-forwarded to the distance metric rather than controlling copying."
contract: Delete the `copy` parameter block from the `_hdbscan_prims` docstring.
instances: single-instance

### F4 — `min_samples` documented as `default=None` where the signature has a numeric/required default
severity: low
evidence: `_brute_mst` takes `min_samples` as a required positional (`sklearn/cluster/_hdbscan/hdbscan.py:82`) yet its docstring says `min_samples : int, default=None` (`:95`); `_hdbscan_brute` defaults `min_samples=5` (`:160`) but documents `default=None` (`:179`); `_hdbscan_prims` defaults `min_samples=5` (`:272`) but documents `default=None` (`:290`).
scenario: "A maintainer relies on the docstring and assumes `min_samples` defaults to `None` in these helpers → writes call sites/None-handling that never triggers, or misreports the helper contract."
contract: Update each helper's `min_samples` docstring default to match its signature (remove `default=None` for the required `_brute_mst` arg; use `default=5` for `_hdbscan_brute` and `_hdbscan_prims`).
instances: [sklearn/cluster/_hdbscan/hdbscan.py:95, sklearn/cluster/_hdbscan/hdbscan.py:179, sklearn/cluster/_hdbscan/hdbscan.py:290]

### F5 — `_sparse_mutual_reachability_graph` docstring documents a `distance_matrix` parameter that is not in the signature
severity: low
evidence: `sklearn/cluster/_hdbscan/_reachability.pyx:152-159` defines the signature as `(data, indices, indptr, n_samples, further_neighbor_idx, max_distance)`, but the Parameters section at `:167-169` documents `distance_matrix : sparse matrix ...` and never documents `data`, `indices`, `indptr`, or `n_samples`.
scenario: "A developer reads the docstring to learn the calling convention, expects to pass a `distance_matrix`, and is misled about the actual CSR-component arguments the function requires."
contract: Replace the `distance_matrix` entry with entries for the actual parameters (`data`, `indices`, `indptr`, `n_samples`) that describe the CSR components.
instances: single-instance

### F6 — User-guide text inverts the DBSCAN* noise condition and contains rendering typos
severity: medium
evidence: `doc/modules/clustering.rst:1010-1011` states "Any points whose core distance is less than :math:`\varepsilon`: are at this staged marked as noise." In HDBSCAN*/DBSCAN* a point is noise when its core distance is *greater than* ε (too sparse to be a core point at that scale); the ≤ ε points are the ones retained. The same sentence has the typo "staged" (→ "stage") and stray trailing colons after the math roles (`:math:`\varepsilon`:`) at `:1009` and `:1010`.
scenario: "A reader following the user guide to understand the algorithm concludes that dense points (small core distance) are discarded as noise → an exactly backwards mental model of how ε trims the mutual-reachability graph."
contract: Change "less than" to "greater than" in the noise sentence, fix "staged"→"stage", and remove the stray trailing colons on the `:math:`\varepsilon`` roles.
instances: single-instance

### F7 — (out-of-theme) Gallery "Scale Invariance" section's narration is contradicted by the code, which never scales the data
severity: medium
evidence: `examples/cluster/plot_hdbscan.py:106-110` loops over `scale in (1, 0.5, 3)` under comments (`:102-105`) asserting "HDBSCAN is scale-invariant", but line 109 calls `hdb.fit(X)` and line 110 plots `X` — always the unscaled data — so every subplot clusters identical data and the "scale" label is cosmetic; the section demonstrates nothing about scale invariance.
scenario: "A user runs the gallery example to see HDBSCAN's scale invariance → sees three identical plots that would look the same for any (even scale-variant) estimator, so the documented claim is unsupported by the shown output."
contract: Fit and plot the scaled data in the loop, i.e. `hdb.fit(X * scale)` and `plot(X * scale, hdb.labels_, hdb.probabilities_, ...)`, so the section actually exercises scale invariance.
instances: single-instance

### F8 — Repeated spelling typos in Cython docstrings ("reahability", "collecteion", "tree tree")
severity: low
evidence: The phrase "MST representation of the mutual-reahability graph. The MST is represented as a collecteion of edges." recurs verbatim (e.g. `sklearn/cluster/_hdbscan/_linkage.pyx:75-76`, `:137-138`, `:228-229`), and "The single-linkage tree tree (dendrogram)" duplicates the word "tree" (e.g. `sklearn/cluster/_hdbscan/_linkage.pyx:234`, `sklearn/cluster/_hdbscan/hdbscan.py:148`, `:219`, `:325`, `:361`).
scenario: "A reader of the developer-facing docstrings encounters the misspellings 'reahability'/'collecteion' and the duplicated 'tree tree' → minor loss of polish and searchability of the term 'reachability'."
contract: Fix the spellings to "reachability" and "collection" and remove the duplicated "tree" wherever these phrases appear.
instances: [sklearn/cluster/_hdbscan/_linkage.pyx:75, sklearn/cluster/_hdbscan/_linkage.pyx:76, sklearn/cluster/_hdbscan/_linkage.pyx:137, sklearn/cluster/_hdbscan/_linkage.pyx:138, sklearn/cluster/_hdbscan/_linkage.pyx:228, sklearn/cluster/_hdbscan/_linkage.pyx:229, sklearn/cluster/_hdbscan/_linkage.pyx:234, sklearn/cluster/_hdbscan/hdbscan.py:148, sklearn/cluster/_hdbscan/hdbscan.py:219, sklearn/cluster/_hdbscan/hdbscan.py:325, sklearn/cluster/_hdbscan/hdbscan.py:361]