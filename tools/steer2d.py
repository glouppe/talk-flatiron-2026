"""2D toy animations of PPR and KPS, steering a frozen diffusion prior.

Usage: python tools/steer2d.py {ppr,kps} [--frames-only]

The prior is a Gaussian mixture, so the denoiser E[x | x_t], the Tweedie
covariance V[x | x_t] and the transition p(x | x_t) are all exact. The
diffusion is variance exploding, x_t = x + sigma_t * eps. Both animations
share the same prior, target circle |x| = R, layout and stage strip
(denoise, correct, renoise), so that the two methods read side by side.

  PPR (Rochman-Sharabi and Louppe, NeurIPS 2026, Algorithm 2): at each level,
  predict with the bridge, then M times: project through the denoiser,
  x* = argmin_x c(d(x)) with c(x) = (|x| - R)^2, and renoise around d(x*).

  KPS (Andry, Savary, Rozet and Louppe, under review, Algorithm 1), gradient
  variant: at each level, M times: draw x ~ p(x | x_t), simulate
  y_i = |x| + eta, Kalman update with the particle's own Jacobian, then
  renoise (last sweep: bridge to the next level).
"""
import subprocess
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba

plt.rcParams.update({'font.family': 'Roboto', 'mathtext.fontset': 'cm'})

rng = np.random.default_rng(0)

# Prior: Gaussian mixture (same as the 2D toy of the Mainz talk)
MUS = np.array([[-2.0, 2.0], [2.2, 1.8], [0.0, -2.2], [-2.5, -1.0], [2.5, -1.5]])
COVS = np.array([[[0.5, 0.3], [0.3, 0.4]], [[0.4, -0.25], [-0.25, 0.5]], [[0.9, 0.0], [0.0, 0.2]],
                 [[0.2, 0.0], [0.0, 0.5]], [[0.3, 0.15], [0.15, 0.3]]])
WS = np.array([0.25, 0.2, 0.25, 0.15, 0.15])

R = 2.7         # target circle |x| = R
SIGMA_Y = 0.15  # KPS observation noise, y = |x| + eta
N = 200         # particles
LEVELS = np.geomspace(4.0, 0.03, 10)  # noise levels, from high to low
M = 2           # corrector sweeps per level
F = (18, 5)     # frames per stage, at the first level and from the fourth level on
FPS = 25

BLUE_NOISY = '#9db8dc'
BLUE = '#356aaf'
RED = '#d62728'


# Exact posterior of the mixture given x_t ----------------------------------

def _components(xt, s):
    """Responsibilities r (n, K), means mt (n, K, 2) and covariance Ct (K, 2, 2) of p(x | x_t)."""
    I = np.eye(2)
    logr, mts, Cts = [], [], []
    for m, C, w in zip(MUS, COVS, WS):
        Cm = C + s**2 * I
        d = xt - m
        Cmi = np.linalg.inv(Cm)
        logr.append(np.log(w) - 0.5 * np.einsum('ni,ij,nj->n', d, Cmi, d) - 0.5 * np.log(np.linalg.det(Cm)))
        Ct = np.linalg.inv(np.linalg.inv(C) + I / s**2)
        mts.append((Ct @ (np.linalg.inv(C) @ m))[None] + xt @ Ct.T / s**2)
        Cts.append(Ct)
    logr = np.stack(logr, 1)
    r = np.exp(logr - logr.max(1, keepdims=True))
    return r / r.sum(1, keepdims=True), np.stack(mts, 1), np.array(Cts)


def denoise(xt, s):
    r, mt, _ = _components(xt, s)
    return np.einsum('nk,nki->ni', r, mt)


def tweedie_cov(xt, s):
    r, mt, Ct = _components(xt, s)
    mean = np.einsum('nk,nki->ni', r, mt)
    second = np.einsum('nk,kij->nij', r, Ct) + np.einsum('nk,nki,nkj->nij', r, mt, mt)
    return second - mean[:, :, None] * mean[:, None, :]


def sample_posterior(xt, s):
    r, mt, Ct = _components(xt, s)
    k = np.array([rng.choice(len(WS), p=p) for p in r])
    L = np.linalg.cholesky(Ct)
    return mt[np.arange(len(xt)), k] + np.einsum('nij,nj->ni', L[k], rng.normal(size=xt.shape))


def bridge(xt, x, s, s2):
    """Draw x_s ~ p(x_s | x_t, x) for the VE diffusion, s2 < s."""
    if s2 == 0:
        return x.copy()
    a = s2**2 / s**2
    return x + a * (xt - x) + s2 * np.sqrt(1 - a) * rng.normal(size=x.shape)


# The two samplers, recorded as a list of stages ------------------------------

