#!/usr/bin/env python3
"""Crystallographic Orthogonal Indexer v1.0: signed plane-normal calculator.

All hkl inputs are signed Miller PLANE indices, not direct-lattice directions.
Core reciprocal conversion and Front-first Gram-Schmidt functions are retained
from the independently developed v1.1 module. No XYZ or previous package needed.
Run: python main.py
"""
from __future__ import annotations

import math
from decimal import Decimal
import os
from pathlib import Path
import re
import tempfile

import numpy as np

PRODUCT_NAME = "Crystallographic Orthogonal Indexer"
VERSION = "1.0"
NAMES = ("Front", "Right", "Top")
CELL_NAMES = ("a", "b", "c", "alpha", "beta", "gamma")
FIELD_NAMES = CELL_NAMES + tuple(f"{name} {i}" for name in NAMES for i in "hkl")
TOP_DOT_FLOOR = 1e-8
EXAMPLE = ("15.0100", "17.6472", "16.2603", "90", "101.633", "90",
           "2", "5", "3", "3", "-5", "4", "", "", "")

def vector3(value, name="vector"):
    """Return an independent, finite three-vector or raise ValueError."""
    try:
        v = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite three-vector") from exc
    if v.shape != (3,) or not np.isfinite(v).all():
        raise ValueError(f"{name} must be a finite three-vector")
    return v.copy()

def unit(value):
    v = vector3(value)
    scale = np.max(np.abs(v))
    if scale == 0:
        raise ValueError("zero vector has no direction")
    return (v / scale) / np.linalg.norm(v / scale)

def angle_deg(first, second):
    """Directed-vector angle in [0,180], NOT an unsigned line/axis angle."""
    a, b = unit(first), unit(second)
    return float(np.degrees(np.arctan2(np.linalg.norm(np.cross(a, b)), a @ b)))

def cell_matrix(cell):
    """A=[a b c], columns in ab'c*, for a valid (a,b,c,alpha,beta,gamma).

    Positive Cholesky factors fix the right-handed Cartesian convention without
    sign choices. Numerically singular cells (condition number > 1e12, or
    normalized metric eigenvalue <= 64*machine epsilon*largest eigenvalue) fail.
    No crystal symmetry or setting transformation is inferred from the cell.
    """
    p = np.asarray(cell, dtype=float)
    if p.shape != (6,) or not np.isfinite(p).all():
        raise ValueError("cell needs six finite values")
    lengths, angles = p[:3], p[3:]
    if np.any(lengths <= 0) or np.any(angles <= 0) or np.any(angles >= 180):
        raise ValueError("lengths must be positive; angles strictly between 0 and 180 degrees")
    ca, cb, cg = np.cos(np.radians(angles))
    metric_unit = np.array([[1, cg, cb], [cg, 1, ca], [cb, ca, 1]])
    eigenvalues = np.linalg.eigvalsh(metric_unit)
    if eigenvalues[0] <= 64*np.finfo(float).eps*eigenvalues[-1]:
        raise ValueError("cell angle metric is invalid or numerically degenerate")
    try:
        A = np.linalg.cholesky(metric_unit).T @ np.diag(lengths)
    except np.linalg.LinAlgError as exc:
        raise ValueError("cell angle metric is not positive definite") from exc
    if not np.isfinite(A).all() or np.linalg.cond(A) > 1e12:
        raise ValueError("cell is numerically singular/ill-conditioned (condition > 1e12)")
    return A

