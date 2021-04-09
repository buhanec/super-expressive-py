"""Meta types for regex structures."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from string import ascii_letters, digits, hexdigits
from typing import Optional as Optional_, Sequence, Union

__all__ = ('Element', 'ContainsChild', 'ContainsChildren', 'Quantifier',
           'QuantifierRequiresGroup', 'Root', 'Noop',
           'StartOfInput', 'EndOfInput', 'AnyChar', 'WhitespaceChar',
           'NonWhitespaceChar', 'Digit', 'NonDigit', 'Word', 'NonWord',
           'WordBoundary', 'NonWordBoundary', 'Newline', 'CarriageReturn',
           'Tab', 'NullByte', 'AnyOfChars', 'AnythingButString',
           'AnythingButChars', 'AnythingButRange', 'Char', 'Range', 'String',
           'NamedBackReference', 'Backreference', 'Capture', 'Subexpression',
           'NamedCapture', 'Group', 'AnyOf', 'AssertAhead', 'AssertNotAhead',
           'Exactly', 'AtLeast', 'Between', 'BetweenLazy', 'ZeroOrMore',
           'ZeroOrMoreLazy', 'OneOrMore', 'OneOrMoreLazy', 'Opt',
           'AsciiBell', 'AsciiBackspace', 'AsciiFormfeed', 'AsciiVerticalTab',
           'Backslash', 'StartOfString', 'EndOfString', 'Hex', 'Unicode')

import unicodedata

HEX_DIGITS = set(hexdigits)
GROUP_NAME_CHARS = set(ascii_letters + digits + '_')
SPECIAL_CHARS = set('\\.^$|?*+()[]{}-')
ESCAPE_TABLE = {ord(c): f'\\{c}' for c in SPECIAL_CHARS}


class Element:
    pass


@dataclass(frozen=True)
class ContainsChild(Element):
    """Lazy way of handling deferred types with a child."""

    child: Optional_[Element] = None

    def replace_child(self, old: Element, new: Element):
        kwargs = {f.name: getattr(self, f.name) for f in fields(self)}
        child: Element = kwargs.pop('child')
        if child is not old:
            raise ValueError(f'Could not find {old!r} as child of {self!r}')
        kwargs['child'] = new
        # noinspection PyArgumentList
        return type(self)(**kwargs)

    def add_child(self, child: Element):
        if self.child is not None:
            raise RuntimeError(f'Setting a non-None child on {self!r}')
        kwargs = {f.name: getattr(self, f.name) for f in fields(self)}
        kwargs['child'] = child
        # noinspection PyArgumentList
        return type(self)(**kwargs)


@dataclass(frozen=True)
class ContainsChildren(Element):
    """Lazy way of handling deferred types with children."""

    children: Sequence[Element] = tuple()

    def replace_child(self, old: Element, new: Element):
        kwargs = {f.name: getattr(self, f.name) for f in fields(self)}
        children: Sequence[Element] = kwargs.pop('children')
        kwargs['children'] = tuple(new if c is old else c for c in children)
        if not any(c is new for c in kwargs['children']):
            raise ValueError(f'Could not find {new!r} in children of {self!r}')
        # noinspection PyArgumentList
        return type(self)(**kwargs)

    def add_child(self, child: Element):
        kwargs = {f.name: getattr(self, f.name) for f in fields(self)}
        children: Sequence[Element] = kwargs.pop('children')
        kwargs['children'] = tuple(children) + (child,)
        # noinspection PyArgumentList
        return type(self)(**kwargs)


class Quantifier(ContainsChild, ABC):

    @property
    @abstractmethod
    def symbol(self) -> str:
        return NotImplemented

    def __str__(self) -> str:
        inner = str(self.child)
        if isinstance(self.child, QuantifierRequiresGroup):
            inner = f'(?:{inner})'
        return f'{inner}{self.symbol}'


class QuantifierRequiresGroup(Element):
    pass


# Type definitions

@dataclass(frozen=True)
class Root(ContainsChildren, QuantifierRequiresGroup, Element):
    """Root element."""

    def __str__(self) -> str:
        return ''.join(map(str, self.children))


@dataclass(frozen=True)
class Noop(Element):
    """Noop element."""

    def __str__(self) -> str:
        return ''


@dataclass(frozen=True)
class StartOfInput(Element):
    """Start of input element."""

    def __str__(self) -> str:
        return '^'


@dataclass(frozen=True)
class EndOfInput(Element):
    """End of input element."""

    def __str__(self) -> str:
        return '$'


@dataclass(frozen=True)
class AnyChar(Element):
    """Any char element."""

    def __str__(self) -> str:
        return '.'


@dataclass(frozen=True)
class WhitespaceChar(Element):
    """Whitespace char element."""

    def __str__(self) -> str:
        return r'\s'


@dataclass(frozen=True)
class NonWhitespaceChar(Element):
    """Non whitespace char element."""

    def __str__(self) -> str:
        return r'\S'


@dataclass(frozen=True)
class Digit(Element):
    """Digit element."""

    def __str__(self) -> str:
        return r'\d'


@dataclass(frozen=True)
class NonDigit(Element):
    """Non digit element."""

    def __str__(self) -> str:
        return r'\D'


@dataclass(frozen=True)
class Word(Element):
    """Word element."""

    def __str__(self) -> str:
        return r'\w'


@dataclass(frozen=True)
class NonWord(Element):
    """Non word element."""

    def __str__(self) -> str:
        return r'\W'


@dataclass(frozen=True)
class WordBoundary(Element):
    """Word boundary element."""

    def __str__(self) -> str:
        return r'\b'


@dataclass(frozen=True)
class NonWordBoundary(Element):
    """Non word boundary element."""

    def __str__(self) -> str:
        return r'\B'


@dataclass(frozen=True)
class Newline(Element):
    """Newline element."""

    def __str__(self) -> str:
        return r'\n'


@dataclass(frozen=True)
class CarriageReturn(Element):
    """Carriage return element."""

    def __str__(self) -> str:
        return r'\r'


@dataclass(frozen=True)
class Tab(Element):
    """Tab element."""

    def __str__(self) -> str:
        return r'\t'


@dataclass(frozen=True)
class NullByte(Element):
    """Null byte element."""

    def __str__(self) -> str:
        return r'\x00'


@dataclass(frozen=True)
class AnyOfChars(Element):
    """Any of chars element."""
    chars: str

    @property
    def chars_escaped(self) -> str:
        return self.chars.translate(ESCAPE_TABLE)

    def __post_init__(self) -> None:
        if not self.chars:
            raise ValueError('chars must have at least one character')

    def __str__(self) -> str:
        return f'[{self.chars_escaped}]'


@dataclass(frozen=True)
class AnythingButString(Element):
    """Anything but string element."""
    string: str

    def __post_init__(self) -> None:
        if not self.string:
            raise ValueError('string must have at least one character')

    def __str__(self) -> str:
        negated = ''.join(f'[^{c.translate(ESCAPE_TABLE)}]' for c in self.string)
        return f'(?:{negated})'


@dataclass(frozen=True)
class AnythingButChars(AnyOfChars):
    """Anything but chars element."""

    def __str__(self) -> str:
        return f'[^{self.chars_escaped}]'


@dataclass(frozen=True)
class AnythingButRange(Element):
    """Anything but range element."""

    low: Union[int, str]
    high: Union[int, str]

    @property
    def _low(self) -> str:
        if isinstance(self.low, int):
            return chr(self.low)
        return self.low

    @property
    def low_escaped(self) -> str:
        return self._low.translate(ESCAPE_TABLE)

    @property
    def _high(self) -> str:
        if isinstance(self.high, int):
            return chr(self.high)
        return self.high

    @property
    def high_escaped(self) -> str:
        return self._high.translate(ESCAPE_TABLE)

    def __post_init__(self) -> None:
        try:
            _ = self._low
        except ValueError as e:
            raise ValueError(f'Invalid low {self.low!r}') from e
        try:
            _ = self._high
        except ValueError as e:
            raise ValueError(f'Invalid low {self.high!r}') from e
        if len(self._low) != 1:
            raise ValueError(f'low must be a single character or '
                             f'number (got {self.low!r}')
        if len(self._high) != 1:
            raise ValueError(f'low must be a single character or '
                             f'number (got {self.high!r}')
        if ord(self._low) >= ord(self._high):
            raise ValueError(f'low must have a smaller character value '
                             f'than high (low = {self.low!r}, '
                             f'high = {self.high!r})')

    def __str__(self) -> str:
        return f'[^{self.low_escaped}-{self.high_escaped}]'


@dataclass(frozen=True)
class Char(Element):
    """Char element."""

    char: Union[int, str]

    @property
    def _char(self) -> str:
        if isinstance(self.char, int):
            return chr(self.char)
        return self.char

    @property
    def char_escaped(self) -> str:
        return self._char.translate(ESCAPE_TABLE)

    def __post_init__(self) -> None:
        if isinstance(self.char, str):
            if len(self.char) != 1:
                raise ValueError(f'char can only be a single '
                                 f'character (got {self.char!r}')
        else:
            try:
                chr(self.char)
            except ValueError as e:
                raise ValueError(f'Invalid char {self.char!r}') from e

    def __str__(self) -> str:
        return self.char_escaped


@dataclass(frozen=True)
class Range(AnythingButRange):
    """Range element."""

    def __str__(self) -> str:
        return f'[{self.low_escaped}-{self.high_escaped}]'


@dataclass(frozen=True)
class String(QuantifierRequiresGroup, Element):
    """String element."""
    string: str

    def __post_init__(self) -> None:
        if not self.string:
            raise ValueError('string must have at least one character')

    def __str__(self) -> str:
        return self.string.translate(ESCAPE_TABLE)


@dataclass(frozen=True)
class NamedBackReference(Element):
    """Named backreference element."""
    name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError('Name must be at least one character')
        if set(self.name) - GROUP_NAME_CHARS or not self.name[0].isalpha():
            raise ValueError(f'Name {self.name} is not valid '
                             f'(only letters, numbers, and underscore)')

    def __str__(self) -> str:
        return f'\\g<{self.name}>'


@dataclass(frozen=True)
class Backreference(Element):
    """Backreference element"""
    index: int

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError('Index must be non-negative')

    def __str__(self) -> str:
        return f'\\{self.index}'


@dataclass(frozen=True)
class Capture(ContainsChildren, Element):
    """Capture element."""

    def __str__(self) -> str:
        inner = ''.join(map(str, self.children))
        return f'({inner})'


@dataclass(frozen=True)
class Subexpression(ContainsChildren, QuantifierRequiresGroup, Element):
    """Subexpression element."""

    def __str__(self) -> str:
        return ''.join(map(str, self.children))


@dataclass(frozen=True)
class _NamedCapture:
    name: str
    children = tuple()


@dataclass(frozen=True)
class NamedCapture(ContainsChildren, _NamedCapture, Element):
    """Named capture element."""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError('Name must be at least one character')
        if set(self.name) - GROUP_NAME_CHARS or not self.name[0].isalpha():
            raise ValueError(f'Name {self.name} is not valid '
                             f'(only letters, numbers, and underscore)')

    def __str__(self) -> str:
        inner = ''.join(map(str, self.children))
        return f'(?P<{self.name}>{inner})'


@dataclass(frozen=True)
class Group(ContainsChildren, Element):
    """Group element."""

    def __str__(self) -> str:
        inner = ''.join(map(str, self.children))
        return f'(?:{inner})'


@dataclass(frozen=True)
class AnyOf(ContainsChildren, Element):
    """Any of element."""

    def __str__(self) -> str:
        fusable = []
        for child in self.children:
            if type(child) is Char:
                child: Char
                fusable.append(child.char_escaped)
            elif type(child) is AnyOfChars:
                child: AnyOfChars
                fusable.append(child.chars_escaped)
            elif type(child) is Range:
                child: Range
                fusable.append(f'{child.low_escaped}-{child.high_escaped}')

        inner_bits = [str(child) for child in self.children
                      if not type(child) in {Char, AnyOfChars, Range}]

        if fusable:
            if not inner_bits:
                return f'[{"".join(fusable)}]'
            inner_bits.append(f'[{"".join(fusable)}]')

        inner = '|'.join(inner_bits)

        return f'(?:{inner})'


@dataclass(frozen=True)
class AssertAhead(ContainsChildren, Element):
    """Assert ahead element."""

    def __str__(self) -> str:
        inner = ''.join(map(str, self.children))
        return f'(?={inner})'


@dataclass(frozen=True)
class AssertNotAhead(ContainsChildren, Element):
    """Assert not ahead element."""

    def __str__(self) -> str:
        inner = ''.join(map(str, self.children))
        return f'(?!{inner})'


# Quantifiers

@dataclass(frozen=True)
class _Exactly:
    times: int
    child: Optional_[Element] = None


@dataclass(frozen=True)
class Exactly(Quantifier, _Exactly):
    """Exactly element."""

    @property
    def symbol(self) -> str:
        return f'{{{self.times}}}'

    def __post_init__(self) -> None:
        if self.times <= 0:
            raise ValueError(f'times must be a positive integer '
                             f'(got {self.times})')


@dataclass(frozen=True)
class AtLeast(Exactly):
    """At least element."""

    @property
    def symbol(self) -> str:
        return f'{{{self.times},}}'


@dataclass(frozen=True)
class _Between:
    """Between element."""
    low: int
    high: int
    child: Optional_[Element] = None


@dataclass(frozen=True)
class Between(Quantifier, _Between):
    """Between element."""

    @property
    def symbol(self) -> str:
        return f'{{{self.low},{self.high}}}'

    def __post_init__(self) -> None:
        if self.low < 0:
            raise ValueError(f'low must be a non-negative integer (got {self.low})')
        if self.low >= self.high:
            raise ValueError(f'low must be less than high '
                             f'(low = {self.low}, high = {self.high})')


@dataclass(frozen=True)
class BetweenLazy(Between):
    """Between lazy element."""

    @property
    def symbol(self) -> str:
        return super().symbol + '?'


@dataclass(frozen=True)
class ZeroOrMore(Quantifier):
    """Zero or more element."""

    @property
    def symbol(self) -> str:
        return r'*'


@dataclass(frozen=True)
class ZeroOrMoreLazy(ZeroOrMore):
    """Zero or more lazy element."""

    @property
    def symbol(self) -> str:
        return super().symbol + '?'


@dataclass(frozen=True)
class OneOrMore(Quantifier):
    """One or more element."""

    @property
    def symbol(self) -> str:
        return '+'


@dataclass(frozen=True)
class OneOrMoreLazy(OneOrMore):
    """One or more lazy element."""

    @property
    def symbol(self) -> str:
        return super().symbol + '?'


@dataclass(frozen=True)
class Opt(Quantifier):
    """Optional element."""

    @property
    def symbol(self) -> str:
        return '?'


# Python specific

@dataclass(frozen=True)
class AsciiBell(Element):
    """ASCII bell element."""

    def __str__(self) -> str:
        return r'\a'


@dataclass(frozen=True)
class AsciiBackspace(Element):
    """ASCII backspace element."""

    def __str__(self) -> str:
        return r'\b'


@dataclass(frozen=True)
class AsciiFormfeed(Element):
    """ASCII fromfeed element."""

    def __str__(self) -> str:
        return r'\f'


@dataclass(frozen=True)
class AsciiVerticalTab(Element):
    """ASCII vertical tab element."""

    def __str__(self) -> str:
        return r'\v'


@dataclass(frozen=True)
class Backslash(Element):
    """ASCII backslash element."""

    def __str__(self) -> str:
        return r'\\'


@dataclass(frozen=True)
class StartOfString(Element):
    """Start of string element."""

    def __str__(self) -> str:
        return r'\A'


@dataclass(frozen=True)
class EndOfString(Element):
    """End of string element."""

    def __str__(self) -> str:
        return r'\Z'


@dataclass(frozen=True)
class Hex(Element):
    code: str

    def __post_init__(self) -> None:
        if len(self.code) != 2 or set(self.code) - HEX_DIGITS:
            raise ValueError(f'Invalid hex char {self.code!r}')

    def __str__(self) -> str:
        return f'\\x{self.code}'


@dataclass(frozen=True)
class Unicode(Element):
    code: str

    def __post_init__(self) -> None:
        str(self)

    def __str__(self) -> str:
        # Check if named unicode character
        try:
            unicodedata.lookup(self.code)
        except KeyError:
            pass
        else:
            return f'\\N{{{self.code}}}'

        # Check if single byte self.code
        if len(self.code) == 4 and not set(self.code) - HEX_DIGITS:
            return f'\\u{self.code}'

        # Check if double byte self.code
        if 4 < len(self.code) <= 8 and not set(self.code) - HEX_DIGITS:
            try:
                chr(int(self.code, 16))
            except ValueError:
                pass
            else:
                return f'\\U{self.code}'

        raise ValueError(f'Invalid unicode char {self.code!r}')
