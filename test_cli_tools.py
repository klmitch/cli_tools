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

import argparse
import mock
import unittest2

import cli_tools


class TestException(Exception):
    pass


class TestCleanText(unittest2.TestCase):
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


class TestScriptAdaptor(unittest2.TestCase):
    def test_get_adaptor_unset(self):
        func = mock.Mock(__doc__='', _script_adaptor=None)

        result = cli_tools.ScriptAdaptor._get_adaptor(func)

        self.assertIsInstance(result, cli_tools.ScriptAdaptor)
        self.assertEqual(func._script_adaptor, result)
        self.assertEqual(func.processor, result.processor)
        self.assertEqual(func.setup_args, result.setup_args)
        self.assertEqual(func.get_kwargs, result.get_kwargs)
        self.assertEqual(func.safe_call, result.safe_call)
        self.assertEqual(func.console, result.console)

    def test_get_adaptor_set(self):
        func = mock.Mock(__doc__='', processor='processor',
                         setup_args='setup_args', get_kwargs='get_kwargs',
                         safe_call='safe_call', console='console')
        sa = cli_tools.ScriptAdaptor(func)
        func._script_adaptor = sa

        result = cli_tools.ScriptAdaptor._get_adaptor(func)

        self.assertEqual(result, sa)
        self.assertEqual(func.processor, 'processor')
        self.assertEqual(func.setup_args, 'setup_args')
        self.assertEqual(func.get_kwargs, 'get_kwargs')
        self.assertEqual(func.safe_call, 'safe_call')
        self.assertEqual(func.console, 'console')

    def test_init(self):
        func = mock.Mock(__doc__="description")
        sa = cli_tools.ScriptAdaptor(func)

        self.assertEqual(sa._func, func)
        self.assertTrue(callable(sa._processor))
        self.assertEqual(sa._processor('foo'), None)
        self.assertEqual(sa._arguments, [])
        self.assertEqual(sa._groups, {})
        self.assertEqual(sa.prog, None)
        self.assertEqual(sa.usage, None)
        self.assertEqual(sa.description, 'description')
        self.assertEqual(sa.epilog, None)
        self.assertEqual(sa.formatter_class, argparse.HelpFormatter)

    def test_add_argument(self):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func)

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
        sa = cli_tools.ScriptAdaptor(func)

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
        sa = cli_tools.ScriptAdaptor(func)
        sa._groups['group'] = dict(type=None)

        self.assertRaises(argparse.ArgumentError, sa._add_group,
                          'group', 'group', dict(a=1, b=2, c=3))

    def test_processor(self):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func)

        result = sa.processor('func')

        self.assertEqual(result, 'func')
        self.assertEqual(sa._processor, 'func')

    def test_setup_args(self):
        parser = mock.Mock()
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func)
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

    @mock.patch.object(inspect, 'getargspec', return_value=inspect.ArgSpec(
        ('a', 'b', 'c'), None, None, None))
    def test_get_kwargs(self, mock_getargspec):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func)

        result = sa.get_kwargs(argparse.Namespace(a=1, b=2, c=3, d=4))

        self.assertEqual(result, dict(a=1, b=2, c=3))
        mock_getargspec.assert_called_once_with(func)

    @mock.patch.object(inspect, 'getargspec', return_value=inspect.ArgSpec(
        ('a', 'b', 'c'), None, 'kwargs', None))
    def test_get_kwargs_extra(self, mock_getargspec):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func)

        result = sa.get_kwargs(argparse.Namespace(a=1, b=2, c=3, d=4))

        self.assertEqual(result, dict(a=1, b=2, c=3, d=4))
        mock_getargspec.assert_called_once_with(func)

    @mock.patch.object(inspect, 'getargspec', return_value=inspect.ArgSpec(
        ('a', 'b', 'c'), None, None, None))
    def test_get_kwargs_required(self, mock_getargspec):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func)

        self.assertRaises(AttributeError, sa.get_kwargs,
                          argparse.Namespace(a=1, b=2))
        mock_getargspec.assert_called_once_with(func)

    @mock.patch.object(inspect, 'getargspec', return_value=inspect.ArgSpec(
        ('a', 'b', 'c'), None, None, (10,)))
    def test_get_kwargs_optional(self, mock_getargspec):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func)

        result = sa.get_kwargs(argparse.Namespace(a=1, b=2))

        self.assertEqual(result, dict(a=1, b=2))
        mock_getargspec.assert_called_once_with(func)

    def test_safe_call(self):
        func = mock.Mock(__doc__='', return_value='result')
        sa = cli_tools.ScriptAdaptor(func)

        result = sa.safe_call(dict(a=1, b=2, c=3))

        self.assertEqual(result, ('result', None))
        func.assert_called_once_with(a=1, b=2, c=3)

    @mock.patch('sys.exc_info', return_value='exception info')
    def test_safe_call_noargs(self, mock_exc_info):
        func = mock.Mock(__doc__='', side_effect=TestException("testing"))
        sa = cli_tools.ScriptAdaptor(func)

        result = sa.safe_call(dict(a=1, b=2, c=3))

        self.assertEqual(result, (None, 'exception info'))
        func.assert_called_once_with(a=1, b=2, c=3)

    def test_safe_call_exception_withdebug(self):
        func = mock.Mock(__doc__='', side_effect=TestException("testing"))
        sa = cli_tools.ScriptAdaptor(func)

        self.assertRaises(TestException, sa.safe_call, dict(a=1, b=2, c=3),
                          argparse.Namespace(debug=True))
        func.assert_called_once_with(a=1, b=2, c=3)

    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=False)
    @mock.patch.object(argparse, 'ArgumentParser', return_value=mock.Mock(**{
        'parse_args.return_value': 'parsed args',
    }))
    @mock.patch.object(cli_tools.ScriptAdaptor, 'setup_args')
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value='keyword args')
    @mock.patch.object(cli_tools.ScriptAdaptor, 'safe_call',
                       return_value=('result', None))
    def test_console_basic(self, mock_safe_call, mock_get_kwargs,
                           mock_setup_args, mock_ArgumentParser,
                           mock_isgeneratorfunction):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func)
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
        mock_get_kwargs.assert_called_once_with('parsed args')
        mock_safe_call.assert_called_once_with('keyword args', 'parsed args')
        self.assertEqual(result, 'result')

    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=False)
    @mock.patch.object(argparse, 'ArgumentParser', return_value=mock.Mock(**{
        'parse_args.return_value': 'parsed args',
    }))
    @mock.patch.object(cli_tools.ScriptAdaptor, 'setup_args')
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value='keyword args')
    @mock.patch.object(cli_tools.ScriptAdaptor, 'safe_call',
                       return_value=(None, ('type', 'exception', 'tb')))
    def test_console_exception(self, mock_safe_call, mock_get_kwargs,
                               mock_setup_args, mock_ArgumentParser,
                               mock_isgeneratorfunction):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func)
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
        mock_get_kwargs.assert_called_once_with('parsed args')
        mock_safe_call.assert_called_once_with('keyword args', 'parsed args')
        self.assertEqual(result, 'exception')

    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=False)
    @mock.patch.object(argparse, 'ArgumentParser', return_value=mock.Mock(**{
        'parse_args.return_value': 'parsed args',
    }))
    @mock.patch.object(cli_tools.ScriptAdaptor, 'setup_args')
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value='keyword args')
    @mock.patch.object(cli_tools.ScriptAdaptor, 'safe_call',
                       return_value=('result', None))
    def test_console_processor_func(self, mock_safe_call, mock_get_kwargs,
                                    mock_setup_args, mock_ArgumentParser,
                                    mock_isgeneratorfunction):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func)
        sa._processor = mock.Mock()

        result = sa.console('override args')

        self.assertFalse(mock_ArgumentParser.called)
        sa._processor.assert_called_once_with('override args')
        mock_get_kwargs.assert_called_once_with('override args')
        mock_safe_call.assert_called_once_with('keyword args', 'override args')
        self.assertEqual(result, 'result')

    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=True)
    @mock.patch.object(argparse, 'ArgumentParser', return_value=mock.Mock(**{
        'parse_args.return_value': 'parsed args',
    }))
    @mock.patch.object(cli_tools.ScriptAdaptor, 'setup_args')
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value='keyword args')
    @mock.patch.object(cli_tools.ScriptAdaptor, 'safe_call',
                       return_value=('result', None))
    def test_console_processor_gen_nopost(self, mock_safe_call,
                                          mock_get_kwargs, mock_setup_args,
                                          mock_ArgumentParser,
                                          mock_isgeneratorfunction):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func)
        generator = mock.Mock(**{
            'next.side_effect': StopIteration,
        })
        sa._processor = mock.Mock(return_value=generator)

        result = sa.console('override args')

        self.assertFalse(mock_ArgumentParser.called)
        sa._processor.assert_called_once_with('override args')
        generator.assert_has_calls([
            mock.call.next(),
        ])
        self.assertEqual(len(generator.method_calls), 1)
        mock_get_kwargs.assert_called_once_with('override args')
        mock_safe_call.assert_called_once_with('keyword args', 'override args')
        self.assertEqual(result, 'result')

    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=True)
    @mock.patch.object(argparse, 'ArgumentParser', return_value=mock.Mock(**{
        'parse_args.return_value': 'parsed args',
    }))
    @mock.patch.object(cli_tools.ScriptAdaptor, 'setup_args')
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value='keyword args')
    @mock.patch.object(cli_tools.ScriptAdaptor, 'safe_call',
                       return_value=('result', None))
    def test_console_processor_gen_override(self, mock_safe_call,
                                            mock_get_kwargs, mock_setup_args,
                                            mock_ArgumentParser,
                                            mock_isgeneratorfunction):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func)
        generator = mock.Mock(**{
            'send.return_value': 'override result',
        })
        sa._processor = mock.Mock(return_value=generator)

        result = sa.console('override args')

        self.assertFalse(mock_ArgumentParser.called)
        sa._processor.assert_called_once_with('override args')
        generator.assert_has_calls([
            mock.call.next(),
            mock.call.send('result'),
            mock.call.close(),
        ])
        self.assertEqual(len(generator.method_calls), 3)
        mock_get_kwargs.assert_called_once_with('override args')
        mock_safe_call.assert_called_once_with('keyword args', 'override args')
        self.assertEqual(result, 'override result')

    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=True)
    @mock.patch.object(argparse, 'ArgumentParser', return_value=mock.Mock(**{
        'parse_args.return_value': 'parsed args',
    }))
    @mock.patch.object(cli_tools.ScriptAdaptor, 'setup_args')
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value='keyword args')
    @mock.patch.object(cli_tools.ScriptAdaptor, 'safe_call',
                       return_value=('result', None))
    def test_console_processor_gen_no_override(self, mock_safe_call,
                                               mock_get_kwargs,
                                               mock_setup_args,
                                               mock_ArgumentParser,
                                               mock_isgeneratorfunction):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func)
        generator = mock.Mock(**{
            'send.side_effect': StopIteration,
        })
        sa._processor = mock.Mock(return_value=generator)

        result = sa.console('override args')

        self.assertFalse(mock_ArgumentParser.called)
        sa._processor.assert_called_once_with('override args')
        generator.assert_has_calls([
            mock.call.next(),
            mock.call.send('result'),
            mock.call.close(),
        ])
        self.assertEqual(len(generator.method_calls), 3)
        mock_get_kwargs.assert_called_once_with('override args')
        mock_safe_call.assert_called_once_with('keyword args', 'override args')
        self.assertEqual(result, 'result')

    @mock.patch.object(inspect, 'isgeneratorfunction', return_value=True)
    @mock.patch.object(argparse, 'ArgumentParser', return_value=mock.Mock(**{
        'parse_args.return_value': 'parsed args',
    }))
    @mock.patch.object(cli_tools.ScriptAdaptor, 'setup_args')
    @mock.patch.object(cli_tools.ScriptAdaptor, 'get_kwargs',
                       return_value='keyword args')
    @mock.patch.object(cli_tools.ScriptAdaptor, 'safe_call',
                       return_value=(None, ('type', 'exception', 'tb')))
    def test_console_processor_gen_throw(self, mock_safe_call, mock_get_kwargs,
                                         mock_setup_args, mock_ArgumentParser,
                                         mock_isgeneratorfunction):
        func = mock.Mock(__doc__='')
        sa = cli_tools.ScriptAdaptor(func)
        generator = mock.Mock(**{
            'throw.side_effect': TestException("testing"),
        })
        sa._processor = mock.Mock(return_value=generator)

        result = sa.console('override args')

        self.assertFalse(mock_ArgumentParser.called)
        sa._processor.assert_called_once_with('override args')
        generator.assert_has_calls([
            mock.call.next(),
            mock.call.throw('type', 'exception', 'tb'),
            mock.call.close(),
        ])
        self.assertEqual(len(generator.method_calls), 3)
        mock_get_kwargs.assert_called_once_with('override args')
        mock_safe_call.assert_called_once_with('keyword args', 'override args')
        self.assertEqual(result, 'testing')


