
"""

    SIMple OPTion parser for command line options.
    ^^^    ^^^

    (c)2014 T.A. Wassenaar

"""

import copy
import __main__ as main


MULTI = M = 1
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

            attr, typ, num, default, multi, description = self._optiondict[opt]

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
            elif multi:
                # A multi-option adds an item or a tuple to the list
                options[attr] = options.get(attr, list())
                options[attr].append(val[0] if num == 1 else tuple(val))
            else:
                # Other options just set item or tuple
                options[attr] = val[0] if num == 1 else tuple(val)

        # All mandatory options should be seen
        mandatory = set([ opt 
                          for opt, val in self._optiondict.items() 
                          if (val[4] & MANDATORY)])
        if mandatory - seen:
            raise MissingMandatoryError

        return options


def option2tuple(opt):
    """Return a tuple of option, taking possible presence of level into account"""

    if isinstance(opt[0], int):
        tup = opt[1], opt[2:]
    else:
        tup = opt[0], opt[1:]

    return tup
