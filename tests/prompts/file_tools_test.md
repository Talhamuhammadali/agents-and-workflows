# File Tools Test Prompt

You are testing the workspace file tools. Run through every test below **in order**.

## Rules
1. **Create a to-do list first** — one item per test (W1, W2, ... C2). Check each off as you go.
2. **If a test fails, note the failure and move on** to the next test. Do not stop to fix or retry — capture what went wrong and continue.
3. Be smart about it — if a prior test created or modified a file that a later test depends on, adapt accordingly.
4. After all tests, give a **summary**: which passed, which failed, and a brief reason for each failure.

---

## Write Tool Tests

### W1 — Create a new file from scratch
> Create a file `src/constants.py` with a `MAX_RETRIES = 5` and `APP_NAME = "sandbox"` constants.

**Verify:** `src/constants.py` exists with both constants.

### W2 — Create a file in an existing subdirectory
> Create a file `docs/changelog.md` with a header `# Changelog` and an entry `## 0.1.0` with bullet `- Initial release`.

**Verify:** `docs/changelog.md` has the header and entry.

### W3 — Create a file in a NEW subdirectory (should fail)
> Create a file `logs/app.log` with content `started`.

**Verify:** Tool raises error — parent directory `logs/` does not exist. Agent should recognize this and create the directory first (via bash) or inform the user.

### W4 — Overwrite an existing file
> Overwrite `config.json` with `{"app_name": "sandbox-v2", "version": "0.2.0", "debug": true, "max_retries": 5}`.

**Verify:** `config.json` has the new content, old content is gone.

---

## Edit Tool Tests

### E1 — Simple single replacement
> In `src/main.py`, change the greeting from `"Hello, {name}!"` to `"Hi there, {name}!"`.

**Verify:** Only that one f-string changed. Rest of file untouched.

### E2 — Replace a function body
> In `src/utils.py`, update `is_even` to use bitwise AND instead: `return n & 1 == 0`.

**Verify:** Only the return statement in `is_even` changed.

### E3 — Edit that requires context (ambiguous match)
> In `src/main.py`, change `print` to `logging.info` — but only the one inside `main()` that prints the greeting, not the arithmetic one.

**Verify:** Agent must provide enough surrounding context in `old_string` to make a unique match. Should change `print(greet("World"))` to `logging.info(greet("World"))`.

### E4 — Replace all occurrences
> In `docs/notes.md`, replace every `-` bullet with `*`.

**Verify:** All three bullets changed from `- ` to `* `. The `---` separator should NOT be affected (agent should use `- ` with trailing space as the match pattern).

### E5 — Edit non-existent string (should fail gracefully)
> In `src/main.py`, replace `"Goodbye"` with `"See you"`.

**Verify:** Tool raises "String not found" error. Agent communicates this clearly.

### E6 — Multi-line edit
> In `src/main.py`, replace the entire `add` function (signature + body + docstring) with a `subtract` function that returns `a - b`.

**Verify:** `add` is gone, `subtract` exists. The `main()` call still references `add` — agent should ideally notice and update it too, or flag it.

---

## Combined Write + Edit Flow

### C1 — Create then immediately edit
> First create `src/models.py` with a `User` class that has `name` and `email` fields. Then edit it to add an `age` field.

**Verify:** File exists with all three fields.

### C2 — Edit config then create a module that reads it
> Edit `config.json` to add `"log_level": "INFO"`. Then create `src/logger.py` that defines a `LOG_LEVEL = "INFO"` constant.

**Verify:** Both files are correct.
