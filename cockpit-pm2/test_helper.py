import importlib.machinery
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


HELPER_PATH = Path(__file__).with_name('cockpit-pm2-helper')
loader = importlib.machinery.SourceFileLoader('pm2_helper', str(HELPER_PATH))
spec = importlib.util.spec_from_loader(loader.name, loader)
helper = importlib.util.module_from_spec(spec)
loader.exec_module(helper)


def process(process_id=0, name='seapro', pid=100):
    return {'id': process_id, 'name': name, 'pid': pid}


class Pm2PublicLinkTests(unittest.TestCase):
    def test_explicit_full_site_and_route_are_both_returned(self):
        sites = [{
            'domain': 'seapro.kirss.ee', 'host': '127.0.0.1', 'port': 8080,
            'https_port': 443, 'certificate': 'a9.kirss.ee', 'enabled': True,
            'managed_by': 'pm2', 'owner_user': 'rix', 'owner_app': 'seapro',
        }]
        routes = [{
            'domain': 'a9-server.kirss.ee', 'path': '/seapro', 'https_port': 443,
            'certificate': 'a9.kirss.ee', 'enabled': True, 'managed_by': 'pm2',
            'owner_user': 'rix', 'owner_app': 'seapro',
        }]
        with mock.patch.object(helper, 'reverse_proxy_sites', return_value=sites), \
             mock.patch.object(helper, 'reverse_proxy_routes', return_value=routes), \
             mock.patch.object(helper, 'process_port_hints', return_value={0: {8080}}):
            links = helper.process_public_urls('rix', [process()], [])
        self.assertEqual(links['seapro'], [
            'https://seapro.kirss.ee/',
            'https://a9-server.kirss.ee/seapro/',
        ])

    def test_legacy_local_site_is_inferred_from_unique_listener_port(self):
        sites = [{
            'domain': 'seapro.kirss.ee', 'host': '127.0.0.1', 'port': 8080,
            'https_port': 443, 'certificate': 'a9.kirss.ee', 'enabled': True,
        }]
        with mock.patch.object(helper, 'reverse_proxy_sites', return_value=sites), \
             mock.patch.object(helper, 'reverse_proxy_routes', return_value=[]), \
             mock.patch.object(helper, 'process_port_hints', return_value={0: {8080}}):
            links = helper.process_public_urls('rix', [process()], [])
        self.assertEqual(links['seapro'], ['https://seapro.kirss.ee/'])

    def test_remote_site_is_not_inferred_from_matching_port(self):
        sites = [{
            'domain': 'nas.example.ee', 'host': '192.168.0.252', 'port': 5001,
            'https_port': 5001, 'certificate': 'example.ee', 'enabled': True,
        }]
        with mock.patch.object(helper, 'reverse_proxy_sites', return_value=sites), \
             mock.patch.object(helper, 'reverse_proxy_routes', return_value=[]), \
             mock.patch.object(helper, 'process_port_hints', return_value={0: {5001}}):
            links = helper.process_public_urls('rix', [process()], [])
        self.assertEqual(links['seapro'], [])

    def test_listener_port_detection_includes_child_processes_and_port_env(self):
        raw = [{'pm_id': 0, 'pm2_env': {'PORT': '3000'}}]

        def command(args, check=True, timeout=45, env=None):
            if args[0] == '/usr/bin/ps':
                return SimpleNamespace(returncode=0, stdout='100 1\n101 100\n', stderr='')
            return SimpleNamespace(
                returncode=0,
                stdout='LISTEN 0 511 127.0.0.1:8080 0.0.0.0:* users:(("node",pid=101,fd=7))\n',
                stderr='',
            )

        with mock.patch.object(helper, 'run', side_effect=command):
            hints = helper.process_port_hints(raw, [process()])
        self.assertEqual(hints[0], {3000, 8080})


if __name__ == '__main__':
    unittest.main()
