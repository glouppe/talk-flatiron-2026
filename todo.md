# TODO

Flatiron talk, October 28, 2026, 45 minutes: *Harness, don't retrain: diffusion models as steerable priors for inverse problems.*

Slide numbers refer to the deck as forked from Mainz (`n / 41`). They will shift as slides are removed and added, so each item also names the slide.

## Story

**Thesis.** Generation is a loop of denoise and renoise steps around a frozen network, and we own the loop. Steer the loop, and one pretrained prior serves many inverse problems without retraining.

**Visual thread.** The two equations of the sampling step (O4) come back in each part, with the term that method changes in red.

**Application.** The atmosphere runs through the talk. The question is what it takes to steer a single prior of the atmosphere. This is the logical order, not the history of the papers, so the talk should never say "then we needed X".

| Step | Problem | Answer | Change to the loop |
|---|---|---|---|
| 0 | Steering needs $\nabla \log p(y \mid x\_t)$, which is intractable | MMPS | the steer line |
| 1 | Trajectories are longer than the training windows | SDA, then GiBBS | the denoiser is assembled from windows (SDA); the loop runs per block (GiBBS) |
| 2 | Trajectories have $O(10^{10})$ variables | LoLA, Appa | the loop runs in latent space |
| 3 | Samples must satisfy physical constraints exactly: conservation laws, zero divergence, boundary conditions | PPR | inner loop: project, renoise |
| 4 | Real instruments are simulators: radiances, not states | KPS (ongoing) | inner loop: Kalman update, renoise |

Steps 3 and 4 relax the observation model assumed in steps 0–2, which is noisy, Gaussian and differentiable. Step 3 turns soft guidance into hard constraints $c(x) = 0$ (the limit $\sigma\_y \to 0$). Step 4 removes the Gaussian likelihood and the gradients.

**Payoff.** One Appa prior, several tasks: reanalysis from sparse observations (Appa), constrained sampling (PPR on Appa) and, as an outlook, satellite radiances (KPS). Only claim the third as future work, since KPS has not been run on Appa.

**Thread for the conclusions.** PPR and KPS both alternate *correct $x$, renoise $x\_t$*, which is a Gibbs sampler at a fixed noise level. GiBBS is a Gibbs sampler across time.

**Callbacks to the opening.** Earth observation (the atmosphere slides, 19–20 after the cuts: "satellites measure radiances, not the state", in the notes) motivates KPS. Black-hole imaging (slides 8–9) provides the KPS result. The "retrain" slide (19) comes back as the payoff: one prior, several tasks.

Target: about 39 slides. The plan removes 8 slides and adds about 6.

## Remove

- [x] **R1.** Slides 21–23 (coastal hypoxia).
- [x] **R2.** Slides 24–27 (regional downscaling, MARionette).
- [x] **R3.** Slide 39 (assimilating with a forecaster, FA-APF).
- [x] **R4.** Unused figures and videos: `hyp-*`, `blacksea-oxygen.jpg`, `mar-*`, `faapf*`, `videos/marionette-*`. On the thank-you slide, remove Grégoire, Peters and Fettweis (Mangeleer and Faulx stay, as Appa authors).

## Opening (slides 1–20, plus 2 new)

