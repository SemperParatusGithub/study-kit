# Golden math corpus

Every formula here must render in KaTeX (strict) and convert through pandoc to Typst and
compile without a single warning. This is the math dialect authors may use; see
`docs/architecture.md` §2.3. Constructs that fail in either engine live in
`math-denied.md` instead.

## Arithmetic, fractions, roots

$$
\frac{a+b}{c-d} \quad \tfrac{1}{2} \quad \dfrac{x}{y}
$$

$$
\sqrt{2} \quad \sqrt[3]{x^2+1} \quad \frac{1}{\sqrt{2}} \approx 0{,}707
$$

$$
3{,}3\,\mathrm{k\Omega} + 470\,\Omega = 3{,}77\,\mathrm{k\Omega}
$$

$$
1{,}5 \cdot 10^{-3}\,\mathrm{A} = 1{,}5\,\mathrm{mA}
$$

$$
f_\mathrm{g} = \frac{1}{2\pi RC} \approx 1{,}59\,\mathrm{kHz}
$$

$$
\binom{n}{k} = \frac{n!}{k!\,(n-k)!}
$$

$$
a \pm b \quad a \mp b \quad a \times b \quad a \cdot b \quad a / b \quad a \div b
$$

## Relations and logic

$$
a \approx b \quad a \neq b \quad a \leq b \quad a \geq b \quad a \ll b \quad a \gg b \quad a \propto b \quad a \equiv b \quad a \sim b
$$

$$
A \Rightarrow B \quad A \Leftrightarrow B \quad x \to \infty \quad x \mapsto x^2 \quad A \Leftarrow B
$$

$$
\forall x \in \mathbb{R}\colon\ \exists n \in \mathbb{N} \text{ mit } n > x
$$

$$
A \cup B \quad A \cap B \quad A \subset B \quad A \subseteq B \quad \emptyset \quad x \notin A
$$

$$
f\colon \mathbb{R} \to \mathbb{C}, \quad \mathbb{Z} \subset \mathbb{Q} \subset \mathbb{R}
$$

## Greek and accents

$$
\alpha\,\beta\,\gamma\,\delta\,\varepsilon\,\zeta\,\eta\,\vartheta\,\lambda\,\mu\,\nu\,\xi\,\pi\,\rho\,\sigma\,\tau\,\varphi\,\chi\,\psi\,\omega
$$

$$
\Gamma\,\Delta\,\Theta\,\Lambda\,\Xi\,\Pi\,\Sigma\,\Phi\,\Psi\,\Omega
$$

$$
\hat{x} \quad \bar{x} \quad \tilde{x} \quad \dot{x} \quad \ddot{x} \quad \vec{F} \quad \overline{AB}
$$

$$
\underline{U} = \hat{U}\,\mathrm{e}^{\mathrm{j}\varphi_u}
$$

$$
\underline{Z}^* = R - \mathrm{j}X
$$

## Complex AC analysis

$$
\underline{Z}_C = \frac{1}{\mathrm{j}\omega C}, \qquad \underline{Z}_L = \mathrm{j}\omega L
$$

$$
\underline{H}(\mathrm{j}\omega) = \frac{1}{1 + \mathrm{j}\omega RC}
$$

$$
|\underline{H}(\mathrm{j}\omega)| = \frac{1}{\sqrt{1 + (\omega RC)^2}}, \qquad \arg \underline{H} = -\arctan(\omega RC)
$$

$$
\underline{S} = \underline{U}\,\underline{I}^* = P + \mathrm{j}Q, \qquad |\underline{S}| = \sqrt{P^2 + Q^2}
$$

$$
\cos\varphi = \frac{P}{|\underline{S}|}
$$

$$
U_\mathrm{eff} = \frac{\hat{u}}{\sqrt{2}} = \sqrt{\frac{1}{T}\int_0^T u^2(t)\,\mathrm{d}t}
$$

$$
\mathrm{Re}\{\underline{Z}\} = R, \qquad \mathrm{Im}\{\underline{Z}\} = X
$$

