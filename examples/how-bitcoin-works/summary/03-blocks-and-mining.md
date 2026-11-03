---
topic: blocks-and-mining
title: Blocks and mining
objectives:
  - 'Name the six fields of a block header and say what the main ones are for'
  - 'Build a Merkle root from a list of transactions and work out the size of a Merkle proof'
  - 'Explain what miners actually do and why changing an old block is so expensive'
  - 'Work out a difficulty adjustment, including its limit of a factor of 4'
  - 'Find the block subsidy at a given height and explain why the supply ends just below 21 million'
---

## From single payments to a chain of blocks

After [Keys and transactions](topic:keys-and-transactions), anyone can check that a payment is
properly signed. A signature cannot show which of two conflicting payments came first, though,
so Bitcoin also needs a record of order that is hard to alter. It builds one with a
[hash function](topic:keys-and-transactions), SHA-256, whose fingerprints have 256 bits.

::: definition
**Block**

A batch of transactions under a short summary. The sequence of blocks is the blockchain.
:::

::: definition
**Block header**

The 80-byte summary of a block. Hashing it twice with SHA-256 gives the block's hash.
:::

Its six fields are the version (4 bytes), the previous block's hash (32), the Merkle root (32), a
timestamp (4), the target in a compact form called nBits (4) and the nonce (4). The previous hash
makes this a chain: each header holds the fingerprint of the one before, so it depends on them all.

## The Merkle tree: many transactions, one hash

A header stays at 80 bytes whether its block carries ten transactions or thousands, because the
transactions are condensed step by step into a single hash.

::: definition
**Merkle tree**

A tree of hashes: neighbours are hashed in pairs, the results are paired and hashed again (an odd
one out is paired with itself), until one hash remains, the Merkle root.
:::

::: example
For four transactions with txids $A, B, C, D$, where $H(a, b)$ hashes two values joined together,
the root is $H(H(A, B), H(C, D))$. To prove that $C$ is in the block, it is enough to supply $D$ and
$H(A, B)$: you compute the root from them and compare it with the header.
:::

A proof needs one hash per level, about $\log_2 n$ hashes for $n$ transactions. For 4,000
transactions that is 12 hashes of 32 bytes, or 384 bytes; for 8,000 it is just one hash more.
The headers add up to only about 4.2 MB per year, as the white paper notes.

::: definition
**Simplified payment verification (SPV)**

Checking that a transaction is in a block with only the block headers and a Merkle proof. This shows
that the transaction was included, not that it is valid: the wallet relies on the network for that.
:::

## Proof of work: what miners do

So far a block could be recomputed in a moment, so rewriting history would cost nothing. Proof of
work adds the cost: a header counts only if its hash, read as a number, is below a limit $T$:

$$
\text{hash} < T, \qquad P(\text{success per try}) = \frac{T}{2^{256}}, \qquad \text{expected tries} = \frac{2^{256}}{T}
$$

::: definition
**Target**

The number $T$ a block's hash must fall below. A smaller target leaves fewer winning hashes.
:::

::: definition
**Nonce**

The header field a miner varies to get a new hash. It has only $2^{32}$ values, about 4.3 billion;
when they run out, the miner changes other data, such as an extra nonce in the first transaction.
:::

::: definition
**Proof of work**

A result that is costly to find and quick to check: here, a header whose hash is below the target.
:::

::: definition
**Mining**

Trying nonce after nonce, hashing the header each time, until a hash falls below the target. There
is no hard equation to solve: SHA-256 cannot be run backwards, so guessing is the only method.
:::

::: example
With $T = 2^{255}$, half of all hashes win, so two tries are expected. With $T = 2^{236}$, a winning
hash begins with 20 zero bits, and $2^{20} = 1048576$ tries are expected: about 1 s for a machine
doing $10^6$ hashes per second. Cutting the target in half always doubles the expected work.
:::

Each try is independent, so the wait for the next block follows an exponential distribution with a
mean of 10 minutes, $P(\text{within } t) = 1 - e^{-t / 10\,\mathrm{min}}$. About 63.2% of blocks come
within 10 minutes, 9.5% within 1 minute, and 5.0% take longer than 30 minutes.

::: warning
**Ten minutes is an average, not a timetable**

No miner is ever partly done: after 20 minutes without a block, the expected wait is still 10 minutes.
:::

## Why an old block is expensive to change

Suppose someone alters an old transaction. Its txid changes, then the Merkle root, then the block's
hash, which is now almost certainly above the target, so the block must be mined again. Its new
hash no longer matches the previous hash in the next header, so that block must be mined again too,
and so on up to the newest block, while everyone else keeps extending the chain. No rule forbids
trying; it is just very costly, and [The network and consensus](topic:network-and-consensus) has the odds.

