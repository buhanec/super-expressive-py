"""Test subexpressions."""

import pytest

from superexpressive import SuperExpressive

SIMPLE = (SuperExpressive()
              .string('hello')
              .any_char
              .string('world'))

FLAGS = (SuperExpressive()
             .unicode
             .case_insensitive
             .string('hello')
             .any_char
             .string('world'))

START_END = (SuperExpressive()
                 .start_of_input
                 .string('hello')
                 .any_char
                 .string('world')
                 .end_of_input)

NAMED_CAPTURE = (SuperExpressive()
                    .named_capture('module')
                    .exactly(2).any_char
                    .end()
                    .named_backreference('module'))

INDEXED_BACKREFERENCE = (SuperExpressive()
                             .capture
                             .exactly(2).any_char
                             .end()
                             .backreference(1))

SECOND_LAYER = SuperExpressive().exactly(2).any_char
FIRST_LAYER = (SuperExpressive()
               .string('outer begin')
               .named_capture('innerSubExpression')
               .optional.subexpression(SECOND_LAYER)
               .end()
               .string('outer end'))


def test_wrong_input_type():
    with pytest.raises(Exception):
        SuperExpressive().subexpression('nope')


def test_simple():
    assert str(
        SuperExpressive()
            .start_of_input
            .at_least(3).digit
            .subexpression(SIMPLE)
            .range('0', '9')
            .end_of_input
    ) == r'^\d{3,}hello.world[0-9]$'


def test_simple_quantified():
    assert str(
        SuperExpressive()
            .start_of_input
            .at_least(3).digit
            .one_or_more.subexpression(SIMPLE)
            .range('0', '9')
            .end_of_input
    ) == r'^\d{3,}(?:hello.world)+[0-9]$'


def test_ignore_flags():
    assert (
        SuperExpressive()
            .line_by_line
            .start_of_input
            .at_least(3).digit
            .subexpression(FLAGS, ignore_flags=True)
            .range('0', '9')
            .end_of_input
            .compile()
    ).flags == SuperExpressive().line_by_line.compile().flags


def test_flags_merge():
    assert (
        SuperExpressive()
            .line_by_line
            .start_of_input
            .at_least(3).digit
            .subexpression(FLAGS, ignore_flags=False)
            .range('0', '9')
            .end_of_input
            .compile()
    ).flags == (FLAGS.compile().flags
                | SuperExpressive().line_by_line.compile().flags)


def test_start_end():
    assert str(
        SuperExpressive(check_simple_start_and_end=True)
            .at_least(3).digit
            .subexpression(START_END, ignore_start_and_end=False)
            .range('0', '9')
    ) == r'\d{3,}^hello.world$[0-9]'


def test_clashing_start_end():
    with pytest.raises(ValueError):
        (SuperExpressive(check_simple_start_and_end=True)
            .end_of_input
            .subexpression(START_END, ignore_start_and_end=False))


def test_no_namespacing():
    assert str(
        SuperExpressive()
            .at_least(3).digit
            .subexpression(NAMED_CAPTURE)
            .range('0', '9')
    ) == r'\d{3,}(?P<module>.{2})\g<module>[0-9]'


def test_namespacing():
    assert str(
        SuperExpressive()
            .at_least(3).digit
            .subexpression(NAMED_CAPTURE, namespace='yolo')
            .range('0', '9')
    ) == r'\d{3,}(?P<yolomodule>.{2})\g<yolomodule>[0-9]'


def test_name_collision():
    with pytest.raises(ValueError):
        (SuperExpressive()
            .named_capture('module')
                .at_least(3).digit
            .end()
            .subexpression(NAMED_CAPTURE)
            .range('0', '9'))


def test_name_collision_with_namespace():
    with pytest.raises(ValueError):
        (SuperExpressive()
            .named_capture('yolomodule')
                .at_least(3).digit
            .end()
            .subexpression(NAMED_CAPTURE, namespace='yolo')
            .range('0', '9'))


def test_indexed_backreferencing():
    assert str(
        SuperExpressive()
        .capture
            .at_least(3).digit
        .end()
        .subexpression(INDEXED_BACKREFERENCE)
        .backreference(1)
        .range('0', '9')
    ) == r'(\d{3,})(.{2})\2\1[0-9]'


def test_deeply_nested():
    assert str(
        SuperExpressive()
        .capture
            .at_least(3).digit
        .end()
        .subexpression(FIRST_LAYER)
        .backreference(1)
        .range('0', '9')
    ) == r'(\d{3,})outer begin(?P<innerSubExpression>(?:.{2})?)outer end\1[0-9]'