$$
\underline{Z} = |\underline{Z}|\,\mathrm{e}^{\mathrm{j}\varphi} = |\underline{Z}| \angle \varphi
$$

$$
R_\mathrm{ges} = R_1 \parallel R_2 = \frac{R_1 R_2}{R_1 + R_2}
$$

$$
U_2 = U_0 \cdot \frac{R_2}{R_1 + R_2}
$$

$$
L_\mathrm{dB} = 20\log_{10}\left|\underline{H}\right|\,\mathrm{dB}, \qquad 20\log_{10}\frac{1}{\sqrt{2}} \approx -3{,}01\,\mathrm{dB}
$$

$$
\omega_0 = \frac{1}{\sqrt{LC}}, \qquad Q = \frac{1}{R}\sqrt{\frac{L}{C}}
$$

## DC networks

$$
\sum_{k=1}^{n} I_k = 0, \qquad \sum_{k=1}^{m} U_k = 0
$$

$$
P = U I = I^2 R = \frac{U^2}{R}
$$

$$
\eta = \frac{P_\mathrm{ab}}{P_\mathrm{zu}} \cdot 100\,\%
$$

$$
\begin{pmatrix} G_{11} & -G_{12} \\ -G_{21} & G_{22} \end{pmatrix}
\begin{pmatrix} \varphi_1 \\ \varphi_2 \end{pmatrix} =
\begin{pmatrix} I_{q1} \\ I_{q2} \end{pmatrix}
$$

$$
\mathbf{G}\,\boldsymbol{\varphi} = \mathbf{i}_q
$$

## Calculus

$$
\frac{\mathrm{d}}{\mathrm{d}t}\,u_C(t) = \frac{1}{C}\,i_C(t)
$$

$$
\frac{\partial f}{\partial x} \quad \frac{\partial^2 f}{\partial x\,\partial y} \quad \nabla f \quad \Delta f = \nabla^2 f
$$

$$
\int_0^\infty \mathrm{e}^{-st}\,\mathrm{d}t = \frac{1}{s}, \qquad \operatorname{Re}\{s\} > 0
$$

$$
\oint_{\partial A} \vec{E} \cdot \mathrm{d}\vec{s} = -\frac{\mathrm{d}}{\mathrm{d}t}\iint_A \vec{B} \cdot \mathrm{d}\vec{A}
$$

$$
\lim_{x \to 0} \frac{\sin x}{x} = 1
$$

$$
\left.\frac{\mathrm{d}u}{\mathrm{d}t}\right|_{t=0} = \frac{U_0}{\tau}
$$

$$
u_C(t) = U_0\left(1 - \mathrm{e}^{-t/\tau}\right), \qquad \tau = RC
$$

$$
\prod_{k=1}^{n} k = n!, \qquad \sum_{n=0}^{\infty} \frac{x^n}{n!} = \mathrm{e}^x
$$

$$
f(x) \approx f(x_0) + f'(x_0)(x - x_0) + \frac{f''(x_0)}{2}(x - x_0)^2
$$

$$
\nabla \times \vec{H} = \vec{J} + \frac{\partial \vec{D}}{\partial t}, \qquad \nabla \cdot \vec{B} = 0
$$

## Signals and systems

$$
X(\mathrm{j}\omega) = \int_{-\infty}^{\infty} x(t)\,\mathrm{e}^{-\mathrm{j}\omega t}\,\mathrm{d}t
$$

$$
X(s) = \mathcal{L}\{x(t)\} = \int_0^\infty x(t)\,\mathrm{e}^{-st}\,\mathrm{d}t
$$

$$
x(t) \;\circ\!-\!\bullet\; X(s)
$$

$$
y(t) = (x * h)(t) = \int_{-\infty}^{\infty} x(\tau)\,h(t - \tau)\,\mathrm{d}\tau
$$

$$
X[k] = \sum_{n=0}^{N-1} x[n]\,\mathrm{e}^{-\mathrm{j}2\pi kn/N}
$$

$$
\varepsilon(t) = \begin{cases} 0 & t < 0 \\ 1 & t \geq 0 \end{cases}
$$

