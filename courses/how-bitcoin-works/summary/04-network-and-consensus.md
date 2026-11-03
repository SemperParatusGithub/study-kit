---
topic: network-and-consensus
title: The network and consensus
objectives:
  - 'Explain what a full node checks and why a miner cannot force an invalid block on it'
  - 'Describe how the network settles on one chain after two miners find a block at nearly the same time'
  - 'Explain why a payment becomes safer with every block on top of it'
  - 'Compute the chance $P$ that an attacker catches up from its hash-power share $q$ and the block count $z$'
  - 'Tell what a 51% attack can and cannot do, and why the incentives speak against it'
---

## Many computers, no centre

[Blocks and mining](topic:blocks-and-mining) showed how a block is made. But who decides that it
counts? No office or server does. Bitcoin is a [peer-to-peer network](topic:why-bitcoin) of nodes
that may join or leave at any time; one that returns after a break asks its neighbours what it
missed and checks it.

::: definition
**Gossip**

How Bitcoin's messages spread: each node passes a new transaction or block on to the nodes it is
connected to. A lost message does little harm, since a node requests a block it finds it has missed.
:::

::: definition
**Full node**

A computer that checks every transaction and block against the rules for itself: valid
signatures, no output spent twice, no more new coins than the subsidy allows, enough proof of work.
:::

::: definition
**Mempool**

One node's waiting room for valid transactions that are not yet in a block. Every node has its
own, and since messages arrive in different orders, two mempools can differ.
:::

::: warning
**Miners do not make the rules**

Hash power (the hashing a miner does per second) buys a chance to propose the next block, nothing
more. Full nodes ignore a block that breaks a rule, however much work went into it.
:::

## Agreeing on one chain

With nobody in charge, each node applies one rule that gives the same answer to everyone who has
seen the same blocks: among all valid chains, follow the one that took the most work to build.

::: definition
**Most-work chain**

The valid chain whose blocks together represent the most expected hashing, often loosely called
the longest chain. What counts is work, not block count: ten blocks at difficulty 1 are 10 units
of work, while eight blocks at difficulty 2 are 16 units, and those eight win.
:::

Disagreement happens for an innocent reason. Blocks take time to cross the network, so a second
miner can find a block before hearing of the first. Nodes stay with whichever they saw first until
the next block builds on one of the two; that branch now has more work, and everyone moves over.

![A tie at height 101, and how the next block breaks it](fig:nc-temporary-fork)

::: definition
**Stale block**

A valid block that lost such a tie and is no longer in the most-work chain. Its miner gets nothing,
which is why coinbase outputs can only be spent after 100 more blocks.
:::

::: definition
**Reorganization**

A node's switch to a chain with more work than the one it followed. The blocks of the old branch
are undone, and their transactions return to the mempool unless the new branch already has them.
:::

## Confirmations and the attacker's race

A reorganization can remove a payment, so being in a block is not final. But a buried block falls
only to a rival branch that overtakes all the work on top, so settlement is a likelihood that grows.

::: definition
**Confirmation**

A block that buries a transaction. Wallets count the transaction's own block as the first
confirmation and each block on top as one more. Six confirmations, about 60 minutes on average,
are a common convention for large payments.
:::

How much safer does each block make you? The white paper models an
attack. A dishonest payer pays you and secretly mines a rival chain in which the same coins go back
to itself. You wait until the payment's block has $z$ blocks on top, then hand over the goods. If the
secret chain ever gets ahead, the payer publishes it, every node switches and your payment is gone.
A fresh key, given out just before the payment, stops the payer preparing this in advance.

Let $q$ be the attacker's share of all hash power and $p = 1 - q$ the honest share. Call $r$ the
chance of ever gaining one block on the honest chain: either the attacker finds the next block
(probability $q$), or it falls one further behind (probability $p$) and must then gain two, so
$r = q + p\,r^2$. For $p > q$ the solution that applies is $r = q/p$, and from $z$ blocks behind:

$$
q_z = \begin{cases} 1 & \text{if } p \le q \\ (q/p)^z & \text{if } p > q \end{cases}
$$

