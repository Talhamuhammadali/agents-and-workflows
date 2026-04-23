---
name: fileops
description: Effective use of workspace file and shell tools — Read, Write, Edit, Grep, Glob, bash — including how to combine them.
allowed-tools: "Read, Write, Edit, Grep, Glob, bash"
version: 1.0.0
---

# File operations — effective usage

You have six workspace tools. Each one has a narrow, specific purpose. Knowing
*which tool to reach for* is worth more than knowing any one tool deeply.

| Tool   | Role                                                 |
|--------|------------------------------------------------------|
| Glob   | Find files by name / extension                       |
| Grep   | Find files by content (regex)                        |
| Read   | View a file's content (with line numbers)            |
| Write  | Create a new file OR fully replace an existing one   |
| Edit   | Surgically modify part of an existing file           |
| bash   | Everything else (mkdir, git, tests, CLI tooling)     |

All paths are relative to the workspace root. All tools are sandboxed to the
workspace — they cannot reach outside it.

## The golden rules

1. **Search before you read.** If you don't already know where something is,
   don't guess paths — use Glob (by name) or Grep (by content) first.
2. **Read before you edit.** Edit matches exact strings. Never call Edit on a
   file you haven't Read in this conversation. If the file is large, Read the
   specific region (`offset` + `limit`) that contains the target.
3. **Prefer Edit over Write for existing files.** Write overwrites the whole
   file. Only Write when you're creating a new file or truly replacing
   everything.
4. **Prefer Grep/Glob over `bash rg`/`bash find`.** The in-process tools are
   faster, sandboxed, and return structured output.
5. **Use bash for what the file tools can't do**: creating directories,
   moving/renaming, running tests, git, package managers.

## Tool-by-tool

### Glob — "what files exist matching a pattern?"

```
pattern: "**/*.py"              → every Python file
pattern: "src/**/test_*.py"     → only test files under src
pattern: "*.md"                 → top-level docs only
```

Sorted newest-first by modification time, so the files you've been touching
bubble up. Returns up to 200 paths by default — raise `limit` if you need
more, but a broader pattern usually means you should narrow your thinking
instead.

### Grep — "where is this symbol / string / pattern?"

Two-phase workflow:

1. **Locate files** with `output_mode="files_with_matches"` (default). Cheap,
   returns just filenames.
2. **Inspect hits** with `output_mode="content"` and `context=3` (or
   `before`/`after`) for surrounding lines.

```
# phase 1: where does FooBar appear?
pattern="FooBar", file_type="py"
# phase 2: show the hits with context
pattern="FooBar", file_type="py", output_mode="content", context=3
```

For regex work: `case_insensitive=true` for case-blind matches, `multiline=true`
if the pattern must span lines (sets `re.DOTALL | re.MULTILINE`). Use
`file_type="py"` as the cleanest way to restrict by extension; fall back to
`glob="**/*.tsx"` only when `file_type` doesn't cover it.

### Read — "what's in this file?"

Output is `cat -n`-formatted (line number + TAB + content). Those line numbers
match Grep's output — never include the prefix when writing `old_string` for
Edit.

For large files, read the slice you need:

```
path="src/app.py", offset=450, limit=80
```

`force=true` skips the "unchanged since last read" optimization and always
returns the full content. You almost never need it — the default is the
right behaviour.

### Write — "replace / create the whole file"

Use when:
- Creating a new file
- Rewriting more than ~70% of an existing file

Do NOT use for small edits. Overwriting a 500-line file to change one function
is wasteful and risks losing unrelated changes.

The parent directory must already exist — Write does not mkdir. If it
doesn't, run `bash: mkdir -p <dir>` first.

### Edit — "surgical change to part of a file"

Edit matches `old_string` exactly, including whitespace and indentation, and
replaces it with `new_string`. Two failure modes:

- **No match** → your `old_string` doesn't appear verbatim. Re-Read the region
  and copy the text.
- **Multiple matches** without `replace_all=true` → you must add more
  surrounding context until the snippet becomes unique, OR set
  `replace_all=true` if every occurrence should change.

Rename a symbol everywhere in a file: `replace_all=true` with the identifier
as `old_string`.

