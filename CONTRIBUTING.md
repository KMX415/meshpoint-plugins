# Contributing

Create a branch and open a pull request against `main`. Keep changes scoped to
one plugin or one shared catalog change. Explain the behavior change, compatible
Meshpoint version, automated checks, and any hardware validation performed.
Keep author credits and license notices when adapting outside work.

1. Edit the plugin under `apps/<id>/`.
2. Update its `plugin.toml` version when behavior changes.
3. Run `python scripts/catalog.py --write` to regenerate `repo.json`.
4. Run `python -m unittest discover -s tests`.
5. Check out the core revision from `.github/workflows/ci.yml` and run
   `python scripts/validate.py --core /path/to/meshpoint`.
6. Run relevant core tests with the changed plugin files, as CI does. Report
   hardware testing separately; a parser test is not reception validation.

The compatibility job pins a specific Meshpoint commit. Updating that pin requires
a reviewed PR. A passing CI run does not authorize installation scripts, dependency
upgrades, or new default transmissions without review.

## Reviews and releases

`main` requires the Plugin compatibility check, one independent approval,
code-owner review, and resolved review conversations. New pushes dismiss old
approvals. These rules also apply to administrators. Plugin code can be maintained
by either maintainer; repository administration stays with KMX415. Changes to CI,
catalog tooling, and ownership rules require the same independent code-owner review.

Users install from a commit pinned by Meshpoint's source manager. Merging a PR
does not automatically update installed plugins. Reviewers must keep release-candidate
and experimental status visible until the corresponding hardware checks are complete.
