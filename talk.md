class: black-slide
background-image: url(figures/title-bg.gif)
background-size: cover

.overlay-box.overlay-title-slide[
.overlay-title[Harness, don't retrain<br>.smaller[Diffusion models as steerable priors for inverse problems]]

.title-author[![](figures/faces/gilles.jpg).title-author-text[Gilles Louppe<br>.smaller[[g.louppe@uliege.be](mailto:g.louppe@uliege.be)]]]

.title-footer[.smaller[Flatiron Institute, New York<br>October 28, 2026]![](figures/logo-uliege-white.png)]
]

???

Thank you for the invitation. It is a pleasure to be here.

This talk is about one property of diffusion models. Their sampling can be steered at inference time, without retraining. A single pretrained model then serves as the prior of many inverse problems.

We will start with a few pictures of inverse problems in science. Then we will follow one of them, the state of the atmosphere, until the end of the talk.

---

class: middle, black-slide, center
background-image: url(figures/title-bg.gif)
background-size: cover

.bold.larger.shadowed[From a noisy observation $y$...]

???

Suppose we observe this. It is a coarse and noisy observation $y$ of a 2D turbulent flow, averaged over large blocks.

---

class: middle, black-slide, center

.bg-video[<video autoplay muted loop playsinline poster="figures/x.png" src="figures/videos/teaser-x.mp4"></video>]

.bold.larger.shadowed[... can we recover <br> all plausible physical states $x$?]

???

Given $y$, we want to recover all plausible physical states $x$ that could have produced it. Here is one of them, the true flow. Many others are consistent with the same blocks. We want them all, as a distribution.

This toy flow is not an exception. The same question arises whenever an instrument stands between us and the system we study. Let me show you five examples, from molecules to galaxies.

---

class: black-slide
background-image: url(figures/mic-y.png)
background-size: cover

.overlay-box.overlay-intro[
.overlay-title[Cryo-electron microscopy]

Thousands of noisy 2D projections $y$ of a molecule, in unknown orientations.
]

.footnote[Simulated particle images of the .italic[P. falciparum] 80S ribosome (EMD-2660).]

???

First, structural biology. Cryo-electron microscopy images molecules frozen in ice. Each image is a 2D projection of the molecule, seen from an unknown angle, blurred by the microscope and buried in noise. The noise is unavoidable, because a stronger electron beam would destroy the sample. A typical dataset holds hundreds of thousands of such images. This is the observation $y$.

---

class: black-slide
background-image: url(figures/mic-x.png)
background-size: cover

.overlay-box.overlay-intro[
.overlay-title[Cryo-electron microscopy]

The 3D structure $x$ of the molecule.
]

.footnote[Structure: EMD-2660, [Wong et al](https://doi.org/10.7554/eLife.03080), eLife 2014. Flow-prior reconstruction: [Zhou et al](https://arxiv.org/abs/2410.08631), ICLR 2025 (arXiv:2410.08631).]

???

From all those images, we want to recover the molecule itself, in 3D. Here, a ribosome of the malaria parasite, at near-atomic resolution. That is our state $x$, and every detail of it has to be inferred from those noisy projections.

---

class: black-slide
background-image: url(figures/mri-y.png)
background-size: cover

.overlay-box.overlay-top-right[
.overlay-title[Accelerated MRI]

Undersampling k-space speeds up the scan but leaves aliased images $y$.
]

.footnote[Credits: [Rozet et al](https://arxiv.org/abs/2405.13712), NeurIPS 2024 (arXiv:2405.13712).]

???

Second, medical imaging. An MRI scan measures the image in Fourier space, line by line. To make scans faster, we measure only some of the lines, here one out of six. A naive reconstruction then gives these blurry, aliased images. This is the observation $y$.

---

class: black-slide
background-image: url(figures/mri-x.png)
background-size: cover

.overlay-box.overlay-top-right[
.overlay-title[Accelerated MRI]

The full-resolution scans $x$.
]

.footnote[Credits: [Rozet et al](https://arxiv.org/abs/2405.13712), NeurIPS 2024 (arXiv:2405.13712).]

???

What we would like to see instead is the knee itself, at full resolution. That is our state $x$. To get there, the missing lines have to be filled in, in a way that is consistent with what a knee looks like.

---

class: black-slide
background-image: url(figures/sat-y.png)
background-size: cover

.overlay-box.overlay-intro-right[
.overlay-title[Earth observation]

Satellites measure infrared radiances $y$, not the state of the atmosphere.
]

.footnote[Data: [GridSat-B1](https://www.ncei.noaa.gov/products/gridded-geostationary-brightness-temperature), NOAA NCEI, infrared brightness temperatures, March 21, 2021, 00:00 UTC.]

???

Third, weather. Satellites do not measure the atmosphere directly. They measure radiation. Here, the infrared radiation seen by the geostationary satellites, at one instant. Cold cloud tops appear white. This is the observation $y$.

To go from the state of the atmosphere to these radiances, we need a radiative transfer model, a simulator in its own right. Keep it in mind. We will need it at the end.

---

class: black-slide
background-image: url(figures/sat-x.png)
background-size: cover

.overlay-box.overlay-intro-right[
.overlay-title[Earth observation]

The state $x$ of the atmosphere, here water vapour, wind, temperature and humidity.
]

.footnote[Data: [ERA5](https://doi.org/10.1002/qj.3803) reanalysis, via [WeatherBench 2](https://github.com/google-research/weatherbench2), March 21, 2021, 00:00 UTC.]

???

What we really want is the atmosphere itself, at that same instant, in 3D. That is our state $x$. We show four of its variables, water vapour, wind, temperature and humidity. Recovering this state from observations is called data assimilation. It is the problem we will follow for the rest of the talk.

---

class: black-slide
background-image: url(figures/bh-y.png)
background-size: cover

.overlay-box.overlay-top-left[
.overlay-title[Black hole imaging]

A few radio telescopes across the Earth sample the Fourier transform $y$ of the image.
]

.footnote[Data: [EHT Collaboration](https://github.com/eventhorizontelescope/2019-D01-01), M87*, April 11, 2017.]

???

Fourth, radio astronomy. The Event Horizon Telescope combines radio telescopes all over the Earth, to image the black hole at the center of the galaxy M87. Each pair of telescopes measures one Fourier coefficient of the image. As the Earth rotates, these measurements trace these tracks. This is everything that was measured on one night in April 2017. This is the observation $y$, and most of the plane is empty.

---

class: black-slide
background-image: url(figures/bh-x.png)
background-size: cover

.overlay-box.overlay-top-left[
.overlay-title[Black hole imaging]

Images $x$ of M87*, all consistent with the data.
]

.footnote[Credits: [Wu et al](https://arxiv.org/abs/2405.18782), NeurIPS 2024 (arXiv:2405.18782).]

???

From those few measurements, we want the image of the black hole. Or rather, images, because many of them fit the same data. Here are a few, each one a possible state $x$. The ring is always there. The fine details change from one to the next.

---

class: black-slide
background-image: url(figures/lens-y.png)
background-size: cover

.overlay-box.overlay-intro-right[
.overlay-title[Gravitational lensing]

A foreground galaxy distorts a background galaxy into an Einstein ring $y$.
]

.footnote[Credits: [Adam et al](https://arxiv.org/abs/2211.03812), NeurIPS ML4PS workshop 2022 (arXiv:2211.03812).]

???

Fifth, cosmology. A massive galaxy in the foreground bends the light of a more distant galaxy into a ring, an Einstein ring. This noisy ring is the observation $y$.

---

class: black-slide
background-image: url(figures/lens-x.png)
background-size: cover

.overlay-box.overlay-intro-right[
.overlay-title[Gravitational lensing]

Undistorted images $x$ of the background galaxy, all consistent with the data.
]

.footnote[Credits: [Adam et al](https://arxiv.org/abs/2211.03812), NeurIPS ML4PS workshop 2022 (arXiv:2211.03812).]

???

What we want is the galaxy as it would look without the lens. Here again, there is not a single answer, but several plausible galaxies, each a possible state $x$. Pass any of them through the lens again, and you get back the ring we observed.

---

class: middle

.center.width-80[![](figures/setup.svg)]

## Inverse problems in science

Given noisy observations $y$, estimate the posterior distribution $$p(x|y) \propto p(x) p(y|x)$$ of latent states $x$.

???

All these examples are the same problem, and this diagram shows it.

A physical model describes the state $x$ of a system, a cell, a galaxy, the Earth. An observation model, the instrument, turns this state into the observation $y$, through a microscope, a telescope or a satellite. Both run forward, from causes to effects.

We want to go backward. Given $y$, which states $x$ could have produced it? There is no single answer, because the observation is noisy and incomplete. There is a distribution of answers, the posterior $p(x|y)$.

By Bayes' rule, the posterior combines two terms, one for each box. The prior $p(x)$ comes from the physical model. The likelihood $p(y|x)$ comes from the observation model.

---

class: middle

.grid[
.kol-1-4[&nbsp;]
.kol-3-4[.flow.flow-right[Generation]]
]

.grid[
.kol-1-4[&nbsp;]
.kol-3-8[.center[.icons[![](figures/icons/galaxie.png)![](figures/icons/globe-terrestre.png)![](figures/icons/cellule-de-plante.png)]<br>.bold[Prior] $p(x)$]]
.kol-3-8[.center[.icons[![](figures/icons/observatoire.png)![](figures/icons/satellite.png)![](figures/icons/microscope.png)]<br>.bold[Likelihood] $p(y | x)$]]
]

.recipe[
.grid[
.kol-1-4[.italic[Cryo-EM]]
.kol-3-8[.center[3D structures of molecules]]
.kol-3-8[.center[projection, microscope blur, noise]]
]

.grid[
.kol-1-4[.italic[MRI]]
.kol-3-8[.center[full-resolution scans]]
.kol-3-8[.center[undersampled Fourier, noise]]
]
.grid[
.kol-1-4[.italic[Earth observation]]
.kol-3-8[.center[3D atmospheric states]]
.kol-3-8[.center[radiative transfer]]
]
.grid[
.kol-1-4[.italic[Black hole imaging]]
.kol-3-8[.center[images of black holes]]
.kol-3-8[.center[sparse Fourier sampling, noise]]
]
.grid[
.kol-1-4[.italic[Lensing]]
.kol-3-8[.center[undistorted images of galaxies]]
.kol-3-8[.center[lensing, telescope blur, noise]]
]
]

.grid[
.kol-1-4[&nbsp;]
.kol-3-4[.flow.flow-left[Inference]]
]

???

Here are the prior and the likelihood of each example.

The likelihood is the easy part. It is the instrument, which we usually know well, a projection, a Fourier transform, a radiative transfer model, plus noise.

The prior is the hard part. It is often already available, as a scientific simulator, an ocean model, a climate model, a simulation of black holes. But a simulator is a regular computer program. It runs forward and offers no way to run it backward, conditioned on an observation. In that form, the prior is of little help for inversion.

For a given system, the two terms do not change at the same pace. The instrument changes: a new satellite, a new resolution, a new network of stations. The physics does not. The prior should be learned once, and reused with every new likelihood.

For inference, we need a representation of the prior that we can work with. Deep generative models will give us one.

---

class: middle

## Diffusion models 101

A forward diffusion process gradually turns samples $x \sim p(x)$ into noise,
$$\text{d} x\_t = f\_t x\_t \text{d}t + g\_t \text{d}w\_t.$$

.center[
.width-90[![](figures/perturb_kolmogorov.gif)]
.italic[Forward diffusion process.]
]

.footnote[Adapted from [Song](https://yang-song.net/blog/2021/score/), 2021.]

???

Diffusion models are the representation we will use. Trained on the outputs of a simulator, or on data, they learn to generate new samples of the system. And, as we will see, their way of generating can be steered by an observation.

A diffusion model is made of two parts. The first is a gradual noising process. The second is the reverse of it, which removes the noise.

The first part is easy. Starting from a sample of the data, we add a little noise, then a little more, until nothing but noise remains. This is described by a stochastic differential equation, where $x\_t$ is the perturbed sample at time $t$. On the left, the flow of the opening slides dissolves into noise. On the right, the same process on a simple 1D distribution, two modes that slowly merge into a single Gaussian.

---

class: middle

The reverse process is also a diffusion, driven by the .bold[score] $\nabla\_{x\_t} \log p(x\_t)$,
$$\text{d}x\_t = \left[ f\_t x\_t - g\_t^2 \nabla\_{x\_t} \log p(x\_t) \right] \text{d}t + g\_t \text{d}w\_t.$$
Simulating it from noise $x\_1$ to $t = 0$ generates samples $x\_0 \sim p(x)$.

.center[
.width-90[![](figures/denoise_kolmogorov.gif)]
.italic[Reverse denoising process.]
]

.footnote[Adapted from [Song](https://yang-song.net/blog/2021/score/), 2021.]

???

The second part runs this process backward in time. The reverse is again a stochastic differential equation, and it involves one new quantity, the score of the noisy data at each time $t$.

And this is how we generate data. We start from pure noise, a random draw that carries no information at all. Then we run the reverse process, step by step, back to $t = 0$. The noise is gradually removed, structure appears, and a flow emerges.

This flow never existed. It is not a copy of a training example. It is a new sample, drawn from the distribution of all flows the model has learned. Every run starts from different noise, and gives a different, plausible flow.

That is exactly what we wanted from a prior. A way to draw plausible states of the system, as many as we want.

---

class: middle

.center.width-90[![](figures/denoiser.svg)]

The score is unknown, but can be approximated via a neural denoiser $d\_\theta(x\_t, t)$ trained to recover $x$ from $x\_t$,
$$\min\_\theta \\, \mathbb{E}\_{p(t)p(x)p(x\_t|x)} \left[ || d\_\theta(x\_t, t) - x ||^2\_2 \right].$$
The optimal denoiser is $\mathbb{E}[x | x\_t]$, which gives the score by Tweedie's formula,
$$\nabla\_{x\_t} \log p(x\_t) = \Sigma\_t^{-1}(\mathbb{E}[x | x\_t] - x\_t) \approx \Sigma\_t^{-1}(d\_\theta(x\_t, t) - x\_t) = s\_\theta(x\_t, t).$$

???

There is one catch. The reverse process needs the score, and we do not know it.

We can approximate the score via a neural network trained to denoise. We take a sample, add noise to it at some level $t$, and ask the network to recover the clean sample. The network sees the noisy flow and the noise level, and returns its best guess of the clean flow. We repeat this for all noise levels.

The best possible denoiser returns the average of all clean samples compatible with the noisy one. And a classical result, Tweedie's formula, turns this average into the score. So a good denoiser gives us the score, and the score gives us the reverse process.

---

class: middle

<div class="step">
<div><img src="figures/loop/xt.png">$x_t$</div>
<div class="arrow">$\xrightarrow{\;\text{denoise}\;}$</div>
<div><img src="figures/loop/xhat.png">$\hat{x}$</div>
<div class="arrow">$\xrightarrow{\;\text{renoise}\;}$</div>
<div><img src="figures/loop/xt1.png">$x_s$</div>
</div>

In practice, the reverse process is simulated in a few dozen steps, from $t = 1$ down to $t = 0$. Each step, from $t$ to the next time $s < t$, denoises the current state with the score, by Tweedie's formula,
$$\hat{x} = x\_t + \Sigma\_t \, s\_\theta(x\_t, t),$$
then renoises it to the lower noise level, by sampling the Gaussian
$$x\_s \sim p(x\_s \mid x\_t, x = \hat{x}).$$

???

In practice, we do not solve the reverse equation exactly. We discretize it into a few dozen noise levels, and each step does two things. First, it uses the score to compute the best guess $\hat{x}$ of the clean state. By Tweedie's formula, this is the output of the denoiser. We write it with the score, because the score is what we will modify. Then, it adds noise back, at a lower level, by sampling the Gaussian of the next noisy state given the current one and the guess. This Gaussian is known in closed form. For a diffusion $x\_t = x + \epsilon$, with $\epsilon \sim \mathcal{N}(0, \Sigma\_t)$, its mean is $\hat{x} + \Sigma\_s \Sigma\_t^{-1}(x\_t - \hat{x})$ and its covariance $\Sigma\_s - \Sigma\_s \Sigma\_t^{-1} \Sigma\_s$. Repeated, these two steps simulate the reverse equation of the previous slide. The images above are one such step.

That is the whole sampler. A short loop, around a network that was trained once and is never modified. The network belongs to whoever trained it. The loop is ours, and we can change it as we like. The rest of the talk is about what to put in it.

---

class: middle

## Retrain...

.center.width-90[![](figures/denoiser-y.svg)]

To sample from the posterior $p(x|\textcolor{#d62728}{y})$, one can .bold[hard-wire] the observation $\textcolor{#d62728}{y}$ as an additional input of the denoiser $d\_\theta(x\_t, t, \textcolor{#d62728}{y})$ and train it on pairs $(x, \textcolor{#d62728}{y})$.

.alert[Every new instrument requires training a new network.]

???

Back to inverse problems. We want a diffusion model that gives us samples of $x$ given $y$.

The direct approach feeds $y$ to the denoiser as an extra input, here the coarse observation of the opening slide, and trains it on pairs of $x$ and $y$. This works, but the network is then tied to one instrument. Change the instrument, its resolution or its noise, and the network must be trained again.

---

class: middle

## ... or harness

.center.width-10[![](figures/icons/remote-control.png)]

Instead, we keep the pretrained model and .bold[harness] its sampling. Since
$$\nabla\_{x\_t} \log p(x\_t | \textcolor{#d62728}{y}) = \nabla\_{x\_t} \log p(x\_t) + \nabla\_{x\_t} \log p(\textcolor{#d62728}{y} | x\_t),$$
it suffices to add the likelihood score to the prior score in the denoising step,
$$\hat{x} = x\_t + \Sigma\_t \big( \underbrace{s\_\theta(x\_t, t)}\_{\text{pretrained prior}} + \underbrace{\textcolor{#d62728}{\nabla\_{x\_t} \log p(y | x\_t)}}\_{\text{likelihood}} \big),$$
and to renoise as before. The loop then produces posterior samples $x \sim p(x | \textcolor{#d62728}{y})$, and the network is never retrained.

???

There is a better way, and it is the main idea of this talk. We do not retrain anything. We harness the pretrained model instead.

By Bayes' rule, the score of the posterior is the score of the prior plus the score of the likelihood. The prior score comes from the pretrained diffusion model. The likelihood score comes from the model of the instrument.

So we go back to the sampling step of a few slides ago and change one term. In the denoising step, we add the likelihood score to the prior score. The renoising step does not change. The loop now produces posterior samples. Equivalently, the reverse equation is driven by the score of the posterior instead of the score of the prior.

The network is untouched. Change the instrument, and only the red term changes. The same prior serves any instrument, zero-shot. Few generative models can be conditioned this simply. Diffusion models can.

There is one catch. The likelihood score of a noisy state is intractable.

---

class: middle

.avatars[![](figures/faces/frozet.jpg)![](figures/faces/gerome.jpg)![](figures/faces/francois_lanusse.jpg)]

## The likelihood score

The likelihood of a noisy state,
$$p(y | x\_t) = \int p(y | x) p(x | x\_t) \text{d}x,$$
is intractable.

MMPS approximates $p(x | x\_t)$ by a Gaussian, with Tweedie's covariance,
$$p(x | x\_t) \approx \mathcal{N}\big(x \mid \mathbb{E}[x | x\_t], \mathbb{V}[x | x\_t]\big), \quad \mathbb{V}[x | x\_t] = \Sigma\_t \nabla\_{x\_t} \mathbb{E}[x | x\_t].$$
For $p(y | x) = \mathcal{N}(y | Ax, \Sigma\_y)$,
$$\textcolor{#d62728}{\nabla\_{x\_t} \log p(y | x\_t)} \approx \nabla\_{x\_t} \mathbb{E}[x | x\_t]^\top A^\top \big(\Sigma\_y + A \mathbb{V}[x | x\_t] A^\top\big)^{-1} \big(y - A \mathbb{E}[x | x\_t]\big).$$

.footnote[Credits: [Rozet et al](https://arxiv.org/abs/2405.13712), NeurIPS 2024 (arXiv:2405.13712). DPS: [Chung et al](https://arxiv.org/abs/2209.14687), ICLR 2023.]

???

The likelihood of a noisy state averages the likelihood of the clean state over all clean states compatible with the noisy one. This integral is intractable.

The simplest approximation, DPS, replaces this distribution by a single point, the output of the denoiser. At high noise, this point is a poor summary. Many clean states are compatible with the noisy one, and DPS keeps only their average.

Our approximation, MMPS, keeps the uncertainty. It replaces the distribution by a Gaussian. The mean is the output of the denoiser. The covariance is given by the second-order Tweedie formula, the Jacobian of the denoiser. For a Gaussian instrument, the likelihood of the noisy state is then Gaussian too, and its score has this closed form.

The covariance has as many entries as the state squared, and we never build it. We only need its products with vectors, which automatic differentiation gives for the cost of a backward pass. A few iterations of conjugate gradient solve the system.

This assumes a Gaussian likelihood and a linear instrument, or one we can linearize. We will come back to this assumption at the end of the talk.

---

class: black-slide
background-image: url(figures/satellite-crop.gif)
background-size: cover

.overlay-box.overlay-bottom-left[
.overlay-title[Observations $y$]

Every day, satellites and ground stations deliver millions of sparse, noisy and indirect measurements of the atmosphere.
]

.footnote[Animation: [ESA/ATG medialab](https://www.esa.int/ESA_Multimedia), Sentinel-1.]

???

Our third example is the atmosphere as a whole. Every day, satellites and weather stations deliver millions of observations. They are sparse, noisy and indirect, and they keep arriving over time. This is $y$.

---

class: black-slide
background-image: url(figures/da-x.png)
background-size: cover

.overlay-box.overlay-bottom-right[
.overlay-title[Trajectories $x\_{1:L}$]

Reanalyses of the past and the initial conditions of every weather forecast require the full state of the atmosphere, estimated from these observations.
]

.footnote[Data: [ERA5](https://doi.org/10.1002/qj.3803) reanalysis, 10 m wind speed, March 21, 2021.]

???

From all these observations, we want to reconstruct the atmosphere itself, in 3D and over time, as a trajectory. Here you see one moment of it, through the surface wind. Estimating it from observations is data assimilation. It produces the reanalyses that climate science relies on, and the starting point of every weather forecast.

---

class: middle

## Data assimilation

We estimate trajectories $x\_{1:L}$ given observations $y\_{1:L}$, as the posterior
$$p(x\_{1:L} | y\_{1:L}) \propto p(x\_1) p(y\_1 | x\_1) \prod\_{i=2}^{L} p(x\_{i} | x\_{i-1}) p(y\_{i} | x\_{i}).$$

.center.width-100[![](figures/dynamical.svg)]

???

Formally, the atmosphere evolves from one state to the next, following a transition model, and each state is observed through an observation model. Data assimilation is the posterior over whole trajectories, given all observations.

This problem is as old as numerical weather prediction. The methods used operationally today, such as 4D-Var and ensemble Kalman filters, rely on Gaussian or linear assumptions about the dynamics.

In our group, we asked whether a diffusion prior over trajectories, which makes no such assumption, could do the job. The next slides show how we did it, in three steps.

---

class: middle

.avatars[![](figures/faces/francois.jpg)]

.center.width-100[![](figures/sda.svg)]

SDA trains a diffusion model on short windows. If the dynamics are Markovian,
$$\nabla\_{x\_i} \log p(x\_{1:L}) = \nabla\_{x\_i} \log p(x\_{i-k:i+k}),$$
and approximately so for noisy $x\_{1:L}(t)$. The score of a long trajectory is thus assembled from short windows, and posterior sampling proceeds as before.

.footnote[Credits: [Rozet and Louppe](https://arxiv.org/abs/2306.10574), NeurIPS 2023 (arXiv:2306.10574).]

???

The first step is our score-based data assimilation, SDA. We train a diffusion model on short windows of a trajectory. Because the dynamics are Markovian, each state only interacts with its close neighbors in time. So the score of a long trajectory can be assembled from the scores of short windows, all computed in parallel. This is exact for clean trajectories, and approximate for noisy ones. The rest is the recipe we already know. We add the likelihood score of the observations, and the trajectories we sample become posterior trajectories, without retraining anything.

---

class: middle

.avatars[![](figures/faces/francois.jpg)]

.center.width-100[![](figures/sda1-0.png)]

.center[Ground truth $x\_{1:L}$ and coarse, noisy, sparse observations $y$.]

.footnote[Credits: [Rozet and Louppe](https://arxiv.org/abs/2306.10574), NeurIPS 2023 (arXiv:2306.10574).]

???

A toy example, a 2D turbulent flow. The top row is the true trajectory. The second row shows what we observe, coarse, noisy, and only every few time steps.

---

class: middle
count: false

.avatars[![](figures/faces/francois.jpg)]

.center.width-100[![](figures/sda1.png)]

.center[Posterior samples of the trajectory, given $y$.]

.footnote[Credits: [Rozet and Louppe](https://arxiv.org/abs/2306.10574), NeurIPS 2023 (arXiv:2306.10574).]

???

And these are posterior samples. They are consistent with the observations, and they differ where the observations leave room.

---

class: middle

.avatars[![](figures/faces/fanny.jpg)![](figures/faces/gerome.jpg)![](figures/faces/frozet.jpg)]

## Long trajectories

Training a diffusion model on whole trajectories $x\_{1:L}$ is too expensive for long horizons. Instead, models of short windows $x\_{i-k:i+k}$ must be composed at sampling time.

.center.width-100[![](figures/gibbs-strategies.png)]

GiBBS redraws blocks $x\_{i:j}$ from their exact conditionals $p(x\_{i:j} | x\_{i-k:i-1}, x\_{j+1:j+k}, y)$, in parallel. Unlike AR and AAO (SDA), it converges to $p(x\_{1:L} | y)$.

.footnote[Credits: Bodart et al, under review at ICLR 2027.]

???

For long trajectories, such as a whole season, we cannot train a model over the whole horizon. We must compose short windows at sampling time, and how we compose them matters.

Rolling out one window after the other ignores future observations, and errors accumulate. Composing all windows at once, as SDA does, has a subtler problem. Each window only sees its neighbors, so the information brought by an observation at one time step does not travel far enough. It fails to reach states far in the past or far in the future, where it should still matter.

Our new solution, GiBBS, goes back to an old idea, Gibbs sampling. It repeatedly redraws blocks of states, given their neighbors and the observations. All blocks of the same color are redrawn in parallel, and the blocks shift from one cycle to the next. Over the cycles, the information of each observation propagates along the whole trajectory, and the chain converges to the true posterior.

---

class: middle

.avatars[![](figures/faces/fanny.jpg)![](figures/faces/gerome.jpg)![](figures/faces/frozet.jpg)]

.center.width-100[![](figures/gibbs-kolmogorov.png)]

.center[Posterior samples of the trajectory, given $y$.]

.footnote[Credits: Bodart et al, under review at ICLR 2027.]

???

As an example, we go back to the turbulent flow, with observations that only cover the middle of the trajectory. GiBBS keeps the vortices coherent all along. The all-at-once composition smooths them out, and the rollout drifts away.

So far, every state was a small 2D flow, a few thousand numbers. With SDA and GiBBS, we can now handle long trajectories of them. But the real atmosphere is not a small 2D flow.

---

class: black-slide
background-image: url(figures/earth-bg.png)
background-size: cover

.overlay-box.overlay-bottom-right[
.overlay-title[$O(10^{10})$ variables]

At 0.25°, 6 variables on 13 pressure levels, hourly over two weeks, a trajectory $x\_{1:L}$ has $721 \times 1440 \times 6 \times 13 \times 24 \times 14 \approx 27 \times 10^9$ variables.
]

???

At the resolution of modern weather models, a two-week trajectory of the atmosphere has about 27 billion variables. That is far beyond what a diffusion model can handle directly.

---

class: middle

.avatars[![](figures/faces/frozet.jpg)![](figures/faces/ruben_ohana.jpg)![](figures/faces/michael_mccabe.jpg)![](figures/faces/francois_lanusse.jpg)![](figures/faces/shirley_ho.jpg)]

## Latent diffusion

.center.width-95[![](figures/lola.svg)]

.grid[
.kol-3-4[
.center[
<video poster="figures/videos/lola_euler_poster.jpg" controls="" muted="" loop="" width="100%" autoplay>
        <source src="figures/videos/lola_euler.mp4" type="video/mp4">
</video>
]
]
.kol-1-4[<br><br>LDMs trained on compressed latent states $z = E(x)$ remain accurate even at high compression rates.]
]

.footnote[Credits: [Rozet et al](https://arxiv.org/abs/2507.02608), NeurIPS 2025 (arXiv:2507.02608).]

???

So we compress. A latent diffusion model learns the prior in a compressed space, much smaller than the original one, and decodes its samples back. Our work on LoLA showed that this works well for physics, even at high compression. This was a surprise. Physics is defined in the original space, through equations on the full fields, and we expected compression to break it. It does not. The latent space retains what matters for the dynamics.

---

class: middle

.avatars[![](figures/faces/gerome.jpg)![](figures/faces/sacha.jpg)![](figures/faces/frozet.jpg)![](figures/faces/victor.jpg)![](figures/faces/omer.jpg)![](figures/faces/mathias.jpg)![](figures/faces/elise.jpg)]

## Appa

.center.width-80[![](figures/appa.png)]

An autoencoder compresses each atmospheric state $x$ 450 times into a latent state $z = E(x)$. A latent diffusion model generates trajectories $z\_{1:L}$, decoded as $x\_{1:L} = D(z\_{1:L})$. Posterior sampling runs in latent space.

.footnote[Credits: [Andry et al](https://arxiv.org/abs/2504.18720), NeurIPS ML4PS workshop 2025 (arXiv:2504.18720).]

???

Based on this idea, we built Appa, for the global atmosphere. An autoencoder compresses each state 450 times. A latent diffusion model, with a billion parameters, generates trajectories in that compressed space. Data assimilation then happens in latent space, at the scale of the whole Earth.

---

class: middle

.avatars[![](figures/faces/gerome.jpg)![](figures/faces/sacha.jpg)![](figures/faces/frozet.jpg)![](figures/faces/victor.jpg)![](figures/faces/omer.jpg)![](figures/faces/mathias.jpg)![](figures/faces/elise.jpg)]

.center[
<video poster="figures/videos/appa_reanalysis_poster.jpg" controls="" muted="" loop="" width="70%" autoplay>
<source src="figures/videos/appa_reanalysis_1week.mp4" type="video/mp4">
</video>
]

.footnote[Credits: [Andry et al](https://arxiv.org/abs/2504.18720), NeurIPS ML4PS workshop 2025 (arXiv:2504.18720).]

???

What Appa produces are, in effect, videos of the atmosphere. Each frame is the state of the whole planet at one hour, and the video is generated so that it agrees with everything we observed along the way.

Here is one week. Rows 1 and 4 are the truth. Rows 2 and 5 are the observations, satellite tracks and weather stations, sparse and scattered. Rows 3 and 6 are Appa's videos, filled in everywhere, and consistent with those observations.

---

class: middle

## Conclusions

.grid[
.kol-1-3[.center[.bold[Hypoxia]<br>.smaller[Satellites detect a third of summer hypoxic events in the Black Sea, from the surface alone.]]]
.kol-1-3[.center[.bold[Downscaling]<br>.smaller[Kilometer-scale weather for Belgium, in seconds, anchored to ground stations.]]]
.kol-1-3[.center[.bold[Data assimilation]<br>.smaller[Global reanalyses from sparse observations, and data assimilation with existing forecasters.]]]
]

.challenge[
- Can we trust a posterior when there is no ground truth to compare with?
- What happens when the prior was learned from imperfect simulations?
- Can priors be learned from noisy observations alone?
- Can we sample $10^{10}$ variables as fast as the weather changes?
]

???

Let me come back to the three examples.

In the Black Sea, satellites alone can now detect a third of the summer hypoxic events. Over Belgium, we get kilometer-scale weather in seconds, as an ensemble, and anchored to weather stations. And for the whole atmosphere, we can reconstruct the past from sparse observations, and turn existing forecasters into data assimilation systems.

None of this is finished. Four questions keep us busy.

Can we trust the posteriors? In science, we rarely know the true state, so we need ways to check that the uncertainty we report is the right one.

What if the prior is wrong? A prior learned from a simulator inherits its biases, and the posterior can then be confidently wrong.

Can we do without simulators? In some fields, we only have noisy and incomplete observations. Learning the prior directly from them is possible, and we have started to do it.

And can we go fast enough? Weather centers assimilate hundreds of millions of observations every few hours. Our methods are not there yet.

---

class: black-slide
background-image: url(figures/closing.png)
background-size: cover

.overlay-box.overlay-center.overlay-equation[
$$p(x | y) \propto p(x) \, p(y | x)$$
]

???

I will leave you with the equation we started from.

Molecules, knees, black holes, galaxies, the Black Sea, the rain over Belgium, the whole atmosphere. Very different problems, but always the same recipe. A prior for the physics of the system, learned by a diffusion model. A likelihood for the instrument. And posterior sampling, which combines them.

Thank you.

---

count: false

.center.width-10[![](figures/icons/high-five.png)]

.center[

.width-13.circle[![](figures/faces/frozet.jpg)] 
.width-13.circle[![](figures/faces/gerome.jpg)] 
.width-13.circle[![](figures/faces/fanny.jpg)] 
.width-13.circle[![](figures/faces/thomas.jpg)] 
.width-13.circle[![](figures/faces/omer.jpg)]

.width-13.circle[![](figures/faces/victor.jpg)] 
.width-13.circle[![](figures/faces/elise.jpg)] 
.width-13.circle[![](figures/faces/sacha.jpg)] 
.width-13.circle[![](figures/faces/mathias.jpg)]

.width-13.circle[![](figures/faces/francois_lanusse.jpg)] 
.width-13.circle[![](figures/faces/ruben_ohana.jpg)] 
.width-13.circle[![](figures/faces/michael_mccabe.jpg)] 
.width-13.circle[![](figures/faces/shirley_ho.jpg)]

.smaller[François Rozet, Gérôme Andry, Fanny Bodart, Thomas Savary, Omer Rochman, Victor Mangeleer, Elise Faulx, Sacha Lewin, Matthias Pirlet, François Lanusse, Ruben Ohana, Michael McCabe, Shirley Ho]

]

---

class: middle, center, end-slide
count: false

The end.
