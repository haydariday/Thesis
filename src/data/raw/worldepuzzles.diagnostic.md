# Wordle Puzzles Dataset — Diagnostic

**File:** `src/data/raw/worldepuzzles.json`
**Download / recorded date:** 2026-10-08 02:57:08 UTC (4 hours before 2026-10-08 06:57:08 UTC)
**Size:** 395,370 bytes / 395,370 chars
**Parsed:** valid JSON, top-level `dict` with numeric-string keys (`"0"` … `"1936"`)
**Note:** filename has typo — `worlde` vs `wordle`. Consider renaming to `wordlepuzzles.json`.

### Checksums

```
SHA256: ed235aa79e1c13a684b7517dda08976967ce8ddb653943632d71b7dea2c41a27
MD5:    84468106d10ccef6b4c98d7bea4ed880
```

Verify with:

```bash
sha256sum src/data/raw/worldepuzzles.json
md5sum src/data/raw/worldepuzzles.json
wc -c src/data/raw/worldepuzzles.json
```

## 1. Coverage

- Total entries: **1865**
- Key range: `0` – `1936` (expected 1937 entries if contiguous)
- Missing keys: **72**
  - `552–619` (68 keys), `621–624` (4 keys)
  - i.e. `[552, 553, …, 619, 621, 622, 623, 624]`
  - Key `620` is present; `552–619, 621–624` are absent.
- Action: decide if gap is deleted puzzles / source pagination issue. Do not assume `len == max_num+1`. Look up by key, not by index.

## 2. Schema

Two dominant schemas, plus 2 outliers:

| count | fields |
|------:|--------|
| 1178 | `answer, cumulative, date, datestr, individual, num, sample` |
| 685 | `+ hardmode` (`answer, cumulative, date, datestr, hardmode, individual, num, sample`) |
| 1 | key `625` (`PINKY`): missing `sample` |
| 1 | key `1273` (`BOXER`): missing `datestr`, has `hardmode` |

Example entry (key `0`):
```json
{"date": "06/19", "num": 0, "answer": "CIGAR",
 "cumulative": [0, 3, 26, 66, 91, 98],
 "individual": [0, 3, 23, 40, 25, 7],
 "sample": 1780105, "datestr": "061921"}
```

`hardmode` shape (when present):
```json
"hardmode": {"cumulative": [0, 1, 19, 63, 90, 97],
             "individual": [0, 1, 18, 44, 27, 7],
             "sample": 224075}
```

- Entries with `hardmode`: **686**, starting at key `1225` through `1936` (with gaps from missing keys).
- `cumulative` / `individual`: always `list[int]` length 6, `cumulative` is monotonic in all 1865 entries — OK.
- `sample`: int when present.

## 3. `answer` field

- All 1865 answers match `^[A-Z]{5}$` — OK, no lowercase / non-alpha / wrong length.
- Unique answers: **1839 / 1865**
- Duplicates: **26 answers × 2 occurrences each** (likely original list + reused/future list merged):

```
ACUTE, AGREE, AWAKE, BATON, BREAK, BRING, CIGAR, CLICK, CLOCK,
COMET, FEIGN, FLUME, FOCUS, FORTH, GRADE, GRIPE, IVORY, LINEN,
PROVE, SANDY, SMILE, SQUAD, STAND, STOUT, THUMB, TRACE
```

E.g. `CIGAR: keys 0 (06/19/21) and 1689 (02/02/26)`, `PROVE: keys 163 and 1936`.

- Top letters across all answers: E(1013), A(790), R(712), O(626), T(606), L(583), I(532), S(517), N(472), C(386) — normal English distribution.

## 4. Data-quality issues (must-fix before training/eval)

1. **Key `1502` — `num` mismatch (critical):**
   ```json
   {"date": "07/30", "num": 843, "answer": "ASSAY", ... "datestr": "073025"}
   ```
   Key says `1502`, field says `843`. Neighbours `1501 → num 1501`, `1503 → num 1503` are consistent. Treat key `1502` as suspect / drop or re-derive `num` from key.

