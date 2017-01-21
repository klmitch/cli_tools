# Copyright (C) 2013, 2014, 2017 by Kevin L. Mitchell <klmitch@mit.edu>
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import argparse
import inspect
import sys

import pkg_resources
import six


__all__ = ['console', 'prog', 'usage', 'description', 'epilog',
           'formatter_class', 'argument', 'argument_group',
           'mutually_exclusive_group', 'subparsers', 'load_subcommands']


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


def expose(func):
    """
    A decorator for ``ScriptAdaptor`` methods.  Methods so decorated
    will be exposed on the function decorated by ``cli_tools``.  This
    has no effect on classes decorated by ``cli_tools``.

    :param func: The function to expose.

    :returns: The function.
    """

    # Just set the expose attribute on the function.
    func._cli_expose = True
    return func


class ScriptAdaptorMeta(type):
    """
    A metaclass for ``ScriptAdaptor``.  This builds a list of the
    names of methods that have been decorated with ``@expose``.  This
    is used to copy the exposed methods onto a decorated function.
    """

    def __new__(mcs, name, bases, namespace):
        """
        Create the ``ScriptAdaptor`` class.  This ensures that an
        ``exposed`` class attribute is set to the set of method names
        that should be exposed on a decorated function.

        :param name: The class name.
        :param bases: A tuple of the base classes.
        :param namespace: A dictionary containing the class namespace.

        :returns: The constructed class.
        """

        # Build up the set of exposed method names
        exposed = set()
        for name, value in namespace.items():
            if callable(value) and getattr(value, '_cli_expose', False):
                exposed.add(name)
        namespace['exposed'] = exposed

        # Construct and return the class
        return super(ScriptAdaptorMeta, mcs).__new__(mcs, name, bases,
                                                     namespace)


