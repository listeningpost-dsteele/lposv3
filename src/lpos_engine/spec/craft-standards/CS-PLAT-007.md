---
id: CS-PLAT-007
title: Database Reliability, Data Durability, and Recovery Standard
version: 1.0.0
status: Accepted
owner: Listening Post
---

<!-- Generated from LPOS expert corpus v1.2, source SHA-256 fcc787db6f8ab0be691f9030af927005a005561db1c0fecdee5f6dbdc87a060f, source lines 45042-45073. Runtime lifecycle is governed separately. -->

# Database Reliability, Data Durability, and Recovery Standard

Material operational data stores must define:

- engine, version, topology, and owner;
- data classes;
- workload and capacity;
- availability, consistency, and performance requirements;
- replication and lag;
- backup, retention, encryption, and key dependencies;
- RPO and RTO;
- restore and failover procedure;
- integrity validation;
- migration compatibility;
- and operational telemetry.

Backup success is not restore proof. Replication is not disaster recovery. Code rollback is not data rollback.

Reject untested restore, inaccessible keys, destructive unbounded migration, hidden replication lag, incompatible mixed versions, and unsupported engine expertise.
