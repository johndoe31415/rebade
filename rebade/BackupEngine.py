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
import math
import contextlib
import subprocess
import logging
import dataclasses
import requests
from rebade.Configuration import BackupMethod, HookMethod, Condition
from rebade.Tools import FileSystemTools
from rebade.CmdlineEscape import CmdlineEscape
from rebade.Enums import ResticBackupReturncodes

_log = logging.getLogger(__spec__.name)

@dataclasses.dataclass
class ExecutionCommand():
	cmdline: list[str] = dataclasses.field(default_factory = list)
	env: dict = dataclasses.field(default_factory = dict)

	def append(self, args: list[str]):
		self.cmdline += args

	def prepend(self, args: list[str]):
		self.cmdline = args + self.cmdline

class BackupEngine():
	def __init__(self, restic_binary: str, nice: int = 19, ionice_class: str = "idle"):
		self._restic_binary = restic_binary
		self._nice = nice
		self._ionice_class = ionice_class

	def _restic_target_command(self, cmd: ExecutionCommand, target: dict):
		method = BackupMethod(target["method"])
		match method:
			case BackupMethod.SFTP:
				repo_string = [ "sftp://" ]
				if "username" in target:
					repo_string.append(f"{target['username']}@")
				repo_string.append(target["hostname"])
				if "port" in target:
					repo_string.append(f":{target['port']}")
				repo_string.append("/")
				repo_string.append(target["remote_path"])
				cmd.append([ "-r", "".join(repo_string) ])

			case BackupMethod.REST:
				repo_string = [ "rest:" ]
				repo_string.append(target.get("protocol", "https"))
				repo_string += [ "://" ]
				repo_string.append(target["hostname"])
				if "port" in target:
					repo_string.append(f":{target['port']}")
				repo_string.append(target["remote_path"])

				if "username" in target:
					cmd.env["RESTIC_REST_USERNAME"] = target["username"]
				if "password" in target:
					cmd.env["RESTIC_REST_PASSWORD"] = target["password"]

				cmd.append([ "-r", "".join(repo_string) ])
				if "ca_filename" in target:
					cmd.append([ "--cacert", target["ca_filename"] ])

			case BackupMethod.Local:
				cmd.append([ "-r", target["remote_path"] ])

			case _:
				raise NotImplementedError(method)

	def _restic_remote_command(self, cmd: ExecutionCommand, plan: "Plan") -> dict:
		self._restic_target_command(cmd, plan.target)
		cmd.prepend([ "-p", plan.keyfile ])

	def _restic_backup_command(self, cmd: ExecutionCommand, plan: "Plan") -> dict:
		self._restic_remote_command(cmd, plan)
		cmd.prepend([ "backup" ])
		for exclude in plan.source.exclude:
			cmd.append([ "--exclude", exclude ])
		if len(plan.source.only_filesystems) > 0:
			# List filesystems and exclude all those that are not in the list
			for mounted_filesystem in FileSystemTools.get_mounted_filesystems():
				if mounted_filesystem.fstype not in plan.source.only_filesystems:
					cmd.append([ "--exclude", mounted_filesystem.mountpoint ])
		for path in plan.source.paths:
			cmd.append([ path ])

	@contextlib.contextmanager
	def execute_pre_post_hooks(self, plan: "BackupPlan"):
		run_args = { }
		self.execute_hooks(plan.pre_hooks, run_args)
		yield run_args
		self.execute_hooks(plan.post_hooks, run_args)

	def _condition_satisfied(self, hook: "Hook", run_args: dict):
		match hook.condition:
			case Condition.Success:
				return run_args.get("backup_success", True)

			case Condition.Failure:
				return not run_args.get("backup_success", False)

		return False

	def execute_hook(self, hook: "Hook", run_args: dict):
		if not self._condition_satisfied(hook, run_args):
			_log.warning("Skipping hook %s -> condition not satisfied", str(hook))
			return
		_log.debug("Executing hook %s", str(hook))

		match hook.method:
			case HookMethod.HttpGet:
				requests.get(hook.args["uri"])

	def execute_hooks(self, hooks: "BackupPlan", run_args: dict):
		for hook in hooks:
			self.execute_hook(hook, run_args)

	def _run_cmd(self, command: ExecutionCommand) -> int:
		env = dict(os.environ)
		env.update(command.env)
		cmdline = [ "systemd-inhibit", "--who=Rebade backup daemon", "--why=Backup action running", "--mode=delay", "--what=shutdown:sleep" ] + list(command.cmdline)
		_log.debug("Execution of command: %s with %d environment vars", CmdlineEscape().cmdline(cmdline), len(command.env))
		returncode = subprocess.run(cmdline, env = env, check = False).returncode
		return returncode

	def execute_backup(self, plan: "BackupPlan"):
		with self.execute_pre_post_hooks(plan) as run_args:
			command = ExecutionCommand()
			self._restic_backup_command(command, plan)
			command.prepend([ self._restic_binary ])
			command.prepend([ "nice", "-n", str(self._nice) ])
			command.prepend([ "ionice", "-c", self._ionice_class ])
			returncode = self._run_cmd(command)
			try:
				backup_status = ResticBackupReturncodes(returncode)
			except ValueError:
				pass

			# Run the post-hook only if the backup was a complete success (so
			# we get notified if there are only partial snapshots created)
			run_args["backup_success"] = (backup_status == ResticBackupReturncodes.Success)
			return backup_status

	def execute_mount(self, plan: "BackupPlan", mountpoint: str):
		with contextlib.suppress(FileExistsError):
			os.makedirs(mountpoint)
		command = ExecutionCommand()
		self._restic_remote_command(command, plan)
		command.prepend([ self._restic_binary, "mount" ])
		command.append([ mountpoint ])
		return self._run_cmd(command)

	def execute_forget(self, plan: "BackupPlan", scale = 1.0):
		time_params = {
			"--keep-monthly": 12 * 3,
			"--keep-weekly": 52,
			"--keep-daily": 3 * 7,
			"--keep-hourly": 24,
		}
		time_params = { key: str(math.ceil(value * scale)) for (key, value) in time_params.items() }

		command = ExecutionCommand()
		self._restic_remote_command(command, plan)
		command.prepend([ self._restic_binary, "forget" ])
		command.append([ "--keep-yearly", "unlimited" ])

		for (key, value) in time_params.items():
			command.append([ key, value ])
		command.append([ "--prune" ])
		return self._run_cmd(command)

	def execute_generic_action(self, plan: "BackupPlan", action: str):
		command = ExecutionCommand()
		self._restic_remote_command(command, plan)
		command.prepend([ self._restic_binary, action ])
		success = self._run_cmd(command)
		return success
