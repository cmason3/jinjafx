import pathlib, re
from setuptools import setup

for line in open('jinjafx.py'):
  if line.startswith('__version__'):
    exec(line)
    break

HERE = pathlib.Path(__file__).parent

README = (HERE / "README.md").read_text()
README = re.sub(r'<p.+</p>', '', README)

setup(
  name="jinjafx",
  version=__version__,
  description="JinjaFx - Jinja2 Templating Tool",
  long_description=README,
  long_description_content_type="text/markdown",
  url="https://github.com/cmason3/jinjafx",
  author="Chris Mason",
  author_email="chris@netnix.org",
  license="MIT",
  classifiers=[
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3"
  ],
  packages=["jinjafx"],
  include_package_data=True,
  install_requires=["jinja2", "netaddr"],
  entry_points={
    "console_scripts": [
      "jinjafx=jinjafx:main",
    ]
  }
)
