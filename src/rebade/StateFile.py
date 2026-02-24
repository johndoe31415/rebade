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

import json
import time

class StateFile():
	def __init__(self, filename: str, write_every_secs: int = 300):
		self._filename = filename
		self._write_every_secs = write_every_secs
		try:
			with open(filename) as f:
				self._state = json.load(f)
		except (FileNotFoundError, json.decoder.JSONDecodeError):
			self._state = {
				"activity": { },
				"holdoff": { },
			}
		self._dirty = None

	def add_activity(self, name: str, increment_secs: int):
		if name not in self._state["activity"]:
			self.reset_activity(name)
		self._state["activity"][name] += increment_secs
		self._on_change()

	def reset_activity(self, name: str):
		self._state["activity"][name] = 0
		self._persist()

	def get_activity(self, name: str):
		if name not in self._state["activity"]:
			self.reset_activity(name)
		return self._state["activity"][name]

	def get_holdoff(self, name: str):
		return self._state["holdoff"].get(name, 0)

	def set_holdoff(self, name: str, timestamp: float):
		self._state["holdoff"][name] = timestamp
		self._persist()

	def _on_change(self):
		if self._dirty is None:
			self._dirty = time.time()
		dirty_for = time.time() - self._dirty
		if dirty_for > self._write_every_secs:
			self._persist()

	def _persist(self):
		with open(self._filename, "w") as f:
			json.dump(self._state, f)
		self._dirty = None
