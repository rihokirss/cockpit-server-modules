import importlib.machinery
import importlib.util
from pathlib import Path
import unittest
import subprocess
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader(
    'radius_helper', str(Path(__file__).with_name('cockpit-radius-helper')))
spec = importlib.util.spec_from_loader(loader.name, loader)
h = importlib.util.module_from_spec(spec)
loader.exec_module(h)


class RadiusPolicyTests(unittest.TestCase):
    def test_vpn_role_is_scoped_to_packet_source_and_accept_only(self):
        config = {'auth_port': 1812, 'accounting_port': 1813,
                  'vpn_role': {'enabled': True, 'gateway_ip': '192.0.2.1'}}
        text = h.render_site(config)
        self.assertIn('Packet-Src-IP-Address == 192.0.2.1', text)
        self.assertNotIn('NAS-IP-Address ==', text)
        self.assertNotIn('cockpit_vpn_role', text.split('Post-Auth-Type REJECT')[1])
        config['vpn_role']['enabled'] = False
        self.assertNotIn('cockpit_vpn_role', h.render_site(config))

    def test_vpn_role_validation_rejects_collisions_and_outside_addresses(self):
        config = {'clients': [{'ipaddr': '192.0.2.1/32'}]}
        role = {'enabled': True, 'gateway_ip': '192.0.2.1', 'group': 'admins',
                'subnet': '10.0.0.0/24', 'reserved_start': '10.0.0.240',
                'reserved_end': '10.0.0.249', 'addresses': 'alice=10.0.0.240\nbob=10.0.0.241'}
        with patch.object(h, 'validate_group', return_value=('admins', 'S-1-5-21-1', 1001)):
            self.assertEqual(h.validate_vpn_role(role, config)['addresses']['alice'], '10.0.0.240')
            for addresses in ('alice=10.0.0.240\nbob=10.0.0.240',
                              'alice=10.0.0.240\nALICE=10.0.0.241',
                              'alice=10.0.0.10', 'alice=bad', 'alice;cmd=10.0.0.240'):
                with self.assertRaises(ValueError):
                    h.validate_vpn_role({**role, 'addresses': addresses}, config)
            with self.assertRaises(ValueError):
                h.validate_vpn_role(role, {'clients': [{'ipaddr': '192.0.2.0/24'}]})

    def test_role_requires_mapping_and_ad_membership_and_rejects_foreign_domains(self):
        role_loader = importlib.machinery.SourceFileLoader('vpn_role', str(Path(__file__).with_name('cockpit-radius-vpn-role')))
        role_spec = importlib.util.spec_from_loader(role_loader.name, role_loader)
        role = importlib.util.module_from_spec(role_spec)
        role_loader.exec_module(role)
        config = {'domain': 'TEST', 'realm': 'test.example', 'group_gid': 1234,
                  'addresses': {'alice': '10.0.0.240'}}
        member = lambda *a, **kw: subprocess.CompletedProcess(a, 0, '100\n1234\n', '')
        ordinary = lambda *a, **kw: subprocess.CompletedProcess(a, 0, '100\n', '')
        failed = lambda *a, **kw: subprocess.CompletedProcess(a, 1, '', 'error')
        for user in ('alice', 'TEST\\Alice', 'alice@test.example'):
            self.assertEqual(role.address_for(config, user, member), '10.0.0.240')
            self.assertIsNone(role.address_for(config, user, ordinary))
        self.assertIsNone(role.address_for(config, 'bob', member))
        self.assertIsNone(role.address_for(config, 'bob@alternate.example', member))
        self.assertEqual(role.address_for({**config, 'aliases': {'alice@alternate.example': 'alice'}},
                                         'alice@alternate.example', member), '10.0.0.240')
        with self.assertRaises(RuntimeError):
            role.address_for(config, 'alice', failed)
        for user in ('EVIL\\alice', 'alice@evil.example', 'alice;cmd', 'alice$(cmd)'):
            with self.assertRaises(ValueError):
                role.address_for(config, user, member)

    def test_existing_radius_group_does_not_fall_back_to_domain_users(self):
        for name in ('radius', 'Radius', 'RADIUS', 'ITK radius'):
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
