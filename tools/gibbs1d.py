"""AR, SDA (AAO) and GiBBS on an Ornstein-Uhlenbeck interpolation task.

Usage: python tools/gibbs1d.py

Outputs figures/steer/gibbs-problem.png (final samples of AR and SDA) and
figures/steer/gibbs.mp4 (the GiBBS chain over its cycles).

The prior is a stationary AR(1) process, x_{i+1} = a x_i + sqrt(1 - a^2) eps_i, so all
conditionals are Gaussian and exact. The first and last W states are observed, with
small Gaussian noise. Each method only uses windows of W states, as a local model would.

  AR      rollout: each window is drawn given the last state of the previous one and
          the observations inside it. Blind to future observations.
  AAO     SDA: reverse diffusion, with the score of each state assembled from its own
          window of 2k + 1 states (a banded, "fully convolutional" score), and the
          likelihood score of MMPS computed with the same local denoiser.
  GiBBS   blocks of B states are redrawn from their exact conditionals given their
          Markov blanket (one state on each side) and their observations; odd blocks,
          then even blocks; the layout shifts by B / 2 every other cycle.
"""
import subprocess

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams.update({'font.family': 'Roboto', 'mathtext.fontset': 'cm'})
rng = np.random.default_rng(3)

L, W, A = 100, 16, 0.998       # trajectory length, window size, AR(1) coefficient
SIGMA_Y = 0.05                 # observation noise
OBS = np.r_[0:10, L - 10:L]    # observed states: the first and last 10
S = 10                         # sample trajectories per method
LEVELS = np.geomspace(5.0, 0.02, 40)   # AAO noise levels
HALF = 7                       # AAO window: x_{i-7:i+7}
B = W - 2                      # GiBBS block size (window = block + one state on each side)
CYCLES = 48

BLUE = '#356aaf'
RED = '#d62728'
GREY = '0.3'
FPS = 25

K = A ** np.abs(np.arange(L)[:, None] - np.arange(L)[None])   # prior covariance
# a ground truth that starts high and ends low, so that the observations must inform the whole trajectory
_mu, _C = (lambda G: (G @ np.linalg.inv(K[np.ix_([0, L - 1], [0, L - 1])]) @ np.array([1.8, -1.8]),
                      K - G @ np.linalg.inv(K[np.ix_([0, L - 1], [0, L - 1])]) @ G.T))(K[:, [0, L - 1]])
truth = _mu + np.linalg.cholesky(_C + 1e-9 * np.eye(L)) @ rng.normal(size=L)
y = truth[OBS] + SIGMA_Y * rng.normal(size=len(OBS))


def condition(mu, C, idx, values, noise):
    """Condition N(mu, C) on noisy observations of the coordinates idx."""
    G = C[:, idx]
    gain = G @ np.linalg.inv(C[np.ix_(idx, idx)] + noise**2 * np.eye(len(idx)))
    return mu + gain @ (values - mu[idx]), C - gain @ G.T


def draw(mu, C, n):
    return mu + (np.linalg.cholesky(C + 1e-9 * np.eye(len(mu))) @ rng.normal(size=(len(mu), n))).T


def local_draw(x, block, given):
    """Exact draw of x[block] given x[given] and the observations inside the block, for each sample."""
    idx = np.r_[given, block]
    nb = len(given)
    out = x.copy()
    for n in range(len(x)):
        mu, C = np.zeros(len(idx)), K[np.ix_(idx, idx)]
        if nb:
            mu, C = condition(mu, C, np.arange(nb), x[n, given], 1e-6)
        mu, C = mu[nb:], C[nb:, nb:]
        obs = [j for j, i in enumerate(block) if i in OBS]
        if obs:
            vals = np.array([y[list(OBS).index(block[j])] for j in obs])
            mu, C = condition(mu, C, np.array(obs), vals, SIGMA_Y)
        out[n, block] = draw(mu, C, 1)[0]
    return out


def run_ar():
    """States of the AR rollout, one per window."""
    x = np.full((S, L), np.nan)
    states = []
    start = 0
    while start < L:
        block = np.arange(start, min(start + W - 1, L))
        if start == 0:
            z = np.zeros((S, L)); z = local_draw(z, block, np.array([], int))
        else:
            z = np.nan_to_num(x); z = local_draw(z, block, np.array([start - 1]))
        x[:, block] = z[:, block]
        states.append(x.copy())
        start += W - 1
    return states


