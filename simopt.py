"""
SIMple OPTion parser for command line options.
^^^ ^^^

simopt is a lightweight option parser built around a single principle: options
should be named, and the option list in the source should read like the help
text the program produces. It is designed for scientific computing scripts
where named options are strongly preferred over positional arguments, because
named invocations are self-documenting and reproducible.

The central object is :class:`Options`, which is constructed from a plain
Python list of tuples. Each tuple describes one command-line option; plain
strings in the list become section headers in the help output. The same list
that defines the parser *is* the help — no separate documentation step is
needed, and reading the source is equivalent to reading the output of --help.

Typical usage::

    import sys
    from simopt import Options, MANDATORY as MA, SimoptHelp, Usage, MissingMandatoryError

    options = [
        "Input/output",
        (0, "-f", "trajectory", str,   1, None, MA, "Input trajectory file"),
        (0, "-o", "output",     str,   1, "out", 0, "Output file prefix"),
        "Parameters",
        (0, "-dt", "timestep",  float, 1, 0.002, 0, "Time step (ps)"),
        (0, "-v",  "verbose",   bool,  0, False, 0, "Verbose output"),
    ]

    opt = Options(options)
    try:
        parsed = opt.parse(sys.argv[1:])
    except SimoptHelp:
        print(opt)
        sys.exit(0)
    except (MissingMandatoryError, Usage) as e:
        print(e)
        sys.exit(1)
"""

__authors__ = ["Tsjerk A. Wassenaar"]
__year__ = 2014

# Read the version from a file to make sure
# that it is consistent with the one in setup.py
import os
import copy
import functools
import __main__ as main

here = os.path.dirname(__file__)
try:
    with open(os.path.join(here, 'VERSION.txt'), encoding='UTF-8') as infile:
        __version__ = infile.readline().strip()
except FileNotFoundError:
    __version__ = "unknown"

del here
del os


# ---------------------------------------------------------------------------
# Option modifier flags
#
# These are bit flags that can be combined with | and tested with &.
# Short aliases (MU, MA) are provided to keep option lists compact and
# readable, paralleling the terse style of the option tuples themselves.
# ---------------------------------------------------------------------------

MULTI = MU = 1
"""Allow an option to appear more than once on the command line.

Each occurrence appends a value (or a tuple of values when nargs > 1) to a
list.  The default for a MULTI option should normally be None; the attribute
is initialised to an empty list when no default is given.
"""

MANDATORY = MA = 2
"""Require an option to be present on the command line.

If a MANDATORY option is absent, :class:`MissingMandatoryError` is raised
after all arguments have been processed, listing every missing flag together.
"""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SimoptException(Exception):
    """Base class for all simopt exceptions.

    Catching this class catches any error or signal raised by simopt,
    which is useful when you want uniform handling regardless of cause.
    """


class SimoptHelp(SimoptException):
    """Raised when the user passes ``-h`` or ``--help``.

    This is a signal, not an error.  The caller should print the help text
    and exit normally::

        try:
            parsed = opt.parse(sys.argv[1:])
        except SimoptHelp:
            print(opt)
            sys.exit(0)
    """


class MissingMandatoryError(SimoptException):
    """Raised when one or more mandatory options were not supplied.

    All missing options are collected before the exception is raised, so the
    user sees the complete list in a single message rather than one flag at
    a time.

    Attributes
    ----------
    missing : set
        The command-line flags (e.g. ``{"-f", "-o"}``) that were required
        but absent from the argument list.
    """

    def __init__(self, missing):
        self.missing = missing

    def __str__(self):
        msg = ["Mandatory options were missing from the command line:"]
        msg.extend(list(self.missing))
        msg.append("Run with option -h/--help to get the help.")
        return "\n".join(msg)


