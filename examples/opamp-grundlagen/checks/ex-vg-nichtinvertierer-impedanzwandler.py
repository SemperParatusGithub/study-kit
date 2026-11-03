# Non-inverting amplifier V = 7.5, R1 = 2.7 kOhm, +-12 V; sensor U0 = 1.1 V, Ri = 82 kOhm, RL = 5.6 kOhm.
from studykit.check import answers

V, R1, Usat = 7.5, 2.7e3, 12.0
U0, Ri, RL = 1.1, 82e3, 5.6e3
R2 = (V - 1) * R1
UL1 = U0 * RL / (Ri + RL)
UL2 = U0  # ideal follower draws no current from the sensor
Ua0 = max(-Usat, min(Usat, V * U0))  # infinite input resistance: Ue = U0
answers(R2=R2 / 1e3, Ua=V * 0.65, UL1=UL1, UL2=UL2, Ua0=Ua0, method="ideal op amp rules")