def signed_plane_normal(A, hkl):
    """Crystallographic reciprocal normal, in inverse angstrom (no 2*pi)."""
    # Preserve original integer/exact-number values until validation is complete.
    try:
        original = np.asarray(hkl, dtype=object)
        if original.shape != (3,):
            raise ValueError("hkl must be a three-vector")
        exact = [Decimal(value) if isinstance(value, str) else value for value in original]
        integers = [int(value) for value in exact]
        valid = all(value == integer and abs(integer) <= 2**53
                    for value, integer in zip(exact, integers))
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise ValueError("hkl must contain exactly representable signed integers") from exc
    if not valid:
        raise ValueError("hkl must contain exactly representable signed integers")
    h = np.asarray(integers, dtype=float)
    if not np.any(h):
        raise ValueError("(0,0,0) does not define a plane normal")
    A = np.asarray(A, dtype=float)
    if A.shape != (3, 3) or not np.isfinite(A).all():
        raise ValueError("A must be a finite 3x3 direct-cell matrix")
    if np.linalg.det(A) <= 0 or np.linalg.cond(A) > 1e12:
        raise ValueError("A must be nonsingular and right-handed")
    n = np.linalg.solve(A.T, h)
    if not np.isfinite(n).all():
        raise ValueError("normal is outside floating-point range")
    return n

def front_preserving_frame(front, right):
    """Front-first Gram-Schmidt: Q=[F R T], R nearest perpendicular to F.

    R = (r - (F.r)F)/|r - (F.r)F|; T = F x R. The positive denominator is
    normalization, not a discretionary sign selection. Parallel/antiparallel
    inputs have no unique R and are rejected (sin(angle) <= 1e-10).
    """
    F, r = unit(front), unit(right)
    residual = r - (F @ r) * F
    norm = np.linalg.norm(residual)
    if norm <= 1e-10:
        raise ValueError("Front/Right are parallel or numerically near-collinear")
    R = residual / norm
    T = unit(np.cross(F, R))
    return np.column_stack((F, R, T))


def parse_fields(values):
    """Parse all 15 entries. Miller indices must be signed integer strings."""
    if len(values) != 15:
        raise ValueError("Enter six cell parameters and all three hkl triples.")
    parsed = []
    for index, (label, value) in enumerate(zip(FIELD_NAMES, values)):
        value = str(value).strip()
        if not value:
            raise ValueError(f"Enter {label}. Top hkl is required; it is never guessed.")
        if index >= 6:
            if not re.fullmatch(r"[+-]?[0-9]+", value):
                raise ValueError(f"{label}: enter a signed integer, for example -3.")
            # Bound before conversion to avoid enormous-input integer parsing.
            if len(value.lstrip('+-').lstrip('0')) > 16:
                raise ValueError(f"{label}: magnitude must not exceed 2^53.")
            number = int(value)
            if abs(number) > 2**53:
                raise ValueError(f"{label}: magnitude must not exceed 2^53.")
        else:
            try:
                number = float(value)
            except ValueError as exc:
                raise ValueError(f"{label}: enter a number using a decimal point.") from exc
            if not math.isfinite(number):
                raise ValueError(f"{label}: the value must be finite.")
        parsed.append(number)
    return parsed[:6], parsed[6:9], parsed[9:12], parsed[12:15]


