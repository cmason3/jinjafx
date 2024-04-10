## CHANGELOG

### [v1.19.2] - In Development
- Exceptions are now always mapped back to the specific line within the Jinja2 template
- Added an actual `CHANGELOG.md` instead of relying on GitHub Release history

### [v1.19.1] - March 25, 2024
- Dropped support for Python 3.8
- Added support for using `vars.json` alongside `vars.yml`

### [v1.18.7] - January 9, 2024
- Don't use a completely random nonce for `vaulty_encrypt` as it will potentially result in nonce re-use
- Update copyright year to 2024 in all files

### [v1.18.6] - November 30, 2023
- Added support for `ansible.netcommon.vlan_parser` filter
- Added support for `ansible.netcommon.vlan_expander` filter
- Renamed `ext_ansible_ipaddr.py` extension to `ext_ansible_netcommon.py`

#### 1.18.5 - 22<sup>nd</sup> November 2023
- Added support for `summarize_address_range` filter due to a lack of support in the Ansible `ipaddr` filter

#### 1.18.4 - 20<sup>th</sup> November 2023
- Added support for `ipsort` filter which will sort a list of IPv4 and/or IPv6 addresses into numerical order

#### 1.18.3 - 3<sup>rd</sup> November 2023
- Added support for Cisco's Type 10 hashing algorithm (Unix Crypt based SHA512) as used in IOS-XR 64-bit

#### 1.18.2 - 25<sup>th</sup> October 2023
- Added support for row specific hierarchical counters to allow `jinjafx.counter()` to be used for heading numbering (see `README.md` for more details), e.g:

```jinja2
{{ jinjafx.counter('A.') }} Heading
{{ jinjafx.counter('A.A.') }} Heading
{{ jinjafx.counter('A.A.A.') }} Heading
{{ jinjafx.counter('A.A.A.') }} Heading
{{ jinjafx.counter('A.') }} Heading
```

Would result in the following:

```
1. Heading
1.1. Heading
1.1.1. Heading
1.1.2. Heading
2. Heading
```

- `jinjafx.counter()` keys are now case insensitive

#### 1.18.0 - 19<sup>th</sup> October 2023
- Fixed an issue where a Jinja2 template could modify variables within `vars.yml` and the change would persist to subsequent data rows. This was fixed by performing a deep copy instead of a shallow copy before each data row is rendered - hopefully it doesn't have any unexpected consequences

#### 1.17.9 - 27<sup>th</sup> September 2023
- JinjaFx will now display the full output path when writing outputs to file

#### 1.17.8 - 23<sup>rd</sup> September 2023
- Fixed syntax errors on Python <3.8 so version checking works

#### 1.17.7 - 21<sup>st</sup> September 2023
- Enforce minimal Python version in code

#### 1.17.6 - 20<sup>th</sup> August 2023
- Allow `data.csv` to be read from `<stdin>`

#### 1.17.5 - 11<sup>th</sup> August 2023
- Added support for keyless YAML via the `_` website

#### 1.17.4 - 18<sup>th</sup> July 2023
- Added `__all__` variable to `jinjafx.py`

#### 1.17.3 - 28<sup>th</sup> April 2023
- Added support for a looping counter `{n1|n2|n3[:repeat]}`
- Removed debug statement that was left in the previous release

#### 1.17.2 - 28<sup>th</sup> April 2023
- Added support for an optional repeat operator to passive `{start:step[:repeat]}` and active `{start[-end]:step[:repeat]}` counters

#### 1.17.1 - 26<sup>th</sup> April 2023
- Added support for an optional split operator for `jinjafx.first()` and `jinjafx.last()`

#### 1.17.0 - 24<sup>th</sup> April 2023
- Dropped support for Python 3.7
- Added support for `vars` and `varnames` shorthand aliases
- Migrated codebase to use Python's walrus operator
- Migrated type annotations into `README.md`

#### 1.16.2 - 21<sup>st</sup> February 2023
- Fixed typo - rename filter `to_bool` to `bool` to align with Ansible

#### 1.16.1 - 17<sup>th</sup> February 2023
- Further enhancements to Python Type Hints - removed `Any` return type from `__jfx_expand()` and replaced with valid type
- JinjaFx now passes `mypy` validation with `--strict` across entire codebase (added `ignore` directive to Ansible extensions for untyped and resolved other errors)

