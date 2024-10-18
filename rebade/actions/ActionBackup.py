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

import time
from rebade.MultiCommand import LoggingAction
from rebade.Configuration import Configuration
from rebade.BackupEngine import BackupEngine
from rebade.Tools import inhibit_suspend

class ActionBackup(LoggingAction):
	def run(self):
		self._config = Configuration.parse_json_file(self._args.config_file)
		backup_engine = BackupEngine(self._args.restic_binary)
		attempt_count = 0
		with inhibit_suspend():
			while True:
				attempt_count += 1
				all_successful = True
				for plan in self._config.get_plans_by_name(self._args.plan_name):
					if not backup_engine.execute_backup(plan):
						all_successful = False

				if all_successful or self._args.oneshot:
					break
				else:
					wait_time_secs = 60
					print(f"Attempt #{attempt_count} was unsuccessful; retrying in {wait_time_secs} seconds...")
					time.sleep(wait_time_secs)
		return 0 if all_successful else 1