def solve_frame(cell, front, right, top):
    """Preserve F, orthogonalize R, then choose Top using its signed reference.

    t is the converted, normalized user Top. Let u = F cross R. T = sign(t.u)u.
    Reject |t.u| <= max(1e-8, 128*eps*cond(A)/sin(angle(F_raw,R_raw))).
    The floor is dimensionless (~5.73e-7 degrees from the F/R plane). The
    conditioning term conservatively rejects numerically unstable sign choices;
    neither is an estimate of experimental indexing or angular uncertainty.
    """
    try:
        with np.errstate(over="raise", divide="raise", invalid="raise"):
            A = cell_matrix(cell)
            normals = []
            for name, h in zip(NAMES, (front, right, top)):
                try:
                    normals.append(signed_plane_normal(A, h))
                except ValueError as exc:
                    raise ValueError(f"{name}: {exc}") from exc
            raw = np.column_stack(normals)
            raw_unit = np.column_stack([unit(n) for n in normals])
            Q = front_preserving_frame(raw[:, 0], raw[:, 1])
            separation = np.linalg.norm(np.cross(raw_unit[:, 0], raw_unit[:, 1]))
            tolerance = max(TOP_DOT_FLOOR,
                            128*np.finfo(float).eps*np.linalg.cond(A)/separation)
            top_dot = float(raw_unit[:, 2] @ Q[:, 2])
            if abs(top_dot) <= tolerance:
                raise ValueError(
                    "Top direction is ambiguous: its signed normal is in, or too "
                    "close to, the Front/Right plane for a reliable sign choice. "
                    f"|Top dot (F cross R)|={abs(top_dot):.3g}; required > {tolerance:.3g}. "
                    "Enter an independently known Top plane normal out of that plane.")
            sign = 1 if top_dot > 0 else -1
            D = Q.copy()
            D[:, 2] *= sign
            error = float(np.max(np.abs(D.T @ D - np.eye(3))))
            if error > 1e-8:
                raise ValueError("Front/Right are too ill-conditioned for a reliable frame.")
            B = np.linalg.inv(A).T
            if not np.isfinite(raw).all() or not np.isfinite(B).all():
                raise ValueError("Values exceed the supported floating-point range.")
            return {
                "version": VERSION, "cell": list(cell),
                "hkl": [list(h) for h in (front, right, top)],
                "A": A, "B": B, "raw": raw, "raw_unit": raw_unit,
                "Q_standard": Q, "D": D, "sign": sign,
                "top_dot": top_dot, "top_tolerance": tolerance,
                "adjustments": [angle_deg(raw_unit[:, j], D[:, j]) for j in range(3)],
                "raw_angles": [angle_deg(raw_unit[:, i], raw_unit[:, j])
                               for i, j in ((0, 1), (0, 2), (1, 2))],
                "norms": np.linalg.norm(D, axis=0),
                "dots": [float(D[:, i] @ D[:, j]) for i, j in ((0, 1), (0, 2), (1, 2))],
                "det": float(np.linalg.det(D)), "orthogonality_error": error,
                "duality_error": float(np.max(np.abs(A.T @ B-np.eye(3)))),
            }
    except (FloatingPointError, np.linalg.LinAlgError, OverflowError) as exc:
        raise ValueError("Cell/indices exceed stable numerical limits; check their scale and geometry.") from exc


