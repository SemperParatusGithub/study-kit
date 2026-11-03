# Inverting amplifier R1 = 6.8 kOhm, R2 = 27 kOhm, Ue = 0.35 V, ideal op amp.
from studykit.check import answers

R1, R2, Ue = 6.8e3, 27e3, 0.35
V = -R2 / R1
answers(V=V, Ua=V * Ue, Rein=R1 / 1e3, Ie=Ue / R1 * 1e6, method="node at virtual ground")
