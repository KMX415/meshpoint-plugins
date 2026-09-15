# Security

Plugins execute with the Meshpoint service account's permissions. Repository
review and integrity checks do not sandbox plugin code.

Report vulnerabilities privately using this repository's GitHub **Security >
Report a vulnerability** feature. Do not include credentials, private messages,
or device configuration in public issues. If private reporting is unavailable,
use the security contact described by the main Meshpoint repository.

No production credentials are required by CI. Pull-request checks use read-only
repository access. Do not add `pull_request_target` workflows that execute PR code.
Do not commit local configuration, captured radio data, identities, or secrets.
