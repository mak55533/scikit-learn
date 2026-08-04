### F1 — Test uses element-wise array addition instead of concatenation, so the "clean" reference dataset still contains an outlier
severity: medium
evidence: sklearn/cluster/tests/test_hdbscan.py:212 — `clean_idx = list(set(range(200)) - set(missing_labels_idx + infinite_labels_idx))`. `missing_labels_idx` (`[2, 5]`) and `infinite_labels_idx` (`[0]`) are numpy arrays returned by `np.flatnonzero`, so `+` broadcasts element-wise: `array([2,5]) + array([0])` == `array([2,5])`, not the intended concatenation `[2,5,0]`. Index `0` (an `np.inf` outlier row) is therefore never removed from `clean_idx`.
scenario: "test_dbscan_clustering_outlier_data runs → the `clean_model` is fit on `X_outlier[clean_idx]` which still includes the infinite-outlier row 0, so the test asserts equivalence against a dataset that is not actually outlier-free and passes for the wrong reason (no regression caught if outlier removal semantics break)."
contract: Build the exclusion set with list/array concatenation, e.g. `set(np.concatenate([missing_labels_idx, infinite_labels_idx]))`, so the clean dataset genuinely excludes all outlier rows including the infinite one at index 0.
instances: single-instance

### F2 — No test exercises `store_centers` with non-finite (missing/`np.nan`) data, hiding a `-3`-label crash in `_weighted_cluster_center`
severity: medium
evidence: sklearn/cluster/tests/test_hdbscan.py:308-327 — `test_hdbscan_centers` only fits on fully finite data (`make_blobs` output and clean `X`). Meanwhile `sklearn/cluster/_hdbscan/hdbscan.py:895` computes `n_clusters = len(set(self.labels_) - {-1, -2})`, which does NOT subtract the `-3` "missing" label defined at `hdbscan.py:74`. With missing data present, `self.labels_` contains `-3`, so `n_clusters` is over-counted by one and the `for idx in range(n_clusters)` loop (`hdbscan.py:907`) reaches an index with no matching points, producing an empty `data`/`np.average` call.
scenario: "User calls `HDBSCAN(store_centers='centroid').fit(X)` on data containing an `np.nan` row → `n_clusters` includes the spurious `-3` cluster → the centroid loop indexes a nonexistent cluster and raises on `np.average` of an empty slice; no test covers this combination so the regression ships silently."
contract: Add a test that fits `HDBSCAN(store_centers="both")` on data containing an `np.nan`/`np.inf` row and asserts `centroids_`/`medoids_` have exactly the non-outlier cluster count, and fix the source set to `{-1, -2, -3}`.
instances: [sklearn/cluster/tests/test_hdbscan.py:308, sklearn/cluster/_hdbscan/hdbscan.py:895]

### F3 — `test_labelling_thresholding` supplies a `cluster_label_map` key that is never reachable, giving false confidence in two-cluster label mapping
severity: low
evidence: sklearn/cluster/tests/test_hdbscan.py:502-533 — the hand-built `condensed_tree` has every `parent == 5` (`n_samples`), so in `_do_labelling` (`sklearn/cluster/_hdbscan/_tree.pyx:480`) `root_cluster = np.min(parent_array) == 5` and the only non-root/non-noise label path (`_tree.pyx:493-494`) can map to cluster `5` only. The test passes `cluster_label_map={n_samples: 0, n_samples + 1: 1}` (line 515/525) but the `n_samples + 1: 1` entry can never be exercised by this single-parent tree; the test only ever validates the single-cluster (label `0` / noise) branch.
scenario: "A regression that mishandles the multi-cluster label mapping in `_do_labelling` → this test still passes because its literal tree only reaches the single-cluster branch, so the extra map entry advertises coverage that does not exist."
contract: Either drop the unreachable `n_samples + 1` map entry or extend the fixture with a second parent cluster so the multi-label mapping branch is genuinely exercised.
instances: [sklearn/cluster/tests/test_hdbscan.py:515, sklearn/cluster/tests/test_hdbscan.py:525]

### F4 — `test_outlier_data` infinite branch asserts probability-zero indices are exactly the outliers, but noise points also have probability zero
severity: low
evidence: sklearn/cluster/tests/test_hdbscan.py:49-65 — for `outlier_type="infinite"`, `prob_check = lambda x, y: x == y` with `prob == 0` (`hdbscan.py:71`), and the test asserts `(model.probabilities_ == 0).nonzero()` equals exactly `[0, 5]`. Per the estimator contract (`hdbscan.py:545` "Noisy samples have probability zero"), any `-1` noise point produced by the clustering also has probability `0`, which would make the equality with `[0, 5]` fail; the test only passes because this particular well-separated `X` happens to yield no zero-probability noise points.
scenario: "A data/parameter change (or algorithm tweak) that introduces even one ordinary noise point → `probabilities_ == 0` returns more than `[0, 5]` and the assertion breaks, even though infinite-outlier handling is correct — the test conflates 'infinite outlier' with 'any probability-zero point'."
contract: Assert the infinite-outlier condition on `labels_ == -2` (as the missing branch effectively does via label) or intersect the probability check with the outlier label indices, rather than relying on the whole dataset having no zero-probability noise samples.
instances: single-instance