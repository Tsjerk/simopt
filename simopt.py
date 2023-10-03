
"""

    SIMple OPTion parser for command line options.
    ^^^    ^^^
"""

__authors__ = ["Tsjerk A. Wassenaar"]
__year__ = 2014


# Read the version from a file to make sure 
# that it is consistent with the one in setup.py
import os
here = os.path.dirname(__file__)
try:
    with open(os.path.join(here, 'VERSION.txt')) as infile:
        __version__ = infile.readline().strip()
except:
    __version__ = "unknown"
del here
del os


import copy
import functools
import __main__ as main



MULTI = MU = 1
MANDATORY = MA = 2

class SimoptException(Exception):
    pass


class SimoptHelp(SimoptException):
    """
    Exception raised to signal that the user required the help with --help.
    """


class MissingMandatoryError(SimoptException):
    """
    Exception raised when a mandatory option is not provided.
    """
    def __init__(self, missing):
        self.missing = missing

    def __str__(self):
        msg = ["Mandatory options were missing from the command line:"]
        msg.extend(list(self.missing))
        msg.append("Run with option -h/--help to get the help.")
        return "\n".join(msg)


class Usage(SimoptException):
    def __init__(self, msg, program=getattr(main,"__file__",None)):
        if program:
            self.msg = "{}: {}\nTry '{} --help' for more information.".format(program, msg, program)
        else:
            self.msg = "Failed to parse options: {}".format(msg)

    def __str__(self):
        return self.msg


class Options:
    """
    A simple option parser.
    All options are registered in the list __options as tuples consisting of:

        LEVEL       - User level indicator for option
        OPTION      - Option name.
        ATTRIBUTE   - Attribute on this class through which the option is available.
        TYPE        - Type of the value(s).
        NUMBER      - Number of arguments for option.
        DEFAULT     - Default value. 'None' if no default.
        FLAGS       - Modify behaviour of option.
        DESCRIPTION - Description of the option.

    """

    def __init__(self, options, args=None):
        """Set up options object."""

        self.options = options

        # Make a dictionary from the option list
        self._optiondict = dict([option2tuple(i) for i in options if not type(i) == str])

        # Set the options as attributes of this object
        for opt in self._optiondict.values():
            setattr(self,opt[0],([] if not opt[3] else [opt[3]]) if (opt[4] & MULTI) else opt[3])

        # Parse the arguments, if given
        if args:
            self.parse(args)


    def _default_dict(self):
        """Return a dictionary with the default for each option."""
        options = {}
        for attr, _, _, default, multi, _ in self._optiondict.values():
            if multi and default is None:
                options[attr] = []
            else:
                options[attr] = default
        return options

    @property
    def mandatory_arguments(self):
        return set([opt
                    for opt, val
                    in self._optiondict.items()
                    if (val[4] & MANDATORY)])

    @property
    def mandatory_keys(self):
        return set([val[0]
                    for val in self._optiondict.values()
                    if val[4] & MANDATORY])

    def __str__(self):
        """Make a string from the option list.

        This method defines how the object looks like when converted to string.
        """
        return self.help(args=self.args)


    def help(self, args=None, userlevel=9):
        """Make a string from the option list"""
        out = [main.__file__+"\n"]

        if args is not None:
            parsed = self.parse(args, ignore_help=True)
        else:
            parsed = self._default_dict()

        for thing in self.options:
            if type(thing) == str:
                out.append("     "+thing)
            elif thing[0] <= userlevel:
                out.append("     %10s   %s ( %s )" % (thing[1], thing[-1], str(parsed[thing[2]])))

        return "\n".join(out)+"\n"


    def parse(self, args, ignore_help=False):
        """Parse the (command-line) arguments."""
        options = self._default_dict()

        seen = set()

        # Do not alter the arguments. We may need them later.
        args = copy.copy(args)
        while args:
            opt = args.pop(0)

            seen.add(opt)

            if opt in ("--help","-h"):
                if ignore_help:
                    continue
                raise SimoptHelp

            if not opt in self._optiondict:
                raise Usage("Unrecognized option '%s'"%opt)

            attr, typ, num, default, flags, description = self._optiondict[opt]

            if num > len(args):
                raise Usage("Option '%s' requires %d arguments"%(opt,num))

            if num:
                a = args.pop(0)
                try:
                    val = [typ(a) for i in range(num)]
                except ValueError:
                    raise Usage("Invalid argument to option '%s': %s"%(opt,repr(a)))
            else:
                # Boolean flag
                val = [True]

            if typ == bool:
                # A boolean option is simply set to True if given
                options[attr] = True
            elif flags & MULTI:
                # A multi-option adds an item or a tuple to the list
                options[attr] = options.get(attr, list())
                options[attr].append(val[0] if num == 1 else tuple(val))
            else:
                # Other options just set item or tuple
                options[attr] = val[0] if num == 1 else tuple(val)

        # All mandatory options should be seen
        missing = self.mandatory_arguments - seen
        if not ignore_help and missing:
            raise MissingMandatoryError(missing)

        return options


