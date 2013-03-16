## Copyright (C) 2013 by Kevin L. Mitchell <klmitch@mit.edu>
##
## This program is free software: you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation, either version 3 of the
## License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see
## <http://www.gnu.org/licenses/>.

import inspect
import sys

import argparse


__all__ = ['console', 'prog', 'usage', 'description', 'epilog',
           'formatter_class', 'argument', 'argument_group',
           'mutually_exclusive_group']


def _clean_text(text):
    """
    Clean up a multiple-line, potentially multiple-paragraph text
    string.  This is used to extract the first paragraph of a string
    and eliminate line breaks and indentation.  Lines will be joined
    together by a single space.

    :param text: The text string to clean up.  It is safe to pass
                 ``None``.

    :returns: The first paragraph, cleaned up as described above.
    """

    desc = []
    for line in (text or '').strip().split('\n'):
        # Clean up the line...
        line = line.strip()

        # We only want the first paragraph
        if not line:
            break

        desc.append(line)

    return ' '.join(desc)


class ScriptAdaptor(object):
    """
    An adaptor for the function.  Keeps track of the declared command
    line arguments and includes methods for declaring processors and
    calling the function from the console.
    """

    @classmethod
    def _get_adaptor(cls, func):
        """
        Gets the ScriptAdaptor for a function.

        :param func: The function to obtain the ScriptAdaptor of.

        :returns: The ScriptAdaptor.
        """

        # Get the adaptor, creating one if necessary
        adaptor = getattr(func, '_script_adaptor', None)
        if adaptor is None:
            adaptor = cls(func)
            func._script_adaptor = adaptor

            # Set up the added functions
            func.processor = adaptor.processor
            func.setup_args = adaptor.setup_args
            func.get_kwargs = adaptor.get_kwargs
            func.safe_call = adaptor.safe_call
            func.console = adaptor.console

        return adaptor

    def __init__(self, func):
        """
        Initialize a ScriptAdaptor.

        :param func: The underlying function.
        """

        self._func = func
        self._processor = lambda x: None
        self._arguments = []
        self._groups = {}
        self.prog = None
        self.usage = None
        self.description = _clean_text(func.__doc__)
        self.epilog = None
        self.formatter_class = argparse.HelpFormatter

    def _add_argument(self, args, kwargs, group):
        """
        Add an argument specification to the list of argument
        specifications.  The argument specification is inserted at the
        beginning of the list of argument specifications, so that the
        decorators may be added in natural order.

        :param args: The positional arguments of the argument
                     specification.
        :param kwargs: The keyword arguments of the argument
                       specification.
        :param group: An argument group name.  If provided, the
                      argument specification will be added to the
                      named group, rather than to the general list of
                      arguments.
        """

        if group:
            self._groups.setdefault(group, dict(arguments=[]))
            self._groups[group]['arguments'].insert(0, (args, kwargs))
        else:
            self._arguments.insert(0, ('argument', args, kwargs))

    def _add_group(self, group, type, kwargs):
        """
        Add an argument group specification to the list of argument
        specifications.  The group specification is inserted at the
        beginning of the list of argument specifications, so that the
        decorators may be added in natural order.

        :param group: The name of the argument group.  If the group is
                      already defined, an ``argparse.ArgumentError``
                      will be raised.
        :param type: Either "group" or "exclusive", depending on the
                     desired group type.
        :param kwargs: The keyword arguments of the group
                       specification.
        """

        # Make sure the group exists
        self._groups.setdefault(group, dict(arguments=[]))

        # Look out for the pre-existence of the group
        if 'type' in self._groups[group]:
            raise argparse.ArgumentError(None, "group %s: conflicting groups" %
                                         group)

        # Save the data
        self._groups[group]['type'] = type

        # Add the group to the argument specification list
        self._arguments.insert(0, ('group', group, kwargs))

    def processor(self, func):
        """
        Sets a processor for the underlying function.  A processor
        function runs before and potentially after the underlying
        function, but only when it is being called as a console
        script.  This method may be used as a decorator, e.g.:

            @console
            def func():
                pass

            @func.processor
            def _proc(args):
                pass

        If the processor is a regular function, it will be called just
        before the underlying function is called, and it will be
        passed the parsed arguments.

        If the processor is a generator, the segment before the first
        ``yield`` statement will be executed just before the
        underlying function is called.  The return result of the
        ``yield`` statement will be the return result of the
        underlying function, and if another value is ``yield``ed, that
        value will replace the return result for the purposes of the
        console script.

        :param func: The function to be installed as a processor.

        :returns: The function, allowing this method to be used as a
                  decorator.
        """

        self._processor = func
        return func

    def setup_args(self, parser):
        """
        Set up an ``argparse.ArgumentParser`` object by adding all the
        arguments taken by the function.  This is available to allow
        other users access to the argument specifications.

        :param parser: An ``argparse.ArgumentParser`` object, or any
                       related object having an ``add_argument()``
                       method.
        """

        for arg_type, args, kwargs in self._arguments:
            if arg_type == 'argument':
                parser.add_argument(*args, **kwargs)
            elif arg_type == 'group':
                # Get the group information
                arguments = self._groups[args]['arguments']
                type = self._groups[args]['type']

                # Create the group in the parser
                if type == 'group':
                    group = parser.add_argument_group(**kwargs)
                elif type == 'exclusive':
                    group = parser.add_mutually_exclusive_group(**kwargs)
                else:
                    # Huh, don't know that group...
                    continue  # Pragma: nocover

                # Set up all the arguments
                for a_args, a_kwargs in arguments:
                    group.add_argument(*a_args, **a_kwargs)

    def get_kwargs(self, args):
        """
        Given an ``argparse.Namespace``, as produced by
        ``argparse.ArgumentParser.parse_args()``, determines the
        keyword arguments to pass to the underlying function.  Note
        that an ``AttributeError`` exception will be raised if any
        argument required by the function is not set in ``args``.

        :param args: A ``argparse.Namespace`` object containing the
                     argument values.

        :returns: A dictionary containing the keyword arguments to be
                  passed to the underlying function.
        """

        # We need to figure out which arguments the final function
        # actually needs
        kwargs = {}
        argspec = inspect.getargspec(self._func)
        required = set(argspec.args[:-len(argspec.defaults)]
                       if argspec.defaults else argspec.args)
        for arg_name in argspec.args:
            try:
                kwargs[arg_name] = getattr(args, arg_name)
            except AttributeError:
                if arg_name in required:
                    # If this happens, that's a programming error
                    raise

        # If the function accepts any keyword argument, add whatever
        # remains
        if argspec.keywords:
            for key, value in args.__dict__.items():
                if key in kwargs:
                    # Already handled
                    continue
                kwargs[key] = value

        return kwargs

    def safe_call(self, kwargs, args=None):
        """
        Call the underlying function safely.  If successful, the
        function return value (likely ``None``) will be returned.  If
        the underlying function raises an exception, the return value
        will be the string value of the exception, unless an
        ``argparse.Namespace`` object defining a ``debug`` attribute
        of ``True`` is provided, in which case the exception will be
        re-raised.

        :param kwargs: A dictionary of keyword arguments to pass to
                       the underlying function.
        :param args: If provided, this should be an
                     ``argparse.Namespace`` object with a ``debug``
                     attribute set to a boolean value.

        :returns: A tuple of the function return value and exception
                  information.  Only one of these values will be
                  non-``None``.
        """

        try:
            return self._func(**kwargs), None
        except Exception:
            if args and getattr(args, 'debug', False):
                raise
            return None, sys.exc_info()

    def console(self, args=None, argv=None):
        """
        Call the function as a console script.  Command line arguments
        are parsed (unless ``args`` is passed), the processor (if any)
        is called, then the underlying function is called.  If a
        ``debug`` attribute is set by the command line arguments, and
        if it is ``True``, any exception raised by the underlying
        function will be re-raised; otherwise, the return value will
        be either the return value of the function or the string value
        of the exception (unless overwritten by the processor).

        :param args: If provided, should be an ``argparse.Namespace``
                     containing the required argument values for the
                     function.  This can be used to parse the
                     parameters separately.
        :param argv: If provided, should be a list of argument strings
                     to be parsed by the argument parser, in
                     preference to ``sys.argv[1:]``.

        :returns: The function return value, the string value of any
                  exception raised by the function, or a value yielded
                  by the processor to replace the function value.
        """

        # First, let's parse the arguments
        if not args:
            parser = argparse.ArgumentParser(
                prog=self.prog,
                usage=self.usage,
                description=self.description,
                epilog=self.epilog,
                formatter_class=self.formatter_class,
            )
            self.setup_args(parser)
            args = parser.parse_args(args=argv)

        # Next, let's run the processor
        post = None
        if inspect.isgeneratorfunction(self._processor):
            post = self._processor(args)
            try:
                post.next()
            except StopIteration:
                # Won't be any post-processing anyway
                post = None
        else:
            self._processor(args)

        # Call the function
        result, exc_info = self.safe_call(self.get_kwargs(args), args)

        # If the processor has a post phase, run it
        if post:
            try:
                if exc_info:
                    result = post.throw(*exc_info)
                else:
                    result = post.send(result)
            except StopIteration:
                # No result replacement...
                pass
            except Exception:
                exc_info = sys.exc_info()

            post.close()

        if exc_info:
            return str(exc_info[1])
        return result


