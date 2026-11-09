"""First contact: /hebe help explains value and steps without touching data."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hebe.commands import handle
from hebe.service import Service


class NoDialog:
    def ask_choice(self, *a): raise AssertionError('help must not open a dialog')


class Help(unittest.TestCase):
    def test_help_names_value_steps_and_saves_nothing(self):
        with tempfile.TemporaryDirectory() as home:
            text = handle(NoDialog(), home, 'help')
            for part in ('Longevity Intelligence for Hermes', 'Blood PhenoAge', '/hebe import',
                         'What could I try to lower my Blood PhenoAge?', '/hebe plan start', 'Research'):
                self.assertIn(part, text)
            self.assertEqual(Service(home).results(), [])

    def test_unknown_command_points_to_help(self):
        with tempfile.TemporaryDirectory() as home:
            self.assertIn('/hebe help', handle(NoDialog(), home, 'nonsense'))

    def test_first_result_names_the_next_step(self):
        class Save:
            def ask_choice(self, *a): return 'save'
        with tempfile.TemporaryDirectory() as home:
            self.assertIn('What could I try to lower my Blood PhenoAge?', handle(Save(), home, ''))


if __name__ == '__main__': unittest.main()