class Usage(SimoptException):
    """Raised when the command-line invocation is incorrect.

    Covers two cases:
    - an unrecognised flag was given, or
    - a recognised flag did not receive the expected number of arguments.

    The message includes the program name (taken from ``__main__.__file__``
    when available) and a hint to run with ``--help``.

    Parameters
    ----------
    msg : str
        A short description of what went wrong.
    program : str or None
        The program name to include in the error message.  Defaults to
        ``__main__.__file__`` so that scripts automatically get their own
        name in error output.
    """

    def __init__(self, msg, program=getattr(main, "__file__", None)):
        if program:
            self.msg = f"{program}: {msg}\nTry '{program} --help' for more information."
        else:
            self.msg = f"Failed to parse options: {msg}"

    def __str__(self):
        return self.msg


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------

class Options:
    """A named-option parser built from a plain Python list.

    The option list is the central artefact of simopt.  It is a plain Python
    list whose entries are either:

    - a ``str``, used as a section header in the help output, or
    - a ``tuple`` describing one command-line option.

    Option tuples have the following fields::

        (level, flag, attribute, type, nargs, default, flags, description)

    level
        ``int``.  Help verbosity level.  Options whose level exceeds the
        requested level are hidden from the help output.  Use 0 for options
        that should always be shown, and higher numbers for advanced or
        rarely-needed options.
    flag
        ``str``.  The command-line flag, e.g. ``"-f"`` or ``"--file"``.
    attribute
        ``str``.  The key under which the parsed value appears in the dict
        returned by :meth:`parse`.
    type
        ``callable``.  Applied to each raw argument string to produce a typed
        value.  Any callable that takes a single string is valid — ``int``,
        ``float``, ``str``, or a custom converter.  Use ``bool`` for flags
        that take no argument (nargs must then be 0).
    nargs
        ``int``.  Number of argument strings consumed from the command line.
        Use 0 for boolean flags.
    default
        The value used when the option is absent.  Use ``None`` when there
        is no sensible default; ``None`` combined with ``MULTI`` initialises
        the attribute to an empty list.
    flags
        Bit field of modifier flags: ``MULTI`` and/or ``MANDATORY``,
        combined with ``|``.  Use ``0`` for no modifiers.
    description
        ``str``.  The help text shown next to the option.

    The ``level`` field may be omitted; the tuple then starts with ``flag``::

        ("-f", "trajectory", str, 1, None, MA, "Input trajectory file")

    Section headers (plain strings) in the option list are printed as-is in
    the help output, allowing related options to be visually grouped both in
    the source code and in the help text.

    Parameters
    ----------
    options : list or str
        The option list (a Python list of tuples and strings), a
        newline-delimited string of the same, or a path to a file containing
        the option definitions.
    args : list of str, optional
        If provided, :meth:`parse` is called immediately with these arguments
        and the result is stored in ``self.args``.

    Examples
    --------
    ::

        from simopt import Options, MULTI, MANDATORY as MA

        options = [
            "Input",
            (0, "-f", "input",  str, 1, None,  MA,   "Input file (required)"),
            (0, "-o", "output", str, 1, "out", 0,    "Output prefix"),
            "Parameters",
            (0, "-n", "count",  int, 1, 100,   0,    "Number of iterations"),
            (0, "-v", "verbose",bool,0, False, 0,    "Verbose output"),
        ]

        opt = Options(options)
        parsed = opt.parse(["-f", "data.xtc", "-n", "500"])
        # parsed == {"input": "data.xtc", "output": "out", "count": 500, "verbose": False}
    """

    def __init__(self, options, args=None):
        """Initialise the Options object and optionally parse arguments.

        Parameters
        ----------
        options : list, tuple, or str
            Option definitions.  Accepted forms:
            - A Python list (or tuple) of option tuples and section strings.
            - A newline-delimited string encoding the same.
            - A file path; the file is read and its lines used as entries.
        args : list of str, optional
            Command-line arguments to parse immediately.  When given,
            :meth:`parse` is called and its result stored in ``self.args``.

        Raises
        ------
        TypeError
            If ``options`` is not a list, tuple, string, or readable file path.
        """
        if isinstance(options, (list, tuple)):
            self.options = options[:]
        elif isinstance(options, str):
            if '\n' in options:
                # Treat as an inline multi-line string rather than a file path
                self.options = options.split('\n')
            else:
                try:
                    with open(options, encoding='UTF-8') as optfile:
                        self.options = optfile.readlines()
                except FileNotFoundError as exc:
                    raise TypeError('Invalid source for option list.') from exc
        else:
            raise TypeError('Invalid source for option list.')

        # Build a dict keyed by flag (e.g. "-f") for O(1) lookup during parsing.
        # String entries (section headers) are skipped.
        self._optiondict = dict([
            option2tuple(i) for i in options if not isinstance(i, str)
        ])

        # Initialise each option as an attribute on this object so that the
        # Options instance can be passed directly to functions that access
        # values as attributes rather than dict keys.
        for opt in self._optiondict.values():
            setattr(self, opt[0], ([] if not opt[3] else [opt[3]]) if (opt[4] & MULTI) else opt[3])

        # Optionally parse immediately if arguments were supplied
        self.args = None
        if args:
            self.parse(args)

    def default_dict(self):
        """Return a dict mapping each attribute name to its default value.

        For MULTI options with no default (default is None) the value is an
        empty list rather than None, consistent with the semantics of a
        repeatable option that has not been given.

        Returns
        -------
        dict
            ``{attribute: default}`` for every option in the option list.
        """
        options = {}
        for attr, _, _, default, multi, _ in self._optiondict.values():
            if multi and default is None:
                options[attr] = []
            else:
                options[attr] = default
        return options

    @property
    def mandatory_arguments(self):
        """The set of command-line flags that are marked MANDATORY.

        Returns
        -------
        set of str
            Flag strings (e.g. ``{"-f", "-o"}``) whose MANDATORY bit is set.
            Used by :meth:`parse` to check that every required option was seen.
        """
        return {
            opt
            for opt, val in self._optiondict.items()
            if val[4] & MANDATORY
        }

    @property
    def mandatory_keys(self):
        """The set of attribute names that correspond to MANDATORY options.

        Returns
        -------
        set of str
            Attribute names (e.g. ``{"input", "output"}``) whose MANDATORY
            bit is set.  Used by :func:`opt_func` to validate keyword
            arguments against the option definition.
        """
        return {
            val[0]
            for val in self._optiondict.values()
            if val[4] & MANDATORY
        }

    def __str__(self):
        """Return the help text for the current option list.

        Delegates to :meth:`help`.  When ``self.args`` is set (i.e. arguments
        were supplied at construction time), the help shows the parsed values
        rather than the defaults.
        """
        return self.help(args=self.args)

    def help(self, args=None, userlevel=9):
        """Format the option list as a human-readable help string.

        Section header strings are printed as-is (indented by one space).
        Each option tuple whose level does not exceed ``userlevel`` is printed
        as a line showing the flag, the description, and the current or
        default value in parentheses.

        Parameters
        ----------
        args : list of str, optional
            When given, the arguments are parsed (with help-raising suppressed)
            so that the help shows actual values rather than defaults.  This
            lets the user see what the program *would* use for each option
            given the arguments supplied so far.
        userlevel : int, optional
            Options whose level exceeds this value are omitted.  Defaults to
            9, which shows everything.

        Returns
        -------
        str
            The formatted help text, ready to print.
        """
        out = [main.__file__ + "\n"]

        if args is not None:
            parsed = self.parse(args, ignore_help=True)
        else:
            parsed = self.default_dict()

        for thing in self.options:
            if isinstance(thing, str):
                # Section header
                out.append(" " + thing)
            elif thing[0] <= userlevel:
                # Option line: flag, description, current/default value
                out.append(f"  {thing[1]:10} {thing[-1]} ( {parsed[thing[2]]} )")

        return "\n".join(out) + "\n"

    def parse(self, args, ignore_help=False):
        """Parse a list of command-line argument strings.

        Arguments are consumed left to right.  Each flag is looked up in the
        option dict; the appropriate number of following tokens is consumed
        and converted using the option's type callable.  The original list is
        not modified.

        Special cases:

        - ``-h`` / ``--help`` raises :class:`SimoptHelp` (unless
          ``ignore_help`` is True, in which case the flag is skipped).
        - Boolean options (``type == bool``, ``nargs == 0``) set the
          attribute to ``True`` without consuming any further tokens.
        - MULTI options append each occurrence to a list rather than
          overwriting.
        - When ``nargs > 1`` the values are stored as a tuple.

        Parameters
        ----------
        args : list of str
            The argument strings to parse, typically ``sys.argv[1:]`` or the
            portion after a subcommand name has been removed.
        ignore_help : bool, optional
            When True, ``-h``/``--help`` is silently skipped rather than
            raising :class:`SimoptHelp`.  Used internally by :meth:`help` to
            parse the argument list for display purposes without triggering
            the help signal.

        Returns
        -------
        dict
            ``{attribute: value}`` for every option, including those not
            present on the command line (which receive their default values).

        Raises
        ------
        SimoptHelp
            If ``-h`` or ``--help`` is encountered and ``ignore_help`` is
            False.
        Usage
            If an unrecognised flag is encountered, or a flag does not
            receive enough arguments, or a type conversion fails.
        MissingMandatoryError
            If any MANDATORY option was absent from the argument list.
        """
        options = self.default_dict()
        seen = set()

        # Work on a shallow copy so the caller's list is not modified.
        # The original may be needed for display purposes (e.g. self.args).
        args = copy.copy(args)

        while args:
            opt = args.pop(0)
            seen.add(opt)

            if opt in ("--help", "-h"):
                if ignore_help:
                    continue
                raise SimoptHelp

            if opt not in self._optiondict:
                raise Usage(f"Unrecognized option '{opt}'")

            attr, typ, num, default, flags, description = self._optiondict[opt]

            if num > len(args):
                raise Usage(f"Option '{opt}' requires {num} arguments")

            if num:
                # Consume the next token and apply the type converter.
                # For nargs > 1 the same converter is applied to each token
                # (multi-argument options with mixed types are not supported).
                a = args.pop(0)
                try:
                    val = [typ(a) for i in range(num)]
                except ValueError as exc:
                    raise Usage(f"Invalid argument to option '{opt}': {repr(a)}") from exc
            else:
                # Boolean flag: no argument consumed
                val = [True]

            if typ == bool:
                # Boolean options are simply set to True; the default (False)
                # is already in place from default_dict().
                options[attr] = True
            elif flags & MULTI:
                # Repeatable option: accumulate into a list.
                # Single-argument options append the value directly;
                # multi-argument options append a tuple.
                options[attr] = options.get(attr, [])
                options[attr].append(val[0] if num == 1 else tuple(val))
            else:
                # Standard option: last occurrence wins.
                options[attr] = val[0] if num == 1 else tuple(val)

        # Check that every mandatory flag was seen at least once.
        # We collect all missing flags before raising so the user sees
        # the complete list in one message.
        missing = self.mandatory_arguments - seen
        if not ignore_help and missing:
            raise MissingMandatoryError(missing)

        return options


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def option2tuple(opt):
    """Normalise an option tuple, handling the optional leading level field.

    Option tuples may include an integer level as their first element, or
    omit it (in which case the level defaults to 0 implicitly via the caller).
    This function returns a ``(flag, rest)`` pair suitable for building the
    option dict, regardless of which form was used.

    Parameters
    ----------
    opt : tuple
        An option tuple in either the full form
        ``(level, flag, attribute, type, nargs, default, flags, description)``
        or the short form
        ``(flag, attribute, type, nargs, default, flags, description)``.

    Returns
    -------
    tuple
        ``(flag, (attribute, type, nargs, default, flags, description))``
        — the flag as the key and the remaining fields as the value.
    """
    if isinstance(opt[0], int):
        # Full form: level is present, flag is opt[1]
        tup = opt[1], opt[2:]
    else:
        # Short form: no level, flag is opt[0]
        tup = opt[0], opt[1:]
    return tup


