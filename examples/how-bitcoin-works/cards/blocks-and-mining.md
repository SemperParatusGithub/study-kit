---
topic: blocks-and-mining
title: 'Flash cards: Blocks and mining'
---

:::: {.flashcard #card-blocks-and-mining-001}
What turns a sequence of blocks into a chain?

::: back
Every header contains the hash of the header before it, so each block depends on all the earlier ones.
:::
::::

:::: {.flashcard #card-blocks-and-mining-002}
A block holds four transactions with txids $A, B, C, D$. What is its Merkle root?

::: back
$H(H(A, B), H(C, D))$, where $H(a, b)$ hashes two values joined together.
:::
::::

:::: {.flashcard #card-blocks-and-mining-003}
In a block with the txids $A, B, C, D$, what must you be given to prove that $C$ is included?

::: back
$D$ and $H(A, B)$. From these you compute the root and compare it with the one in the header.
:::
::::

:::: {.flashcard #card-blocks-and-mining-004}
Roughly how many hashes does a Merkle proof contain for $n$ transactions?

::: back
About $\log_2 n$, one per level of the tree, so doubling the transactions adds just one hash.
:::
::::

:::: {.flashcard #card-blocks-and-mining-005}
What can a wallet using simplified payment verification not find out on its own?

::: back
Whether a transaction is valid. Headers and a Merkle proof show only that it was included in a block, so the wallet relies on the network for the rest.
:::
::::

:::: {.flashcard #card-blocks-and-mining-006}
What condition must a block's hash meet for the block to count?

::: back
Read as a number, the hash must be below the target $T$.
:::
::::

:::: {.flashcard #card-blocks-and-mining-007}
How does the expected number of tries depend on the target $T$?

::: back
It is $2^{256} / T$, so cutting the target in half doubles the expected work.
:::
::::

:::: {.flashcard #card-blocks-and-mining-008}
What does a miner change to get a new hash on the next try?

::: back
The nonce, a header field. It has only $2^{32}$ values, so after those the miner changes other data, such as an extra nonce in the first transaction.
:::
::::

:::: {.flashcard #card-blocks-and-mining-009}
Why is there no shortcut to a winning hash?

::: back
SHA-256 cannot be run backwards, so there is no equation to solve and guessing is the only method.
:::
::::

:::: {.flashcard #card-blocks-and-mining-010}
No block has appeared for 20 minutes. What is the expected wait for the next one?

::: back
Still 10 minutes. Each try is independent, so no miner is ever partly done.
:::
::::

:::: {.flashcard #card-blocks-and-mining-011}
Why does altering an old transaction mean re-mining every later block?

::: back
The change alters that block's hash, which no longer matches the previous hash in the next header. That block must then be mined again, and so on up to the newest one.
:::
::::

:::: {.flashcard #card-blocks-and-mining-012}
What would happen to the block rate if the target never changed?

::: back
Blocks would speed up or slow down with the total hash power, which shifts as machines improve and miners come and go.
:::
::::

:::: {.flashcard #card-blocks-and-mining-013}
How often is the target recalculated?

::: back
Every 2016 blocks, which is about 14 days at the intended pace.
:::
::::

:::: {.flashcard #card-blocks-and-mining-014}
The last 2016 blocks took only 3 days. By what factor is the target multiplied?

::: back
By exactly $1/4$: the ratio $3/14 \approx 0.214$ is below the limit, and one adjustment changes the target by at most a factor of 4.
:::
::::

:::: {.flashcard #card-blocks-and-mining-015}
Why can the outputs of a coinbase transaction be spent only after 100 more blocks?

::: back
Its block may still go stale, which would drop it out of the chain.
:::
::::

:::: {.flashcard #card-blocks-and-mining-016}
What is the block subsidy at height 700,000?

::: back
6.25 BTC: $k = \left\lfloor 700000 / 210000 \right\rfloor = 3$ halvings, and $s_3 = 50\,\mathrm{BTC} / 2^3$.
:::
::::

:::: {.flashcard #card-blocks-and-mining-017}
Why does a halving cut a miner's reward by less than half?

::: back
It cuts only the subsidy; the block's fees are unaffected.
:::
::::

:::: {.flashcard #card-blocks-and-mining-018}
Why does the supply end just below 21 million BTC and not at exactly 21 million?

::: back
The subsidy is rounded down to whole satoshis and reaches nothing at $k = 33$, so the total stops at 20,999,999.9769 BTC.
:::
::::

:::: {.flashcard #card-blocks-and-mining-019}
Why do most miners join a mining pool?

::: back
A lone miner might wait years for one large reward. A pool shares the rewards by work done, so the income is small but steady.
:::
::::

:::: {.flashcard #card-blocks-and-mining-020}
Why can a mining pool not change Bitcoin's rules?

::: back
Nodes check every block for themselves and ignore one that breaks the rules, however much hash power stands behind it.
:::
::::
