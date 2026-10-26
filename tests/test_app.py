"""Core, file safety, and real-Tcl/controller tests; no display is required.

These tests do NOT claim native Tk widgets/dialog rendering was exercised.
"""
import importlib.util
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import tkinter as tk
import numpy as np
import crystallographic_orthogonal_indexer as app

CUBIC = (1, 1, 1, 90, 90, 90)
LEFT = ('1', '1', '1', '90', '90', '90', '1', '0', '0', '0', '1', '0', '0', '0', '-1')
RIGHT = LEFT[:-1] + ('1',)


class CoreTests(unittest.TestCase):
    def test_cubic_both_handednesses(self):
        for h, sign in (((0, 0, 1), 1), ((0, 0, -1), -1)):
            r = app.solve_frame(CUBIC, (1, 0, 0), (0, 1, 0), h)
            np.testing.assert_allclose(r['D'], np.diag((1, 1, sign)), atol=1e-14)
            self.assertEqual(r['sign'], sign)
            self.assertAlmostEqual(r['det'], sign)
            np.testing.assert_allclose(np.cross(r['D'][:, 0], r['D'][:, 1]), sign*r['D'][:, 2], atol=1e-14)

    def test_orthorhombic_normal_not_direct_direction(self):
        r = app.solve_frame((2, 3, 5, 90, 90, 90), (1, 1, 0), (0, 1, 1), (0, 0, 1))
        np.testing.assert_allclose(r['raw'][:, 0], (.5, 1/3, 0), atol=1e-14)
        self.assertGreater(app.angle_deg(r['raw'][:, 0], (2, 3, 0)), 20)

    def test_oblique_plane_perpendicularity(self):
        cell = (4, 6, 7, 70, 105, 80)
        r = app.solve_frame(cell, (2, -3, 1), (1, 4, -2), (-1, 1, 3))
        for j, h in enumerate(r['hkl']):
            # An independent in-plane fractional displacement satisfies h.d=0.
            h = np.array(h)
            for axis in np.eye(3):
                d = np.cross(h, axis)
                self.assertAlmostEqual(float(r['raw'][:, j] @ (r['A'] @ d)), 0, places=12)
        np.testing.assert_allclose(r['A'].T @ r['B'], np.eye(3), atol=1e-14)

    def test_signed_inputs_no_hidden_flip(self):
        for fsign in (-1, 1):
            for rsign in (-1, 1):
                for tsign in (-1, 1):
                    r = app.solve_frame(CUBIC, (fsign, 0, 0), (0, rsign, 0), (0, 0, tsign))
                    np.testing.assert_allclose(r['D'], np.diag((fsign, rsign, tsign)), atol=1e-14)
                    self.assertGreater(np.dot(r['D'][:, 1], r['raw_unit'][:, 1]), 0)
                    self.assertGreater(np.dot(r['D'][:, 2], r['raw_unit'][:, 2]), 0)

    def test_nonorthogonal_adjustments(self):
        r = app.solve_frame(CUBIC, (1, 0, 0), (1, 1, 0), (1, 1, -1))
        np.testing.assert_allclose(r['adjustments'], (0, 45, math.degrees(math.acos(1/math.sqrt(3)))), atol=1e-12)
        np.testing.assert_allclose(r['raw'][:, 2], (1, 1, -1), atol=1e-14)

    def test_random_valid_cells_and_roundtrip(self):
        rng = np.random.default_rng(1202)
        passed = 0
        for _ in range(200):
            cell = tuple(rng.uniform(2, 30, 3)) + tuple(rng.uniform(70, 110, 3))
            h = rng.integers(-7, 8, (3, 3))
            if abs(np.linalg.det(h)) < .5:
                continue
            r = app.solve_frame(cell, *h)
            np.testing.assert_allclose(r['D'].T @ r['D'], np.eye(3), atol=1e-12)
            self.assertAlmostEqual(abs(r['det']), 1, places=12)
            v = rng.normal(size=3)
            np.testing.assert_allclose(r['D'] @ (r['D'].T @ v), v, atol=1e-12)
            np.testing.assert_allclose(r['Q_standard'][:, :2], r['D'][:, :2], atol=0)
            passed += 1
        self.assertGreater(passed, 170)

    def test_invalid_cells(self):
        for cell in ((0, 1, 1, 90, 90, 90), (-1, 1, 1, 90, 90, 90),
                     (1, 1, 1, 0, 90, 90), (1, 1, 1, 180, 90, 90),
                     (1, 1, 1, 10, 10, 170), (1, 1, 1, 60, 60, 120),
                     (1e-20, 1, 1, 90, 90, 90), (1e308, 1e308, 1e308, 90, 90, 90),
                     (1, 1, 1, float('nan'), 90, 90), (1, 1, 1, 90, 90, float('inf'))):
            with self.subTest(cell=cell), self.assertRaises(ValueError):
                app.solve_frame(cell, (1, 0, 0), (0, 1, 0), (0, 0, 1))

    def test_zero_parallel_noninteger_nonfinite(self):
        for h in ((0, 0, 0), (1.5, 0, 0), (float('nan'), 0, 1), (float('inf'), 1, 0)):
            for index in range(3):
                args = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
                args[index] = h
                with self.assertRaises(ValueError):
                    app.solve_frame(CUBIC, *args)
        for right in ((1, 0, 0), (-1, 0, 0), (10**11, 1, 0)):
            with self.assertRaisesRegex(ValueError, 'parallel|collinear'):
                app.solve_frame(CUBIC, (1, 0, 0), right, (0, 0, 1))

    def test_top_ambiguity_boundary(self):
        for top in ((1, 1, 0), (10**9, 0, 1), (10**9, 0, -1)):
            with self.assertRaisesRegex(ValueError, 'Top direction is ambiguous'):
                app.solve_frame(CUBIC, (1, 0, 0), (0, 1, 0), top)
        for top, sign in (((10**7, 0, 1), 1), ((10**7, 0, -1), -1)):
            r = app.solve_frame(CUBIC, (1, 0, 0), (0, 1, 0), top)
            self.assertEqual(r['sign'], sign)
        # Conditioning-aware threshold rejects an otherwise above-floor margin.
        with self.assertRaisesRegex(ValueError, 'Top direction is ambiguous'):
            app.solve_frame((1, 1, 1e5, 90, 90, 90), (1, 0, 0), (0, 1, 0), (1000, 0, 1))

    def test_parse_fields(self):
        self.assertEqual(app.parse_fields(LEFT)[3], [0, 0, -1])
        for index, value in ((0, ''), (1, 'nan'), (2, 'inf'), (0, '1,2'),
                             (6, '1.0'), (7, '1e0'), (8, '9007199254740993'),
                             (12, ''), (14, 'NaN')):
            fields = list(LEFT); fields[index] = value
            with self.assertRaises(ValueError): app.parse_fields(fields)
        with self.assertRaises(ValueError): app.parse_fields([])

    def test_no_invented_top_in_example(self):
        self.assertEqual(app.EXAMPLE[-3:], ('', '', ''))
        with self.assertRaisesRegex(ValueError, 'Top hkl is required'):
            app.parse_fields(app.EXAMPLE)

    def test_report_conventions(self):
        r = app.solve_frame(*app.parse_fields(LEFT)); text = app.format_report(r)
        for expected in ('CRYSTALLOGRAPHIC ORTHOGONAL INDEXER v1.0',
                         'LEFT-HANDED', 'F cross R = -T', 'det(D) = -1',
                         'NOT a proper rotation', 'Signed Top plane hkl',
                         'Directed angular adjustments', 'Q_standard', 'v_physical = D.T @ v_xyz'):
            self.assertIn(expected, text)
        self.assertEqual(text, app.format_report(app.solve_frame(*app.parse_fields(LEFT))))


