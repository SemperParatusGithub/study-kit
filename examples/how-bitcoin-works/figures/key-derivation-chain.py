"""From one seed to an address: every step is easy forwards and infeasible backwards."""

from studykit.figures import block

ALT = (
    "A chain of four items joined by three one-way steps, left to right. The seed, a phrase of "
    "12 or 24 words, goes through the BIP 32 key tree and gives a private key, a 256-bit random "
    "number. The private key goes through the elliptic curve secp256k1 and gives a public key. "
    "The public key goes through HASH160 and an encoding step and gives an address. Each arrow "
    "can be followed only from left to right."
)


def build():
    return block.chain(
        ["BIP 32 tree", "secp256k1 curve", "HASH160, encoding"],
        signals=["seed", "private key", "public key", "address"],
        size="full",
        alt=ALT,
    )
