"""2D toy animations of the sampling loop, and of MMPS, PPR and KPS as steered versions of it.

Usage: python tools/steer2d.py {prior,mmps,lin,ppr,kps,cases}

The prior is a Gaussian mixture, so the denoiser E[x | x_t], the Tweedie
covariance V[x | x_t] and the transition p(x | x_t) are all exact. The
diffusion is variance exploding, x_t = x + sigma_t * eps.

All animations are built from the same primitives:

  denoise    x_hat = x_t + Sigma_t s(x_t, t) = E[x | x_t] (KPS draws x_hat ~ p(x | x_t))
  correct    a method-specific change of x_hat, driven by the observation (in red)
  renoise    to the next level, x_s ~ p(x_s | x_t, x = x_hat) (the bridge), or
             at the same level, x_t ~ p(x_t | x = x_hat) (the forward kernel)

Denoise, then renoise with the bridge, is one step of the reverse SDE. The
detour through x_hat is where observations and constraints act, since they
are defined on clean states.

  prior    denoise, renoise to the next level.
  mmps     y = x + eta, Gaussian. Denoise, add Sigma_t times the likelihood
           score of MMPS (Rozet et al, NeurIPS 2024), renoise. With A = I,
           x_hat + V (Sigma_y + V)^-1 (y - x_hat).
  lin      y = |x| + eta, a non-linear operator, linearized around x_hat; then MMPS.
  ppr      c(x) = (|x| - R)^2 = 0. Algorithm 2 of Rochman-Sharabi and Louppe
           (NeurIPS 2026): denoise and renoise to the next level, then M times:
           project through the denoiser, renoise at the same level.
  kps      y = x + eta with uniform noise, from a black-box simulator.
           Algorithm 1 of Andry, Savary, Rozet and Louppe (under review): M
           times: draw x_hat ~ p(x | x_t), simulate y_i, Kalman update, renoise
           at the same level (last sweep: to the next level).
"""
import subprocess
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
from matplotlib.collections import LineCollection

plt.rcParams.update({'font.family': 'Roboto', 'mathtext.fontset': 'cm'})

rng = np.random.default_rng(0)

# Prior: Gaussian mixture (same as the 2D toy of the Mainz talk)
MUS = np.array([[-2.0, 2.0], [2.2, 1.8], [0.0, -2.2], [-2.5, -1.0], [2.5, -1.5]])
COVS = np.array([[[0.5, 0.3], [0.3, 0.4]], [[0.4, -0.25], [-0.25, 0.5]], [[0.9, 0.0], [0.0, 0.2]],
                 [[0.2, 0.0], [0.0, 0.5]], [[0.3, 0.15], [0.15, 0.3]]])
WS = np.array([0.25, 0.2, 0.25, 0.15, 0.15])

Y_POINT, SIGMA_POINT = np.array([1.5, 1.0]), 0.5   # MMPS: y = x + eta, eta ~ N(0, 0.5^2 I)
Y_LIN, SIGMA_LIN = 2.7, 0.15                       # lin: y = |x| + eta, eta ~ N(0, 0.15^2)
R = 2.7                                            # PPR: c(x) = (|x| - R)^2
Y_KPS, W_KPS = np.array([2.0, -1.1]), 0.8          # KPS: y = x + eta, eta ~ U([-0.8, 0.8]^2)

N = 60                                # particles
LEVELS = np.geomspace(4.0, 0.03, 10)  # noise levels, from high to low
M = 2                                 # corrector sweeps per level (PPR, KPS)
F = (26, 8)                           # frames per stage, at the first level and from the fourth level on
FPS = 25
DIM = 0.5                             # opacity of the inactive rows of the stage strip

# One colour per kind of element, in the plane and in the equations alike
BLUE_NOISY = '#7fa3d6'   # noisy states x_1, x_t, x_s
BLUE = '#356aaf'         # clean states: estimates x_hat, final samples x_0
ORANGE = '#f28e2b'       # corrected estimates
RED = '#d62728'          # observation y, constraint c, simulated observations y_i
PURPLE = '#7a5aa6'       # covariance V[x | x_t]
TEAL = '#2a9d8f'         # projected noisy states x*
GREY = '0.3'             # exact posterior


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
    """Renoise to the next level: x_s ~ p(x_s | x_t, x), s2 < s."""
    if s2 == 0:
        return x.copy()
    a = s2**2 / s**2
    return x + a * (xt - x) + s2 * np.sqrt(1 - a) * rng.normal(size=x.shape)


