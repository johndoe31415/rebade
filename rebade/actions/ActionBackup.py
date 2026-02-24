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

import time
import sys
from rebade.MultiCommand import LoggingAction
from rebade.Configuration import Configuration
from rebade.BackupEngine import BackupEngine
from rebade.Enums import ResticBackupReturncodes

class ActionBackup(LoggingAction):
	def run(self):
		self._config = Configuration.parse_json_file(self._args.config_file)
		backup_engine = BackupEngine(self._args.restic_binary)
		attempt_count = 0

		plans = self._config.get_plans_by_name(self._args.plan_name)
		while True:
			repeat_plans = [ ]
			attempt_count += 1
			for plan in plans:
				backup_status = backup_engine.execute_backup(plan)
				if backup_status not in [ ResticBackupReturncodes.Success, ResticBackupReturncodes.IncompleteSnapshot ]:
					# We need to repeat this plan
					print(f"Backup plan {plan.name} failed: {backup_status.name if hasattr(backup_status, 'name') else backup_status}", file = sys.stderr)
					repeat_plans.append(plan)
				else:
					print(f"Backup plan {plan.name} finished: {backup_status.name if hasattr(backup_status, 'name') else backup_status}", file = sys.stderr)

			if (len(repeat_plans) == 0) or ((self._args.max_backup_attempts != 0) and (attempt_count >= self._args.max_backup_attempts)):
				break

			# We need to redo some plans.
			wait_time_secs = 60 * min(attempt_count, 30)
			print(f"Attempt #{attempt_count} was unsuccessful, {len(repeat_plans)} of {len(plans)} failed; retrying in {wait_time_secs} seconds...", file = sys.stderr)
			plans = repeat_plans
			time.sleep(wait_time_secs)
		return 0 if (len(repeat_plans) == 0) else 1
