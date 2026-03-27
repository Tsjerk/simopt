# simopt — SIMple OPTion parser

`simopt` is a lightweight Python module for parsing command-line options in
scientific programs. It is built around a single design principle: **options
should be named, and the option list in the code should read like the help
text the program produces**.

---

## Motivation

In scientific computing programs or scripts may accept many parameters,
and positional order quickly becomes a liability. This contrasts with shell 
commands that are typically short and meaning is obvious from context. 
Therefore, scientific command-line programs should prefer the use of 
named arguments. 

A recorded invocation thatreads

```
run_analysis.py trajectory.xtc topology.tpr 0.35 1200 42
```

is opaque. An invocation that reads

```
run_analysis.py -f trajectory.xtc -s topology.tpr -cutoff 0.35 -nsteps 1200 -seed 42
```

is self-documenting. It can be copied into a lab notebook, a methods section,
or a Makefile and remain unambiguous. This is the convention established by
tools like GROMACS, and it is the convention `simopt` is built to support.

The second motivation is readability of the source code itself. With most
option-parsing libraries the option definitions are scattered through setup
code, and you have to run the program with `-h` to understand what it accepts.
With `simopt` the option list sits at the top of a script as a plain Python
list. Reading the source and reading the help output are the same act.

---

## Installation

```bash
pip install simopt
```

Or simply copy `simopt.py` into your project — it has no dependencies beyond
the Python standard library.

---

## Quick start

```python
import sys
from simopt import Options, MULTI, MANDATORY as MA

options = [
    "Input/output",
    (0, "-f",      "trajectory", str,   1, None,  MA,    "Input trajectory file"),
    (0, "-s",      "topology",   str,   1, None,  MA,    "Input topology file"),
    (0, "-o",      "output",     str,   1, "out", 0,     "Output file"),
    "Analysis parameters",
    (0, "-cutoff", "cutoff",     float, 1, 0.35,  0,     "Distance cutoff (nm)"),
    (0, "-nsteps", "nsteps",     int,   1, 1000,  0,     "Number of steps"),
    (0, "-v",      "verbose",    bool,  0, False, 0,     "Verbose output"),
]

opt = Options(options, sys.argv[1:])
parsed = opt.parse(sys.argv[1:])

print(parsed["trajectory"])
print(parsed["cutoff"])
```

Running with `-h` or `--help` prints the option list, formatted with the
section headers and current (or default) values shown inline.

---

## The option list format

Each entry in the option list is either a plain string (used as a section
header in the help output) or a tuple describing one option:

```
(level, flag, attribute, type, nargs, default, flags, description)
```

| Field         | Type       | Description |
|---------------|------------|-------------|
| `level`       | `int`      | Help level. Options with a high level are hidden from basic `-h` output. |
| `flag`        | `str`      | The command-line flag, e.g. `"-f"` or `"--file"`. |
| `attribute`   | `str`      | Key used in the returned options dict. |
| `type`        | `callable` | Called on each raw string argument to produce a typed value. Use `bool` for flags that take no argument. |
| `nargs`       | `int`      | Number of arguments consumed. `0` for boolean flags. |
| `default`     | `object`   | Default value, or `None` if there is no default. |
| `flags`       | `int`      | Modifier flags: `MULTI` (option may appear more than once) and/or `MANDATORY`. |
| `description` | `str`      | Help text shown next to the option. |

The `level` field may be omitted, in which case the tuple starts with `flag`:

```python
("-f", "trajectory", str, 1, None, MA, "Input trajectory file")
```

---

## Modifier flags

Two modifier flags are available and can be combined with `|`:

```python
from simopt import MULTI, MANDATORY
# or their short aliases:
from simopt import MU, MA
```

`MANDATORY` — the option must be present on the command line. If it is
missing, a `MissingMandatoryError` is raised with a clear message listing
what was absent.

`MULTI` — the option may appear more than once. Each occurrence appends a
value (or tuple of values, if `nargs > 1`) to a list. The default for a
`MULTI` option should normally be `None`; the attribute will be initialised
to an empty list.

```python
(0, "-f", "input_files", str, 1, None, MULTI|MA, "Input file (repeatable)")
```

---

## Boolean flags

Set `type` to `bool` and `nargs` to `0`. The attribute is set to `True`
whenever the flag appears on the command line.

```python
(0, "-v", "verbose", bool, 0, False, 0, "Enable verbose output")
```

---

## Section headers

Plain strings in the option list become section headers in the help output.
They cost nothing in terms of parsing and make both the source and the help
legible at a glance:

```python
options = [
    "Input",
    (0, "-f", "trajectory", str, 1, None, MA, "Trajectory file"),
    (0, "-s", "topology",   str, 1, None, MA, "Topology file"),
    "Output",
    (0, "-o", "output",     str, 1, "out", 0, "Output prefix"),
    "Parameters",
    (0, "-dt", "timestep",  float, 1, 0.002, 0, "Time step (ps)"),
]
```

---

## Leveled help