def console(func):
    """
    Decorator to mark a script as a console script.  This decorator is
    optional, but can be used if no arguments other than the default
    ``argparse`` arguments (such as "--help") are specified.
    """

    # This will ensure that the ScriptAdaptor is attached to the
    # function
    ScriptAdaptor._get_adaptor(func)
    return func


def prog(text):
    """
    Decorator used to specify the program name for the console script
    help message.

    :param text: The text to use for the program name.
    """

    def decorator(func):
        adaptor = ScriptAdaptor._get_adaptor(func)
        adaptor.prog = text
        return func
    return decorator


def usage(text):
    """
    Decorator used to specify a usage string for the console script
    help message.

    :param text: The text to use for the usage.
    """

    def decorator(func):
        adaptor = ScriptAdaptor._get_adaptor(func)
        adaptor.usage = _clean_text(text)
        return func
    return decorator


def description(text):
    """
    Decorator used to specify a short description of the console
    script.  This can be used to override the default, which is
    derived from the docstring of the function.

    :param text: The text to use for the description.
    """

    def decorator(func):
        adaptor = ScriptAdaptor._get_adaptor(func)
        adaptor.description = _clean_text(text)
        return func
    return decorator


def epilog(text):
    """
    Decorator used to specify an epilog for the console script help
    message.

    :param text: The text to use for the epilog.
    """

    def decorator(func):
        adaptor = ScriptAdaptor._get_adaptor(func)
        adaptor.epilog = _clean_text(text)
        return func
    return decorator