#### 1.16.0 - 16<sup>th</sup> February 2023
- Python Type Hints (PEP484) have been added to core JinjaFx (`jinjafx.py` and `ext_jinjafx.py`) files and pass `strict` validation with `mypy`
- The Ansible extensions (`ext_ansible_core.py` and `ext_ansible_ipaddr.py`) have been updated so they pass `mypy` validation with `check-untyped-defs` but not `strict` as that is for Ansible upstream to update and then they will be incorporated into JinjaFx
- Fixed an issue where `hwaddr("linux")` wasn't working

#### 1.15.4 - 1<sup>st</sup> February 2023
- Added support for Ansible filter `urlsplit`

#### 1.15.3 - 18<sup>th</sup> January 2023
- Further enhancements to exception handling within templates

#### 1.15.2 - 17<sup>th</sup> January 2023
- Added support for Ansible's `varnames` lookup
- Improved exception handling within templates to include line numbers

#### 1.15.1 - 30<sup>th</sup> December 2022
- Removed support for Python 3.6 due to end of life
- Updated Python build to use `pyproject.toml` to avoid deprecation

#### 1.15.0 - 30<sup>th</sup> December 2022
- Deprecated support for Python 3.6 as it is end of life
- Added support for the "global" section within DataTemplates
- The `xpath` filter only works if the `lxml` python module is present
- Increased version dependency on `cryptography` to remove `default_backend` use
- Moved some of the cryptographic hashes to use `hashlib` as it is faster
- Replaced the deprecated `crypt` module as it will be removed in Python 3.12
- Improved exception handling by displaying more context
- Fixed a Python 3.6 issue with `importlib`

#### 1.14.3 - 14<sup>th</sup> December 2022
- Fixed issue with jinja2 rendering of `vars.yml` with lookup
- Fixed `link_local_query` to use /16 instead of /24
- Update copyright year to 2023 in all files

#### 1.14.2 - 5<sup>th</sup> November 2022
- Added `jinjafx_render_vars` variable to replace command line option `-xg`

#### 1.14.1 - 2<sup>nd</sup> November 2022
- Added `-xg` command line option to disable recursive rendering of global variables

#### 1.14.0 - 2<sup>nd</sup> November 2022
- Support Jinja2 syntax within `vars.yml` which can reference variables it defines

#### 1.13.3 - 30<sup>th</sup> September 2022
- Fixed an issue with `jinjafx.now()` where it wasn't working when passed a timezone

#### 1.13.2 - 19<sup>th</sup> August 2022
- The `JinjaFx()` function will now throw a `MemoryError` exception if required

#### 1.13.1 - 17<sup>th</sup> August 2022
- Fixed `jinjafx_adjust_headers` which was broken in the last release

#### 1.13.0 - 17<sup>th</sup> August 2022
- BREAKING CHANGE - `jinjafx.data` has reluctantly been changed from a list of lists to a function. This has been done to address memory issues with large datasets, where it doubled the memory requirements. Any occurrences of `jinjafx.data[row][col]` will now need to be replaced with `jinjafx.data(row, col)`, which should be functionally the same
- Massive performance improvements following the removal of `deepcopy` and profiling/optimising the code - using a large dataset, processing was improved from 104 seconds down to 8 seconds!
- Further memory reductions by ensuring data doesn't get duplicated multiple times while rows are being expanded
- Added support for `-var` command line argument to pass global Jinja2 variables on the command line
- Fields can now be designated as `:float` in `data.csv` to provide similar behaviour to using `:int`
- Added support for Jinja2's `SandboxedEnvironment` which will be used by JinjaFx Server. When the Sandbox is enabled there is also a global limit of 5000 expansions to limit the size of datasets
- Code re-arrangements to make it more Pythonic and updates to strings to use f-strings for formatting

