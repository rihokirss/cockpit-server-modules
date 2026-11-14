import contextlib
import datetime
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


def load_helper(name):
    path = Path(__file__).with_name(name)
    loader = importlib.machinery.SourceFileLoader(name.replace('-', '_'), str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


h = load_helper('cockpit-samba-sysvol-helper')
ad = load_helper('cockpit-samba-ad-helper')


class SysvolTests(unittest.TestCase):
    def test_config_rejects_shell_options_and_unknown_roles(self):
        for peer in ('-oProxyCommand=anything', 'dc2;whoami', 'dc2\nother', ''):
            with self.assertRaises(ValueError):
                h.validate_config({'role': 'coordinator', 'peer': peer})
        with self.assertRaises(ValueError):
            h.validate_config({'role': 'primary', 'peer': 'dc2.example.test'})
        with self.assertRaises(ValueError):
            h.validate_config({'role': 'peer', 'peer': 'dc1', 'unison_profile': '../../other'})

    def test_gpo_paths_never_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'policy'
            root.mkdir()
            (root / 'normal').write_text('ok')
            self.assertEqual(len(list(h.checked_paths(root))), 2)
            (root / 'outside').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):
                list(h.checked_paths(root))

    def test_freshness_does_not_hide_failed_or_missing_runs(self):
        recent = datetime.datetime.now(datetime.timezone.utc)
        self.assertTrue(h.sync_health({'ok': True, 'finished_at': recent.isoformat()}))
        self.assertFalse(h.sync_health({'ok': False, 'finished_at': recent.isoformat()}))
        self.assertFalse(h.sync_health({'ok': True, 'finished_at': (recent - datetime.timedelta(hours=1)).isoformat()}))
        self.assertFalse(h.sync_health({}))

    def test_json_state_is_private_and_atomic(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'state.json'
            h.write_json(path, {'ok': True})
            self.assertEqual(h.read_json(path), {'ok': True})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(Path(temp).iterdir()), [path])

    def test_file_conflicts_and_timeouts_still_repair_both_dcs_and_fail(self):
        for outcome in ('conflict', 'timeout', 'ok'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as temp:
                calls = []

                def command(args, **kwargs):
                    if '-version' in args:
                        return subprocess.CompletedProcess(args, 0, 'unison same version', '')
                    if outcome == 'timeout':
                        raise subprocess.TimeoutExpired(args, 600)
                    return subprocess.CompletedProcess(args, 1 if outcome == 'conflict' else 0,
                                                       'conflicting file' if outcome == 'conflict' else '', '')

                def remote(config, action, payload=None, **kwargs):
                    calls.append(action)
                    if action == 'status-local':
                        return {'role': 'peer'}
                    if action == 'record-sync':
                        self.assertEqual(payload['ok'], outcome == 'ok')
                    return {'ok': True}

                with patch.object(h, 'STATE', Path(temp)), \
                     patch.object(h, 'validate_profile'), \
                     patch.object(h, 'verify_peer_domain'), \
                     patch.object(h, 'lock', return_value=contextlib.nullcontext()), \
                     patch.object(h, 'remote', side_effect=remote), \
                     patch.object(h, 'command', side_effect=command), \
                     patch.object(h, 'repair', return_value={'ok': True}) as repair:
                    config = {'role': 'coordinator', 'peer': 'dc2', 'unison_profile': 'sysvol'}
                    if outcome == 'ok':
                        self.assertTrue(h.run_sync(config)['ok'])
                    else:
                        with self.assertRaises(RuntimeError):
                            h.run_sync(config)
                    repair.assert_called_once()
                    self.assertIn('repair', calls)
                    state = json.loads((Path(temp) / 'sysvol-status.json').read_text())
                    self.assertEqual(state['ok'], outcome == 'ok')
                    self.assertFalse(state['running'])

    def test_peer_control_is_forwarded_and_never_runs_local_unison(self):
        with patch.object(h.os, 'geteuid', return_value=0), \
             patch.object(h.CONFIG.__class__, 'exists', return_value=True), \
             patch.object(h, 'load_config', return_value={'role': 'peer', 'peer': 'dc1'}), \
             patch.object(h, 'verify_peer_domain'), \
             patch.object(h, 'remote', side_effect=[{'role': 'coordinator'}, {'message': 'enabled'}]) as remote, \
             patch.object(h, 'command') as command:
            self.assertEqual(h.main('enable')['message'], 'enabled')
            self.assertEqual(remote.call_args.args[1], 'enable')
            command.assert_not_called()

    def test_peer_control_rejects_peer_to_peer_recursion(self):
        with patch.object(h.os, 'geteuid', return_value=0), \
             patch.object(h.CONFIG.__class__, 'exists', return_value=True), \
             patch.object(h, 'load_config', return_value={'role': 'peer', 'peer': 'dc1'}), \
             patch.object(h, 'verify_peer_domain'), \
             patch.object(h, 'remote', return_value={'role': 'peer'}) as remote:
            with self.assertRaises(ValueError):
                h.main('enable')
            remote.assert_called_once()

    def test_cross_domain_sysvol_is_rejected(self):
        with patch.object(h, 'domain_identity', return_value={'realm': 'example.test', 'sid': 'S-1-5-21-1'}):
            h.verify_peer_domain({'domain': {'realm': 'example.test', 'sid': 'S-1-5-21-1'}})
            for peer in ({}, {'domain': {'realm': 'example.test', 'sid': 'S-1-5-21-2'}}):
                with self.assertRaises(ValueError):
                    h.verify_peer_domain(peer)

    def test_drs_counts_inbound_partitions_only(self):
        raw = '''==== INBOUND NEIGHBORS ====
DC=example,DC=test
    Site\\DC2 via RPC
    Last attempt was successful
    0 consecutive failure(s).
CN=Configuration,DC=example,DC=test
    Site\\DC2 via RPC
    Last attempt was successful
    0 consecutive failure(s).
==== OUTBOUND NEIGHBORS ====
DC=example,DC=test
    Site\\DC2 via RPC
    6 consecutive failure(s).
'''
        with patch.object(ad, 'samba', return_value=subprocess.CompletedProcess([], 0, raw, '')):
            result = ad.replication()
        self.assertEqual(result['partitions'], 2)
        self.assertEqual(result['failures'], 0)
        self.assertTrue(result['healthy'])

    def test_ad_success_does_not_mask_sysvol_failure(self):
        with patch.object(ad, 'replication', return_value={'healthy': True}), \
             patch.object(ad, 'sysvol', return_value={'healthy': False}):
            self.assertFalse(ad.replication_status()['overall_healthy'])


if __name__ == '__main__':
    unittest.main()
