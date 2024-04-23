# rebade
rebade is the Restic Backup Daemon, a friendly frontend for restic. It uses a central JSON configuration
file to manage sources and targets and allows invocation by calling those repositories by name. This
makes it easier to remember complex syntax for repository URIs and such.

It additionally has a daemon component which monitors and tracks user activity
of a system. This enables it to execute a restic system backup after a specific
amount of *activity*. In other words, it is easy to setup a cron job to create
a backup every 6 hours, but rebade only backs up after 6 hours of *work* time,
i.e., time in which there was some input to the system. Activity time is also
persisted (unlike [systemd timers](https://github.com/systemd/systemd/issues/3107)
unfortunately).

## Configuration
There is a configuration file that usually is located in
`/etc/rebade/config.json`. It may look something like this, which is fairly
close to the backup configuration I'm running myself:

```json
{
	"plans": {
		"system-backup": {
			"default": true,
			"source": {
				"paths": [
					"/"
				],
				"exclude": [
					"/proc",
					"/sys",
					"/dev",
					"/var/cache/apt/archives",
					"/run/user",
					"/tmp",
					"/mnt",
					"/media",
					"/run/snapd",
					"/home/joe/.steam/steamapps/common",
					"/home/joe/.cache",
					"/root/.cache"
				]
			},
			"target": {
				"method": "sftp",
				"username": "joe",
				"hostname": "my-backup-server.com",
				"remote_path": "/backup/joe/restic"
			},
			"post_hooks": [
				{
					"method": "http_get",
					"condition": "success",
					"uri": "https://hc-ping.com/ba789f38-cc2f-4f09-8b17-d48c5b99247a"
				}
			],
			"keyfile": "/etc/rebade/backup_key.txt",
			"soft_period_secs": 18000,
			"hard_period_secs": 21600
		}
	}
}
```

Multiple "plans" may be specified, but this configuration knows only one, which
centrally backs up the whole system. When running in daemonized mode, a backup
is started after the period. Note there are two values here, one is set to 5
hours and the other to 6 hours.

What this means is that as soon as the "soft" period is reached, a backup is
triggered only if the user is now absent (no activity recoded for a period of
at least 5 minutes). As soon as the "hard" period is reached, a backup is
triggered in any case. The idea behind this is that when you leave your
computer for a lunch break and we *could* do a backup, do it while the user is
away. After some threshold is reached, perform a backup either way. Note that
the backup is running with minimal nice and ionice settings to be as
non-intrusive as possible.

Also note that after a successful backup, we notify a third-party service so
that we can monitor if backups fail for some reason.

## Usage
If you want to configure daemon mode, place a configuration file and then run:

```
# rebade daemon -a install
```

Which will install and activate a corresponding systemd unit.

## License
GNU GPL-3.
