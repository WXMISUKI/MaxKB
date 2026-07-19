# Pilot Dataset Specification

## ADDED Requirements

### Requirement: Project-level logical knowledge base

The pilot SHALL use one project-level logical knowledge base for the first construction supervision review scenario.

#### Scenario: Pilot knowledge base is created

- **WHEN** the local MaxKB pilot is initialized
- **THEN** it creates or identifies a knowledge base for `南江至东岭高速公路改扩建工程 JD-A1`
- **AND** all pilot documents are associated with `project_id=project-njdl-jd-a1`

### Requirement: Metadata-filtered review scope

The pilot SHALL preserve review scope through metadata rather than relying on document names alone.

#### Scenario: LJ-01 opening-condition documents are ingested

- **WHEN** LJ-01 opening-condition documents are added
- **THEN** each document includes project, contract package, supervision section, subcontract team, review task, basis version, document type, source object, effective status, and indexed time metadata

#### Scenario: A review query is executed

- **WHEN** a query asks about LJ-01 opening-condition readiness
- **THEN** retrieval can be filtered to `subcontract_team_id=team-lj-01` and `review_task_id=opening-condition-lj01`

### Requirement: Construction-plan review evidence

The pilot SHALL include enough construction-plan material to test plan review retrieval.

#### Scenario: Roadbed filling plan is reviewed

- **WHEN** a query asks whether the K12+000-K18+500 roadbed filling construction plan is acceptable
- **THEN** retrieval can return the plan, quality control plan, material test summary, safety risk controls, project basis, and relevant official-source summaries

### Requirement: Official-source registry

The pilot SHALL record official standard and policy sources before any source material is added to the knowledge base.

#### Scenario: A standard is used as review basis

- **WHEN** a standard such as JTG G10-2016, JTG F80/1-2017, JTG F90-2015, or JTG/T 3610-2019 is referenced
- **THEN** the pilot records title, standard number, issuing authority, official URL, recommended usage, and ingestion status

#### Scenario: A source is not clearly official or reusable

- **WHEN** a source is from a non-official mirror, unclear download site, or copyrighted copy
- **THEN** the pilot SHALL NOT store the full file in the knowledge base and may only store a citation or self-written summary

### Requirement: Supportive retrieval only

The pilot SHALL keep retrieval outputs separate from formal review decisions.

#### Scenario: Retrieval supports a review

- **WHEN** MaxKB returns snippets for opening-condition or construction-plan review
- **THEN** those snippets are treated as supportive recall and must not be stored as final approval, rejection, or compliance conclusion without human confirmation

### Requirement: Local validation before customization

The pilot SHALL validate MaxKB knowledge-base capability before backend customization.

#### Scenario: Data pack is generated

- **WHEN** the simulated data pack has been generated
- **THEN** the team uploads it to local MaxKB and records retrieval quality before deciding whether MaxKB source-code changes are needed

