import unittest
import collections
from .bib import *
from .algo import *
from .messages import *
from . import algo

def od(*args):
    return collections.OrderedDict(zip(args[::2], args[1::2]))

def ent(typ, key, fields):
    return Entry(fields, typ, key)

class BibParserTest(unittest.TestCase):
    def __test_parse(self, string, ents):
        # Parse string and get entries
        got = list(Parser().parse(string).finalize().values())
        self.assertEqual(got, ents)

    def test_basic(self):
        self.__test_parse(
            '@misc{x, title="title", author={author}}\n@misc{y, title=123,}',
            [ent('misc', 'x', od('title', 'title',
                                 'author', 'author')),
             ent('misc', 'y', od('title', '123'))])

    def test_balanced(self):
        self.__test_parse(
            '@misc{x, title={a{b}c}, author="x{y}z"}',
            [ent('misc', 'x', od('title', 'a{b}c',
                                 'author', 'x{y}z'))])

    def test_whitespace(self):
        self.__test_parse(
            ' @ misc { x , title = {a} , }',
            [ent('misc', 'x', od('title', 'a'))])

    def test_compress(self):
        self.__test_parse(
            '@misc{x, title={  a\t  b\n  c  }}',
            [ent('misc', 'x', od('title', 'a b c'))])

    def test_funny_keys(self):
        self.__test_parse(
            '@misc{@"#%\'()=, title="a"}',
            [ent('misc', '@"#%\'()=', od('title', 'a'))])
        for string in ['@misc{}', '@misc{,}', '@misc{\n}']:
            self.__test_parse(string, [ent('misc', '', od())])
        self.__test_parse(
            '@misc{,title="a"}',
            [ent('misc', '', od('title', 'a'))])
        self.__test_parse(
            '@misc(k)ey, title="a")\n@misc{k{ey, title="a"}',
            [ent('misc', 'k)ey', od('title', 'a')),
             ent('misc', 'k{ey', od('title', 'a'))])

    def test_string(self):
        self.__test_parse(
            '@string{foo = {a}}\n@misc{x, title = foo # "b" # foo # 2}',
            [ent('misc', 'x', od('title', 'aba2'))])

    def test_comment(self):
        self.__test_parse(
            # Braces intentionally unbalanced, everything on one line
            '@comment{abc@misc{x}',
            [ent('misc', 'x', od())])

class EntryTest(unittest.TestCase):
    def test_to_bib(self):
        entry = Entry([('author', 'An Author'),
                       ('title', 'This is a ' + 'really '*10 + 'long title'),
                       ('month', 'November'), ('year', '2013')],
                      typ='misc', key='key')
        self.assertEqual(
            entry.to_bib(),
            '''\
@misc{key,
  author       = {An Author},
  title        = {This is a really really really really really really
    really really really really long title},
  month        = nov,
  year         = 2013,
}''')
        self.assertEqual(
            entry.to_bib(month_to_macro=False, wrap_width=None),
            '''\
@misc{key,
  author       = {An Author},
  title        = {This is a really really really really really really really really really really long title},
  month        = {November},
  year         = 2013,
}''')

    def test_month_num(self):
        def test(string, expect):
            entry = Entry([('month', string)], field_pos={'month': Pos.unknown})
            self.assertEqual(entry.month_num(), expect)
        for i, name in enumerate(['Jan.','Feb.','Mar.','Apr.','May','June',
                                  'July','Aug.','Sept.','Oct.','Nov.','Dec.']):
            test(name, i+1)
        for i, name in enumerate(['January','February','March','April',
                                  'May','June','July','August',
                                  'September','October','November','December']):
            test(name, i+1)
        self.assertRaises(InputError, test, 'Foo', None)
        self.assertRaises(InputError, test, 'Janruary', None)

    def test_date_key(self):
        def test(year, month, expect):
            fields = []
            if year: fields.append(('year', year))
            if month: fields.append(('month', month))
            entry = Entry(fields, field_pos={'year' : Pos.unknown,
                                             'month' : Pos.unknown})
            got = entry.date_key()
            if expect is not None:
                self.assertEqual(got, expect)
        test(None, None, ())
        test('2013', None, (2013,))
        test('2013', 'jan', (2013, 1))
        self.assertRaises(InputError, test, 'x', None, None)
        self.assertRaises(InputError, test, None, 'jan', None)
        self.assertRaises(InputError, test, '2013', 'foo', None)