class TestDecorators(unittest2.TestCase):
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

    @mock.patch.object(cli_tools, '_clean_text', side_effect=lambda x: x)
    @mock.patch.object(cli_tools.ScriptAdaptor, '_get_adaptor',
                       return_value=mock.Mock())
    def test_usage(self, mock_get_adaptor, mock_clean_text):
        decorator = cli_tools.usage('text')

        self.assertTrue(callable(decorator))
        self.assertFalse(mock_get_adaptor.called)

        func = mock.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        mock_clean_text.assert_called_once_with('text')
        self.assertEqual(result, func)
        self.assertEqual(mock_get_adaptor.return_value.usage, 'text')

    @mock.patch.object(cli_tools, '_clean_text', side_effect=lambda x: x)
    @mock.patch.object(cli_tools.ScriptAdaptor, '_get_adaptor',
                       return_value=mock.Mock())
    def test_description(self, mock_get_adaptor, mock_clean_text):
        decorator = cli_tools.description('text')

        self.assertTrue(callable(decorator))
        self.assertFalse(mock_get_adaptor.called)

        func = mock.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        mock_clean_text.assert_called_once_with('text')
        self.assertEqual(result, func)
        self.assertEqual(mock_get_adaptor.return_value.description, 'text')

    @mock.patch.object(cli_tools, '_clean_text', side_effect=lambda x: x)
    @mock.patch.object(cli_tools.ScriptAdaptor, '_get_adaptor',
                       return_value=mock.Mock())
    def test_epilog(self, mock_get_adaptor, mock_clean_text):
        decorator = cli_tools.epilog('text')

        self.assertTrue(callable(decorator))
        self.assertFalse(mock_get_adaptor.called)

        func = mock.Mock()
        result = decorator(func)

        mock_get_adaptor.assert_called_once_with(func)
        mock_clean_text.assert_called_once_with('text')
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
