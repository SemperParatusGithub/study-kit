# Denied math: each construct must still FAIL in KaTeX or in pandoc -> Typst

If `studykit golden` reports that one of these now works, the toolchain changed: review
the denylist in `docs/architecture.md` §2.3 before allowing it. Constructs that convert
*silently wrong* (they pass both engines) are enforced by the math lint instead; see
§2.3 "Verified in Phase 1".

$$
\textcolor{red}{x}
$$

$$
x = 1 \label{eq:a}
$$

$$
\eqref{eq:a}
$$

$$
\ref{eq:a}
$$

$$
\begin{vmatrix} a & b \\ c & d \end{vmatrix}
$$

$$
\begin{Vmatrix} a & b \\ c & d \end{Vmatrix}
$$

$$
\SI{3}{\volt}
$$

$$
\qty{3}{V}
$$

$$
x \in \R
$$

$$
n \in \N
$$

$$
\ce{H2O}
$$

$$
\pu{3 V}
$$

$$
\def\foo{x}\foo
$$

$$
ä + ü
$$
