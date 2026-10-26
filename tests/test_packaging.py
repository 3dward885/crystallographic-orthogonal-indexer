"""Static/build-helper checks, NOT native Windows compilation or install tests."""
import ast
import importlib.util
import json
from pathlib import Path
import runpy
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

import crystallographic_orthogonal_indexer as app
import main

ROOT = Path(__file__).resolve().parents[1]


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'tools'/f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PackagingTests(unittest.TestCase):
    def test_product_version_metadata_consistent(self):
        self.assertEqual(app.PRODUCT_NAME, 'Crystallographic Orthogonal Indexer')
        self.assertEqual(app.VERSION, '1.0')
        for path in ('packaging/installer.iss', 'packaging/version_info.txt', 'USER_GUIDE.txt'):
            self.assertIn('1.0', (ROOT/path).read_text())
            self.assertIn('Crystallographic Orthogonal Indexer'.lower(), (ROOT/path).read_text().lower())
        expression = ast.parse((ROOT/'packaging/version_info.txt').read_text())
        fixed_info = next(node for node in ast.walk(expression)
                          if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                          and node.func.id == 'FixedFileInfo')
        numeric_versions = {keyword.arg: ast.literal_eval(keyword.value)
                            for keyword in fixed_info.keywords
                            if keyword.arg in ('filevers', 'prodvers')}
        self.assertEqual(numeric_versions, {'filevers': (1, 0, 0, 0), 'prodvers': (1, 0, 0, 0)})
        for node in ast.walk(expression):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id=='StringStruct':
                self.assertNotIn(ast.literal_eval(node.args[0]), ('CompanyName','LegalCopyright'))

    def test_spec_fails_closed_on_nonwindows(self):
        with patch.object(sys, 'platform', 'linux'):
            with self.assertRaisesRegex(SystemExit, 'Windows'):
                runpy.run_path(str(ROOT/'packaging/CrystallographicOrthogonalIndexer.spec'), init_globals={'SPECPATH':str(ROOT/'packaging')})

    def test_installer_peruser_shortcuts_uninstall(self):
        text=(ROOT/'packaging/installer.iss').read_text()
        active='\n'.join(line for line in text.splitlines() if not line.lstrip().startswith(';'))
        for setting in ('PrivilegesRequired=lowest','DefaultDirName={localappdata}\\Programs\\Crystallographic Orthogonal Indexer',
                        'Uninstallable=yes','CreateUninstallRegKey=yes','ArchitecturesAllowed=x64os',
                        'AppId={{B11BE05C-E5E8-4447-8DB4-A8289A009D74}',
                        'Flags: unchecked','{group}\\{#ProductName}','{userdesktop}',
                        'postinstall skipifsilent unchecked'):
            self.assertIn(setting,active)
        for forbidden in ('[Registry]','[UninstallDelete]','AppPublisher=','SignTool=','PrivilegesRequired=admin'):
            self.assertNotIn(forbidden,active)

    def test_build_gates_dependencies_and_never_installs_finished_app(self):
        text=(ROOT/'build_windows.ps1').read_text()
        for expected in ('if ($InstallBuildDependencies)', '3,13,17','26.2.2','--require-native',
                         "'--smoke-test'", "state='built-not-installation-tested'",'installer_executed=$false'):
            self.assertIn(expected,text)
        self.assertNotIn('Start-Process -FilePath $Installer',text)
        self.assertNotIn('ExecutionPolicy Bypass',text)
        pins=(ROOT/'requirements-build.txt').read_text()
        for pin in ('numpy==2.3.5','pyinstaller==6.22.3','pyinstaller-hooks-contrib==2026.9'):
            self.assertIn(pin,pins)

    def test_icon_is_multisize_windows_ico(self):
        data=(ROOT/'packaging/app.ico').read_bytes()
        zero,kind,count=struct.unpack('<HHH',data[:6])
        self.assertEqual((zero,kind),(0,1));self.assertGreaterEqual(count,5)

    def test_main_normal_launch_and_option_rejection(self):
        with patch.object(app,'main') as launch:
            self.assertEqual(main.main([]),0);launch.assert_called_once()
        with self.assertRaises(SystemExit):main.main(['--unexpected'])
        with patch.object(main,'smoke_test',return_value=0) as smoke:
            self.assertEqual(main.main(['--smoke-test','qa.json']),0)
            smoke.assert_called_once_with('qa.json')

    def test_environment_gate_nonwindows(self):
        tool=load_tool('verify_build_environment')
        with patch.object(sys,'platform','linux'):
            with self.assertRaisesRegex(SystemExit,'Windows'):tool.check()

    def test_license_collection_missing_fails(self):
        tool=load_tool('collect_notices')
        class Distribution:
            files=[]
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(sys,'base_prefix',folder), patch.object(tool.metadata,'distribution',return_value=Distribution()):
                with self.assertRaisesRegex(SystemExit,'Missing runtime license notices'):
                    tool.collect(Path(folder)/'out')
            self.assertFalse((Path(folder)/'out/inventory.json').exists())

    def test_license_collection_copies_real_texts_and_hashes(self):
        tool=load_tool('collect_notices')
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)/'python';base.mkdir()
            for rel in ('LICENSE.txt','tcl/tcl8.6/license.terms','tcl/tk8.6/license.terms'):
                p=base/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('Synthetic test fixture: '+rel)
            wheel=Path(folder)/'site';wheel.mkdir()
            (wheel/'LICENSE.txt').write_text('Synthetic wheel test fixture')
            class Distribution:
                files=[Path('LICENSE.txt')]
                def locate_file(self,p):return wheel/p
            with patch.object(sys,'base_prefix',str(base)), patch.object(tool.metadata,'distribution',return_value=Distribution()), patch.object(tool.metadata,'version',return_value='test-fixture'):
                result=tool.collect(Path(folder)/'out')
            self.assertFalse(result['complete_license_audit'])
            self.assertEqual(len(result['files']),6)
            for record in result['files']:
                self.assertEqual((Path(folder)/'out'/record['file']).read_text(),Path(record['source']).read_text())
                self.assertEqual(len(record['sha256']),64)


if __name__ == '__main__': unittest.main(verbosity=2)