def forward(x, s):
    """Renoise at the same level: x_t ~ p(x_t | x)."""
    return x + s * rng.normal(size=x.shape)


# The samplers, recorded as a list of stages ---------------------------------
# A stage: name, a (positions before), b (positions after), k (level), s (noise level), row and eq
# (highlighted in the strip), colour of the particles at the end, loop (arrow to light up),
# and optional overlays: ell (covariances), arrows (from, to), sims, tangents, hollow (from, to).

def stage(name, a, b, k, s, row, eq=None, color=BLUE, loop=None, **overlays):
    return dict(name=name, a=a, b=b, k=k, s=s, row=row, eq=eq, color=color, loop=loop, **overlays)


def renoised(s2):
    return BLUE if s2 == 0 else BLUE_NOISY   # x_0 is clean


def run_prior():
    stages, levels = [], np.concatenate([LEVELS, [0.0]])
    xt = levels[0] * rng.normal(size=(N, 2))
    for k in range(len(LEVELS)):
        s, s2 = levels[k], levels[k + 1]
        xh = denoise(xt, s)
        stages.append(stage('denoise', xt, xh, k, s, 1, loop='outer' if k else None))
        xn = bridge(xt, xh, s, s2)
        stages.append(stage('renoise', xh, xn, k, s2, 2, color=renoised(s2)))
        xt = xn
    return stages, xt


def run_mmps(linear=True):
    stages, levels = [], np.concatenate([LEVELS, [0.0]])
    xt = levels[0] * rng.normal(size=(N, 2))
    for k in range(len(LEVELS)):
        s, s2 = levels[k], levels[k + 1]
        xh = denoise(xt, s)
        V = tweedie_cov(xt, s)
        stages.append(stage('denoise', xt, xh, k, s, 1, loop='outer' if k else None, ell=(xh, V)))
        if linear:   # y = x + eta: A = I
            xc = xh + np.einsum('nij,nj->ni', V @ np.linalg.inv(SIGMA_POINT**2 * np.eye(2) + V), Y_POINT - xh)
            stages.append(stage('correct', xh, xc, k, s, 2, color=ORANGE, ell=(xh, V), arrows=(xh, xc)))
        else:        # y = |x| + eta, linearized around x_hat: A(x) ~ |x_hat| + J (x - x_hat)
            J = xh / np.linalg.norm(xh, axis=1, keepdims=True)
            stages.append(stage('linearize', xh, xh, k, s, 2, eq=0, ell=(xh, V), tangents=J))
            VJ = np.einsum('nij,nj->ni', V, J)
            gain = VJ / (np.einsum('ni,ni->n', J, VJ) + SIGMA_LIN**2)[:, None]
            xc = xh + gain * (Y_LIN - np.linalg.norm(xh, axis=1))[:, None]
            stages.append(stage('correct', xh, xc, k, s, 2, eq=1, color=ORANGE, ell=(xh, V), tangents=J,
                                arrows=(xh, xc)))
        xn = bridge(xt, xc, s, s2)
        stages.append(stage('renoise', xc, xn, k, s2, 3, color=renoised(s2)))
        xt = xn
    return stages, xt


def project(xt, s, iters=30):
    """PPR projection through the denoiser: argmin_x (|d(x)| - R)^2, Gauss-Newton from x_t."""
    x = xt.copy()
    for _ in range(iters):
        d = denoise(x, s)
        nd = np.linalg.norm(d, axis=1, keepdims=True)
        g = np.einsum('nij,nj->ni', tweedie_cov(x, s) / s**2, d / nd)  # J_d^T grad|d|, J_d = V / s^2
        step = (nd - R) * g / (np.sum(g**2, 1, keepdims=True) + 1e-9)
        step *= np.minimum(1, (2 * s + 0.5) / (np.linalg.norm(step, axis=1, keepdims=True) + 1e-9))
        x = x - step
    return x


