#	rebade - Restic backup daemon, a friendly frontend for restic
#	Copyright (C) 2024-2024 Johannes Bauer
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
import glob
import select
import time
import subprocess
import logging
from rebade.StateFile import StateFile
from rebade.MultiCommand import LoggingAction
from rebade.Configuration import Configuration
from rebade.BackupEngine import BackupEngine
from rebade.Tools import inhibit_suspend

_log = logging.getLogger(__spec__.name)

class ActionDaemon(LoggingAction):
	@property
	def systemd_unit_name(self):
		return os.path.basename(self._args.systemd_unit_filename)

	def _open_event_devices(self):
		for filename in glob.glob("/dev/input/event*"):
			f = open(filename, "rb")
			self._descriptors[f.fileno()] = f
			os.set_blocking(f.fileno(), False)

	def _close_event_devices(self):
		for f in self._descriptors.values():
			f.close()

	def _clear_fd(self, fd):
		f = self._descriptors[fd]
		while True:
			# This call to read will OSError ("no such device") if the input
			# device is removed
			if f.read() is None:
				return

	def _clear_all_fds(self):
		for fd in self._descriptors.keys():
			self._clear_fd(fd)

	def _wait_for_action(self, timeout_secs = 20):
		(rlist, wlist, xlist) = select.select([ fd for fd in self._descriptors.keys() ], [ ], [ ], timeout_secs)
		if len(rlist) > 0:
			# Read from all FDs
			for fd in rlist:
				self._clear_fd(fd)
			return True
		else:
			return False

	def _time_tick(self, step_secs = 20):
		t0 = time.time()
		tend = t0 + step_secs

		self._clear_all_fds()
		had_action = self._wait_for_action(step_secs)
		remaining = tend - time.time()
		if remaining > 0:
			time.sleep(remaining)
		t1 = time.time()
		tdiff = t1 - t0
		return had_action and (abs(tdiff - step_secs) < 0.5)

	def _run_loop(self):
		inactivity_secs = 0

		while True:
			if self._time_tick(self._args.timestep_secs):
				# Have activity.
				for plan in self._plans:
					self._state_file.add_activity(plan.name, self._args.timestep_secs)
				inactivity_secs = 0
			else:
				inactivity_secs += self._args.timestep_secs

			# Check if any is above threshold
			execute_plans = [ ]
			now = time.time()
			for plan in self._plans:
				activity_secs = self._state_file.get_activity(plan.name)
				holdoff = self._state_file.get_holdoff(plan.name)
				if inactivity_secs > 5 * 60:
					# User is currently inactive, use the soft threshold
					threshold = plan.soft_period_secs
				else:
					# Use is currently active, only run backup if we hit the hard threshold
					threshold = plan.hard_period_secs

				_log.debug(f"Plan {plan.name} has {activity_secs} secs of activity, holdoff at {holdoff}, threshold at {threshold} secs")
				if (activity_secs > threshold) and (now > holdoff):
					# Add to execution list.
					execute_plans.append(plan)

			if len(execute_plans) > 0:
				with inhibit_suspend():
					for plan in execute_plans:
						_log.info(f"Now executing: {plan.name}")
						if self._backup_engine.execute_backup(plan):
							# Backup successful
							self._state_file.reset_activity(plan.name)
							_log.info(f"Successfully backed up: {plan.name}")
						else:
							# Incur a holdoff, do not reset activity
							holdoff = time.time() + 1800
							self._state_file.set_holdoff(plan.name, holdoff)
							_log.warning(f"Failed to backed up: {plan.name} -- incurring holdoff")

	def _open_run_close(self):
		try:
			self._open_event_devices()
			self._run_loop()
		finally:
			self._close_event_devices()

	def _run_watch(self):
		self._config = Configuration.parse_json_file(self._args.config_file)
		self._plans = self._config.get_plans_by_name(self._args.plan_name)
		self._state_file = StateFile(self._args.state_file)
		self._backup_engine = BackupEngine(self._args.restic_binary)
		self._descriptors = { }
		while True:
			try:
				self._open_run_close()
			except OSError as e:
				delay_secs = 3
				print(f"Caught {e.__class__.__name__}: {str(e)} -- restarting in {delay_secs} seconds", file = sys.stderr)
				time.sleep(delay_secs)

	def _escape(self, cmd):
		# TODO IMPLEMENT ME
		return cmd

	def _run_install(self):
		rebade_binary = os.path.realpath(sys.argv[0])
		with open(self._args.systemd_unit_filename, "w") as f:
			plan_args = "" if (len(self._args.plan_name) == 0) else f" {' '.join(name for name in self._args.plan_name)}"
			print("[Unit]", file = f)
			print("Description=Restic backup daemon (rebade)", file = f)
			print("After=network-online.target", file = f)
			print(file = f)
			print("[Service]", file = f)
			print("Type=simple", file = f)
			print(f"ExecStart={self._escape(rebade_binary)} daemon -a watch --restic-binary {self._escape(self._args.restic_binary)} --state-file {self._escape(self._args.state_file)} --config-file {self._escape(self._args.config_file)} --timestep-secs {self._args.timestep_secs}{plan_args}", file = f)
			print("Environment=\"XDG_CACHE_HOME=/root/.cache\"", file = f)
			print(file = f)
			print("[Install]", file = f)
			print("WantedBy=multi-user.target", file = f)

		subprocess.check_call([ "systemctl", "daemon-reload" ])
		subprocess.check_call([ "systemctl", "enable", self.systemd_unit_name ])
		subprocess.check_call([ "systemctl", "start", self.systemd_unit_name ])

	def _run_uninstall(self):
		subprocess.check_call([ "systemctl", "stop", self.systemd_unit_name ])
		subprocess.check_call([ "systemctl", "disable", self.systemd_unit_name ])
		os.unlink(self._args.systemd_unit_filename)

	def run(self):
		run_method = getattr(self, f"_run_{self._args.action}")
		run_method()
