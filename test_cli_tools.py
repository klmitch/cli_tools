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

import pkg_resources
import pytest
import six

import cli_tools


class ExceptionForTest(Exception):
    pass


class MockGen(six.Iterator):
    def __init__(self, generator):
        self.generator = generator

    def __iter__(self):
        return self

    def __next__(self):
        return self.generator.next()

    def send(self, value):
        return self.generator.send(value)

    def throw(self, exc_type, exc_value=None, exc_tb=None):
        return self.generator.throw(exc_type, exc_value, exc_tb)

    def close(self):
        return self.generator.close()


class MockGenFunc(object):
    def __init__(self, generator):
        self.generator = generator

    def __call__(self, *args, **kwargs):
        # Log in the call, but ignore return value
        self.generator.call(*args, **kwargs)

        # It'll always be a MockGen object
        return MockGen(self.generator)


class TestCleanText(object):
    def test_clean_text(self):
        text = """
            This is a\t
            test of the text cleaner.

            This won't be included.
        """

        result = cli_tools._clean_text(text)

        assert result == "This is a test of the text cleaner."

    def test_clean_text_blank(self):
        result = cli_tools._clean_text(None)

        assert result == ''


class TestExpose(object):
    def test_basic(self):
        @cli_tools.expose
        def test_func():
            pass

        assert test_func._cli_expose is True


class TestScriptAdaptorMeta(object):
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

        assert SAMTest.exposed == set(['test_func2', 'test_func4'])


