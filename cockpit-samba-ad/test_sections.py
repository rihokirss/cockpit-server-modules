import importlib.machinery
import importlib.util
import unittest
from pathlib import Path
from unittest import mock

loader = importlib.machinery.SourceFileLoader('section_helper', str(Path(__file__).with_name('cockpit-samba-ad-helper')))
spec = importlib.util.spec_from_loader(loader.name, loader)
helper = importlib.util.module_from_spec(spec)
loader.exec_module(helper)


class SectionTests(unittest.TestCase):
    def test_overview_identity_does_not_wait_for_counts_or_replication(self):
        with mock.patch.object(helper, 'domain_info', return_value={'dc': 'dc1'}), \
             mock.patch.object(helper, 'service_active', return_value=True), \
             mock.patch.object(helper, 'replication', side_effect=AssertionError('unrelated RPC')), \
             mock.patch.object(helper, 'user_items', side_effect=AssertionError('unrelated query')):
            result = helper.main({'action': 'overview', 'section': 'identity'})
        self.assertEqual(result, {'domain': {'dc': 'dc1'}, 'service': {'active': True}})

    def test_ad_section_never_runs_sysvol(self):
        with mock.patch.object(helper, 'replication', return_value={'healthy': True}), \
             mock.patch.object(helper, 'sysvol', side_effect=AssertionError('unrelated SSH')):
            self.assertEqual(helper.main({'action': 'replication', 'section': 'ad'}), {'healthy': True})

    def test_sysvol_section_is_independent_of_ad_rpc(self):
        with mock.patch.object(helper, 'sysvol', return_value={'configured': False}), \
             mock.patch.object(helper, 'replication', side_effect=AssertionError('unrelated RPC')):
            self.assertEqual(helper.main({'action': 'replication', 'section': 'sysvol'}), {'sysvol': {'configured': False}})

    def test_sections_cannot_invoke_mutations_or_arbitrary_functions(self):
        for action, section in [('overview', 'service_restart'), ('service_restart', 'identity'), ('overview', '__import__')]:
            with self.assertRaisesRegex(ValueError, 'Tundmatu'):
                helper.main({'action': action, 'section': section})


if __name__ == '__main__':
    unittest.main()