class StateTests(unittest.TestCase):
    def setUp(self): self.state = app.CalculatorState()

    def test_initial_edit_calculate_and_stale_save(self):
        self.assertFalse(self.state.fresh)
        with self.assertRaises(ValueError): self.state.save('unused.txt')
        self.state.edit(LEFT); report = self.state.calculate()
        self.assertTrue(self.state.fresh); self.assertIn('LEFT-HANDED', report)
        self.state.edit(RIGHT)
        self.assertFalse(self.state.fresh); self.assertEqual(self.state.report, '')
        with self.assertRaises(ValueError): self.state.save('unused.txt')
        self.assertIn('RIGHT-HANDED', self.state.calculate())

    def test_repeated_calculations_and_error_invalidates(self):
        self.state.edit(LEFT)
        first = self.state.calculate()
        self.assertEqual(first, self.state.calculate())
        self.state.edit(('',)*15)
        with self.assertRaises(ValueError): self.state.calculate()
        self.assertIsNone(self.state.result)
        self.assertFalse(self.state.fresh)

    def test_save_cancellation_writes_nothing(self):
        self.state.edit(LEFT); self.state.calculate(); writer = Mock()
        for path in ('', None, ()):
            self.assertFalse(self.state.save(path, writer=writer))
        writer.assert_not_called(); self.assertTrue(self.state.fresh)

    def test_atomic_save_unicode_paths_and_repeat(self):
        self.state.edit(LEFT); self.state.calculate()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'results Å space.txt'
            self.assertTrue(self.state.save(path)); self.assertEqual(path.read_text(encoding='utf-8'), self.state.report)
            self.state.edit(RIGHT); self.state.calculate(); self.state.save(path)
            self.assertIn('RIGHT-HANDED', path.read_text(encoding='utf-8'))
            self.assertEqual(len(list(Path(folder).iterdir())), 1)

    def test_failed_replace_preserves_existing_and_cleans_temp(self):
        self.state.edit(LEFT); self.state.calculate()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'existing.txt'; path.write_text('original')
            with patch.object(app.os, 'replace', side_effect=PermissionError('test access denied')):
                with self.assertRaises(PermissionError): self.state.save(path)
            self.assertEqual(path.read_text(), 'original')
            self.assertEqual(len(list(Path(folder).iterdir())), 1)
            self.assertTrue(self.state.fresh)

    def test_failed_write_missing_folder(self):
        self.state.edit(LEFT); self.state.calculate()
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(OSError): self.state.save(Path(folder)/'missing'/'report.txt')
        self.assertTrue(self.state.fresh)