@six.add_metaclass(ScriptAdaptorMeta)
class ScriptAdaptor(object):
    """
    An adaptor for the function.  Keeps track of the declared command
    line arguments and includes methods for declaring processors and
    calling the function from the console.
    """

    @classmethod
    def _get_adaptor(cls, func):
        """
        Gets the ``ScriptAdaptor`` for a function.

        :param func: The function to obtain the ``ScriptAdaptor`` of.

        :returns: The ``ScriptAdaptor``.
        """

        # Get the adaptor, creating one if necessary
        adaptor = getattr(func, 'cli_tools', None)
        if adaptor is None:
            is_class = inspect.isclass(func)

            adaptor = cls(func, is_class)
            func.cli_tools = adaptor

            # Set up the added functions
            if not is_class:
                for meth in cls.exposed:
                    setattr(func, meth, getattr(adaptor, meth))

        return adaptor

    def __init__(self, func, is_class=None):
        """
        Initialize a ``ScriptAdaptor``.

        :param func: The underlying function.
        :param is_class: A boolean specifying whether the ``func`` is
                         actually a class.
        """

        self._func = func
        self._is_class = (is_class if is_class is not None
                          else inspect.isclass(func))
        self._run = 'run' if self._is_class else None
        self._args_hook = lambda x: None
        self._processor = lambda x: None
        self._arguments = []
        self._groups = {}
        self._subcommands = {}
        self._entrypoints = set()
        self.do_subs = False
        self.subkwargs = {}
        self.prog = None
        self.usage = None
        self.description = _clean_text(func.__doc__)
        self.epilog = None
        self.formatter_class = argparse.HelpFormatter

        # This will be an attribute name for the adaptor implementing
        # the subcommand; this allows for the potential of arbitrary
        # depth on subcommands
        self._subcmd_attr = '_script_adaptor_%x' % id(self)

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

    def _add_subcommand(self, name, adaptor):
        """
        Add a subcommand to the parser.

        :param name: The name of the command to be added.
        :param adaptor: The corresponding ScriptAdaptor instance.
        """

        self._subcommands[name] = adaptor
        self.do_subs = True

    def _add_extensions(self, group):
        """
        Adds extensions to the parser.  This will cause a walk of a
        ``pkg_resources`` entrypoint group, adding each discovered
        function that has an attached ScriptAdaptor instance as a
        subcommand.  This walk is performed immediately prior to
        building the subcommand processor.  Note that no attempt is
        made to avoid duplication of subcommands.

        :param group: The entrypoint group name.
        """

        self._entrypoints.add(group)

        # We are now in subparsers mode
        self.do_subs = True

    def _process_entrypoints(self):
        """
        Perform a walk of all entrypoint groups declared using
        ``_add_extensions()``.  This is called immediately prior to
        building the subcommand processor.
        """

        # Walk the set of all declared entrypoints
        for group in self._entrypoints:
            for ep in pkg_resources.iter_entry_points(group):
                try:
                    func = ep.load()
                    self._add_subcommand(ep.name, func.cli_tools)
                except (ImportError, AttributeError,
                        pkg_resources.UnknownExtra):
                    # Ignore any expected errors
                    pass

        # We've processed these entrypoints; avoid double-processing
        self._entrypoints = set()

    @expose
    def args_hook(self, func):
        """
        Sets a hook for constructing the arguments.  This hook could
        be used to allow, for instance, a set of authentication
        plugins to add their configuration options to the argument
        parser.  This method may be used as a decorator, e.g.:

            @console
            def func():
                pass

            @func.args_hook
            def _hook(parser):
                pass

        If the hook is a regular function, it will be called after
        processing all of the regular argument specifications.

        If the hook is a generator, the segment before the first
        ``yield`` statement will be executed before adding any regular
        argument specifications, and the remainder will be executed
        afterward.

        :param func: The function to be installed as an argument hook.

        :returns: The function, allowing this method to be used as a
                  decorator.
        """

        self._args_hook = func
        return func

    @expose
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

    @expose
    def subcommand(self, name=None):
        """
        Decorator used to mark another function as a subcommand of
        this function.  If ``function()`` is the parent function, this
        decorator can be used in any of the following ways:

            @function.subcommand('spam')
            def foo():
                pass

            @function.subcommand()
            def bar():
                pass

            @function.subcommand
            def baz():
                pass

        In the first case, the command name is set explicitly.  In the
        latter two cases, the command name is the function name.

        :param name: If a string, gives the name of the subcommand.
                     If a callable, specifies the function being added
                     as a subcommand.  If not specified, a decorator
                     will be returned which will derive the name from
                     the function.

        :returns: If ``name`` was a callable, it will be returned.
                  Otherwise, returns a callable which takes a callable
                  as an argument and returns that callable, to conform
                  with the decorator syntax.
        """

        def decorator(func):
            cmdname = name or func.__name__
            adaptor = self._get_adaptor(func)
            self._add_subcommand(cmdname, adaptor)
            return func

        # If we were passed a callable, we were used without
        # parentheses, and will derive the command name from the
        # function...
        if callable(name):
            func = name
            name = None
            return decorator(func)

        return decorator

    @expose
    def setup_args(self, parser):
        """
        Set up an ``argparse.ArgumentParser`` object by adding all the
        arguments taken by the function.  This is available to allow
        other users access to the argument specifications.

        :param parser: An ``argparse.ArgumentParser`` object, or any
                       related object having an ``add_argument()``
                       method.
        """

        # Run the args hook, if it's a generator
        post = self._args_hook
        if inspect.isgeneratorfunction(self._args_hook):
            post = self._args_hook(parser)
            try:
                six.next(post)
            except StopIteration:
                # Won't be doing any post-processing anyway
                post = None

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
                    continue  # pragma: no cover

                # Set up all the arguments
                for a_args, a_kwargs in arguments:
                    group.add_argument(*a_args, **a_kwargs)

        # If we have subcommands, set up the parser appropriately
        if self.do_subs:
            self._process_entrypoints()
            subparsers = parser.add_subparsers(**self.subkwargs)
            for cmd, adaptor in self._subcommands.items():
                cmd_parser = subparsers.add_parser(
                    cmd,
                    prog=adaptor.prog,
                    usage=adaptor.usage,
                    description=adaptor.description,
                    epilog=adaptor.epilog,
                    formatter_class=adaptor.formatter_class,
                )
                adaptor.setup_args(cmd_parser)

                # Remember which adaptor implements the subcommand
                defaults = {self._subcmd_attr: adaptor}
                cmd_parser.set_defaults(**defaults)

        # If the hook has a post phase, run it
        if post:
            if inspect.isgenerator(post):
                try:
                    six.next(post)
                except StopIteration:
                    pass
                post.close()
            else:
                post(parser)

    @expose
    def get_kwargs(self, func, args=None):
        """
        Given an ``argparse.Namespace``, as produced by
        ``argparse.ArgumentParser.parse_args()``, determines the
        keyword arguments to pass to the specified function.  Note
        that an ``AttributeError`` exception will be raised if any
        argument required by the function is not set in ``args``.

        :param func: A callable to introspect.
        :param args: A ``argparse.Namespace`` object containing the
                     argument values.

        :returns: A dictionary containing the keyword arguments to be
                  passed to the underlying function.
        """

        # For backwards compatibility, handle the case when we were
        # called with only one argument
        if args is None:
            args = func
            func = self._func

        # Get the argument spec for the correct underlying function
        if inspect.isclass(func):
            try:
                # Try __new__() first; this will raise a TypeError if
                # __new__() hasn't been overridden
                argspec = inspect.getargspec(func.__new__)
                ismethod = True
            except TypeError:
                try:
                    # OK, no __new__(); try __init__()
                    argspec = inspect.getargspec(func.__init__)
                    ismethod = True
                except TypeError:
                    # OK, no __init__(); that means that the class
                    # initializer takes no arguments
                    argspec = inspect.ArgSpec([], None, None, None)
                    ismethod = False
        else:
            argspec = inspect.getargspec(func)
            ismethod = inspect.ismethod(func)

        # We need to figure out which arguments the final function
        # actually needs
        kwargs = {}
        req_args = (argspec.args[:-len(argspec.defaults)]
                    if argspec.defaults else argspec.args)
        required = set(req_args[1:] if ismethod else req_args)
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

    @expose
    def safe_call(self, args):
        """
        Call the processor and the underlying function.  If the
        ``debug`` attribute of ``args`` exists and is ``True``, any
        exceptions raised by the underlying function will be
        re-raised.

        :param args: This should be an ``argparse.Namespace`` object;
                     the keyword arguments for the function will be
                     derived from it.

        :returns: A tuple of the function return value and exception
                  information.  Only one of these values will be
                  non-``None``.
        """

        # Run the processor
        post = None
        if inspect.isgeneratorfunction(self._processor):
            post = self._processor(args)
            try:
                six.next(post)
            except StopIteration:
                # Won't be doing any post-processing anyway
                post = None
        else:
            self._processor(args)

        # Initialize the results
        result = None
        exc_info = None

        try:
            # Call the function
            result = self._func(**self.get_kwargs(self._func, args))
        except Exception:
            if args and getattr(args, 'debug', False):
                # Re-raise if desired
                raise
            exc_info = sys.exc_info()

        if self._is_class:
            # All we've done so far is initialize the class; now we
            # need to actually run it
            try:
                meth = getattr(result, self._run)
                result = meth(**self.get_kwargs(meth, args))
            except Exception:
                if args and getattr(args, 'debug', False):
                    # Re-raise if desired
                    raise
                result = None  # must clear result
                exc_info = sys.exc_info()

        # If the processor has a post phase, run it
        if post:
            try:
                if exc_info:
                    # Overwrite the result and exception information
                    result = post.throw(*exc_info)
                    exc_info = None
                else:
                    result = post.send(result)
            except StopIteration:
                # No result replacement...
                pass
            except Exception:
                # Overwrite the result and exception information
                exc_info = sys.exc_info()
                result = None

            post.close()

        return result, exc_info

    @expose
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

        # Get the adaptor
        if self.do_subs:
            # If the subcommand attribute isn't set, we'll call our
            # underlying function
            adaptor = getattr(args, self._subcmd_attr, self)
        else:
            adaptor = self

        # Call the function
        result, exc_info = adaptor.safe_call(args)

        if exc_info:
            return str(exc_info[1])
        return result

    @expose
    def get_subcommands(self):
        """
        Retrieve a dictionary of the recognized subcommands.

        :returns: A dictionary mapping subcommand names to the
                  implementing functions.
        """

        # We only have a return value if we're in subparsers mode
        if not self.do_subs:
            return {}

        # Process any declared entrypoints
        self._process_entrypoints()

        # Return the subcommands dictionary
        return dict((k, v._func) for k, v in self._subcommands.items())


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
        adaptor.usage = text
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
        adaptor.description = text
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
        adaptor.epilog = text
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


def subparsers(**kwargs):
    """
    Decorator used to specify alternate keyword arguments to pass to
    the ``argparse.ArgumentParser.add_subparsers()`` call.
    """

    def decorator(func):
        adaptor = ScriptAdaptor._get_adaptor(func)
        adaptor.subkwargs = kwargs
        adaptor.do_subs = True
        return func
    return decorator


def load_subcommands(group):
    """
    Decorator used to load subcommands from a given ``pkg_resources``
    entrypoint group.  Each function must be appropriately decorated
    with the ``cli_tools`` decorators to be considered an extension.

    :param group: The name of the ``pkg_resources`` entrypoint group.
    """

    def decorator(func):
        adaptor = ScriptAdaptor._get_adaptor(func)
        adaptor._add_extensions(group)
        return func
    return decorator
