# Controlled Vocabulary – Levels & Outcomes (Draft)

## Purpose
This document defines the standardized **log levels** and **outcomes** used across all domains in the ULog project.  
The goal is to ensure consistent interpretation of log severity and process results across teams and systems.

---

## Levels

| Level | Description | Example |
|-------|--------------|----------|
| **debug** | Detailed internal information for troubleshooting; not shown in production logs. | Model configuration parameters during startup |
| **info** | Normal operational events confirming that the system is working as expected. | Job scheduled successfully |
| **warn** | Indicates a potential issue or unexpected behavior that doesn’t interrupt execution. | Partial data missing; using defaults |
| **error** | A significant problem that caused a specific operation to fail but system remains functional. | Database connection timeout |
| **critical** | A severe problem causing service interruption or system crash. | Model training process terminated unexpectedly |

---

## Outcomes

| Outcome | Description | Derived from |
|----------|--------------|--------------|
| **success** | Task or process completed as expected with no errors. | Slurm: `COMPLETED` |
| **failure** | Task failed due to an error or exception. | Slurm: `FAILED` |
| **timeout** | Task did not finish before the configured time limit. | Slurm: `TIMEOUT` |
| **cancelled** | Task was intentionally stopped by the user or scheduler. | Slurm: `CANCELLED` |
| **running** | Task currently in progress. | Slurm: `RUNNING` |
| **pending** | Task queued but not yet started. | Slurm: `PENDING` |

---

## Design References & Rationale

The **levels** and **outcomes** defined here draw inspiration from both **standardized logging practices** and **HPC job management systems**.

- **Levels** are aligned with the **Syslog severity hierarchy** from [RFC 5424](https://datatracker.ietf.org/doc/html/rfc5424), ensuring interoperability with widely used logging frameworks.  
- **Outcomes** follow the **state model of Slurm Workload Manager**, reflecting real-world workflow and cluster job lifecycles (`COMPLETED`, `FAILED`, `TIMEOUT`, etc.).

---

## Example Mapping

| Raw Log Message | Mapped Level | Mapped Outcome |
|-----------------|---------------|----------------|
| “Job 456 completed successfully.” | info | success |
| “Job 457 failed due to file not found.” | error | failure |
| “Job 458 cancelled by user.” | warn | cancelled |
| “Job 459 still running after 3h.” | info | running |
| “Job 460 exceeded walltime.” | error | timeout |

---

*Author: Sanaa Amina GOURINE  
*Contributor to: Omdena ULog Project – Sprint 1 (Controlled Vocabulary)* - Subtask 1 (Levels and Outcomes)* 