The `level` field controls which options appear in the help at a given
verbosity level. A program can expose only its essential options by default
and reveal advanced tuning options when the user explicitly requests them.
This is useful for scripts that have accumulated many options over time
without burdening new users with all of them at once.

---

## Reading options from a file

The `Options` constructor accepts a file path as well as a list:

```python
opt = Options("myprogram.options")
```

Each line of the file is treated as an entry. This allows option definitions
to be shared across multiple scripts or maintained separately from the code.

---

## The `opt_func` decorator

`opt_func` is a decorator that restores Python's normal argument checking for
functions that accept an options dict as `**kwargs`. Without it, passing a
dict of keyword arguments bypasses the interpreter's checks for missing or
unknown arguments. The decorator uses the `Options` instance to enforce that:

- only known keys are passed,
- all mandatory keys are present, and
- default values are injected for any optional keys that were omitted.

```python
from simopt import Options, opt_func, MANDATORY as MA

options = Options([
    (0, "-f", "input",    str, 1, None,  MA, "Input file"),
    (0, "-o", "output",   str, 1, None,  MA, "Output file"),
    (0, "-p", "topology", str, 1, None,  0,  "Optional topology"),
])

@opt_func(options)
def process(**arguments):
    print(arguments["input"], arguments["output"])

# Call with a fully parsed dict
parsed = options.parse(sys.argv[1:])
process(**parsed)

# Or call directly, supplying only what you need —
# defaults are filled in automatically
process(input="traj.xtc", output="result.dat")
```

By default `opt_func` enforces mandatory arguments. This can be turned off:

```python
@opt_func(options, check_mandatory=False)
def process(**arguments):
    ...
```

Note that `opt_func` only works with keyword arguments. Positional arguments
will raise a `TypeError`.

---

## Subcommands

For programs that expose multiple subcommands (in the style of `gmx mdrun`,
`git commit`, etc.), `simopt` composes naturally with a thin dispatcher. Each
subcommand is its own scope with its own option list. The dispatcher reads the
first argument, selects the corresponding `Options` object, and hands off:

```python
import sys
from simopt import Options, MANDATORY as MA

# --- subcommand definitions -------------------------------------------

run_options = [
    "Simulation options",
    (0, "-f",      "mdp",        str,   1, None,  MA, "Input parameter file (.mdp)"),
    (0, "-c",      "coordinates",str,   1, None,  MA, "Input coordinates"),
    (0, "-nsteps", "nsteps",     int,   1, 1000,  0,  "Number of steps"),
]

analyze_options = [
    "Analysis options",
    (0, "-f",     "trajectory",  str,   1, None,  MA, "Input trajectory"),
    (0, "-o",     "output",      str,   1, "out", 0,  "Output file prefix"),
    (0, "-cutoff","cutoff",      float, 1, 0.35,  0,  "Distance cutoff (nm)"),
]

subcommands = {
    "run":     (run_options,     "Run a simulation"),
    "analyze": (analyze_options, "Analyse a trajectory"),
}

# --- dispatcher -------------------------------------------------------

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(f"Usage: myprog <subcommand> [options]\n")
        print("Subcommands:")
        for name, (_, description) in subcommands.items():
            print(f"  {name:12} {description}")
        return

    subcmd = sys.argv[1]
    if subcmd not in subcommands:
        print(f"Unknown subcommand '{subcmd}'. Run with -h for help.")
        sys.exit(1)

    opt_list, _ = subcommands[subcmd]
    opt = Options(opt_list)
    parsed = opt.parse(sys.argv[2:])
    # dispatch to the appropriate function ...

if __name__ == "__main__":
    main()
```

Each subcommand is entirely self-contained. There are no shared option lists
to merge and no parser state to coordinate between subcommands.

---

## Exceptions

| Exception               | Raised when |
|-------------------------|-------------|
| `SimoptHelp`            | The user passes `-h` or `--help`. |
| `MissingMandatoryError` | One or more mandatory options were not supplied. Provides a clear list of what was missing. |
| `Usage`                 | An unrecognised option was given, or an option received the wrong number of arguments. |

A typical invocation pattern:

```python
import sys
from simopt import Options, SimoptHelp, MissingMandatoryError, Usage

opt = Options(options)
try:
    parsed = opt.parse(sys.argv[1:])
except SimoptHelp:
    print(opt)
    sys.exit(0)
except (MissingMandatoryError, Usage) as e:
    print(e)
    sys.exit(1)
```

---

## Design notes

`simopt` deliberately does not support positional arguments. In scientific
computing, named options are strongly preferable because they make invocations
self-documenting and reproducible. A command line recorded in a notebook or a
methods section should be unambiguous without reference to argument order.

The library also makes no attempt to be a framework. It does one thing — parse
a named option list — and stays out of the way. The option list is plain Python
data, which means it can be read, written, passed around, and inspected without
any library involvement. The help output is a direct rendering of that same
data, so reading the source and reading the help are equivalent acts.

---

## License

MIT. See `LICENSE` for details.