def formatter_class(klass):
    """
    Decorator used to specify the formatter class for the console
    script.

    :param klass: The formatter class to use.
    """

    def decorator(func):
        adaptor = ScriptAdaptor._get_adaptor(func)
        adaptor.formatter_class = klass
        return func
    return decorator


def argument(*args, **kwargs):
    """
    Decorator used to specify an argument taken by the console script.
    Positional and keyword arguments have the same meaning as those
    given to ``argparse.ArgumentParser.add_argument()``.
    """

    def decorator(func):
        adaptor = ScriptAdaptor._get_adaptor(func)
        group = kwargs.pop('group', None)
        adaptor._add_argument(args, kwargs, group=group)
        return func
    return decorator


def argument_group(group, **kwargs):
    """
    Decorator used to specify an argument group.  Keyword arguments
    have the same meaning as those given to
    ``argparse.ArgumentParser.add_argument_group()``.

    Arguments may be placed in a given argument group by passing the
    ``group`` keyword argument to @argument().

    :param group: The name of the argument group.
    """

    def decorator(func):
        adaptor = ScriptAdaptor._get_adaptor(func)
        adaptor._add_group(group, 'group', kwargs)
        return func
    return decorator


def mutually_exclusive_group(group, **kwargs):
    """
    Decorator used to specify a mutually exclusive argument group.
    Keyword arguments have the same meaning as those given to
    ``argparse.ArgumentParser.add_mutually_exclusive_group()``.

    Arguments may be placed in a given argument group by passing the
    ``group`` keyword argument to @argument().

    :param group: The name of the argument group.
    """

    def decorator(func):
        adaptor = ScriptAdaptor._get_adaptor(func)
        adaptor._add_group(group, 'exclusive', kwargs)
        return func
    return decorator
