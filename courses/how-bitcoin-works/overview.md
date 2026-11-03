---
title: Overview
---

## Big picture

Bitcoin is a way to pay someone over the internet with no bank in the middle. Copying a file
is easy, so the hard part of digital money is stopping the same coin from being spent twice.
A bank solves this by keeping the books. Bitcoin hands the books to everyone: many computers
hold the same public record and agree on the order of the entries, although none of them is
in charge and they do not trust one another. Whether you want to hold bitcoin, build
on it or simply judge the claims made about it, the useful question is how that agreement
comes about and what it costs.

The five chapters answer that question from the bottom up.
[Why Bitcoin exists](topic:why-bitcoin) sets out the problem and why ordering transactions is
the heart of it. [Keys and transactions](topic:keys-and-transactions) shows what a payment
actually is. [Blocks and mining](topic:blocks-and-mining) explains how payments are put in a
record that is expensive to rewrite.
[The network and consensus](topic:network-and-consensus) turns to the many independent
computers that enforce the rules and settle on one history. Finally,
[Upgrades, scaling and limits](topic:scaling-and-limits) asks how such a system can change at
all, and where its limits lie.

## Concept map

![The five chapters and how each one builds on the ones before it](fig:topic-map)

## How the parts connect

The thread is one payment, followed from the moment it is signed until it is hard to undo.

It starts with the problem. If nobody keeps an official record, a recipient cannot tell
whether a coin has already gone to somebody else. To reject the second spend you do not need
to know who anyone is; you only need to know which spend came first. Everything later serves
this one need for an agreed order.

A payment then needs a form that anyone can check. There are no accounts in Bitcoin, only
unspent outputs of earlier transactions, each locked so that only the holder of the right
private key can unlock it. A transaction consumes some of these outputs and creates new ones,
and a signature proves the right to do so. Whatever the inputs hold beyond the outputs goes to
the miner as the fee: paying 0.3 BTC out of a 0.5 BTC output with 0.1999 BTC of change leaves
a fee of 0.0001 BTC. A valid signature still says nothing about order, so a double spend is
perfectly possible at this stage.

Order comes from blocks. Miners collect transactions, condense them into a single Merkle root
and search for a block header whose hash falls below a target. Each header contains the hash
of the one before, so changing an old block means redoing the work of every block since. The
work is also rewarded: the first transaction in each block lets the miner claim new coins
plus the fees. Two built-in rules keep this steady. The difficulty is adjusted every 2016
blocks to hold the pace near one block per ten minutes, which makes that period about 14 days,
and the new coins per block halve every 210,000 blocks, or about every four years, so the
supply ends just below 21 million.

Blocks only settle anything if the whole network accepts the same ones. Each full node checks
every transaction and block for itself and follows the valid chain with the most accumulated
work, so when two miners find a block at nearly the same moment, one of the blocks soon goes
stale. The payment from the start of this thread becomes safer with each block on top of it,
which is what a confirmation count measures. An attacker with 10% of the hash power, mining
in secret while five blocks pile up on a payment, has a chance of about 0.09% of ever
overtaking that chain; with 30%, the same chance is about 18%. Even an attacker with a majority can only undo recent history or hold back
transactions, and cannot forge signatures or break the rules that the nodes enforce.

The strengths from these chapters also set the limits in the last one. Because every node
checks everything, block space stays scarce and rule changes need wide agreement. That is the
background to the difference between soft and hard forks, to SegWit and Taproot, and to moving
small payments off the chain into Lightning channels. It is also where the open questions
about energy use, privacy and quantum computers belong.

## How to study this

- Read the chapters in order, since each relies on the one before. The last chapter also draws
  directly on the transaction format from [Keys and transactions](topic:keys-and-transactions).
- At the end of each chapter, describe in your own words what has happened so far to a single
  payment; a gap in that story shows you what to reread.
- Try a chapter's flash cards once you have finished it, answering each one before you turn it
  over, and go back through them a day or two later.
- Use the glossary when a later chapter uses a term you can no longer define exactly, such as
  UTXO, target or stale block, then return to where you stopped.
- Afterwards you should be able to work out a fee and change, explain why a block is costly to
  rewrite, judge how many confirmations a payment needs, and tell a soft fork from a hard fork.
- Further reading: the [Bitcoin white paper](https://bitcoin.org/bitcoin.pdf) and the
  [Bitcoin developer guide](https://developer.bitcoin.org/devguide/).
