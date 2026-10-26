"""Frozen entry point; ordinary launch opens the unchanged calculator UI."""
from pathlib import Path
import json
import sys
import tempfile
import traceback


def smoke_test(destination):
    """Explicit build-only smoke mode. Never run implicitly at normal startup."""
    import numpy as np
    import tkinter as tk
    import crystallographic_orthogonal_indexer as app
    result = {'application_version': app.VERSION, 'frozen': bool(getattr(sys, 'frozen', False)),
              'platform': sys.platform, 'python': sys.version, 'numpy': np.__version__,
              'native_file_dialog_tested': False, 'visual_layout_inspected': False}
    root = None
    try:
        root = tk.Tk()
        gui = app.IndexerApp(root)
        root.update()
        left = ('1','1','1','90','90','90','1','0','0','0','1','0','0','0','-1')
        gui.set_values(left)
        if not gui.calculate():
            raise RuntimeError('Frozen calculation failed')
        np.testing.assert_allclose(gui.state.result['D'], np.diag((1,1,-1)), atol=1e-12)
        if str(gui.output.cget('state')) != 'disabled':
            raise RuntimeError('Result pane is not read-only')
        with tempfile.TemporaryDirectory(prefix='coi-smoke-') as folder:
            report = Path(folder)/'Synthetic report.txt'
            gui.state.save(report)
            if 'LEFT-HANDED' not in report.read_text(encoding='utf-8'):
                raise RuntimeError('Frozen TXT save failed')
        gui.variables[0].set('2')
        if gui.state.fresh:
            raise RuntimeError('Edited result remained fresh')
        root.update()
        result['tcl'] = root.tk.call('info', 'patchlevel')
        result['tk'] = root.tk.call('package', 'require', 'Tk')
        root.tk.call(root.protocol('WM_DELETE_WINDOW'))
        root = None
        result['status'] = 'passed'
    except Exception:
        result['status'] = 'failed'
        result['error'] = traceback.format_exc()
    finally:
        if root is not None:
            try: root.destroy()
            except tk.TclError: pass
    Path(destination).write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return 0 if result['status'] == 'passed' else 1


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) == 2 and args[0] == '--smoke-test':
        return smoke_test(args[1])
    if args:
        raise SystemExit('Only the build-only --smoke-test OUTPUT.json option is supported.')
    import crystallographic_orthogonal_indexer
    crystallographic_orthogonal_indexer.main()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
