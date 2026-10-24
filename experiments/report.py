"""
The paper's tables and figures from results/*.csv.

Writes docs/paper/tables/e*.tex (the tabular environments that sections/evaluation.tex
inputs), docs/paper/tables/results.tex (LaTeX macros for the numbers in the text) and
docs/paper/figures/*.pdf (matplotlib, when it is installed).
"""

from __future__ import annotations

import math
from pathlib import Path

import common  # noqa: F401  (puts the stack on sys.path)
from common.metrics import read_rows, summary

PAPER = Path(__file__).resolve().parents[1] / 'docs' / 'paper'
TABLES = PAPER / 'tables'
FIGURES = PAPER / 'figures'


def values(rows: list[dict], key: str, **where) -> list[float]:
    """Return the float column key of the rows matching every where item."""
    return [float(r[key]) for r in rows if all(r[k] == v for k, v in where.items())]


def pm(xs, digits: int = 2) -> str:
    """Return mean plus-minus std (LaTeX) of the finite values."""
    s = summary(xs)
    return f'{s["mean"]:.{digits}f} $\\pm$ {s["std"]:.{digits}f}' if s['n'] else '--'


def stat(xs, name: str, digits: int = 2) -> str:
    """Return one statistic (mean, std, median, min, max, n) of the finite values."""
    s = summary(xs)
    return '--' if not s['n'] else f'{s[name]:.{digits}f}' if name != 'n' else str(s['n'])


def tabular(spec: str, header: str, rows: list[str]) -> str:
    """Return a booktabs tabular."""
    body = '\n'.join(f'    {r} \\\\' for r in rows)
    return (f'\\begin{{tabular}}{{{spec}}}\n  \\toprule\n  {header} \\\\\n  \\midrule\n'
            f'{body}\n  \\bottomrule\n\\end{{tabular}}\n')  # fmt: skip


def e1(macros: dict) -> str:
    """Table E1 and its macros."""
    rows = read_rows('e1_stopping')
    lines = []
    for v in sorted({r['speed'] for r in rows}, key=float):
        model = values(rows, 'model_m', speed=v)[0]
        travel = values(rows, 'travel_m', speed=v)
        clear = values(rows, 'min_clearance_m', speed=v)
        lines.append(f'{float(v):.1f} & {model:.2f} & {pm(travel, 3)} & {stat(clear, "min", 3)}')
    macros['EOneRuns'] = str(len(rows))
    for letter, v in zip('ABCD', sorted({r['speed'] for r in rows}, key=float), strict=True):
        macros[f'EOneMeasured{letter}'] = stat(values(rows, 'travel_m', speed=v), 'mean', 2)
        macros[f'EOneModel{letter}'] = f'{values(rows, "model_m", speed=v)[0]:.2f}'
    speeds = {r['speed'] for r in rows}
    spread = [summary(values(rows, 'travel_m', speed=v))['std'] for v in speeds]
    macros['EOneStdMax'] = f'{max(spread):.3f}'
    macros['EOneClearMin'] = stat(values(rows, 'min_clearance_m'), 'min', 3)
    macros['EOneReactMin'] = stat(values(rows, 'reaction_sec'), 'min', 2)
    macros['EOneReactMax'] = stat(values(rows, 'reaction_sec'), 'max', 2)
    macros['EOneCollisions'] = str(sum(r['collided'] == 'True' for r in rows))
    ratio = [float(r['travel_m']) / float(r['model_m']) for r in rows]
    macros['EOneRatioMax'] = f'{max(ratio):.2f}'
    return tabular('@{}rrrr@{}', '$v$ (m/s) & $D(v)$ (m) & measured (m) & clearance (m)', lines)


def e2(macros: dict) -> str:
    """Table E2 and its macros."""
    rows = read_rows('e2_blind')
    lines = []
    for kind in ('silent', 'empty', 'sparse'):
        for version in ('v0.2', 'v0.1'):
            auto = {'kind': kind, 'mode': 'auto', 'version': version}
            remote = {'kind': kind, 'mode': 'remote', 'version': version}
            zero = values(rows, 'zero_after_sec', **auto)
            never = all(math.isinf(z) for z in zero)
            t0 = 'never' if never else pm(zero, 2)
            dist = values(rows, 'distance_m', **auto)
            d = f'$\\ge${stat(dist, "min", 1)}' if never else pm(dist, 2)
            creep = stat(values(rows, 'creep_mps', **remote), 'max', 2)
            lines.append(f'{kind} & {version} & {t0} & {d} & {creep}')
    macros['ETwoRuns'] = str(len(rows))
    blind = [r for r in rows if r['kind'] in ('empty', 'sparse') and r['version'] == 'v0.2']
    auto = [r for r in blind if r['mode'] == 'auto']
    macros['ETwoBlindZeroMax'] = stat([float(r['zero_after_sec']) for r in auto], 'max', 2)
    macros['ETwoBlindDistanceMax'] = stat([float(r['distance_m']) for r in auto], 'max', 2)
    silent = [float(r['zero_after_sec']) for r in rows if r['kind'] == 'silent'
              and r['mode'] == 'auto']  # fmt: skip
    macros['ETwoSilentZeroMax'] = stat(silent, 'max', 2)
    creep = [float(r['creep_mps']) for r in rows
             if r['mode'] == 'remote' and r['version'] == 'v0.2']  # fmt: skip
    macros['ETwoCreepMax'] = stat(creep, 'max', 2)
    return tabular('@{}llrrr@{}', 'LiDAR & stack & $t_0$ (s) & $d$ (m) & creep (m/s)', lines)


