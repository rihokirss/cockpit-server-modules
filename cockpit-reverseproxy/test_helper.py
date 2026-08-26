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
    def test_migrated_headers_and_timeouts_survive_validation(self):
        source=site(443,'192.168.0.10',5052)
        source.update(headers={'Host':'example.ee','X-Forwarded-For':'$remote_addr',
                               'Cache-Control':'no-store, no-cache'},read_timeout=600,send_timeout=300)
        result=helper.validate(source)
        config=helper.generate([result],[],[])
        self.assertIn('proxy_read_timeout 600s;',config)
        self.assertIn('proxy_send_timeout 300s;',config)
        self.assertIn('proxy_set_header Cache-Control "no-store, no-cache";',config)
        self.assertIn('proxy_set_header X-Forwarded-For "$remote_addr";',config)
        self.assertEqual(config.count('proxy_set_header Host '),1)

    def test_custom_header_validation_and_quoting_prevent_directive_injection(self):
        for headers in ({'Bad;name':'value'},{'X-Test':'line\nbreak'},{'X-Test':'a','x-test':'b'},[]):
            with self.assertRaises(ValueError):helper.proxy_options({'headers':headers})
        for timeout in (0,86401,True,'1; bad'):
            with self.assertRaises(ValueError):helper.proxy_options({'read_timeout':timeout})
        lines=helper.proxy_location('http://example:80',options={'headers':{'X-Test':'"; deny all; #'}})
        self.assertIn('        proxy_set_header X-Test "\\"; deny all; #";',lines)

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

    def test_full_site_pm2_owner_is_validated_and_preserved(self):
        value = site(443, '127.0.0.1', 8080)
        value.update({'managed_by': 'pm2', 'owner_user': 'rix', 'owner_app': 'seapro'})
        validated = helper.validate(value)
        self.assertEqual(validated['managed_by'], 'pm2')
        self.assertEqual(validated['owner_user'], 'rix')
        self.assertEqual(validated['owner_app'], 'seapro')

    def test_partial_full_site_pm2_owner_is_rejected(self):
        value = site(443, '127.0.0.1', 8080)
        value.update({'owner_user': 'rix'})
        with self.assertRaisesRegex(ValueError, 'PM2 omanik'):
            helper.validate(value)

    def test_portal_entries_are_visible_by_default_and_can_be_hidden(self):
        visible = site(443, '127.0.0.1', 8080)
        hidden = site(5001, '192.168.0.252', 5001, 'https')
        hidden['portal_hidden'] = True
        disabled = site(8125, '192.168.0.200', 8123)
        disabled['enabled'] = False
        result = helper.portal_catalog([visible, hidden, disabled], [])
        self.assertEqual([entry['id'] for entry in result['services']], [visible['id']])

    def test_portal_catalog_supports_https_ports_and_route_subpaths(self):
        synology = site(5001, '192.168.0.252', 5001, 'https')
        synology.update({'portal_label': 'Synology', 'portal_category': 'storage'})
        route = {
            'id': str(uuid.uuid4()), 'domain': 'a9-server.kirss.ee', 'path': '/tinkerbox',
            'certificate': CERTIFICATE, 'https_port': 443, 'enabled': True,
            'portal_label': 'Tinkerbox', 'portal_category': 'tool',
        }
        result = helper.portal_catalog([synology], [route])
        by_label = {entry['label']: entry for entry in result['services']}
        self.assertEqual(by_label['Synology']['url'], 'https://a9.kirss.ee:5001/')
        self.assertEqual(by_label['Tinkerbox']['url'], 'https://a9-server.kirss.ee/tinkerbox/')
        self.assertEqual(by_label['Tinkerbox']['type'], 'route')

    def test_invalid_portal_category_is_rejected(self):
        value = site(443, '127.0.0.1', 8080)
        value['portal_category'] = 'admin'
        with self.assertRaisesRegex(ValueError, 'kategooria'):
            helper.validate(value)

    def test_catalog_json_never_contains_internal_proxy_details(self):
        value = site(443, '10.23.45.67', 49152)
        value.update({'portal_label': 'SeaPro', 'portal_description': 'Mereprojekt', 'portal_category': 'project'})
        encoded = json.dumps(helper.portal_catalog([value], []))
        self.assertNotIn('10.23.45.67', encoded)
        self.assertNotIn('49152', encoded)
        self.assertNotIn('/etc/letsencrypt', encoded)
        self.assertNotIn('certificate', encoded)
        self.assertEqual(set(helper.portal_catalog([value], [])['services'][0]), {'id','label','description','category','type','url'})

    def test_catalog_file_is_written_atomically_as_public_json(self):
        value = site(443, '127.0.0.1', 8080)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory, 'services.json')
            with mock.patch.object(helper, 'CATALOG', target):
                helper.write_catalog([value], [])
            data = json.loads(target.read_text())
            self.assertEqual(len(data['services']), 1)
            self.assertEqual(target.stat().st_mode & 0o777, 0o644)

    def test_api_location_is_generated_only_for_catalog_site(self):
        portal = site(443, '127.0.0.1', 8090)
        portal['portal_catalog'] = True
        ordinary = site(5001, '192.168.0.252', 5001, 'https')
        config = helper.generate([portal, ordinary], [], [])
        self.assertEqual(config.count('location = /api/services'), 1)
        self.assertIn(f'alias {helper.CATALOG};', config)

    def test_dsm_web_paths_are_exposed_on_standard_https_port(self):
        portal = site(443, '127.0.0.1', 8090)
        synology = site(5001, '192.168.0.252', 5001, 'https')
        synology['dsm_passthrough'] = True
        config = helper.generate([portal, synology], [], [])
        port_443 = config[config.index('listen 443 ssl'):config.index('listen 5001 ssl')]
        self.assertIn('location = /index.cgi {', port_443)
        self.assertIn('location ^~ /webman/ {', port_443)
        self.assertIn('location ^~ /webapi/ {', port_443)
        self.assertIn('location ^~ /scripts/ {', port_443)
        self.assertIn('location ^~ /synoSDSjslib/ {', port_443)
        self.assertIn('proxy_pass https://192.168.0.252:5001;', port_443)
        self.assertNotIn('location ^~ /webman/ {', config[config.index('listen 5001 ssl'):])

    def test_dsm_passthrough_requires_standard_https_site(self):
        synology = site(5001, '192.168.0.252', 5001, 'https')
        synology['dsm_passthrough'] = True
        with self.assertRaisesRegex(ValueError, 'HTTPS port 443'):
            helper.validate_sites([synology])

    def test_only_one_dsm_passthrough_target_is_allowed_per_domain(self):
        portal = site(443, '127.0.0.1', 8090)
        first = site(5001, '192.168.0.252', 5001, 'https')
        second = site(5002, '192.168.0.253', 5001, 'https')
        first['dsm_passthrough'] = second['dsm_passthrough'] = True
        with self.assertRaisesRegex(ValueError, 'ainult üks'):
            helper.validate_sites([portal, first, second])

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


