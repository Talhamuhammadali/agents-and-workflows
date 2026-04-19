# `glob_search` — Findings & Recommended Improvements

## Confirmed Behaviour (Working Correctly)

| Pattern / Feature | Result |
|---|---|
| `**/*` — recursive all files | ✅ Returns every file across all directories |
| Extension filtering (`**/*.py`, `**/*.sql`, etc.) | ✅ Works correctly |
| `path` scoping (`path=src`, `path=docs`, etc.) | ✅ Restricts search to the given subtree |
| Filename patterns (`**/main.py`, `**/experiment*.py`) | ✅ Wildcard prefix/suffix matching works |
| `**/example.*` — any extension for a stem | ✅ Returns all variants |
| `**/*notes*`, `**/*hello*` — substring stem match | ✅ Finds files containing the substring |
| Case sensitivity (`Example.java` vs `example.*`) | ✅ Case-sensitive by default |
| `limit` (e.g. 1, 3) | ✅ Respected correctly |
| `limit=0` | ✅ Returns all results — intentional "no limit" convention |
| `limit=9999` (over total count) | ✅ Gracefully returns all without error |
| `*` (single-level root only) | ✅ Shallow glob works as expected |
| Nonexistent `path` | ✅ Returns a clear `Error: Directory not found` |
| No matches | ✅ Returns a clear `No matches` system message |

---

## Issues & Recommended Fixes

### 1. Brace Expansion Silently Fails
**Priority: High**

**Current behaviour:** `**/*.{py,sql,yml}` returns no matches with no error or warning.

**Problem:** Silent failure — indistinguishable from a pattern that genuinely matches nothing. Hard to debug.

**Should:** Either support brace expansion by unioning results across expanded patterns (standard shell behaviour), or raise an explicit error:
```
Error: Brace expansion not supported — use separate calls per extension.
```

---

### 2. Case-Insensitive Mode Missing
**Priority: Medium**

**Current behaviour:** Always case-sensitive. No toggle available.

**Problem:** Inconsistent with `grep_search`, which already exposes a `case_insensitive` boolean flag. Users switching between the two tools will be surprised.

**Should:** Add a `case_insensitive` boolean parameter (default `false`) to match `grep_search`'s interface.

---

### 3. No Exclusion / Negation Support
**Priority: Medium**

**Current behaviour:** No way to express "all files matching X, except Y".

**Problem:** Common need — e.g. all `.py` files excluding tests, or all models excluding a specific subdirectory.

**Should:** Add an explicit `exclude` parameter accepting a glob pattern:
```
pattern="**/*.py", exclude="**/experiment*.py"
```
An `exclude` list (multiple patterns) would be even better. Embedding negation in the pattern string (e.g. `!` prefix) is an alternative but an explicit parameter is cleaner.

---

### 4. Bare `*.ext` Pattern is a Silent Footgun
**Priority: High**

**Current behaviour:** `*.py` only matches files in the literal root directory. If none exist there, returns nothing — no warning.

**Problem:** Users almost always intend `**/*.py`. The distinction is easy to miss, and the silent no-result response gives no hint that the pattern is the issue.

**Should:** Either:
- Auto-promote bare `*.ext` to `**/*.ext` (prioritise user intent), or
- Emit a hint: `No matches — did you mean **/*.py?`

---

### 5. Sort Order Not Controllable
**Priority: Low**

**Current behaviour:** Results always sorted by modification time, newest first (documented).

**Problem:** mtime ordering is non-deterministic across environments. For scripted use, CI pipelines, or dbt workflows, this makes output order unpredictable.

**Should:** Add a `sort_by` parameter:
- `mtime` — current default, useful for "what changed recently"
- `path` — alphabetical, deterministic, better for reproducible output

---

## Priority Summary

| # | Issue | Priority |
|---|---|---|
| 1 | Brace expansion silently fails | 🔴 High |
| 4 | Bare `*.ext` pattern gives no warning | 🔴 High |
| 2 | No `case_insensitive` flag | 🟡 Medium |
| 3 | No exclusion/negation support | 🟡 Medium |
| 5 | Sort order not controllable | 🟢 Low |