def run_aao():
    """States of the AAO reverse diffusion (noisy trajectories), one per noise level."""
    Ainv = np.zeros((L, len(OBS))); Ainv[OBS, np.arange(len(OBS))] = 1
    Aobs = Ainv.T
    xt = LEVELS[0] * rng.normal(size=(S, L))
    states = [xt.copy()]
    levels = np.r_[LEVELS, 0.0]
    for k in range(len(LEVELS)):
        s, s2 = levels[k], levels[k + 1]
        # banded score: each state only sees its window
        Bm = np.zeros((L, L))
        for i in range(L):
            w = np.arange(max(0, i - HALF), min(L, i + HALF + 1))
            P = np.linalg.inv(K[np.ix_(w, w)] + s**2 * np.eye(len(w)))
            Bm[i, w] = -P[list(w).index(i)]
        D = np.eye(L) + s**2 * Bm        # local denoiser, E[x | x_t] = D x_t
        V = s**2 * D                     # Tweedie covariance of the local denoiser
        E = xt @ D.T
        Sy = SIGMA_Y**2 * np.eye(len(OBS)) + Aobs @ V @ Aobs.T
        lik = ((y - E @ Aobs.T) @ np.linalg.inv(Sy).T) @ Aobs @ D   # MMPS likelihood score
        xh = E + s**2 * lik
        if s2 == 0:
            xt = xh
        else:
            a = s2**2 / s**2
            xt = xh + a * (xt - xh) + s2 * np.sqrt(1 - a) * rng.normal(size=xt.shape)
        states.append(xt.copy())
    return states


def run_gibbs():
    """States of GiBBS, one per half-cycle, with the blocks just redrawn."""
    x = draw(np.zeros(L), K, S)          # blind start, from the prior
    states = [(x.copy(), [])]
    for c in range(CYCLES):
        shift = (c % 2) * (B // 2)
        starts = np.arange(shift - B, L, B)
        blocks = [np.arange(max(0, a), min(L, a + B)) for a in starts]
        blocks = [b for b in blocks if len(b)]
        for parity in (0, 1):
            redrawn = []
            for j, b in enumerate(blocks):
                if j % 2 != parity:
                    continue
                given = np.array([i for i in (b[0] - 1, b[-1] + 1) if 0 <= i < L])
                x = local_draw(x, b, given)
                redrawn.append(b)
            states.append((x.copy(), redrawn))
    return states


def panel(ax, post_mu, band, name, sub):
    t = np.arange(L)
    ax.fill_between(t, post_mu - band, post_mu + band, color='0.85', lw=0)
    ax.plot(t, post_mu, color=GREY, lw=1, ls='--')
    ax.plot(OBS, y, 'o', color=RED, ms=3, zorder=5)
    ax.set_ylim(-3.2, 3.2); ax.set_xlim(0, L - 1); ax.set_yticks([])
    for sp in ('top', 'right', 'left'):
        ax.spines[sp].set_visible(False)
    ax.text(-0.02, 0.6, name, transform=ax.transAxes, ha='right', va='center', fontsize=16, weight='bold')
    ax.text(-0.02, 0.36, sub, transform=ax.transAxes, ha='right', va='center', fontsize=12, color='0.35')
    return [ax.plot([], [], color=BLUE, lw=1, alpha=0.7)[0] for _ in range(S)]


def legend(ax):
    ax.plot([], [], 'o', color=RED, ms=3, label='observations $y$')
    ax.fill_between([], [], [], color='0.85', label='exact posterior')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.3), ncol=2, frameon=False, fontsize=12)


