### F1 — `_weighted_cluster_center` indexes finite-only `X` with a raw-length `labels_` mask
severity: high
evidence: hdbscan.py:855 passes the finite-only `X` (reassigned at hdbscan.py:733 `X = X[finite_index]`) into `_weighted_cluster_center`, whose body at hdbscan.py:908-909 does `mask = self.labels_ == idx` then `data = X[mask]`; but `self.labels_` was replaced at hdbscan.py:840-844 with a raw-length array (`np.empty(self._raw_data.shape[0], ...)`), so `mask` has raw length while `X` has finite length.
scenario: "Fit with `store_centers` set and input containing any `np.nan`/`np.inf` row (metric != 'precomputed') → boolean mask of raw length is applied to the finite-only `X`, raising `IndexError: boolean index did not match indexed array` and aborting `fit`."
contract: In `_weighted_cluster_center`, index against `self._raw_data` (raw length, aligned with `self.labels_`/`self.probabilities_`) rather than the reduced finite-only `X`, so the mask length matches the data length.
instances: [sklearn/cluster/_hdbscan/hdbscan.py:855, sklearn/cluster/_hdbscan/hdbscan.py:908, sklearn/cluster/_hdbscan/hdbscan.py:909, sklearn/cluster/_hdbscan/hdbscan.py:910]

### F2 — Cluster count excludes only `{-1, -2}`, contradicting the `-3` outlier contract
severity: medium
evidence: hdbscan.py:895 `n_clusters = len(set(self.labels_) - {-1, -2})` omits the `-3` ("missing") label, even though `_OUTLIER_ENCODING` defines a `-3` label (hdbscan.py:73-78) and the `centroids_`/`medoids_` docstrings state "the `-1, -2, -3` labels for the outlier clusters are excluded" (hdbscan.py:561-562, 572-573).
scenario: "Fit with `store_centers` set and input containing `np.nan` rows → `-3` is counted as a real cluster, so `n_clusters` is one too large and the loop at hdbscan.py:907 iterates an `idx` with no members, producing an all-empty `data` and a spurious/NaN centroid row (or `np.average` empty-weights error)."
contract: Subtract the full outlier set (`{-1, -2, -3}`, i.e. `set(self.labels_) - {out["label"] for out in _OUTLIER_ENCODING.values()} - {-1}`) so `n_clusters` counts only genuine clusters, matching the documented contract.
instances: single-instance

### F3 — `n_jobs` documented default (`None`) does not match the actual constructor default (`4`)
severity: low
evidence: The class docstring at hdbscan.py:486 declares `n_jobs : int, default=None` ("`None` means 1 ..."), but `__init__` sets `n_jobs=4` (hdbscan.py:658), which is also the plan's stated default (PLAN.md R2).
scenario: "A user reads the docstring, expects single-threaded execution by default (`n_jobs=None` → 1), but the estimator actually runs with `n_jobs=4`, silently changing parallelism/behavior versus the documented interface."
contract: Change the docstring to `n_jobs : int, default=4` so the documented default matches the constructor signature.
instances: single-instance