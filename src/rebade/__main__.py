#	rebade - Restic backup daemon, a friendly frontend for restic
#	Copyright (C) 2024-2026 Johannes Bauer
#
#	This file is part of rebade.
#
#	rebade is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	rebade is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with rebade; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>

import sys
import rebade
from rebade.MultiCommand import MultiCommand
from rebade.actions.ActionBackup import ActionBackup
from rebade.actions.ActionDaemon import ActionDaemon
from rebade.actions.ActionMount import ActionMount
from rebade.actions.ActionForget import ActionForget
from rebade.actions.ActionGeneric import ActionGeneric
from rebade.actions.ActionCronjob import ActionCronjob

def main():
	mc = MultiCommand(description = "Restic Backup Daemon -- frontend to Restic", trailing_text = f"rebade v{rebade.VERSION}")

	def genparser(parser):
		parser.add_argument("-m", "--max-backup-attempts", type = int, default = 5, help = "When backup fails with a fatal error (i.e., no snapshot was created), rebade will retry a number of times. By default, this number is %(default)d. When set to zero, this means retry infinitely.")
		parser.add_argument("--restic-binary", metavar = "filename", default = "restic", help = "Specifies the restic binary. Defaults to %(default)s.")
		parser.add_argument("-c", "--config-file", metavar = "filename", default = "/etc/rebade/config.json", help = "Specifies the global configuration file. Defaults to %(default)s.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increase verbosity. Can be given multiple times.")
		parser.add_argument("plan_name", nargs = "*", help = "Backup plan(s) to execute. If not specified, uses the default plan.")
	mc.register("backup", "Perform a backup plan", genparser, action = ActionBackup)

	def genparser(parser):
		parser.add_argument("--systemd-unit-filename", metavar = "filename", default = "/etc/systemd/system/rebade-daemon.service", help = "Systemd unit when installing/deinstalling. Defaults to %(default)s.")
		parser.add_argument("-a", "--action", choices = [ "watch", "install", "uninstall" ], default = "watch", help = "Perform a specific action. Can be one of %(choices)s, defaults to %(default)s.")
		parser.add_argument("--restic-binary", metavar = "filename", default = "restic", help = "Specifies the restic binary. Defaults to %(default)s.")
		parser.add_argument("-s", "--state-file", metavar = "filename", default = "/etc/rebade/state.json", help = "Specifies the file in which the state is kept. Defaults to %(default)s.")
		parser.add_argument("-c", "--config-file", metavar = "filename", default = "/etc/rebade/config.json", help = "Specifies the global configuration file. Defaults to %(default)s.")
		parser.add_argument("-t", "--timestep-secs", metavar = "secs", type = int, default = 30, help = "Timestep interval in which to look for activity. Defaults to %(default)d secs.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increase verbosity. Can be given multiple times.")
		parser.add_argument("plan_name", nargs = "*", help = "Backup plan(s) to execute. If not specified, uses the default plan.")
	mc.register("daemon", "Watch for activity and execute backup when a threshold is reached", genparser, action = ActionDaemon)

	def genparser(parser):
		parser.add_argument("--systemd-unit-name", metavar = "name", default = "main", help = "Systemd unit when installing/deinstalling. Defaults to %(default)s.")
		parser.add_argument("-d", "--delete", action = "store_true", help = "Remove the cronjob.")
		parser.add_argument("--restic-binary", metavar = "filename", default = "restic", help = "Specifies the restic binary. Defaults to %(default)s.")
		parser.add_argument("-c", "--config-file", metavar = "filename", default = "/etc/rebade/config.json", help = "Specifies the global configuration file. Defaults to %(default)s.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increase verbosity. Can be given multiple times.")
		parser.add_argument("plan_name", nargs = "*", help = "Backup plan(s) to forget. If not specified, uses the default plan.")
	mc.register("cronjob", "Schedule a systemd timer cronjob that executes the backup plan(s)", genparser, action = ActionCronjob)

	def genparser(parser):
		parser.add_argument("--restic-binary", metavar = "filename", default = "restic", help = "Specifies the restic binary. Defaults to %(default)s.")
		parser.add_argument("-c", "--config-file", metavar = "filename", default = "/etc/rebade/config.json", help = "Specifies the global configuration file. Defaults to %(default)s.")
		parser.add_argument("-m", "--mountpoint", metavar = "path", default = "/mnt/restic", help = "Specifies the mountpoint. Defaults to %(default)s.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increase verbosity. Can be given multiple times.")
		parser.add_argument("plan_name", nargs = "?", help = "Backup plan to mount. If not specified, uses the default plan.")
	mc.register("mount", "Mount a remote backup target", genparser, action = ActionMount)

	def genparser(parser):
		parser.add_argument("--restic-binary", metavar = "filename", default = "restic", help = "Specifies the restic binary. Defaults to %(default)s.")
		parser.add_argument("-c", "--config-file", metavar = "filename", default = "/etc/rebade/config.json", help = "Specifies the global configuration file. Defaults to %(default)s.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increase verbosity. Can be given multiple times.")
		parser.add_argument("plan_name", nargs = "*", help = "Backup plan(s) to forget. If not specified, uses the default plan.")
	mc.register("forget", "Forget remote backup repository snapshot(s)", genparser, action = ActionForget)

	def genparser(parser):
		parser.add_argument("--restic-binary", metavar = "filename", default = "restic", help = "Specifies the restic binary. Defaults to %(default)s.")
		parser.add_argument("-c", "--config-file", metavar = "filename", default = "/etc/rebade/config.json", help = "Specifies the global configuration file. Defaults to %(default)s.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increase verbosity. Can be given multiple times.")
		parser.add_argument("plan_name", nargs = "*", help = "Backup plan(s) to forget. If not specified, uses the default plan.")
	mc.register("unlock", "Remove remote backup repository lock(s)", genparser, action = ActionGeneric)

	def genparser(parser):
		parser.add_argument("--restic-binary", metavar = "filename", default = "restic", help = "Specifies the restic binary. Defaults to %(default)s.")
		parser.add_argument("-c", "--config-file", metavar = "filename", default = "/etc/rebade/config.json", help = "Specifies the global configuration file. Defaults to %(default)s.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increase verbosity. Can be given multiple times.")
		parser.add_argument("plan_name", nargs = "*", help = "Backup plan(s) to forget. If not specified, uses the default plan.")
	mc.register("check", "Check remote backup repository fidelity", genparser, action = ActionGeneric)

	def genparser(parser):
		parser.add_argument("--restic-binary", metavar = "filename", default = "restic", help = "Specifies the restic binary. Defaults to %(default)s.")
		parser.add_argument("-c", "--config-file", metavar = "filename", default = "/etc/rebade/config.json", help = "Specifies the global configuration file. Defaults to %(default)s.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increase verbosity. Can be given multiple times.")
		parser.add_argument("plan_name", nargs = "*", help = "Backup plan(s) to forget. If not specified, uses the default plan.")
	mc.register("snapshots", "List snapshots in remote repository", genparser, action = ActionGeneric)

	def genparser(parser):
		parser.add_argument("--restic-binary", metavar = "filename", default = "restic", help = "Specifies the restic binary. Defaults to %(default)s.")
		parser.add_argument("-c", "--config-file", metavar = "filename", default = "/etc/rebade/config.json", help = "Specifies the global configuration file. Defaults to %(default)s.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increase verbosity. Can be given multiple times.")
		parser.add_argument("plan_name", nargs = "*", help = "Backup plan(s) to forget. If not specified, uses the default plan.")
	mc.register("prune", "Remove unused files from repository", genparser, action = ActionGeneric)

	def genparser(parser):
		parser.add_argument("--restic-binary", metavar = "filename", default = "restic", help = "Specifies the restic binary. Defaults to %(default)s.")
		parser.add_argument("-c", "--config-file", metavar = "filename", default = "/etc/rebade/config.json", help = "Specifies the global configuration file. Defaults to %(default)s.")
		parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increase verbosity. Can be given multiple times.")
		parser.add_argument("plan_name", nargs = "*", help = "Backup plan(s) to forget. If not specified, uses the default plan.")
	mc.register("init", "Initialize a repository", genparser, action = ActionGeneric)

	returncode = mc.run(sys.argv[1:])
	return (returncode or 0)