def e3(macros: dict) -> str:
    """Table E3 and its macros."""
    rows = read_rows('e3_localization')
    names = {'hard_replace': 'Hard replace (v0.1)', 'ekf_tags': 'EKF, tags',
             'ekf_tags_scan': 'EKF, tags + scan match'}  # fmt: skip
    lines = []
    for method, label in names.items():
        w = {'method': method}
        lines.append(f'{label} & {pm(values(rows, "ate_m", **w), 3)} & '
                     f'{pm(values(rows, "max_m", **w), 2)} & '
                     f'{pm(values(rows, "yaw_rmse_deg", **w), 2)}')  # fmt: skip
        key = ''.join(p.capitalize() for p in method.split('_'))
        for kind in ('inliers', 'outliers'):
            seen = sum(values(rows, kind, **w))
            rejected = sum(values(rows, f'{kind}_rejected', **w))
            macros[f'EThree{key}{kind.capitalize()}Rejected'] = f'{100.0 * rejected / seen:.0f}'
            accepted = 100.0 * (seen - rejected) / seen
            macros[f'EThree{key}{kind.capitalize()}Accepted'] = f'{accepted:.0f}'
            macros[f'EThree{key}{kind.capitalize()}'] = f'{seen:.0f}'
        macros[f'EThree{key}WorstMax'] = stat(values(rows, 'max_m', **w), 'max', 2)
    matches = values(rows, 'scan_matches', method='ekf_tags_scan')
    rejected = values(rows, 'scan_rejected', method='ekf_tags_scan')
    macros['EThreeScanRejected'] = f'{100.0 * sum(rejected) / max(sum(matches), 1):.1f}'
    macros['EThreeDistance'] = stat(values(rows, 'distance_m', method='ekf_tags'), 'mean', 0)
    macros['EThreeRuns'] = str(len(values(rows, 'ate_m', method='ekf_tags')))
    return tabular('@{}lrrr@{}', 'Method & ATE (m) & max (m) & yaw (°)', lines)


def e4(macros: dict) -> str:
    """Table E4 and its macros."""
    rows = read_rows('e4_path_shift')
    labels = {'path_shift': 'path shift', 'reactive': 'reactive', 'off': 'none'}
    lines = []
    for layout, name in (('on_route', 'on'), ('beside_route', 'beside')):
        for mode, label in labels.items():
            w = {'layout': layout, 'mode': mode}
            done = [r for r in rows if r['layout'] == layout and r['mode'] == mode]
            ok = sum(r['completed'] == 'True' for r in done)
            time = pm(values(rows, 'time_sec', **w), 1) if ok else '--'
            lines.append(
                f'{name} & {label} & {ok}/{len(done)} & {time} & '
                f'{pm(values(rows, "stops", completed="True", **w), 1) if ok else "--"} & '
                f'{clearance(values(rows, "min_clearance_m", **w))} & '
                f'{stat(values(rows, "max_offset_m", **w), "max", 2)}'
            )
    macros['EFourCollisions'] = str(sum(r['collided'] == 'True' for r in rows))
    macros['EFourRuns'] = str(len(rows))
    return tabular('@{}llrrrrr@{}', 'people & avoidance & done & time (s) & stops & '
                   'clear. (m) & offset (m)', lines)  # fmt: skip


def clearance(xs) -> str:
    """Return the smallest clearance (m), 'contact' when a person touched the body."""
    smallest = min(xs)
    return 'contact' if smallest <= 0.0 else f'{smallest:.2f}'


def write(name: str, text: str):
    """Write a generated file under docs/paper/tables."""
    TABLES.mkdir(parents=True, exist_ok=True)
    header = '% Generated by experiments/report.py from experiments/results; do not edit.\n'
    (TABLES / name).write_text(header + text, encoding='utf-8')


def main():
    """Write every table, the macros and (with matplotlib) the figures."""
    macros: dict[str, str] = {}
    for name, make in (('e1', e1), ('e2', e2), ('e3', e3), ('e4', e4)):
        write(f'{name}.tex', make(macros))
    write('results.tex', ''.join(f'\\newcommand{{\\{k}}}{{{v}}}\n' for k, v in macros.items()))
    try:
        import plots
    except ImportError:
        return
    plots.main(FIGURES)


if __name__ == '__main__':
    main()
