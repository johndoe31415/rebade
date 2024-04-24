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
import stat
import enum
import json
from rebade.Exceptions import ConfigurationException, PlanNotFoundException, InsecurePermissionsException, NoDefaultPlanException

class HookMethod(enum.Enum):
	HttpGet = "http_get"

class Condition(enum.Enum):
	Success = "success"
	Failure = "failure"

class Hook():
	def __init__(self, method: HookMethod, condition: Condition, args: dict):
		self._method = method
		self._condition = condition
		self._args = args

	@property
	def method(self):
		return self._method

	@property
	def condition(self):
		return self._condition

	@property
	def args(self):
		return self._args

	@classmethod
	def parse(cls, data: dict):
		method = HookMethod(data["method"])
		condition = Condition(data["condition"])
		match method:
			case HookMethod.HttpGet:
				if not "uri" in data:
					raise ValueError("No 'uri' provided for http_get hook.")
				args = {
					"uri": data["uri"],
				}
		return cls(method = method, condition = condition, args = args)


class BackupSource():
	def __init__(self, paths: list[str], exclude: list[str]):
		self._paths = paths
		self._exclude = exclude

	@property
	def paths(self):
		return self._paths

	@property
	def exclude(self):
		return self._exclude

	@classmethod
	def parse(cls, data: dict):
		paths = data["paths"]
		exclude = data.get("exclude", [ ])
		return cls(paths = paths, exclude = exclude)

class BackupMethod(enum.Enum):
	SFTP = "sftp"

class BackupTarget():
	def __init__(self, method: BackupMethod, args: dict):
		self._method = method
		self._args = args

	@property
	def method(self):
		return self._method

	@property
	def args(self):
		return self._args

	@classmethod
	def parse(cls, data: dict):
		method = BackupMethod(data["method"])
		args = { }
		match method:
			case BackupMethod.SFTP:
				if "username" in data:
					args["username"] = data["username"]
				args["hostname"] = data["hostname"]
				if "port" in data:
					args["port"] = data["port"]
				args["remote_path"] = data["remote_path"]
		return cls(method = method, args = args)

class BackupPlan():
	def __init__(self, name: str, is_default: bool, keyfile: str, soft_period_secs: int, hard_period_secs: int, source: BackupSource, target: BackupTarget, pre_hooks: list[Hook], post_hooks: list[Hook]):
		self._validate_keyfile(keyfile)
		self._name = name
		self._is_default = is_default
		self._keyfile = keyfile
		self._soft_period_secs = soft_period_secs
		self._hard_period_secs = hard_period_secs
		self._source = source
		self._target = target
		self._pre_hooks = pre_hooks
		self._post_hooks = post_hooks

	def _validate_keyfile(self, filename: str):
		mode = stat.S_IMODE(os.stat(filename).st_mode)
		if mode != 0o600:
			raise InsecurePermissionsException(f"Permissions of {filename} expected to be 600 but were {mode:o}. Refusing to work with this keyfile.")

	@property
	def name(self):
		return self._name

	@property
	def is_default(self):
		return self._is_default

	@property
	def keyfile(self):
		return self._keyfile

	@property
	def soft_period_secs(self):
		return self._soft_period_secs

	@property
	def hard_period_secs(self):
		return self._hard_period_secs

	@property
	def source(self):
		return self._source

	@property
	def target(self):
		return self._target

	@property
	def pre_hooks(self):
		return self._pre_hooks

	@property
	def post_hooks(self):
		return self._post_hooks

	@classmethod
	def parse(cls, plan_name: str, plan_data: dict):
		source = BackupSource.parse(plan_data["source"])
		target = BackupTarget.parse(plan_data["target"])
		pre_hooks = [ ] if ("pre_hooks" not in plan_data) else [ Hook.parse(hook_data) for hook_data in plan_data["pre_hooks"] ]
		post_hooks = [ ] if ("post_hooks" not in plan_data) else [ Hook.parse(hook_data) for hook_data in plan_data["post_hooks"] ]
		return cls(name = plan_name, is_default = plan_data.get("default", False), keyfile = plan_data["keyfile"], soft_period_secs = plan_data.get("soft_period_secs", 12 * 3600), hard_period_secs = plan_data.get("hard_period_secs", 16 * 3600), source = source, target = target, pre_hooks = pre_hooks, post_hooks = post_hooks)

class Configuration():
	def __init__(self, plans: dict):
		self._plans = plans
		self._default_plan = None
		self._process_data()

	def get_plan_by_name(self, plan_name: str | None, return_default_plan = False):
		if plan_name not in self._plans:
			if return_default_plan:
				return self.default_plan
			else:
				raise PlanNotFoundException(f"No such plan found: {plan_name}")
		return self._plans[plan_name]

	def get_plans_by_name(self, plan_names: list[str] | None):
		if (plan_names is None) or (len(plan_names) == 0):
			return [ self.default_plan ]
		else:
			return [ self.get_plan_by_name(name) for name in plan_names ]

	def _process_data(self):
		self._default_plan = None
		for plan in self._plans.values():
			if plan.is_default:
				if self._default_plan is not None:
					raise ConfigurationException("Invalid plan configuration, duplicate default plan found.")
				self._default_plan = plan

	@property
	def default_plan(self):
		if self._default_plan is None:
			raise NoDefaultPlanException("No plan defined as default.")
		return self._default_plan

	@classmethod
	def parse_json(cls, json_data: dict):
		plans = { }
		for (plan_name, plan_data) in json_data.get("plans", { }).items():
			plan = BackupPlan.parse(plan_name, plan_data)
			plans[plan_name] = plan
		return cls(plans = plans)

	@classmethod
	def parse_json_file(cls, json_filename: str):
		with open(json_filename) as f:
			return cls.parse_json(json.load(f))