class ControllerTests(unittest.TestCase):
    """Actual callbacks/StringVar traces; widget surfaces/dialogs replaced by mocks."""
    def setUp(self):
        self.interp = tk.Tcl()
        self.ui = app.IndexerApp.__new__(app.IndexerApp)
        self.ui.root = Mock()
        self.ui.state = app.CalculatorState()
        self.ui.last_directory = None; self.ui.saving = False
        self.ui.variables = [tk.StringVar(self.interp) for _ in app.FIELD_NAMES]
        self.ui.status = tk.StringVar(self.interp)
        self.ui.output = Mock(); self.ui.save_button = Mock()
        self.ui.entries = [Mock() for _ in app.FIELD_NAMES]
        for v in self.ui.variables: v.trace_add('write', self.ui.on_edit)

    def fill(self, values=LEFT):
        self.ui.set_values(values)
        self.assertTrue(self.ui.calculate())

    def test_trace_invalidates_and_disables_save(self):
        self.fill(); self.ui.variables[0].set('2')
        self.assertFalse(self.ui.state.fresh)
        self.ui.save_button.configure.assert_called_with(state='disabled')
        self.assertIn('Not calculated', self.ui.status.get())

    def test_output_readonly_after_calculate_error_edit(self):
        self.fill(); self.ui.output.configure.assert_called_with(state='disabled')
        self.ui.variables[0].set('bad'); self.assertFalse(self.ui.calculate())
        self.ui.output.configure.assert_called_with(state='disabled')
        self.assertIn('not completed', self.ui.status.get())

    def test_clear_example_and_repeat(self):
        self.fill(); self.ui.clear()
        self.assertEqual([v.get() for v in self.ui.variables], ['']*15)
        self.assertFalse(self.ui.state.fresh)
        self.ui.load_example()
        self.assertEqual([v.get() for v in self.ui.variables][-3:], ['']*3)
        self.assertFalse(self.ui.calculate())
        self.fill(RIGHT); self.fill(LEFT)

    def test_save_dialog_cancel(self):
        self.fill()
        with patch('tkinter.filedialog.asksaveasfilename', return_value='') as chooser:
            self.assertFalse(self.ui.save())
        self.assertIn('cancelled', self.ui.status.get()); self.assertFalse(self.ui.saving)
        self.assertEqual(chooser.call_args.kwargs['defaultextension'], '.txt')
        self.assertEqual(chooser.call_args.kwargs['initialfile'], 'crystallographic_indices.txt')
        self.assertTrue(self.ui.state.fresh)

    def test_save_success_then_failure(self):
        self.fill()
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder)/'report.txt')
            with patch('tkinter.filedialog.asksaveasfilename', return_value=path):
                self.assertTrue(self.ui.save()); self.assertIn('Saved TXT:', self.ui.status.get())
            self.assertEqual(Path(path).read_text(), self.ui.state.report)
            with patch('tkinter.filedialog.asksaveasfilename', return_value=folder):
                self.assertFalse(self.ui.save()); self.assertIn('Could not save:', self.ui.status.get())
            self.assertTrue(self.ui.state.fresh); self.assertFalse(self.ui.saving)

    def test_edits_during_dialog_never_save_old_result(self):
        self.fill()
        def change(**kwargs):
            self.ui.variables[0].set('5'); return 'must_not_be_written.txt'
        with patch('tkinter.filedialog.asksaveasfilename', side_effect=change), patch.object(self.ui.state, 'save') as save:
            self.assertFalse(self.ui.save())
            save.assert_not_called()
        self.assertIn('changed while', self.ui.status.get())

    def test_reentrant_and_stale_save_do_not_open_dialog(self):
        with patch('tkinter.filedialog.asksaveasfilename') as chooser:
            self.assertFalse(self.ui.save())
            self.fill(); self.ui.saving = True
            self.assertFalse(self.ui.save()); chooser.assert_not_called()


