## CHANGELOG

#### 1.19.2 - In Development
- Exceptions are now always mapped back to the specific line within the Jinja2 template

#### 1.19.1 - 25<sup>th</sup> March 2024
- Dropped support for Python 3.8
- Added support for using `vars.json` alongside `vars.yml`



#### 1.0.5 - 11<sup>th</sup> May 2020
- Added support for regex style capture groups
- Added support for `jinjafx.fields()`
- Enabled Ansible Core filters if available
- Improved error reporting in JinjaFx Server
- Fixed an issue with elapsed time being incorrect

#### 1.0.4 - 5<sup>th</sup> May 2020
- Added support for `ipaddr` Ansible filters (if Ansible is installed and requires `netaddr` Python module)

#### 1.0.3 - 4<sup>th</sup> May 2020
- Fixed an issue where whitespace options weren't being acted upon

#### 1.0.2 - 3<sup>rd</sup> May 2020
- Added support for the JinjaFx Server

#### 1.0.1 - 29<sup>th</sup> April 2020
- Added support for Jinja2 extensions using the `jinja_extensions` variable

#### 1.0.0 - 20<sup>th</sup> April 2020
- Initial release
