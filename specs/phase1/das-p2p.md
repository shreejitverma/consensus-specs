# Ethereum 2.0 Phase 1 -- Data Availability Sampling - Network specification

**Notice**: This document is a work-in-progress for researchers and implementers.

## Table of contents

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->


- [Introduction](#introduction)
- [DAS Subnets](#das-subnets)
  - [Horizontal subnets](#horizontal-subnets)
    - [Publishing](#publishing)
    - [Horizontal propagation](#horizontal-propagation)
    - [Horizontal to vertical](#horizontal-to-vertical)
  - [Vertical subnets](#vertical-subnets)
    - [Slow rotation: Backbone](#slow-rotation-backbone)
    - [Quick Rotation: Sampling](#quick-rotation-sampling)
- [DAS in the Gossip domain: Push](#das-in-the-gossip-domain-push)
  - [Topics and messages](#topics-and-messages)
    - [Horizontal subnets: `shard_blob_{shard}`](#horizontal-subnets-shard_blob_shard)
    - [Vertical subnets: `das_sample_{subnet_index}`](#vertical-subnets-das_sample_subnet_index)
- [DAS in the Req-Resp domain: Pull](#das-in-the-req-resp-domain-pull)
  - [Messages](#messages)
    - [DASQuery](#dasquery)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->


## Introduction

For an introduction about DAS itself, see [the DAS participation spec](./das-participation.md#data-availability-sampling).
This is not a pre-requisite for the network layer, but will give you valuable context. 

For sampling, all nodes need to query for `k` random samples each slot.

*__TODO__: describe big picture of sampling workload size*

This is a lot of work, and ideally happens at a low latency.

To achieve quick querying, the query model is changed to *push* the samples to listeners instead, using GossipSub.
The listeners then randomly rotate their subscriptions to keep queries unpredictable.
Except for a small subset of subscriptions, which will function as a backbone to keep topics more stable and allow for efficient peer discovery.

Publishing can utilize the fan-out functionality in GossipSub, and is easier to split between nodes:
nodes on the horizontal networks can help by producing the same samples and fan-out publishing to their own peers.

This push model also helps to obfuscate the original source of a message:
the listeners do not have to make individual queries to some identified source.

The push model does not aim to serve "historical" queries (anything older than the most recent).
Historical queries are still required for the unhappy case, where messages are not pushed quick enough,
and missing samples are not reconstructed by other nodes on the horizontal subnet quick enough.

The main challenge in supporting historical queries is to target the right nodes, 
without concentrating too many requests on a single node, or breaking the network/consensus identity separation.

## DAS Subnets

On a high level, the push-model roles are divided into:
- Sources: create blobs of shard block data, and transformed into many tiny samples. 
- Sinks: continuously look for samples

At full operation, the network has one proposer, per shard, per slot.

In the push-model, there are:
- *Vertical subnets*: Sinks can subscribe to indices of samples: there is a sample to subnet mapping.
- *Horizontal subnets*: Sources need to distribute samples to all vertical networks: they participate in a fanout layer.

### Horizontal subnets

The shift of the distribution responsibility to a proposer can only be achieved with amplification:
a regular proposer cannot reach every vertical subnet.

#### Publishing

To publish their work, proposers propagate the shard block as a whole on a shard-block subnet.

The proposer can fan-out their work more aggressively, by using the fan-out functionality of GossipSub:
it may publish to all its peers on the subnet, instead of just those in its mesh.

#### Horizontal propagation

Peers on the horizontal subnet are expected to at least perform regular propagation of shard blocks, like how do would participate in any other topic.

*Although this may be sufficient for testnets, expect parameter changes in the spec here.*

#### Horizontal to vertical

Nodes on this same subnet can replicate the sampling efficiently (including a proof for each sample),
and distribute it to any vertical networks that are available to them.

Since the messages are content-addressed (instead of origin-stamped), 
multiple publishers of the same samples on a vertical subnet do not hurt performance, 
but actually improve it by shortcutting regular propagation on the vertical subnet, and thus lowering the latency to a sample.


### Vertical subnets

Vertical subnets propagate the samples to every peer that is interested.
These interests are randomly sampled and rotate quickly: although not perfect, 
sufficient to avoid any significant amount of nodes from being 100% predictable.

As soon as a sample is missing after the expected propagation time window,
nodes can divert to the pull-model, or ultimately flag it as unavailable data.

Note that the vertical subnets are shared between the different shards,
and a simple hash function `(shard, slot, sample_index) -> subnet_index` defines which samples go where.
This is to evenly distribute samples to subnets, even when one shard has more activity than the other.

TODO: define `(shard, slot, sample_index) -> subnet_index` hash function.

#### Slow rotation: Backbone

To allow for subscriptions to rotate quickly and randomly, a backbone is formed to help onboard peers into other topics.

This backbone is based on a pure function of the *node* identity and time:
- Nodes can be found *without additional discovery overhead*:
  peers on a vertical topic can be found by searching the local peerstore for identities that hash to the desired topic(s). 
- Nodes can be held accountable for contributing to the backbone:
  peers that particpate in DAS but are not active on the appropriate backbone topics can be scored down.

A node should anticipate backbone topics to subscribe to based their own identity.
These subscriptions rotate slowly, and with different offsets per node identity to avoid sudden network-wide rotations.

```python
# TODO hash function: (node, time)->subnets
```

Backbone subscription work is outlined in the [DAS participation spec](./das-participation.md#slow-rotation-backbone)

#### Quick Rotation: Sampling

A node MUST maintain `k` random subscriptions to topics, and rotate these according to the [DAS participation spec](./das-participation.md#quick-rotation-sampling).
If the node does not already have connected peers on the topic it needs to sample, it can search its peerstore, and if necessary in the DHT, for peers in the topic backbone.

## DAS in the Gossip domain: Push

### Topics and messages

Following the same scheme as the [Phase0 gossip topics](../phase0/p2p-interface.md#topics-and-messages), names and payload types are:
| Name                             | Message Type              |
|----------------------------------|---------------------------|
| `shard_blob_{shard}`             | `SignedShardBlob`         |
| `shard_header_{shard}`           | `SignedShardHeader`       |
| `das_sample_{subnet_index}`      | `DASSample`               |

TODO: separate phase 1 network spec.

#### Horizontal subnets: `shard_blob_{shard}`

Shard block data, in the form of a `SignedShardBlob` is published to the `shard_blob_{shard}` subnets.

If participating in DAS, upon receiving a `signed_blob` for the first time, with a `slot` not older than `MAX_RESAMPLE_TIME`,
a subscriber of a `shard_blob_{shard}` SHOULD reconstruct the samples and publish them to vertical subnets.
Take `blob = signed_blob.blob`:
1. Extend the data: `extended_data = extend_data(blob.data)`
2. Create samples with proofs: `samples = sample_data(blob.slot, blob.shard, extended_data)`
3. Fanout-publish the samples to the vertical subnets of its peers (not all vertical subnets may be reached).

The [DAS participation spec](./das-participation.md#horizontal-subnets) outlines when and where to participate in DAS on horizontal subnets.

The following validations MUST pass before forwarding the `signed_blob` (with inner `blob`) on the horizontal subnet or creating samples for it.
- _[REJECT]_ `blob.shard` MUST match the topic `{shard}` parameter. (And thus within valid shard index range)
- _[IGNORE]_ The `blob` is not from a future slot (with a `MAXIMUM_GOSSIP_CLOCK_DISPARITY` allowance) --
  i.e. validate that `blob.slot <= current_slot`
  (a client MAY queue future blobs for processing at the appropriate slot).
- _[IGNORE]_ The blob is the first blob with valid signature received for the proposer for the `(slot, shard)` combination.
- _[REJECT]_ As already limited by the SSZ list-limit, it is important the blob is well-formatted and not too large.
- _[REJECT]_ The `blob.data` MUST NOT contain any point `p >= MODULUS`. Although it is a `uint256`, not the full 256 bit range is valid.
- _[REJECT]_ The proposer signature, `signed_blob.signature`, is valid with respect to the `proposer_index` pubkey, signed over the SSZ output of `commit_to_data(blob.data)`.
- _[REJECT]_ The blob is proposed by the expected `proposer_index` for the blob's slot.

TODO: make double blob proposals slashable?

#### Vertical subnets: `das_sample_{subnet_index}`

Shard blob samples can be verified with just a 48 byte KZG proof (commitment quotient polynomial), 
against the commitment to blob polynomial, specific to that `(shard, slot)` key.

The following validations MUST pass before forwarding the `sample` on the vertical subnet.
- _[IGNORE]_ The commitment for the (`sample.shard`, `sample.slot`, `sample.index`) tuple must be known.
   If not known, the client MAY queue the sample, if it passes formatting conditions.
- _[REJECT]_ `sample.shard`, `sample.slot` and `sample.index` are hashed into a `sbunet_index` (TODO: define hash) which MUST match the topic `{subnet_index}` parameter.
- _[REJECT]_ `sample.shard` must be within valid range: `0 <= sample.shard < get_active_shard_count(state, compute_epoch_at_slot(sample.slot))`.
- _[REJECT]_ `sample.index` must be within valid range: `0 <= sample.index < sample_count`, where:
    - `sample_count = (points_count + POINTS_PER_SAMPLE - 1) // POINTS_PER_SAMPLE`
    - `points_count` is the length as claimed along with the commitment, which must be smaller than `MAX_SAMPLES_PER_BLOCK`.
- _[IGNORE]_ The `sample` is not from a future slot (with a `MAXIMUM_GOSSIP_CLOCK_DISPARITY` allowance) --
  i.e. validate that `sample.slot <= current_slot`. A client MAY queue future samples for processing at the appropriate slot, if it passed formatting conditions.
- _[IGNORE]_ This is the first received sample with the (`sample.shard`, `sample.slot`, `sample.index`) key tuple.
- _[REJECT]_ As already limited by the SSZ list-limit, it is important the sample data is well-formatted and not too large.
- _[REJECT]_ The `sample.data` MUST NOT contain any point `p >= MODULUS`. Although it is a `uint256`, not the full 256 bit range is valid.
- _[REJECT]_ The `sample.proof` MUST be valid: `verify_sample(sample, sample_count, commitment)`

Upon receiving a valid sample, it SHOULD be retained for a buffer period, if the local node is part of the backbone that covers this sample.
This is to serve other peers that may have missed it.


## DAS in the Req-Resp domain: Pull

To pull samples from nodes, in case of network instability when samples are unavailable, a new query method is added to the Req-Resp domain.

This builds on top of the protocol identification and encoding spec which was introduced in [the Phase0 network spec](../phase0/p2p-interface.md). 

Note that the Phase1 DAS networking uses a different protocol prefix: `/eth2/das/req`

The result codes are extended with:
-  3: **ResourceUnavailable** -- when the request was valid but cannot be served at this point in time.

TODO: unify with phase0? Lighthoue already defined this in their response codes enum.

### Messages

#### DASQuery

**Protocol ID:** `/eth2/das/req/query/1/`

Request Content:
```
(
  sample_index: SampleIndex
)
```

Response Content:
```
(
  DASSample
)
```

When the sample is:
- Available: respond with a `Success` result code, and the encoded sample.
- Expected to be available, but not: respond with a `ResourceUnavailable` result code.
- Not available, but never of interest to the node: respond with an `InvalidRequest` result code.

When the node is part of the backbone and expected to have the sample, the validity of the quest MUST be recognized with `Success` or `ResourceUnavailable`.