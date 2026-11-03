# Summing amplifier RF = 24k, R1 = 8k, R2 = 12k, R3 = 48k; U1 = 0.25, U2 = -0.6, U3 = 1.5 V.
from studykit.check import answers

RF = 24e3
R = [8e3, 12e3, 48e3]
U = [0.25, -0.6, 1.5]
I = [u / r for u, r in zip(U, R, strict=True)]  # into the virtual-ground node
Ua = -RF * sum(I)
assert abs(Ua) < 12
answers(I1=I[0] * 1e6, I2=I[1] * 1e6, I3=I[2] * 1e6, Ua=Ua, method="node at virtual ground")