- [x] **O1.** Slide 1: new title, Flatiron Institute, October 28, 2026. Rewrite the notes: one idea (steer, don't retrain), followed through one application, the atmosphere.
- [x] **O2.** Intro examples cut to three (cryo-EM, MRI, black holes; slides 4–9). Earth observation and lensing were removed (figures deleted); the atmosphere slides (former 23–24) are now titled "Earth observation", and their notes carry the radiance seed for KPS.
- [x] **O3.** Slides 14–15: say in the notes that the instrument $p(y \mid x)$ changes from one problem to the next, but the physics $p(x)$ does not.
- [x] **O4.** New slide after slide 18 (denoiser): one sampling step. On top, three tiles generated from `figures/x.png` (`figures/loop/`): $x\_t$, then (denoise) $\hat{x}$, then (renoise) $x\_s$. Below, two display equations: denoise with the score, $\hat{x} = x\_t + \Sigma\_t s\_\theta(x\_t, t)$, then renoise, $x\_s \sim p(x\_s \mid x\_t, x = \hat{x})$ for the next time $s < t$. Same notation as slide 18 ($\Sigma\_t$, $s\_\theta$), keep it in all callbacks. Callbacks reuse these two equations and colour the changed term in red (`\textcolor{#d62728}{...}`, as for $y$ on slide 20).
- [x] **O5.** Slide 19 (hard-wired denoiser): keep. Title it "Posterior sampling: retrain..." (states the problem and sets up slide 20).
- [x] **O6.** Slide 20: the thesis slide, "... or harness". Repeat the denoise equation of O4 with the posterior score: $\hat{x} = x\_t + \Sigma\_t \big(s\_\theta(x\_t, t) + \textcolor{#d62728}{\nabla\_{x\_t} \log p(y \mid x\_t)}\big)$. Steering changes one term in the loop and leaves the network untouched. Keep the SDE smaller, or move it to the notes. Drop the DPS/MMPS footnote, which moves to O7. In the notes, replace "three problems... the ocean" with a transition: the gradient in that line is the catch.
- [x] **O7.** New slide after slide 20: MMPS. $p(y \mid x\_t) = \int p(y \mid x)\, p(x \mid x\_t)\, \text{d}x$ is intractable. DPS uses a Dirac at $\mathbb{E}[x \mid x\_t]$. MMPS uses a Gaussian with the Tweedie covariance $\mathbb{V}[x \mid x\_t] = \Sigma\_t \nabla\_{x\_t} d\_\theta^\top$, solved by conjugate gradient with vector-Jacobian products. State the assumption explicitly, $p(y \mid x) = \mathcal{N}(y \mid \mathcal{A}(x), \Sigma\_y)$ with $\mathcal{A}$ differentiable, because N1 relaxes it. Start from the MMPS slide of the CSML/KULeuven talks and tighten it. Credit: [Rozet et al](https://arxiv.org/abs/2405.13712), NeurIPS 2024. Avatars: François Rozet, Gérôme Andry, François Lanusse.

## Atmosphere: long trajectories (slides 28–34)

- [x] **A1.** Slides 28–30 (observations $y$, trajectories $x\_{1:L}$, data assimilation): keep. Rewrite the notes of slide 28 ("Our third example..."). Rewrite the notes of slide 30 ("three steps") to announce the obstacles in the order of the table above.
- [x] **A2.** Slides 31–32 (SDA): keep. Callback: the score $s\_\theta$ of the step is assembled from windows, and the red likelihood term is MMPS.
- [x] **A3.** Slides 33–34 (GiBBS): keep. Callback: the loop runs per block, conditioned on the block's Markov blanket and in parallel across same-colour blocks. Credit: Bodart, Andry, Rozet and Louppe, under review at ICLR 2027. Check that `gibbs-strategies.png` matches Fig. 1 of the paper.

## Atmosphere: scale (slides 35–38)

- [x] **S1.** Slide 35 ($O(10^{10})$ variables): keep.
- [x] **S2.** Slide 36 (LoLA): keep. In the notes, say that this work started here at Flatiron, with Lanusse, Ohana, McCabe and Ho.
- [x] **S3.** Slides 37–38 (Appa): keep. In the notes, say that posterior sampling runs in latent space with $y = \mathcal{A}(D(z)) + \eta$, using MMPS through the decoder. This is the first task for the Appa prior: reanalysis.

## Atmosphere: beyond noisy, Gaussian observations (new, 4 slides)

- [x] **N1.** New slide, transition: so far, $y$ has been a noisy, Gaussian, differentiable function of the state. Two cases break this:
  - the physics imposes exact constraints that a learned prior only satisfies approximately: conservation of mass and energy, $\nabla \cdot u = 0$, boundary conditions;
  - real instruments are simulators, such as radiative transfer from the state to satellite radiances (callback to the Earth observation slides, 19–20).

  Could be folded into the first lines of N2 if time is short.
- [x] **N2.** New slide, PPR. Physical constraints $c(x) = 0$ must hold exactly, not on average. A diffusion prior satisfies them only approximately, and guidance cannot fix that: as $\sigma\_y \to 0$, the likelihood becomes a Dirac and its gradients break down. Projections enforce the constraint but leave the data manifold. The target is the constrained marginal $p^{\mathcal{C}}\_t$. Proposition 3.1: "draw a feasible $x\_0$, renoise" leaves it invariant. PPR approximates this by projecting through the denoiser, $\arg\min\_x c(d\_\theta(x))$, then renoising, $M$ times. Show the two step equations of O4, with the project-then-renoise correction in red between them. Optionally add PPR Fig. 1 (DATA 2D marginals). Avatar: Omer Rochman-Sharabi. Credit: [Rochman-Sharabi and Louppe](https://arxiv.org/abs/2601.21033), NeurIPS 2026.
- [x] **N3.** New slide, PPR on Appa (PPR Fig. 5). Caveat: the paper has no experiment with a physical constraint. All three experiments use exact observations as the constraint. Present this slide as "PPR works for any non-linear $c$, even through a 170M-parameter decoder at $O(10^8)$ variables", with the constraint $c(z) = \lVert D(z^{12}) - y \rVert^2$ (the exact state at 12:00, a forecasting task for the same prior). Never suggest that a conservation law was enforced. No result with a physical constraint exists yet, so list it under open problems in C1. PPR beats DPS, MMPS and the projection baselines on all surface variables, at every lead time. In the notes, mention the KS result: more than 82% of PPR samples are feasible, against at most 1% for the baselines.
- [x] **N4.** New slide, KPS (ongoing). The instrument is any stochastic simulator $y = \mathcal{A}(x, \eta)$, with no likelihood and possibly no gradients. KPS draws $x^{(i)} \sim p(x \mid x\_t)$ and simulates $y^{(i)}$. It linearizes the simulator statistically from these pairs, applies a Kalman update $x^{(i)} \leftarrow x^{(i)} + K(y - y^{(i)})$, then renoises. Show the two step equations of O4 with the Kalman correction of $\hat{x}$ in red, next to PPR's: same structure, a different correction. Figure: KPS Fig. 5, two black-hole images from one ensemble that fit the visibilities as well as the truth (callback to slides 8–9). In the notes, give the InverseBench numbers and the outlook to radiances in Appa. Avatars: Gérôme Andry, Thomas Savary, François Rozet. Credit: Andry, Savary, Rozet and Louppe, under review at ICLR 2027.

- [x] **N5.** Extra slide after KPS: black-hole imaging (KPS appendix Fig. 14: truth, mean, four samples, four test images; `figures/kps-blackhole.png`), callback to slides 8–9. No heading, a caption instead (same for the PPR-on-Appa slide).
- [x] **N6.** PPR and KPS animations on a shared 2D toy (`tools/steer2d.py`, output in `figures/steer/`): same prior, same circle, same stage strip (denoise, correction in red, renoise). Regenerate with `python3 tools/steer2d.py {ppr,kps}`.
- [x] **S4.** New slide after Appa: posterior sampling in latent space. Likelihood through the decoder, joint linearization of $\mathcal{A} \circ D$ around $\hat{z} = \mathbb{E}[z \mid z\_t]$, MMPS with $J$ in place of $A$.

## Conclusions (slides 40–41)

- [x] **C1.** Slide 40: one frozen prior, steered at inference time, with one take-home per row of the story table. Add the thread: correct, renoise, repeat. Payoff: one Appa prior for reanalysis, constrained sampling and, next, radiances. Open problems: physical constraints at scale (PPR on conservation laws in Appa), calibration without ground truth, imperfect priors, speed at $10^{10}$ variables, strongly non-linear simulators.
- [x] **C2.** Slide 41 (closing equation): rewrite the notes. Drop "the Black Sea, the rain over Belgium".
- [x] **C3.** Thank-you slide: Rozet, Andry, Bodart, Savary, Rochman-Sharabi; Mangeleer, Faulx, Lewin, Pirlet (Appa); Lanusse, Ohana, McCabe, Ho (done with R4).

## Figures to extract

- [x] **F1.** PPR: Fig. 5 (Appa), optionally Fig. 1.
- [x] **F2.** KPS: Fig. 5 (black-hole modes).
