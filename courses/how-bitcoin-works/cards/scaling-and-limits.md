---
topic: scaling-and-limits
title: 'Flash cards: upgrades, scaling and limits'
---

:::: {.flashcard #card-scaling-and-limits-001}
What happens to a node that does not upgrade when a soft fork takes effect?

::: back
It goes on accepting the new blocks, because the new rules only narrow down the old ones.
:::
::::

:::: {.flashcard #card-scaling-and-limits-002}
Why can a hard fork split the chain for good?

::: back
It loosens the rules, so nodes left on the old software reject some new blocks. Unless nearly everyone upgrades, the two groups never agree on one chain again.
:::
::::

:::: {.flashcard #card-scaling-and-limits-003}
Why is block space kept scarce on purpose?

::: back
Every full node checks every block, so larger blocks make a node more costly to run. Checking the rules would then drift to a few large operators, the kind of trust Bitcoin set out to remove.
:::
::::

:::: {.flashcard #card-scaling-and-limits-004}
Why could SegWit be introduced as a soft fork?

::: back
It moved signatures to a place old nodes never look at, so to them a block still appears to be at most 1 MB.
:::
::::

:::: {.flashcard #card-scaling-and-limits-005}
What is the weight of a block with 800,000 non-witness and 800,000 witness bytes?

::: back
$4 \cdot 800000 + 800000 = 4000000$ units. That is exactly the limit, although the block is only 1.6 MB.
:::
::::

:::: {.flashcard #card-scaling-and-limits-006}
What are the two ways to spend a Taproot output?

::: back
With one signature, or by revealing one script from a set of alternatives. When the signature is used, the alternatives never appear on the chain.
:::
::::

:::: {.flashcard #card-scaling-and-limits-007}
Which steps of a payment channel touch the chain?

::: back
Only opening and closing. Every state in between is a signed transaction that the two parties keep unpublished.
:::
::::

:::: {.flashcard #card-scaling-and-limits-008}
What keeps a channel partner from closing with an old state that suits them better?

::: back
The other party can then claim all the funds in the channel as a penalty.
:::
::::

:::: {.flashcard #card-scaling-and-limits-009}
Alice pays Bob through Carol with chained HTLCs. Why does Carol not lose money when Bob collects from her?

::: back
Bob can collect only by revealing the secret behind the hash, and Carol then uses that same secret to collect from Alice.
:::
::::

:::: {.flashcard #card-scaling-and-limits-010}
Why is energy per transaction a misleading measure for Bitcoin?

::: back
Mining secures blocks, not single transactions. A nearly empty block takes the same work as a full one, so more transactions do not directly mean more electricity.
:::
::::

:::: {.flashcard #card-scaling-and-limits-011}
Why is Bitcoin called pseudonymous rather than anonymous?

::: back
People act under an alias instead of a real name, yet every transaction is public and chain analysis can link addresses, reused ones above all.
:::
::::

:::: {.flashcard #card-scaling-and-limits-012}
Which part of Bitcoin would a large enough quantum computer threaten?

::: back
The signatures rather than the hashes, which would call for a further upgrade.
:::
::::