def format_report(data):
    """Deterministic UTF-8 report; every vector is a horizontal row."""
    def row(v):
        return "[" + "  ".join(f"{x: .12g}" for x in v) + "]"

    left = data["sign"] < 0
    handed = "LEFT-HANDED" if left else "RIGHT-HANDED"
    relation = "F cross R = -T" if left else "F cross R = T"
    lines = [f"{PRODUCT_NAME.upper()} v{VERSION}",
             f"FINAL PHYSICAL LABELS: {handed}; {relation}",
             f"det(D) = {data['det']:.12g}", "",
             "FINAL UNIT VECTORS -- Cartesian ab'c*, horizontal (x,y,z)"]
    for j, name in enumerate(NAMES):
        lines.append(f"{name:5s}: {row(data['D'][:, j])}")
    lines += ["", "INPUTS",
              "Cell [a,b,c / angstrom; alpha,beta,gamma / degrees]: [" +
              "  ".join(format(float(x), ".17g") for x in data["cell"]) + "]"]
    for name, h in zip(NAMES, data["hkl"]):
        lines.append(f"Signed {name} plane hkl: [" + "  ".join(str(int(x)) for x in h) + "]")
    lines += ["", "METHOD / PREMISES",
              "hkl are signed Miller plane indices, not direct-lattice directions.",
              "Cell angles: alpha = angle(b,c), beta = angle(a,c), gamma = angle(a,b).",
              "x parallel +a; y parallel +b minus projection on a (b'); z parallel a cross b (c*).",
              "A has direct-cell vectors as columns: Cartesian position = A @ fractional position.",
              "B = inv(A).T; signed reciprocal normal = B @ hkl (no 2*pi).",
              "Front-first Gram-Schmidt: F = unit(nFront);",
              "R = unit(unit(nRight) - dot(unit(nRight),F)*F); U = F cross R.",
              "T = sign(dot(unit(nTop),U))*U. Only Top's hemisphere selects its final sign.",
              "Front is preserved; Right and Top are explicitly adjusted to orthogonality.",
              "No axis swapping, automatic handedness enforcement, camera or molecule transformation.",
              "Molecular comparison requires matching indexing conventions and Cartesian ab'c* coordinates.",
              "This calculation does not independently establish physical orientation or a magnetic easy axis.",
              "", "ORIGINAL SIGNED NORMALS -- preserved, not orthogonalized"]
    for j, name in enumerate(NAMES):
        lines += [f"{name} reciprocal normal / inverse angstrom: {row(data['raw'][:, j])}",
                  f"{name} normalized original: {row(data['raw_unit'][:, j])}"]
    lines += ["Raw directed mutual angles [F-R, F-T, R-T] / degrees: " + row(data["raw_angles"]),
              "Directed angular adjustments [Front, Right, Top] / degrees: " + row(data["adjustments"]),
              f"Signed Top-reference dot U: {data['top_dot']:.12g}",
              f"Top ambiguity rejection threshold: |dot| <= {data['top_tolerance']:.12g}",
              "Threshold = max(1e-8, 128*machine_epsilon*cond(A)/sin(raw F-R angle)).",
              "This is a numerical stability guard, not an experimental uncertainty estimate.",
              "", "COMPONENT MAPS (column-vector convention)",
              "D columns = final F,R,T. v_xyz = D @ v_physical; v_physical = D.T @ v_xyz.",
              "For a point relative to origin p0: p_xyz = p0 + D @ p_physical."]
    if left:
        lines += ["WARNING: D is an improper orthogonal map, NOT a proper rotation.",
                  "Do NOT use this left-handed D as an EasySpin Euler/rotation frame."]
    else:
        lines += ["D is a proper right-handed orthogonal basis; EasySpin transform sense must still be respected."]
    for name, matrix in (("A (direct-cell columns / angstrom)", data["A"]),
                         ("B (reciprocal-cell columns / inverse angstrom)", data["B"]),
                         ("D (FINAL physical basis columns F,R,T)", data["D"]),
                         ("D.T (XYZ components to FINAL physical components)", data["D"].T)):
        lines += ["", name] + [row(v) for v in matrix]
    lines += ["", "SEPARATE RIGHT-HANDED COMPUTATIONAL REFERENCE",
              "Q_standard = [F,R,U], U = F cross R; det(Q_standard) = +1.",
              "This reference does NOT relabel physical Top when the final frame is left-handed.",
              "v_xyz = Q_standard @ v_standard; v_standard = Q_standard.T @ v_xyz."]
    lines += [row(v) for v in data["Q_standard"]]
    lines += ["", "VALIDATION",
              "Final column norms [F,R,T]: " + row(data["norms"]),
              "Final dot products [F.R,F.T,R.T]: " + row(data["dots"]),
              f"det(D): {data['det']:.12g}; {relation}",
              f"max abs(D.T @ D - I): {data['orthogonality_error']:.6e}",
              f"max abs(A.T @ B - I): {data['duality_error']:.6e}",
              "Numbers are computed in float64; printed precision is not experimental accuracy.", ""]
    return "\n".join(lines)


def atomic_write_text(path, text):
    """Write beside destination, then replace atomically; leave originals on failure."""
    target = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=target.parent, prefix=".coi-",
                                         suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class CalculatorState:
    """UI-independent freshness and save rules, also tested without a display."""
    def __init__(self):
        self.values = ("",) * 15
        self.calculated_values = None
        self.result = None
        self.report = ""

    def edit(self, values):
        self.values = tuple(str(x) for x in values)
        self.calculated_values = None
        self.result = None
        self.report = ""

    @property
    def fresh(self):
        return self.calculated_values == self.values and self.result is not None

    def calculate(self):
        self.calculated_values = None
        self.result = None
        self.report = ""
        self.result = solve_frame(*parse_fields(self.values))
        self.report = format_report(self.result)
        self.calculated_values = self.values
        return self.report

    def save(self, path, writer=atomic_write_text):
        if not self.fresh:
            raise ValueError("Inputs changed or no result exists. Click Calculate before saving.")
        if not path:
            return False
        writer(path, self.report)
        return True