### bash — "anything the file tools can't do"

Reach for bash when you need:
- `mkdir -p path/to/dir` — Write does not create parent directories
- `mv old new`, `cp src dst`, `rm file` — no dedicated tool for these
- `git status`, `git diff`, `git log`, `git add -p` — repo state
- Running tests: `pytest`, `npm test`, `cargo test`
- Running the code: `python script.py`, language servers, formatters
- Package managers: `pip install`, `npm install`, `uv sync`

Output is streamed live to the user AND returned to you after completion.
Default timeout 120s, bump with `timeout=` for slow operations.

System installers (`apt`, `apt-get`, `yum`) are blocked — they won't run even
if you try. Output over ~10k tokens is tail-truncated.

## Combining tools effectively

The value of this skill is in combinations. Single-tool tasks are rare.

### Pattern: "change a function across the codebase"

```
1. Grep  pattern="def old_name", output_mode="files_with_matches"
         → list of files
2. Grep  pattern="old_name", file_type="py", output_mode="content", context=2
         → see every call site
3. Read  each file once, at the right offset
4. Edit  with replace_all=true per file, OR one Edit per site for finer control
5. bash  "pytest -x"   → verify nothing broke
```

### Pattern: "add a new module and wire it up"

```
1. Glob  pattern="src/**/__init__.py"
         → find where packages live
2. bash  "mkdir -p src/foo"   (only if the dir doesn't exist)
3. Write src/foo/__init__.py
4. Write src/foo/core.py
5. Read  the sibling __init__.py that already exports modules
6. Edit  it to add the new export
7. bash  "python -c 'import src.foo'"   → smoke-import
```

### Pattern: "bug hunt — I know a symptom, not the cause"

```
1. Grep  pattern=<the error message fragment>, output_mode="files_with_matches"
         → where does this message come from?
2. Grep  output_mode="content", context=5   → see the raising site
3. Read  the file(s) involved at the right offsets
4. bash  "git log --oneline -- <file>"      → recent changes touching it
5. bash  "git show <sha>"                   → the suspicious diff
```

### Pattern: "explore an unfamiliar codebase"

```
1. Glob  pattern="*.md"                    → READMEs first
2. Read  the top-level README
3. Glob  pattern="**/__init__.py" or "src/**/*.py" (limit=50)
4. Grep  pattern="def main|if __name__", output_mode="files_with_matches"
         → find entry points
5. Read  the entry point
```

## Cost discipline

Every tool call costs tokens. Work the following budget in your head:

- **Glob first (cheapest)** to shrink the search space.
- **Grep next** with `files_with_matches` before `content`.
- **Read narrow slices** — `offset` + `limit` — not whole files, whenever the
  file is > ~300 lines and you already know which region matters.
- **Batch Edits** to the same file — no need to Read again between Edits in
  the same turn unless your earlier Edit changed the region you're editing.
- **Don't re-Read** a file you just read (the tool returns an "unchanged"
  signal if you try anyway — that's your cue to stop).

## Anti-patterns — don't do these

- Reading a file before searching for it. Search is cheaper.
- Using Write to change three lines of a 500-line file.
- Calling Edit with `old_string` you typed from memory.
- Running `bash cat file` instead of Read (loses line numbers, no caching).
- Running `bash grep -r` instead of Grep (slower, no structured filters).
- Running `bash find` instead of Glob.
- Creating a file with Write when the parent dir doesn't exist — you'll just
  error. `bash mkdir -p` first.

## When tools fail

- **Edit: "multiple matches found"** → make `old_string` bigger until unique,
  or set `replace_all=true` if every occurrence should change.
- **Edit: "no match found"** → the file differs from what you expect. Re-Read
  the region (paste the line-number Grep gave you into Read's `offset`), then
  copy the exact text.
- **Read: "unchanged"** → you already have the content from an earlier Read.
  Don't re-Read; use the content you already saw.
- **Write: parent dir missing** → `bash: mkdir -p <dir>` then retry.
- **Grep: no matches** → widen the pattern first (shorter string,
  `case_insensitive=true`), before concluding the symbol doesn't exist.
