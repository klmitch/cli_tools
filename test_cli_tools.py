# Copyright (C) 2013, 2014 by Kevin L. Mitchell <klmitch@mit.edu>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see
# <http://www.gnu.org/licenses/>.

import argparse
import inspect
import unittest

import mock
import pkg_resources
import six

import cli_tools


class TestException(Exception):
    pass


class CleanTextTest(unittest.TestCase):
    def test_clean_text(self):
        text = """
            This is a\t
            test of the text cleaner.

            This won't be included.
        """

        result = cli_tools._clean_text(text)

        self.assertEqual(result, "This is a test of the text cleaner.")

    def test_clean_text_blank(self):
        result = cli_tools._clean_text(None)

        self.assertEqual(result, '')


class ExposeTest(unittest.TestCase):
    def test_basic(self):
        @cli_tools.expose
        def test_func():
            pass

        self.assertTrue(test_func._cli_expose)


class ScriptAdaptorMeta(unittest.TestCase):
    def test_new(self):
        class TestObject(object):
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        @six.add_metaclass(cli_tools.ScriptAdaptorMeta)
        class SAMTest(object):
            def test_func1(self):
                pass

            @cli_tools.expose
            def test_func2(self):
                pass

            def test_func3(self):
                pass

            @cli_tools.expose
            def test_func4(self):
                pass

            attr1 = TestObject()
            attr2 = TestObject(_cli_expose=False)
            attr3 = TestObject(_cli_expose=True)

        self.assertEqual(SAMTest.exposed, set(['test_func2', 'test_func4']))