def run_ppr():
    stages, levels = [], np.concatenate([LEVELS, [0.0]])
    xt = levels[0] * rng.normal(size=(N, 2))
    for k in range(len(LEVELS) - 1):
        s, s2 = levels[k], levels[k + 1]
        xh = denoise(xt, s)
        stages.append(stage('denoise', xt, xh, k, s, 1, loop='outer' if k else None))
        xs = bridge(xt, xh, s, s2)
        stages.append(stage('renoise', xh, xs, k, s2, 2, color=BLUE_NOISY))
        for m in range(M):
            xstar = project(xs, s2)
            xc = denoise(xstar, s2)
            stages.append(stage('correct', xs, xc, k, s2, 3, color=ORANGE, loop='inner' if m else None,
                                hollow=(xs, xstar)))
            last = k == len(LEVELS) - 2 and m == M - 1
            xs = xc if last else forward(xc, s2)
            stages.append(stage('renoise', xc, xs, k, 0 if last else s2, 4, color=renoised(0 if last else s2)))
    return stages, xs


def run_kps():
    stages, levels = [], np.concatenate([LEVELS, [0.0]])
    xt = levels[0] * rng.normal(size=(N, 2))
    Sy = W_KPS**2 / 3 * np.eye(2)   # covariance of the simulator noise
    for k in range(len(LEVELS)):
        s, s2 = levels[k], levels[k + 1]
        for m in range(M):
            x = sample_posterior(xt, s)
            V = tweedie_cov(xt, s)
            ell = (denoise(xt, s), V)
            stages.append(stage('denoise', xt, x, k, s, 1, loop='inner' if m else ('outer' if k else None), ell=ell))
            yi = x + rng.uniform(-W_KPS, W_KPS, size=x.shape)        # simulate y_i = A(x_i, eta_i)
            stages.append(stage('simulate', x, x, k, s, 2, eq=0, ell=ell, sims=yi))
            # Kalman update, with the Jacobian of A (the identity) and the covariance of eta
            xc = x + np.einsum('nij,nj->ni', V @ np.linalg.inv(V + Sy), Y_KPS - yi)
            stages.append(stage('correct', x, xc, k, s, 2, eq=1, color=ORANGE, ell=ell, sims=yi))
            if m < M - 1:
                xn = forward(xc, s)
                stages.append(stage('renoise', xc, xn, k, s, 3, eq=0, color=BLUE_NOISY))
            else:
                xn = bridge(xt, xc, s, s2)
                stages.append(stage('renoise', xc, xn, k, s2, 3, eq=1, color=renoised(s2)))
            xt = xn
    return stages, xt


# Exact targets ---------------------------------------------------------------------

def prior_density(X):
    out = 0
    for m, C, w in zip(MUS, COVS, WS):
        Ci = np.linalg.inv(C)
        d = X - m
        out = out + w * np.exp(-0.5 * np.einsum('...i,ij,...j->...', d, Ci, d)) / np.sqrt(np.linalg.det(C))
    return out


def target_density(method, X):
    if method == 'mmps':
        return prior_density(X) * np.exp(-0.5 * np.sum((X - Y_POINT)**2, -1) / SIGMA_POINT**2)
    if method == 'lin':
        return prior_density(X) * np.exp(-0.5 * (np.linalg.norm(X, axis=-1) - Y_LIN)**2 / SIGMA_LIN**2)
    if method == 'kps':
        return prior_density(X) * np.all(np.abs(X - Y_KPS) <= W_KPS, -1)
    return None


# Stage strip ---------------------------------------------------------------------

K_, N_, B_, O_, R_, P_, T_ = 'black', BLUE_NOISY, BLUE, ORANGE, RED, PURPLE, TEAL
# Equations as lists of (math, colour) pieces; '#' marks plain text
DENOISE = [(r'\hat{x}', B_), (r'\;=\;', K_), (r'x_t', N_), (r'\,+\,\Sigma_t\, s_\theta(', K_), (r'x_t', N_), (r', t)', K_)]
COVARIANCE = [(r'\mathbb{V}', P_), (r'\;=\;\Sigma_t \nabla_{x_t}', K_), (r'\hat{x}', B_)]


