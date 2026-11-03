---
topic: why-bitcoin
title: Why Bitcoin exists
objectives:
  - 'Explain what double spending is and why digital money has this problem while banknotes do not'
  - 'Describe how a bank prevents double spending and what relying on a trusted third party costs'
  - 'Explain why digital signatures alone cannot stop a double spend'
  - 'Justify why rejecting a double spend takes a public record and one agreed order of transactions'
  - 'Explain why agreeing on which payment came first is hard without a central clock'
---

## Copying is easy, paying is not

Hand someone a banknote and it has left your pocket; the paper can only be in one place. A digital
file behaves the other way round: sending it means making a copy, and you still have the original.
If money were simply a file, you could pay with it as often as you liked.

::: definition
**Double spending**

Paying with the same money more than once, so that two recipients each believe it is now theirs.
:::

::: example
**One coin, two payments**

Alice owns one digital coin worth 0.5 BTC (BTC, short for bitcoin, is the unit of money here). She
writes payment T1, giving the coin to Bob, and payment T2, giving the same coin to Carol. Together
they promise 1 BTC, twice what she has, yet Bob and Carol each hold a payment that looks fine.
"Coin" is a simplification: [Keys and transactions](topic:keys-and-transactions) shows what Bitcoin has instead.
:::

## The usual answer: someone keeps the books

Money in a bank is not an object you hold but an entry in the bank's records. If Alice's coin were
a bank balance, T1 would reduce it to zero and the bank would simply refuse T2. Double spending is
solved, because one party sees every payment and decides.

::: definition
**Ledger**

A record of payments, from which you can work out who owns what. A private ledger is kept by one
party and is visible only to it.
:::

::: definition
**Trusted third party**

An institution, such as a bank, that stands between the two sides of a payment. Both rely on it to
keep the ledger correctly and to treat them fairly.
:::

This works well for most payments, but the white paper lists costs:

- **Payments are never quite final:** the institution settles disputes, so payments can be
  reversed, and sellers ask buyers for extra details and accept some fraud.
- **Small payments do not pay off:** settling disputes costs money, which sets a lower limit.
- **Everything hangs on one company:** the whole money system depends on how it behaves.

Cash avoids all three, but only face to face. A central issuer of digital coins that checks every
payment, which the white paper calls a mint, does not help
either: it stops the double spend and keeps the dependency.

## Why signatures are not enough

Cryptography looks like the obvious way out, and it does solve part of the problem: anyone can
check who approved a payment, with no bank to ask.

::: definition
**Digital signature**

A short piece of data that only the holder of a secret key (the private key) can produce for one
particular message. Anyone can check it with the matching public key, and it stops matching if
the message is changed.
:::

::: warning
**A valid signature does not make a payment safe**

Nobody but Alice can spend Alice's coin, but she can sign both T1 and T2, and both signatures are
genuine. A signature proves that the owner approved this payment, not that the owner approved no
other. It stops thieves, not an owner who pays twice.
:::

## Only the order matters

Here comes the key simplification. To decide between T1 and T2, you need not know who Alice is or
whether she is honest. You only need to know which one came first.

::: theorem
**The rule for conflicts**

Of two payments that spend the same money, the earlier one counts and the later one is rejected.
All this takes is an order that everyone shares.
:::

So Bob needs to know that no earlier payment of this coin exists. But you cannot show that
something is absent unless you could have seen it, which means seeing every payment. A bank can.
Without a bank, every payment has to be announced to everybody, and everybody keeps the record, as
the white paper concludes. Such a recorded payment is a transaction.

::: definition
**Public ledger**

A ledger that anyone can read and copy. Bitcoin's public ledger is the list of all accepted
transactions, and any participant can keep a full copy. It shows amounts and where they move but
no names, although payments can often be linked, see the white paper.
:::

::: definition
**Peer-to-peer network**

A network whose computers, called nodes, talk directly to one another, with no central server that
they all depend on. A node can join or leave whenever it likes.
:::

![A bank alone holds a private ledger, while every node holds its own copy of a public one](fig:why-bitcoin-ledgers)

## Agreeing on "first" without a clock

Announcing every payment moves the problem without ending it. Messages take different times over
different routes, so honest nodes can hear the same two payments in opposite order.

![Alice sends T1 and T2 at the same moment; node A receives T1 first and node B receives T2 first](fig:why-bitcoin-arrival-order)

::: example
**Two honest nodes disagree**

Take the made-up delays from the figure. Node A gets T1 after 40 ms and T2 after 190 ms, so for
150 ms it knows only T1 and then treats T2 as the double spend. Node B gets T2 after 60 ms and T1
after 210 ms, so for 150 ms it knows only T2 and then treats T1 as the double spend.
:::

The obvious fixes fail, because nobody is in charge and some participants may lie:

- **Writing the time on each payment:** the sender chooses it, so Alice can backdate either one.
- **Using the nodes' clocks:** they differ, no official clock exists, and a node can claim any time.
- **Voting per computer or internet address:** one person can cheaply pose as thousands of voters,
  as the white paper notes.

The way out is to ask for less. It does not matter whether T1 really left Alice's computer before
T2; what matters is that all nodes end up with the same order, whichever it is. If they settle on
T2, Carol has been paid and Bob has not, and the ledger is consistent again. So Bob should not hand
over goods the moment he sees T1: at that point it is only a message that has reached some nodes.

::: warning
**"First" does not mean first by the clock**

In Bitcoin, "first" means earlier in the one history the network has agreed on. That order need
not match the order in which things physically happened.
:::

## What Bitcoin sets out to do

::: definition
**Bitcoin**

A system for paying over the internet with no trusted third party, in which a peer-to-peer network
keeps a public ledger and agrees on one order of transactions. Its white paper appeared on
31 October 2008 under the name Satoshi Nakamoto; its first block of transactions, the genesis
block, was mined on 3 January 2009.
:::

The rest of this course takes the open questions one at a time:

| Question | Bitcoin's answer | Chapter |
|---|---|---|
| Who may spend this money? | A signature that anyone can check | [Keys and transactions](topic:keys-and-transactions) |
| How is the order recorded? | Linked blocks that take real computing work to make | [Blocks and mining](topic:blocks-and-mining) |
| How do strangers settle on one history? | Each node checks everything and follows the chain with the most work | [The network and consensus](topic:network-and-consensus) |
| What does this cost, and how can it change? | Scarce block space, electricity, slow rule changes | [Upgrades, scaling and limits](topic:scaling-and-limits) |

::: warning
**"No trusted party" does not mean no assumptions**

You can run the checks yourself, but the design is only safe while honest nodes together control
more computing power than any group of attackers working together, the condition named in the white paper. You also give something up: with no one to mediate,
a payment sent by mistake cannot be called back.
:::

::: takeaways
- Digital money can be copied, so the same money can be paid to two people: double spending.
- A bank prevents this by seeing every payment, at the price of depending on that institution.
- Signatures show who approved a payment, not that the owner approved no other.
- Rejecting a double spend only takes knowing which payment came first, and that takes seeing all
  payments: hence a public ledger.
- Nodes hear payments in different orders and no clock can be trusted, so the hard problem is
  getting strangers to agree on one order, which only has to be the same for everyone.
:::
