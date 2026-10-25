"""Plot complete archived activation windows; no native model or integration."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--integrator-report', type=Path,
                        help='Overlay separately versioned Radau evidence; preserve the Euler curves')
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError('plot output already exists')
    r = json.loads(args.report.read_text(encoding='utf-8'))
    if not r['evaluation']['integrity_passed']: raise ValueError('complete verified archive required')
    integrated = None
    if args.integrator_report:
        integrated = json.loads(args.integrator_report.read_text(encoding='utf-8'))
        expected = integrated['ready']['sources']['docs/evidence/lf-activation-transient-v1/run/validation.json']
        if not integrated['evaluation']['integrity_passed'] or hashlib.sha256(args.report.read_bytes()).hexdigest() != expected:
            raise ValueError('integrator requires the exact preserved Euler/reference archive')
    colors = ('#c43b36', '#d58b00', '#2477b5')
    fig, axes = plt.subplots(3, 1, figsize=(10, 12), sharex=True, constrained_layout=True)
    gain, bias = np.array(r['ready']['binding']['frozen_gain']), np.array(r['ready']['binding']['frozen_bias'])
    for dt, color in zip((1e-4, 5e-5, 2.5e-5), colors):
        for condition, panel in (('PULSE', 0), ('RELAX_ZERO', 1)):
            case = next(c for c in r['cases'] if c['dt'] == dt and c['condition'] == condition)
            a = np.vstack((case['initial']['activation'], [s['after'] for s in case['steps']]))
            if np.max(np.ptp(a, axis=1)) > 1e-12:
                raise ValueError('shared activation plot requires identical four source traces')
            times = np.arange(len(a))*dt*1000
            axes[panel].plot(times, a[:, 0], color=color, label=f'Native Euler {dt*1e6:g} us', lw=1.2)
            if integrated:
                newer = next(c for c in integrated['cases'] if c['dt'] == dt and c['condition'] == condition)
                states = np.vstack((newer['initial']['activation'], *[s['samples'] for s in newer['steps']]))
                if np.max(np.ptp(states, axis=1)) > 1e-12:
                    raise ValueError('shared plot requires identical four Radau activation traces')
                fine_times = np.arange(len(states))*.025
                axes[panel].plot(fine_times, states[:, 0], color=color, ls='--', lw=1,
                                 label=f'Radau {dt*1e6:g} us (overlaps reference)')
                if panel == 0:
                    axes[2].plot(fine_times, -(states[:, 2]*gain[2]+bias[2]), color=color, ls='--', lw=1,
                                 label=f'Radau {dt*1e6:g} us')
            if panel == 0:
                f = np.vstack((case['initial']['force'], [s['refreshed_force'] for s in case['steps']]))
                axes[2].plot(times, -f[:, 2], color=color, lw=1.2, label=f'Native Euler {dt*1e6:g} us')
            if dt == 2.5e-5:
                reference = np.asarray(case['reference_activations'])
                axes[panel].plot(times, reference[:, 0], '--', color='#191919', lw=1.6, label='DOP853 reference')
                if panel == 0:
                    axes[2].plot(times, -(reference[:, 2]*gain[2]+bias[2]), '--', color='#191919', lw=1.6, label='DOP853 force reference')
    floor = float(r['ready']['binding']['ctrlrange'][0][0])
    axes[0].axhline(floor, color='#5e8068', lw=1, ls=':', label='Floor baseline (all three grids)')
    axes[0].axhline(1, color='#777777', lw=.8, ls=':')
    axes[1].axhline(floor, color='#5e8068', lw=1, ls=':', label='Floor baseline / equilibrium')
    axes[2].axhline(-bias[2], color='#777777', lw=1, ls=':', label='Passive component')
    titles = ('Pulse: all four source activation states have identical traces',
              'Raw zero input: relaxation from activation zero',
              'Anterior rotator: total tension retains passive preload')
    for ax, title in zip(axes, titles):
        ax.set_title(title, fontsize=11, loc='left')
        ax.set_xlim(0, 10)
        ax.grid(alpha=.2)
        ax.legend(fontsize=7 if integrated else 8, loc='upper right')
    axes[0].set_ylabel('Activation')
    axes[1].set_ylabel('Activation')
    axes[1].ticklabel_format(axis='y', style='sci', scilimits=(-3, 3))
    axes[2].set_ylabel('Native force units\n(not calibrated to FlyGym/SI)')
    axes[2].set_xlabel('Time (ms); full fixed window')
    heading = 'Radau integration compared with preserved Euler failures' if integrated else 'Source-law transient validation: numerical limits retained'
    fig.suptitle(heading+'\nFixed lengths, no body/joint motion or CNS; pulse raw control 1 from 2 to 5 ms', fontsize=12)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=150)
    plt.close(fig)


if __name__ == '__main__': main()