def to_next(xhat):
    return [(r'x_s', N_), (r'\;\sim\; p(x_s \mid\;', K_), (r'x_t', N_), (r',\ x\;=\;', K_), (r'\hat{x}', xhat), (r')', K_)]


SCORE = [(r'\hat{x}', O_), (r'\;\leftarrow\;', K_), (r'\hat{x}', B_), (r'\,+\,\Sigma_t \nabla_{x_t} \log p(', K_),
         (r'y', R_), (r'\mid\;', K_), (r'x_t', N_), (r')', K_)]
GAIN = [(r'@\hat{x}', K_), (r'\;=\;', K_), (r'\hat{x}', B_), (r'+', K_), (r'\mathbb{V}', P_), (r'A^{T}', R_), (r'(\Sigma_y+', K_),
        (r'A', R_), (r'\mathbb{V}', P_), (r'A^{T}', R_), (r')^{-1}(', K_), (r'y', R_), (r'-', K_), (r'A', R_),
        (r'\hat{x}', B_), (r')', K_)]
LABELS = {
    'prior': [('denoise', [DENOISE]), ('renoise', [to_next(B_)])],
    'mmps': [('denoise', [DENOISE, COVARIANCE]), ('likelihood score', [SCORE, GAIN]), ('renoise', [to_next(O_)])],
    'lin': [('denoise', [DENOISE, COVARIANCE]),
            ('linearize, likelihood score', [[(r'A(x)', R_), (r'\;\approx\;', K_), (r'A(', R_), (r'\hat{x}', B_),
                                              (r')\,+\,', R_), (r'J(x-', R_), (r'\hat{x}', B_), (r')', R_)], SCORE]),
            ('renoise', [to_next(O_)])],
    'ppr': [('denoise', [DENOISE]), ('renoise', [to_next(B_)]),
            ('project', [[(r'x^*', T_), (r'\;=\;\arg\min_x\ ', K_), (r'c', R_), (r'(d_\theta(x))', K_),
                          (r'#,  from ', K_), (r'x_s', N_)],
                         [(r'\hat{x}', O_), (r'\;\leftarrow\; d_\theta(', K_), (r'x^*', T_), (r')', K_)]]),
            ('renoise', [[(r'x_s', N_), (r'\;\sim\; p(x_s \mid\; x\;=\;', K_), (r'\hat{x}', O_), (r')', K_)]])],
    'kps': [('denoise', [[(r'\hat{x}^{(i)}', B_), (r'\;\sim\; p(x \mid\;', K_), (r'x_t^{(i)}', N_), (r')', K_)]]),
            ('Kalman update', [[(r'y^{(i)}', R_), (r'\;=\;\mathcal{A}(', K_), (r'\hat{x}^{(i)}', B_), (r', \eta^{(i)})', K_)],
                               [(r'\hat{x}^{(i)}', O_), (r'\;\leftarrow\;', K_), (r'\hat{x}^{(i)}', B_),
                                (r'\,+\,K^{(i)}(', K_), (r'y', R_), (r'\,-\,', K_), (r'y^{(i)}', R_), (r')', K_)]]),
            ('renoise', [[(r'x_t^{(i)}', N_), (r'\;\sim\; p(x_t \mid\; x\;=\;', K_), (r'\hat{x}^{(i)}', O_), (r')', K_),
                          (r'#   if $m < M$', K_)],
                         [(r'x_s^{(i)}', N_), (r'\;\sim\; p(x_s \mid\;', K_), (r'x_t^{(i)}', N_), (r',\ x\;=\;', K_),
                          (r'\hat{x}^{(i)}', O_), (r')', K_), (r'#   if $m = M$', K_)]])],
}
INIT = ('initialize', [[(r'x_1', N_), (r'\;\sim\;\mathcal{N}(0, \Sigma_1)', K_)]])
INIT_KPS = ('initialize', [[(r'x_1^{(i)}', N_), (r'\;\sim\;\mathcal{N}(0, \Sigma_1),\ \ i = 1, \dots, N', K_)]])
CORRECTION_ROWS = {'prior': [], 'mmps': [2], 'lin': [2], 'ppr': [3], 'kps': [2]}   # row names in red
# loop arrows: (key, source row, source equation, target row, to the row name or to its first equation)
LOOPS = {
    'prior': [('outer', 2, 0, 1, 'name')],
    'mmps': [('outer', 3, 0, 1, 'name')],
    'lin': [('outer', 3, 0, 1, 'name')],
    'ppr': [('outer', 4, 0, 1, 'name'), ('inner', 4, 0, 3, 'eq')],
    'kps': [('outer', 3, 1, 1, 'name'), ('inner', 3, 0, 1, 'eq')],
}
LOOP_TEXT = {'outer': r'$t \leftarrow s$', 'inner': r'$M$ times'}
FINAL = {'prior': r'samples $x_0 \sim p(x)$', 'mmps': r'samples $x_0 \sim p(x \mid y)$',
         'lin': r'samples $x_0 \sim p(x \mid y)$', 'ppr': r'samples $x_0 \sim p(x \mid x \in \mathcal{C})$',
         'kps': r'samples $x_0 \sim p(x \mid y)$'}