#### 1.12.3 - 13<sup>th</sup> July 2022
- Backported [ansible/ansible#70337](https://github.com/ansible/ansible/issues/70337) to Ansible Core filters
- Allow `ipaddr` style filters to be used via `ansible.utils.ipaddr`
- Improved exception handling to match Exception explicitly

#### 1.12.2 - 21<sup>st</sup> June 2022
- Added support for an `xpath` filter to manipulate XML and HTML

#### 1.12.1 - 29<sup>th</sup> May 2022
- Changed order of import so extensions will now redefine existing filters if using the same name

#### 1.12.0 - 13<sup>th</sup> May 2022
- Increased `jinja2` minimal version to 3.0.0 to support `jinja2.pass_environment`
- Allow output format to be transparently passed through in templates for JinjaFx Server

#### 1.11.9 - 11<sup>th</sup> May 2022
- Added support for Ansible filter `extract`
- Added support for Ansible filter `flatten`
- Added support for Ansible filter `product`
- Added support for Ansible filter `permutations`
- Added support for Ansible filter `combinations`
- Added support for Ansible filter `unique`
- Added support for Ansible filter `intersect`
- Added support for Ansible filter `difference`
- Added support for Ansible filter `symmetric_difference`
- Added support for Ansible filter `union`
- Added support for Ansible filter `zip`
- Added support for Ansible filter `zip_longest`

#### 1.11.8 - 6<sup>th</sup> May 2022
- Added support for Ansible filter `dict2items`
- Added support for Ansible filter `items2dict`

#### 1.11.7 - 5<sup>th</sup> May 2022
- Added support for Ansible filter `regex_escape`
- Added support for Ansible filter `random`
- Added support for Ansible filter `shuffle`
- Added support for Ansible filter `ternary`

#### 1.11.6 - 1<sup>st</sup> May 2022
- Added `py36` specific wheel to deal with dependencies deprecating Python 3.6 due to EOL (RHEL8 uses 3.6 as default)

#### 1.11.4 - 29<sup>th</sup> April 2022
- Nothing significant - updates to PyPI packaging and `README.md`

#### 1.11.3 - 21<sup>st</sup> April 2022
- Added support for `vaulty_encrypt` and `vaulty_decrypt` using ChaCha20-Poly1305 encryption

#### 1.11.2 - 15<sup>th</sup> April 2022
Added Support for Ansible Tests `contains`, `any` and `all`
Added Support for Ansible Filters `from_yaml` and `from_json`
Updated `lookup` to accept `ansible.builtin.vars` as well as `vars`
Updated `to_yaml` and `to_nice_yaml` to use `SafeDumper`

#### 1.11.1 - 11<sup>th</sup> April 2022
- Added support for `-encrypt` to encrypt strings and files using Ansible Vault
- Added support for `-decrypt` to decrypt strings and files using Ansible Vault

#### 1.11.0 - 5<sup>th</sup> April 2022
- Added support for DataTemplates (`-dt`) with DataSets (`-ds`)
- Updated usage screen to include more detailed output

#### 1.10.4 - 22<sup>nd</sup> March 2022
- Fixed a bug when output tags aren't on their own line and output was being lost

#### 1.10.3 - 22<sup>nd</sup> March 2022
- Added support for the following Ansible core filters: `to_yaml`, `to_nice_yaml`, `to_json`, `to_nice_json`, `to_bool`, `to_datetime` and `strftime`
- Added support for the following Ansible math filters: `log`, `pow` and `root`

#### 1.10.2 - 21<sup>st</sup> March 2022
- Added `ansible_vault_decrypt` public method for JinjaFx Server

#### 1.10.1 - 21<sup>st</sup> March 2022
- Ported Ansible Vault decryption to JinjaFx which completely removes Ansible as a dependency

#### 1.10.0 - 3<sup>rd</sup> March 2022
- Removed support for passing a DataTemplate on the command line using `-dt`
- Removed support for importing Ansible Filters and Tests - provide common ones as JinjaFx extensions (this may cause breakages if a filter was being used that I haven't included)
- Added extension `ext_ansible_core.plugin` for `b64encode`, `b64decode`, `hash`, `regex_replace`, `regex_search` and `regex_findall` filters
- Added extension `ext_ansible_ipaddr.plugin` to port all `ipaddr` filters (i.e. `ipaddr`, `ipmath`, etc)

#### 1.9.5 - 17<sup>th</sup> February 2022
- Added support for `cisco8hash` filter
- Added support for `cisco9hash` filter
- Added support for `junos6hash` filter

#### 1.9.2 - 8<sup>th</sup> February 2022
- Removed legacy Python 2 fudges around `bytes` vs `str` - inputs to `jinjafx()` must now be of type `str`
- Removed support for previously deprecated legacy padding in counters

#### 1.9.1 - 21<sup>st</sup> January 2022
- Fixed an issue when importing Extensions

#### 1.9.0 - 21<sup>st</sup> January 2022
- Added JinjaFx Extension which adds support for `cisco_snmpv3_key`, `junos_snmpv3_key`, `cisco7encode` and `junos9encode` custom filters

#### 1.8.5 - 20<sup>th</sup> January 2022
- Added support for specifying directories to search for Jinja2 Extensions

#### 1.8.4 - 7<sup>th</sup> January 2022
- Added missing `pyyaml` dependency to `setup.py`

#### 1.8.2 - 10<sup>th</sup> December 2021
- Added support for `jinjafx.now()` to output current date and time

#### 1.8.1 - 8<sup>th</sup> December 2021
- Added support for `ansible.builtin.vars` lookup

#### 1.8.0 - 6<sup>th</sup> December 2021
- Added support for the `%` Pad Operator for zero padding on numbers
- Deprecated zero padding on counters in favour of the Pad Operator

#### 1.7.3 - 30<sup>th</sup> November 2021
- Fixed an issue where it couldn't import a `jinja2_extension` from the current directory

#### 1.7.2 - 26<sup>th</sup> November 2021
- Added `__main__.py` so `python3 -m jinjafx` works

#### 1.7.1 - 26<sup>th</sup> November 2021
- Split out jinjafx_server into separate repository
- Improved function and variable encapsulation
- Make jinjafx available as a PyPI module
- Removed support for `jinjafx.nslookup()`

#### 1.7.0 - 20<sup>th</sup> October 2021
##### JinjaFx Server
- Completely removed jQuery dependency and migrated codebase to Bootstrap v5
- Improved the security of the HAProxy Dockerfile by dropping to a non-root user
- Added GZip compression across the board to all aspects of JinjaFx
- Updated `Cache-Control` headers to work better with ETags
- Increased logging verbosity of 404 errors
- Updated CodeMirror library to 5.63.3
- Improved HTTP `<meta>` tags for SEO

#### 1.6.1 - 12<sup>th</sup> October 2021
##### JinjaFx Server
- Dropped support for IE11 - it is a security risk and is holding back development
- Reduced logging output to only show legitimate requests if verbose logging is not enabled
- Updated CodeMirror to 5.63.1 and add `crossorigin` flag to imports
- Fixed a race condition when prompting for DataTemplate password
- Removed all reliance on jQuery outside of Bootstrap 4 modals
- Switched from `moment.js` to `day.js` for time and date stuff
- Updated font size of CSV table as it was too small
- Added support for GZip compression of resources

#### 1.6.0 - 1<sup>st</sup> September 2021
- Added support for `prompt` syntax for JinjaFx Input
- Changed the shebang lines to use Python 3 as Python 2 is EOL
- Commented out `__future__` imports for Python 2 as it is EOL

#### 1.5.7 - 2<sup>nd</sup> July 2021
##### JinjaFx Server
- Terminate gracefully when receiving `SIGTERM` or `SIGINT`

#### 1.5.6 - 17<sup>th</sup> June 2021
##### JinjaFx Server
- Fixed an issue where Ansible Vaulted credentials didn't work
- Reduced Docker image size to around 150MB from over 650MB

#### 1.5.5 - 11<sup>th</sup> June 2021
##### JinjaFx Server
- Logging now includes the number of bytes on POST requests
- Fixed a bug where the reported revision wasn't formatted correctly
- Fixed an issue in IE11 where the CSV data table wasn't showing
- Added support for Jinja2 folding for `template.j2`
- Changed the formatting of `data.csv` CSV table
- Fixed a left radius on the "Update" button
- Updated CodeMirror to v5.61.1

#### 1.5.4 - 11<sup>th</sup> May 2021
- Added support for `jinjafx.warning()`

#### 1.5.3 - 27<sup>th</sup> April 2021
##### JinjaFx Server
- Non-printable ASCII characters are now highlighted in red in the data pane

#### 1.5.2 - 19<sup>th</sup> April 2021
##### JinjaFx Server
- Updated versions of included JavaScript libraries
- Included `Content-Security-Policy` header
- Included `X-Content-Type-Options` header
- Included `Referrer-Policy` header
- Removed all inline style blocks
- Removed all inline script blocks
- Removed support for inline JavaScript in JinjaFx Input Forms

#### 1.5.1 - 13<sup>th</sup> April 2021
##### JinjaFx Server
- Added support for inline JavaScript in JinjaFx Input Forms
- Added support for Jinja2 templating in JinjaFx Input Forms
- Added support for being able to change protection passwords
- Added support for HTTP OPTIONS method

#### 1.5.0 - 6<sup>th</sup> April 2021
##### JinjaFx
- Added support for `match`, `search` and `regex` Ansible tests
##### JinjaFx Server
- Added support for JinjaFx Input Forms
- Added support for Password Protected DataTemplates
- Added support for restoring a pane to it's original size after expanding it
- Added support for fullscreen mode using F11 (or Cmd-Enter on Mac)
- Added support for Ctrl+S and Ctrl+G shortcut keys
- Added support for DataTemplate revisions to mitigate 0-RTT replay attacks
- Added support for ETags to allow cacheing of static content
- Added support for "Copy" button on HTML outputs
- Added support for "Download" button even on single outputs
- Fixed an issue where `template.j2` was being trimmed
- Fixed an issue if `vars.yml` was all commented out

#### 1.4.0 - 10<sup>th</sup> March 2021
##### JinjaFx Server
- Added support for Data Sets - the same template can now be used with different `data.csv`/`vars.yml`
- Log output now hides valid internal .js, .css and .png requests in output
- Updated `viewportMargin` to fix issue an issue where panes weren't showing data until after a redraw event
- Display a `$` sign at the end of the row in `template.j2` to indicate trailing whitespace
- Present a warning if the remote DataTemplate changes after you have made changes locally
- Don't remove comments from `data.csv` when file was being exported or saved
- Added `Cache-Control` header to GET requests to stop data being cached
- Added a "Copy" button on Output window to copy output to clipboard
- Updated CodeMirror and Bootstrap to latest versions

#### 1.3.4 - 24<sup>th</sup> February 2021
- Fixed a code execution security risk in YAML parsing thanks to `@b1nslashsh`
- Fixed an issue where a colon couldn't be used in output names
- Minor tweak to the default pane dimensions in JinjaFx Server
- Improved the formatting of the Generated time and date

#### 1.3.3 - 19<sup>th</sup> February 2021
- Added support for using the longer `ansible.netcommon` prefix for `ipaddr` Ansible filters
- Improved `jinjafx_adjust_headers` variable to specify desired case (upper or lower)
- Updated fields in saved DataTemplates to use valid field names
- Updated CodeMirror from version 5.58.3 to 5.59.2

#### 1.3.2 - 11<sup>th</sup> February 2021
- Fixed an issue where `data.csv` didn't go disabled when waiting
- Split out JinjaFx Server into a separate directory
- Updates to `jinjafx.nslookup` to use `getnameinfo` instead of `gethostbyname`

#### 1.3.1 - 23<sup>rd</sup> January 2021
- Added support for `ANSIBLE_VAULT_PASSWORD_FILE` to match Ansible
- Renamed `ANSIBLE_VAULT_PASS` to `ANSIBLE_VAULT_PASSWORD` for consistency
- Added support for `-m` to merge global variables instead of overwriting duplicate keys
- Added support for API only mode to JinjaFx Server to start without web front end
- JinjaFx Server now makes it obvious if it is waiting for something
- Updated error handling routines and fixed a few minor bugs

#### 1.3.0 - 15<sup>th</sup> December 2020
##### JinjaFx
- Added JinjaFx function `jinjafx.nslookup()` for dns lookups in templates
- Renamed `jfx` symlink to `jinjafx`
##### JinjaFx Server
- Added support for using aws s3 buckets as dt repository
- Added wait cursor when loading dt from repository
- Updated get/put routines for repository to use a unique link per request
- Added rate limit support for get link and update link
- Started to implement support for dt lock files for read only files
##### All
- Stop officially supporting Python 2.7

#### 1.2.3 - 1<sup>st</sup> December 2020
- Added support for `vars.yml` variable `jinjafx_adjust_headers`
- Added support for JinjaFx function `jinjafx.exception()`

#### 1.2.2 - 12<sup>th</sup> November 2020
- Added support for "intelligent bracket auto-escaping"
- Escape characters are now removed from inside capture groups
- Updated `jinjafx_filter` so it is now case sensitive when matching
- Added support for custom sort order in `jinjafx_sort`
- Added support for ordered output blocks

#### 1.2.1 - 30<sup>th</sup> October 2020
- Added `jfx` symlink to jinjafx repository
- Only try to expand static groups if it detects a `|` between parenthesis
- Whitespace is now automatically removed from header fields
- Added `jinjafx.yml` for deploying using Kubernetes

#### 1.2.0 - 13<sup>th</sup> October 2020
- Renamed variable `jinja_extensions` to `jinja2_extensions` in `vars.yml`
- Added support for variable `jinjafx_sort` in `vars.yml`
- Added support for variable `jinjafx_filter` in `vars.yml`
- Added support for declaring a field of type `int`
- Error messages will now contain the original data row number before expansion
- Updated 3rd party libraries to latest versions from `cdnjs`
- Added option `-q` to JinjaFx which suppresses title and version

#### 1.1.6 - 28<sup>th</sup> September 2020
- Better handling of read-only DataTemplates in JinjaFx Server
- JinjaFx now correctly imports the `ipaddr` filter with Ansible 2.10
- Added support to JinjaFx to change the default output directory for relative outputs

#### 1.1.5 - 7<sup>th</sup> September 2020
- Added support to be able to maximise panes in JinjaFx Server
- JinjaFx will now warn if it can't import Ansible filters via `jinjafx.import_filters()`

#### 1.1.4 - 20<sup>th</sup> August 2020
- Added support for Ansible Vaulted strings in `vars.yml`

#### 1.1.3 - 19<sup>th</sup> July 2020
- Active counters and ranges in character classes can now decrement as well as increment

#### 1.1.2 - 9<sup>th</sup> July 2020
- Added support for "Update Link" capability
- Added support for active counters in `jinjafx.expand()`
- Improved error handling - it now reports the data row

#### 1.1.1 - 28<sup>th</sup> June 2020
- Completely rewrote JinjaFx Server web UI using Bootstrap v4.4.1
- Added support for processing JinjaFx DataTemplates to JinjaFx

#### 1.1.0 - 22<sup>nd</sup> June 2020
- Removed propriety DataTemplate format in JinjaFx Server in favour of YAML
- Fixed an issue where the data pane was blank after pasting in JinjaFx Server
- Removed `--ask-vault-pass` in JinjaFx - it now detects if it needs to ask you
- Added support for a vaulted `vars.yml` in JinjaFx Server
- Updated CodeMirror to version 5.55.0 in JinjaFx Server

#### 1.0.10 - 14<sup>th</sup> June 2020
- Added support for comments in `data.csv`
- Error message if it detects invalid characters in header fields
- Minor changes to the link format on "Get Link"
- Fixed an issue with white-space at the beginning of rows
- Cosmetic changes to `data.csv` table in JinjaFx Server

#### 1.0.9 - 9<sup>th</sup> June 2020
- Greatly improved error reporting in templates
- Fixed HTTP status codes for AJAX requests
- Fixed CodeMirror search dialogue
- Added HAProxy rate limit example

#### 1.0.8 - 1<sup>st</sup> June 2020
- Removed Data URL in DataTemplate Export in JinjaFx Server
- Added support for "Get Link" in JinjaFx Server using a Repository Directory
- Added support for data row expansion counters

#### 1.0.7 - 18<sup>th</sup> May 2020
- Added Data URL in DataTemplate Export in JinjaFx Server
- Improved support for tabular view of the `data.csv` window

#### 1.0.6 - 12<sup>th</sup> May 2020
- Fixed regression from previous version where I completely messed up `jinjafx.expand()` with regex capture groups
- The `data.csv` pane in the JinjaFx Server now formats itself into a table when focus is lost

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

[v1.19.1]: https://github.com/cmason3/jinjafx/compare/v1.19.1...v1.18.7
[v1.18.7]: https://github.com/cmason3/jinjafx/compare/v1.18.7...v1.18.6
[v1.18.6]: https://github.com/cmason3/jinjafx/compare/v1.18.6...v1.18.5
