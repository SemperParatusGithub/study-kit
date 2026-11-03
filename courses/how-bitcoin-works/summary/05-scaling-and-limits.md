---
topic: scaling-and-limits
title: Upgrades, scaling and limits
objectives:
  - Tell a soft fork from a hard fork and say what each does to nodes that do not upgrade
  - Compute the weight of a block or a transaction from its witness and non-witness bytes
  - Explain why block space is kept scarce and what SegWit and Taproot changed
  - Describe how a Lightning channel moves payments off the chain and what that costs
  - Weigh the limits of Bitcoin in energy use, privacy, reversibility and quantum computing
---

## Changing the rules

[Full nodes](topic:network-and-consensus) enforce the rules, each for itself, so nobody can order
an upgrade. A rule changes only if people choose to run the new software, and some never will, so
what counts is how a change treats the old nodes. SegWit (2017) and Taproot (2021) were soft forks;
Bitcoin Cash split off in August 2017 through a hard fork to larger blocks.

::: definition
**Soft fork**

A change that tightens the rules, so that old nodes still accept the new blocks.
:::

::: definition
**Hard fork**

A change that loosens the rules, so that old nodes reject some new blocks. Without near-unanimity
the chain splits for good.
:::

![Soft fork: the new rules lie inside the old ones. Hard fork: a new block can lie outside them.](fig:scaling-fork-rules)

::: warning
**Two meanings of "fork"**

The brief fork when two miners find a block at once needs no rule change and heals by itself. And
"soft" does not mean painless: upgraded nodes can reject an old miner's block, so it goes smoothly
only if most of the hash power enforces the new rules.
:::

## SegWit and block weight

Every full node checks every block. Bigger blocks would make a node more costly to run, and checking
the rules would drift to a few large operators, the very trust Bitcoin set out to remove. At 2 MB
per block a node gains about 105 GB a year; at 200 MB, about 10.5 TB. So space stays scarce on purpose.

Before 2017 the limit was 1 MB, and signatures counted like everything else. SegWit moved them where
old nodes never look, so to them a block still looks like at most 1 MB, which made this a soft fork.
The limit since then, with $b$ counting bytes:

$$
\text{weight} = 4 \cdot b_\text{non-witness} + 1 \cdot b_\text{witness} \le 4000000
$$

::: definition
**Witness**

The unlocking data of an input, mainly its signature, kept apart from the rest of a transaction.
:::

::: definition
**SegWit**

Segregated Witness: the 2017 soft fork that moved signatures into the witness and added block weight.
:::

::: definition
**Block weight**

The measure of a block's size since SegWit: 4 units per non-witness byte, 1 per witness byte.
:::

::: example
**Computing weight**

A transaction of 150 non-witness and 110 witness bytes weighs $4 \cdot 150 + 110 = 710$ units. A
block of 700,000 non-witness and 1,200,000 witness bytes weighs exactly 4,000,000 units at 1.9 MB.
At an assumed 1,300 units per transaction, a block holds about 3,077, or 5 per second over 600 s.
:::

So 4,000,000 units does not mean 4 MB: real blocks come to roughly 1.5 to 2 MB and a few transactions
per second worldwide, far below a card network. SegWit also removed a danger for Lightning below: a
third party could change a txid by altering a signature without invalidating it. A SegWit txid no
longer covers the signature, so a transaction can safely spend another that is not yet confirmed.

## Taproot

::: definition
**Taproot**

The 2021 soft fork adding an output that can be spent either by one signature or by revealing one
script from a set of alternatives; if the signature is used, the chain never shows the alternatives.
Its new Schnorr signatures let several signers combine their keys into what looks like one signature.
:::

## Lightning: payments off the chain

Two parties can settle most payments between themselves, with the chain as the final referee.

::: definition
**Payment channel**

Two parties lock funds in a 2-of-2 multisignature output, then keep exchanging signed, unpublished
transactions that split those funds anew. Only opening and closing touch the chain.
:::

![A channel: opening and closing are on the chain; the states between them are not.](fig:scaling-lightning-channel)

Say Alice locks 0.06 BTC and Bob 0.04 BTC. She pays him 0.01 BTC by signing a new split of 0.05 and
0.05; he pays back 0.002 BTC with a split of 0.052 and 0.048. Each holds the latest state signed by
the other, so either can close alone. What stops Alice from publishing the first state, which suits
her better? If a party publishes an old state, the other can claim all the funds as a penalty.

::: definition
**Lightning Network**

The network of payment channels across which payments are routed in several hops.
:::

::: definition
**HTLC**

Hash time-locked contract: a payment that can be claimed only with the secret behind a given hash,
before a deadline. Chained HTLCs make all hops of a route complete or fail together.
:::

To pay Bob through Carol, Alice gets the hash of a secret from Bob and offers Carol 0.01 BTC for that
secret within two days; Carol offers Bob the same within one day. To collect, Bob must reveal the
secret, and Carol can then use it to collect from Alice. If Bob stays silent, both offers expire. The
costs: you must stay online or have someone watch for old states, Carol needs 0.01 BTC on her side
of the channel to Bob, and every channel must still be opened on the chain.

## The trade-offs that remain

Proof of work uses a lot of electricity by design, since that cost is what makes
[rewriting history](topic:blocks-and-mining) expensive. Payments
cannot be reversed by anyone, so there is no help after a mistake or a fraud. A large enough quantum
computer would threaten the signatures rather than the hashes and would call for a further upgrade.

::: warning
**Energy per transaction is misleading**

Mining secures blocks, not single transactions. An almost empty block needs the same work as a full
one, so more transactions do not directly mean more electricity.
:::

::: definition
**Pseudonymous**

Acting under an alias rather than a real name. Bitcoin is pseudonymous, not anonymous: every
transaction is public, and chain analysis can link addresses, especially reused ones.
:::

::: takeaways
- A soft fork tightens the rules and old nodes go along; a hard fork loosens them and they fall away.
- Blocks are limited to keep full nodes affordable: $4 \cdot b_\text{non-witness} + b_\text{witness} \le 4000000$.
- Lightning moves payments into channels, at the price of staying online and needing liquidity.
- Energy use, public records and no reversal are costs of the design, not accidents.
:::
