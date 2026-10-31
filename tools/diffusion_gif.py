"""Forward and reverse diffusion GIFs (slides 12 and 13), after Song (2021).

Usage: python tools/diffusion_gif.py

Same convention as the slides (EDM, f_t = 0): x_t = x + sigma_t eps, with the noise
schedule and colours of tools/step1d.py. Left, the Kolmogorov flow of slide 3, noised;
right, a two-mode 1D density p_t over time, with a few sample paths. The reverse GIF
plays forward paths backwards, which is a valid sample of the reverse process.
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image

plt.rcParams.update({'font.family': 'Roboto', 'mathtext.fontset': 'cm'})
rng = np.random.default_rng(1)

MU, S0, W = np.array([-1.5, 1.5]), 0.2, np.array([0.5, 0.5])   # as in tools/step1d.py
SMIN, SMAX = 0.02, 4.0
sigma = lambda t: SMIN * (SMAX / SMIN) ** t
dmap = LinearSegmentedColormap.from_list('bluered', ['#14213d', '#2f4b9a', '#7a5aa6', '#c8506a', '#f08a5d'])
K, T = 100, 128                      # frames, image tile size

ts = np.linspace(0, 1, K + 1)
sig = sigma(ts)
# image: the Kolmogorov flow, in [-1, 1]; one Brownian path per pixel, x_t = x + sigma_t eps_t.
# A large image keeps its structure under much more noise than a single number, so its schedule goes
# up to sigma = 80, as in EDM. For display only, x_t is divided by sqrt(1 + sigma_t^2).
SIG_IMG = SMIN * (80.0 / SMIN) ** ts
x0 = np.asarray(Image.open('figures/x.png').convert('RGB').resize((2 * T, 2 * T), Image.LANCZOS)) / 127.5 - 1
noise = np.zeros_like(x0); xs = [x0]
for k in range(K):
    noise = noise + np.sqrt(SIG_IMG[k + 1]**2 - (SIG_IMG[k]**2 if k else 0)) * rng.normal(size=x0.shape)
    xs.append((x0 + noise) / np.sqrt(1 + SIG_IMG[k + 1]**2))

# 1D: density p_t on a grid, and four sample paths
grid = np.linspace(-5, 5, 300)
dens = np.stack([sum(w * np.exp(-0.5 * (grid - m)**2 / (S0**2 + s**2)) / np.sqrt(S0**2 + s**2)
                     for m, w in zip(MU, W)) for s in sig], 1)
paths = np.zeros((K + 1, 4)); paths[0] = MU[[0, 0, 1, 1]] + S0 * rng.normal(size=4)
for k in range(K):
    paths[k + 1] = paths[k] + np.sqrt(sig[k + 1]**2 - (sig[k]**2 if k else 0)) * rng.normal(size=4)


def frame(k, reverse):
    i = K - k if reverse else k
    fig = plt.figure(figsize=(7.38, 2.61), dpi=100)
    # both panels exactly the same height: a square image, and the 1D panel beside it
    h = 0.96; w = h * 2.61 / 7.38
    ax0 = fig.add_axes([0.005, 0.02, w, h])
    ax0.imshow(np.clip((xs[i] + 1) / 2, 0, 1), interpolation='nearest', aspect='auto'); ax0.axis('off')
    ax1 = fig.add_axes([0.03 + w, 0.02, 0.965 - w - 0.025, h])
    ax1.imshow(dens / dens.max(0, keepdims=True), extent=[0, 1, -5, 5], aspect='auto', origin='lower', cmap=dmap)
    sl = slice(i, K + 1) if reverse else slice(0, i + 1)
    for j in range(4):
        ax1.plot(ts[sl], paths[sl, j], color='white', lw=1.4)
        ax1.plot(ts[i], paths[i, j], 'o', color='white', ms=4)
    ax1.set_xlim(0, 1); ax1.set_ylim(-5, 5); ax1.axis('off')
    ax1.plot([], [], color='white', label='Reverse stochastic process' if reverse else 'Forward stochastic process')
    ax1.legend(loc='upper right', fontsize=11, framealpha=0.25, labelcolor='white', facecolor='black', edgecolor='none')
    fig.canvas.draw()
    im = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()); plt.close(fig)
    return im


for reverse, name in [(False, 'figures/perturb_kolmogorov.gif'), (True, 'figures/denoise_kolmogorov.gif')]:
    frames = [frame(k, reverse) for k in range(K + 1)]
    frames += [frames[-1]] * 20   # pause on the last frame
    frames[0].save(name, save_all=True, append_images=frames[1:], duration=50, loop=0, optimize=True)
