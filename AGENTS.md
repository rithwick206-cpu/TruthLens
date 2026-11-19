# TruthLens Agent Guidelines & Project Rules

TruthLens is a Multimodal Digital Forensics & Deepfake Detection platform. All development follows strict phased execution.

## Core Rules

1. **Architecture Separation**:
   - Backend lives in `backend/` (Python FastAPI + SQLite).
   - Frontend will be built later in `frontend/` after all backend phases pass.
   - Do not write frontend code or ML inference until explicitly requested.

2. **API Contract Integrity**:
   - The single source of truth for all API contracts is `backend/schemas.py`.
   - Never break or remove existing fields without updating `schemas.py` and verifying cross-compatibility.

3. **Digital Evidence Preservation**:
   - Always preserve uploaded original files untouched in `backend/storage/originals/` with calculated SHA-256 hashes.
   - Evidence integrity and forensic traceability must be maintained across all analysis stages.

4. **Automated Verification**:
   - Always verify each phase by running automated `pytest` checks against the FastAPI app before marking a phase complete.
