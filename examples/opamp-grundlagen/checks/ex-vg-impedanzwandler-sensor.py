# Sensor U0 = 0.9 V, Ri = 68 kOhm, load RL = 3.3 kOhm; direct and through an ideal follower.
from studykit.check import answers

U0, Ri, RL = 0.9, 68e3, 3.3e3
UL = U0 * RL / (Ri + RL)  # voltage divider
anteil = UL / U0 * 100
IL = U0 / RL * 1e6  # follower: no input current, full U0 at the load; µA
answers(UL=UL, anteil=anteil, IL=IL, method="divider Ri-RL; ideal follower")
