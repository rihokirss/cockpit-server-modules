import importlib.machinery
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader(
    'radius_helper', str(Path(__file__).with_name('cockpit-radius-helper')))
spec = importlib.util.spec_from_loader(loader.name, loader)
h = importlib.util.module_from_spec(spec)
loader.exec_module(h)


class RadiusPolicyTests(unittest.TestCase):
    def test_existing_radius_group_does_not_fall_back_to_domain_users(self):
        for name in ('radius', 'Radius', 'RADIUS'):
            with patch.object(h, 'domain_info', return_value={'realm': 'example.test'}), \
                 patch.object(h, 'ad_groups', return_value=[name, 'Domain Users']), \
                 patch.object(h, 'validate_group', return_value=(name, 'S-1-5-21-1', 1001)):
                self.assertEqual(h.defaults()['allowed_group'], name)

    def test_legacy_vpn_exception_is_per_host_and_keeps_proxy_protection(self):
        fields = {'name': 'VPN gateway', 'ipaddr': '192.0.2.1', 'secret': 's' * 40,
                  'require_message_authenticator': 'no'}
        client = h.validate_client(fields)
        rendered = h.render_clients({'clients': [client]})
        self.assertIn('192.0.2.1/32', rendered)
        self.assertIn('require_message_authenticator = no', rendered)
        self.assertIn('limit_proxy_state = yes', rendered)
        with self.assertRaises(ValueError):
            h.validate_client({**fields, 'ipaddr': '192.0.2.0/24'})
        with self.assertRaises(ValueError):
            h.validate_client({**fields, 'require_message_authenticator': 'anything'})


if __name__ == '__main__':
    unittest.main()