class IndexerApp:
    """Conventional Tk desktop form. No filesystem writes except explicit Save TXT."""
    def __init__(self, root):
        import tkinter as tk
        from tkinter import ttk
        self.root = root
        self.state = CalculatorState()
        self.last_directory = None
        self.saving = False
        root.title(f"{PRODUCT_NAME} {VERSION}")
        width = min(1020, max(780, root.winfo_screenwidth()-80))
        height = min(800, max(680, root.winfo_screenheight()-100))
        root.geometry(f"{width}x{height}")
        root.minsize(780, 680)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        outer = ttk.Frame(root, padding=16)
        outer.grid(sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(5, weight=1)
        ttk.Label(outer, text=PRODUCT_NAME, font=("", 18, "bold")).grid(sticky="w")
        ttk.Label(outer, text="Signed plane normals → orthogonal physical axes → save a TXT report.").grid(sticky="w", pady=(2, 12))
        inputs = ttk.Frame(outer)
        inputs.grid(row=2, sticky="ew")
        inputs.columnconfigure(0, weight=1)
        inputs.columnconfigure(1, weight=1)
        self.variables = [tk.StringVar(root) for _ in FIELD_NAMES]
        self.entries = []
        cellbox = ttk.LabelFrame(inputs, text="1 · Unit cell", padding=10)
        cellbox.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        for j, name in enumerate(CELL_NAMES):
            rowindex, column = divmod(j, 3)
            ttk.Label(cellbox, text=name + (" (Å)" if j < 3 else " (°)")).grid(row=2*rowindex, column=column, sticky="w", padx=4)
            entry = ttk.Entry(cellbox, textvariable=self.variables[j], width=12)
            entry.grid(row=2*rowindex+1, column=column, sticky="ew", padx=4, pady=(2, 7))
            cellbox.columnconfigure(column, weight=1)
            self.entries.append(entry)
        axesbox = ttk.LabelFrame(inputs, text="2 · Signed Miller plane indices", padding=10)
        axesbox.grid(row=0, column=1, sticky="nsew")
        for j, text in enumerate(("", "h", "k", "l")):
            ttk.Label(axesbox, text=text).grid(row=0, column=j)
        for rowindex, name in enumerate(NAMES, 1):
            ttk.Label(axesbox, text=name).grid(row=rowindex, column=0, sticky="w", padx=(0, 8))
            for j in range(3):
                index = 6 + 3*(rowindex-1) + j
                entry = ttk.Entry(axesbox, textvariable=self.variables[index], width=9)
                entry.grid(row=rowindex, column=j+1, padx=3, pady=3, sticky="ew")
                axesbox.columnconfigure(j+1, weight=1)
                self.entries.append(entry)
        self.note = ttk.Label(outer, text="Front is preserved; Right is orthogonalized. Your Top hkl selects Top's sense.\nTop is required. Left-handed physical labels are allowed and clearly reported.", wraplength=930)
        self.note.grid(row=3, sticky="ew", pady=(10, 8))
        buttons = ttk.Frame(outer)
        buttons.grid(row=4, sticky="ew", pady=(0, 10))
        self.calculate_button = ttk.Button(buttons, text="Calculate", command=self.calculate)
        self.calculate_button.pack(side="left")
        self.save_button = ttk.Button(buttons, text="Save TXT…", command=self.save, state="disabled")
        self.save_button.pack(side="left", padx=8)
        ttk.Button(buttons, text="Load cell + F/R example", command=self.load_example).pack(side="left", padx=(16, 8))
        ttk.Button(buttons, text="Clear", command=self.clear).pack(side="left")
        results = ttk.LabelFrame(outer, text="3 · Results (read-only, selectable text)", padding=8)
        results.grid(row=5, sticky="nsew")
        results.rowconfigure(0, weight=1)
        results.columnconfigure(0, weight=1)
        self.output = tk.Text(results, wrap="none", font=("Courier", 10), height=18,
                              state="disabled", takefocus=True, padx=8, pady=6)
        self.output.grid(row=0, column=0, sticky="nsew")
        ybar = ttk.Scrollbar(results, orient="vertical", command=self.output.yview)
        ybar.grid(row=0, column=1, sticky="ns")
        xbar = ttk.Scrollbar(results, orient="horizontal", command=self.output.xview)
        xbar.grid(row=1, column=0, sticky="ew")
        self.output.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        self.status = tk.StringVar(root, "Enter all inputs, then click Calculate. Nothing is saved automatically.")
        self.status_label = ttk.Label(outer, textvariable=self.status, wraplength=930)
        self.status_label.grid(row=6, sticky="ew", pady=(8, 0))
        self.replace_output("Enter your unit cell and all three signed hkl triples.\n\nThe example button leaves Top blank: no experimental Top is invented.")
        for variable in self.variables:
            variable.trace_add("write", self.on_edit)
        root.bind("<Control-Return>", lambda event: self.calculate())
        root.bind("<Control-s>", lambda event: self.save())
        root.bind("<Configure>", self.on_resize)
        root.protocol("WM_DELETE_WINDOW", root.destroy)
        self.entries[0].focus_set()

    def on_resize(self, event):
        if event.widget == self.root:
            width = max(600, event.width-40)
            self.note.configure(wraplength=width)
            self.status_label.configure(wraplength=width)

    def replace_output(self, text):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def on_edit(self, *_):
        self.state.edit([v.get() for v in self.variables])
        self.save_button.configure(state="disabled")
        self.replace_output("Inputs changed. Click Calculate to generate a current result.")
        self.status.set("Not calculated for these inputs. Save TXT is disabled.")

    def calculate(self):
        try:
            report = self.state.calculate()
        except ValueError as exc:
            self.save_button.configure(state="disabled")
            self.replace_output("Please check the inputs:\n\n" + str(exc))
            self.status.set("Calculation not completed. Correct the input and try again.")
            return False
        self.replace_output(report)
        self.save_button.configure(state="normal")
        handed = "LEFT-HANDED (not an EasySpin rotation frame)" if self.state.result["sign"] < 0 else "RIGHT-HANDED"
        self.status.set(f"Calculated: {handed}. Ready to save TXT to your chosen folder.")
        return True

    def set_values(self, values):
        for variable, value in zip(self.variables, values):
            variable.set(str(value))

    def load_example(self):
        self.set_values(EXAMPLE)
        self.entries[12].focus_set()
        self.status.set("Example cell + Front/Right loaded. Enter your actual signed Top hkl; it is not inferred.")

    def clear(self):
        self.set_values(("",)*15)
        self.entries[0].focus_set()
        self.status.set("Inputs cleared. No files were changed.")

    def save(self):
        from tkinter import filedialog
        if self.saving:
            return False
        if not self.state.fresh:
            self.status.set("Click Calculate for the current inputs before saving.")
            return False
        self.saving = True
        snapshot = self.state.calculated_values
        try:
            options = dict(parent=self.root, title="Save Crystallographic Orthogonal Indexer TXT report",
                           defaultextension=".txt", initialfile="crystallographic_indices.txt",
                           confirmoverwrite=True,
                           filetypes=[("Text report", "*.txt"), ("All files", "*")])
            if self.last_directory:
                options["initialdir"] = self.last_directory
            path = filedialog.asksaveasfilename(**options)
            if not path:
                self.status.set("Save cancelled. No file was written.")
                return False
            # Tk dialogs run a nested event loop. Recheck freshness after return.
            if not self.state.fresh or self.state.calculated_values != snapshot:
                self.status.set("Inputs changed while choosing the file. Calculate again before saving.")
                return False
            self.state.save(path)
            self.last_directory = str(Path(path).parent)
            self.status.set(f"Saved TXT: {path}")
            return True
        except (OSError, ValueError) as exc:
            self.status.set(f"Could not save: {exc}. Choose another writable folder or filename.")
            return False
        finally:
            self.saving = False


def main():
    import tkinter as tk
    root = tk.Tk()
    IndexerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