class TestScriptAdaptor(object):
    def test_get_adaptor_unset(self, mocker):
        mock_isclass = mocker.patch('inspect.isclass', return_value=False)
        func = mocker.Mock(__doc__='', cli_tools=None)

        result = cli_tools.ScriptAdaptor._get_adaptor(func)

        assert isinstance(result, cli_tools.ScriptAdaptor) is True
        assert func.cli_tools == result
        assert func.args_hook == result.args_hook
        assert func.processor == result.processor
        assert func.subcommand == result.subcommand
        assert func.setup_args == result.setup_args
        assert func.get_kwargs == result.get_kwargs
        assert func.safe_call == result.safe_call
        assert func.console == result.console
        assert func.get_subcommands == result.get_subcommands
        mock_isclass.assert_called_once_with(func)

    def test_get_adaptor_set(self, mocker):
        mock_isclass = mocker.patch('inspect.isclass', return_value=False)
        func = mocker.Mock(
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

        assert result == sa
        assert func.args_hook == 'args_hook'
        assert func.processor == 'processor'
        assert func.subcommand == 'subcommand'
        assert func.setup_args == 'setup_args'
        assert func.get_kwargs == 'get_kwargs'
        assert func.safe_call == 'safe_call'
        assert func.console == 'console'
        assert func.get_subcommands == 'get_subcommands'
        assert not mock_isclass.called

    def test_get_adaptor_class(self, mocker):
        mock_isclass = mocker.patch('inspect.isclass', return_value=True)
        func = mocker.Mock(
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

        assert isinstance(result, cli_tools.ScriptAdaptor) is True
        assert func.args_hook == 'args_hook'
        assert func.processor == 'processor'
        assert func.subcommand == 'subcommand'
        assert func.setup_args == 'setup_args'
        assert func.get_kwargs == 'get_kwargs'
        assert func.safe_call == 'safe_call'
        assert func.console == 'console'
        assert func.get_subcommands == 'get_subcommands'
        mock_isclass.assert_called_once_with(func)

    def test_init_notclass(self, mocker):
        mock_isclass = mocker.patch('inspect.isclass', return_value=True)
        func = mocker.Mock(__doc__="description")
        sa = cli_tools.ScriptAdaptor(func, False)

        assert sa._func == func
        assert sa._is_class is False
        assert sa._run is None
        assert callable(sa._args_hook)
        assert sa._args_hook('foo') is None
        assert callable(sa._processor)
        assert sa._processor('foo') is None
        assert sa._arguments == []
        assert sa._groups == {}
        assert sa._subcommands == {}
        assert sa._entrypoints == set()
        assert sa.do_subs is False
        assert sa.subkwargs == {}
        assert sa.prog is None
        assert sa.usage is None
        assert sa.description == 'description'
        assert sa.epilog is None
        assert sa.formatter_class == argparse.HelpFormatter
        assert sa._subcmd_attr == '_script_adaptor_%x' % id(sa)
        assert not mock_isclass.called

    def test_init_isclass(self, mocker):
        mock_isclass = mocker.patch('inspect.isclass', return_value=False)
        func = mocker.Mock(__doc__="description")
        sa = cli_tools.ScriptAdaptor(func, True)

        assert sa._func == func
        assert sa._is_class is True
        assert sa._run == 'run'
        assert callable(sa._args_hook)
        assert sa._args_hook('foo') is None
        assert callable(sa._processor)
        assert sa._processor('foo') is None
        assert sa._arguments == []
        assert sa._groups == {}
        assert sa._subcommands == {}
        assert sa._entrypoints == set()
        assert sa.do_subs is False
        assert sa.subkwargs == {}
        assert sa.prog is None
        assert sa.usage is None
        assert sa.description == 'description'
        assert sa.epilog is None
        assert sa.formatter_class == argparse.HelpFormatter
        assert sa._subcmd_attr == '_script_adaptor_%x' % id(sa)
        assert not mock_isclass.called

    def test_init_discoverclass_false(self, mocker):
        mock_isclass = mocker.patch('inspect.isclass', return_value=False)
        func = mocker.Mock(__doc__="description")
        sa = cli_tools.ScriptAdaptor(func)

        assert sa._func == func
        assert sa._is_class is False
        assert sa._run is None
        assert callable(sa._args_hook)
        assert sa._args_hook('foo') is None
        assert callable(sa._processor)
        assert sa._processor('foo') is None
        assert sa._arguments == []
        assert sa._groups == {}
        assert sa._subcommands == {}
        assert sa._entrypoints == set()
        assert sa.do_subs is False
        assert sa.subkwargs == {}
        assert sa.prog is None
        assert sa.usage is None
        assert sa.description == 'description'
        assert sa.epilog is None
        assert sa.formatter_class == argparse.HelpFormatter
        assert sa._subcmd_attr == '_script_adaptor_%x' % id(sa)
        mock_isclass.assert_called_once_with(func)

    def test_init_discoverclass_true(self, mocker):
        mock_isclass = mocker.patch('inspect.isclass', return_value=True)
        func = mocker.Mock(__doc__="description")
        sa = cli_tools.ScriptAdaptor(func)

        assert sa._func == func
        assert sa._is_class is True
        assert sa._run == 'run'
        assert callable(sa._args_hook)
        assert sa._args_hook('foo') is None
        assert callable(sa._processor)
        assert sa._processor('foo') is None
        assert sa._arguments == []
        assert sa._groups == {}
        assert sa._subcommands == {}
        assert sa._entrypoints == set()
        assert sa.do_subs is False
        assert sa.subkwargs == {}
        assert sa.prog is None
        assert sa.usage is None
        assert sa.description == 'description'
        assert sa.epilog is None
        assert sa.formatter_class == argparse.HelpFormatter
        assert sa._subcmd_attr == '_script_adaptor_%x' % id(sa)
        mock_isclass.assert_called_once_with(func)

    def test_add_argument(self, mocker):
        func = mocker.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)

        sa._add_argument((1, 2, 3), dict(a=4, b=5, c=6), None)
        sa._add_argument((4, 5, 6), dict(a=1, b=2, c=3), None)
        sa._add_argument((3, 2, 1), dict(a=6, b=5, c=4), 'group')
        sa._add_argument((6, 5, 4), dict(a=3, b=2, c=1), 'group')

        assert sa._arguments == [
            ('argument', (4, 5, 6), dict(a=1, b=2, c=3)),
            ('argument', (1, 2, 3), dict(a=4, b=5, c=6)),
        ]
        assert sa._groups == dict(group=dict(arguments=[
            ((6, 5, 4), dict(a=3, b=2, c=1)),
            ((3, 2, 1), dict(a=6, b=5, c=4)),
        ]))

    def test_add_group_newgroup(self, mocker):
        func = mocker.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)

        sa._add_group('group1', 'group', dict(a=1, b=2, c=3))
        sa._add_group('group2', 'exclusive', dict(a=3, b=2, c=1))

        assert sa._groups == dict(
            group1=dict(arguments=[], type='group'),
            group2=dict(arguments=[], type='exclusive'),
        )
        assert sa._arguments == [
            ('group', 'group2', dict(a=3, b=2, c=1)),
            ('group', 'group1', dict(a=1, b=2, c=3)),
        ]

    def test_add_group_oldgroup(self, mocker):
        func = mocker.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._groups['group'] = dict(type=None)

        with pytest.raises(argparse.ArgumentError):
            sa._add_group('group', 'group', dict(a=1, b=2, c=3))

    def test_add_subcommand(self, mocker):
        func = mocker.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)

        sa._add_subcommand('cmd', 'adaptor')
        sa._add_subcommand('dmc', 'rotpada')

        assert sa._subcommands == dict(cmd='adaptor', dmc='rotpada')
        assert sa.do_subs is True

    def test_add_extensions(self, mocker):
        func = mocker.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)

        sa._add_extensions('group1')
        sa._add_extensions('group2')

        assert sa._entrypoints == set(['group1', 'group2'])
        assert sa.do_subs is True

    def test_process_entrypoints(self, mocker):
        mock_iter_entry_points = mocker.patch.object(
            pkg_resources, 'iter_entry_points'
        )
        mock_add_subcommand = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_add_subcommand'
        )
        eps = {
            'ep1': mocker.Mock(**{
                'load.return_value': mocker.Mock(cli_tools='adaptor1'),
            }),
            'ep2': mocker.Mock(**{
                'load.return_value': mocker.Mock(cli_tools='adaptor2'),
            }),
            'ep3': mocker.Mock(**{
                'load.return_value': mocker.Mock(cli_tools='adaptor3'),
            }),
        }
        for name, ep in eps.items():
            ep.name = name
        ep_groups = {
            'group1': [
                mocker.Mock(**{'load.side_effect': ImportError}),
                mocker.Mock(**{
                    'load.side_effect': pkg_resources.UnknownExtra,
                }),
                mocker.Mock(**{'load.side_effect': AttributeError}),
                eps['ep1'],
                eps['ep2'],
            ],
            'group2': [eps['ep3']],
        }
        mock_iter_entry_points.side_effect = lambda x: ep_groups[x]

        func = mocker.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._entrypoints = set(['group1', 'group2'])

        sa._process_entrypoints()

        mock_iter_entry_points.assert_has_calls([
            mocker.call('group1'),
            mocker.call('group2'),
        ], any_order=True)
        mock_add_subcommand.assert_has_calls([
            mocker.call('ep1', 'adaptor1'),
            mocker.call('ep2', 'adaptor2'),
            mocker.call('ep3', 'adaptor3'),
        ], any_order=True)
        assert sa._entrypoints == set()

    def test_args_hook(self, mocker):
        func = mocker.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)

        result = sa.args_hook('func')

        assert result == 'func'
        assert sa._args_hook == 'func'

    def test_processor(self, mocker):
        func = mocker.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)

        result = sa.processor('func')

        assert result == 'func'
        assert sa._processor == 'func'

    def test_subcommand_basic(self, mocker):
        mock_get_adaptor = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_get_adaptor', return_value='adaptor'
        )
        mock_add_subcommand = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_add_subcommand'
        )
        func = mocker.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)

        decorator = sa.subcommand('cmd')

        assert callable(decorator)
        assert not mock_add_subcommand.called

        subcmd = mocker.Mock(__name__='subcmd')
        result = decorator(subcmd)

        assert result == subcmd
        mock_get_adaptor.assert_called_once_with(subcmd)
        mock_add_subcommand.assert_called_once_with('cmd', 'adaptor')

    def test_subcommand_derived(self, mocker):
        mock_get_adaptor = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_get_adaptor', return_value='adaptor'
        )
        mock_add_subcommand = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_add_subcommand'
        )
        func = mocker.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)

        decorator = sa.subcommand()

        assert callable(decorator)
        assert not mock_add_subcommand.called

        subcmd = mocker.Mock(__name__='subcmd')
        result = decorator(subcmd)

        assert result == subcmd
        mock_get_adaptor.assert_called_once_with(subcmd)
        mock_add_subcommand.assert_called_once_with('subcmd', 'adaptor')

    def test_subcommand_noparams(self, mocker):
        mock_get_adaptor = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_get_adaptor', return_value='adaptor'
        )
        mock_add_subcommand = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_add_subcommand'
        )
        func = mocker.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        subcmd = mocker.Mock(__name__='subcmd')

        result = sa.subcommand(subcmd)

        assert result == subcmd
        mock_get_adaptor.assert_called_once_with(subcmd)
        mock_add_subcommand.assert_called_once_with('subcmd', 'adaptor')

    def test_setup_args(self, mocker):
        mock_process_entrypoints = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_process_entrypoints'
        )
        mocker.patch.object(inspect, 'isgeneratorfunction', return_value=False)
        mocker.patch.object(inspect, 'isgenerator', return_value=False)
        parser = mocker.Mock()
        func = mocker.Mock(__doc__='')
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
            mocker.call.add_argument(7, 8, 9, a=0, b=1, c=2),
            mocker.call.add_argument(8, 9, 0, a=1, b=2, c=3),
            mocker.call.add_argument_group(title='title', description='desc'),
            mocker.call.add_argument_group()
            .add_argument(1, 2, 3, a=4, b=5, c=6),
            mocker.call.add_argument_group()
            .add_argument(2, 3, 4, a=5, b=6, c=7),
            mocker.call.add_argument(9, 0, 1, a=2, b=3, c=4),
            mocker.call.add_mutually_exclusive_group(required=True),
            mocker.call.add_mutually_exclusive_group()
            .add_argument(3, 4, 5, a=6, b=7, c=8),
            mocker.call.add_mutually_exclusive_group()
            .add_argument(4, 5, 6, a=7, b=8, c=9),
            mocker.call.add_argument(0, 1, 2, a=3, b=4, c=5),
        ])
        assert not mock_process_entrypoints.called

    def test_setup_args_hook_func(self, mocker):
        mock_process_entrypoints = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_process_entrypoints'
        )
        mocker.patch.object(inspect, 'isgeneratorfunction', return_value=False)
        mocker.patch.object(inspect, 'isgenerator', return_value=False)

        def hook(parser):
            parser.hook()

        parser = mocker.Mock()
        func = mocker.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._args_hook = mocker.Mock(side_effect=hook)
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
            mocker.call.add_argument(7, 8, 9, a=0, b=1, c=2),
            mocker.call.add_argument(8, 9, 0, a=1, b=2, c=3),
            mocker.call.add_argument_group(title='title', description='desc'),
            mocker.call.add_argument_group()
            .add_argument(1, 2, 3, a=4, b=5, c=6),
            mocker.call.add_argument_group()
            .add_argument(2, 3, 4, a=5, b=6, c=7),
            mocker.call.add_argument(9, 0, 1, a=2, b=3, c=4),
            mocker.call.add_mutually_exclusive_group(required=True),
            mocker.call.add_mutually_exclusive_group()
            .add_argument(3, 4, 5, a=6, b=7, c=8),
            mocker.call.add_mutually_exclusive_group()
            .add_argument(4, 5, 6, a=7, b=8, c=9),
            mocker.call.add_argument(0, 1, 2, a=3, b=4, c=5),
            mocker.call.hook(),
        ])
        assert not mock_process_entrypoints.called

    def test_setup_args_hook_gen(self, mocker):
        mock_process_entrypoints = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_process_entrypoints'
        )
        mocker.patch.object(inspect, 'isgeneratorfunction', return_value=True)
        mocker.patch.object(inspect, 'isgenerator', return_value=True)
        parser = mocker.Mock()

        def hook():
            parser.hook()

        func = mocker.Mock(__doc__='')
        gen = mocker.Mock(**{
            'next.side_effect': hook,
        })
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._args_hook = MockGenFunc(gen)
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
            mocker.call.hook(),
            mocker.call.add_argument(7, 8, 9, a=0, b=1, c=2),
            mocker.call.add_argument(8, 9, 0, a=1, b=2, c=3),
            mocker.call.add_argument_group(title='title', description='desc'),
            mocker.call.add_argument_group()
            .add_argument(1, 2, 3, a=4, b=5, c=6),
            mocker.call.add_argument_group()
            .add_argument(2, 3, 4, a=5, b=6, c=7),
            mocker.call.add_argument(9, 0, 1, a=2, b=3, c=4),
            mocker.call.add_mutually_exclusive_group(required=True),
            mocker.call.add_mutually_exclusive_group()
            .add_argument(3, 4, 5, a=6, b=7, c=8),
            mocker.call.add_mutually_exclusive_group()
            .add_argument(4, 5, 6, a=7, b=8, c=9),
            mocker.call.add_argument(0, 1, 2, a=3, b=4, c=5),
            mocker.call.hook(),
        ])
        gen.assert_has_calls([
            mocker.call.call(parser),
            mocker.call.next(),
            mocker.call.next(),
            mocker.call.close(),
        ])
        assert len(gen.method_calls) == 4
        assert not mock_process_entrypoints.called

    def test_setup_args_hook_gen_nopost(self, mocker):
        mock_process_entrypoints = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_process_entrypoints'
        )
        mocker.patch.object(inspect, 'isgeneratorfunction', return_value=True)
        mock_isgenerator = mocker.patch.object(
            inspect, 'isgenerator', return_value=False
        )
        parser = mocker.Mock()

        def hook():
            parser.hook()
            raise StopIteration

        func = mocker.Mock(__doc__='')
        gen = mocker.Mock(**{
            'next.side_effect': hook,
        })
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._args_hook = MockGenFunc(gen)
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
            mocker.call.hook(),
            mocker.call.add_argument(7, 8, 9, a=0, b=1, c=2),
            mocker.call.add_argument(8, 9, 0, a=1, b=2, c=3),
            mocker.call.add_argument_group(title='title', description='desc'),
            mocker.call.add_argument_group()
            .add_argument(1, 2, 3, a=4, b=5, c=6),
            mocker.call.add_argument_group()
            .add_argument(2, 3, 4, a=5, b=6, c=7),
            mocker.call.add_argument(9, 0, 1, a=2, b=3, c=4),
            mocker.call.add_mutually_exclusive_group(required=True),
            mocker.call.add_mutually_exclusive_group()
            .add_argument(3, 4, 5, a=6, b=7, c=8),
            mocker.call.add_mutually_exclusive_group()
            .add_argument(4, 5, 6, a=7, b=8, c=9),
            mocker.call.add_argument(0, 1, 2, a=3, b=4, c=5),
        ])
        gen.assert_has_calls([
            mocker.call.call(parser),
            mocker.call.next(),
        ])
        assert len(gen.method_calls) == 2
        assert not mock_isgenerator.called
        assert not mock_process_entrypoints.called

    def test_setup_args_hook_gen_stop(self, mocker):
        mock_process_entrypoints = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_process_entrypoints'
        )
        mocker.patch.object(inspect, 'isgeneratorfunction', return_value=True)
        mocker.patch.object(inspect, 'isgenerator', return_value=True)
        do_stop = [False]
        parser = mocker.Mock()

        def hook():
            parser.hook()
            if do_stop[0]:
                raise StopIteration
            else:
                do_stop[0] = True

        func = mocker.Mock(__doc__='')
        gen = mocker.Mock(**{
            'next.side_effect': hook,
        })
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._args_hook = MockGenFunc(gen)
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
            mocker.call.hook(),
            mocker.call.add_argument(7, 8, 9, a=0, b=1, c=2),
            mocker.call.add_argument(8, 9, 0, a=1, b=2, c=3),
            mocker.call.add_argument_group(title='title', description='desc'),
            mocker.call.add_argument_group()
            .add_argument(1, 2, 3, a=4, b=5, c=6),
            mocker.call.add_argument_group()
            .add_argument(2, 3, 4, a=5, b=6, c=7),
            mocker.call.add_argument(9, 0, 1, a=2, b=3, c=4),
            mocker.call.add_mutually_exclusive_group(required=True),
            mocker.call.add_mutually_exclusive_group()
            .add_argument(3, 4, 5, a=6, b=7, c=8),
            mocker.call.add_mutually_exclusive_group()
            .add_argument(4, 5, 6, a=7, b=8, c=9),
            mocker.call.add_argument(0, 1, 2, a=3, b=4, c=5),
            mocker.call.hook(),
        ])
        gen.assert_has_calls([
            mocker.call.call(parser),
            mocker.call.next(),
            mocker.call.next(),
            mocker.call.close(),
        ])
        assert len(gen.method_calls) == 4
        assert not mock_process_entrypoints.called

    def test_setup_args_subcmds(self, mocker):
        mock_process_entrypoints = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_process_entrypoints'
        )
        mocker.patch.object(inspect, 'isgeneratorfunction', return_value=False)
        mocker.patch.object(inspect, 'isgenerator', return_value=False)
        cmd_parser = mocker.Mock(name='cmd')
        dmc_parser = mocker.Mock(name='dmc')
        parser = mocker.Mock(**{
            'add_subparsers.return_value': mocker.Mock(**{
                'add_parser.side_effect': [cmd_parser, dmc_parser],
            }),
        })
        func = mocker.Mock(__doc__='')
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
        cmd_adaptor = mocker.Mock(
            prog='cmd_prog',
            usage='cmd_usage',
            description='cmd_description',
            epilog='cmd_epilog',
            formatter_class='cmd_formatter_class',
        )
        dmc_adaptor = mocker.Mock(
            prog='dmc_prog',
            usage='dmc_usage',
            description='dmc_description',
            epilog='dmc_epilog',
            formatter_class='dmc_formatter_class',
        )
        sa._subcommands = mocker.Mock(**{'items.return_value': [
            ('cmd', cmd_adaptor),
            ('dmc', dmc_adaptor),
        ]})
        sa.do_subs = True
        sa.subkwargs = dict(a=1, b=2, c=3)

        sa.setup_args(parser)

        parser.assert_has_calls([
            mocker.call.add_argument(7, 8, 9, a=0, b=1, c=2),
            mocker.call.add_argument(8, 9, 0, a=1, b=2, c=3),
            mocker.call.add_argument_group(title='title', description='desc'),
            mocker.call.add_argument_group()
            .add_argument(1, 2, 3, a=4, b=5, c=6),
            mocker.call.add_argument_group()
            .add_argument(2, 3, 4, a=5, b=6, c=7),
            mocker.call.add_argument(9, 0, 1, a=2, b=3, c=4),
            mocker.call.add_mutually_exclusive_group(required=True),
            mocker.call.add_mutually_exclusive_group()
            .add_argument(3, 4, 5, a=6, b=7, c=8),
            mocker.call.add_mutually_exclusive_group()
            .add_argument(4, 5, 6, a=7, b=8, c=9),
            mocker.call.add_argument(0, 1, 2, a=3, b=4, c=5),
            mocker.call.add_subparsers(a=1, b=2, c=3),
            mocker.call.add_subparsers().add_parser(
                'cmd',
                prog='cmd_prog',
                usage='cmd_usage',
                description='cmd_description',
                epilog='cmd_epilog',
                formatter_class='cmd_formatter_class',
            ),
            mocker.call.add_subparsers().add_parser(
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

    def test_get_kwargs(self, mocker):
        mock_isclass = mocker.patch.object(
            inspect, 'isclass', return_value=False
        )
        mock_ismethod = mocker.patch.object(
            inspect, 'ismethod', return_value=False
        )
        mock_getargspec = mocker.patch.object(
            inspect, 'getargspec',
            return_value=inspect.ArgSpec(('a', 'b', 'c'), None, None, None)
        )
        func1 = mocker.Mock(__doc__='')
        func2 = mocker.Mock()
        sa = cli_tools.ScriptAdaptor(func1, False)

        result = sa.get_kwargs(func2, argparse.Namespace(a=1, b=2, c=3, d=4))

        assert result == dict(a=1, b=2, c=3)
        mock_isclass.assert_called_once_with(func2)
        mock_getargspec.assert_called_once_with(func2)
        mock_ismethod.assert_called_once_with(func2)

    def test_get_kwargs_compatibility(self, mocker):
        mock_isclass = mocker.patch.object(
            inspect, 'isclass', return_value=False
        )
        mock_ismethod = mocker.patch.object(
            inspect, 'ismethod', return_value=False
        )
        mock_getargspec = mocker.patch.object(
            inspect, 'getargspec',
            return_value=inspect.ArgSpec(('a', 'b', 'c'), None, None, None)
        )
        func = mocker.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)

        result = sa.get_kwargs(argparse.Namespace(a=1, b=2, c=3, d=4))

        assert result == dict(a=1, b=2, c=3)
        mock_isclass.assert_called_once_with(func)
        mock_getargspec.assert_called_once_with(func)
        mock_ismethod.assert_called_once_with(func)

    def test_get_kwargs_method(self, mocker):
        mock_isclass = mocker.patch.object(
            inspect, 'isclass', return_value=False
        )
        mock_ismethod = mocker.patch.object(
            inspect, 'ismethod', return_value=True
        )
        mock_getargspec = mocker.patch.object(
            inspect, 'getargspec', return_value=inspect.ArgSpec(
                ('self', 'a', 'b', 'c'), None, None, None
            )
        )
        func1 = mocker.Mock(__doc__='')
        func2 = mocker.Mock()
        sa = cli_tools.ScriptAdaptor(func1, False)

        result = sa.get_kwargs(func2, argparse.Namespace(a=1, b=2, c=3, d=4))

        assert result == dict(a=1, b=2, c=3)
        mock_isclass.assert_called_once_with(func2)
        mock_getargspec.assert_called_once_with(func2)
        mock_ismethod.assert_called_once_with(func2)

    def test_get_kwargs_class_new(self, mocker):
        mock_isclass = mocker.patch.object(
            inspect, 'isclass', return_value=True
        )
        mock_ismethod = mocker.patch.object(
            inspect, 'ismethod', return_value=False
        )
        mock_getargspec = mocker.patch.object(
            inspect, 'getargspec', side_effect=[
                inspect.ArgSpec(('cls', 'a', 'b', 'c'), None, None, None),
            ]
        )
        func1 = mocker.Mock(__doc__='')
        func2 = mocker.Mock()
        sa = cli_tools.ScriptAdaptor(func1, False)

        result = sa.get_kwargs(func2, argparse.Namespace(a=1, b=2, c=3, d=4))

        assert result == dict(a=1, b=2, c=3)
        mock_isclass.assert_called_once_with(func2)
        mock_getargspec.assert_has_calls([
            mocker.call(func2.__new__),
        ])
        assert mock_getargspec.call_count == 1
        assert not mock_ismethod.called

    def test_get_kwargs_class_init(self, mocker):
        mock_isclass = mocker.patch.object(
            inspect, 'isclass', return_value=True
        )
        mock_ismethod = mocker.patch.object(
            inspect, 'ismethod', return_value=False
        )
        mock_getargspec = mocker.patch.object(
            inspect, 'getargspec', side_effect=[
                TypeError,
                inspect.ArgSpec(('self', 'a', 'b', 'c'), None, None, None),
            ]
        )
        func1 = mocker.Mock(__doc__='')
        func2 = mocker.Mock()
        sa = cli_tools.ScriptAdaptor(func1, False)

        result = sa.get_kwargs(func2, argparse.Namespace(a=1, b=2, c=3, d=4))

        assert result == dict(a=1, b=2, c=3)
        mock_isclass.assert_called_once_with(func2)
        mock_getargspec.assert_has_calls([
            mocker.call(func2.__new__),
            mocker.call(func2.__init__),
        ])
        assert mock_getargspec.call_count == 2
        assert not mock_ismethod.called

    def test_get_kwargs_class_nofunc(self, mocker):
        mock_isclass = mocker.patch.object(
            inspect, 'isclass', return_value=True
        )
        mock_ismethod = mocker.patch.object(
            inspect, 'ismethod', return_value=False
        )
        mock_getargspec = mocker.patch.object(
            inspect, 'getargspec', side_effect=[
                TypeError,
                TypeError,
                inspect.ArgSpec(('self', 'a', 'b', 'c'), None, None, None),
            ]
        )
        func1 = mocker.Mock(__doc__='')
        func2 = mocker.Mock()
        sa = cli_tools.ScriptAdaptor(func1, False)

        result = sa.get_kwargs(func2, argparse.Namespace(a=1, b=2, c=3, d=4))

        assert result == {}
        mock_isclass.assert_called_once_with(func2)
        mock_getargspec.assert_has_calls([
            mocker.call(func2.__new__),
            mocker.call(func2.__init__),
        ])
        assert mock_getargspec.call_count == 2
        assert not mock_ismethod.called

    def test_get_kwargs_extra(self, mocker):
        mock_isclass = mocker.patch.object(
            inspect, 'isclass', return_value=False
        )
        mock_ismethod = mocker.patch.object(
            inspect, 'ismethod', return_value=False
        )
        mock_getargspec = mocker.patch.object(
            inspect, 'getargspec',
            return_value=inspect.ArgSpec(('a', 'b', 'c'), None, 'kwargs', None)
        )
        func1 = mocker.Mock(__doc__='')
        func2 = mocker.Mock()
        sa = cli_tools.ScriptAdaptor(func1, False)

        result = sa.get_kwargs(func2, argparse.Namespace(a=1, b=2, c=3, d=4))

        assert result == dict(a=1, b=2, c=3, d=4)
        mock_isclass.assert_called_once_with(func2)
        mock_getargspec.assert_called_once_with(func2)
        mock_ismethod.assert_called_once_with(func2)

    def test_get_kwargs_required(self, mocker):
        mock_isclass = mocker.patch.object(
            inspect, 'isclass', return_value=False
        )
        mock_ismethod = mocker.patch.object(
            inspect, 'ismethod', return_value=False
        )
        mock_getargspec = mocker.patch.object(
            inspect, 'getargspec',
            return_value=inspect.ArgSpec(('a', 'b', 'c'), None, None, None)
        )
        func1 = mocker.Mock(__doc__='')
        func2 = mocker.Mock()
        sa = cli_tools.ScriptAdaptor(func1, False)

        with pytest.raises(AttributeError):
            sa.get_kwargs(func2, argparse.Namespace(a=1, b=2))
        mock_isclass.assert_called_once_with(func2)
        mock_getargspec.assert_called_once_with(func2)
        mock_ismethod.assert_called_once_with(func2)

    def test_get_kwargs_optional(self, mocker):
        mock_isclass = mocker.patch.object(
            inspect, 'isclass', return_value=False
        )
        mock_ismethod = mocker.patch.object(
            inspect, 'ismethod', return_value=False
        )
        mock_getargspec = mocker.patch.object(
            inspect, 'getargspec',
            return_value=inspect.ArgSpec(('a', 'b', 'c'), None, None, (10,))
        )
        func1 = mocker.Mock(__doc__='')
        func2 = mocker.Mock()
        sa = cli_tools.ScriptAdaptor(func1, False)

        result = sa.get_kwargs(func2, argparse.Namespace(a=1, b=2))

        assert result == dict(a=1, b=2)
        mock_isclass.assert_called_once_with(func2)
        mock_getargspec.assert_called_once_with(func2)
        mock_ismethod.assert_called_once_with(func2)

    def test_safe_call(self, mocker):
        mocker.patch('sys.exc_info')
        mocker.patch.object(inspect, 'isgeneratorfunction', return_value=False)
        mock_get_kwargs = mocker.patch.object(
            cli_tools.ScriptAdaptor, 'get_kwargs',
            return_value=dict(a=1, b=2, c=3)
        )
        func = mocker.Mock(__doc__='', return_value='result')
        sa = cli_tools.ScriptAdaptor(func, False)
        args = mocker.Mock(debug=False)

        result = sa.safe_call(args)

        assert result == ('result', None)
        mock_get_kwargs.assert_called_once_with(func, args)
        func.assert_called_once_with(a=1, b=2, c=3)

    def test_safe_call_exc(self, mocker):
        mocker.patch('sys.exc_info', return_value=('type', 'exception', 'tb'))
        mocker.patch.object(inspect, 'isgeneratorfunction', return_value=False)
        mock_get_kwargs = mocker.patch.object(
            cli_tools.ScriptAdaptor, 'get_kwargs',
            return_value=dict(a=1, b=2, c=3)
        )
        func = mocker.Mock(__doc__='', side_effect=ExceptionForTest)
        sa = cli_tools.ScriptAdaptor(func, False)
        args = mocker.Mock(debug=False)

        result = sa.safe_call(args)

        assert result == (None, ('type', 'exception', 'tb'))
        mock_get_kwargs.assert_called_once_with(func, args)
        func.assert_called_once_with(a=1, b=2, c=3)

    def test_safe_call_exc_debug(self, mocker):
        mock_exc_info = mocker.patch('sys.exc_info')
        mocker.patch.object(inspect, 'isgeneratorfunction', return_value=False)
        mock_get_kwargs = mocker.patch.object(
            cli_tools.ScriptAdaptor, 'get_kwargs',
            return_value=dict(a=1, b=2, c=3)
        )
        func = mocker.Mock(__doc__='', side_effect=ExceptionForTest)
        sa = cli_tools.ScriptAdaptor(func, False)
        args = mocker.Mock(debug=True)

        with pytest.raises(ExceptionForTest):
            sa.safe_call(args)
        mock_get_kwargs.assert_called_once_with(func, args)
        func.assert_called_once_with(a=1, b=2, c=3)
        assert not mock_exc_info.called

    def test_safe_call_class(self, mocker):
        mocker.patch('sys.exc_info')
        mocker.patch.object(inspect, 'isgeneratorfunction', return_value=False)
        mock_get_kwargs = mocker.patch.object(
            cli_tools.ScriptAdaptor, 'get_kwargs',
            return_value=dict(a=1, b=2, c=3)
        )
        obj = mocker.Mock(**{
            'run.return_value': 'result',
        })
        func = mocker.Mock(__doc__='', return_value=obj)
        sa = cli_tools.ScriptAdaptor(func, True)
        args = mocker.Mock(debug=False)

        result = sa.safe_call(args)

        assert result == ('result', None)
        mock_get_kwargs.assert_has_calls([
            mocker.call(func, args),
            mocker.call(obj.run, args),
        ])
        func.assert_called_once_with(a=1, b=2, c=3)
        obj.run.assert_called_once_with(a=1, b=2, c=3)

    def test_safe_call_class_exc(self, mocker):
        mocker.patch('sys.exc_info', return_value=('type', 'exception', 'tb'))
        mocker.patch.object(inspect, 'isgeneratorfunction', return_value=False)
        mock_get_kwargs = mocker.patch.object(
            cli_tools.ScriptAdaptor, 'get_kwargs',
            return_value=dict(a=1, b=2, c=3)
        )
        obj = mocker.Mock(**{
            'run.side_effect': ExceptionForTest,
        })
        func = mocker.Mock(__doc__='', return_value=obj)
        sa = cli_tools.ScriptAdaptor(func, True)
        args = mocker.Mock(debug=False)

        result = sa.safe_call(args)

        assert result == (None, ('type', 'exception', 'tb'))
        mock_get_kwargs.assert_has_calls([
            mocker.call(func, args),
            mocker.call(obj.run, args),
        ])
        func.assert_called_once_with(a=1, b=2, c=3)
        obj.run.assert_called_once_with(a=1, b=2, c=3)

    def test_safe_call_class_exc_debug(self, mocker):
        mock_exc_info = mocker.patch(
            'sys.exc_info', return_value=('type', 'exception', 'tb')
        )
        mocker.patch.object(inspect, 'isgeneratorfunction', return_value=False)
        mock_get_kwargs = mocker.patch.object(
            cli_tools.ScriptAdaptor, 'get_kwargs',
            return_value=dict(a=1, b=2, c=3)
        )
        obj = mocker.Mock(**{
            'run.side_effect': ExceptionForTest,
        })
        func = mocker.Mock(__doc__='', return_value=obj)
        sa = cli_tools.ScriptAdaptor(func, True)
        args = mocker.Mock(debug=True)

        with pytest.raises(ExceptionForTest):
            sa.safe_call(args)
        mock_get_kwargs.assert_has_calls([
            mocker.call(func, args),
            mocker.call(obj.run, args),
        ])
        func.assert_called_once_with(a=1, b=2, c=3)
        obj.run.assert_called_once_with(a=1, b=2, c=3)
        assert not mock_exc_info.called

    def test_safe_call_proc_func(self, mocker):
        mocker.patch('sys.exc_info')
        mocker.patch.object(inspect, 'isgeneratorfunction', return_value=False)
        mock_get_kwargs = mocker.patch.object(
            cli_tools.ScriptAdaptor, 'get_kwargs',
            return_value=dict(a=1, b=2, c=3)
        )
        func = mocker.Mock(__doc__='', return_value='result')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._processor = mocker.Mock()
        args = mocker.Mock(debug=False)

        result = sa.safe_call(args)

        assert result == ('result', None)
        sa._processor.assert_called_once_with(args)
        mock_get_kwargs.assert_called_once_with(func, args)
        func.assert_called_once_with(a=1, b=2, c=3)

    def test_safe_call_proc_gen_nopost(self, mocker):
        mocker.patch('sys.exc_info')
        mocker.patch.object(inspect, 'isgeneratorfunction', return_value=True)
        mock_get_kwargs = mocker.patch.object(
            cli_tools.ScriptAdaptor, 'get_kwargs',
            return_value=dict(a=1, b=2, c=3)
        )
        func = mocker.Mock(__doc__='', return_value='result')
        gen = mocker.Mock(**{
            'next.side_effect': StopIteration(),
        })
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._processor = MockGenFunc(gen)
        args = mocker.Mock(debug=False)

        result = sa.safe_call(args)

        assert result == ('result', None)
        gen.assert_has_calls([
            mocker.call.call(args),
            mocker.call.next(),
        ])
        assert len(gen.method_calls) == 2
        mock_get_kwargs.assert_called_once_with(func, args)
        func.assert_called_once_with(a=1, b=2, c=3)

    def test_safe_call_proc_gen_post_res_noreplace(self, mocker):
        mocker.patch('sys.exc_info')
        mocker.patch.object(inspect, 'isgeneratorfunction', return_value=True)
        mock_get_kwargs = mocker.patch.object(
            cli_tools.ScriptAdaptor, 'get_kwargs',
            return_value=dict(a=1, b=2, c=3)
        )
        func = mocker.Mock(__doc__='', return_value='result')
        gen = mocker.Mock(**{
            'send.side_effect': StopIteration(),
        })
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._processor = MockGenFunc(gen)
        args = mocker.Mock(debug=False)

        result = sa.safe_call(args)

        assert result == ('result', None)
        gen.assert_has_calls([
            mocker.call.call(args),
            mocker.call.next(),
            mocker.call.send('result'),
            mocker.call.close(),
        ])
        assert len(gen.method_calls) == 4
        mock_get_kwargs.assert_called_once_with(func, args)
        func.assert_called_once_with(a=1, b=2, c=3)

    def test_safe_call_proc_gen_post_res_replace(self, mocker):
        mocker.patch('sys.exc_info')
        mocker.patch.object(inspect, 'isgeneratorfunction', return_value=True)
        mock_get_kwargs = mocker.patch.object(
            cli_tools.ScriptAdaptor, 'get_kwargs',
            return_value=dict(a=1, b=2, c=3)
        )
        func = mocker.Mock(__doc__='', return_value='result')
        gen = mocker.Mock(**{
            'send.return_value': 'override',
        })
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._processor = MockGenFunc(gen)
        args = mocker.Mock(debug=False)

        result = sa.safe_call(args)

        assert result == ('override', None)
        gen.assert_has_calls([
            mocker.call.call(args),
            mocker.call.next(),
            mocker.call.send('result'),
            mocker.call.close(),
        ])
        assert len(gen.method_calls) == 4
        mock_get_kwargs.assert_called_once_with(func, args)
        func.assert_called_once_with(a=1, b=2, c=3)

    def test_safe_call_proc_gen_post_exc_noreplace(self, mocker):
        mocker.patch('sys.exc_info', return_value=('type', 'exception', 'tb'))
        mocker.patch.object(inspect, 'isgeneratorfunction', return_value=True)
        mock_get_kwargs = mocker.patch.object(
            cli_tools.ScriptAdaptor, 'get_kwargs',
            return_value=dict(a=1, b=2, c=3)
        )
        func = mocker.Mock(__doc__='', side_effect=ExceptionForTest)
        gen = mocker.Mock(**{
            'throw.return_value': 'thrown',
        })
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._processor = MockGenFunc(gen)
        args = mocker.Mock(debug=False)

        result = sa.safe_call(args)

        assert result == ('thrown', None)
        gen.assert_has_calls([
            mocker.call.call(args),
            mocker.call.next(),
            mocker.call.throw('type', 'exception', 'tb'),
            mocker.call.close(),
        ])
        assert len(gen.method_calls) == 4
        mock_get_kwargs.assert_called_once_with(func, args)
        func.assert_called_once_with(a=1, b=2, c=3)

    def test_safe_call_proc_gen_post_exc_replace(self, mocker):
        mocker.patch(
            'sys.exc_info', side_effect=[
                ('type', 'exception', 'tb'),
                ('otype', 'something', 'bt'),
            ]
        )
        mocker.patch.object(inspect, 'isgeneratorfunction', return_value=True)
        mock_get_kwargs = mocker.patch.object(
            cli_tools.ScriptAdaptor, 'get_kwargs',
            return_value=dict(a=1, b=2, c=3)
        )
        func = mocker.Mock(__doc__='', side_effect=ExceptionForTest)
        gen = mocker.Mock(**{
            'throw.side_effect': ExceptionForTest(),
        })
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._processor = MockGenFunc(gen)
        args = mocker.Mock(debug=False)

        result = sa.safe_call(args)

        assert result == (None, ('otype', 'something', 'bt'))
        gen.assert_has_calls([
            mocker.call.call(args),
            mocker.call.next(),
            mocker.call.throw('type', 'exception', 'tb'),
            mocker.call.close(),
        ])
        assert len(gen.method_calls) == 4
        mock_get_kwargs.assert_called_once_with(func, args)
        func.assert_called_once_with(a=1, b=2, c=3)

    def test_console_basic(self, mocker):
        mock_ArgumentParser = mocker.patch.object(
            argparse, 'ArgumentParser', return_value=mocker.Mock(**{
                'parse_args.return_value': 'parsed args',
            })
        )
        mock_setup_args = mocker.patch.object(
            cli_tools.ScriptAdaptor, 'setup_args'
        )
        mock_safe_call = mocker.patch.object(
            cli_tools.ScriptAdaptor, 'safe_call',
            return_value=('result', None)
        )
        func = mocker.Mock(__doc__='')
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
        assert result == 'result'

    def test_console_exception(self, mocker):
        mock_ArgumentParser = mocker.patch.object(
            argparse, 'ArgumentParser', return_value=mocker.Mock(**{
                'parse_args.return_value': 'parsed args',
            })
        )
        mock_setup_args = mocker.patch.object(
            cli_tools.ScriptAdaptor, 'setup_args'
        )
        mock_safe_call = mocker.patch.object(
            cli_tools.ScriptAdaptor, 'safe_call',
            return_value=(None, ('type', 'exception', 'tb'))
        )
        func = mocker.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa.prog = 'program'
        sa.usage = 'usage'
        sa.description = 'description'
        sa.epilog = 'epilog'
        sa.formatter_class = 'formatter_class'

        result = sa.console(args='override args')

        assert not mock_ArgumentParser.called
        assert not mock_setup_args.called
        mock_safe_call.assert_called_once_with('override args')
        assert result == 'exception'

    def test_console_subcmd(self, mocker):
        mock_ArgumentParser = mocker.patch.object(
            argparse, 'ArgumentParser', return_value=mocker.Mock(**{
                'parse_args.return_value': 'parsed args',
            })
        )
        mock_setup_args = mocker.patch.object(
            cli_tools.ScriptAdaptor, 'setup_args'
        )
        mock_safe_call = mocker.patch.object(
            cli_tools.ScriptAdaptor, 'safe_call', return_value=('result', None)
        )
        func = mocker.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa.do_subs = True
        adaptor = mocker.Mock(**{'safe_call.return_value': ('tluser', None)})
        args = mocker.Mock(**{sa._subcmd_attr: adaptor})

        result = sa.console(args=args)

        assert not mock_ArgumentParser.called
        assert not mock_setup_args.called
        assert not mock_safe_call.called
        adaptor.safe_call.assert_called_once_with(args)
        assert result == 'tluser'

    def test_get_subcommands_nosubs(self, mocker):
        mock_process_entrypoints = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_process_entrypoints'
        )
        func = mocker.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._subcommands = mocker.Mock(**{'items.return_value': [
            ('cmd', mocker.Mock(_func='subcmd')),
            ('dmc', mocker.Mock(_func='subdmc')),
        ]})

        result = sa.get_subcommands()

        assert result == {}
        assert not mock_process_entrypoints.called

    def test_get_subcommands(self, mocker):
        mock_process_entrypoints = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_process_entrypoints'
        )
        func = mocker.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func, False)
        sa._subcommands = mocker.Mock(**{'items.return_value': [
            ('cmd', mocker.Mock(_func='subcmd')),
            ('dmc', mocker.Mock(_func='subdmc')),
        ]})
        sa.do_subs = True

        result = sa.get_subcommands()

        assert result == dict(cmd='subcmd', dmc='subdmc')
        mock_process_entrypoints.assert_called_once_with()


