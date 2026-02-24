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

import os
import sys
import subprocess
import logging
from rebade.MultiCommand import LoggingAction

_log = logging.getLogger(__spec__.name)

class ActionCronjob(LoggingAction):
	@property
	def systemd_unit_name(self):
		return f"rebade-{self._args.systemd_unit_name}"

	@property
	def systemd_service_filename(self):
		return f"/etc/systemd/system/{self.systemd_unit_name}.service"

	@property
	def systemd_timer_filename(self):
		return f"/etc/systemd/system/{self.systemd_unit_name}.timer"

	def _run_install(self):
		rebade_binary = os.path.realpath(sys.argv[0])
		with open(self.systemd_service_filename, "w") as f:
			plan_args = "" if (len(self._args.plan_name) == 0) else f" {' '.join(name for name in self._args.plan_name)}"
			print("[Unit]", file = f)
			print(f"Description=Restic backup task (via rebade) of {plan_args}", file = f)
			print("After=network-online.target", file = f)
			print(file = f)
			print("[Service]", file = f)
			print("Type=oneshot", file = f)
			print(f"ExecStart={self._escape(rebade_binary)} backup {plan_args}", file = f)
			print("Environment=\"XDG_CACHE_HOME=/root/.cache\"", file = f)
			print("Nice=10", file = f)

		with open(self.systemd_timer_filename, "w") as f:
			print("[Unit]", file = f)
			print(f"Description=Restic backup timer (via rebade) of {plan_args}", file = f)
			print(file = f)
			print("[Timer]", file = f)
			print("OnCalendar=*-*-* 22:00:00", file = f)
			print("RandomizedDelaySec=1h", file = f)
			print("Persistent=true", file = f)
			print(file = f)
			print("[Install]", file = f)
			print("WantedBy=timers.target", file = f)

		subprocess.check_call([ "systemctl", "daemon-reload" ])
		subprocess.check_call([ "systemctl", "enable", f"{self.systemd_unit_name}.timer" ])
		subprocess.check_call([ "systemctl", "start", f"{self.systemd_unit_name}.timer" ])

	def _run_uninstall(self):
		subprocess.check_call([ "systemctl", "stop", f"{self.systemd_unit_name}.timer" ])
		subprocess.check_call([ "systemctl", "disable", f"{self.systemd_unit_name}.timer" ])
		os.unlink(self.systemd_service_filename)
		os.unlink(self.systemd_timer_filename)
		subprocess.check_call([ "systemctl", "daemon-reload" ])

	def _escape(self, cmd: list[str]) -> list[str]:
		# TODO IMPLEMENT ME
		return cmd

	def run(self):
		if self._args.delete:
			self._run_uninstall()
		else:
			self._run_install()
