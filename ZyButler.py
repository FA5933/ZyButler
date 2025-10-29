#Auth:  Faris Maksoud
#Date Created:  4/12/22
#Date Modified: 10/28/25
#Desc:  Build and execute a zybot command from user-provided variables and Polarion STTL block.

from __future__ import annotations
from dataclasses import dataclass
import sys
import re
import argparse
import logging
import subprocess
import os
from typing import List, Tuple, Optional, Sequence
import shlex

# Import colorama for cross-platform coloring (assumes colorama installed)
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except ImportError:  # graceful fallback if unexpectedly missing
    class _Dummy:
        def __getattr__(self, _):
            return ''
    Fore = Style = _Dummy()  # type: ignore
    def colorama_init(*args, **kwargs):  # type: ignore
        pass

# ---------------- Constants / Patterns ----------------

STTL_BLOCK_PATTERN = re.compile(r'^id:\((.*)\)$', re.IGNORECASE)
TOKEN_PATTERN = re.compile(r'^STTL/STTL-(\d+)$')
DUT_KEY_PATTERN = re.compile(r'^DUT(\d+)$', re.IGNORECASE)
VAR_PAIR_PATTERN = re.compile(r'^[A-Za-z0-9_]+:[^\s]+$')
ALLOWED_NON_DUT_KEYS = {"TESTDIR"}
MIN_SERIAL_LEN = 10  # minimum length for DUT serial validation (now alphanumeric)
EXECUTION_DIR = r"C:\RFS_CI\GIT_REPO\ST_Master\mcd_validation_RFS\RFS"  # Required working directory for zybot execution
# Default zybot base command token used if no custom path supplied
#DEFAULT_ZYBOT_TOKEN = "zybot"

# ---------------- Color / Formatting Helpers ----------------

# Detailed help text. Shows examples for variables, alphanumeric serials, STTL block, path, and color overrides.
FORMAT_HELP = (
    "User Input Format Guide:\n"
    "  Variables:\n"
    "    Use space-separated KEY:VALUE tokens.\n"
    "    DUTn:<serial> where n starts at 1. Serial must be alphanumeric length >= 10.\n"
    "    Optional flags like TESTDIR:TRUE are allowed.\n"
    "    Example: DUT1:ABC1234567 TESTDIR:TRUE\n"
    "  Multiple DUTs:\n"
    "    Example: DUT1:ABC1234567 DUT2:ZX9QWERTYU\n"
    "  STTL Block:\n"
    "    Single line: id:(STTL/STTL-<id> STTL/STTL-<id> ...)\n"
    "    Numeric IDs only; duplicates ignored.\n"
    "    Example: id:(STTL/STTL-238897 STTL/STTL-127394)\n"
    "  Path:\n"
    "    Optional filesystem path to test cases appended at end of command.\n"
    "  Color Control:\n"
    "    Set NO_COLOR=1 to disable ANSI entirely.\n"
    "    Set FORCE_COLOR=1 to force color (will try enabling Windows ANSI).\n"
    "  Execution Directory Requirement:\n"
    f"    Script executes zybot command from: {EXECUTION_DIR}\n"
    "  Command Construction:\n"
    "    Each STTL id expands to -t \"STTL-<id>*\" automatically. Do NOT add quotes or * yourself.\n"
    "  Additional Flags:\n"
    "    Provide generic zybot flags via --flag (CLI) or interactive entry, e.g.:\n"
    "      --flag '-L TRACE' --flag '--dryrun'\n"
    "    Each --flag string is tokenized similar to a shell (quote as needed).\n"
    "    Disallowed inside --flag: -v / -t (handled separately).\n"
    "  CLI Arguments:\n"
    "    --var KEY:VALUE        Repeatable; adds a variable (e.g. --var DUT1:ABC1234567)\n"
    "    --flag FLAG_STRING     Repeatable; adds raw zybot flag tokens (e.g. --flag '-L TRACE')\n"
    "    --sttl-block STRING    Direct STTL block text (id:(STTL/STTL-123 ...))\n"
    "    --sttl-file PATH       Read STTL block from a file (exclusive with --sttl-block)\n"
    "    --path PATH            Optional test case path appended to command\n"
    "    --execute              Run zybot after displaying command\n"
    "    --pretty               Show formatted summary before/with command\n"
    "    --no-color             Disable ANSI color output\n"
    "    --verbose / -V         Debug-level logging\n"
    "    --show-formats         Print this format help and exit\n"
    #"    --zybot-path PATH      (Reserved) Custom zybot executable/script path (currently not executed)\n"
    "  Output Examples:\n"
    "    zybot -v DUT1:ABC1234567 -t \"STTL-238897*\"\n"
    "    zybot --flag '-L TRACE' -v DUT1:ABC1234567 -v DUT2:ZX9QWERTYU -t \"STTL-238897*\" -t \"STTL-127394*\" Tests\\Regression\n"
)

