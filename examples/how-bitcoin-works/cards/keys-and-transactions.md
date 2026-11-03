---
topic: keys-and-transactions
title: 'Flash cards: keys and transactions'
---

:::: {.flashcard #card-keys-and-transactions-001}
Why can a public key be shared while its private key stays secret?

::: back
Getting from the private key to the public key on secp256k1 is quick, but the way back is computationally infeasible.
:::
::::

:::: {.flashcard #card-keys-and-transactions-002}
What happens to the signature check when someone alters the amount or recipient of a signed transaction?

::: back
It fails, because a signature is valid only for the one specific transaction it was computed from.
:::
::::

:::: {.flashcard #card-keys-and-transactions-003}
Who can read the amounts and addresses in a signed transaction?

::: back
Everybody. A signature proves approval, but signing encrypts nothing.
:::
::::

:::: {.flashcard #card-keys-and-transactions-004}
What does a Bitcoin address encode?

::: back
A hash of a public key or of a script, not the key itself.
:::
::::

:::: {.flashcard #card-keys-and-transactions-005}
Why does a single backup of the seed cover every future address of a wallet?

::: back
The wallet derives all its keys from the seed, in a tree (BIP 32).
:::
::::

:::: {.flashcard #card-keys-and-transactions-006}
What does a wallet actually hold?

::: back
Keys. The coins themselves exist only as entries in the public ledger.
:::
::::

:::: {.flashcard #card-keys-and-transactions-007}
What becomes of your coins if you lose the seed and have no other copy of the keys?

::: back
They can never be spent again, since nobody is able to reset a seed for you.
:::
::::

:::: {.flashcard #card-keys-and-transactions-008}
What can anyone do who learns your seed?

::: back
Spend your coins: the seed yields all your private keys, and knowing a private key is enough to spend what it controls.
:::
::::

:::: {.flashcard #card-keys-and-transactions-009}
What does a transaction output consist of?

::: back
An amount in satoshis and a locking script, which is the condition for spending it.
:::
::::

:::: {.flashcard #card-keys-and-transactions-010}
What does a transaction input consist of?

::: back
An outpoint, which refers to one earlier output, and the unlocking data that meets that output's condition.
:::
::::

:::: {.flashcard #card-keys-and-transactions-011}
Bitcoin has no accounts. So what is your balance?

::: back
The sum of the UTXOs, the unspent transaction outputs, that your wallet can unlock.
:::
::::

:::: {.flashcard #card-keys-and-transactions-012}
Why does a typical payment create an output back to the sender?

::: back
An output can only be spent whole, so the unneeded part has to return as change. Without that output the whole remainder becomes fee.
:::
::::

:::: {.flashcard #card-keys-and-transactions-013}
A transaction spends one UTXO of 0.8 BTC and creates outputs of 0.25 BTC and 0.5497 BTC. How large is its fee?

::: back
0.8 − 0.25 − 0.5497 = 0.0003 BTC, or 30,000 sat. No field states the fee: it is the sum of the inputs minus the sum of the outputs.
:::
::::

:::: {.flashcard #card-keys-and-transactions-014}
What does every node check when a pay-to-public-key-hash (P2PKH) output is spent?

::: back
That the supplied public key hashes to the value stored in the output, and that the signature is valid for this key and this transaction.
:::
::::

:::: {.flashcard #card-keys-and-transactions-015}
Why does a valid signature not prevent a double spend?

::: back
Alice can sign two transactions that spend the same outpoint, and both signatures are valid. Signatures say who approved a payment, never which of two conflicting payments came first.
:::
::::