CIRCLE = np.stack([np.cos(np.linspace(0, 2 * np.pi, 60)), np.sin(np.linspace(0, 2 * np.pi, 60))], 1)


# Rendering ---------------------------------------------------------------------

def render(method, stages, final, out):
    g = np.linspace(-5, 5, 300)
    X = np.stack(np.meshgrid(g, g), -1)
    fig = plt.figure(figsize=(9.6, 5.4), dpi=120)
    ax = fig.add_axes([0.0, 0.0, 0.5625, 1.0])
    D = prior_density(X)
    ax.contourf(g, g, D, levels=np.linspace(0.02 * D.max(), D.max(), 12), cmap='Greys', alpha=0.45)
    th = np.linspace(0, 2 * np.pi, 400)

    # observation or constraint
    if method == 'mmps':
        for w, a in [(2 * SIGMA_POINT, 0.12), (SIGMA_POINT, 0.15)]:
            ax.fill(Y_POINT[0] + w * np.cos(th), Y_POINT[1] + w * np.sin(th), color=RED, alpha=a, lw=0)
        ax.plot(*Y_POINT, marker='*', ms=14, color=RED, mec='white', mew=0.8, zorder=5)
        ax.text(Y_POINT[0] + 0.2, Y_POINT[1] - 0.45, r'$y$', fontsize=18, color=RED, zorder=5)
    elif method == 'lin':
        for w, a in [(2 * SIGMA_LIN, 0.12), (SIGMA_LIN, 0.15)]:
            ax.fill(np.r_[(Y_LIN + w) * np.cos(th), (Y_LIN - w) * np.cos(th[::-1])],
                    np.r_[(Y_LIN + w) * np.sin(th), (Y_LIN - w) * np.sin(th[::-1])], color=RED, alpha=a, lw=0)
        ax.text(0, Y_LIN + 0.4, r'$A(x) = |x| \approx y$', fontsize=17, color=RED, ha='center', va='bottom', zorder=5)
    elif method == 'ppr':
        ax.plot(R * np.cos(th), R * np.sin(th), color=RED, lw=1.5, alpha=0.9)
        ax.text(0, R + 0.2, r'$c(x) = 0$', fontsize=18, color=RED, ha='center', va='bottom', zorder=5)
    elif method == 'kps':
        sx = Y_KPS[0] + W_KPS * np.array([-1, 1, 1, -1]); sy = Y_KPS[1] + W_KPS * np.array([-1, -1, 1, 1])
        ax.fill(sx, sy, color=RED, alpha=0.15, lw=0)
        ax.plot(*Y_KPS, marker='*', ms=14, color=RED, mec='white', mew=0.8, zorder=5)
        ax.text(Y_KPS[0] + 0.2, Y_KPS[1] - 0.45, r'$y$', fontsize=18, color=RED, zorder=5)

    # exact posterior, dashed, from the start
    T = target_density(method, X)
    if T is not None:
        ax.contour(g, g, T, levels=np.linspace(0.1, 0.9, 4) * T.max(), colors=GREY, linewidths=0.9,
                   linestyles='dashed', alpha=0.8)
        ax.plot([-4.8, -4.2], [-4.7, -4.7], color=GREY, lw=0.9, ls='--')
        ax.text(-4.1, -4.7, 'exact posterior', fontsize=12, color=GREY, va='center')
    ax.set_xlim(-5, 5); ax.set_ylim(-5, 5); ax.set_aspect('equal'); ax.axis('off')

    sc = ax.scatter(np.zeros(N), np.zeros(N), s=14, edgecolor='white', lw=0.4, zorder=3)
    sh = ax.scatter(np.zeros(N), np.zeros(N), s=14, facecolors='none', edgecolors=TEAL, lw=0.8, zorder=3)
    sm = ax.scatter(np.zeros(N), np.zeros(N), s=22, facecolors='none', edgecolors=RED, lw=1.0, zorder=4)
    lc = LineCollection([], colors=RED if method == 'kps' else ORANGE, linewidths=0.8, zorder=4)
    ax.add_collection(lc)
    tg = LineCollection([], colors=RED, linewidths=0.8, zorder=4)     # linearized level sets
    ax.add_collection(tg)
    el = LineCollection([], colors=PURPLE, linewidths=0.7, zorder=2)  # covariances V[x | x_t]
    ax.add_collection(el)

    # stage strip, vertically centred on the mixture
    tx = fig.add_axes([0.56, 0.0, 0.44, 1.0]); tx.axis('off'); tx.set_xlim(0, 1); tx.set_ylim(0, 1)
    labels = [INIT_KPS if method == 'kps' else INIT] + LABELS[method]
    X0 = 0.09
    renderer = fig.canvas.get_renderer()
    width = tx.get_window_extent(renderer).width
    FS_EQ, FS_NAME = 16, 18
    em = FS_EQ * fig.dpi / 72 / width   # one em, in axes units

    def pieces(y, eq):
        """Draw one equation as coloured pieces, side by side on a common baseline."""
        x, out = X0, []
        for txt, col in eq:
            if txt.startswith('@'):   # phantom: only leaves the space of its math, to align with the line above
                t = tx.text(x, y, '$%s$' % txt[1:], fontsize=FS_EQ, va='baseline')
                x += t.get_window_extent(renderer).width / width
                t.remove()
                continue
            t = tx.text(x, y, txt[1:] if txt.startswith('#') else '$%s$' % txt, fontsize=FS_EQ, color=col, va='baseline')
            x += t.get_window_extent(renderer).width / width
            tail = txt   # trailing math spaces are not part of the measured width
            while True:
                for cmd, w in ((r'\;', 5 / 18), (r'\,', 3 / 18), (r'\ ', 1 / 3)):
                    if tail.endswith(cmd):
                        x += w * em; tail = tail[:-len(cmd)]; break
                else:
                    break
            out.append(t)
        return out

    # vertical layout: noise level, then rows (name, equations), then the assumption, centred as a block
    FIRST, LINE, GAP, LEV = 0.06, 0.06, 0.07, 0.0
    heights = [FIRST + LINE * (len(eqs) - 1) + 0.02 for _, eqs in labels]
    total = LEV + sum(heights) + GAP * (len(labels) - 1)
    y0 = 0.5 + total / 2 - LEV
    rows, tops = [], []
    for i, (name, eqs) in enumerate(labels):
        col = RED if i in CORRECTION_ROWS[method] else 'black'
        t1 = tx.text(X0, y0, name, fontsize=FS_NAME, color=col, weight='bold', va='bottom')
        rows.append((t1, [pieces(y0 - FIRST - LINE * j, eq) for j, eq in enumerate(eqs)]))
        tops.append(y0)
        y0 -= heights[i] + GAP
    lev = ax.text(-4.85, 4.85, '', fontsize=FS_NAME, color='black', va='top', zorder=6)   # noise level, in the plane

    loops = {}
    eq_y = lambda row, j: tops[row] - FIRST - LINE * j + 0.012   # vertical centre of an equation
    aspect = (1.0 * 5.4) / (0.44 * 9.6)   # axes height over width
    for key, src, j, dst, where in LOOPS[method]:
        shared = len({(r, q) for _, r, q, _, _ in LOOPS[method]}) < len(LOOPS[method])   # loops leaving one line
        start = eq_y(src, j) + ((0.015 if key == 'inner' else -0.015) if shared else 0)
        end = tops[dst] + 0.02 if where == 'name' else eq_y(dst, 0)
        w = 0.085 if key == 'outer' else 0.035
        arrow = tx.annotate('', xy=(X0 - 0.015, end), xytext=(X0 - 0.015, start),
                            arrowprops=dict(arrowstyle='->', color='black', lw=1.5,
                                            connectionstyle='bar,fraction=%.3f' % (-w / abs(end - start))))
        text = tx.text(X0 - 0.015 - w * aspect - 0.022, (start + end) / 2, LOOP_TEXT[key], fontsize=14,
                       rotation=90, ha='center', va='center', color='black')
        loops[key] = (arrow, text)

    ffmpeg = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba',
                               '-s', '%dx%d' % fig.canvas.get_width_height(), '-r', str(FPS), '-i', '-',
                               '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16', out],
                              stdin=subprocess.PIPE)

    def emit(P, cols, active, s, eq=None, ov={}, u=1.0, ov_alpha=0.0, loop_on=None, label=None):
        sc.set_offsets(P); sc.set_facecolors(cols)
        sc.set_edgecolors(np.tile([1, 1, 1, cols[0, 3]], (N, 1)))
        for key, (arrow, text) in loops.items():
            arrow.arrow_patch.set_alpha(1.0 if key == loop_on else DIM)
            text.set_alpha(1.0 if key == loop_on else DIM)
        if 'hollow' in ov:   # noisy states moved by the projection, x_s -> x*
            h0, h1 = ov['hollow']; sh.set_offsets((1 - u) * h0 + u * h1); sh.set_alpha(0.5)
        else:
            sh.set_alpha(0)
        if 'sims' in ov:     # simulated observations and innovations
            sims = ov['sims']; sm.set_offsets(sims); sm.set_alpha(ov_alpha)
            lc.set_segments(np.stack([sims, np.tile(Y_KPS, (len(sims), 1))], 1)); lc.set_alpha(ov_alpha)
        elif 'arrows' in ov:  # likelihood-score corrections
            a0, a1 = ov['arrows']; sm.set_alpha(0)
            lc.set_segments(np.stack([a0, a1], 1)); lc.set_alpha(0.7)
        else:
            sm.set_alpha(0); lc.set_segments([])
        if 'tangents' in ov:  # linearized level sets {x : |x_hat| + J (x - x_hat) = y}
            J = ov['tangents']; foot = Y_LIN * J; perp = np.stack([-J[:, 1], J[:, 0]], 1)
            tg.set_segments(np.stack([foot - 0.6 * perp, foot + 0.6 * perp], 1))
            tg.set_alpha(0.5 * ov_alpha)
        else:
            tg.set_segments([])
        if 'ell' in ov:       # covariances of p(x | x_t), one standard deviation
            c, Vh = ov['ell']
            L = np.linalg.cholesky(Vh + 1e-9 * np.eye(2))
            el.set_segments([ci + CIRCLE @ Li.T for ci, Li in zip(c, L)]); el.set_alpha(0.25 * ov_alpha)
        else:
            el.set_segments([])
        for i, (t1, t2) in enumerate(rows):
            t1.set_alpha(1.0 if i == active else DIM)
            for j, line in enumerate(t2):
                on = i == active and (eq is None or j == eq)
                for t in line:
                    t.set_alpha(1.0 if on else DIM)
        lev.set_text(label or (r'noise level $\sigma_t = %.2f$' % s))
        fig.canvas.draw()
        ffmpeg.stdin.write(fig.canvas.buffer_rgba().tobytes())

    # initialization: the particles are drawn from N(0, Sigma_1)
    x1 = stages[0]['a']
    for f in range(F[0] + 10):
        emit(x1, np.tile(to_rgba(BLUE_NOISY, min(1, (f + 1) / F[0])), (N, 1)), 0, LEVELS[0])
    prev = BLUE_NOISY
    for st in stages:
        ov = {key: st[key] for key in ('arrows', 'sims', 'hollow', 'tangents') if key in st}   # no covariance ellipses
        nf = max(F[1], F[0] - (F[0] - F[1]) * st['k'] // 3)
        c0, c1 = np.array(to_rgba(prev)), np.array(to_rgba(st['color']))
        for f in range(nf):
            u = (f + 1) / nf
            u = u * u * (3 - 2 * u)
            # overlays fade in on the stage that introduces them, and simulated observations fade out on the update
            ov_alpha = {'denoise': u, 'linearize': u, 'simulate': u}.get(st['name'], 1.0)
            if st['name'] == 'correct' and 'sims' in ov:
                ov_alpha = 1 - u
            emit((1 - u) * st['a'] + u * st['b'], np.tile((1 - u) * c0 + u * c1, (N, 1)), st['row'], st['s'],
                 st['eq'], ov, u, ov_alpha, st['loop'] if f < max(3, nf // 2) else None)
        prev = st['color']
    for f in range(4 * FPS):
        emit(final, np.tile(to_rgba(BLUE), (N, 1)), -1, 0, label=FINAL[method])
    ffmpeg.stdin.close(); ffmpeg.wait()
    plt.close(fig)


def render_cases(out='figures/steer/cases.png'):
    """Two static panels: an exact constraint, and a simulator we can only sample from."""
    g = np.linspace(-5, 5, 300)
    X = np.stack(np.meshgrid(g, g), -1)
    D = prior_density(X)
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.6), dpi=150)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.88, bottom=0.01, wspace=0.08)
    th = np.linspace(0, 2 * np.pi, 400)
    for ax, title in zip(axes, ['Exact constraints', 'Simulators']):
        ax.contourf(g, g, D, levels=np.linspace(0.02 * D.max(), D.max(), 12), cmap='Greys', alpha=0.45)
        ax.set_xlim(-5, 5); ax.set_ylim(-5, 5); ax.set_aspect('equal'); ax.axis('off')
        ax.set_title(title, fontsize=17, weight='bold')
    # exact constraint: the samples must lie on the circle
    axes[0].plot(R * np.cos(th), R * np.sin(th), color=RED, lw=1.8)
    axes[0].text(0, R + 0.2, r'$c(x) = 0$', fontsize=17, color=RED, ha='center', va='bottom')
    p = prior_density(R * np.stack([np.cos(th), np.sin(th)], -1)); p /= p.sum()
    ang = rng.choice(th, size=60, p=p)
    axes[0].scatter(R * np.cos(ang), R * np.sin(ang), s=16, color=BLUE, edgecolor='white', lw=0.4, zorder=3)
    axes[0].text(0, -4.6, 'the samples must lie exactly on the constraint', fontsize=12, color='0.35', ha='center')
    # simulator: from one state, we can draw observations, but not evaluate their density
    x = np.array([1.4, -1.6])
    ys = x + rng.uniform(-W_KPS, W_KPS, size=(80, 2))
    axes[1].scatter(*ys.T, s=12, facecolors='none', edgecolors=RED, lw=0.8, zorder=3)
    axes[1].scatter(*x, s=40, color=BLUE, edgecolor='white', lw=0.6, zorder=4)
    axes[1].annotate(r'$x$', xy=x, xytext=(x[0] - 1.6, x[1] + 0.9), fontsize=17, color=BLUE, ha='center',
                     arrowprops=dict(arrowstyle='-', color=BLUE, lw=0.8))
    axes[1].plot(*Y_KPS, marker='*', ms=14, color=RED, mec='white', mew=0.8, zorder=5)
    axes[1].text(Y_KPS[0] + 0.25, Y_KPS[1] + 0.15, r'$y$', fontsize=17, color=RED)
    axes[1].text(x[0] - 1.6, x[1] - 1.5, r'$y^{(i)} = \mathcal{A}(x, \eta^{(i)})$', fontsize=15, color=RED, ha='center')
    axes[1].text(0, -4.6, 'we can draw observations, but not evaluate their density', fontsize=12, color='0.35',
                 ha='center')
    fig.savefig(out)


if __name__ == '__main__':
    method = sys.argv[1]
    if method == 'cases':
        render_cases(); sys.exit()
    run = {'prior': run_prior, 'mmps': run_mmps, 'lin': lambda: run_mmps(linear=False),
           'ppr': run_ppr, 'kps': run_kps}[method]
    stages, final = run()
    out = 'figures/steer/%s.mp4' % method
    render(method, stages, final, out)
    print(out, 'stages', len(stages), 'mean', final.mean(0).round(2), 'std', final.std(0).round(2))