RESET = Style.RESET_ALL
BOLD = Style.BRIGHT
DIM = Style.DIM
# Foreground colors
CYAN = Fore.CYAN
MAGENTA = Fore.MAGENTA
GREEN = Fore.GREEN
YELLOW = Fore.YELLOW
RED = Fore.RED

_def_use_color = True


# ---------------- Exceptions ----------------

class ParseError(ValueError):
    pass

class ValidationError(ValueError):
    pass


def supports_color() -> bool:
    if os.environ.get('NO_COLOR'):
        return False
    # Require TTY unless FORCE_COLOR specified
    if not sys.stdout.isatty() and not os.environ.get('FORCE_COLOR'):
        return False
    return True

def color(txt: str, *codes: str) -> str:
    if not _def_use_color:
        return txt
    return ''.join(codes) + txt + RESET

def hr(char: str = '-', width: int = 60) -> str:
    return char * width

def print_format_help():
    print(color(hr(), CYAN))
    for line in FORMAT_HELP.splitlines():
        if line.strip():
            print(color(line, CYAN))
    print(color(hr(), CYAN))

# ---------------- Dataclass ----------------

@dataclass
class ZybotCommand:
    vars: List[Tuple[str, str]]
    sttls: List[str]
    path: Optional[str] = None
    flags: List[str] = None  # raw additional flags (each element is one argument token)

    def build_args(self) -> List[str]:
        args: List[str] = ["zybot"]
        if self.flags:
            args.extend(self.flags)
        for k, v in self.vars:
            args.extend(["-v", f"{k}:{v}"])
        for sid in self.sttls:
            args.extend(["-t", f"{sid}*"])  # raw arg; quoting added for display only
        if self.path:
            args.append(self.path)
        return args

    def display_command(self) -> str:
        raw = self.build_args()
        disp: List[str] = []
        i = 0
        while i < len(raw):
            token = raw[i]
            disp.append(token)
            if token == "-t" and i + 1 < len(raw):
                pattern = raw[i + 1]
                disp.append(f'"{pattern}"')
                i += 2
                continue
            i += 1
        return " ".join(disp)

    def pretty(self) -> str:
        lines: List[str] = []
        lines.append(color('=== Zybot Command Summary ===', CYAN))
        lines.append(color(f'Script Execution Directory:', BOLD, GREEN))
        lines.append(color(EXECUTION_DIR, BOLD))
        if self.flags:
            lines.append(color('Flags:', BOLD, GREEN))
            lines.append('  ' + ' '.join(self.flags))
        else:
            lines.append(color('Flags: (none)', DIM))
        if self.vars:
            lines.append(color('Variables:', BOLD, GREEN))
            for k, v in self.vars:
                lines.append(f'  {color(k, BOLD)}: {v}')
        else:
            lines.append(color('Variables: (none)', DIM))
        if self.sttls:
            lines.append(color(f'STTL IDs ({len(self.sttls)}):', BOLD, GREEN))
            for sid in self.sttls[:25]:
                lines.append(color(f'  {sid}', BOLD))
            if len(self.sttls) > 25:
                lines.append(color(f'  ... ({len(self.sttls) - 25} more)', BOLD))
        else:
            lines.append(color('STTL IDs: (none)', DIM))
        if self.path:
            lines.append(color(f'Test Script Path: {self.path}', BOLD, GREEN))
            lines.append(color(self.path, BOLD))
        else:
            lines.append(color('Path: (none)', DIM))

        lines.append(color('Full Command:', BOLD, GREEN))
        cmd = self.display_command()
        if len(cmd) <= 100:
            lines.append(color(f'  {cmd}', BOLD))
        else:
            current = '  '
            for part in cmd.split():
                if len(current) + len(part) + 1 > 100:
                    lines.append(current.rstrip())
                    current = '  ' + part + ' '
                else:
                    current += part + ' '
            if current.strip():
                lines.append(current.rstrip())
        lines.append(color(hr(), DIM))
        return '\n'.join(lines)

