# Changelog

## [v1.19.2] - In Development
- Exceptions are now always mapped back to the specific line within the Jinja2 template
- Added an actual `CHANGELOG.md` instead of relying on GitHub Release history

## [v1.19.1] - March 25, 2024
- Dropped support for Python 3.8
- Added support for using `vars.json` alongside `vars.yml`

## [v1.18.7] - January 9, 2024
- Don't use a completely random nonce for `vaulty_encrypt` as it will potentially result in nonce re-use
- Update copyright year to 2024 in all files

## [v1.18.6] - November 30, 2023
- Added support for `ansible.netcommon.vlan_parser` filter
- Added support for `ansible.netcommon.vlan_expander` filter
- Renamed `ext_ansible_ipaddr.py` extension to `ext_ansible_netcommon.py`
