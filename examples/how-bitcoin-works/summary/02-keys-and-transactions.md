---
topic: keys-and-transactions
title: Keys and transactions
objectives:
  - 'Explain how a private key, a public key, a signature and an address relate, and which of them may be shared'
  - 'Say what a wallet and its seed really hold, and what losing or leaking the seed means'
  - 'Describe a transaction as inputs that spend earlier outputs and outputs that create new UTXOs'
  - 'Work out the change and the fee of a transaction from its inputs and outputs'
  - 'Trace how a locking script and the unlocking data work together in a pay-to-public-key-hash output'
  - 'Explain why a valid signature does not prevent a double spend'
---

## Proving the right to spend

[Why Bitcoin exists](topic:why-bitcoin) replaced the bank's private books with a public ledger.
With no bank to check who you are, the right to spend must be something a stranger can verify from
the data alone: a pair of linked numbers, one secret and one public.

::: definition
**Private key**

A 256-bit random number: whoever knows it can spend the coins it controls. With about
$2^{256} \approx 1.16 \cdot 10^{77}$ possible values, guessing somebody else's key is hopeless.
:::

::: definition
**Public key**

A number computed from the private key on the elliptic curve secp256k1. The computation is
quick; going back from public to private key is computationally infeasible.
:::

::: definition
**Digital signature**

A value computed from a private key and one specific transaction. Anyone with the public key can
check it, and checking reveals nothing about the private key.
:::

A signature covers the transaction, so changing an amount or recipient makes the check fail. Signing
is not encrypting, though: everybody can read the amounts and addresses of every transaction.

## Addresses and wallets

To be paid you hand out an address, which is built from your public key with a hash function.

::: definition
**Hash function**

A function that turns data of any length into a fingerprint of fixed length. A tiny change in the
data gives a completely different fingerprint, and the function cannot be run backwards.
:::

::: definition
**Address**

An encoded hash of a public key or of a script, not the key itself. The hash here is
$\mathrm{HASH160}(x) = \mathrm{RIPEMD160}(\mathrm{SHA256}(x))$. Legacy addresses start with 1 or 3,
SegWit addresses with bc1q and Taproot addresses with bc1p.
:::

![From a seed to an address; each step works only from left to right](fig:key-derivation-chain)

::: definition
**Seed**

A phrase of 12 or 24 words (BIP 39) from which a wallet derives all its keys in a tree (BIP 32),
so one backup covers every future address.
:::

::: warning
**A wallet does not contain coins**

Coins exist only as entries in the public ledger; a wallet, the software or device you use, holds
keys. Lose the seed with no other copy of the keys and the coins can never be spent; leak it and
anyone can spend them. Nobody can reset it for you.
:::

## Transactions and the UTXO model

Bitcoin has no accounts and no coin objects: its ledger is a list of transactions, signed messages
that each spend earlier outputs and create new ones. Only the coinbase transaction of
[Blocks and mining](topic:blocks-and-mining) spends nothing.

::: definition
**Transaction output**

An amount in satoshis (1 BTC is 100,000,000 satoshis, or sat) and a locking script, the condition
for spending it.
:::

::: definition
**Transaction input**

A reference to one earlier output, called its outpoint, plus the unlocking data that meets that
output's condition. The outpoint is the output's index and the id of its transaction, the txid,
which is $\mathrm{SHA256}(\mathrm{SHA256}(x))$ for the serialized transaction $x$.
:::

::: definition
**UTXO**

An unspent transaction output. Your balance is the sum of the UTXOs your wallet can unlock.
:::

![Inputs spend earlier outputs; the outputs not yet spent are the UTXOs](fig:utxo-chain)

In the figure, Bob's balance is 0.0498 BTC, because his 0.3 BTC output is already spent. Follow the
arrows backwards and you get the white paper's coin, a chain of signatures,
though a node only asks whether an output is still unspent.

## Change and fee

An output can only be spent whole, like a banknote, and a transaction may combine several inputs.
The usual shape is one payment plus change. No field states
the fee; it is whatever the outputs leave unclaimed.

::: definition
**Change**

An output that returns the unneeded part of the inputs to the sender. Forget it and the whole
remainder becomes fee: with only the 0.3 BTC output below, Alice would pay 0.2 BTC, or 20,000,000 sat.
:::

::: definition
**Transaction fee**

$\text{fee} = \sum \text{inputs} - \sum \text{outputs}$, collected by the miner who includes it.
:::

![Alice pays Bob: the fee is what no output claims](fig:tx-alice-fee)

::: example
**Paying with one input and with two**

Alice has a UTXO of 0.5 BTC, pays Bob 0.3 BTC and takes 0.1999 BTC as change, so the fee is
0.5 − 0.3 − 0.1999 = 0.0001 BTC, or 10,000 sat. Dana has UTXOs of 0.02 and 0.05 BTC and pays
0.06 BTC. Neither is enough alone, so she spends both; with a fee of 0.00002 BTC (2,000 sat) her
change is 0.07 − 0.06 − 0.00002 = 0.00998 BTC.
:::

Block space is scarce, so wallets bid in satoshis per [virtual byte](topic:scaling-and-limits), and
miners take the best-paying first. The fee follows size, not amount: at 50 sat per virtual byte, an
assumed 200 virtual bytes cost 10,000 sat whether they move 100 BTC or 0.01 BTC.

## Scripts: how an output is locked

::: definition
**Script**

A program in Bitcoin's small stack language, deliberately without loops so its running time is
bounded. The locking script sits in the output; the input supplies the unlocking data.
:::

In the common pattern, pay-to-public-key-hash (P2PKH), Alice's output stores the hash of Bob's
public key. To spend it, Bob's input supplies that public
key and a signature, and every node asks:

1. Does the supplied public key hash to the stored value?
2. Is the signature valid for this key and this transaction?

Pay-to-script-hash (P2SH) locks to the hash of a script revealed only at spending. Multisignature
needs several keys, such as 2 of 3; a timelock forbids spending before a block height or time.

## What a valid transaction does not settle

Nodes check that every input points at an existing unspent output and meets its lock, and that the
outputs do not exceed the inputs. None of that says which of two transactions came first.

::: warning
**A valid signature does not stop a double spend**

Alice can sign one transaction paying her 0.5 BTC output to Bob and another paying it to Carol.
Both signatures are valid and both spend the same outpoint, yet only one can count. Settling which
is the job of [Blocks and mining](topic:blocks-and-mining).
:::

The public record also limits privacy. It shows amounts and addresses but no names, much as a stock
exchange publishes its trades and not the traders. A fresh key
pair per transaction helps, but several inputs in one transaction point to one owner.

::: takeaways
- The private key stays secret; a signature proves control of it for one specific transaction.
- An address is an encoded hash of a public key or script; a seed backs up all your keys.
- There are no accounts: inputs spend earlier outputs, and your balance is the sum of your UTXOs.
- Outputs are spent whole, so payments need change, and fee = inputs − outputs.
- Signatures say who approved a payment, never which of two conflicting payments came first.
:::