## Keeping the pace: difficulty adjustment

The total hash power changes as machines improve and miners come and go. With a fixed target,
blocks would speed up or slow down with it, so the target is recalculated at regular intervals.

::: definition
**Difficulty adjustment**

The reset of the target every 2016 blocks, to hold the pace near one block per 10 minutes. A lower
target means a higher difficulty. Every node derives the same value from the chain's timestamps.
:::

The intended period is $2016 \cdot 10\,\mathrm{min} = 14\,\text{days} = 1209600\,\mathrm{s}$. The
target scales with the time $t_\mathrm{actual}$ those blocks really took, by at most a factor of 4:

$$
T_\mathrm{new} = T_\mathrm{old} \cdot \frac{t_\mathrm{actual}}{14\,\text{days}}, \qquad \frac{1}{4} \le \frac{T_\mathrm{new}}{T_\mathrm{old}} \le 4
$$

::: example
If the 2016 blocks took 12 days, one came every 8.57 minutes. The target is multiplied by
$12/14 \approx 0.857$, and expected tries rise by a factor of $14/12 \approx 1.167$. If they took
2 days, the ratio $2/14 \approx 0.143$ is below the limit, so the target is multiplied by exactly $1/4$.
:::

## The reward and the halving

Mining costs electricity, so it has to pay, and with no issuer, new coins need a way into circulation.

::: definition
**Block subsidy**

The newly created bitcoin a miner may claim per block.
:::

::: definition
**Coinbase transaction**

The first transaction of a block, which pays its miner the subsidy plus the block's
[fees](topic:keys-and-transactions). Its outputs can be spent only after 100 more blocks, about 16.7
hours, because a block may still go [stale](topic:network-and-consensus), dropping out of the chain.
:::

::: example
A subsidy of 3.125 BTC and 4,000 transactions with an assumed average fee of 0.0001 BTC give
0.4 BTC in fees and a reward of 3.525 BTC, of which fees are about 11.3%.
:::

::: definition
**Halving**

The cut of the block subsidy to half its value every 210,000 blocks, about every four years.
:::

The schedule follows the block height, a block's position in the chain counted from 0, so the
years in the chart are rounded. With $k$ halvings so far, the subsidy is

$$
s_k = \frac{50\,\mathrm{BTC}}{2^k}, \qquad k = \left\lfloor \frac{\text{height}}{210000} \right\rfloor
$$

![Block subsidy per era: each step lasts 210,000 blocks, about four years](fig:block-subsidy-halving)

::: example
Block 500,000: $500000/210000 \approx 2.38$, so $k = 2$ and 12.5 BTC. Block 840,000: exactly $k = 4$,
so it is the first at 3.125 BTC (April 2024). Block 1,000,000: $1000000/210000 \approx 4.76$, still $k = 4$.
:::

Each era issues half as much as the one before: 10,500,000 BTC in the first, 5,250,000 BTC in the
second. After five eras, 20,343,750 BTC exist, 96.875% of 21 million. Carried on forever, the series
$210000 \cdot 50\,\mathrm{BTC} \cdot (1 + 1/2 + 1/4 + \dots)$ would reach exactly 21 million.
But the subsidy is rounded down to whole satoshis: it is 1 satoshi at $k = 32$ and nothing at
$k = 33$, around the year 2140, so the true total is 20,999,999.9769 BTC. From then on miners earn
only fees, and nobody knows yet whether those will pay for enough security.

::: warning
**A halving cuts only the subsidy**

Fees are unaffected, so the reward falls by less than half, and blocks keep coming at the same pace.
:::

## Who mines today

The search needs nothing but hashes per second, so ordinary computers lost out long ago. Today
the work runs on chips built for this one task.

::: definition
**ASIC**

A chip made for a single job, here computing SHA-256 as fast and as cheaply as possible. It can do
nothing else.
:::

A lone miner might wait years for a block and then earn the whole reward at once. So most miners
join forces and share the income, in proportion to the work each one shows.

::: definition
**Mining pool**

A group of miners who split the search and share the rewards, which turns a rare large payout into a
steady small one. A pool coordinates the work; it cannot change the rules, since the
[nodes](topic:network-and-consensus) check every block all the same.
:::

::: takeaways
- A block is a batch of transactions under an 80-byte header with the previous hash and a Merkle root.
- A Merkle proof needs only about $\log_2 n$ hashes, which makes SPV possible.
- Mining is guessing until the hash is below the target; changing a block means re-mining all later ones.
- Every 2016 blocks, about 14 days, nodes reset the target, by at most a factor of 4.
- The subsidy halves every 210,000 blocks, so the supply ends at 20,999,999.9769 BTC.
:::
