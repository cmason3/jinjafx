import sys, pathlib, re
from setuptools import setup

__version__ = 'null'
for line in open('jinjafx.py'):
  if line.startswith('__version__'):
    exec(line)
    break

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()
README = re.sub(r'^.*\[<img', '[<img', README, flags=re.DOTALL)
README = re.sub(r'<p.+?</p>', '', README, flags=re.DOTALL)

install_requires = ["jinja2>=3.0", "pytz", "pyyaml", "cryptography>=3.1", "netaddr"]

# if sys.version_info.major == 3 and sys.version_info.minor == 6:
#   install_requires = ["jinja2>=3.0,<3.1", "pytz", "pyyaml", "cryptography>=3.1,<37.0", "netaddr"]

setup(
  name="jinjafx",
  version=__version__,
  python_requires=">=3.9",
  description="JinjaFx - Jinja2 Templating Tool",
  long_description=README,
  long_description_content_type="text/markdown",
  url="https://github.com/cmason3/jinjafx",
  author="Chris Mason",
  author_email="chris@netnix.org",
  license="MIT",
  classifiers=[
    "Development Status :: 5 - Production/Stable",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3"
  ],
  packages=["jinjafx"],
  include_package_data=True,
  package_data={'': ['extensions/*.py']},
  install_requires=install_requires,
  entry_points={
    "console_scripts": [
      "jinjafx=jinjafx:main",
    ]
  }
)