def site_route(path='/labs', port=8095, https_port=443, certificate=CERTIFICATE):
    return {
        'id': str(uuid.uuid4()), 'domain': 'a9.kirss.ee', 'path': path, 'scheme': 'http',
        'host': '127.0.0.1', 'port': port, 'https_port': https_port,
        'certificate': certificate, 'description': '', 'strip_prefix': False,
        'websocket': False, 'enabled': True,
    }


class SiteDomainRouteTests(unittest.TestCase):
    """Sub-path routes riding on a full-domain service (e.g. a9.kirss.ee/labs)."""

    def setUp(self):
        self.cert_patch = mock.patch.object(helper, 'has_cert', side_effect=lambda name: name == CERTIFICATE)
        self.cert_patch.start()
        self.addCleanup(self.cert_patch.stop)

    def test_route_on_site_domain_is_injected_into_tls_block(self):
        config = helper.generate([site(443, '127.0.0.1', 8090)], [site_route()], [])
        self.assertIn('location = /labs { return 308 /labs/$is_args$args; }', config)
        self.assertIn('location ^~ /labs/ {', config)
        self.assertIn('proxy_pass http://127.0.0.1:8095;', config)
        # No third standalone server block for the same domain.
        self.assertEqual(config.count('server_name a9.kirss.ee;'), 2)
        self.assertNotIn('location / { return 404; }', config)

    def test_route_locations_precede_site_root_location(self):
        config = helper.generate([site(443, '127.0.0.1', 8090)], [site_route()], [])
        tls_block = config[config.index('listen 443 ssl'):]
        self.assertLess(tls_block.index('location ^~ /labs/'), tls_block.index('    location / {'))

    def test_route_on_plain_http_site_domain(self):
        plain = site(443, '127.0.0.1', 8090)
        plain['certificate'] = ''
        route = site_route(certificate='')
        with mock.patch.object(helper, 'certificate_for_domain', return_value=''), \
             mock.patch.object(helper, 'has_cert', return_value=False):
            config = helper.generate([plain], [route], [])
        http_block = config[config.index('listen 80'):]
        self.assertIn('location ^~ /labs/', http_block)

    def test_route_port_or_cert_mismatch_with_site_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'ühtima täisdomeeni'):
            helper.route_groups([site_route(https_port=5001)], [site(443, '127.0.0.1', 8090)], [])

    def test_route_host_on_site_domain_still_rejected(self):
        hosts = [{'domain': 'a9.kirss.ee', 'https_port': 443, 'certificate': CERTIFICATE, 'enabled': True}]
        with self.assertRaisesRegex(ValueError, 'täisdomeeni proxy kasutuses'):
            helper.route_groups([], [site(443, '127.0.0.1', 8090)], hosts)

    def test_route_save_on_site_domain_skips_route_host(self):
        captured = {}

        def persist(sites, routes=None, hosts=None):
            captured['routes'] = routes
            captured['hosts'] = hosts

        request = {'action': 'route_save', 'route': site_route()}
        with mock.patch.object(helper, 'load', return_value=[site(443, '127.0.0.1', 8090)]), \
             mock.patch.object(helper, 'load_routes', return_value=[]), \
             mock.patch.object(helper, 'load_route_hosts', return_value=[]), \
             mock.patch.object(helper, 'cert_domains', return_value=['a9.kirss.ee']), \
             mock.patch.object(helper, 'persist', side_effect=persist):
            result = helper.main(request)
        self.assertTrue(result['ok'])
        self.assertEqual(captured['hosts'], [])
        self.assertEqual(len(captured['routes']), 1)

    def test_route_save_on_site_domain_inherits_certificate(self):
        request = {'action': 'route_validate', 'route': site_route(certificate='')}
        with mock.patch.object(helper, 'load', return_value=[site(443, '127.0.0.1', 8090)]), \
             mock.patch.object(helper, 'load_routes', return_value=[]), \
             mock.patch.object(helper, 'load_route_hosts', return_value=[]), \
             mock.patch.object(helper, 'certificate_for_domain', return_value=''), \
             mock.patch.object(helper, 'cert_domains', return_value=['a9.kirss.ee']):
            result = helper.main(request)
        self.assertEqual(result['route']['certificate'], CERTIFICATE)

    def test_portal_catalog_url_for_route_on_site_domain(self):
        route = site_route()
        route.update({'portal_label': 'ITK Labs', 'portal_category': 'project'})
        result = helper.portal_catalog([], [route])
        self.assertEqual(result['services'][0]['url'], 'https://a9.kirss.ee/labs/')
        self.assertEqual(result['services'][0]['type'], 'route')

    def test_catalog_location_coexists_with_site_domain_routes(self):
        portal = site(443, '127.0.0.1', 8090)
        portal['portal_catalog'] = True
        config = helper.generate([portal], [site_route()], [])
        self.assertEqual(config.count('location = /api/services'), 1)
        self.assertIn('location ^~ /labs/', config)

    def test_multiple_tls_ports_inject_route_only_into_matching_block(self):
        sites = [site(443, '127.0.0.1', 8090), site(5001, '192.168.0.252', 5001, 'https')]
        config = helper.generate(sites, [site_route()], [])
        self.assertEqual(config.count('location ^~ /labs/'), 1)
        self.assertLess(config.index('listen 443 ssl'), config.index('location ^~ /labs/'))
        self.assertLess(config.index('location ^~ /labs/'), config.index('listen 5001 ssl'))

    def test_disabled_site_makes_route_standalone_again(self):
        disabled = site(443, '127.0.0.1', 8090)
        disabled['enabled'] = False
        config = helper.generate([disabled], [site_route()], [])
        self.assertIn('location ^~ /labs/', config)
        self.assertIn('location / { return 404; }', config)


if __name__ == '__main__':
    unittest.main()
