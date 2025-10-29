# ZyButler

ZyButler is a helper script that assembles and (optionally) executes a `zybot` command based on:
- Device variable definitions (e.g. DUT1:SERIAL)
- A Polarion STTL block containing one or more test IDs
- An optional test path
- Additional raw zybot flags

It supports both an interactive menu and full CLI mode.

## Key Features
- Interactive guided entry (variables, STTL block, path, flags)
- CLI invocation for automation / scripting
- Automatic parsing & validation of STTL block: `id:(STTL/STTL-123 STTL/STTL-456 ...)`
- Validation of DUT serials (alphanumeric, length >= 10)
- Duplicate STTL IDs automatically deduplicated
- Pretty formatted summary output (`--pretty`)
- Colorized logging (DEBUG dim cyan, INFO green, WARNING bold yellow, ERROR/CRITICAL bold red)
- ANSI color control via `--no-color`, `NO_COLOR`, and `FORCE_COLOR` environment variables

## Requirements
- Python 3.8+ (3.8 recommended to support `logging.basicConfig(force=True)`; script falls back gracefully on <3.8)
- `colorama` (optional; without it output is plain text)

Install colorama (if needed):
```
pip install colorama
```

## File Layout
```
ZyButler_v1/
  ZyButler.py
  README.md
```

## STTL Block Format
A single line beginning with `id:(` followed by one or more `STTL/STTL-<numeric>` tokens separated by spaces, ending with `)`.
Example:
```
id:(STTL/STTL-238897 STTL/STTL-127394 STTL/STTL-127394)
```
Resulting IDs used: `STTL-238897` and `STTL-127394` (duplicate removed).

## Variables Format
Space-separated `KEY:VALUE` tokens.
- DUTn:<serial> where n starts at 1 (DUT1, DUT2, ...)
- Serial must be alphanumeric and length >= 10
- Allowed non-DUT key: `TESTDIR`

Example:
```
DUT1:ABC1234567 DUT2:ZX9QWERTYU TESTDIR:TRUE
```

## Additional Flags
Use repeated `--flag` arguments. Each `--flag` string is shell-tokenized (respect quotes). Disallowed tokens here: `-v` and `-t` (they are auto-generated for variables and STTL IDs).

Examples:
```
--flag "-L TRACE" --flag "--dryrun"
```
Becomes arguments: `-L TRACE --dryrun`.

## Command Construction Rules
- Each STTL numeric id maps to: `-t "STTL-<id>*"` (the `*` wildcard is appended automatically)
- Each variable maps to: `-v KEY:VALUE`
- Path (if provided) is appended at the end
- Flags are inserted after the `zybot` executable and before variables

## Quick Start (Interactive)
From the script directory:
```
python ZyButler.py
```
Follow the prompts to build and optionally execute the command.

## Quick Start (CLI)
Basic example (build only):
```
python ZyButler.py --var DUT1:ABC1234567 --sttl-block "id:(STTL/STTL-238897 STTL/STTL-127394)"
```
Pretty summary and execute immediately:
```
python ZyButler.py --var DUT1:ABC1234567 --var DUT2:ZX9QWERTYU \
  --flag "-L TRACE" --sttl-block "id:(STTL/STTL-238897 STTL/STTL-127394)" \
  --path Tests\Regression --pretty --execute
```
Disable color:
```
python ZyButler.py --no-color ...
```
Force color even if stdout not a TTY (e.g. CI logs):
```
FORCE_COLOR=1 python ZyButler.py ...
```
(Windows CMD: `set FORCE_COLOR=1` first.)

## Environment Variables
- `NO_COLOR` (any value): disables all ANSI color
- `FORCE_COLOR` (any value): forces color even if not a TTY

## Exit Codes (Selected)
- 0: Success / command displayed (and optionally executed successfully)
- 2: STTL block or file error
- 3: Variable or flag validation error / missing required vars
- 5: Execution directory missing or execution failure
- 130: Interrupted by user (Ctrl+C)

## Logging & Color
Logging is initialized after color determination so `--no-color` or `NO_COLOR` removes all color from log messages. Errors and critical issues are bold red; warnings bold yellow; info green; debug dim cyan.

## Common Errors & Tips
- "STTL block must match id:(STTL/STTL-<id> ...)": Ensure the line starts with `id:(` and ends with `)` with proper token spacing.
- "Invalid DUT serial": Check alphanumeric constraint and length (>=10).
- "Unknown variable key": Only DUTn and TESTDIR are accepted currently.
- Use quotes around the entire STTL block argument when passing via `--sttl-block` to avoid shell splitting.

## Extending
Potential future enhancements:
- Support additional variable keys
- Add background color or style variations
- Integrate custom zybot path parameter
- Persist recent commands history

## License / Attribution
Internal utility script. Author: Faris Maksoud. Date Created: 2022-04-12.

## Disclaimer
This script assumes the required zybot executable is available in PATH and that the working directory `C:\RFS_CI\GIT_REPO\ST_Master\mcd_validation_RFS\RFS` exists and contains necessary test artifacts.

---
Feel free to submit improvements or request additional examples.