def project(xt, s, iters=30):
    """PPR projection through the denoiser: argmin_x (|d(x)| - R)^2, Gauss-Newton from x_t."""
    x = xt.copy()
    for _ in range(iters):
        d = denoise(x, s)
        nd = np.linalg.norm(d, axis=1, keepdims=True)
        f = nd - R
        g = np.einsum('nij,nj->ni', tweedie_cov(x, s) / s**2, d / nd)  # J_d^T grad|d|, J_d = V / s^2
        step = f * g / (np.sum(g**2, 1, keepdims=True) + 1e-9)
        nrm = np.linalg.norm(step, axis=1, keepdims=True)
        step *= np.minimum(1, (2 * s + 0.5) / (nrm + 1e-9))
        x = x - step
    return x


def run_ppr():
    stages = []
    levels = np.concatenate([LEVELS, [0.0]])
    xt = levels[0] * rng.normal(size=(N, 2))
    for k in range(len(LEVELS) - 1):
        s, s2 = levels[k], levels[k + 1]
        xh = denoise(xt, s)
        stages.append(('denoise', xt, xh, k, s))
        xs = bridge(xt, xh, s, s2)
        stages.append(('renoise', xh, xs, k, s2))
        xt = xs
        for m in range(M):
            xh = denoise(xt, s2)
            stages.append(('denoise', xt, xh, k, s2))
            xc = denoise(project(xt, s2), s2)
            stages.append(('correct', xh, xc, k, s2))
            if k == len(LEVELS) - 2 and m == M - 1:
                return stages, xc
            xn = xc + s2 * rng.normal(size=xc.shape)
            stages.append(('renoise', xc, xn, k, s2))
            xt = xn


def run_kps():
    stages = []
    levels = np.concatenate([LEVELS, [0.0]])
    xt = levels[0] * rng.normal(size=(N, 2))
    for k in range(len(LEVELS)):
        s, s2 = levels[k], levels[k + 1]
        for m in range(M):
            x = sample_posterior(xt, s)
            stages.append(('denoise', xt, x, k, s))
            yi = np.linalg.norm(x, axis=1) + SIGMA_Y * rng.normal(size=N)
            sims = x * (yi / np.linalg.norm(x, axis=1))[:, None]          # y_i, drawn at radius y_i
            stages.append(('simulate', x, x, k, s, sims))
            A = x / np.linalg.norm(x, axis=1, keepdims=True)              # Jacobian of |x|, per particle
            V = tweedie_cov(xt, s)
            VA = np.einsum('nij,nj->ni', V, A)
            K = VA / (np.einsum('ni,ni->n', A, VA) + SIGMA_Y**2)[:, None]
            xc = x + K * (R - yi)[:, None]
            stages.append(('correct', x, xc, k, s, sims))
            if m < M - 1:
                xn = xc + s * rng.normal(size=xc.shape)
                stages.append(('renoise', xc, xn, k, s))
            else:
                xn = bridge(xt, xc, s, s2)
                if s2 == 0:
                    return stages, xc
                stages.append(('renoise', xc, xn, k, s2))
            xt = xn


# Rendering ---------------------------------------------------------------------

def prior_density(X):
    out = 0
    for m, C, w in zip(MUS, COVS, WS):
        Ci = np.linalg.inv(C)
        d = X - m
        out = out + w * np.exp(-0.5 * np.einsum('...i,ij,...j->...', d, Ci, d)) / np.sqrt(np.linalg.det(C))
    return out


LABELS = {
    'ppr': [('denoise', [r'$\hat{x} = d_\theta(x_t, t)$']),
            ('project', [r'$x^* = \arg\min_x\ c(d_\theta(x))$']),
            ('renoise', [r'$x_t \sim p(x_t \mid x = d_\theta(x^*))$'])],
    'kps': [('denoise', [r'$x^{(i)} \sim p(x \mid x_t^{(i)})$']),
            ('Kalman update', [r'$y^{(i)} = \mathcal{A}(x^{(i)}, \eta^{(i)})$',
                               r'$x^{(i)} \leftarrow x^{(i)} + K^{(i)}(y - y^{(i)})$']),
            ('renoise', [r'$x_t^{(i)} \sim p(x_t \mid x^{(i)})$'])],
}
FINAL = {'ppr': r'samples $x \sim p(x \mid x \in \mathcal{C})$', 'kps': r'samples $x \sim p(x \mid y)$'}
STAGE_ROW = {'denoise': 0, 'simulate': 1, 'correct': 1, 'renoise': 2}
STAGE_EQ = {'simulate': 0, 'correct': -1}   # equation highlighted within the row (default: all)
STAGE_COLOR = {'denoise': BLUE, 'simulate': BLUE, 'correct': RED, 'renoise': BLUE_NOISY}


