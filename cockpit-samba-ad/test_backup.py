import importlib.machinery
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader(
    'samba_backup_helper', str(Path(__file__).with_name('cockpit-samba-ad-helper')))
spec = importlib.util.spec_from_loader(loader.name, loader)
h = importlib.util.module_from_spec(spec)
loader.exec_module(h)


class BackupCommandTests(unittest.TestCase):
    def authenticated_command(self, args, fail=False):
        captured = {}
        request = {'admin_user': 'BackupAdmin', 'admin_password': 'test-only-password'}
        original_temporary_file = tempfile.NamedTemporaryFile
        with tempfile.TemporaryDirectory() as directory:
            def temporary_file(*args, **kwargs):
                kwargs['dir'] = directory
                return original_temporary_file(*args, **kwargs)

            def run(argv, **kwargs):
                captured['argv'] = argv
                credential = Path(argv[argv.index('-A') + 1])
                captured['credential'] = credential
                self.assertEqual(credential.stat().st_mode & 0o777, 0o600)
                self.assertIn('password = test-only-password', credential.read_text())
                self.assertNotIn(request['admin_password'], argv)
                if fail:
                    raise RuntimeError('backup command failed')
                return subprocess.CompletedProcess(argv, 0, 'ok', '')

            with patch.object(h, 'domain_info', return_value={'netbios': 'EXAMPLE'}), \
                 patch.object(h.tempfile, 'NamedTemporaryFile', side_effect=temporary_file), \
                 patch.object(h, 'run', side_effect=run):
                if fail:
                    with self.assertRaises(RuntimeError):
                        h.samba_auth(request, args)
                else:
                    h.samba_auth(request, args)
            self.assertFalse(captured['credential'].exists())
        return captured['argv']

    def test_online_backup_uses_server_without_ldap_H(self):
        argv = self.authenticated_command(['domain', 'backup', 'online',
                                            '--server=dc1.example.test', '--targetdir=/backup'])
        self.assertIn('--server=dc1.example.test', argv)
        self.assertNotIn('-H', argv)
        self.assertIn('--use-kerberos=off', argv)

    def test_gpo_backup_keeps_ldap_target(self):
        argv = self.authenticated_command(['gpo', 'backup', '{00000000-0000-0000-0000-000000000001}'])
        self.assertEqual(argv[argv.index('-H') + 1], 'ldap://127.0.0.1')

    def test_failed_backup_also_removes_credentials(self):
        self.authenticated_command(['domain', 'backup', 'online', '--server=dc1'], fail=True)

    def test_backup_directory_is_private_even_if_it_already_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'backups'
            target.mkdir(mode=0o755)
            with patch.object(h, 'BACKUPS', target), \
                 patch.object(h, 'BACKUP_STATUS', Path(directory) / 'status.json'), \
                 patch.object(h, 'domain_info', return_value={'dc': 'dc1.example.test'}), \
                 patch.object(h, 'samba_auth', return_value=subprocess.CompletedProcess([], 0, 'ok', '')) as auth, \
                 patch.object(h, 'audit'):
                h.main({'action': 'backup'})
            self.assertEqual(target.stat().st_mode & 0o777, 0o700)
            self.assertIn('--server=dc1.example.test', auth.call_args.args[1])
            self.assertFalse(Path(auth.call_args.kwargs['env']['TMPDIR']).exists())

    def test_failed_backup_keeps_both_output_streams_and_redacts_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            status=Path(directory) / 'status.json'
            request={'action':'backup','admin_password':'do-not-log-this'}
            failed=subprocess.CompletedProcess([],1,'Copying SYSVOL files\n',
                'Traceback: failure do-not-log-this /run/cockpit-samba-auth-test123')
            with patch.object(h,'BACKUPS',Path(directory)/'backups'), \
                 patch.object(h,'BACKUP_STATUS',status), \
                 patch.object(h,'domain_info',return_value={'dc':'dc1'}), \
                 patch.object(h,'samba_auth',return_value=failed), \
                 patch.object(h,'audit'):
                with self.assertRaises(RuntimeError):h.main(request)
                record=h.backup_status()
            self.assertFalse(record['ok'])
            self.assertIn('Copying SYSVOL files',record['output'])
            self.assertIn('Traceback',record['output'])
            self.assertNotIn('do-not-log-this',status.read_text())
            self.assertNotIn('/run/cockpit-samba-auth-test123',status.read_text())
            self.assertEqual(status.stat().st_mode & 0o777,0o600)

    def test_failed_sysvol_copy_is_removed_with_private_work_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            status=Path(directory)/'status.json'
            created=[]
            def failed_copy(request,args,**kwargs):
                work=Path(kwargs['env']['TMPDIR'])
                self.assertEqual(work.stat().st_mode & 0o777,0o700)
                (work/'partial-sysvol-copy').write_text('incomplete data')
                created.append(work)
                raise RuntimeError('SMB access denied')
            with patch.object(h,'BACKUPS',Path(directory)/'backups'), \
                 patch.object(h,'BACKUP_STATUS',status), \
                 patch.object(h,'domain_info',return_value={'dc':'dc1'}), \
                 patch.object(h,'samba_auth',side_effect=failed_copy), \
                 patch.object(h,'audit'):
                with self.assertRaisesRegex(RuntimeError,'SMB access denied'):h.main({'action':'backup'})
            self.assertTrue(created)
            self.assertFalse(created[0].exists())


if __name__ == '__main__':
    unittest.main()
