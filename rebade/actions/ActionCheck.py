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

from rebade.MultiCommand import LoggingAction
from rebade.Configuration import Configuration
from rebade.BackupEngine import BackupEngine

class ActionCheck(LoggingAction):
	def run(self):
		self._config = Configuration.parse_json_file(self._args.config_file)
		plans = self._config.get_plans_by_name(self._args.plan_name)
		backup_engine = BackupEngine(self._args.restic_binary)
		for plan in plans:
			backup_engine.execute_check(plan)
