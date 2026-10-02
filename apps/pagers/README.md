# pagers

Optional Meshpoint receiver plugin, adapted from javastraat/meshpoint at `b18d6742de6c4cf7fb2e743c690400bea5790a9f`. Original author: Einstein PD2EMC.

This folder is catalog source, not an installed or enabled module. Install only the modules you want through Settings > Plugins. Receiver modules use the optional RTL-SDR host page; install and enable `rtlsdr` as well. Restart after enabling.

Required commands: rtl_fm, multimon-ng. Install the documented native tools on the device before enabling this module. Setup does not run automatically. See [the optional plugin guide](../../docs/PLUGINS.md) for package availability, setup limitations, hardware sharing, and removal.

Enabling creates an idle listener. Press Start in the plugin page to open the receiver. A running receiver holds the shared SDR until stopped; switching pages does not interrupt it.

This is unreleased integration work. Tests use mocked processes; device and RF validation remains required before release.

## Frequency selection

Enter a local receive frequency before starting; there is no implicit local
channel. The page validates a value in the adapter's 24 to 1766 MHz input range;
that range does not establish hardware coverage or usable reception. Stop
before retuning. Page selections last for the running Meshpoint session.
For a persistent default, configure `plugins.pagers.frequency_mhz`.
See [receiver regions](../../docs/PLUGINS.md#receiver-regions-and-local-channels).


## Unattended listening

Start reception, then enable **Keep running** to continue listening after
leaving the tab. Administrators can change this setting without a restart;
it is saved as `plugins.pagers.keep_running`. Turning it off starts
a fresh 10-minute idle timeout. The setting defaults off and does not start
reception automatically after a reboot. Stop releases the shared dongle.
