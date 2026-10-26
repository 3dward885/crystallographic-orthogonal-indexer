"""Input-boundary and stored-reference regressions; no experimental Top invented."""
from contextlib import redirect_stdout
from decimal import Decimal
from fractions import Fraction
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import numpy as np
import crystallographic_orthogonal_indexer as app


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = json.loads((ROOT / 'tests/fixtures/accepted_v1_1_Ho1_results.json').read_text(encoding='utf-8'))


class IntegerBoundaryTests(unittest.TestCase):
    def test_signed_integer_boundary_is_preserved(self):
        for magnitude in (2**53 - 1, 2**53):
            for sign in (-1, 1):
                value = sign * magnitude
                for values in ((value, 0, 1), (value, 0.0, 1.0), np.array((value, 0, 1), dtype=np.int64)):
                    with self.subTest(value=value, input_type=type(values).__name__):
                        np.testing.assert_array_equal(app.signed_plane_normal(np.eye(3), values), (float(value), 0, 1))

    def test_integer_beyond_boundary_is_rejected_before_rounding(self):
        for magnitude in (2**53 + 1, 2**53 + 2, 2**63, 10**500):
            for sign in (-1, 1):
                for values in ((sign * magnitude, 0, 1), (sign * magnitude, 0.0, 1.0)):
                    with self.subTest(value=sign * magnitude, mixed_float=isinstance(values[1], float)):
                        with self.assertRaises(ValueError):
                            app.signed_plane_normal(np.eye(3), values)

    def test_exact_noninteger_cannot_round_into_an_integer(self):
        for value in (Decimal('1.00000000000000000001'), Fraction(10**20 + 1, 10**20)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                app.signed_plane_normal(np.eye(3), (value, 0, 1))

    def test_integer_valued_floats_and_numeric_text_remain_accepted(self):
        np.testing.assert_array_equal(app.signed_plane_normal(np.eye(3), (1.0, np.float64(-2), '3.0')), (1, -2, 3))


class StoredReferenceTests(unittest.TestCase):
    def setUp(self):
        inputs = REFERENCE['input']
        self.A = app.cell_matrix(inputs['cell_a_b_c_alpha_beta_gamma'])
        self.front = app.signed_plane_normal(self.A, inputs['front_hkl'])
        self.right = app.signed_plane_normal(self.A, inputs['right_hkl'])
        self.Q = app.front_preserving_frame(self.front, self.right)

    def test_stored_cell_normals_and_front_right(self):
        np.testing.assert_allclose(self.A, REFERENCE['basis']['A_columns_direct_cell_angstrom'], rtol=0, atol=5e-14)
        np.testing.assert_allclose(self.front, REFERENCE['raw_signed']['front_normal_inv_angstrom'], rtol=0, atol=5e-15)
        np.testing.assert_allclose(self.right, REFERENCE['raw_signed']['right_normal_inv_angstrom'], rtol=0, atol=5e-15)
        np.testing.assert_allclose(self.Q[:, 0], REFERENCE['display_frame']['front_unit'], rtol=0, atol=5e-15)
        np.testing.assert_allclose(self.Q[:, 1], REFERENCE['display_frame']['right_unit'], rtol=0, atol=5e-15)
        self.assertAlmostEqual(app.angle_deg(self.front, self.right), REFERENCE['raw_signed']['front_right_angle_deg'], places=12)
        self.assertAlmostEqual(app.angle_deg(self.right, self.Q[:, 1]), REFERENCE['standard_right_handed_frame']['adjustment_deg_front_right_top'][1], places=12)

    def test_explicit_top_reversal_is_separate_from_right_handed_reference(self):
        self.assertNotIn('top_hkl', REFERENCE['input'])
        self.assertTrue(REFERENCE['display_frame']['reverse_display_top'])
        np.testing.assert_allclose(self.Q, REFERENCE['standard_right_handed_frame']['Q_columns_F_R_T_acetate_to_xyz'], rtol=0, atol=5e-15)
        display = self.Q.copy()
        display[:, 2] *= -1  # Reproduce only the recorded display reversal, not a Top hkl.
        np.testing.assert_allclose(display, REFERENCE['display_frame']['D_columns_F_R_T_display_to_xyz'], rtol=0, atol=5e-15)
        np.testing.assert_allclose(np.cross(display[:, 0], display[:, 1]), -display[:, 2], rtol=0, atol=5e-15)
        self.assertAlmostEqual(np.linalg.det(self.Q), 1, places=13)
        self.assertAlmostEqual(np.linalg.det(display), -1, places=13)


class BuildEnvironmentTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('regression_build_environment', ROOT / 'tools/verify_build_environment.py')
        self.tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.tool)
        self.versions = {'numpy': '2.3.5', 'pyinstaller': '6.22.3', 'pyinstaller-hooks-contrib': '2026.9', 'pip': '26.2.2'}

    def check_with_versions(self, versions):
        root = Mock()
        root.tk.call.return_value = 'synthetic-Tk-version'
        with patch.object(self.tool.sys, 'platform', 'win32'), \
             patch.object(self.tool.sys, 'version_info', (3, 13, 17)), \
             patch.object(self.tool.platform, 'machine', return_value='AMD64'), \
             patch.object(self.tool, 'sysconfig_free_threaded', return_value=False), \
             patch.object(self.tool.metadata, 'version', side_effect=versions.__getitem__), \
             patch.object(self.tool.tkinter, 'Tk', return_value=root) as create_root, \
             redirect_stdout(io.StringIO()) as output:
            self.tool.check()
        return json.loads(output.getvalue()), create_root

    def test_reused_environment_with_wrong_pip_is_rejected(self):
        self.versions['pip'] = '0.0.0-synthetic-mismatch'
        with self.assertRaisesRegex(SystemExit, 'pins'):
            self.check_with_versions(self.versions)

    def test_matching_environment_receipt_includes_pip(self):
        receipt, create_root = self.check_with_versions(self.versions)
        self.assertEqual(receipt['packages'], self.versions)
        create_root.assert_called_once()


if __name__ == '__main__':
    unittest.main(verbosity=2)
