# `grep_search` Tool — Assessment Report

**Tested against:** `grep_test/` fixture directory (7 files, 2 levels deep, 5 extensions: `.py`, `.yaml`, `.md`, `.csv`, `.txt`)

---

## Summary

All 14 parameters tested. The tool is **fully functional and reliable** across every scenario. One behavioural nuance noted for `multiline` mode. No crashes, no silent failures.

---

## Test Results

### 1. `output_mode='files_with_matches'` ✅
- Returns a flat list of file paths that contain at least one match.
- Default mode — lowest noise, best for "does this pattern exist, and where?"
- Case-sensitive by default: `employee` did **not** match `Employee` or `EMPLOYEE`.

---

### 2. `output_mode='content'` ✅
- Returns each matching line with its filename and line number.
- Format: `filename → line_number → line_content`, separated by `--` between blocks.
- Line numbers are accurate and consistent with actual file layout.
- Best mode for precision navigation before calling `read_file`.

---

### 3. `output_mode='count'` ✅
- Returns `filename: N` count per file.
- Counts are correct (cross-checked against `content` mode).
- Ideal for density analysis — quickly shows which files have the most hits.

---

### 4. `case_insensitive=true` ✅
- Correctly expands match scope to cover all casing variants.
- Example: `employee` → also matched `Employee`, `EMPLOYEE`, `employees`.
- File count grew from 5 → 6, match counts increased accurately in all files.
- Default is **case-sensitive** — must be explicitly opted into for case-agnostic search.

---

### 5. Regex patterns ✅
- Full Python `re` syntax is supported.
- Tested and confirmed working:
  - Character classes: `[\w\.-]+@[\w\.-]+\.\w{2,}` — matched all emails in CSV.
  - Quantifiers: `\d{5,6}` — matched 5- and 6-digit salary values.
  - Alternation groups: `def (get|run|load)_\w+` — matched targeted function names across files.
- No escaping issues. The engine is Python `re`, not POSIX grep.

---

### 6. `multiline=true` ✅ *(with behavioural note)*
- Pattern `def transform.*\n.*"""` correctly matched a function signature spanning two lines.
- **Behavioural note:** With `multiline=true`, the tool applies `re.DOTALL | re.MULTILINE`, which makes `.` match newlines. This causes the returned content block to span from the match to a much larger portion of the file — not just the two matched lines.
- **Implication:** Do not use `multiline=true` when you need tight, line-level output. Use it only when you need cross-line detection and are okay with a broader content window.

---

### 7. `before` / `after` / `context` ✅
- `before=N`: returns N lines preceding the match line. Verified with `before=2`.
- `after=N`: returns N lines following the match line. Verified with `after=2`.
- `context=N`: shorthand for equal `before` and `after`. Verified with `context=2`.
- All three are precise — exactly N lines, no more, no less.
- `context` is the cleanest option when symmetric padding is needed.

---

### 8. `file_type` filter ✅
- `file_type='py'` correctly restricted search to `**/*.py` files only.
- `.yaml`, `.md`, `.csv`, `.txt` files were all excluded.
- Shorthand — internally expands to a glob pattern.
- **Note:** `file_type` and `glob` are mutually exclusive per the spec; `file_type` takes precedence when both are set.

---

### 9. `glob` filter ✅
- Custom glob `**/sub/*.py` restricted results to `pipeline.py` in the `sub/` directory.
- Root-level `.py` files (`employees.py`, `utils.py`) were correctly excluded.
- More flexible than `file_type` — supports path-aware patterns, prefix matching, etc.
- Use `glob` when you need structural file targeting beyond just extension.

---

### 10. `path` restriction ✅
- Setting `path='grep_test/sub'` hard-scoped the search to that directory tree only.
- No root-level files appeared in results.
- Works as expected — equivalent to setting a search root.
- **Note:** Passing a file path directly (e.g. `path='grep_test/data.csv'`) raises a `Directory not found` error — `path` must be a directory, not a file.

---

### 11. `head_limit` ✅
- `head_limit=5` returned exactly 5 results and stopped.
- Default is 250 — sufficient for most codebases, but large files/patterns may need explicit adjustment.
- Hard cutoff, not a soft hint.

---

### 12. `offset` ✅
- `offset=5` skipped the first 5 matches and resumed from match 6 onward.
- Combined with `head_limit`, this provides reliable **pagination** over large result sets.
- Verified by cross-referencing offset+limit windows against the full result set — no duplicates, no gaps.

---

### 13. `show_line_numbers=false` ✅
- Line number prefixes are stripped from the output.
- Content and filename header are still returned.
- Useful when output is going into a report, a downstream prompt, or any context where positional info is noise.
- Default is `true` — keep it on during navigation/debugging.

---

### 14. No-match scenario ✅
- Returns a clean `[SYSTEM] No matches for pattern '...' under '...'` message.
- Does **not** raise an exception or return an ambiguous empty result.
- Safe to use in automated / chained workflows — the no-match state is explicitly distinguishable.

---

## Parameter Interaction Notes

| Combination | Behaviour |
|---|---|
| `head_limit` + `offset` | Clean pagination — verified, no gaps or duplicates |
| `file_type` + `path` | Both apply independently — AND logic |
| `glob` + `path` | Both apply — glob is relative to the `path` root |
| `case_insensitive` + regex | Works correctly — flags are combined |
| `multiline` + `context` | Not tested in combination — likely to produce very large output blocks; use with caution |
| `path` = file (not dir) | **Raises error** — path must be a directory |

---

## Recommended Usage Patterns

```
# 1. Locate files first, then read precisely
grep_search(pattern, output_mode='files_with_matches')
→ read_file(path, offset=<line>)

# 2. Audit pattern density across a codebase
grep_search(pattern, output_mode='count', file_type='py')

# 3. Paginate large result sets
grep_search(pattern, output_mode='content', head_limit=50, offset=0)
grep_search(pattern, output_mode='content', head_limit=50, offset=50)
...

# 4. Cross-line detection (use with caution)
grep_search(pattern_with_\n, multiline=True, output_mode='files_with_matches')
→ then use read_file for the precise window
```

---

## Verdict

The `grep_search` tool is **production-ready** for all standard code and content navigation tasks. It covers the full parameter surface correctly with one caveat: `multiline=true` is best used as a detection tool (with `files_with_matches`) rather than a content extraction tool, due to the large output spans it produces under `re.DOTALL`.
