# Changelog

## [1.19.2] - 2024-04-10
- Exceptions are now always mapped back to the specific line within the Jinja2 template
- Added an actual `CHANGELOG.md` instead of relying on GitHub Release history

## [1.19.1] - 2024-03-25
- Dropped support for Python 3.8
- Added support for using `vars.json` alongside `vars.yml`

## [1.18.7] - 2024-01-09
- Don't use a completely random nonce for `vaulty_encrypt` as it will potentially result in nonce re-use
- Update copyright year to 2024 in all files

## [1.18.6] - 2023-11-30
- Added support for `ansible.netcommon.vlan_parser` filter
- Added support for `ansible.netcommon.vlan_expander` filter
- Renamed `ext_ansible_ipaddr.py` extension to `ext_ansible_netcommon.py`
