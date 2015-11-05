"""Unit test for pep257 module decorator handling.

Use tox or py.test to run the test suite.
"""

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import textwrap

from .. import pep257


class TestParser:
    """Check parsing of Python source code."""

    def test_parse_class_single_decorator(self):
        """Class decorator is recorded in class instance."""
        code = textwrap.dedent("""\
            @first_decorator
            class Foo:
                pass
        """)
        module = pep257.parse(StringIO(code), 'dummy.py')
        decorators = module.children[0].decorators

        assert 1 == len(decorators)
        assert 'first_decorator' == decorators[0].name
        assert '' == decorators[0].arguments

    def test_parse_class_decorators(self):
        """Class decorators are accumulated together with their arguments."""
        code = textwrap.dedent("""\
            @first_decorator
            @second.decorator(argument)
            @third.multi.line(
                decorator,
                key=value,
                )
            class Foo:
                pass
        """)

        module = pep257.parse(StringIO(code), 'dummy.py')
        defined_class = module.children[0]
        decorators = defined_class.decorators

        assert 3 == len(decorators)
        assert 'first_decorator' == decorators[0].name
        assert '' == decorators[0].arguments
        assert 'second.decorator' == decorators[1].name
        assert 'argument' == decorators[1].arguments
        assert 'third.multi.line' == decorators[2].name
        assert 'decorator,key=value,' == decorators[2].arguments

    def test_parse_class_nested_decorator(self):
        """Class decorator is recorded even for nested classes."""
        code = textwrap.dedent("""\
            @parent_decorator
            class Foo:
                pass
                @first_decorator
                class NestedClass:
                    pass
        """)
        module = pep257.parse(StringIO(code), 'dummy.py')
        nested_class = module.children[0].children[0]
        decorators = nested_class.decorators

        assert 1 == len(decorators)
        assert 'first_decorator' == decorators[0].name
        assert '' == decorators[0].arguments

    def test_parse_method_single_decorator(self):
        """Method decorators are accumulated."""
        code = textwrap.dedent("""\
            class Foo:
                @first_decorator
                def method(self):
                    pass
        """)

        module = pep257.parse(StringIO(code), 'dummy.py')
        defined_class = module.children[0]
        decorators = defined_class.children[0].decorators

        assert 1 == len(decorators)
        assert 'first_decorator' == decorators[0].name
        assert '' == decorators[0].arguments

    def test_parse_method_decorators(self):
        """Multiple method decorators are accumulated along with their args."""
        code = textwrap.dedent("""\
            class Foo:
                @first_decorator
                @second.decorator(argument)
                @third.multi.line(
                    decorator,
                    key=value,
                    )
                def method(self):
                    pass
        """)

        module = pep257.parse(StringIO(code), 'dummy.py')
        defined_class = module.children[0]
        decorators = defined_class.children[0].decorators

        assert 3 == len(decorators)
        assert 'first_decorator' == decorators[0].name
        assert '' == decorators[0].arguments
        assert 'second.decorator' == decorators[1].name
        assert 'argument' == decorators[1].arguments
        assert 'third.multi.line' == decorators[2].name
        assert 'decorator,key=value,' == decorators[2].arguments

    def test_parse_function_decorator(self):
        """A function decorator is also accumulated."""
        code = textwrap.dedent("""\
            @first_decorator
            def some_method(self):
                pass
        """)

        module = pep257.parse(StringIO(code), 'dummy.py')
        decorators = module.children[0].decorators

        assert 1 == len(decorators)
        assert 'first_decorator' == decorators[0].name
        assert '' == decorators[0].arguments

    def test_parse_method_nested_decorator(self):
        """Method decorators are accumulated for nested methods."""
        code = textwrap.dedent("""\
            class Foo:
                @parent_decorator
                def method(self):
                    @first_decorator
                    def nested_method(arg):
                        pass
        """)

        module = pep257.parse(StringIO(code), 'dummy.py')
        defined_class = module.children[0]
        decorators = defined_class.children[0].children[0].decorators

        assert 1 == len(decorators)
        assert 'first_decorator' == decorators[0].name
        assert '' == decorators[0].arguments


class TestMethod:
    """Unit test for Method class."""

    def makeMethod(self, name='someMethodName'):
        """Return a simple method instance."""
        children = []
        all = ['ClassName']
        source = textwrap.dedent("""\
            class ClassName:
                def %s(self):
        """ % (name))

        module = pep257.Module('module_name', source, 0, 1, [],
                               'Docstring for module', [], None, all)

        cls = pep257.Class('ClassName', source, 0, 1, [],
                           'Docstring for class', children, module, all)

        return pep257.Method(name, source, 0, 1, [],
                             'Docstring for method', children, cls, all)

    def test_is_public_normal(self):
        """Methods are normally public, even if decorated."""
        method = self.makeMethod('methodName')
        method.decorators = [pep257.Decorator('some_decorator', [])]

        assert method.is_public

    def test_is_public_setter(self):
        """Setter methods are considered private."""
        method = self.makeMethod('methodName')
        method.decorators = [
            pep257.Decorator('some_decorator', []),
            pep257.Decorator('methodName.setter', []),
        ]

        assert not method.is_public

    def test_is_public_deleter(self):
        """Deleter methods are also considered private."""
        method = self.makeMethod('methodName')
        method.decorators = [
            pep257.Decorator('methodName.deleter', []),
            pep257.Decorator('another_decorator', []),
        ]

        assert not method.is_public

    def test_is_public_trick(self):
        """Common prefix does not necessarily indicate private."""
        method = self.makeMethod("foo")
        method.decorators = [
            pep257.Decorator('foobar', []),
            pep257.Decorator('foobar.baz', []),
        ]

        assert method.is_public
