"""One step of the reverse process, Euler-Maruyama vs ancestral sampling, in 1D.

Usage: python tools/step1d.py

Same picture as the reverse diffusion animation of slide 13: a two-mode density,
diffused by a variance-exploding process, x_t = x + sigma_t eps. All quantities are
exact: the density p_t, the score, and the denoiser E[x | x_t]. One step goes from
time t to time s. Euler-Maruyama moves x_t along the score directly; ancestral
sampling goes through the denoised x_hat, drawn at t = 0, then renoises to s.
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

plt.rcParams.update({'font.family': 'Roboto', 'mathtext.fontset': 'cm'})

MU, S0, W = np.array([-1.5, 1.5]), 0.2, np.array([0.5, 0.5])   # prior: two narrow modes
SMIN, SMAX = 0.02, 4.0
sigma = lambda t: SMIN * (SMAX / SMIN) ** t                      # VE noise schedule
T, S = 0.85, 0.55                                                 # one step, from t down to s
X_T = 3.6                                                         # the current noisy state
dmap = LinearSegmentedColormap.from_list('bluered', ['#14213d', '#2f4b9a', '#7a5aa6', '#c8506a', '#f08a5d'])


def density(x, t):
    v = S0**2 + sigma(t)**2
    return sum(w * np.exp(-0.5 * (x - m)**2 / v) / np.sqrt(v) for m, w in zip(MU, W))


def denoise(x, t):
    s2 = sigma(t)**2
    v = S0**2 + s2
    r = np.array([w * np.exp(-0.5 * (x - m)**2 / v) for m, w in zip(MU, W)])
    r = r / r.sum(0)
    return (r * np.array([(m * s2 + x * S0**2) / v for m in MU])).sum(0)


st, ss = sigma(T), sigma(S)
xhat = denoise(X_T, T)
score = (xhat - X_T) / st**2
mean = X_T + (st**2 - ss**2) * score                       # same for both
sd_euler = np.sqrt(st**2 - ss**2)
sd_anc = np.sqrt(ss**2 - ss**4 / st**2)
rng = np.random.default_rng(2)
z = rng.normal()
x_euler, x_anc = mean + sd_euler * z, mean + sd_anc * z

grid = np.linspace(-5, 5, 300)
X0, X1 = -0.06, 1.0
tt = np.linspace(X0, X1, 300)
dens = np.stack([density(grid, min(max(t, 0), 1)) for t in tt], 1)
fig, axes = plt.subplots(1, 2, figsize=(9.6, 2.5), dpi=170)
fig.subplots_adjust(left=0.005, right=0.995, top=0.86, bottom=0.01, wspace=0.03)
W_ = dict(color='white', lw=2.2)
for ax, title in zip(axes, ['Euler–Maruyama', 'ancestral sampling']):
    ax.imshow(dens / dens.max(0, keepdims=True), extent=[X0, X1, -5, 5], aspect='auto', origin='lower', cmap=dmap)
    ax.axvline(T, color='white', lw=0.8, ls=':', alpha=0.6)
    ax.axvline(S, color='white', lw=0.8, ls=':', alpha=0.6)
    ax.text(T, -4.7, '$t$', color='white', fontsize=16, ha='center', va='bottom')
    ax.text(S, -4.7, '$s$', color='white', fontsize=16, ha='center', va='bottom')
    ax.set_title(title, fontsize=15, color='#354046')
    ax.set_xlim(X0, X1); ax.set_ylim(-5, 5); ax.axis('off')
    ax.plot(T, X_T, 'o', color='white', ms=10, zorder=5)
    ax.text(T + 0.03, X_T, '$x_t$', color='white', fontsize=18, va='center')

# Euler-Maruyama: straight to x_s
a = axes[0]
a.annotate('', xy=(S, x_euler), xytext=(T, X_T), arrowprops=dict(arrowstyle='->', shrinkA=7, shrinkB=7, **W_))
a.plot(S, x_euler, 'o', color='white', ms=10, zorder=5)
a.text(S - 0.03, x_euler, '$x_s$', color='white', fontsize=18, ha='right', va='center')

# ancestral: denoise to x_hat at t = 0, then renoise to x_s
a = axes[1]
a.annotate('', xy=(0, xhat), xytext=(T, X_T),
           arrowprops=dict(arrowstyle='->', shrinkA=7, shrinkB=7, ls=(0, (3, 3)), color='white', lw=1.8))
a.annotate('', xy=(S, x_anc), xytext=(0, xhat), arrowprops=dict(arrowstyle='->', shrinkA=7, shrinkB=7, **W_))
a.plot(0, xhat, 'o', mfc='none', mec='white', ms=12, mew=2, zorder=5)
a.plot(S, x_anc, 'o', color='white', ms=10, zorder=5)
a.text(0.03, xhat - 0.45, r'$\hat{x}$', color='white', fontsize=18, va='top')
a.text(S + 0.03, x_anc - 0.35, '$x_s$', color='white', fontsize=18, va='top')
a.text(0.45, 0.5 * (xhat + X_T) + 0.35, 'denoise', color='white', fontsize=13, ha='center', va='bottom')
a.text(0.27, 0.5 * (xhat + x_anc) - 0.3, 'renoise', color='white', fontsize=13, ha='center', va='top')
fig.savefig('figures/steer/step.png')
print('x_hat %.2f, mean %.2f, x_euler %.2f, x_anc %.2f' % (xhat, mean, x_euler, x_anc))