@unittest.skipUnless(os.environ.get('DISPLAY') or os.name == 'nt', 'A real Tk display is unavailable')
class NativeTkTests(unittest.TestCase):
    """Real Tk widgets, hidden by default. Visual QA requires explicit opt-in."""
    def test_build_resize_calculate_clear_close(self):
        root = tk.Tk()
        root.withdraw()
        visible = os.environ.get('COI_VISIBLE_GUI_TESTS') == '1'
        try:
            ui = app.IndexerApp(root)
            self.assertEqual(root.title(), 'Crystallographic Orthogonal Indexer 1.0')
            if visible:
                root.deiconify()
            root.update()
            ui.set_values(LEFT); self.assertTrue(ui.calculate()); root.update()
            self.assertEqual(str(ui.output.cget('state')), 'disabled')
            root.geometry('780x680'); root.update()
            if visible:
                self.assertGreater(ui.output.winfo_height(), 80)
            else:
                self.assertGreater(ui.output.winfo_reqheight(), 80)
            ui.clear(); self.assertFalse(ui.state.fresh)
            self.assertEqual(str(ui.save_button.cget('state')), 'disabled')
            # Trigger the registered window close handler, rather than bypassing it.
            root.tk.call(root.protocol('WM_DELETE_WINDOW'))
        finally:
            try: root.destroy()
            except tk.TclError: pass


if __name__ == '__main__':
    unittest.main(verbosity=2)
