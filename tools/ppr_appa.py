"""PPR on Appa: CRPS per surface variable, from Tables 6-10 of Rochman-Sharabi and Louppe (NeurIPS 2026).

Usage: python tools/ppr_appa.py

Values are means over the 24 hourly timesteps of 4 test dates. Lower is better.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams.update({'font.family': 'Roboto', 'mathtext.fontset': 'cm'})

METHODS = ['PPR', 'MMPS', 'HDC', 'TS', 'CPS', 'DPS']
CRPS = {   # variable: {method: CRPS}
    '2 m temperature [K]': dict(PPR=0.693, MMPS=0.708, TS=1.564, CPS=1.675, HDC=1.385, DPS=2.165),
    '10 m U wind [m/s]': dict(PPR=0.599, MMPS=0.796, TS=1.923, CPS=2.129, HDC=2.117, DPS=2.072),
    '10 m V wind [m/s]': dict(PPR=0.594, MMPS=0.815, TS=1.907, CPS=2.114, HDC=2.159, DPS=2.006),
    'Sea level pressure [Pa]': dict(PPR=59.5, MMPS=69.8, TS=337.6, CPS=393.6, HDC=361.6, DPS=361.4),
    'Precipitation [mm]': dict(PPR=0.068, MMPS=0.075, TS=0.101, CPS=0.102, HDC=0.103, DPS=0.104),
}
BLUE, GREY, INK, MUTED = '#356aaf', '#c3c8cc', '#354046', '#6c777d'

fig, axes = plt.subplots(1, len(CRPS), figsize=(9.6, 3.8), dpi=170, sharey=True)
fig.subplots_adjust(left=0.09, right=0.99, top=0.78, bottom=0.03, wspace=0.14)
ys = range(len(METHODS))[::-1]
for ax, (var, vals) in zip(axes, CRPS.items()):
    v = [vals[m] for m in METHODS]
    ax.barh(list(ys), v, height=0.62, color=[BLUE if m == 'PPR' else GREY for m in METHODS])
    for y, x, m in zip(ys, v, METHODS):
        ax.text(x + 0.02 * max(v), y, ('%.3g' % x), va='center', fontsize=12,
                color=INK if m == 'PPR' else MUTED, weight='bold' if m == 'PPR' else 'normal')
    ax.set_xlim(0, 1.45 * max(v))
    ax.set_title(var.replace(' [', '\n['), fontsize=13, color=INK, pad=8)
    ax.set_xticks([])
    for sp in ('top', 'right', 'bottom'):
        ax.spines[sp].set_visible(False)
    ax.spines['left'].set_color(GREY)
    ax.tick_params(axis='y', length=0)
axes[0].set_yticks(list(ys))
axes[0].set_yticklabels(METHODS, fontsize=14, color=INK)
fig.text(0.09, 0.94, 'CRPS, lower is better', fontsize=13, color=MUTED, va='bottom')
fig.savefig('figures/steer/ppr-appa.png')
