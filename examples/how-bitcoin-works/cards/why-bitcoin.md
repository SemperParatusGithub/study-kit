---
topic: why-bitcoin
title: 'Flash cards: Why Bitcoin exists'
---

:::: {.flashcard #card-why-bitcoin-001}
What is double spending?

::: back
Paying with the same money more than once, which leaves two recipients each convinced it now belongs to them.
:::
::::

:::: {.flashcard #card-why-bitcoin-002}
Why does digital money have a double-spending problem that banknotes do not have?

::: back
Sending a file makes a copy and leaves you the original, whereas a banknote can only be in one place.
:::
::::

:::: {.flashcard #card-why-bitcoin-003}
How does a bank stop a double spend?

::: back
Every payment goes through its own ledger, so the first one lowers the balance and the bank refuses the second.
:::
::::

:::: {.flashcard #card-why-bitcoin-004}
Why do very small payments not pay off through a trusted third party?

::: back
The institution has to settle disputes, and the cost of doing so sets a lower limit on what is worth paying.
:::
::::

:::: {.flashcard #card-why-bitcoin-005}
Why can a digital signature not stop an owner from paying twice?

::: back
The owner can sign both payments and both signatures are genuine. A signature proves approval of this payment, not that no other was approved.
:::
::::

:::: {.flashcard #card-why-bitcoin-006}
Two payments spend the same money. By which rule is one of them rejected?

::: back
The earlier one counts and the later one is rejected, so all it takes is an order that everyone shares.
:::
::::

:::: {.flashcard #card-why-bitcoin-007}
Without a bank, why must every payment be announced to everybody?

::: back
A recipient has to know that no earlier payment of the same money exists, and you can only show that something is absent if you could have seen it.
:::
::::

:::: {.flashcard #card-why-bitcoin-008}
How can two honest nodes hear the same two payments in opposite order?

::: back
Messages take different times over different routes, so each node may receive a different payment first.
:::
::::

:::: {.flashcard #card-why-bitcoin-009}
Why can the time written on a payment not settle which one came first?

::: back
The sender chooses that time, so it can be backdated.
:::
::::

:::: {.flashcard #card-why-bitcoin-010}
Why does voting per computer or internet address fail as a way of choosing the order?

::: back
One person can cheaply pose as thousands of voters.
:::
::::

:::: {.flashcard #card-why-bitcoin-011}
What does "first" mean for a payment in Bitcoin?

::: back
Earlier in the one history the network has agreed on, which need not match the order in which things physically happened.
:::
::::

:::: {.flashcard #card-why-bitcoin-012}
What condition must hold for Bitcoin's design to stay safe?

::: back
Honest nodes together must control more computing power than any group of attackers working together.
:::
::::
