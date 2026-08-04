### F1 — `_weighted_cluster_center` indexes reduced `X` with full-size `labels_` mask when non-finite data is present
severity: high
evidence: `sklearn/cluster/_hdbscan/hdbscan.py:733,844,855,908-909` — in `fit`, when `metric != "precomputed"` and the input has non-finite rows, `X = X[finite_index]` (line 733) reduces `X` to only finite samples, then `self.labels_` is replaced by full raw-size `new_labels` (line 844). `_weighted_cluster_center(X)` is then called with the *reduced* `X` (line 855), but inside it computes `mask = self.labels_ == idx` (line 908) — a boolean of raw length — and applies it as `data = X[mask]` (line 909), where `X` has only `finite_count` rows.
scenario: "`HDBSCAN(store_centers='centroid').fit(X)` where `X` contains any `np.nan`/`np.inf` row → boolean mask of length `n_raw` is applied to feature array of length `n_finite < n_raw`, raising `IndexError: boolean index did not match indexed array` (or silently misaligning centroids/medoids)."
contract: In `fit`, pass the raw-aligned feature array (or restrict the mask to `finite_index`) into `_weighted_cluster_center` so the mask length matches the data length whenever non-finite samples were removed.
instances: single-instance

### F2 — Cluster count in `_weighted_cluster_center` omits the `-3` (missing) outlier label, over-counting clusters
severity: medium
evidence: `sklearn/cluster/_hdbscan/hdbscan.py:895` — `n_clusters = len(set(self.labels_) - {-1, -2})`; the missing-data outlier label is `-3` (`_OUTLIER_ENCODING["missing"]["label"]`, line 75) and is NOT subtracted. The class docstring (lines 561-562, 572-573) explicitly states the `-1, -2, -3` outlier labels are all excluded from `n_clusters`.
scenario: "`HDBSCAN(store_centers='centroid').fit(X)` where `X` has an `np.nan` row (label `-3` present) → `n_clusters` is inflated by 1, the centroid/medoid array is allocated one row too large, and the loop `for idx in range(n_clusters)` iterates one extra positive label with no members, producing a garbage/degenerate final center row (`np.average` over an empty slice or an all-False mask)."
contract: Exclude all outlier labels when counting clusters: `n_clusters = len(set(self.labels_) - {-1, -2, -3})` (matching the documented contract).
instances: single-instance