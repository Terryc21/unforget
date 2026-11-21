"""Surface 5: the gh command scan_surfaces hands the LLM must match ANY deferral label.

`gh issue list --label a,b` requires ALL labels on one issue, so the old command
found almost nothing. The fix uses `--search 'label:a,b'` (ANY). These tests pin
the command's shape offline; the live check runs only with GH_LIVE=1.
"""
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills' / 'unforget' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import scan_surfaces  # noqa: E402


def plant_repo(root: Path, url: str) -> None:
    (root / '.git').mkdir()
    (root / '.git' / 'config').write_text(f'[remote "origin"]\n\turl = {url}\n')


class GitHubSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_github_remote_returns_the_any_label_command(self):
        plant_repo(self.root, 'https://github.com/example/app.git')
        result = scan_surfaces.scan_github_issues(self.root)
        self.assertEqual(result['state'], 'github-detected-defer-to-gh-cli')
        argv = shlex.split(result['command'])
        self.assertEqual(argv[:3], ['gh', 'issue', 'list'])
        self.assertNotIn('--label', argv, '--label a,b means ALL labels; use --search')
        query = argv[argv.index('--search') + 1]
        self.assertEqual(query, 'label:' + ','.join(scan_surfaces.GH_DEFERRAL_LABELS))
        self.assertIn(result['command'], result['notes'][0])

    def test_every_deferral_label_is_in_the_query(self):
        for label in ('deferred', 'wontfix-for-now', 'post-release', 'backlog'):
            self.assertIn(label, scan_surfaces.GH_DEFERRAL_COMMAND)

    def test_non_github_remote_offers_no_command(self):
        plant_repo(self.root, 'https://gitlab.com/example/app.git')
        result = scan_surfaces.scan_github_issues(self.root)
        self.assertEqual(result['state'], 'non-github-remote')
        self.assertNotIn('command', result)

    def test_not_a_repo_offers_no_command(self):
        result = scan_surfaces.scan_github_issues(self.root)
        self.assertEqual(result['state'], 'not-a-git-repo')
        self.assertNotIn('command', result)

    def test_only_origin_counts_not_upstream(self):
        (self.root / '.git').mkdir()
        (self.root / '.git' / 'config').write_text(
            '[remote "origin"]\n\turl = https://gitlab.com/me/fork.git\n'
            '[remote "upstream"]\n\turl = https://github.com/them/app.git\n')
        result = scan_surfaces.scan_github_issues(self.root)
        self.assertEqual(result['state'], 'non-github-remote')

    def test_dot_git_file_with_unreadable_gitdir_is_not_a_repo(self):
        (self.root / '.git').write_text('gitdir: ../nowhere/.git/worktrees/x\n')
        result = scan_surfaces.scan_github_issues(self.root)
        self.assertEqual(result['state'], 'not-a-git-repo')
        self.assertIn('gitdir could not be read', result['notes'][0])

    @unittest.skipUnless(shutil.which('git'), 'needs git')
    def test_real_worktree_and_submodule_find_the_github_origin(self):
        def git(cwd, *args):
            subprocess.run(['git', '-C', str(cwd), '-c', 'user.name=t', '-c', 'user.email=t@example.com',
                            '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
                            '-c', 'protocol.file.allow=always', *args], check=True, capture_output=True)
        main, sub = self.root / 'main', self.root / 'sub'
        for repo in (main, sub):
            repo.mkdir()
            git(repo, 'init', '-q')
            (repo / 'f').write_text('x')
            git(repo, 'add', 'f')
            git(repo, 'commit', '-qm', 'init')
        git(main, 'remote', 'add', 'origin', 'git@github.com:example/app.git')
        git(main, 'worktree', 'add', '-q', str(self.root / 'linked'))
        git(main, 'submodule', 'add', '-q', str(sub), 'mod')
        git(main / 'mod', 'remote', 'set-url', 'origin', 'https://github.com/example/lib.git')
        self.assertTrue((self.root / 'linked' / '.git').is_file(), 'a linked worktree has a .git FILE')
        self.assertTrue((main / 'mod' / '.git').is_file(), 'a submodule has a .git FILE')
        for where in (main, self.root / 'linked', main / 'mod'):
            self.assertEqual(scan_surfaces.scan_github_issues(where)['state'],
                             'github-detected-defer-to-gh-cli', where.name)
        self.assertEqual(scan_surfaces.scan_github_issues(sub)['state'], 'non-github-remote')

    @unittest.skipUnless(os.environ.get('GH_LIVE') == '1', 'set GH_LIVE=1 to query GitHub')
    def test_live_search_form_is_any_and_label_form_is_all(self):
        """Two labels with known disjoint issues: search finds the union, --label finds none."""
        def count(*args):
            out = subprocess.run(['gh', 'issue', 'list', '-R', 'cli/cli', '--state', 'all',
                                  '-L', '200', *args, '--json', 'number', '--jq', 'length'],
                                 capture_output=True, text=True, check=True).stdout
            return int(out.strip())
        a, b = count('--search', 'label:gh-gpg-key'), count('--search', 'label:gh-ruleset')
        self.assertGreater(a, 0)
        self.assertGreater(b, 0)
        self.assertEqual(count('--search', 'label:gh-gpg-key,gh-ruleset'), a + b)
        self.assertEqual(count('--label', 'gh-gpg-key,gh-ruleset'), 0)


if __name__ == '__main__':
    unittest.main()
