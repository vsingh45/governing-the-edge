#!/usr/bin/env python3
"""
patch_intake_temp0.py
=====================
Sets the intake extraction call to temperature=0.0 so the deterministic
hard-stop predicates receive stable field input across identical runs.

Touches ONLY the intake llm_call in agents/local_agents.py.
Idempotent-guarded: refuses to double-apply.

Run from the repo root:
    python patch_intake_temp0.py
"""
import pathlib, sys

ROOT = pathlib.Path(".").resolve()
MARKER = "# [INTAKE_TEMP0_PATCH]"
TARGET = "agents/local_agents.py"

src = (ROOT / TARGET).read_text()

if MARKER in src:
    sys.exit("Patch already applied (marker found). Aborting to avoid double-apply.")

OLD = "        response_schema=IntakeOutput,\n    )"
NEW = (
    "        response_schema=IntakeOutput,\n"
    f"        temperature=0.0,   {MARKER}\n"
    "    )"
)

if OLD not in src:
    sys.exit(f"ERROR: could not find intake llm_call anchor in {TARGET}. Aborting.")

count = src.count(OLD)
if count != 1:
    sys.exit(f"ERROR: anchor matched {count} times (expected 1). Aborting.")

patched = src.replace(OLD, NEW, 1)
(ROOT / TARGET).write_text(patched)
print(f"  patched {TARGET}: intake llm_call now has temperature=0.0")
print("Done.")