# ---------------- Parsing Helpers ----------------

def parse_sttl_block(raw: str) -> List[str]:
    raw = raw.strip()
    m = STTL_BLOCK_PATTERN.match(raw)
    if not m:
        raise ParseError("STTL block must match id:(STTL/STTL-<id> ...)")
    body = m.group(1).strip()
    if not body:
        raise ParseError("STTL block empty")
    tokens = body.split()
    seen = set()
    ordered: List[str] = []
    for tok in tokens:
        tm = TOKEN_PATTERN.match(tok)
        if not tm:
            raise ParseError(f"Malformed STTL token: {tok}")
        sid = f"STTL-{tm.group(1)}"
        if sid in seen:
            continue
        seen.add(sid)
        ordered.append(sid)
    if not ordered:
        raise ParseError("No valid STTL tokens parsed")
    return ordered

def normalize_key(key: str) -> str:
    return key.upper()

def parse_vars(raw_tokens: Sequence[str], allow_empty: bool = False) -> List[Tuple[str, str]]:
    if not raw_tokens:
        if allow_empty:
            return []
        raise ValidationError("No variables provided")
    pairs: List[Tuple[str, str]] = []
    for kv in raw_tokens:
        if not VAR_PAIR_PATTERN.match(kv):
            raise ValidationError(f"Invalid KEY:VALUE format: {kv}")
        key, value = kv.split(":", 1)
        key_u = normalize_key(key)
        if DUT_KEY_PATTERN.match(key_u):
            # Accept alphanumeric serials; enforce length only
            if (not value.isalnum()) or len(value) < MIN_SERIAL_LEN:
                raise ValidationError(
                    f"Invalid DUT serial for {key}: must be alphanumeric length >= {MIN_SERIAL_LEN}"
                )
        elif key_u not in ALLOWED_NON_DUT_KEYS:
            raise ValidationError(f"Unknown variable key: {key}")
        pairs.append((key_u, value))
    return pairs

def parse_flags(flag_specs: Sequence[str]) -> List[str]:
    """Expand repeated --flag specifications into individual argument tokens.
    Each spec can contain one or multiple tokens (e.g. "-L TRACE" or "--dryrun").
    Validation: Disallow -v and -t tokens here (they belong to variables / STTL IDs)."""
    tokens: List[str] = []
    for spec in flag_specs:
        if not spec.strip():
            continue
        split = shlex.split(spec)
        for tok in split:
            if tok in {"-v", "-t"}:
                raise ValidationError(f"Disallowed token in --flag specification: {tok}")
            tokens.append(tok)
    return tokens

# ---------------- Unified Build Function ----------------

def build_command(vars_tokens: Sequence[str], sttl_block: str, path: Optional[str], allow_empty_vars: bool = False, flags: Optional[Sequence[str]] = None) -> ZybotCommand:
    vars_list = parse_vars(vars_tokens, allow_empty=allow_empty_vars)
    sttls = parse_sttl_block(sttl_block)
    flag_tokens = parse_flags(flags or [])
    return ZybotCommand(vars=vars_list, sttls=sttls, path=path or None, flags=flag_tokens)

