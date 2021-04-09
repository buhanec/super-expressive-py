"""Super Expressive library for building regular expressions."""

from dataclasses import dataclass, fields
import logging
import re
from typing import AbstractSet, Any, Optional, Sequence, Tuple, Union
from typing.re import Match, Pattern

from superexpressive.types import *

logger = logging.getLogger(__name__)

STACKABLE = (ContainsChild, ContainsChildren)
Stackable = Union[ContainsChild, ContainsChildren]
CharT = Union[int, str]


@dataclass(frozen=True)
class SuperExpressive:
    """Super Expressive root."""

    check_simple_start_and_end: bool = False
    stack: Sequence[Stackable] = (Root(),)
    named_groups: AbstractSet[str] = frozenset()
    total_capture_groups: int = 0

    f_ascii: bool = False
    f_ignorecase: bool = False
    f_locale: bool = False
    f_unicode: bool = True
    f_multiline: bool = False
    f_dotall: bool = False
    f_global: bool = False

    def _replace(self,
                 start_defined: Optional[bool] = None,
                 end_defined: Optional[bool] = None,
                 stack: Optional[Sequence[Stackable]] = None,
                 named_groups: Optional[AbstractSet[str]] = None,
                 total_capture_groups: Optional[int] = None,
                 f_ascii: Optional[bool] = None,
                 f_ignorecase: Optional[bool] = None,
                 f_locale: Optional[bool] = None,
                 f_unicode: Optional[bool] = None,
                 f_multiline: Optional[bool] = None,
                 f_dotall: Optional[bool] = None,
                 f_global: Optional[bool] = None) -> 'SuperExpressive':
        kwargs = {f.name: getattr(self, f.name) for f in fields(self)}
        if start_defined is not None:
            kwargs['start_defined'] = start_defined
        if end_defined is not None:
            kwargs['end_defined'] = end_defined
        if stack is not None:
            kwargs['stack'] = stack
        if named_groups is not None:
            kwargs['named_groups'] = named_groups
        if total_capture_groups is not None:
            kwargs['total_capture_groups'] = total_capture_groups
        if f_ascii is not None:
            if f_ascii:
                kwargs['f_locale'] = False
                kwargs['f_unicode'] = False
            kwargs['f_ascii'] = f_ascii
        if f_ignorecase is not None:
            kwargs['f_ignorecase'] = f_ignorecase
        if f_locale is not None:
            if f_locale:
                kwargs['f_ascii'] = False
                kwargs['f_unicode'] = False
            kwargs['f_locale'] = f_locale
        if f_unicode is not None:
            if f_unicode:
                kwargs['f_ascii'] = False
                kwargs['f_locale'] = False
            kwargs['f_unicode'] = f_unicode
        if f_multiline is not None:
            kwargs['f_multiline'] = f_multiline
        if f_dotall is not None:
            kwargs['f_dotall'] = f_dotall
        if f_global is not None:
            kwargs['f_global'] = f_global
        # noinspection PyArgumentList
        return type(self)(**kwargs)

    @property
    def _start_defined(self) -> bool:
        for s in self.stack:
            if (isinstance(s, ContainsChild)
                    and isinstance(s.child, StartOfInput)
                    or isinstance(s, ContainsChildren)
                    and any(isinstance(c, StartOfInput) for c in s.children)):
                return True
        return False

    @property
    def _end_defined(self) -> bool:
        for s in self.stack:
            if (isinstance(s, ContainsChild)
                    and isinstance(s.child, StartOfInput)
                    or isinstance(s, ContainsChildren)
                    and any(isinstance(c, StartOfInput) for c in s.children)):
                return True
        return False

    def _push(self, element: Element) -> 'SuperExpressive':
        # print('pushing', repr(element))
        # print('stack', self.stack)
        stack = self.stack
        current = self.stack[-1]

        # Set child and propage new elements
        new = current.add_child(element)
        new_stack = []

        previous = current
        replaced = new
        for stackable in reversed(stack[:-1]):
            # print()
            # print('stackable', repr(stackable), '::', repr(current), '->', repr(new))
            previous, replaced = stackable, stackable.replace_child(previous, replaced)
            new_stack.append(replaced)
        stack = tuple(reversed(new_stack)) + (new,)

        # If new element is stackable, add to stack
        if isinstance(element, STACKABLE):
            # print()
            # print('result', stack + (element,))
            # print()
            # print('-' * 80)
            # print()
            return self._replace(stack=stack + (element,))

        # Otherwise try to pop as many ContainsChild that are now set
        while stack and isinstance(stack[-1], ContainsChild):
            # print()
            # print('stack', repr(stack))
            # print('popping', repr(stack[-1]))
            stack = stack[:-1]
        # print()
        # print('result', stack)
        # print()
        # print('-' * 80)
        # print()
        return self._replace(stack=stack)

    def _merge_in_element(self,
                          element: Element,
                          namespace: str,
                          ignore_start_and_end: bool) -> Tuple['SuperExpressive', Element]:
        merged = self
        additional_capture_groups = 0

        if isinstance(element, Backreference):
            index = element.index + self.total_capture_groups
            element = Backreference(index=index)

        if isinstance(element, Capture):
            additional_capture_groups += 1

        if isinstance(element, NamedCapture):
            if namespace:
                element = NamedCapture(children=element.children,
                                       name=f'{namespace}{element.name}')
            if element.name in self.named_groups:
                raise ValueError(f'Cannot use {element.name!r} again '
                                 f'for a capture group')
            named_groups = set(self.named_groups)
            named_groups.add(element.name)
            named_groups = frozenset(named_groups)
            merged = merged._replace(named_groups=named_groups)

        if isinstance(element, NamedBackReference):
            if namespace:
                element = NamedBackReference(name=element.name)

        if isinstance(element, ContainsChild):
            merged, new_child = merged._merge_in_element(
                element.child,
                namespace=namespace,
                ignore_start_and_end=ignore_start_and_end
            )
            element = element.replace_child(element.child, new_child)

        if isinstance(element, ContainsChildren):
            for child in element.children:
                merged, new_child = merged._merge_in_element(
                    child,
                    namespace=namespace,
                    ignore_start_and_end=ignore_start_and_end
                )
                element = element.replace_child(child, new_child)

        if isinstance(element, StartOfInput):
            if ignore_start_and_end:
                element = Noop()
            elif merged._start_defined and merged.check_simple_start_and_end:
                raise ValueError('The parent regex already has a '
                                 'defined start of input. You can '
                                 'ignore a subexpression\'s '
                                 'start_of_input/end_of_input markers '
                                 'with the ignore_start_and_end option')
            elif merged._end_defined and merged.check_simple_start_and_end:
                raise ValueError('The parent regex already has a '
                                 'defined end of input. You can '
                                 'ignore a subexpression\'s '
                                 'start_of_input/end_of_input markers '
                                 'with the ignore_start_and_end option')

        if isinstance(element, EndOfInput):
            if ignore_start_and_end:
                element = Noop()
            elif merged._end_defined and merged.check_simple_start_and_end:
                raise ValueError('The parent regex already has a '
                                 'defined end of input. You can '
                                 'ignore a subexpression\'s '
                                 'start_of_input/end_of_input markers '
                                 'with the ignore_start_and_end option')

        return merged, element

    # Flags ############################################################

    @property
    def allow_multiple_matches(self):
        return self._replace(f_global=True)

    @property
    def line_by_line(self):
        return self._replace(f_multiline=True)

    @property
    def case_insensitive(self):
        return self._replace(f_ignorecase=True)

    @property
    def unicode(self):
        return self._replace(f_unicode=True)

    @property
    def ascii(self):
        return self._replace(f_ascii=True)

    @property
    def locale(self):
        return self._replace(f_locale=True)

    @property
    def single_line(self):
        return self._replace(f_dotall=True)

    # Elements #########################################################

    @property
    def any_char(self) -> 'SuperExpressive':
        return self._push(AnyChar())

    @property
    def whitespace_char(self) -> 'SuperExpressive':
        return self._push(WhitespaceChar())

    @property
    def non_whitespace_char(self) -> 'SuperExpressive':
        return self._push(NonWhitespaceChar())

    @property
    def digit(self) -> 'SuperExpressive':
        return self._push(Digit())

    @property
    def non_digit(self) -> 'SuperExpressive':
        return self._push(NonDigit())

    @property
    def word(self) -> 'SuperExpressive':
        return self._push(Word())

    @property
    def non_word(self) -> 'SuperExpressive':
        return self._push(NonWord())

    @property
    def word_boundary(self) -> 'SuperExpressive':
        return self._push(WordBoundary())

    @property
    def non_word_boundary(self) -> 'SuperExpressive':
        return self._push(NonWordBoundary())

    @property
    def newline(self) -> 'SuperExpressive':
        return self._push(Newline())

    @property
    def carriage_return(self) -> 'SuperExpressive':
        return self._push(CarriageReturn())

    @property
    def tab(self) -> 'SuperExpressive':
        return self._push(Tab())

    @property
    def null_byte(self) -> 'SuperExpressive':
        return self._push(NullByte())

    def named_backreference(self, name: str) -> 'SuperExpressive':
        if name not in self.named_groups:
            raise ValueError(f'No capture group called {name} exists '
                             f'(create one with .named_capture())')
        return self._push(NamedBackReference(name=name))

    def backreference(self, index: int) -> 'SuperExpressive':
        if not 0 <= index <= self.total_capture_groups:
            raise ValueError(f'Invalid index {index}. There are '
                             f'{self.total_capture_groups} capture '
                             f'groups on this SuperExpression')
        return self._push(Backreference(index=index))

    @property
    def any_of(self) -> 'SuperExpressive':
        return self._push(AnyOf())

    @property
    def group(self) -> 'SuperExpressive':
        return self._push(Group())

    @property
    def assert_ahead(self) -> 'SuperExpressive':
        return self._push(AssertAhead())

    @property
    def assert_not_ahead(self) -> 'SuperExpressive':
        return self._push(AssertNotAhead())

    @property
    def capture(self) -> 'SuperExpressive':
        return (self
                ._push(Capture())
                ._replace(total_capture_groups=self.total_capture_groups + 1))

    def named_capture(self, name: str) -> 'SuperExpressive':
        if name in self.named_groups:
            raise ValueError(f'Cannot use {name!r} again for a capture group')
        named_groups = set(self.named_groups)
        named_groups.add(name)
        return (self
                ._push(NamedCapture(name=name))
                ._replace(named_groups=frozenset(named_groups)))

    def _quantify(self, quantifier: Quantifier) -> 'SuperExpressive':
        if isinstance(self.stack[-1], Quantifier):
            raise RuntimeError(f'Cannot quantify regular expression '
                               f'with {quantifier} because it\'s '
                               f'already being quantifier with '
                               f'{self.stack[-1]}')
        return self._push(quantifier)

    @property
    def optional(self) -> 'SuperExpressive':
        return self._quantify(Opt())

    @property
    def zero_or_more(self) -> 'SuperExpressive':
        return self._quantify(ZeroOrMore())

    @property
    def zero_or_more_lazy(self) -> 'SuperExpressive':
        return self._quantify(ZeroOrMoreLazy())

    @property
    def one_or_more(self) -> 'SuperExpressive':
        return self._quantify(OneOrMore())

    @property
    def one_or_more_lazy(self) -> 'SuperExpressive':
        return self._quantify(OneOrMoreLazy())

    def exactly(self, times: int) -> 'SuperExpressive':
        return self._quantify(Exactly(times=times))

    def at_least(self, times: int):
        return self._quantify(AtLeast(times=times))

    def between(self, low: int, high: int) -> 'SuperExpressive':
        return self._quantify(Between(low=low, high=high))

    def between_lazy(self, low: int, high: int) -> 'SuperExpressive':
        return self._quantify(BetweenLazy(low=low, high=high))

    @property
    def start_of_input(self) -> 'SuperExpressive':
        if self._start_defined and self.check_simple_start_and_end:
            raise RuntimeError('This regex already has a defined start '
                               'of input')
        if self._end_defined and self.check_simple_start_and_end:
            raise RuntimeError('Cannot define the start of input after '
                               'the end of input')
        return self._push(StartOfInput())

    @property
    def end_of_input(self) -> 'SuperExpressive':
        if self._end_defined and self.check_simple_start_and_end:
            raise RuntimeError('This regex already has a defined end '
                               'of input')
        return self._push(EndOfInput())

    def any_of_chars(self, chars: str) -> 'SuperExpressive':
        return self._push(AnyOfChars(chars))

    def end(self) -> 'SuperExpressive':
        if len(self.stack) <= 1:
            raise RuntimeError('Cannot call end while building the '
                               'root expression')
        if not isinstance(self.stack[-1], ContainsChildren):
            raise RuntimeError(f'Cannot call end while unset '
                               f'expression {self.stack[-1]}')

        # Pop element and try to pop as many ContainsChild that are now set
        stack = self.stack[:-1]
        while stack and isinstance(stack[-1], ContainsChild):
            stack = stack[:-1]
        return self._replace(stack=stack)

    def anything_but_string(self, string: str) -> 'SuperExpressive':
        return self._push(AnythingButString(string=string))

    def anything_but_chars(self, chars: str) -> 'SuperExpressive':
        return self._push(AnythingButChars(chars=chars))

    def anything_but_range(self, low: CharT, high: CharT) -> 'SuperExpressive':
        return self._push(AnythingButRange(low=low, high=high))

    def string(self, string: str) -> 'SuperExpressive':
        return self._push(String(string=string))

    def char(self, char: CharT) -> 'SuperExpressive':
        return self._push(Char(char=char))

    def range(self, low: CharT, high: CharT) -> 'SuperExpressive':
        return self._push(Range(low=low, high=high))

    def subexpression(self,
                      expression: 'SuperExpressive',
                      namespace: str = '',
                      ignore_flags: bool = True,
                      ignore_start_and_end: bool = True) -> 'SuperExpressive':
        if len(expression.stack) != 1:
            raise ValueError(f'Cannot call subexpression with a not '
                             f'yet fully specified regex object. (Try '
                             f'adding a .end call to match the '
                             f'{expression.stack[-1]} on the '
                             f'subexpression)')

        element: Root
        merged, element = self._merge_in_element(
            expression.stack[0],
            namespace=namespace,
            ignore_start_and_end=ignore_start_and_end
        )

        if not ignore_flags:
            if (self.f_unicode != expression.f_unicode
                    or self.f_ascii != expression.f_ascii
                    or self.f_locale != expression.f_locale):
                raise ValueError(f'Incompatible flags from '
                                 f'subexpression ({expression.flags}) '
                                 f'and root expression ({merged.flags}). '
                                 f'You can ignore the subexpression '
                                 f'flags with the ignore_flags option')
            if expression.f_ignorecase:
                merged = self._replace(f_ignorecase=True)
            if expression.f_multiline:
                merged = self._replace(f_multiline=True)
            if expression.f_dotall:
                merged = self._replace(f_dotall=True)
            if expression.f_global:
                merged = self._replace(f_global=True)

        return merged._push(Subexpression(children=element.children)).end()

    # Python Specific ##################################################

    @property
    def ascii_bell(self) -> 'SuperExpressive':
        return self._push(AsciiBell())

    @property
    def ascii_backspace(self) -> 'SuperExpressive':
        if not isinstance(self.stack[-1], AnyOf):
            raise RuntimeError(f'Can only use ASCII backsppace within '
                               f'an any_of group')
        return self._push(AsciiBackspace())

    @property
    def ascii_formfeed(self) -> 'SuperExpressive':
        return self._push(AsciiFormfeed())

    @property
    def ascii_vertical_tab(self) -> 'SuperExpressive':
        return self._push(AsciiVerticalTab())

    @property
    def backslash(self) -> 'SuperExpressive':
        return self._push(Backslash())

    @property
    def start_of_string(self) -> 'SuperExpressive':
        return self._push(StartOfString())

    @property
    def end_of_string(self) -> 'SuperExpressive':
        return self._push(EndOfString())

    def hex_char(self, code: str) -> 'SuperExpressive':
        return self._push(Hex(code=code))

    def unicode_char(self, code: str) -> 'SuperExpressive':
        return self._push(Unicode(code=code))

    # Evaluation / casting #############################################

    @property
    def _flags(self) -> int:
        return ((re.ASCII if self.f_ascii else 0)
                | (re.IGNORECASE if self.f_ignorecase else 0)
                | (re.LOCALE if self.f_locale else 0)
                | (re.UNICODE if self.f_unicode else 0)
                | (re.MULTILINE if self.f_multiline else 0)
                | (re.DOTALL if self.f_dotall else 0))

    def compile(self) -> Pattern:
        return re.compile(str(self), flags=self._flags)

    def match(self, string: str) -> Optional[Match]:
        if self.f_global:
            return re.findall(str(self), string, flags=self._flags)
        return re.match(str(self), string, flags=self._flags)

    def __getattr__(self, item: str) -> Any:
        snake_cased = ''.join(c if c.islower() else f'_{c.lower()}'
                              for c in item)
        print('trying', snake_cased)
        return super().__getattribute__(snake_cased)

    def __str__(self) -> str:
        return str(self.stack[0])