$$
\delta(t) = \frac{\mathrm{d}\varepsilon(t)}{\mathrm{d}t}, \qquad \int_{-\infty}^{\infty} \delta(t)\,\mathrm{d}t = 1
$$

$$
G(s) = \frac{K}{(1 + sT_1)(1 + sT_2)}
$$

$$
H(z) = \frac{\sum_{k=0}^{M} b_k z^{-k}}{1 + \sum_{k=1}^{N} a_k z^{-k}}
$$

$$
T(s) = \frac{G(s)}{1 + G(s)H(s)}
$$

$$
x(t) = \sum_{k=-\infty}^{\infty} c_k\,\mathrm{e}^{\mathrm{j}k\omega_0 t}, \qquad c_k = \frac{1}{T}\int_{0}^{T} x(t)\,\mathrm{e}^{-\mathrm{j}k\omega_0 t}\,\mathrm{d}t
$$

$$
\mathrm{si}(x) = \frac{\sin x}{x}
$$

## Multi-line

$$
\begin{aligned}
\underline{Z} &= R + \mathrm{j}\omega L + \frac{1}{\mathrm{j}\omega C} \\
&= R + \mathrm{j}\left(\omega L - \frac{1}{\omega C}\right)
\end{aligned}
$$

$$
\begin{aligned}
I_1 + I_2 - I_3 &= 0 \\
R_1 I_1 - R_2 I_2 &= U_{q1} - U_{q2} \\
R_2 I_2 + R_3 I_3 &= U_{q2}
\end{aligned}
$$

$$
\begin{gathered}
\nabla \cdot \vec{D} = \rho \\
\nabla \times \vec{E} = -\frac{\partial \vec{B}}{\partial t}
\end{gathered}
$$

$$
|x| = \begin{cases} x & \text{für } x \geq 0 \\ -x & \text{sonst} \end{cases}
$$

## Linear algebra

$$
\mathbf{A} = \begin{bmatrix} a_{11} & a_{12} \\ a_{21} & a_{22} \end{bmatrix}, \qquad \mathbf{A}^{-1} = \frac{1}{\det \mathbf{A}}\begin{bmatrix} a_{22} & -a_{12} \\ -a_{21} & a_{11} \end{bmatrix}
$$

$$
\det \mathbf{A} = \left|\begin{matrix} a & b \\ c & d \end{matrix}\right| = ad - bc
$$

$$
\begin{pmatrix} a_{11} & \cdots & a_{1n} \\ \vdots & \ddots & \vdots \\ a_{m1} & \cdots & a_{mn} \end{pmatrix}
$$

$$
\mathbf{v} = \begin{Bmatrix} x \\ y \end{Bmatrix}
$$

$$
\vec{a} \cdot \vec{b} = |\vec{a}|\,|\vec{b}| \cos\angle(\vec{a}, \vec{b}), \qquad \lVert \vec{x} \rVert_2 = \sqrt{\sum_i x_i^2}
$$

$$
\mathbf{A}^\mathrm{T}, \qquad \mathbf{x}^\mathrm{T}\mathbf{A}\mathbf{x} > 0
$$

$$
\lambda_{1,2} = -\delta \pm \sqrt{\delta^2 - \omega_0^2}
$$

## Functions and operators

$$
\sin x \quad \cos x \quad \tan x \quad \arcsin x \quad \arccos x \quad \arctan x \quad \sinh x \quad \cosh x \quad \tanh x
$$

$$
\ln x \quad \log x \quad \log_2 x \quad \exp(x) \quad \max_{t} u(t) \quad \min_{t} u(t) \quad \sup_n a_n
$$

$$
\lfloor x \rfloor \quad \lceil x \rceil \quad a \bmod n \quad a \equiv b \pmod{n}
$$

$$
\operatorname{sgn}(x) \quad \operatorname{rect}(t) \quad \operatorname{arg}(z)
$$

$$
\left( \frac{a}{b} \right) \quad \left[ \frac{a}{b} \right] \quad \left\{ \frac{a}{b} \right\} \quad \left| \frac{a}{b} \right|
$$