class NameParserTest(unittest.TestCase):
    def test_first_char(self):
        p = algo.NameParser()
        for check, expect in [('abc', 'a'), ('ABC', 'A'), (' abc', 'a'),
                              ('\\abc', 'a'), ('{a} bc', 'b'),
                              ('{\\`a}bc', 'a'), ('{\\aa}bc', 'å'),
                              ('{\\a}bc', 'a')]:
            self.assertEqual(p._first_char(check), expect)

    def test_and(self):
        p = parse_names
        self.assertEqual(p('A B and C D'),
                         [Name('A', '', 'B', ''), Name('C', '', 'D', '')])
        self.assertEqual(p('A B AND C D'),
                         [Name('A', '', 'B', ''), Name('C', '', 'D', '')])
        self.assertEqual(p('A B and and C D'),
                         [Name('A', '', 'B', ''), Name('', '', '', ''),
                          Name('C', '', 'D', '')])
        self.assertEqual(p('A B and and'),
                         [Name('A', '', 'B', ''), Name('', '', 'and', '')])
        self.assertEqual(p('A B { and } C D'),
                         [Name('A B { and } C', '', 'D', '')])
        self.assertEqual(p('A B {\\ and } C D'),
                         [Name('A B', '{\\ and }', 'C D', '')])

    def __test_names(self, *tests):
        for test in tests:
            if len(test) == 4:
                test = test + ('',)
            names = parse_names(test[0])
            self.assertEqual(names, [Name(*test[1:])],
                             'parsing {!r}'.format(test[0]))

    def test_first_von_last(self):
        # Examples mostly from Nicolas Markey's Tame the BeaST
        self.__test_names(
            ('jean de la fontaine',     '', 'jean de la', 'fontaine'),
            ('Jean de la fontaine',     'Jean', 'de la', 'fontaine'),
            ('Jean De La fontaine',     'Jean De La', '', 'fontaine'),
            ('Jean {de} la fontaine',   'Jean {de}', 'la', 'fontaine'),
            ('jean {de} {la} fontaine', '', 'jean', '{de} {la} fontaine'),
            ('Jean {de} {la} fontaine', 'Jean {de} {la}', '', 'fontaine'),
            ('Jean De La Fontaine',     'Jean De La', '', 'Fontaine'),
            ('jean De la Fontaine',     '', 'jean De la', 'Fontaine'),
            ('Jean de La Fontaine',     'Jean', 'de', 'La Fontaine'),
            ('Jean-Baptiste Poquelin',  'Jean-Baptiste', '', 'Poquelin'),
            ('Jean-Baptiste-Poquelin',  '', '', 'Jean-Baptiste-Poquelin'),
            ('Jean- Baptiste-Poquelin', '', '', 'Jean-Baptiste-Poquelin'),
            ('Jean Baptiste Poquelin',  'Jean Baptiste', '', 'Poquelin'),
            ('Jean Baptiste-Poquelin',  'Jean', '', 'Baptiste-Poquelin'),
            ('Jean Baptiste~Poquelin',  'Jean Baptiste', '', 'Poquelin'),
            ('Jean-baptiste Poquelin',  'Jean', 'baptiste', 'Poquelin'))

    def test_von_last_first(self):
        self.__test_names(
            ('de la fontaine, Jean',    'Jean', 'de la', 'fontaine'),
            ('De La Fontaine, Jean',    'Jean', '', 'De La Fontaine'),
            ('De la Fontaine, Jean',    'Jean', 'De la', 'Fontaine'),
            ('de La Fontaine, Jean',    'Jean', 'de', 'La Fontaine'),
            ('{D}e {L}a Cruz, Maria',   'Maria', '{D}e {L}a', 'Cruz'))

    def test_von_last_jr_first(self):
        self.__test_names(
            ('de la fontaine, Jean, Jr', 'Jean', 'de la', 'fontaine', 'Jr'),
            ('De La Fontaine, Jean, Jr', 'Jean', '', 'De La Fontaine', 'Jr'),
            ('De la Fontaine, Jean, Jr', 'Jean', 'De la', 'Fontaine', 'Jr'),
            ('de La Fontaine, Jean, Jr', 'Jean', 'de', 'La Fontaine', 'Jr'))

class CaseTest(unittest.TestCase):
    def __test(self, *tests):
        for string, want in tests:
            self.assertEqual(title_case(string), want,
                             'title-casing {!r}'.format(string))

    def test_basic(self):
        self.__test(
            ('ABC DEF',       'Abc def'),
            ('abc def',       'abc def'),
            ('ABC {DEF} GHI', 'Abc {DEF} ghi'),
            ('ABC D{E}F GHI', 'Abc d{E}f ghi'))

    def test_colons(self):
        self.__test(
            ('ABC DEF: GHI JKL',  'Abc def: Ghi jkl'),
            ('ABC DEF:  GHI JKL', 'Abc def:  Ghi jkl'),
            ('ABC DEF:GHI JKL',   'Abc def:ghi jkl'))

    def test_special(self):
        self.__test(
            # Brace groups beginning with special characters are
            # lower-cased throughout, even under deeper braces
            (r'x {\AE X {X \AE}}', r'x {\ae x {x \ae}}'),
            # Unknown control sequences also trigger brace group
            # lower-casing, but are themselves left alone
            (r'x {\LaTeX X {X} \AE \LaTeX}', r'x {\LaTeX x {x} \ae \LaTeX}'),
            # Special characters are only interpreted at level 1
            (r'x {{\AE}}', r'x {{\AE}}'),
            # If a brace group does not start with a slash, it doesn't
            # get touched.
            (r'x {AE X \AE}', r'x {AE X \AE}'),
            # Special characters that start at position 0 or after a
            # colon are untouched
            (r'{\AE X {X} \AE} X', r'{\AE X {X} \AE} x'),
            (r'X: {\AE X {X} \AE}', r'X: {\AE X {X} \AE}'),
            (r'X:{\ae x {x} \ae}', r'X:{\ae x {x} \ae}'))

class TeXToUnicodeTest(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(tex_to_unicode(r'~\%\&\#\$'), '\u00A0%&#$')
        self.assertEqual(tex_to_unicode(r'x\ss y\i'), 'xßyı')

    def test_accents(self):
        self.assertEqual(tex_to_unicode(r'{\`a}\^{e}'), 'àê')
        self.assertEqual(tex_to_unicode(r'\`i\`\i'), 'ìì')

    def test_ligatures(self):
        self.assertEqual(tex_to_unicode(r'a--b---c-{-}d'), 'a\u2013b\u2014c--d')
