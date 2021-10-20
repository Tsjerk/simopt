# simopt, the SIMple OPTion parser

Simopt is a lightweight module for parsing command line options in python programs.
The options can be written in a separate file or at the top of a script. They are 
(currently) written in a list of tuples, with each entry corresponding to an option
consisting of 

- int: the option level (allowing differentiating help levels)
- str: the option name (command line)
- str: the option target (option class attribute)
- class: the option unit type (parser)
- int: the number of parameters for the option
- object: the default value (None if no default)
- int: flags (MULTI, MANDATORY, ...)
- str: description (help text)

String items in the option list are part of the help and allow sectioning 
options.