def option2tuple(opt):
    """Return a tuple of option, taking possible presence of level into account"""

    if isinstance(opt[0], int):
        tup = opt[1], opt[2:]
    else:
        tup = opt[0], opt[1:]

    return tup


def opt_func(options, check_mandatory=True):
    """
    Restore argument checks for functions that takes options dicts as arguments

    Functions that take the option dictionary produced by :meth:`Options.parse`
    as `kwargs` loose the argument checking usually performed by the python
    interpretor. They also loose the ability to take default values for
    their keyword arguments. Such function is basically unusable without the
    full dictionary produced by the option parser.

    This is a decorator that restores argument checking and default values
    assignment on the basis of an :class:`Options` instance.

        options = Options([
            (0, "-f", "input",    str, 1, None, MULTI, "Input file"),
            (0, "-o", "output",   str, 1, None,    MA, "Output file"),
            (0, "-p", "topology", str, 1, None,     0, "Optional topology"),
        ])

        @opt_func(options)
        def process_things(**arguments):
            # Do something
            return

        # The function can be called with the arguments
        # from the argument parser
        arguments = options.parse()
        process_things(**arguments)

        # It can be called with only part of the arguments,
        # the other arguments will be set to their default as defined by
        # the Options instance
        process_things(output='output.gro')

        # If the function is called with an unknown argument, the decorator
        # raises a TypeError
        process_things(unknown=None)

        # Likewise, if the function is called without the mandatory arguments,
        # the decorator raises a TypeError
        process_things(topology='topology.top')

        # The check for mandatory arguments can be deactivated
        @opt_func(options, check_mandatory=False)
        def process_things(**arguments):
            # Do things
            return

    Note that the decorator cannot be used on functions that accept Other
    arguments than the one defined in the :class:`Options` instance. Also, the
    arguments have to be given as keyword arguments. Positional arguments
    will cause the decorator to raise a `TypeError`.
    """
    # A function `my_function` decorated with `opt_func` is replaced by
    # `opt_func(options)(my_function)`. This is equivalent to
    # `validate_arguments(my_function)` using the `options` argument provided
    # to the decorator. A call to `my_function` results in a call to
    # `opt_func(options)(my_function)(*args, **kwargs)`
    # ^^^^^^^^^^^^^^^^^^ validate_arguments
    # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ wrap
    def validate_arguments(func):
        @functools.wraps(func)
        def wrap(*args, **kwargs):
            if args:
                raise TypeError('{0.__name__}() takes 0 positional arguments '
                                'but {1} was given'.format(func, len(args)))
            keys = set(kwargs.keys())
            missing = options.mandatory_keys - keys
            if missing and check_mandatory:
                raise TypeError('{0.__name__}() is missing the following '
                                'mandatory keyword arguments: {1}'
                                .format(func, ', '.join(missing)))
            arguments = options._default_dict()
            unknown = keys - set(arguments.keys())
            if unknown:
                raise TypeError('{0.__name__}() received the following '
                                'unexpected arguments: {1}'
                                .format(func, ', '.join(unknown)))
            arguments.update(**kwargs)
            return func(**arguments)
        return wrap
    return validate_arguments