# --------------- Zybot Executable Resolution ---------------

def execute(command: ZybotCommand) -> int:
    """
    Simplified execution:
    1. cd to required directory.
    2. Run the full zybot command string exactly as displayed.
    Note: zybot_path ignored; always uses the command built by command.display_command().
    """
    if not os.path.isdir(EXECUTION_DIR):
        logging.error("Execution directory missing: %s", EXECUTION_DIR)
        return 5
    prev_cwd = os.getcwd()
    try:
        if prev_cwd != EXECUTION_DIR:
            os.chdir(EXECUTION_DIR)
            logging.debug("Changed working directory to %s", EXECUTION_DIR)
        cmd_str = command.display_command()
        logging.info("Executing: %s", cmd_str)
        # Use shell to allow quoted -t arguments to be passed intact.
        return subprocess.call(cmd_str, shell=True)
    except OSError as e:
        logging.error("Failed to execute in %s: %s", EXECUTION_DIR, e)
        return 5
    finally:
        try:
            if os.getcwd() != prev_cwd:
                os.chdir(prev_cwd)
                logging.debug("Restored working directory to %s", prev_cwd)
        except OSError:
            pass

# ---------------- Interactive Menu Flow ----------------

def interactive_menu() -> int:
    global _def_use_color
    _def_use_color = supports_color()
    while True:
        print(color('ZyButler', CYAN))
        print(color(hr(), DIM))
        print(color('Select components to provide (enter ? for format help):', CYAN))
        print('  1) Variables + STTL + Path (full)')
        print('  2) STTL only')
        print('  3) Variables + STTL (no path)')
        print('  4) Variables only')
        print('  5) STTL + Path')
        print('  0) Quit')
        print('  ?) Show format help')
        choice = input(color('Enter choice: ', BOLD)).strip()
        if choice == '?':
            print_format_help()
            continue
        if choice == '0':
            print(color('Goodbye.', GREEN))
            return 0
        need_vars = choice in {'1','3','4'}
        need_sttl = choice in {'1','2','3','5'}
        need_path = choice in {'1','5'}
        if not need_vars and not need_sttl and not need_path:
            logging.error('Invalid choice.')
            continue

        vars_tokens: List[str] = []
        if need_vars:
            print(color('\nEnter variables (space-separated KEY:VALUE e.g. DUT1:12345678EE90) or Enter for none:', CYAN))
            vars_input = input().strip()
            vars_tokens = vars_input.split() if vars_input else []
            try:
                vars_list = parse_vars(vars_tokens, allow_empty=True)
            except ValidationError as e:
                logging.error("Variable error: %s", e)
                continue
        else:
            vars_list = []

        sttls: List[str] = []
        if need_sttl:
            print(color('\nPaste STTL block (id:(STTL/STTL-...)):', CYAN))
            sttl_raw = input().strip()
            try:
                sttls = parse_sttl_block(sttl_raw)
            except ParseError as e:
                logging.error("STTL error: %s", e)
                continue
        else:
            sttls = []

        path: Optional[str] = None
        if need_path:
            print(color('\nEnter path (or Enter to skip):', CYAN))
            path_in = input().strip()
            path = path_in or None

        # Flags entry
        flags: List[str] = []
        flag_raw = input(color('\nEnter additional flags (e.g. -L TRACE --dryrun) or Enter for none: ', CYAN)).strip()
        if flag_raw:
            try:
                flags = parse_flags([flag_raw])
            except ValidationError as e:
                logging.error("Flag error: %s", e)
                continue
        # Ask optionally for custom zybot path
        #custom_tool = input(color(f"\nOptional custom zybot path (Enter to use '{DEFAULT_ZYBOT_TOKEN}'): ", BOLD)).strip() or None

        command = ZybotCommand(vars=vars_list, sttls=sttls, path=path, flags=flags)
        print('\n' + command.pretty())
        exec_ans = input(color(f"\nExecute now from {EXECUTION_DIR}? (y/N): ", BOLD)).strip().lower()
        if exec_ans == 'y':
            #rc = execute(command, custom_tool)
            rc = execute(command)
            if rc != 0:
                logging.error("Execution failed with code %s", rc)
            else:
                print(color('Execution completed.', BOLD, GREEN))
        again = input(color('\nGenerate another command? (y/N): ', BOLD)).strip().lower()
        if again != 'y':
            print(color('Goodbye.', GREEN))
            return 0
    # Explicit return to satisfy static analysis (loop guarantees earlier returns)
    return 0