class TestDecorators(object):
    def test_console(self, mocker):
        mock_get_adaptor = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_get_adaptor', return_value=mocker.Mock()
        )
        func = mocker.Mock()
        result = cli_tools.console(func)

        mock_get_adaptor.assert_called_once_with(func)
        assert result == func

    def test_prog(self, mocker):
        mock_get_adaptor = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_get_adaptor', return_value=mocker.Mock()
        )
        decorator = cli_tools.prog('program')

        assert callable(decorator)
        assert not mock_get_adaptor.called

        func = mocker.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        assert result == func
        assert mock_get_adaptor.return_value.prog == 'program'

    def test_usage(self, mocker):
        mock_get_adaptor = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_get_adaptor', return_value=mocker.Mock()
        )
        decorator = cli_tools.usage('text')

        assert callable(decorator)
        assert not mock_get_adaptor.called

        func = mocker.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        assert result == func
        assert mock_get_adaptor.return_value.usage == 'text'

    def test_description(self, mocker):
        mock_get_adaptor = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_get_adaptor', return_value=mocker.Mock()
        )
        decorator = cli_tools.description('text')

        assert callable(decorator)
        assert not mock_get_adaptor.called

        func = mocker.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        assert result == func
        assert mock_get_adaptor.return_value.description == 'text'

    def test_epilog(self, mocker):
        mock_get_adaptor = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_get_adaptor', return_value=mocker.Mock()
        )
        decorator = cli_tools.epilog('text')

        assert callable(decorator)
        assert not mock_get_adaptor.called

        func = mocker.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        assert result == func
        assert mock_get_adaptor.return_value.epilog == 'text'

    def test_formatter_class(self, mocker):
        mock_get_adaptor = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_get_adaptor', return_value=mocker.Mock()
        )
        decorator = cli_tools.formatter_class('class')

        assert callable(decorator)
        assert not mock_get_adaptor.called

        func = mocker.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        assert result == func
        assert mock_get_adaptor.return_value.formatter_class == 'class'

    def test_argument_nogroup(self, mocker):
        mock_get_adaptor = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_get_adaptor', return_value=mocker.Mock()
        )
        decorator = cli_tools.argument(1, 2, 3, a=4, b=5, c=6)

        assert callable(decorator)
        assert not mock_get_adaptor.called

        func = mocker.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        assert result == func
        mock_get_adaptor.return_value._add_argument.assert_called_once_with(
            (1, 2, 3), dict(a=4, b=5, c=6), group=None)

    def test_argument_withgroup(self, mocker):
        mock_get_adaptor = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_get_adaptor', return_value=mocker.Mock()
        )
        decorator = cli_tools.argument(1, 2, 3, a=4, b=5, c=6, group='group')

        assert callable(decorator)
        assert not mock_get_adaptor.called

        func = mocker.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        assert result == func
        mock_get_adaptor.return_value._add_argument.assert_called_once_with(
            (1, 2, 3), dict(a=4, b=5, c=6), group='group')

    def test_argument_group(self, mocker):
        mock_get_adaptor = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_get_adaptor', return_value=mocker.Mock()
        )
        decorator = cli_tools.argument_group('group', a=1, b=2, c=3)

        assert callable(decorator)
        assert not mock_get_adaptor.called

        func = mocker.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        assert result == func
        mock_get_adaptor.return_value._add_group.assert_called_once_with(
            'group', 'group', dict(a=1, b=2, c=3))

    def test_mutually_exclusive_group(self, mocker):
        mock_get_adaptor = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_get_adaptor', return_value=mocker.Mock()
        )
        decorator = cli_tools.mutually_exclusive_group('group', a=1, b=2, c=3)

        assert callable(decorator)
        assert not mock_get_adaptor.called

        func = mocker.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        assert result == func
        mock_get_adaptor.return_value._add_group.assert_called_once_with(
            'group', 'exclusive', dict(a=1, b=2, c=3))

    def test_subparsers(self, mocker):
        mock_get_adaptor = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_get_adaptor', return_value=mocker.Mock()
        )
        decorator = cli_tools.subparsers(a=1, b=2, c=3)

        assert callable(decorator)
        assert not mock_get_adaptor.called

        func = mocker.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        assert result == func
        assert mock_get_adaptor.return_value.subkwargs == dict(a=1, b=2, c=3)
        assert mock_get_adaptor.return_value.do_subs is True

    def test_load_subcommands(self, mocker):
        mock_get_adaptor = mocker.patch.object(
            cli_tools.ScriptAdaptor, '_get_adaptor', return_value=mocker.Mock()
        )
        decorator = cli_tools.load_subcommands('entrypoint.group')

        assert callable(decorator)
        assert not mock_get_adaptor.called

        func = mocker.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        assert result == func
        mock_get_adaptor.return_value._add_extensions.assert_called_once_with(
            'entrypoint.group')