2. **Key `625` (`PINKY`) missing `sample`.** All other non-hardmode entries have it.

3. **Key `1273` (`BOXER`) missing `datestr`, has `hardmode`.** Only entry with this combination.

4. **72 missing keys** (`552–619, 621–624`). If you need a contiguous daily sequence, this file alone is insufficient.

5. **26 duplicate answers.** For Wordle-as-game evaluation, deduplicate to 1839 unique or explicitly allow repeats with date handling.

## 5. Recommendations for this repo

- Current path `src/data/raw/` will be packaged if you build the wheel. Prefer repo-root `data/raw/` for the 395 KB raw dump, and keep only a small cleaned list (e.g. `answers.txt` / `wordle.json`) under `src/multi_agent_testing/data/` or `src/data/processed/` for runtime use.
- Cleaning pipeline (`src/data/processed/` is currently empty):
  1. Rename file → `wordlepuzzles.json`
  2. Validate with `^[A-Z]{5}$`, `len(cumulative)==6`, `num == int(key)`
  3. Emit `answers_unique.json` (1839) + `answers_all.json` (1865 with dates) depending on whether repeats are allowed
  4. Document handling of `1502`, `625`, `1273`, and the 72 gaps
- Do not index by position (`list(data.values())[n]`); always use explicit key/`num` because of gaps.

## 6. How this was checked

Parsed with `json.loads`, verified key contiguity `0..1936`, schema `Counter(tuple(sorted(keys)))`, regex `^[A-Z]{5}$`, `num == int(key)`, `len==6` int arrays, monotonic `cumulative`, `Counter(answer)` for duplicates.

## 7. Allowed guesses — `allowed_guesses.txt`

**File:** `src/data/raw/allowed_guesses.txt`
**Download / recorded date:** 2026-10-08 06:50:19 UTC
**Size:** 89,129 bytes, 14,855 lines (`wc -l` reports 14854 — file has no trailing newline)

### Checksums

```
SHA256: 9df5dad1b44cf1b9e0fa7c3ebff94d69ff7efb59f8691ac88e74e1c7b3da121e
MD5:    539de728911a6f6319faba3acc43417c
```

Verify with:

```bash
sha256sum src/data/raw/allowed_guesses.txt
md5sum src/data/raw/allowed_guesses.txt
wc -l -c src/data/raw/allowed_guesses.txt
```

### Diagnostic

- Encoding: valid UTF-8, LF only (no CRLF).
- Ends with newline: **no** — last line `jalap` is unterminated. Add `\n` on clean.
- Blank lines: 0. Lines with surrounding whitespace: 0.
- Format: **14,855 / 14,855 lines are lowercase `^[a-z]{5}$`** — 0 match `^[A-Z]{5}$`.
  - First 10: `rossa, jetty, wizzo, cuppa, cohoe, gurks, squad, beisa, shrug, fossa`
  - Last 10: `swami, tocky, femal, goary, waacs, dunny, decal, fungs, cadgy, jalap`
- Duplicates: 0 (14,855 unique / 14,855 total) — OK.
- Sorted: no.
- Overlap with `worldepuzzles.json` answers (1,839 unique, uppercase):
  - Case-sensitive `answers ∩ guesses`: **0** (expected — case mismatch).
  - Case-insensitive overlap should be re-checked after `.upper()` normalization (e.g. `squad` appears in both files).
  - **Action:** normalize with `word.strip().upper()` before comparing / validating guesses, and enforce `^[A-Z]{5}$` downstream.
- Top letters: E(7455), S(7319), A(7128), O(5212), R(4714) — normal.
- Recommendation: keep raw as-is for provenance; emit cleaned `allowed_guesses_upper.txt` (uppercased + trailing newline) to `src/data/processed/` for runtime use.
