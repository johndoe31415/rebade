import setuptools

with open("README.md") as f:
	long_description = f.read()

setuptools.setup(
	name = "rebade",
	packages = setuptools.find_packages(),
	version = "0.0.1rc0",
	license = "gpl-3.0",
	description = "Restic backup daemon: a friendly frontend for restic",
	long_description = long_description,
	long_description_content_type = "text/markdown",
	author = "Johannes Bauer",
	author_email = "joe@johannes-bauer.com",
	url = "https://github.com/johndoe31415/rebade",
	download_url = "https://github.com/johndoe31415/rebade/archive/v0.0.1rc0.tar.gz",
	keywords = [ "restic", "backup", "daemon" ],
	install_requires = [
		"requests"
	],
	entry_points = {
		"console_scripts": [
			"rebade = rebade.__main__:main"
		]
	},
	include_package_data = False,
	classifiers = [
		"Development Status :: 5 - Production/Stable",
		"Intended Audience :: Developers",
		"License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
		"Programming Language :: Python :: 3",
		"Programming Language :: Python :: 3 :: Only",
		"Programming Language :: Python :: 3.10",
	],
)