def opt_func(options, check_mandatory=True):
    """Decorator that restores argument checking for option-dict functions.

    Functions that accept the dict produced by :meth:`Options.parse` as
    ``**kwargs`` lose Python's normal argument checking: unknown keys pass
    silently, mandatory keys can be absent, and defaults are not applied.
    This decorator restores all three behaviours using the :class:`Options`
    instance as the authoritative definition.

    When a decorated function is called:

    1. Positional arguments are rejected (all arguments must be keyword).
    2. Mandatory keys (options marked :data:`MANDATORY`) must be present,
       unless ``check_mandatory=False``.
    3. Unknown keys (not present in the option definition) raise TypeError.
    4. Missing optional keys are filled in from the option defaults.

    Parameters
    ----------
    options : Options
        The option definition to validate against.
    check_mandatory : bool, optional
        When False, missing mandatory keys do not raise an error.  Useful
        for functions that are called in contexts where not all options are
        relevant.

    Returns
    -------
    callable
        A decorator that wraps a ``**kwargs`` function with the checks above.

    Notes
    -----
    The decorated function must accept only keyword arguments that correspond
    to attributes defined in ``options``.  It cannot accept positional
    arguments or ``**kwargs`` beyond the option set.

    Examples
    --------
    ::

        options = Options([
            (0, "-f", "input",    str, 1, None, MULTI|MA, "Input file"),
            (0, "-o", "output",   str, 1, None, MA,       "Output file"),
            (0, "-p", "topology", str, 1, None, 0,        "Optional topology"),
        ])

        @opt_func(options)
        def process(**arguments):
            print(arguments["input"], arguments["output"])

        # Calling with a fully parsed dict works as expected:
        process(**options.parse(sys.argv[1:]))

        # Calling with only some arguments fills in the rest from defaults:
        process(input=["data.xtc"], output="result.dat")

        # Passing an unknown key raises TypeError:
        process(input=["data.xtc"], output="result.dat", unknown=True)  # TypeError

        # Omitting a mandatory key raises TypeError (when check_mandatory=True):
        process(topology="top.tpr")  # TypeError
    """
    # opt_func is a decorator factory: it returns a decorator (validate_arguments)
    # that in turn wraps the user's function (wrap).
    #
    # Call chain:
    #   @opt_func(options)          → calls opt_func → returns validate_arguments
    #   def process(**arguments):   → validate_arguments(process) → returns wrap
    #   process(output="x")         → calls wrap → fills defaults → calls process

    def validate_arguments(func):
        @functools.wraps(func)
        def wrap(*args, **kwargs):
            if args:
                raise TypeError(
                    f'{func.__name__}() takes 0 positional arguments '
                    f'but {len(args)} were given'
                )

            keys = set(kwargs.keys())

            # Check mandatory keys are present
            missing = options.mandatory_keys - keys
            if missing and check_mandatory:
                raise TypeError(
                    f'{func.__name__}() is missing the following '
                    f'mandatory keyword arguments: {", ".join(missing)}'
                )

            # Start from defaults so that unspecified optional keys are present
            arguments = options.default_dict()

            # Reject keys that are not part of the option definition
            unknown = keys - set(arguments.keys())
            if unknown:
                raise TypeError(
                    f'{func.__name__}() received the following '
                    f'unexpected keyword arguments: {", ".join(unknown)}'
                )

            arguments.update(**kwargs)
            return func(**arguments)

        return wrap

    return validate_arguments