class ScriptAdaptorTest(unittest.TestCase):
    @mock.patch('inspect.isclass', return_value=False)
    def test_get_adaptor_unset(self, mock_isclass):
        func = mock.Mock(__doc__='', cli_tools=None)

        result = cli_tools.ScriptAdaptor._get_adaptor(func)

        self.assertTrue(isinstance(result, cli_tools.ScriptAdaptor))
        self.assertEqual(func.cli_tools, result)
        self.assertEqual(func.args_hook, result.args_hook)
        self.assertEqual(func.processor, result.processor)
        self.assertEqual(func.subcommand, result.subcommand)
        self.assertEqual(func.setup_args, result.setup_args)
        self.assertEqual(func.get_kwargs, result.get_kwargs)
        self.assertEqual(func.safe_call, result.safe_call)
        self.assertEqual(func.console, result.console)
        self.assertEqual(func.get_subcommands, result.get_subcommands)
        mock_isclass.assert_called_once_with(func)

    @mock.patch('inspect.isclass', return_value=False)
    def test_get_adaptor_set(self, mock_isclass):
        func = mock.Mock(
            __doc__='',
            args_hook='args_hook',
            processor='processor',
            subcommand='subcommand',
            setup_args='setup_args',
            get_kwargs='get_kwargs',
            safe_call='safe_call',
            console='console',
            get_subcommands='get_subcommands',
        )
        sa = cli_tools.ScriptAdaptor(func, False)
        func.cli_tools = sa

        result = cli_tools.ScriptAdaptor._get_adaptor(func)

        self.assertEqual(result, sa)
        self.assertEqual(func.args_hook, 'args_hook')
        self.assertEqual(func.processor, 'processor')
        self.assertEqual(func.subcommand, 'subcommand')
        self.assertEqual(func.setup_args, 'setup_args')
        self.assertEqual(func.get_kwargs, 'get_kwargs')
        self.assertEqual(func.safe_call, 'safe_call')
        self.assertEqual(func.console, 'console')
        self.assertEqual(func.get_subcommands, 'get_subcommands')
        self.assertFalse(mock_isclass.called)

    @mock.patch('inspect.isclass', return_value=True)
    def test_get_adaptor_class(self, mock_isclass):
        func = mock.Mock(
            __doc__='',
            args_hook='args_hook',
            processor='processor',
            subcommand='subcommand',
            setup_args='setup_args',
            get_kwargs='get_kwargs',
            safe_call='safe_call',
            console='console',
            get_subcommands='get_subcommands',
            cli_tools=None,
        )

        result = cli_tools.ScriptAdaptor._get_adaptor(func)

        self.assertTrue(isinstance(result, cli_tools.ScriptAdaptor))
        self.assertEqual(func.args_hook, 'args_hook')
        self.assertEqual(func.processor, 'processor')
        self.assertEqual(func.subcommand, 'subcommand')
        self.assertEqual(func.setup_args, 'setup_args')
        self.assertEqual(func.get_kwargs, 'get_kwargs')
        self.assertEqual(func.safe_call, 'safe_call')
        self.assertEqual(func.console, 'console')
        self.assertEqual(func.get_subcommands, 'get_subcommands')
        mock_isclass.assert_called_once_with(func)

    @mock.patch('inspect.isclass', return_value=True)
    def test_init_notclass(self, mock_isclass):
        func = mock.Mock(__doc__="description")
        sa = cli_tools.ScriptAdaptor(func, False)

        self.assertEqual(sa._func, func)
        self.assertFalse(sa._is_class)
        self.assertEqual(sa._run, None)
        self.assertTrue(callable(sa._args_hook))
        self.assertEqual(sa._args_hook('foo'), None)
        self.assertTrue(callable(sa._processor))
        self.assertEqual(sa._processor('foo'), None)
        self.assertEqual(sa._arguments, [])
        self.assertEqual(sa._groups, {})
        self.assertEqual(sa._subcommands, {})
        self.assertEqual(sa._entrypoints, set())
        self.assertEqual(sa.do_subs, False)
        self.assertEqual(sa.subkwargs, {})
        self.assertEqual(sa.prog, None)
        self.assertEqual(sa.usage, None)
        self.assertEqual(sa.description, 'description')
        self.assertEqual(sa.epilog, None)
        self.assertEqual(sa.formatter_class, argparse.HelpFormatter)
        self.assertEqual(sa._subcmd_attr, '_script_adaptor_%x' % id(sa))
        self.assertFalse(mock_isclass.called)

    @mock.patch('inspect.isclass', return_value=False)
    def test_init_isclass(self, mock_isclass):
        func = mock.Mock(__doc__="description")
        sa = cli_tools.ScriptAdaptor(func, True)

        self.assertEqual(sa._func, func)
        self.assertTrue(sa._is_class)
        self.assertEqual(sa._run, 'run')
        self.assertTrue(callable(sa._args_hook))
        self.assertEqual(sa._args_hook('foo'), None)
        self.assertTrue(callable(sa._processor))
        self.assertEqual(sa._processor('foo'), None)
        self.assertEqual(sa._arguments, [])
        self.assertEqual(sa._groups, {})
        self.assertEqual(sa._subcommands, {})
        self.assertEqual(sa._entrypoints, set())
        self.assertEqual(sa.do_subs, False)
        self.assertEqual(sa.subkwargs, {})
        self.assertEqual(sa.prog, None)
        self.assertEqual(sa.usage, None)
        self.assertEqual(sa.description, 'description')
        self.assertEqual(sa.epilog, None)
        self.assertEqual(sa.formatter_class, argparse.HelpFormatter)
        self.assertEqual(sa._subcmd_attr, '_script_adaptor_%x' % id(sa))
        self.assertFalse(mock_isclass.called)

    @mock.patch('inspect.isclass', return_value=False)
    def test_init_discoverclass_false(self, mock_isclass):
        func = mock.Mock(__doc__="description")
        sa = cli_tools.ScriptAdaptor(func)

        self.assertEqual(sa._func, func)
        self.assertFalse(sa._is_class)
        self.assertEqual(sa._run, None)
        self.assertTrue(callable(sa._args_hook))
        self.assertEqual(sa._args_hook('foo'), None)
        self.assertTrue(callable(sa._processor))
        self.assertEqual(sa._processor('foo'), None)
        self.assertEqual(sa._arguments, [])
        self.assertEqual(sa._groups, {})
        self.assertEqual(sa._subcommands, {})
        self.assertEqual(sa._entrypoints, set())
        self.assertEqual(sa.do_subs, False)
        self.assertEqual(sa.subkwargs, {})
        self.assertEqual(sa.prog, None)
        self.assertEqual(sa.usage, None)
        self.assertEqual(sa.description, 'description')
        self.assertEqual(sa.epilog, None)
        self.assertEqual(sa.formatter_class, argparse.HelpFormatter)
        self.assertEqual(sa._subcmd_attr, '_script_adaptor_%x' % id(sa))
        mock_isclass.assert_called_once_with(func)

    @mock.patch('inspect.isclass', return_value=True)
    def test_init_discoverclass_true(self, mock_isclass):
        func = mock.Mock(__doc__="description")
        sa = cli_tools.ScriptAdaptor(func)

        self.assertEqual(sa._func, func)
        self.assertTrue(sa._is_class)
        self.assertEqual(sa._run, 'run')
        self.assertTrue(callable(sa._args_hook))
        self.assertEqual(sa._args_hook('foo'), None)
        self.assertTrue(callable(sa._processor))
        self.assertEqual(sa._processor('foo'), None)
        self.assertEqual(sa._arguments, [])
        self.assertEqual(sa._groups, {})
        self.assertEqual(sa._subcommands, {})
        self.assertEqual(sa._entrypoints, set())
        self.assertEqual(sa.do_subs, False)
        self.assertEqual(sa.subkwargs, {})
        self.assertEqual(sa.prog, None)
        self.assertEqual(sa.usage, None)
        self.assertEqual(sa.description, 'description')
        self.assertEqual(sa.epilog, None)
        self.assertEqual(sa.formatter_class, argparse.HelpFormatter)
        self.assertEqual(sa._subcmd_attr, '_script_adaptor_%x' % id(sa))
        mock_isclass.assert_called_once_with(func)

    def test_add_argument(self):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)

        sa._add_argument((1, 2, 3), dict(a=4, b=5, c=6), None)
        sa._add_argument((4, 5, 6), dict(a=1, b=2, c=3), None)
        sa._add_argument((3, 2, 1), dict(a=6, b=5, c=4), 'group')
        sa._add_argument((6, 5, 4), dict(a=3, b=2, c=1), 'group')

        self.assertEqual(sa._arguments, [
            ('argument', (4, 5, 6), dict(a=1, b=2, c=3)),
            ('argument', (1, 2, 3), dict(a=4, b=5, c=6)),
        ])
        self.assertEqual(sa._groups, dict(group=dict(arguments=[
            ((6, 5, 4), dict(a=3, b=2, c=1)),
            ((3, 2, 1), dict(a=6, b=5, c=4)),
        ])))

    def test_add_group_newgroup(self):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)

        sa._add_group('group1', 'group', dict(a=1, b=2, c=3))
        sa._add_group('group2', 'exclusive', dict(a=3, b=2, c=1))

        self.assertEqual(sa._groups, dict(
            group1=dict(arguments=[], type='group'),
            group2=dict(arguments=[], type='exclusive'),
        ))
        self.assertEqual(sa._arguments, [
            ('group', 'group2', dict(a=3, b=2, c=1)),
            ('group', 'group1', dict(a=1, b=2, c=3)),
        ])

    def test_add_group_oldgroup(self):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._groups['group'] = dict(type=None)

        self.assertRaises(argparse.ArgumentError, sa._add_group,
                          'group', 'group', dict(a=1, b=2, c=3))

    def test_add_subcommand(self):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)

        sa._add_subcommand('cmd', 'adaptor')
        sa._add_subcommand('dmc', 'rotpada')

        self.assertEqual(sa._subcommands, dict(cmd='adaptor', dmc='rotpada'))
        self.assertEqual(sa.do_subs, True)

    def test_add_extensions(self):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)

        sa._add_extensions('group1')
        sa._add_extensions('group2')

        self.assertEqual(sa._entrypoints, set(['group1', 'group2']))
        self.assertEqual(sa.do_subs, True)

    @mock.patch.object(pkg_resources, 'iter_entry_points')
    @mock.patch.object(cli_tools.ScriptAdaptor, '_add_subcommand')
    def test_process_entrypoints(self, mock_add_subcommand,
                                 mock_iter_entry_points):
        eps = {
            'ep1': mock.Mock(**{
                'load.return_value': mock.Mock(cli_tools='adaptor1'),
            }),
            'ep2': mock.Mock(**{
                'load.return_value': mock.Mock(cli_tools='adaptor2'),
            }),
            'ep3': mock.Mock(**{
                'load.return_value': mock.Mock(cli_tools='adaptor3'),
            }),
        }
        for name, ep in eps.items():
            ep.name = name
        ep_groups = {
            'group1': [
                mock.Mock(**{'load.side_effect': ImportError}),
                mock.Mock(**{'load.side_effect': pkg_resources.UnknownExtra}),
                mock.Mock(**{'load.side_effect': AttributeError}),
                eps['ep1'],
                eps['ep2'],
            ],
            'group2': [eps['ep3']],
        }
        mock_iter_entry_points.side_effect = lambda x: ep_groups[x]

        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._entrypoints = set(['group1', 'group2'])

        sa._process_entrypoints()

        mock_iter_entry_points.assert_has_calls([
            mock.call('group1'),
            mock.call('group2'),
        ], any_order=True)
        mock_add_subcommand.assert_has_calls([
            mock.call('ep1', 'adaptor1'),
            mock.call('ep2', 'adaptor2'),
            mock.call('ep3', 'adaptor3'),
        ], any_order=True)
        self.assertEqual(sa._entrypoints, set())

    def test_args_hook(self):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)

        result = sa.args_hook('func')

        self.assertEqual(result, 'func')
        self.assertEqual(sa._args_hook, 'func')

    def test_processor(self):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)

        result = sa.processor('func')

        self.assertEqual(result, 'func')
        self.assertEqual(sa._processor, 'func')

    @mock.patch.object(cli_tools.ScriptAdaptor, '_get_adaptor',
                       return_value='adaptor')
    @mock.patch.object(cli_tools.ScriptAdaptor, '_add_subcommand')
    def test_subcommand_basic(self, mock_add_subcommand, mock_get_adaptor):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)

        decorator = sa.subcommand('cmd')

        self.assertTrue(callable(decorator))
        self.assertFalse(mock_add_subcommand.called)

        subcmd = mock.Mock(__name__='subcmd')
        result = decorator(subcmd)

        self.assertEqual(result, subcmd)
        mock_get_adaptor.assert_called_once_with(subcmd)
        mock_add_subcommand.assert_called_once_with('cmd', 'adaptor')

    @mock.patch.object(cli_tools.ScriptAdaptor, '_get_adaptor',
                       return_value='adaptor')
    @mock.patch.object(cli_tools.ScriptAdaptor, '_add_subcommand')
    def test_subcommand_derived(self, mock_add_subcommand, mock_get_adaptor):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)

        decorator = sa.subcommand()

        self.assertTrue(callable(decorator))
        self.assertFalse(mock_add_subcommand.called)

        subcmd = mock.Mock(__name__='subcmd')
        result = decorator(subcmd)

        self.assertEqual(result, subcmd)
        mock_get_adaptor.assert_called_once_with(subcmd)
        mock_add_subcommand.assert_called_once_with('subcmd', 'adaptor')

    @mock.patch.object(cli_tools.ScriptAdaptor, '_get_adaptor',
                       return_value='adaptor')
    @mock.patch.object(cli_tools.ScriptAdaptor, '_add_subcommand')
    def test_subcommand_noparams(self, mock_add_subcommand, mock_get_adaptor):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        subcmd = mock.Mock(__name__='subcmd')

        result = sa.subcommand(subcmd)

        self.assertEqual(result, subcmd)
        mock_get_adaptor.assert_called_once_with(subcmd)
        mock_add_subcommand.assert_called_once_with('subcmd', 'adaptor')

    @mock.patch.object(cli_tools.ScriptAdaptor, '_process_entrypoints')
    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=False)
    @mock.patch.object(inspect, 'isgenerator', return_value=False)
    def test_setup_args(self, mock_isgenerator, mock_isgeneratorfunction,
                        mock_process_entrypoints):
        parser = mock.Mock()
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._groups = {
            'group_key': {
                'type': 'group',
                'arguments': [
                    ((1, 2, 3), dict(a=4, b=5, c=6)),
                    ((2, 3, 4), dict(a=5, b=6, c=7)),
                ],
            },
            'exclusive_key': {
                'type': 'exclusive',
                'arguments': [
                    ((3, 4, 5), dict(a=6, b=7, c=8)),
                    ((4, 5, 6), dict(a=7, b=8, c=9)),
                ],
            },
            'other_key': {
                'type': 'other',
                'arguments': [
                    ((5, 6, 7), dict(a=8, b=9, c=0)),
                    ((6, 7, 8), dict(a=9, b=0, c=1)),
                ],
            },
        }
        sa._arguments = [
            ('argument', (7, 8, 9), dict(a=0, b=1, c=2)),
            ('argument', (8, 9, 0), dict(a=1, b=2, c=3)),
            ('group', 'group_key', dict(title='title', description='desc')),
            ('argument', (9, 0, 1), dict(a=2, b=3, c=4)),
            ('group', 'exclusive_key', dict(required=True)),
            ('group', 'other_key', dict(something='nothing')),
            ('argument', (0, 1, 2), dict(a=3, b=4, c=5)),
            ('other', 'args', 'kwargs'),
        ]

        sa.setup_args(parser)

        parser.assert_has_calls([
            mock.call.add_argument(7, 8, 9, a=0, b=1, c=2),
            mock.call.add_argument(8, 9, 0, a=1, b=2, c=3),
            mock.call.add_argument_group(title='title', description='desc'),
            mock.call.add_argument_group()
                .add_argument(1, 2, 3, a=4, b=5, c=6),
            mock.call.add_argument_group()
                .add_argument(2, 3, 4, a=5, b=6, c=7),
            mock.call.add_argument(9, 0, 1, a=2, b=3, c=4),
            mock.call.add_mutually_exclusive_group(required=True),
            mock.call.add_mutually_exclusive_group()
                .add_argument(3, 4, 5, a=6, b=7, c=8),
            mock.call.add_mutually_exclusive_group()
                .add_argument(4, 5, 6, a=7, b=8, c=9),
            mock.call.add_argument(0, 1, 2, a=3, b=4, c=5),
        ])
        self.assertFalse(mock_process_entrypoints.called)

    @mock.patch.object(cli_tools.ScriptAdaptor, '_process_entrypoints')
    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=False)
    @mock.patch.object(inspect, 'isgenerator', return_value=False)
    def test_setup_args_hook_func(self, mock_isgenerator,
                                  mock_isgeneratorfunction,
                                  mock_process_entrypoints):
        def hook(parser):
            parser.hook()

        parser = mock.Mock()
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._args_hook = mock.Mock(side_effect=hook)
        sa._groups = {
            'group_key': {
                'type': 'group',
                'arguments': [
                    ((1, 2, 3), dict(a=4, b=5, c=6)),
                    ((2, 3, 4), dict(a=5, b=6, c=7)),
                ],
            },
            'exclusive_key': {
                'type': 'exclusive',
                'arguments': [
                    ((3, 4, 5), dict(a=6, b=7, c=8)),
                    ((4, 5, 6), dict(a=7, b=8, c=9)),
                ],
            },
            'other_key': {
                'type': 'other',
                'arguments': [
                    ((5, 6, 7), dict(a=8, b=9, c=0)),
                    ((6, 7, 8), dict(a=9, b=0, c=1)),
                ],
            },
        }
        sa._arguments = [
            ('argument', (7, 8, 9), dict(a=0, b=1, c=2)),
            ('argument', (8, 9, 0), dict(a=1, b=2, c=3)),
            ('group', 'group_key', dict(title='title', description='desc')),
            ('argument', (9, 0, 1), dict(a=2, b=3, c=4)),
            ('group', 'exclusive_key', dict(required=True)),
            ('group', 'other_key', dict(something='nothing')),
            ('argument', (0, 1, 2), dict(a=3, b=4, c=5)),
            ('other', 'args', 'kwargs'),
        ]

        sa.setup_args(parser)

        parser.assert_has_calls([
            mock.call.add_argument(7, 8, 9, a=0, b=1, c=2),
            mock.call.add_argument(8, 9, 0, a=1, b=2, c=3),
            mock.call.add_argument_group(title='title', description='desc'),
            mock.call.add_argument_group()
                .add_argument(1, 2, 3, a=4, b=5, c=6),
            mock.call.add_argument_group()
                .add_argument(2, 3, 4, a=5, b=6, c=7),
            mock.call.add_argument(9, 0, 1, a=2, b=3, c=4),
            mock.call.add_mutually_exclusive_group(required=True),
            mock.call.add_mutually_exclusive_group()
                .add_argument(3, 4, 5, a=6, b=7, c=8),
            mock.call.add_mutually_exclusive_group()
                .add_argument(4, 5, 6, a=7, b=8, c=9),
            mock.call.add_argument(0, 1, 2, a=3, b=4, c=5),
            mock.call.hook(),
        ])
        self.assertFalse(mock_process_entrypoints.called)

    @mock.patch.object(cli_tools.ScriptAdaptor, '_process_entrypoints')
    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=True)
    @mock.patch.object(inspect, 'isgenerator', return_value=True)
    def test_setup_args_hook_gen(self, mock_isgenerator,
                                 mock_isgeneratorfunction,
                                 mock_process_entrypoints):
        parser = mock.Mock()

        def hook():
            parser.hook()

        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._args_hook = mock.Mock(return_value=mock.Mock(**{
            'next.side_effect': hook,
        }))
        sa._groups = {
            'group_key': {
                'type': 'group',
                'arguments': [
                    ((1, 2, 3), dict(a=4, b=5, c=6)),
                    ((2, 3, 4), dict(a=5, b=6, c=7)),
                ],
            },
            'exclusive_key': {
                'type': 'exclusive',
                'arguments': [
                    ((3, 4, 5), dict(a=6, b=7, c=8)),
                    ((4, 5, 6), dict(a=7, b=8, c=9)),
                ],
            },
            'other_key': {
                'type': 'other',
                'arguments': [
                    ((5, 6, 7), dict(a=8, b=9, c=0)),
                    ((6, 7, 8), dict(a=9, b=0, c=1)),
                ],
            },
        }
        sa._arguments = [
            ('argument', (7, 8, 9), dict(a=0, b=1, c=2)),
            ('argument', (8, 9, 0), dict(a=1, b=2, c=3)),
            ('group', 'group_key', dict(title='title', description='desc')),
            ('argument', (9, 0, 1), dict(a=2, b=3, c=4)),
            ('group', 'exclusive_key', dict(required=True)),
            ('group', 'other_key', dict(something='nothing')),
            ('argument', (0, 1, 2), dict(a=3, b=4, c=5)),
            ('other', 'args', 'kwargs'),
        ]

        sa.setup_args(parser)

        parser.assert_has_calls([
            mock.call.hook(),
            mock.call.add_argument(7, 8, 9, a=0, b=1, c=2),
            mock.call.add_argument(8, 9, 0, a=1, b=2, c=3),
            mock.call.add_argument_group(title='title', description='desc'),
            mock.call.add_argument_group()
                .add_argument(1, 2, 3, a=4, b=5, c=6),
            mock.call.add_argument_group()
                .add_argument(2, 3, 4, a=5, b=6, c=7),
            mock.call.add_argument(9, 0, 1, a=2, b=3, c=4),
            mock.call.add_mutually_exclusive_group(required=True),
            mock.call.add_mutually_exclusive_group()
                .add_argument(3, 4, 5, a=6, b=7, c=8),
            mock.call.add_mutually_exclusive_group()
                .add_argument(4, 5, 6, a=7, b=8, c=9),
            mock.call.add_argument(0, 1, 2, a=3, b=4, c=5),
            mock.call.hook(),
        ])
        sa._args_hook.assert_called_once_with(parser)
        sa._args_hook.return_value.assert_has_calls([
            mock.call.next(),
            mock.call.next(),
            mock.call.close(),
        ])
        self.assertEqual(len(sa._args_hook.return_value.method_calls), 3)
        self.assertFalse(mock_process_entrypoints.called)

    @mock.patch.object(cli_tools.ScriptAdaptor, '_process_entrypoints')
    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=True)
    @mock.patch.object(inspect, 'isgenerator', return_value=False)
    def test_setup_args_hook_gen_nopost(self, mock_isgenerator,
                                        mock_isgeneratorfunction,
                                        mock_process_entrypoints):
        parser = mock.Mock()

        def hook():
            parser.hook()
            raise StopIteration

        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._args_hook = mock.Mock(return_value=mock.Mock(**{
            'next.side_effect': hook,
        }))
        sa._groups = {
            'group_key': {
                'type': 'group',
                'arguments': [
                    ((1, 2, 3), dict(a=4, b=5, c=6)),
                    ((2, 3, 4), dict(a=5, b=6, c=7)),
                ],
            },
            'exclusive_key': {
                'type': 'exclusive',
                'arguments': [
                    ((3, 4, 5), dict(a=6, b=7, c=8)),
                    ((4, 5, 6), dict(a=7, b=8, c=9)),
                ],
            },
            'other_key': {
                'type': 'other',
                'arguments': [
                    ((5, 6, 7), dict(a=8, b=9, c=0)),
                    ((6, 7, 8), dict(a=9, b=0, c=1)),
                ],
            },
        }
        sa._arguments = [
            ('argument', (7, 8, 9), dict(a=0, b=1, c=2)),
            ('argument', (8, 9, 0), dict(a=1, b=2, c=3)),
            ('group', 'group_key', dict(title='title', description='desc')),
            ('argument', (9, 0, 1), dict(a=2, b=3, c=4)),
            ('group', 'exclusive_key', dict(required=True)),
            ('group', 'other_key', dict(something='nothing')),
            ('argument', (0, 1, 2), dict(a=3, b=4, c=5)),
            ('other', 'args', 'kwargs'),
        ]

        sa.setup_args(parser)

        parser.assert_has_calls([
            mock.call.hook(),
            mock.call.add_argument(7, 8, 9, a=0, b=1, c=2),
            mock.call.add_argument(8, 9, 0, a=1, b=2, c=3),
            mock.call.add_argument_group(title='title', description='desc'),
            mock.call.add_argument_group()
                .add_argument(1, 2, 3, a=4, b=5, c=6),
            mock.call.add_argument_group()
                .add_argument(2, 3, 4, a=5, b=6, c=7),
            mock.call.add_argument(9, 0, 1, a=2, b=3, c=4),
            mock.call.add_mutually_exclusive_group(required=True),
            mock.call.add_mutually_exclusive_group()
                .add_argument(3, 4, 5, a=6, b=7, c=8),
            mock.call.add_mutually_exclusive_group()
                .add_argument(4, 5, 6, a=7, b=8, c=9),
            mock.call.add_argument(0, 1, 2, a=3, b=4, c=5),
        ])
        sa._args_hook.assert_called_once_with(parser)
        sa._args_hook.return_value.assert_has_calls([
            mock.call.next(),
        ])
        self.assertEqual(len(sa._args_hook.return_value.method_calls), 1)
        self.assertFalse(mock_isgenerator.called)
        self.assertFalse(mock_process_entrypoints.called)

    @mock.patch.object(cli_tools.ScriptAdaptor, '_process_entrypoints')
    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=True)
    @mock.patch.object(inspect, 'isgenerator', return_value=True)
    def test_setup_args_hook_gen_stop(self, mock_isgenerator,
                                      mock_isgeneratorfunction,
                                      mock_process_entrypoints):
        do_stop = [False]
        parser = mock.Mock()

        def hook():
            parser.hook()
            if do_stop[0]:
                raise StopIteration
            else:
                do_stop[0] = True

        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._args_hook = mock.Mock(return_value=mock.Mock(**{
            'next.side_effect': hook,
        }))
        sa._groups = {
            'group_key': {
                'type': 'group',
                'arguments': [
                    ((1, 2, 3), dict(a=4, b=5, c=6)),
                    ((2, 3, 4), dict(a=5, b=6, c=7)),
                ],
            },
            'exclusive_key': {
                'type': 'exclusive',
                'arguments': [
                    ((3, 4, 5), dict(a=6, b=7, c=8)),
                    ((4, 5, 6), dict(a=7, b=8, c=9)),
                ],
            },
            'other_key': {
                'type': 'other',
                'arguments': [
                    ((5, 6, 7), dict(a=8, b=9, c=0)),
                    ((6, 7, 8), dict(a=9, b=0, c=1)),
                ],
            },
        }
        sa._arguments = [
            ('argument', (7, 8, 9), dict(a=0, b=1, c=2)),
            ('argument', (8, 9, 0), dict(a=1, b=2, c=3)),
            ('group', 'group_key', dict(title='title', description='desc')),
            ('argument', (9, 0, 1), dict(a=2, b=3, c=4)),
            ('group', 'exclusive_key', dict(required=True)),
            ('group', 'other_key', dict(something='nothing')),
            ('argument', (0, 1, 2), dict(a=3, b=4, c=5)),
            ('other', 'args', 'kwargs'),
        ]

        sa.setup_args(parser)

        parser.assert_has_calls([
            mock.call.hook(),
            mock.call.add_argument(7, 8, 9, a=0, b=1, c=2),
            mock.call.add_argument(8, 9, 0, a=1, b=2, c=3),
            mock.call.add_argument_group(title='title', description='desc'),
            mock.call.add_argument_group()
                .add_argument(1, 2, 3, a=4, b=5, c=6),
            mock.call.add_argument_group()
                .add_argument(2, 3, 4, a=5, b=6, c=7),
            mock.call.add_argument(9, 0, 1, a=2, b=3, c=4),
            mock.call.add_mutually_exclusive_group(required=True),
            mock.call.add_mutually_exclusive_group()
                .add_argument(3, 4, 5, a=6, b=7, c=8),
            mock.call.add_mutually_exclusive_group()
                .add_argument(4, 5, 6, a=7, b=8, c=9),
            mock.call.add_argument(0, 1, 2, a=3, b=4, c=5),
            mock.call.hook(),
        ])
        sa._args_hook.assert_called_once_with(parser)
        sa._args_hook.return_value.assert_has_calls([
            mock.call.next(),
            mock.call.next(),
            mock.call.close(),
        ])
        self.assertEqual(len(sa._args_hook.return_value.method_calls), 3)
        self.assertFalse(mock_process_entrypoints.called)

    @mock.patch.object(cli_tools.ScriptAdaptor, '_process_entrypoints')
    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=False)
    @mock.patch.object(inspect, 'isgenerator', return_value=False)
    def test_setup_args_subcmds(self, mock_isgenerator,
                                mock_isgeneratorfunction,
                                mock_process_entrypoints):
        cmd_parser = mock.Mock(name='cmd')
        dmc_parser = mock.Mock(name='dmc')
        parser = mock.Mock(**{
            'add_subparsers.return_value': mock.Mock(**{
                'add_parser.side_effect': [cmd_parser, dmc_parser],
            }),
        })
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._groups = {
            'group_key': {
                'type': 'group',
                'arguments': [
                    ((1, 2, 3), dict(a=4, b=5, c=6)),
                    ((2, 3, 4), dict(a=5, b=6, c=7)),
                ],
            },
            'exclusive_key': {
                'type': 'exclusive',
                'arguments': [
                    ((3, 4, 5), dict(a=6, b=7, c=8)),
                    ((4, 5, 6), dict(a=7, b=8, c=9)),
                ],
            },
            'other_key': {
                'type': 'other',
                'arguments': [
                    ((5, 6, 7), dict(a=8, b=9, c=0)),
                    ((6, 7, 8), dict(a=9, b=0, c=1)),
                ],
            },
        }
        sa._arguments = [
            ('argument', (7, 8, 9), dict(a=0, b=1, c=2)),
            ('argument', (8, 9, 0), dict(a=1, b=2, c=3)),
            ('group', 'group_key', dict(title='title', description='desc')),
            ('argument', (9, 0, 1), dict(a=2, b=3, c=4)),
            ('group', 'exclusive_key', dict(required=True)),
            ('group', 'other_key', dict(something='nothing')),
            ('argument', (0, 1, 2), dict(a=3, b=4, c=5)),
            ('other', 'args', 'kwargs'),
        ]
        cmd_adaptor = mock.Mock(
            prog='cmd_prog',
            usage='cmd_usage',
            description='cmd_description',
            epilog='cmd_epilog',
            formatter_class='cmd_formatter_class',
        )
        dmc_adaptor = mock.Mock(
            prog='dmc_prog',
            usage='dmc_usage',
            description='dmc_description',
            epilog='dmc_epilog',
            formatter_class='dmc_formatter_class',
        )
        sa._subcommands = mock.Mock(**{'items.return_value': [
            ('cmd', cmd_adaptor),
            ('dmc', dmc_adaptor),
        ]})
        sa.do_subs = True
        sa.subkwargs = dict(a=1, b=2, c=3)

        sa.setup_args(parser)

        parser.assert_has_calls([
            mock.call.add_argument(7, 8, 9, a=0, b=1, c=2),
            mock.call.add_argument(8, 9, 0, a=1, b=2, c=3),
            mock.call.add_argument_group(title='title', description='desc'),
            mock.call.add_argument_group()
                .add_argument(1, 2, 3, a=4, b=5, c=6),
            mock.call.add_argument_group()
                .add_argument(2, 3, 4, a=5, b=6, c=7),
            mock.call.add_argument(9, 0, 1, a=2, b=3, c=4),
            mock.call.add_mutually_exclusive_group(required=True),
            mock.call.add_mutually_exclusive_group()
                .add_argument(3, 4, 5, a=6, b=7, c=8),
            mock.call.add_mutually_exclusive_group()
                .add_argument(4, 5, 6, a=7, b=8, c=9),
            mock.call.add_argument(0, 1, 2, a=3, b=4, c=5),
            mock.call.add_subparsers(a=1, b=2, c=3),
            mock.call.add_subparsers().add_parser(
                'cmd',
                prog='cmd_prog',
                usage='cmd_usage',
                description='cmd_description',
                epilog='cmd_epilog',
                formatter_class='cmd_formatter_class',
            ),
            mock.call.add_subparsers().add_parser(
                'dmc',
                prog='dmc_prog',
                usage='dmc_usage',
                description='dmc_description',
                epilog='dmc_epilog',
                formatter_class='dmc_formatter_class',
            ),
        ])
        cmd_adaptor.setup_args.assert_called_once_with(cmd_parser)
        dmc_adaptor.setup_args.assert_called_once_with(dmc_parser)
        cmd_parser.set_defaults.assert_called_once_with(**{
            sa._subcmd_attr: cmd_adaptor,
        })
        dmc_parser.set_defaults.assert_called_once_with(**{
            sa._subcmd_attr: dmc_adaptor,
        })
        mock_process_entrypoints.assert_called_once_with()

    @mock.patch.object(inspect, 'isclass', return_value=False)
    @mock.patch.object(inspect, 'ismethod', return_value=False)
    @mock.patch.object(inspect, 'getargspec', return_value=inspect.ArgSpec(
        ('a', 'b', 'c'), None, None, None))
    def test_get_kwargs(self, mock_getargspec, mock_ismethod, mock_isclass):
        func1 = mock.Mock(__doc__='')
        func2 = mock.Mock()
        sa = cli_tools.ScriptAdaptor(func1, False)

        result = sa.get_kwargs(func2, argparse.Namespace(a=1, b=2, c=3, d=4))

        self.assertEqual(result, dict(a=1, b=2, c=3))
        mock_isclass.assert_called_once_with(func2)
        mock_getargspec.assert_called_once_with(func2)
        mock_ismethod.assert_called_once_with(func2)

    @mock.patch.object(inspect, 'isclass', return_value=False)
    @mock.patch.object(inspect, 'ismethod', return_value=False)
    @mock.patch.object(inspect, 'getargspec', return_value=inspect.ArgSpec(
        ('a', 'b', 'c'), None, None, None))
    def test_get_kwargs_compatibility(self, mock_getargspec, mock_ismethod,
                                      mock_isclass):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)

        result = sa.get_kwargs(argparse.Namespace(a=1, b=2, c=3, d=4))

        self.assertEqual(result, dict(a=1, b=2, c=3))
        mock_isclass.assert_called_once_with(func)
        mock_getargspec.assert_called_once_with(func)
        mock_ismethod.assert_called_once_with(func)

    @mock.patch.object(inspect, 'isclass', return_value=False)
    @mock.patch.object(inspect, 'ismethod', return_value=True)
    @mock.patch.object(inspect, 'getargspec', return_value=inspect.ArgSpec(
        ('self', 'a', 'b', 'c'), None, None, None))
    def test_get_kwargs_method(self, mock_getargspec, mock_ismethod,
                               mock_isclass):
        func1 = mock.Mock(__doc__='')
        func2 = mock.Mock()
        sa = cli_tools.ScriptAdaptor(func1, False)

        result = sa.get_kwargs(func2, argparse.Namespace(a=1, b=2, c=3, d=4))

        self.assertEqual(result, dict(a=1, b=2, c=3))
        mock_isclass.assert_called_once_with(func2)
        mock_getargspec.assert_called_once_with(func2)
        mock_ismethod.assert_called_once_with(func2)

    @mock.patch.object(inspect, 'isclass', return_value=True)
    @mock.patch.object(inspect, 'ismethod', return_value=False)
    @mock.patch.object(inspect, 'getargspec', side_effect=[
        inspect.ArgSpec(('cls', 'a', 'b', 'c'), None, None, None),
    ])
    def test_get_kwargs_class_new(self, mock_getargspec, mock_ismethod,
                                  mock_isclass):
        func1 = mock.Mock(__doc__='')
        func2 = mock.Mock()
        sa = cli_tools.ScriptAdaptor(func1, False)

        result = sa.get_kwargs(func2, argparse.Namespace(a=1, b=2, c=3, d=4))

        self.assertEqual(result, dict(a=1, b=2, c=3))
        mock_isclass.assert_called_once_with(func2)
        mock_getargspec.assert_has_calls([
            mock.call(func2.__new__),
        ])
        self.assertEqual(mock_getargspec.call_count, 1)
        self.assertFalse(mock_ismethod.called)

    @mock.patch.object(inspect, 'isclass', return_value=True)
    @mock.patch.object(inspect, 'ismethod', return_value=False)
    @mock.patch.object(inspect, 'getargspec', side_effect=[
        TypeError,
        inspect.ArgSpec(('self', 'a', 'b', 'c'), None, None, None),
    ])
    def test_get_kwargs_class_init(self, mock_getargspec, mock_ismethod,
                                   mock_isclass):
        func1 = mock.Mock(__doc__='')
        func2 = mock.Mock()
        sa = cli_tools.ScriptAdaptor(func1, False)

        result = sa.get_kwargs(func2, argparse.Namespace(a=1, b=2, c=3, d=4))

        self.assertEqual(result, dict(a=1, b=2, c=3))
        mock_isclass.assert_called_once_with(func2)
        mock_getargspec.assert_has_calls([
            mock.call(func2.__new__),
            mock.call(func2.__init__),
        ])
        self.assertEqual(mock_getargspec.call_count, 2)
        self.assertFalse(mock_ismethod.called)

    @mock.patch.object(inspect, 'isclass', return_value=True)
    @mock.patch.object(inspect, 'ismethod', return_value=False)
    @mock.patch.object(inspect, 'getargspec', side_effect=[
        TypeError,
        TypeError,
        inspect.ArgSpec(('self', 'a', 'b', 'c'), None, None, None),
    ])
    def test_get_kwargs_class_nofunc(self, mock_getargspec, mock_ismethod,
                                     mock_isclass):
        func1 = mock.Mock(__doc__='')
        func2 = mock.Mock()
        sa = cli_tools.ScriptAdaptor(func1, False)

        result = sa.get_kwargs(func2, argparse.Namespace(a=1, b=2, c=3, d=4))

        self.assertEqual(result, {})
        mock_isclass.assert_called_once_with(func2)
        mock_getargspec.assert_has_calls([
            mock.call(func2.__new__),
            mock.call(func2.__init__),
        ])
        self.assertEqual(mock_getargspec.call_count, 2)
        self.assertFalse(mock_ismethod.called)

    @mock.patch.object(inspect, 'isclass', return_value=False)
    @mock.patch.object(inspect, 'ismethod', return_value=False)
    @mock.patch.object(inspect, 'getargspec', return_value=inspect.ArgSpec(
        ('a', 'b', 'c'), None, 'kwargs', None))
    def test_get_kwargs_extra(self, mock_getargspec, mock_ismethod,
                              mock_isclass):
        func1 = mock.Mock(__doc__='')
        func2 = mock.Mock()
        sa = cli_tools.ScriptAdaptor(func1, False)

        result = sa.get_kwargs(func2, argparse.Namespace(a=1, b=2, c=3, d=4))

        self.assertEqual(result, dict(a=1, b=2, c=3, d=4))
        mock_isclass.assert_called_once_with(func2)
        mock_getargspec.assert_called_once_with(func2)
        mock_ismethod.assert_called_once_with(func2)

    @mock.patch.object(inspect, 'isclass', return_value=False)
    @mock.patch.object(inspect, 'ismethod', return_value=False)
    @mock.patch.object(inspect, 'getargspec', return_value=inspect.ArgSpec(
        ('a', 'b', 'c'), None, None, None))
    def test_get_kwargs_required(self, mock_getargspec, mock_ismethod,
                                 mock_isclass):
        func1 = mock.Mock(__doc__='')
        func2 = mock.Mock()
        sa = cli_tools.ScriptAdaptor(func1, False)

        self.assertRaises(AttributeError, sa.get_kwargs,
                          func2, argparse.Namespace(a=1, b=2))
        mock_isclass.assert_called_once_with(func2)
        mock_getargspec.assert_called_once_with(func2)
        mock_ismethod.assert_called_once_with(func2)

    @mock.patch.object(inspect, 'isclass', return_value=False)
    @mock.patch.object(inspect, 'ismethod', return_value=False)
    @mock.patch.object(inspect, 'getargspec', return_value=inspect.ArgSpec(
        ('a', 'b', 'c'), None, None, (10,)))
    def test_get_kwargs_optional(self, mock_getargspec, mock_ismethod,
                                 mock_isclass):
        func1 = mock.Mock(__doc__='')
        func2 = mock.Mock()
        sa = cli_tools.ScriptAdaptor(func1, False)

        result = sa.get_kwargs(func2, argparse.Namespace(a=1, b=2))

        self.assertEqual(result, dict(a=1, b=2))
        mock_isclass.assert_called_once_with(func2)
        mock_getargspec.assert_called_once_with(func2)
        mock_ismethod.assert_called_once_with(func2)

    @mock.patch('sys.exc_info')
    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=False)
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value=dict(a=1, b=2, c=3))
    def test_safe_call(self, mock_get_kwargs, mock_isgeneratorfunction,
                       mock_exc_info):
        func = mock.Mock(__doc__='', return_value='result')
        sa = cli_tools.ScriptAdaptor(func, False)
        args = mock.Mock(debug=False)

        result = sa.safe_call(args)

        self.assertEqual(result, ('result', None))
        mock_get_kwargs.assert_called_once_with(func, args)
        func.assert_called_once_with(a=1, b=2, c=3)

    @mock.patch('sys.exc_info', return_value=('type', 'exception', 'tb'))
    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=False)
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value=dict(a=1, b=2, c=3))
    def test_safe_call_exc(self, mock_get_kwargs, mock_isgeneratorfunction,
                           mock_exc_info):
        func = mock.Mock(__doc__='', side_effect=TestException)
        sa = cli_tools.ScriptAdaptor(func, False)
        args = mock.Mock(debug=False)

        result = sa.safe_call(args)

        self.assertEqual(result, (None, ('type', 'exception', 'tb')))
        mock_get_kwargs.assert_called_once_with(func, args)
        func.assert_called_once_with(a=1, b=2, c=3)

    @mock.patch('sys.exc_info')
    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=False)
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value=dict(a=1, b=2, c=3))
    def test_safe_call_exc_debug(self, mock_get_kwargs,
                                 mock_isgeneratorfunction, mock_exc_info):
        func = mock.Mock(__doc__='', side_effect=TestException)
        sa = cli_tools.ScriptAdaptor(func, False)
        args = mock.Mock(debug=True)

        self.assertRaises(TestException, sa.safe_call, args)
        mock_get_kwargs.assert_called_once_with(func, args)
        func.assert_called_once_with(a=1, b=2, c=3)
        self.assertFalse(mock_exc_info.called)

    @mock.patch('sys.exc_info')
    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=False)
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value=dict(a=1, b=2, c=3))
    def test_safe_call_class(self, mock_get_kwargs, mock_isgeneratorfunction,
                             mock_exc_info):
        obj = mock.Mock(**{
            'run.return_value': 'result',
        })
        func = mock.Mock(__doc__='', return_value=obj)
        sa = cli_tools.ScriptAdaptor(func, True)
        args = mock.Mock(debug=False)

        result = sa.safe_call(args)

        self.assertEqual(result, ('result', None))
        mock_get_kwargs.assert_has_calls([
            mock.call(func, args),
            mock.call(obj.run, args),
        ])
        func.assert_called_once_with(a=1, b=2, c=3)
        obj.run.assert_called_once_with(a=1, b=2, c=3)

    @mock.patch('sys.exc_info', return_value=('type', 'exception', 'tb'))
    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=False)
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value=dict(a=1, b=2, c=3))
    def test_safe_call_class_exc(self, mock_get_kwargs,
                                 mock_isgeneratorfunction, mock_exc_info):
        obj = mock.Mock(**{
            'run.side_effect': TestException,
        })
        func = mock.Mock(__doc__='', return_value=obj)
        sa = cli_tools.ScriptAdaptor(func, True)
        args = mock.Mock(debug=False)

        result = sa.safe_call(args)

        self.assertEqual(result, (None, ('type', 'exception', 'tb')))
        mock_get_kwargs.assert_has_calls([
            mock.call(func, args),
            mock.call(obj.run, args),
        ])
        func.assert_called_once_with(a=1, b=2, c=3)
        obj.run.assert_called_once_with(a=1, b=2, c=3)

    @mock.patch('sys.exc_info', return_value=('type', 'exception', 'tb'))
    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=False)
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value=dict(a=1, b=2, c=3))
    def test_safe_call_class_exc_debug(self, mock_get_kwargs,
                                       mock_isgeneratorfunction,
                                       mock_exc_info):
        obj = mock.Mock(**{
            'run.side_effect': TestException,
        })
        func = mock.Mock(__doc__='', return_value=obj)
        sa = cli_tools.ScriptAdaptor(func, True)
        args = mock.Mock(debug=True)

        self.assertRaises(TestException, sa.safe_call, args)
        mock_get_kwargs.assert_has_calls([
            mock.call(func, args),
            mock.call(obj.run, args),
        ])
        func.assert_called_once_with(a=1, b=2, c=3)
        obj.run.assert_called_once_with(a=1, b=2, c=3)
        self.assertFalse(mock_exc_info.called)

    @mock.patch('sys.exc_info')
    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=False)
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value=dict(a=1, b=2, c=3))
    def test_safe_call_proc_func(self, mock_get_kwargs,
                                 mock_isgeneratorfunction, mock_exc_info):
        func = mock.Mock(__doc__='', return_value='result')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._processor = mock.Mock()
        args = mock.Mock(debug=False)

        result = sa.safe_call(args)

        self.assertEqual(result, ('result', None))
        sa._processor.assert_called_once_with(args)
        mock_get_kwargs.assert_called_once_with(func, args)
        func.assert_called_once_with(a=1, b=2, c=3)

    @mock.patch('sys.exc_info')
    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=True)
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value=dict(a=1, b=2, c=3))
    def test_safe_call_proc_gen_nopost(self, mock_get_kwargs,
                                       mock_isgeneratorfunction,
                                       mock_exc_info):
        func = mock.Mock(__doc__='', return_value='result')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._processor = mock.Mock(return_value=mock.Mock(**{
            'next.side_effect': StopIteration,
        }))
        args = mock.Mock(debug=False)

        result = sa.safe_call(args)

        self.assertEqual(result, ('result', None))
        sa._processor.assert_called_once_with(args)
        sa._processor.return_value.assert_has_calls([
            mock.call.next(),
        ])
        self.assertEqual(len(sa._processor.return_value.method_calls), 1)
        mock_get_kwargs.assert_called_once_with(func, args)
        func.assert_called_once_with(a=1, b=2, c=3)

    @mock.patch('sys.exc_info')
    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=True)
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value=dict(a=1, b=2, c=3))
    def test_safe_call_proc_gen_post_res_noreplace(self, mock_get_kwargs,
                                                   mock_isgeneratorfunction,
                                                   mock_exc_info):
        func = mock.Mock(__doc__='', return_value='result')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._processor = mock.Mock(return_value=mock.Mock(**{
            'send.side_effect': StopIteration,
        }))
        args = mock.Mock(debug=False)

        result = sa.safe_call(args)

        self.assertEqual(result, ('result', None))
        sa._processor.assert_called_once_with(args)
        sa._processor.return_value.assert_has_calls([
            mock.call.next(),
            mock.call.send('result'),
            mock.call.close(),
        ])
        self.assertEqual(len(sa._processor.return_value.method_calls), 3)
        mock_get_kwargs.assert_called_once_with(func, args)
        func.assert_called_once_with(a=1, b=2, c=3)

    @mock.patch('sys.exc_info')
    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=True)
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value=dict(a=1, b=2, c=3))
    def test_safe_call_proc_gen_post_res_replace(self, mock_get_kwargs,
                                                 mock_isgeneratorfunction,
                                                 mock_exc_info):
        func = mock.Mock(__doc__='', return_value='result')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._processor = mock.Mock(return_value=mock.Mock(**{
            'send.return_value': 'override',
        }))
        args = mock.Mock(debug=False)

        result = sa.safe_call(args)

        self.assertEqual(result, ('override', None))
        sa._processor.assert_called_once_with(args)
        sa._processor.return_value.assert_has_calls([
            mock.call.next(),
            mock.call.send('result'),
            mock.call.close(),
        ])
        self.assertEqual(len(sa._processor.return_value.method_calls), 3)
        mock_get_kwargs.assert_called_once_with(func, args)
        func.assert_called_once_with(a=1, b=2, c=3)

    @mock.patch('sys.exc_info', return_value=('type', 'exception', 'tb'))
    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=True)
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value=dict(a=1, b=2, c=3))
    def test_safe_call_proc_gen_post_exc_noreplace(self, mock_get_kwargs,
                                                   mock_isgeneratorfunction,
                                                   mock_exc_info):
        func = mock.Mock(__doc__='', side_effect=TestException)
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._processor = mock.Mock(return_value=mock.Mock(**{
            'throw.return_value': 'thrown',
        }))
        args = mock.Mock(debug=False)

        result = sa.safe_call(args)

        self.assertEqual(result, ('thrown', None))
        sa._processor.assert_called_once_with(args)
        sa._processor.return_value.assert_has_calls([
            mock.call.next(),
            mock.call.throw('type', 'exception', 'tb'),
            mock.call.close(),
        ])
        self.assertEqual(len(sa._processor.return_value.method_calls), 3)
        mock_get_kwargs.assert_called_once_with(func, args)
        func.assert_called_once_with(a=1, b=2, c=3)

    @mock.patch('sys.exc_info', side_effect=[
        ('type', 'exception', 'tb'),
        ('otype', 'something', 'bt'),
    ])
    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=True)
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value=dict(a=1, b=2, c=3))
    def test_safe_call_proc_gen_post_exc_replace(self, mock_get_kwargs,
                                                 mock_isgeneratorfunction,
                                                 mock_exc_info):
        func = mock.Mock(__doc__='', side_effect=TestException)
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._processor = mock.Mock(return_value=mock.Mock(**{
            'throw.side_effect': TestException,
        }))
        args = mock.Mock(debug=False)

        result = sa.safe_call(args)

        self.assertEqual(result, (None, ('otype', 'something', 'bt')))
        sa._processor.assert_called_once_with(args)
        sa._processor.return_value.assert_has_calls([
            mock.call.next(),
            mock.call.throw('type', 'exception', 'tb'),
            mock.call.close(),
        ])
        self.assertEqual(len(sa._processor.return_value.method_calls), 3)
        mock_get_kwargs.assert_called_once_with(func, args)
        func.assert_called_once_with(a=1, b=2, c=3)

    @mock.patch.object(argparse, 'ArgumentParser', return_value=mock.Mock(**{
        'parse_args.return_value': 'parsed args',
    }))
    @mock.patch.object(cli_tools.ScriptAdaptor, 'setup_args')
    @mock.patch.object(cli_tools.ScriptAdaptor, 'safe_call',
                       return_value=('result', None))
    def test_console_basic(self, mock_safe_call, mock_setup_args,
                           mock_ArgumentParser):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa.prog = 'program'
        sa.usage = 'usage'
        sa.description = 'description'
        sa.epilog = 'epilog'
        sa.formatter_class = 'formatter_class'

        result = sa.console(argv='argument vector')

        mock_ArgumentParser.assert_called_once_with(
            prog='program', usage='usage', description='description',
            epilog='epilog', formatter_class='formatter_class')
        mock_setup_args.assert_called_once_with(
            mock_ArgumentParser.return_value)
        mock_ArgumentParser.return_value.parse_args.assert_called_once_with(
            args='argument vector')
        mock_safe_call.assert_called_once_with('parsed args')
        self.assertEqual(result, 'result')

    @mock.patch.object(argparse, 'ArgumentParser', return_value=mock.Mock(**{
        'parse_args.return_value': 'parsed args',
    }))
    @mock.patch.object(cli_tools.ScriptAdaptor, 'setup_args')
    @mock.patch.object(cli_tools.ScriptAdaptor, 'safe_call',
                       return_value=(None, ('type', 'exception', 'tb')))
    def test_console_exception(self, mock_safe_call, mock_setup_args,
                               mock_ArgumentParser):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa.prog = 'program'
        sa.usage = 'usage'
        sa.description = 'description'
        sa.epilog = 'epilog'
        sa.formatter_class = 'formatter_class'

        result = sa.console(args='override args')

        self.assertFalse(mock_ArgumentParser.called)
        self.assertFalse(mock_setup_args.called)
        mock_safe_call.assert_called_once_with('override args')
        self.assertEqual(result, 'exception')

    @mock.patch.object(argparse, 'ArgumentParser', return_value=mock.Mock(**{
        'parse_args.return_value': 'parsed args',
    }))
    @mock.patch.object(cli_tools.ScriptAdaptor, 'setup_args')
    @mock.patch.object(cli_tools.ScriptAdaptor, 'safe_call',
                       return_value=('result', None))
    def test_console_subcmd(self, mock_safe_call, mock_setup_args,
                            mock_ArgumentParser):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa.do_subs = True
        adaptor = mock.Mock(**{'safe_call.return_value': ('tluser', None)})
        args = mock.Mock(**{sa._subcmd_attr: adaptor})

        result = sa.console(args=args)

        self.assertFalse(mock_ArgumentParser.called)
        self.assertFalse(mock_setup_args.called)
        self.assertFalse(mock_safe_call.called)
        adaptor.safe_call.assert_called_once_with(args)
        self.assertEqual(result, 'tluser')

    @mock.patch.object(cli_tools.ScriptAdaptor, '_process_entrypoints')
    def test_get_subcommands_nosubs(self, mock_process_entrypoints):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._subcommands = mock.Mock(**{'items.return_value': [
            ('cmd', mock.Mock(_func='subcmd')),
            ('dmc', mock.Mock(_func='subdmc')),
        ]})

        result = sa.get_subcommands()

        self.assertEqual(result, {})
        self.assertFalse(mock_process_entrypoints.called)

    @mock.patch.object(cli_tools.ScriptAdaptor, '_process_entrypoints')
    def test_get_subcommands(self, mock_process_entrypoints):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._subcommands = mock.Mock(**{'items.return_value': [
            ('cmd', mock.Mock(_func='subcmd')),
            ('dmc', mock.Mock(_func='subdmc')),
        ]})
        sa.do_subs = True

        result = sa.get_subcommands()

        self.assertEqual(result, dict(cmd='subcmd', dmc='subdmc'))
        mock_process_entrypoints.assert_called_once_with()


