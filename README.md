# Meshpoint official plugins

The official optional-plugin catalog for [Meshpoint](https://github.com/KMX415/meshpoint).
This initial catalog targets the **v0.8.0 release candidate**. Official ownership
does not change the hardware-validation status of an individual plugin. P25
remains experimental; other receivers still need the hardware signoff described
in the [Meshpoint plugin guide](https://github.com/KMX415/meshpoint/blob/feat/v0.8.0/docs/PLUGINS.md).

## Install

In Meshpoint v0.8.0, open **Settings > Plugins > Manage sources**, enable
**Allow plugin downloads**, and choose **Meshpoint Official (release candidate)**.
For builds without that preset, choose Custom repository and enter:

- Repository: `https://github.com/KMX415/meshpoint-plugins`
- Revision: `main`

Review the source and confirm trust. Meshpoint resolves the revision to a fixed
commit. Updating the source pin and updating each installed plugin are separate,
explicit actions. Installation does not enable a plugin or install native tools.

This catalog contains RTL-SDR, Radio, DAB+, ACARS, ADS-B, RTL433, P2000, Pagers,
POCSAG, Reticulum/LXMF, and the experimental P25 adapter. Install and enable the
RTL-SDR host before its receiver plugins. Follow each plugin's setup instructions.

Einstein's [independent catalog](https://github.com/javastraat/meshpoint-plugins)
remains a separate source for experimental and additional plugins. Its contents
do not automatically become official releases.

## Existing installations

Existing plugins keep their original source, settings, and data. Adding this
catalog does not silently transfer their update source. To switch, back up your
configuration and data, disable the plugin, restart, uninstall it, then reinstall
the same plugin ID from this catalog. Meshpoint retains plugin configuration;
data placed inside a plugin's code directory is removed on uninstall.

The original `apps/` and catalog in Meshpoint are retained as a compatibility
snapshot for existing source pins and regression tests. Future plugin development
belongs here. Reticulum Dashboard, Reticulum Browser, and DAPNET are not included
in this initial migration; they require separate compatibility review.

## Development and ownership

Einstein PD2EMC authored the original receiver and Reticulum integrations.
Meshpoint contributors adapted them to the current runtime. See
[ATTRIBUTION.md](ATTRIBUTION.md) for the exact migration source and history.

Changes go through pull requests, an independent approval, and the required
**Plugin compatibility** check. The check validates the catalog using Meshpoint's
actual installer and manifest parser, then runs the core regression suite with
this repository's plugin files. It does not exercise physical radio hardware.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).
Plugins run with the Meshpoint service's permissions; they are not sandboxed.

## License

AGPL-3.0, as inherited from Meshpoint. Existing third-party notices and credits
remain in their source files. External decoder tools retain their own licenses.
