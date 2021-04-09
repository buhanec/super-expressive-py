"""Test core expression functionality."""

import re
from typing import Optional
import unicodedata

from hypothesis import example, given
from hypothesis.strategies import integers, sampled_from
import pytest

from superexpressive import SuperExpressive
from tests.const import NAMED_UNICODE


def test_empty() -> None:
    assert str(SuperExpressive()) == ''


@pytest.mark.parametrize('se, flags', [
    (SuperExpressive().line_by_line, re.MULTILINE | re.UNICODE),
    (SuperExpressive().case_insensitive, re.IGNORECASE | re.UNICODE),
    (SuperExpressive().unicode, re.UNICODE),
    (SuperExpressive().ascii, re.ASCII),
    (SuperExpressive().single_line, re.DOTALL | re.UNICODE),
])
def test_flags(se: SuperExpressive, flags: int) -> None:
    assert se.compile().flags == flags


@pytest.mark.parametrize('se, string', [
    (SuperExpressive().any_char, '.'),
    (SuperExpressive().whitespace_char, r'\s'),
    (SuperExpressive().non_whitespace_char, r'\S'),
    (SuperExpressive().digit, r'\d'),
    (SuperExpressive().non_digit, r'\D'),
    (SuperExpressive().word, r'\w'),
    (SuperExpressive().non_word, r'\W'),
    (SuperExpressive().word_boundary, r'\b'),
    (SuperExpressive().non_word_boundary, r'\B'),
    (SuperExpressive().newline, r'\n'),
    (SuperExpressive().carriage_return, r'\r'),
    (SuperExpressive().tab, r'\t'),
    (SuperExpressive().null_byte, r'\x00'),
])
def test_escapes(se: SuperExpressive, string: str) -> None:
    assert str(se) == string


def test_any_of_basic():
    assert str(
        SuperExpressive()
            .any_of
                .string('hello')
                .digit
                .word
                .char('.')
                .char('#')
            .end()
    ) == r'(?:hello|\d|\w|[\.#])'


def test_any_of_range_fusion():
    assert str(
        SuperExpressive()
            .any_of
                .range('a', 'z')
                .range('A', 'Z')
                .range('0', '9')
                .char('.')
                .char('#')
            .end()
    ) == r'[a-zA-Z0-9\.#]'


def test_any_of_range_fusion_with_other_choices():
    assert str(
        SuperExpressive()
            .any_of
                .range('a', 'z')
                .range('A', 'Z')
                .range('0', '9')
                .char('.')
                .char('#')
                .string('XXX')
            .end()
    ) == r'(?:XXX|[a-zA-Z0-9\.#])'


def test_capture():
    assert str(
        SuperExpressive()
            .capture
                .string('hello ')
                .word
                .char('!')
            .end()
    ) == r'(hello \w!)'


def test_named_capture():
    assert str(
        SuperExpressive()
            .named_capture('this_is_the_name')
                .string('hello ')
                .word
                .char('!')
            .end()
    ) == r'(?P<this_is_the_name>hello \w!)'


def test_named_capture_bad_name():
    with pytest.raises(ValueError):
        (SuperExpressive()
         .named_capture('hello world')
             .string('hello ')
             .word
             .char('!')
         .end())


def test_named_capture_duplicate_name():
    with pytest.raises(ValueError):
        (SuperExpressive()
         .named_capture('hello world')
            .string('hello ')
            .word
            .char('!')
         .end()
         .named_capture('hello world')
             .string('hello ')
             .word
             .char('!')
         .end())


def test_named_backreference():
    assert str(
        SuperExpressive()
            .named_capture('this_is_the_name')
                .string('hello ')
                .word
                .char('!')
            .end()
            .named_backreference('this_is_the_name')
    ) == r'(?P<this_is_the_name>hello \w!)\g<this_is_the_name>'


def test_missing_named_backreference():
    with pytest.raises(ValueError):
        SuperExpressive().named_backreference('not_here')


def test_backreference():
    assert str(
        SuperExpressive()
            .capture
                .string('hello ')
                .word
                .char('!')
            .end()
            .backreference(1)
    ) == r'(hello \w!)\1'


def test_backreference_missing():
    with pytest.raises(ValueError):
        SuperExpressive().backreference(1)


