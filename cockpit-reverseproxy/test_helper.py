import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock


HELPER_PATH = Path(__file__).with_name('cockpit-reverseproxy-helper')
loader = importlib.machinery.SourceFileLoader('reverseproxy_helper', str(HELPER_PATH))
spec = importlib.util.spec_from_loader(loader.name, loader)
helper = importlib.util.module_from_spec(spec)
loader.exec_module(helper)

CERTIFICATE = 'a9.kirss.ee'


def site(port, host, upstream_port, scheme='http'):
    return {
        'id': str(uuid.uuid4()),
        'domain': 'a9.kirss.ee',
        'scheme': scheme,
        'host': host,
        'port': upstream_port,
        'https_port': port,
        'certificate': CERTIFICATE,
        'websocket': True,
        'enabled': True,
    }


class ReverseProxyHelperTests(unittest.TestCase):
    def setUp(self):
        self.cert_patch = mock.patch.object(helper, 'has_cert', side_effect=lambda name: name == CERTIFICATE)
        self.cert_patch.start()
        self.addCleanup(self.cert_patch.stop)

    def test_legacy_site_gets_stable_id(self):
        legacy = [{
            'domain': 'a9.kirss.ee', 'scheme': 'https', 'host': '192.168.0.252',
            'port': 5001, 'https_port': 5001, 'certificate': CERTIFICATE,
            'websocket': True, 'enabled': True,
        }]
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory, 'sites.json')
            database.write_text(json.dumps(legacy))
            with mock.patch.object(helper, 'DB', database):
                first = helper.load()
                second = helper.load()
        self.assertEqual(first[0]['id'], second[0]['id'])
        uuid.UUID(first[0]['id'])

    def test_same_domain_generates_distinct_tls_ports_and_one_http_server(self):
        sites = [
            site(5001, '192.168.0.252', 5001, 'https'),
            site(8125, '192.168.0.200', 8123),
        ]
        config = helper.generate(sites, [], [])
        self.assertEqual(config.count('    listen 80;'), 1)
        self.assertIn('    listen 5001 ssl;', config)
        self.assertIn('    listen 8125 ssl;', config)
        self.assertIn('proxy_pass https://192.168.0.252:5001;', config)
        self.assertIn('proxy_pass http://192.168.0.200:8123;', config)

    def test_save_adds_second_port_without_replacing_first(self):
        existing = site(5001, '192.168.0.252', 5001, 'https')
        captured = {}

        def persist(sites, routes=None, hosts=None):
            captured['sites'] = sites

        request = {
            'action': 'save',
            'site': {
                'domain': 'a9.kirss.ee', 'scheme': 'http', 'host': '192.168.0.200',
                'port': 8123, 'https_port': 8125, 'certificate': CERTIFICATE,
                'websocket': True, 'enabled': True,
            },
        }
        with mock.patch.object(helper, 'load', return_value=[existing]), \
             mock.patch.object(helper, 'load_routes', return_value=[]), \
             mock.patch.object(helper, 'load_route_hosts', return_value=[]), \
             mock.patch.object(helper, 'persist', side_effect=persist):
            result = helper.main(request)
        self.assertTrue(result['ok'])
        self.assertEqual(len(captured['sites']), 2)
        self.assertEqual({item['https_port'] for item in captured['sites']}, {5001, 8125})

    def test_duplicate_domain_and_https_port_is_rejected(self):
        first = site(5001, '192.168.0.252', 5001, 'https')
        duplicate = site(5001, '192.168.0.200', 8123)
        with self.assertRaisesRegex(ValueError, 'juba kasutuses'):
            helper.validate_sites([first, duplicate])

    def test_pm2_route_validation_and_generation_remain_supported(self):
        route = {
            'domain': 'a9-server.kirss.ee', 'path': '/tinkerbox', 'scheme': 'http',
            'host': '127.0.0.1', 'port': 3000, 'https_port': 443,
            'certificate': '', 'description': 'PM2 · rix · tinkerbox',
            'strip_prefix': False, 'websocket': True, 'enabled': True,
            'managed_by': 'pm2', 'owner_user': 'rix', 'owner_app': 'tinkerbox',
        }
        with mock.patch.object(helper, 'certificate_for_domain', return_value=CERTIFICATE), \
             mock.patch.object(helper, 'cert_domains', return_value=['a9-server.kirss.ee']):
            validated = helper.validate_route(route)
            config = helper.generate([], [validated], [{
                'domain': 'a9-server.kirss.ee', 'https_port': 443,
                'certificate': CERTIFICATE, 'enabled': True,
            }])
        self.assertEqual(validated['managed_by'], 'pm2')
        self.assertEqual(validated['owner_app'], 'tinkerbox')
        self.assertIn('location ^~ /tinkerbox/', config)
        self.assertIn('proxy_pass http://127.0.0.1:3000;', config)


if __name__ == '__main__':
    unittest.main()
