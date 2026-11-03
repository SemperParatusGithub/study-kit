---
topic: network-and-consensus
title: 'Flash cards: the network and consensus'
---

:::: {.flashcard #card-network-and-consensus-001}
What does a full node do with a new block before it accepts it?

::: back
It checks the block and its transactions against the rules itself, without trusting the miner or the node that sent it.
:::
::::

:::: {.flashcard #card-network-and-consensus-002}
Why can the mempools of two nodes differ?

::: back
Every node keeps its own waiting room for valid transactions not yet in a block, and messages reach the nodes in different orders.
:::
::::

:::: {.flashcard #card-network-and-consensus-003}
A valid chain of 12 blocks at difficulty 1 competes with a valid chain of 7 blocks at difficulty 2. Which one do nodes follow?

::: back
The 7 blocks: they represent 14 units of work against 12, and a node follows the most work, not the most blocks.
:::
::::

:::: {.flashcard #card-network-and-consensus-004}
Two miners find a block at the same height. How does the network end up on one chain?

::: back
Nodes stay with the block they saw first until the next block builds on one of the two. That branch then has more work, and everyone moves over to it.
:::
::::

:::: {.flashcard #card-network-and-consensus-005}
What is a stale block?

::: back
A valid block that lost a tie and so is not in the most-work chain. Its miner gets nothing, which is why coinbase outputs wait for 100 more blocks before they can be spent.
:::
::::

:::: {.flashcard #card-network-and-consensus-006}
What happens to the transactions in the blocks that a reorganization undoes?

::: back
They go back to the mempool, unless the new branch already contains them. So being in a block does not make a payment final.
:::
::::

:::: {.flashcard #card-network-and-consensus-007}
A payment has six confirmations. How many blocks lie on top of its own block?

::: back
Five, so $z = 5$: wallets count the payment's own block as the first confirmation.
:::
::::

:::: {.flashcard #card-network-and-consensus-008}
For $p > q$, what is the chance that an attacker known to be $z$ blocks behind ever catches up?

::: back
$q_z = (q/p)^z$, where $q$ is the attacker's share of the hash power and $p = 1 - q$ the honest share.
:::
::::

:::: {.flashcard #card-network-and-consensus-009}
Why is $(q/p)^z$ too optimistic for someone waiting on a payment?

::: back
The secret chain cannot be seen, so the attacker may already hold blocks and be less than $z$ behind. $P$ allows for those blocks and is much larger: for $q = 0.1$ and $z = 5$ it is 0.09% instead of 0.0017%.
:::
::::

:::: {.flashcard #card-network-and-consensus-010}
How does $P$ deal with the unknown number $k$ of secret blocks?

::: back
It treats $k$ as Poisson with mean $\lambda = z\,q/p$ and weights each $k$ by the chance of catching up from there: $(q/p)^{z-k}$ for $k \le z$ and 1 for $k > z$.
:::
::::

:::: {.flashcard #card-network-and-consensus-011}
Why does a wait of six confirmations not make every payment safe?

::: back
It means $z = 5$, which leaves $P$ at 0.09% for $q = 0.1$ but at 17.7% for $q = 0.3$. The right wait depends on what is at stake.
:::
::::

:::: {.flashcard #card-network-and-consensus-012}
What is $q_z$ for an attacker with more hash power than everyone else combined?

::: back
$q_z = 1$, since $p < q$: its private chain overtakes the public one sooner or later, however far behind it starts.
:::
::::

:::: {.flashcard #card-network-and-consensus-013}
What can a majority of the hash power achieve?

::: back
Reverse its owner's recent payments (and so double spend), keep chosen transactions out of the chain, and rewrite older blocks at a cost that grows with their depth.
:::
::::

:::: {.flashcard #card-network-and-consensus-014}
Why can a majority of the hash power still not spend coins locked to another person's key?

::: back
Winning the race only settles which valid chain nodes follow. A spend without a valid signature breaks a rule, so full nodes ignore the block that holds it, however much work went into it.
:::
::::

:::: {.flashcard #card-network-and-consensus-015}
What does a miner put at risk by attacking instead of mining honestly?

::: back
Its earnings, since a failed secret chain pays nothing, and the value of the coins it has already earned, which a visible attack can lower. Someone set on harm at any price is held back only by the cost of the hash power.
:::
::::