def test_group():
    assert str(
        SuperExpressive()
            .group
                .string('hello ')
                .word
                .char('!')
            .end()
    ) == r'(?:hello \w!)'


def test_end_no_stack():
    with pytest.raises(RuntimeError):
        SuperExpressive().end()


def test_assert_ahead():
    assert str(
        SuperExpressive()
            .assert_ahead
                .range('a', 'f')
            .end()
            .range('a', 'z')
    ) == r'(?=[a-f])[a-z]'


def test_assert_not_ahead():
    assert str(
        SuperExpressive()
            .assert_not_ahead
                .range('a', 'f')
            .end()
            .range('0', '9')
    ) == r'(?![a-f])[0-9]'


@pytest.mark.parametrize('se, expected', [
    (SuperExpressive().optional.word, r'\w?'),
    (SuperExpressive().zero_or_more.word, r'\w*'),
    (SuperExpressive().zero_or_more_lazy.word, r'\w*?'),
    (SuperExpressive().one_or_more.word, r'\w+'),
    (SuperExpressive().one_or_more_lazy.word, r'\w+?'),
    (SuperExpressive().exactly(4).word, r'\w{4}'),
    (SuperExpressive().at_least(4).word, r'\w{4,}'),
    (SuperExpressive().between(4, 7).word, r'\w{4,7}'),
    (SuperExpressive().between_lazy(4, 7).word, r'\w{4,7}?'),
])
def test_quantifier(se: SuperExpressive, expected) -> None:
    assert str(se) == expected


@pytest.mark.parametrize('se, expected', [
    (SuperExpressive().start_of_input, r'^'),
    (SuperExpressive().end_of_input, r'$'),
    (SuperExpressive().any_of_chars('aeiou.-'), r'[aeiou\.\-]'),
    (SuperExpressive().anything_but_chars('aeiou.-'), r'[^aeiou\.\-]'),
    (SuperExpressive().anything_but_range('0', '9'), r'[^0-9]'),
    (SuperExpressive().string('hello'), r'hello'),
    (SuperExpressive().string('h'), r'h'),
    (SuperExpressive().range('a', 'z'), r'[a-z]'),
])
def test_simple_matchers(se: SuperExpressive, expected) -> None:
    assert str(se) == expected


def test_char_more_than_one_char() -> None:
    with pytest.raises(ValueError):
        SuperExpressive().char('hello')


# Python Specific

@pytest.mark.parametrize('se, string', [
    (SuperExpressive().ascii_bell, r'\a'),
    (SuperExpressive().ascii_formfeed, r'\f'),
    (SuperExpressive().ascii_vertical_tab, r'\v'),
    (SuperExpressive().backslash, r'\\'),
    (SuperExpressive().start_of_string, r'\A'),
    (SuperExpressive().end_of_string, r'\Z'),
])
def test_extra_escapes(se: SuperExpressive, string: str) -> None:
    assert str(se) == string


def test_ascii_backspace() -> None:
    with pytest.raises(RuntimeError):
        _ = SuperExpressive().ascii_backspace
    assert str(SuperExpressive().any_of.ascii_backspace.end()) == r'(?:\b)'


def test_hex_char() -> None:
    for n in range(0x00, 0xFF + 1):
        code = hex(n)[2:].rjust(2, '0')
        assert str(SuperExpressive().hex_char(code)) == f'\\x{code}'


@given(integers(0x00, 0xFF))
@example(0x00)
@example(0xFF)
def test_single_unicode_char(n: int) -> None:
    code = hex(n)[2:].rjust(4, '0')
    assert str(SuperExpressive().unicode_char(code)) == f'\\u{code}'


@given(integers(0x00, 0x00110000))
@example(0x00)
@example(0x00110000 - 1)
def test_double_unicode_char(n: int) -> None:
    code = hex(n)[2:].rjust(8, '0')
    assert str(SuperExpressive().unicode_char(code)) == f'\\U{code}'


def _unicode_name(n: int) -> Optional[str]:
    try:
        return unicodedata.name(chr(n))
    except ValueError:
        return None


@given(sampled_from(sorted(NAMED_UNICODE)))
def test_double_unicode_char(character: str) -> None:
    name = NAMED_UNICODE[character]
    assert str(SuperExpressive().unicode_char(name)) == f'\\N{{{name}}}'