def main():
    post_mu, post_C = condition(np.zeros(L), K, OBS, y, SIGMA_Y)
    band = 2 * np.sqrt(np.diag(post_C))
    ar, aao, gib = run_ar(), run_aao(), run_gibbs()
    t = np.arange(L)

    # the problem: final samples of the two single-pass samplers
    fig, axes = plt.subplots(2, 1, figsize=(9.6, 4.0), dpi=150, sharex=True)
    fig.subplots_adjust(left=0.2, right=0.98, top=0.88, bottom=0.12, hspace=0.3)
    for ax, xs, name, sub in zip(axes, [ar[-1], aao[-1]], ['AR', 'SDA (AAO)'],
                                 ['window after window', 'all windows at once']):
        for line, x in zip(panel(ax, post_mu, band, name, sub), xs):
            line.set_data(t, x)
    # windows, one each: AR draws a window given the end of the previous one;
    # in SDA, the score of state i only sees the window x_{i-HALF:i+HALF}
    a0 = (W - 1) * 3                 # an actual AR window, x_{45:59}
    i0 = a0 + HALF                   # the SDA window of its centre state spans the same states
    axes[0].axvspan(a0 - 0.5, a0 + W - 1.5, color=BLUE, alpha=0.1, lw=0, zorder=0)
    axes[0].text(a0 + (W - 2) / 2, 3.1, 'one window', ha='center', va='top', fontsize=11, color='0.35')
    axes[1].axvspan(i0 - HALF - 0.5, i0 + HALF + 0.5, color=BLUE, alpha=0.1, lw=0, zorder=0)
    # the windows of the other states, all used at once: outlined, fading away from state i
    from matplotlib.patches import Rectangle
    for n, d in enumerate((-30, -20, -10, 10, 20, 30)):
        lo = i0 + d - HALF - 0.5
        inset = 0.25 + 0.2 * (abs(d) // 10)
        axes[1].add_patch(Rectangle((lo, -3.2 + inset), 2 * HALF + 1, 6.4 - 2 * inset, fill=False,
                                    edgecolor=BLUE, lw=1.2, alpha=0.6 * np.exp(-abs(d) / 15), zorder=0))
    axes[1].axvline(i0, color=BLUE, lw=0.8, alpha=0.5, zorder=0)
    axes[1].text(i0, 3.1, 'window of state $i$', ha='center', va='top', fontsize=11, color='0.35')
    axes[-1].set_xlabel('time $i$', fontsize=12)
    legend(axes[0])
    fig.savefig('figures/steer/gibbs-problem.png')
    plt.close(fig)

    # the solution: the GiBBS chain, cycle by cycle
    fig, ax = plt.subplots(figsize=(9.6, 2.6), dpi=120)
    fig.subplots_adjust(left=0.2, right=0.98, top=0.8, bottom=0.2)
    lines = panel(ax, post_mu, band, 'GiBBS', 'blocks redrawn in turn')
    ax.set_xlabel('time $i$', fontsize=12)
    legend(ax)
    progress = ax.text(0.99, 0.95, '', transform=ax.transAxes, ha='right', va='top', fontsize=11, color='0.35')
    shades = []
    ffmpeg = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba',
                               '-s', '%dx%d' % fig.canvas.get_width_height(), '-r', str(FPS), '-i', '-',
                               '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16', 'figures/steer/gibbs.mp4'],
                              stdin=subprocess.PIPE)
    # slow for the first cycles, then faster; hold on the last state
    schedule = [(i, 8 if i <= 16 else 2) for i in range(len(gib))] + [(len(gib) - 1, 3 * FPS)]
    for i, per_state in schedule:
        for line, x in zip(lines, gib[i][0]):
            line.set_data(t, x)
        for sh in shades:
            sh.remove()
        shades = [ax.axvspan(b[0] - 0.5, b[-1] + 0.5, color=BLUE, alpha=0.1, lw=0) for b in gib[i][1]]
        progress.set_text('initialization, blind to $y$' if i == 0 else 'cycle %d / %d' % ((i + 1) // 2, CYCLES))
        fig.canvas.draw()
        for _ in range(per_state):
            ffmpeg.stdin.write(fig.canvas.buffer_rgba().tobytes())
    ffmpeg.stdin.close(); ffmpeg.wait()
    plt.close(fig)

    # how far each method is from the exact posterior, on the unobserved states
    mid = np.setdiff1d(np.arange(L), OBS)
    sd = np.sqrt(np.diag(post_C))[mid]
    for name, xs in zip(['AR', 'SDA (AAO)', 'GiBBS'], [ar[-1], aao[-1], gib[-1][0]]):
        print('%-10s mean error / posterior std %.2f, std ratio %.2f' % (
            name, np.abs(xs.mean(0) - post_mu)[mid].mean() / sd.mean(), (xs.std(0)[mid] / sd).mean()))


if __name__ == '__main__':
    main()
