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

import re
import contextlib
import subprocess
import collections

@contextlib.contextmanager
def inhibit_suspend():
	targets = [
		"sleep.target",
		"suspend.target",
		"hibernate.target",
		"hybrid-sleep.target",
	]
	subprocess.check_call([ "systemctl", "mask", "--runtime" ] + targets)
	yield
	subprocess.check_call([ "systemctl", "unmask", "--runtime" ] + targets)

class FileSystemTools():
	FS_ENTRY_RE = re.compile(r"^(?P<src>[^ ]+) (?P<mntpnt>[^ ]+) (?P<fstype>[^ ]+) ", flags = re.MULTILINE)
	OCT_ESCAPE_RE = re.compile(r"\\(?P<value>[0-7]{3})")
	MountedFileSystem = collections.namedtuple("MountedFileSystem", [ "fstype", "mountpoint" ])

	@classmethod
	def get_mounted_filesystems(cls):
		with open("/proc/mounts") as f:
			for rematch in cls.FS_ENTRY_RE.finditer(f.read()):
				rematch = rematch.groupdict()
				mntpnt = cls.OCT_ESCAPE_RE.sub(lambda innermatch: chr(int(innermatch.groupdict()["value"], 8)), rematch["mntpnt"])
				yield cls.MountedFileSystem(fstype = rematch["fstype"], mountpoint = mntpnt)
