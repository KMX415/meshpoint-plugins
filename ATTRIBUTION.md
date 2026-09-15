# Attribution and migration provenance

The initial `apps/` tree is an unchanged export of:

- Repository: https://github.com/KMX415/meshpoint
- Commit: `d476e29618dc2e1577cd137c3a282f9c3547edb1`
- Original path: `apps/`
- History: https://github.com/KMX415/meshpoint/commits/d476e29618dc2e1577cd137c3a282f9c3547edb1/apps

Albert Einstein (Einstein PD2EMC, GitHub `javastraat`) authored the original
Reticulum and RTL-SDR receiver integrations in
https://github.com/javastraat/meshpoint. KMX415 and Meshpoint contributors adapted
those integrations for the Meshpoint plugin runtime, process isolation, source
installation, and lifecycle handling. The P25 adapter credits Meshpoint contributors
and the upstream OP25 project in its manifest.

This repository starts with a source snapshot rather than rewriting the original
Git history. `UPSTREAM_HISTORY.txt` preserves the source repository's plugin commit
messages, authors, commit IDs, and contributor trailers. All in-file third-party
notices have been retained. The copied root LICENSE governs the inherited code;
it does not replace any additional notices or external tools' licenses.
