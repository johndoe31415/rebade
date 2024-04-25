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
import math
import contextlib
import subprocess
import requests
from rebade.Configuration import BackupMethod, HookMethod, Condition

class BackupEngine():
	def __init__(self, restic_binary: str, nice: int = 19, ionice_class: str = "idle"):
		self._restic_binary = restic_binary
		self._nice = nice
		self._ionice_class = ionice_class

	def _restic_target_args(self, target):
		match target.method:
			case BackupMethod.SFTP:
				cmd_string = [ "sftp://" ]
				if "username" in target.args:
					cmd_string.append(f"{target.args['username']}@")
				cmd_string.append(target.args['hostname'])
				if "port" in target.args:
					cmd_string.append(f":{target.args['port']}")
				cmd_string.append("/")
				cmd_string.append(target.args["remote_path"])
				return [ "-r", "".join(cmd_string) ]
		raise NotImplementedError(target.method)

	def _restic_remote_args(self, plan: "Plan"):
		args = [ ]
		args += [ "-p", plan.keyfile ]
		args += self._restic_target_args(plan.target)
		return args

	def _restic_backup_args(self, plan: "Plan"):
		args = [ "backup" ]
		args += self._restic_remote_args(plan)
		for exclude in plan.source.exclude:
			args += [ "--exclude", exclude ]
		for path in plan.source.paths:
			args += [ path ]
		return args

	@contextlib.contextmanager
	def execute_pre_post_hooks(self, plan: "BackupPlan"):
		run_args = { }
		self.execute_hooks(plan.pre_hooks, run_args)
		yield run_args
		self.execute_hooks(plan.post_hooks, run_args)

	def _condition_satisfied(self, hook: "Hook", run_args: dict):
		if "condition" not in hook.args:
			return True
		condition = hook.args["condition"]
		match condition:
			case Condition.Success:
				return run_args.get("backup_success", True)

			case Condition.Failure:
				return not run_args.get("backup_success", False)

		return False

	def execute_hook(self, hook: "Hook", run_args: dict):
		if not self._condition_satisfied(hook, run_args):
			return

		match hook.method:
			case HookMethod.HttpGet:
				requests.get(hook.args["uri"])

	def execute_hooks(self, hooks: "BackupPlan", run_args: dict):
		for hook in hooks:
			self.execute_hook(hook, run_args)

	def execute_backup(self, plan: "BackupPlan"):
		with self.execute_pre_post_hooks(plan) as run_args:
			cmd = [ "nice", "-n", str(self._nice) ]
			cmd += [ "ionice", "-c", self._ionice_class ]
			cmd += [ self._restic_binary ] + self._restic_backup_args(plan)
			success = subprocess.run(cmd, check = False).returncode == 0
			run_args["backup_success"] = success
			return success

	def execute_mount(self, plan: "BackupPlan", mountpoint: str):
		with contextlib.suppress(FileExistsError):
			os.makedirs(mountpoint)
		cmd = [ self._restic_binary, "mount" ] + self._restic_remote_args(plan)
		cmd += [ mountpoint ]
		success = subprocess.run(cmd, check = False).returncode == 0
		return success

	def execute_forget(self, plan: "BackupPlan", scale = 1.0):
		time_params = {
			"--keep-monthly": 12 * 3,
			"--keep-weekly": 52,
			"--keep-daily": 3 * 7,
			"--keep-hourly": 24,
		}
		time_params = { key: str(math.ceil(value * scale)) for (key, value) in time_params.items() }

		cmd = [ self._restic_binary, "forget" ] + self._restic_remote_args(plan)
		cmd += [ "--keep-yearly", "unlimited" ]
		for (key, value) in time_params.items():
			cmd += [ key, value ]
		cmd += [ "--prune" ]
		success = subprocess.run(cmd, check = False).returncode == 0
		return success

	def execute_generic_action(self, plan: "BackupPlan", action: str):
		cmd = [ self._restic_binary, action ] + self._restic_remote_args(plan)
		success = subprocess.run(cmd, check = False).returncode == 0
		return success
