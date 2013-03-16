============================
Command Line Interface Tools
============================

The command line interface tools module provides several decorators
which can be applied to a regular function to turn it into a console
script.  It is designed to adapt a function so that it can be used as
a ``console_scripts`` entrypoint.  The decorators allow various
command line arguments to be declared, and for the command line to be
parsed using the ``argparse`` module; the results of the parsing are
then passed to the function as regular keyword arguments.  This does
not interfere with the normal calling conventions of the function; it
can be called from Python code directly.

Simple usage of ``cli_tools``
=============================

The simplest example of using the ``cli_tools`` decorators is as
follows::

    from cli_tools import *

    @console
    def function():
        """
        Performs an action.
        """
        ...

In this declaration, the function is defined as taking no arguments
(except ``argparse``'s default of "--help").  The description of the
resulting script will be "Performs an action."

To declare this as an actual console script, the following clause will
need to be added to the ``setup()`` call in your setup.py::

    entry_points={
        'console_scripts': [
            'function = your_module:function.console',
        ],
    }

Notice in particular the ".console" appended to the function name.
The decorators add several attributes to the function, including the
callable ``console()``, which performs the actual command line
argument parsing.

The above example is the simplest example, but it would be more
interesting with some defined arguments::

    @argument('--debug', '-d',
              dest='debug',
              action='store_true',
              default=False,
              help="Run the tool in debug mode.")
    @argument('--dryrun', '--dry_run', '--dry-run', '-n',
              dest='dry_run',
              action='store_true',
              default=False,
              help="Perform a dry run.")
    def function(dry_run=False):
        """
        Performs an action.
        """
        ...

The first thing to notice is the elimination of the ``@console``
decorator.  It doesn't hurt anything to use ``@console``, but all the
decorators perform the same core actions; as long as one of the other
decorators is used, ``@console`` is unnecessary.

The second thing to notice is that the ``dest`` specified for the
"--dryrun" option matches the only function argument.  When run as a
console script, the value computed from the command line arguments
will be passed as this keyword parameter.

The third thing to notice is that the ``dest`` specified for the
"--debug" option matches no function arguments.  That flag will simply
not be passed to the function.

(As it happens, the ``debug`` argument is treated specially.  Under
normal circumstances, if the function raises an exception, the
exception is coerced to a string, printed to standard error, and then
the console script exits.  If the ``debug`` argument is ``True``,
however, the exception will not be caught, resulting in a print out of
the stack trace.)

Getting a Little More Advanced: Set the Description
===================================================

By default, the first paragraph of the function docstring becomes the
description for the console script, which is printed out when the
"--help" option is given.  This and several other ``argparse`` options
may be overridden using the following decorators:

@prog()
  Overrides the ``prog`` parameter passed to
  ``argparse.ArgumentParser``.  By default, it will be ``None``,
  causing the program name to be derived from ``sys.argv[0]``.

@usage()
  Overrides the ``usage`` parameter passed to
  ``argparse.ArgumentParser``.  By default, it will be ``None``,
  causing the usage message to be automatically computed by
  ``argparse``.

@description()
  Overrides the ``description`` parameter passed to
  ``argparse.ArgumentParser``.  By default, it will be the first
  paragraph of the function docstring.

@epilog()
  Overrides the ``epilog`` parameter passed to
  ``argparse.ArgumentParser``.  By default, it will be ``None``; when
  given, the text will be output at the end of the help text.

@formatter_class()
  Overrides the ``formatter_class`` parameter passed to
  ``argparse.ArgumentParser``.  By default, it will be
  ``argparse.HelpFormatter``.  See the ``argparse`` documentation for
  more details.

Getting More Advanced: Argument Groups
======================================

The ``argparse`` package provides the ability to group arguments.
There are two ways of grouping arguments; in the first, related
arguments are simply grouped together so their documentation is more
easily found, while in the second, a group of arguments are identified
as mutually exclusive.  The ``cli_tools`` decorators accommodate this
by adding a special ``group`` parameter to the ``@argument()``
decorator; this group name identifies a group added using the
``@argument_group()`` or ``@mutually_exclusive_group()`` decorators,
and must be unique.  These latter two decorators take the group name
as the first argument, and remaining keyword arguments are passed to
the underlying ``argparse.ArgumentParser.add_argument_group()`` and
``argparse.ArgumentParser.add_mutually_exclusive_group()`` methods.

Argument Declaration Order
==========================

Arguments and groups are constructed in the order in which they appear
in the file; that is, in the earlier example, the "--debug" option
will be added to the argument parser before the "--dryrun" option.
This is opposite the normal decorator rules, but simplifies setting up
the arguments, particularly positional arguments.

Processors
==========

Some functions can't act as stand-alone console scripts without some
sort of setup.  For instance, it may be necessary to configure
logging.  This can be handled by declaring a processor::

    @console
    def function():
        """
        Performs an action.
        """
        ...

    @function.processor
    def _processor(args):
        logging.basicConfig()

Here we declare the function ``_processor()`` as a processor for the
console script ``function()``.  After the command line arguments are
parsed, ``_processor()`` will be called with those arguments; after it
returns, ``function()`` will be called.

It is also possible to perform actions after the function returns.
Consider the following example::

    @console
    def function():
        """
        Performs an action.
        """
        ...
        return result

    @function.processor
    def _processor(args):
        result = yield
        print result
        yield None

Here we turn ``_processor()`` into a generator; the result of the
first ``yield`` statement is the return value of ``function()``, which
we can see will be whatever result it computed.  Thus,
``_processor()`` will print out that result, then yield ``None``--this
is needed so that the script exits without any errors; a non-``None``
value is interpreted as an error condition by the machinery
surrounding the ``console_scripts`` endpoint.

Generator-based processors also receive any exceptions thrown by the
function, like so::

    class BailoutException(Exception):
        pass

    @console
    def function():
        """
        Performs an action.
        """
        ...
        raise BailoutException("I'm done")

    @function.processor
    def _processor(args):
        try:
            result = yield
        except BailoutException:
            print "All done!"
        else:
            print "Results so far: %s" % result
        yield None

Note the ``try`` block around the first ``yield``, which allows the
processor function to catch this special exception and do something
appropriate.

Advanced ``cli_tools`` Usage
============================

The ``console()`` function added to the decorated function uses
several other functions for setting up the argument parser
(``setup_args()``), building the keyword arguments to pass to the
underlying function (``get_kwargs()``), and safely calling the
function and handling exceptions (``safe_call()``).  These functions
are provided to allow other consumers to make use of the argument
information.  This could be used to build a "Swiss army knife" command
interpreter, for instance.
