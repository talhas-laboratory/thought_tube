# Layered Transition Folder

Date: 2026-05-19

## Purpose

This folder is the canonical planning surface for the layered transition from the current mixed repo into a cleaner kernel, assembly, surface, and builder-support architecture.

It exists to prevent the migration plan from fragmenting across unrelated docs.

## Document Set

### 00. Transition Plan

Primary migration strategy and architecture direction:

- [00-transition-plan.md](/Users/talhauddin/software/inner_space/docs/plans/layered-transition-2026-05-19/00-transition-plan.md)

### 01. Module Manifest Spec

Contract for how reusable modules are identified, versioned, and described:

- [01-module-manifest-spec.md](/Users/talhauddin/software/inner_space/docs/plans/layered-transition-2026-05-19/01-module-manifest-spec.md)

### 02. Surface Recipe Spec

Contract for how a surface is assembled from reusable modules and adapters:

- [02-surface-recipe-spec.md](/Users/talhauddin/software/inner_space/docs/plans/layered-transition-2026-05-19/02-surface-recipe-spec.md)

### 03. Reference Surface Regression Checklist

Behavioral checklist for preserving the current Inner World reference surface during extraction:

- [03-reference-surface-regression-checklist.md](/Users/talhauddin/software/inner_space/docs/plans/layered-transition-2026-05-19/03-reference-surface-regression-checklist.md)

### 04. First Extraction Tranche Inventory

The first concrete wave of modules to classify, extract, validate, and wire through the new assembly layer:

- [04-first-extraction-tranche-inventory.md](/Users/talhauddin/software/inner_space/docs/plans/layered-transition-2026-05-19/04-first-extraction-tranche-inventory.md)

### 05. Tranche 1 Module Manifests

The first actual manifest set for tranche 1 modules:

- [05-tranche-1-manifests.md](/Users/talhauddin/software/inner_space/docs/plans/layered-transition-2026-05-19/05-tranche-1-manifests.md)

### 06. Execution Planner

Live execution tracker for the transition work:

- [06-execution-planner.md](/Users/talhauddin/software/inner_space/docs/plans/layered-transition-2026-05-19/06-execution-planner.md)

## How To Use This Folder

Read in this order:

1. `00-transition-plan.md`
2. `01-module-manifest-spec.md`
3. `02-surface-recipe-spec.md`
4. `03-reference-surface-regression-checklist.md`
5. `04-first-extraction-tranche-inventory.md`
6. `05-tranche-1-manifests.md`
7. `06-execution-planner.md`

Execution rule:

- no extraction work should begin until the module manifest and recipe spec are accepted
- no broad owner moves should begin until the reference surface regression checklist is accepted
- no code movement should begin until the tranche inventory is assigned and ordered

## Next Expected Additions

Likely next artifacts in this folder:

- dependency-direction rule sheet
- state boundary spec
- extraction criteria checklist
- versioning policy
- architecture governance rule
- assembly bootstrap design

## Canonical Scope

If new migration-planning documents are created for this transition, they should be added to this folder and linked from this index.