$$
\langle x, y \rangle \quad \lvert x \rvert \quad \lVert x \rVert
$$

## Physics and units

$$
F = q\,(\vec{E} + \vec{v} \times \vec{B})
$$

$$
\varepsilon_0 \approx 8{,}854 \cdot 10^{-12}\,\frac{\mathrm{A\,s}}{\mathrm{V\,m}}, \qquad \mu_0 = 4\pi \cdot 10^{-7}\,\frac{\mathrm{V\,s}}{\mathrm{A\,m}}
$$

$$
C = \varepsilon_0 \varepsilon_\mathrm{r} \frac{A}{d}
$$

$$
W = \frac{1}{2} C U^2 = \frac{1}{2} L I^2
$$

$$
\vartheta = 25\,^\circ\mathrm{C}, \qquad \varphi = 45^\circ
$$

$$
v = 3 \cdot 10^8\,\mathrm{m/s}, \qquad a = 9{,}81\,\mathrm{m\,s^{-2}}
$$

$$
\sigma = \frac{F}{A}, \qquad \varepsilon = \frac{\Delta l}{l_0}, \qquad \sigma = E\,\varepsilon
$$

$$
M = F \cdot r \cdot \sin\alpha, \qquad P = M \cdot \omega = 2\pi n M
$$

## Digital and probability

$$
Y = \overline{A \cdot B} = \overline{A} + \overline{B}
$$

$$
(1011)_2 = 1 \cdot 2^3 + 0 \cdot 2^2 + 1 \cdot 2^1 + 1 \cdot 2^0 = (11)_{10}
$$

$$
P(A \mid B) = \frac{P(B \mid A)\,P(A)}{P(B)}
$$

$$
\mathrm{E}[X] = \sum_i x_i\,p_i, \qquad \mathrm{Var}(X) = \mathrm{E}[X^2] - \mathrm{E}[X]^2
$$

$$
f(x) = \frac{1}{\sigma\sqrt{2\pi}}\,\mathrm{e}^{-\frac{(x-\mu)^2}{2\sigma^2}}
$$

## Spacing and text

$$
a\,b \quad a\;b \quad a\!b \quad a\ b \quad a\quad b \quad a\qquad b
$$

$$
U = R \cdot I \quad \text{(Ohmsches Gesetz)}
$$

$$
\text{Spannungsabfall über } R_2\text{: } U_2 = 4{,}5\,\mathrm{V}
$$

$$
x_{1,2} = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
$$

$$
\underbrace{R_1 + R_2}_{R_\mathrm{s}} \cdot I
$$

$$
\overbrace{a + b + c}^{3\ \text{Terme}}
$$

$$
\boxed{f_\mathrm{g} = \frac{1}{2\pi RC}}
$$

$$
\mathcal{F}\{x(t)\} \quad \mathcal{O}(n \log n) \quad \mathbb{E} \quad \mathfrak{g}
$$

$$
\phantom{x} y \quad x^{2^{n}} \quad x_{i_j} \quad {}^{14}\mathrm{C}
$$

## Inline math in prose

Die Grenzfrequenz $f_\mathrm{g} = 1/(2\pi RC)$ liegt bei $1{,}59\,\mathrm{kHz}$, und die
Phase beträgt dort $-45^\circ$. Für $\omega \to \infty$ gilt $|\underline{H}| \to 0$.

Ein Widerstand von $R = 1\,\mathrm{k\Omega}$ und $C = 100\,\mathrm{nF}$ ergeben
$\tau = RC = 0{,}1\,\mathrm{ms}$; nach $5\tau$ ist der Kondensator praktisch geladen.

Mit $\underline{U} = 230\,\mathrm{V} \angle 0^\circ$ und $\underline{I} = 2\,\mathrm{A} \angle -30^\circ$
folgt $P = 398{,}4\,\mathrm{W}$.

Die Matrix $\mathbf{A} \in \mathbb{R}^{n \times n}$ ist invertierbar, wenn $\det \mathbf{A} \neq 0$ gilt.
