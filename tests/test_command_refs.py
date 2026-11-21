"""Review #11: commands.md was split into reference/commands/<command>.md.

These checks keep the split honest: every reference to a command file names a
file that exists, every "§ Heading" after one names a heading in that file, no
"commands.md § ..." reference is left pointing at the index, and the index and
SKILL.md's routing table cover every command file.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / 'skills' / 'unforget'
CMD_DIR = SKILL / 'reference' / 'commands'
INDEX = SKILL / 'reference' / 'commands.md'
# Historical documents describe the repo as it was; they are not routing.
HISTORY = {'CHANGELOG.md', 'v0.3-roadmap.md', 'v0.3-feedback.md'}

REF_RE = re.compile(r'commands/([a-z-]+)\.md`?(?:\s*§\s*([^\n]+(?:\n[^\n]+)?))?')
BARE_SECTION_RE = re.compile(r'(?<![/\w-])commands\.md`?\s*§')


def norm(text):
    return re.sub(r'[`*_🛑]', '', re.sub(r'\s+', ' ', text)).strip().lower()


def headings(path):
    out, fenced = [], False
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('```'):
            fenced = not fenced
        elif not fenced and re.match(r'^#{1,4} ', line):
            out.append(norm(line.lstrip('#')))
    return out


def docs():
    for path in sorted(list(ROOT.rglob('*.md')) + list(SKILL.rglob('*.py'))):
        rel = path.relative_to(ROOT)
        if '.git' in rel.parts or '.agents' in rel.parts or rel.name in HISTORY:
            continue
        yield path


class CommandReferenceTests(unittest.TestCase):
    def test_command_files_exist(self):
        names = sorted(p.stem for p in CMD_DIR.glob('*.md'))
        self.assertEqual(names, sorted(['add', 'archive', 'branch', 'edit', 'import', 'list',
                                        'list-preferences', 'scan', 'show', 'verify', 'version']))

    def test_every_reference_names_a_file_and_a_heading_in_it(self):
        heads = {p.stem: headings(p) for p in CMD_DIR.glob('*.md')}
        bad = []
        for path in docs():
            text = path.read_text(encoding='utf-8')
            for m in REF_RE.finditer(text):
                name, section = m[1], m[2]
                where = f'{path.relative_to(ROOT)}:{text[:m.start()].count(chr(10)) + 1}'
                if name not in heads:
                    bad.append(f'{where}: no file commands/{name}.md')
                    continue
                if not section:
                    continue
                want = norm(re.sub(r'(^|\n)\s*#\s*', ' ', section))  # wrapped code comments
                if not any(want.startswith(h[:min(len(h), 16)]) for h in heads[name]):
                    bad.append(f'{where}: commands/{name}.md has no heading for § {section[:40]!r}')
        self.assertEqual(bad, [])

    def test_no_section_reference_left_on_the_index(self):
        bad = []
        for path in docs():
            if path == INDEX:
                continue
            text = path.read_text(encoding='utf-8')
            for m in BARE_SECTION_RE.finditer(text):
                bad.append(f'{path.relative_to(ROOT)}:{text[:m.start()].count(chr(10)) + 1}')
        self.assertEqual(bad, [], 'point "§ Heading" references at reference/commands/<file>.md')

    def test_index_lists_every_command_file(self):
        index = INDEX.read_text(encoding='utf-8')
        for path in CMD_DIR.glob('*.md'):
            self.assertIn(f'commands/{path.name}', index)

    def test_skill_routing_points_at_command_files(self):
        skill = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
        for command, name in (('add', 'add'), ('edit', 'edit'), ('import', 'import'), ('list', 'list'),
                              ('show', 'show'), ('scan', 'scan'), ('archive', 'archive'),
                              ('--version', 'version')):
            row = next(line for line in skill.splitlines() if line.startswith(f'| `/unforget {command}`'))
            self.assertIn(f'reference/commands/{name}.md', row, command)
            self.assertNotIn('`reference/commands.md`', row, command)

    def test_add_no_longer_loads_the_whole_spec(self):
        self.assertLess((CMD_DIR / 'add.md').stat().st_size, 15_000)
        self.assertLess(INDEX.stat().st_size, 10_000)


if __name__ == '__main__':
    unittest.main()