# ---------------- CLI Parsing ----------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="ZyButler (simplified)")
    p.add_argument("--var", action="append", metavar="KEY:VALUE", help="Add variable KEY:VALUE (repeatable)")
    p.add_argument("--flag", action="append", metavar="FLAG", help="Additional zybot flag (repeatable). Example: --flag '-L TRACE' --flag '--dryrun'")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--sttl-block", help="STTL block string: id:(STTL/STTL-123 STTL/STTL-456)")
    group.add_argument("--sttl-file", help="File containing single STTL block line")
    p.add_argument("--path", help="Optional test path")
    p.add_argument("--execute", action="store_true", help="Run zybot after building command (from required repo directory)")
    p.add_argument("--pretty", action="store_true", help="Pretty formatted output")
    p.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    p.add_argument("--verbose", "-V", action="store_true", help="Verbose logging")
    p.add_argument("--show-formats", action="store_true", help="Print accepted input format examples and exit")
    #p.add_argument("--zybot-path", help="Full path to zybot executable or Python script (optional)")
    return p

# ---------------- Main Flow ----------------

def cli(argv: List[str]) -> int:
    if not argv:
        return interactive_menu()
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format='[%(levelname)s] %(message)s')

    global _def_use_color
    _def_use_color = supports_color() and not args.no_color

    if args.show_formats:
        print_format_help()
        return 0

    if not args.var:
        logging.error("At least one --var KEY:VALUE required")
        return 3
    try:
        vs = parse_vars(args.var or [], allow_empty=False)
    except ValidationError as e:
        logging.error("Variable error: %s", e)
        return 3
    try:
        flag_tokens = parse_flags(args.flag or [])
    except ValidationError as e:
        logging.error("Flag error: %s", e)
        return 3
    if args.sttl_block:
        sttl_source = args.sttl_block
    elif args.sttl_file:
        try:
            with open(args.sttl_file, 'r', encoding='utf-8') as f:
                sttl_source = f.read().strip()
        except OSError as e:
            logging.error("Failed reading STTL file: %s", e)
            return 2
    else:
        logging.error("Provide --sttl-block or --sttl-file")
        return 2

    try:
        sttls = parse_sttl_block(sttl_source)
    except ParseError as e:
        logging.error("STTL error: %s", e)
        return 2

    command = ZybotCommand(vars=vs, sttls=sttls, path=args.path, flags=flag_tokens)
    if args.pretty:
        print(command.pretty())
        print(color('Full Command:', BOLD, YELLOW))
        print(color(command.display_command(), BOLD))
    else:
        print(command.display_command())

    if args.execute:
        #rc = execute(command, args.zybot_path)
        rc = execute(command)
        if rc != 0:
            logging.error("zybot exited with code %s", rc)
        return rc
    else:
        return 0

# ---------------- Entry Point ----------------

def main():
    try:
        exit_code = cli(sys.argv[1:])
    except KeyboardInterrupt:
        logging.error("Interrupted by user")
        exit_code = 130
    sys.exit(exit_code)

if __name__ == "__main__":
    main()

# --------------- Unit Tests (pytest) ---------------
# Tests are placed in a separate file (test_ZyButler.py).