class DecoratorsTest(unittest.TestCase):
    @mock.patch.object(cli_tools.ScriptAdaptor, '_get_adaptor',
                       return_value=mock.Mock())
    def test_console(self, mock_get_adaptor):
        func = mock.Mock()
        result = cli_tools.console(func)

        mock_get_adaptor.assert_called_once_with(func)
        self.assertEqual(result, func)

    @mock.patch.object(cli_tools.ScriptAdaptor, '_get_adaptor',
                       return_value=mock.Mock())
    def test_prog(self, mock_get_adaptor):
        decorator = cli_tools.prog('program')

        self.assertTrue(callable(decorator))
        self.assertFalse(mock_get_adaptor.called)

        func = mock.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        self.assertEqual(result, func)
        self.assertEqual(mock_get_adaptor.return_value.prog, 'program')

    @mock.patch.object(cli_tools.ScriptAdaptor, '_get_adaptor',
                       return_value=mock.Mock())
    def test_usage(self, mock_get_adaptor):
        decorator = cli_tools.usage('text')

        self.assertTrue(callable(decorator))
        self.assertFalse(mock_get_adaptor.called)

        func = mock.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        self.assertEqual(result, func)
        self.assertEqual(mock_get_adaptor.return_value.usage, 'text')

    @mock.patch.object(cli_tools.ScriptAdaptor, '_get_adaptor',
                       return_value=mock.Mock())
    def test_description(self, mock_get_adaptor):
        decorator = cli_tools.description('text')

        self.assertTrue(callable(decorator))
        self.assertFalse(mock_get_adaptor.called)

        func = mock.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        self.assertEqual(result, func)
        self.assertEqual(mock_get_adaptor.return_value.description, 'text')

    @mock.patch.object(cli_tools.ScriptAdaptor, '_get_adaptor',
                       return_value=mock.Mock())
    def test_epilog(self, mock_get_adaptor):
        decorator = cli_tools.epilog('text')

        self.assertTrue(callable(decorator))
        self.assertFalse(mock_get_adaptor.called)

        func = mock.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        self.assertEqual(result, func)
        self.assertEqual(mock_get_adaptor.return_value.epilog, 'text')

    @mock.patch.object(cli_tools.ScriptAdaptor, '_get_adaptor',
                       return_value=mock.Mock())
    def test_formatter_class(self, mock_get_adaptor):
        decorator = cli_tools.formatter_class('class')

        self.assertTrue(callable(decorator))
        self.assertFalse(mock_get_adaptor.called)

        func = mock.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        self.assertEqual(result, func)
        self.assertEqual(mock_get_adaptor.return_value.formatter_class,
                         'class')

    @mock.patch.object(cli_tools.ScriptAdaptor, '_get_adaptor',
                       return_value=mock.Mock())
    def test_argument_nogroup(self, mock_get_adaptor):
        decorator = cli_tools.argument(1, 2, 3, a=4, b=5, c=6)

        self.assertTrue(callable(decorator))
        self.assertFalse(mock_get_adaptor.called)

        func = mock.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        self.assertEqual(result, func)
        mock_get_adaptor.return_value._add_argument.assert_called_once_with(
            (1, 2, 3), dict(a=4, b=5, c=6), group=None)

    @mock.patch.object(cli_tools.ScriptAdaptor, '_get_adaptor',
                       return_value=mock.Mock())
    def test_argument_withgroup(self, mock_get_adaptor):
        decorator = cli_tools.argument(1, 2, 3, a=4, b=5, c=6, group='group')

        self.assertTrue(callable(decorator))
        self.assertFalse(mock_get_adaptor.called)

        func = mock.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        self.assertEqual(result, func)
        mock_get_adaptor.return_value._add_argument.assert_called_once_with(
            (1, 2, 3), dict(a=4, b=5, c=6), group='group')

    @mock.patch.object(cli_tools.ScriptAdaptor, '_get_adaptor',
                       return_value=mock.Mock())
    def test_argument_group(self, mock_get_adaptor):
        decorator = cli_tools.argument_group('group', a=1, b=2, c=3)

        self.assertTrue(callable(decorator))
        self.assertFalse(mock_get_adaptor.called)

        func = mock.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        self.assertEqual(result, func)
        mock_get_adaptor.return_value._add_group.assert_called_once_with(
            'group', 'group', dict(a=1, b=2, c=3))

    @mock.patch.object(cli_tools.ScriptAdaptor, '_get_adaptor',
                       return_value=mock.Mock())
    def test_mutually_exclusive_group(self, mock_get_adaptor):
        decorator = cli_tools.mutually_exclusive_group('group', a=1, b=2, c=3)

        self.assertTrue(callable(decorator))
        self.assertFalse(mock_get_adaptor.called)

        func = mock.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        self.assertEqual(result, func)
        mock_get_adaptor.return_value._add_group.assert_called_once_with(
            'group', 'exclusive', dict(a=1, b=2, c=3))

    @mock.patch.object(cli_tools.ScriptAdaptor, '_get_adaptor',
                       return_value=mock.Mock())
    def test_subparsers(self, mock_get_adaptor):
        decorator = cli_tools.subparsers(a=1, b=2, c=3)

        self.assertTrue(callable(decorator))
        self.assertFalse(mock_get_adaptor.called)

        func = mock.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        self.assertEqual(result, func)
        self.assertEqual(mock_get_adaptor.return_value.subkwargs,
                         dict(a=1, b=2, c=3))
        self.assertEqual(mock_get_adaptor.return_value.do_subs, True)

    @mock.patch.object(cli_tools.ScriptAdaptor, '_get_adaptor',
                       return_value=mock.Mock())
    def test_load_subcommands(self, mock_get_adaptor):
        decorator = cli_tools.load_subcommands('entrypoint.group')

        self.assertTrue(callable(decorator))
        self.assertFalse(mock_get_adaptor.called)

        func = mock.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        self.assertEqual(result, func)
        mock_get_adaptor.return_value._add_extensions.assert_called_once_with(
            'entrypoint.group')