def render(method, stages, final, out):
    g = np.linspace(-5, 5, 300)
    X = np.stack(np.meshgrid(g, g), -1)
    fig = plt.figure(figsize=(9.6, 5.4), dpi=120)
    ax = fig.add_axes([0.0, 0.0, 0.5625, 1.0])
    D = prior_density(X)
    ax.contourf(g, g, D, levels=np.linspace(0.02 * D.max(), D.max(), 12), cmap='Greys', alpha=0.45)
    th = np.linspace(0, 2 * np.pi, 400)
    circ = R * np.stack([np.cos(th), np.sin(th)], 1)
    if method == 'ppr':
        ax.plot(circ[:, 0], circ[:, 1], color=RED, lw=1.5, alpha=0.9)
    else:
        for w, a in [(2 * SIGMA_Y, 0.12), (SIGMA_Y, 0.15)]:
            ax.fill(np.r_[(R + w) * np.cos(th), (R - w) * np.cos(th[::-1])],
                    np.r_[(R + w) * np.sin(th), (R - w) * np.sin(th[::-1])], color=RED, alpha=a, lw=0)
    ax.set_xlim(-5, 5); ax.set_ylim(-5, 5); ax.set_aspect('equal'); ax.axis('off')
    sc = ax.scatter(np.zeros(N), np.zeros(N), s=14, edgecolor='white', lw=0.4, zorder=3)
    sm = ax.scatter(np.zeros(N), np.zeros(N), s=22, facecolors='none', edgecolors=RED, lw=1.0, zorder=4)

    # Stage strip, as on the sampling slide: denoise, correction (red), renoise
    tx = fig.add_axes([0.56, 0.0, 0.44, 1.0]); tx.axis('off'); tx.set_xlim(0, 1); tx.set_ylim(0, 1)
    rows = []
    y0 = 0.72
    for i, (name, eqs) in enumerate(LABELS[method]):
        col = RED if i == 1 else 'black'
        t1 = tx.text(0.02, y0, name, fontsize=19, color=col, weight='bold', va='bottom')
        t2 = [tx.text(0.02, y0 - 0.025 - 0.08 * j, eq, fontsize=17, color=col, va='top') for j, eq in enumerate(eqs)]
        rows.append((t1, t2))
        bottom = y0 - 0.09 - 0.08 * (len(eqs) - 1)
        y0 = bottom - 0.11
        if i < 2:
            tx.annotate('', xy=(0.1, y0 + 0.06), xytext=(0.1, bottom), arrowprops=dict(arrowstyle='->', color='0.5', lw=1))
    lev = tx.text(0.02, 0.86, '', fontsize=18, color='black')

    ffmpeg = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba',
                               '-s', '%dx%d' % fig.canvas.get_width_height(), '-r', str(FPS), '-i', '-',
                               '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', out],
                              stdin=subprocess.PIPE)

    def emit(P, cols, active, s, eq=None, sims=None, sims_alpha=0.0):
        sc.set_offsets(P); sc.set_facecolors(cols)
        sm.set_offsets(sims if sims is not None else np.zeros((N, 2))); sm.set_alpha(sims_alpha)
        for i, (t1, t2) in enumerate(rows):
            t1.set_alpha(1.0 if i == active else 0.25)
            for j, t in enumerate(t2):
                on = i == active and (eq is None or j == eq % len(t2))
                t.set_alpha(1.0 if on else 0.25)
        lev.set_text(r'noise level $\sigma_t = %.2f$' % s if s > 0 else FINAL[method])
        fig.canvas.draw()
        ffmpeg.stdin.write(fig.canvas.buffer_rgba().tobytes())

    prev = BLUE_NOISY
    for name, a, b, k, s, *rest in stages:
        row = STAGE_ROW[name]
        sims = rest[0] if rest else None
        nf = max(F[1], F[0] - (F[0] - F[1]) * k // 3)
        c0, c1 = np.array(to_rgba(prev)), np.array(to_rgba(STAGE_COLOR[name]))
        for f in range(nf):
            u = (f + 1) / nf
            u = u * u * (3 - 2 * u)
            sa = u if name == 'simulate' else (1 - u if sims is not None else 0.0)
            emit((1 - u) * a + u * b, np.tile((1 - u) * c0 + u * c1, (N, 1)), row, s, STAGE_EQ.get(name), sims, sa)
        prev = STAGE_COLOR[name]
    for _ in range(3 * FPS):
        emit(final, np.tile(to_rgba(RED), (N, 1)), -1, 0)
    ffmpeg.stdin.close(); ffmpeg.wait()
    plt.close(fig)


if __name__ == '__main__':
    method = sys.argv[1]
    stages, final = run_ppr() if method == 'ppr' else run_kps()
    out = 'figures/steer/%s.mp4' % method
    render(method, stages, final, out)
    r = np.linalg.norm(final, axis=1)
    print(out, 'stages', len(stages), '| |x| - R: mean %.3f, std %.3f' % ((r - R).mean(), (r - R).std()))