But you cannot see the secret chain, so you do not know the deficit. While the honest chain added
$z$ blocks, the attacker found $\lambda = z\,q/p$ blocks on average, and the actual number $k$ follows
a Poisson distribution. Weighting each $k$ by its chance of catching up from there gives:

$$
P = \sum_{k=0}^{\infty} \frac{\lambda^k e^{-\lambda}}{k!} \begin{cases} (q/p)^{z-k} & k \le z \\ 1 & k > z \end{cases}
$$

::: example
**Two blocks on top, 10% of the hash power**

With $q = 0.1$, $p = 0.9$ and $z = 2$, the mean is $\lambda = 0.2222$:

| Secret blocks $k$ | Poisson chance | Chance of catching up | Product |
|---|---|---|---|
| 0 | 0.80074 | $(1/9)^2 = 0.01235$ | 0.00989 |
| 1 | 0.17794 | $1/9 = 0.11111$ | 0.01977 |
| 2 | 0.01977 | 1 | 0.01977 |
| more than 2 | 0.00155 | 1 | 0.00155 |

The products add up to $P = 0.05098$, about 5%, as in the white paper's table.
:::

::: warning
**Two different numbers**

$(q/p)^z$ is for an attacker known to be $z$ blocks behind; $P$ allows for blocks already mined in
secret and is much larger. For $q = 0.1$ and $z = 5$, the first is 0.0017% and the second 0.09%.
:::

![The chance of catching up falls with z, far more slowly for a larger q](fig:nc-catch-up)

The chance falls roughly exponentially with $z$, at a rate set by $q$. Reaching $P < 0.001$ takes:

| Attacker's share $q$ | 0.10 | 0.15 | 0.20 | 0.25 | 0.30 | 0.35 | 0.40 | 0.45 |
|---|---|---|---|---|---|---|---|---|
| Blocks on top $z$ | 5 | 8 | 11 | 15 | 24 | 41 | 89 | 340 |
| Average wait in hours | 0.8 | 1.3 | 1.8 | 2.5 | 4.0 | 6.8 | 14.8 | 56.7 |

::: warning
**Six confirmations are a habit, not a guarantee**

Six confirmations mean $z = 5$ in this count, which leaves out the payment's own block. That gives
0.09% against $q = 0.1$ but 17.7% against $q = 0.3$; the right wait depends on what is at stake.
:::

## What a majority can and cannot do

::: definition
**51% attack**

An attack by someone with more hash power than everyone else combined. Then $p < q$, so $q_z = 1$:
the private chain overtakes the public one sooner or later, however far behind it starts.
:::

Winning the race only decides which valid chain nodes follow; their checks still apply to its blocks:

| With a majority, an attacker can | Even so, it cannot |
|---|---|
| reverse its own recent payments, and so double spend | spend coins locked to another person's key |
| keep chosen transactions out of the chain | create coins beyond the subsidy |
| rewrite older blocks, at a cost that grows with their depth | make full nodes accept an invalid block |

::: warning
**51% is no clean border**

An attacker with $q = 0.3$ still has a 62.8% chance against one block on top: a minority can get lucky.
:::

## Why following the rules pays

The network makes about $6 \cdot 24 = 144$ blocks a day, so a miner with $q = 0.3$ finds about 43.2
of them and earns 135 BTC a day at the 3.125 BTC subsidy, before fees. An attack risks that twice: a
failed secret chain earns nothing, and a visible attack can lower the value of the coins the attacker
has earned; see the white paper. Someone who wants to harm the system
at any price is limited only by the cost of the hash power.

::: takeaways
- Miners propose blocks; every full node checks them itself and ignores what breaks the rules.
- Each node follows the valid chain with the most work, so a tie ends with the next block and leaves a stale block.
- Each block on top makes reversal less likely: $z = 5$ gives 0.09% at $q = 0.1$ and 17.7% at $q = 0.3$.
- A majority can undo its own payments and block transactions, but cannot steal coins or break the rules.
- Honest mining is meant to pay better than attacking, which is an incentive and not a guarantee.
:::
