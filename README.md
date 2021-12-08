[![PyPI](https://img.shields.io/pypi/v/jinjafx.svg)](https://pypi.python.org/pypi/jinjafx/)
![Python](https://img.shields.io/badge/python-≥&nbsp;3.6-orange)
![Size](https://img.shields.io/github/languages/code-size/cmason3/jinjafx?label=size)
[<img src="https://img.shields.io/badge/url-https%3A%2F%2Fjinjafx.io-blue" align="right">](https://jinjafx.io)

<h1 align="center">JinjaFx - Jinja2 Templating Tool</h1>

<p align="center"><a href="#jinjafx-usage">JinjaFx Usage</a> || <a href="#jinjafx-templates">JinjaFx Templates</a> || <a href="#ansible-filters">Ansible Filters</a> || <a href="#jinjafx-variables">JinjaFx Variables</a><br /><a href="#jinjafx-input">JinjaFx Input</a> || <a href="#jinja2-extensions">Jinja2 Extensions</a> || <a href="#jinjafx-datatemplates">JinjaFx DataTemplates</a> || <a href="#jinjafx-built-ins">JinjaFx Built-Ins</a></p>

JinjaFx is a Templating Tool that uses [Jinja2](https://jinja.palletsprojects.com/en/3.0.x/templates/) as the templating engine. It is written in Python and is extremely lightweight and hopefully simple - it doesn't require any Python modules that aren't in the base install, with the exception of [jinja2](https://pypi.org/project/Jinja2/) for obvious reasons, and [ansible](https://pypi.org/project/ansible/) if you want to decrypt Ansible Vaulted files and strings or use custom Ansible filters.

JinjaFx differs from the Ansible "template" module as it allows data to be specified in a dynamic "csv" format as well as multiple yaml files. Providing data in "csv" format is easier if the data originates from a spreadsheet or is already in a tabular format. In networking it is common to find a list of physical connections within a patching schedule, which has each connection on a different row - this format isn't easily transposed into yaml, hence the need to be able to use "csv" as a data format in these scenarios.

### Installation

```
python3 -m pip install --upgrade --user jinjafx [ansible-core]
```

### JinjaFx Usage

```
 jinjafx (-t <template.j2> [-d <data.csv>] | -dt <dt.yml>) [-g <vars.yml>] [-o <output file>] [-od <output dir>] [-m] [-q]
   -t <template.j2>              - specify a Jinja2 template
   -d <data.csv>                 - specify row/column based data (comma or tab separated)
   -dt <dt.yml>                  - specify a JinjaFx DataTemplate (contains template and data)
   -g <vars.yml>[, -g ...]       - specify global variables in yaml (supports Ansible vaulted files and strings)
   -o <output file>              - specify the output file (supports Jinja2 variables) (default is stdout)
   -od <output dir>              - change the output dir for output files with a relative path (default is ".")
   -m                            - merge duplicate global variables (dicts and lists) instead of overwriting keys
   -q                            - quiet mode - don't output version or usage information
   
 Environment Variables:
   ANSIBLE_VAULT_PASSWORD        - specify an ansible vault password
   ANSIBLE_VAULT_PASSWORD_FILE   - specify an ansible vault password file
```

JinjaFx allows you to specify a text based "csv" file using the `-d` argument - it is composed of a header row and a series of data rows. It supports both comma and tab separated data and will automagically detect what you are using by analysing the header row - it counts the number of occurrences to determine what one is most prevalent. If it detects a "#" at the beginning of a row then that row is ignored as it is treated as a comment.

```
A, B, C    <- HEADER ROW
1, 2, 3    <- DATA ROW 1
4, 5, 6    <- DATA ROW 2
7, 8, 9    <- DATA ROW 3
```

The case-sensitive header row (see `jinjafx_adjust_headers` in [JinjaFx Variables](#jinjafx-variables)) determines the Jinja2 variables that you will use in your template (which means they can only contain `A-Z`, `a-z`, `0-9` or `_` in their value) and the data rows determine the value of that variable for a given row/template combination. Each data row within your data will be passed to the Jinja2 templating engine to construct an output. In addition or instead of the "csv" data, you also have the option to specify multiple yaml files (using the `-g` argument) to include additional variables that would be global to all rows - multiple `-g` arguments can be specified to combine variables from multiple files. If you define the same key in different files then the last file specified will overwrite the key value, unless you specify `-m` which tells JinjaFx to merge keys, although this only works for keys of the same type that are mergable (i.e. dicts and lists). If you do omit the data then the template will still be executed, but with a single empty row of data.

#### RegEx Style Character Classes and Groups

Apart from normal data you can also specify regex based static character classes or static groups as values within the data rows using `(value1|value2|value3)` or `[a-f]`. These will be expanded using the `jinjafx.expand()` function to multiple rows, for example:

```
DEVICE, TYPE
us(ma|n[yh]|tx)-pe-1[ab], pe
```

The above would be expanded to the following, which JinjaFx would then loop through like normal rows (be careful as you can easily create huge data sets with no boundaries) - if you do wish to use literal brackets then they would need to be escaped (e.g. "\\[" or "\\(") - JinjaFx tries to be intelligent with regards to curly brackets - if it thinks you meant to escape them then it will automatically escape them (i.e. if it can't detect a "|" between the brackets and you aren't referencing them in capture groups).

```
DEVICE, TYPE
usma-pe-1a, pe
usma-pe-1b, pe
ustx-pe-1a, pe
ustx-pe-1b, pe
usny-pe-1a, pe
usny-pe-1b, pe
usnh-pe-1a, pe
usnh-pe-1b, pe
```

#### RegEx Style Capture Groups

It also supports the ability to use regex style capture groups in combination with static groups, which allows the following syntax where we have used "\1" to reference the first capture group that appears within the row:

```
DEVICE, INTERFACE, HOST
spine-0[1-3], et-0/0/([1-4]), leaf-0\1
```

The above would then be expanded to the following, where the leaf number has been populated based on the interface number:

```
DEVICE, INTERFACE, HOST
spine-01, et-0/0/1, leaf-01
spine-01, et-0/0/2, leaf-02
spine-01, et-0/0/3, leaf-03
spine-01, et-0/0/4, leaf-04
spine-02, et-0/0/1, leaf-01
spine-02, et-0/0/2, leaf-02
spine-02, et-0/0/3, leaf-03
spine-02, et-0/0/4, leaf-04
spine-03, et-0/0/1, leaf-01
spine-03, et-0/0/2, leaf-02
spine-03, et-0/0/3, leaf-03
spine-03, et-0/0/4, leaf-04
```

#### Expansion Counters

We also support the ability to use active and passive counters during data expansion with the `{ start[-end]:step }` syntax (step must be positive) - counters are row specific (i.e. they don't persist between different rows). Active counters are easier to explain as they are used to expand rows based on a start and end number (they are bounded) as per the example below. In this instance as we have specified a start (0) and an end (9) it will expand the row to 10 rows using the values from 0 to 9 (i.e. 'et-0/0/0' to 'et-0/0/9').

```
INTERFACE
et-0/0/{0-9:1}
```

Passive counters (i.e. counters where you don't specify an end) don't actually create any additional rows or determine the range of the expansion (they are unbounded). They are used in combination with static character classes, static groups or active counters to increment as the data is expanded into multiple rows. If we take our previous example and modify it to allocate a HOST field to each interface, which uses a number starting at 33, then the following (see 'Pad Operator' for explanation of `%3`):

```
INTERFACE, HOST
et-0/0/{0-9:1}, r740-{33:1}%3
```

Would be expanded to the following (we haven't actually specified 42 as the end number, but it will increment based on the number of rows it is being expanded into):

```
INTERFACE, HOST
et-0/0/0, r740-033
et-0/0/1, r740-034
et-0/0/2, r740-035
et-0/0/3, r740-036
et-0/0/4, r740-037
et-0/0/5, r740-038
et-0/0/6, r740-039
et-0/0/7, r740-040
et-0/0/8, r740-041
et-0/0/9, r740-042
```

#### Field Values

By default all field values are treated as strings which means you need to use the `int` filter (e.g. `{{ NUMBER|int }}`) if you wish to perform mathematical functions on them (e.g. `{{ NUMBER|int + 1 }}`). If you have a field where all the values are numbers and you wish them to be treated as numerical values without having to use the `int` filter, then you can suffix `:int` onto the field name (if it detects a non-numerical value in the data then an error will occur), e.g:

```
NUMBER:int, NAME
1, one
10, ten
2, two
20, twenty
```

#### Pad Operator

JinjaFx supports the ability to add or remove leading zeros from numbers using the `%` pad operator. The pad operator is used by suffixing a `%` to a number followed by the number of zeros to pad the number to (e.g. `100%4` would result in `0100` and `003%0` would result in `3`). Using the following example, we might want to have no padding on the `INTERFACE` field but pad the `HOST` field to 2 characters, e.g:

```
DEVICE, INTERFACE, HOST
spine-01, et-0/0/\1%0, leaf-(0[1-4]|1[0-3])
```

This would then be expanded to the following:

```
DEVICE, INTERFACE, HOST
spine-01, et-0/0/1, leaf-01
spine-01, et-0/0/2, leaf-02
spine-01, et-0/0/3, leaf-03
spine-01, et-0/0/4, leaf-04
spine-01, et-0/0/10, leaf-10
spine-01, et-0/0/11, leaf-11
spine-01, et-0/0/12, leaf-12
spine-01, et-0/0/13, leaf-13
```

If you are using capture groups then you need to ensure the `%` character is outside the group (as per the above example) else it will be copied as well. In the event you want to use a `%` character then you can escape it using `\%`.

The `-o` argument is used to specify the output file, as by default the output is sent to `stdout`. This can be a static file, where all the row outputs will be appended, or you can use Jinja2 syntax (e.g. `-o "{{ DEVICE }}.txt"`) to specify a different output file per row. If you specify a directory path then all required directories will be automatically created - any existing files will be overwritten.

### JinjaFx Templates

JinjaFx templates are Jinja2 templates with one exception - they support a JinjaFx specific syntax that allows you to specify a different output file (or `_stdout_` for stdout) within a Jinja2 template to override the value of `-o` (or output name if being used with the JinjaFx Server):

```jinja2
<output "output file">
...
</output>
```

The above syntax is transparent to Jinja2 and will be ignored by Jinja2, but JinjaFx will parse it and use a different output file for the contents of that specific block. Full Jinja2 syntax is supported within the block as well as supporting nested blocks.

This data could then be used in a template as follows, which would output a different text file per "DEVICE":

```jinja2
<output "{{ DEVICE|lower }}.txt">
edit interfaces {{ INTERFACE }}
set description "## Link to {{ HOST }} ##"
</output>
```

You also have the option of specifying a numerical output block index to order them, e.g:

```jinja2
<output "{{ DEVICE|lower }}.txt">[1]
first
</output>
<output "{{ DEVICE|lower }}.txt">[0]
second
</output>
<output "{{ DEVICE|lower }}.txt">[-1]
third
</output>
```

The outputs are then sorted based on the index (the default index if omitted is 0), which results in the following output:

```
third
second
first
```

By default the following Jinja2 templating options are enabled, but they can be overridden as required in the template as per standard Jinja2 syntax:

```
trim_blocks = True
lstrip_blocks = True
keep_trailing_newline = True
```

### Ansible Filters

Jinja2 is commonly used with Ansible which has a wide variety of [custom filters](https://docs.ansible.com/ansible/latest/user_guide/playbooks_filters.html) that can be used in your Jinja2 templates. However, these filters aren't included in Jinja2 as they are part of Ansible. JinjaFx will silently attempt to enable the following Ansible filters if it detects they are installed:

- <b><code>core</code></b>

This contains the "Core" Ansible filters, which includes `groupby`, `b64decode`, `b64encode`, `to_uuid`, `to_json`, `to_nice_json`, `from_json`, `to_yaml`, `to_nice_yaml`, `from_yaml`, `from_yaml_all`, `basename`, `dirname`, `expanduser`, `expandvars`, `realpath`, `relpath`, `splitext`, `win_basename`, `win_dirname`, `win_splitdrive`, `fileglob`, `bool`, `to_datetime`, `strftime`, `quote`, `md5`, `sha1`, `checksum`, `password_hash`, `hash`, `regex_replace`, `regex_escape`, `regex_search`, `regex_findall`, `ternary`, `random`, `shuffle`, `mandatory`, `comment`, `type_debug`, `combine`, `extract`, `flatten`, `dict2items`, `items2dict`, `subelements` and `random_mac`.

- <b><code>ansible.netcommon.ipaddr</code></b>

This filter allows IP address manipulation and is documented in [playbooks_filters_ipaddr.html](https://docs.ansible.com/ansible/latest/user_guide/playbooks_filters_ipaddr.html). To enable this set of filters you will also need to install the [netaddr](https://pypi.org/project/netaddr/) Python module. These filters can be used using the shorter `|ipaddr` syntax as well as the longer `|ansible.netcommon.ipaddr` syntax. The full list of imported filters are `cidr_merge`, `ipaddr`, `ipmath`, `ipwrap`, `ip4_hex`, `ipv4`, `ipv6`, `ipsubnet`, `next_nth_usable`, `network_in_network`, `network_in_usable`, `reduce_on_network`, `nthhost`, `previous_nth_usable`, `slaac`, `hwaddr` and `macaddr`.

### Ansible Tests

In additional to Ansible Filters, Ansible also introduces [tests](https://docs.ansible.com/ansible/latest/user_guide/playbooks_tests.html) that can be performed with various filters (e.g. `select` and `select_attr`) - the following "Core" Ansible tests have been included in JinjaFx: `regex`, `match` and `search`.

### Ansible Lookups

JinjaFx also support the ability to use the [vars lookup](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/vars_lookup.html) builtin to lookup a dynamic variable name (e.g. `{{ lookup('vars', 'my' ~ 'variable', default=None) }}`).

### JinjaFx Variables

The following variables, if defined within `vars.yml` control how JinjaFx works:

- <b><code>jinjafx_adjust_headers</code></b>

There might be some situations where you can't control the format of the header fields that are provided in `data.csv` - it might come from a spreadsheet where someone hasn't been consistent with the header row and has used uppercase in some situations and lowercase in others or they might have used non-standard characters. The header fields are used by Jinja2 as case-sensitive variables and can't contain spaces or punctuation characters - they can only contain alphanumerical characters and the underscore. To help in these situations, the variable `jinjafx_adjust_headers` can be set in `vars.yml` to either "yes", "no" (the default), "upper" or "lower", which will remove any non-standard characters and change the case depending on the value (i.e. "Assigned / Unassigned" would become `ASSIGNEDUNASSIGNED` if the value was "upper" and `AssignedUnassigned` if the value was "yes").

```yaml
---
jinjafx_adjust_headers: "yes" | "no" | "upper" | "lower"
```

- <b><code>jinjafx_filter</code></b> and <b><code>jinjafx_sort</code></b>

JinjaFx supports the ability to filter as well as sort the data within `data.csv` before it is passed to the templating engine. From a filtering perspective, while you could include and exclude certain rows within your `template.j2` with a conditional `if` statement, it won't allow you to use `jinjafx.first()` and `jinjafx.last()` on the reduced data set. This is where the `jinjafx_filter` key which can be specified in `vars.yml` comes into play - it lets you specify using regular expressions what field values you wish to include in your data, e.g:

```yaml
---
jinjafx_filter:
  "HOST": "^r740"
  "INTERFACE": "^et"
```

The above will filter `data.csv` and only include rows where the "HOST" field value starts with "r740" and where the "INTERFACE" field value starts with "et" (by default it performs a case sensitive match, but "(?i)" can be specified at the beginning of the match string to ignore case).

While data is normally processed in the order in which it is provided, it can be sorted through the use of the `jinjafx_sort` key when specified within `vars.yml`. It takes a case-sensitive list of the fields you wish to sort by, which will then sort the data before it is processed, e.g to sort by "HOST" followed by "INTERFACE" you would specify the following:

```yaml
---
jinjafx_sort:
  - "HOST"
  - "INTERFACE"
```

Sorting is in ascending order as standard, but you can prefix the sort key with "+" (for ascending - the default) or "-" (for descending), e.g: "-INTERFACE" would sort the "INTERFACE" field in descending order. By default all fields are treated as strings - this means "2" will get placed after "10" but before "20" if sorted - if you have numbers and wish them to be sorted numerically then you need to ensure you designate the field as numerical using `:int` on the field name.

While sorting is performed in either ascending or descending order, you can also specify a custom sort order using the following syntax:

```yaml
---
jinjafx_sort:
  - "HOST": { "r740-036": -2, "r740-035": -1, "r740-039": 1 }
```

The above syntax allows you to specify an order key for individual field values - by default all fields have an order key of 0, which means the field name is used as the sort key. If you specify an order key < 0 then the field value will appear before the rest and if yo specify an order key > 0 then the values will appear at the end. If multiple field values have the same order key then they are sorted based on actual field value. In the above example, "r740-036" will appear first, "r740-035" will appear second and everything else afterwards, with "r740-039" appearing last.

### JinjaFx Input

There might be some situations where you want inputs to be provided during the generation of the template which are not known beforehand. JinjaFx supports the ability to prompt the user for input using the `jinjafx_input` variable which can be specified in `vars.yml`. The following example demonstrates how we can prompt the user for two inputs ("Name" and "Age") before the template is generated:

```yaml
---
jinjafx_input:
  prompt:
    name: "Name"
    age: "Age"
```

These inputs can then be referenced in your template using `{{ jinjafx_input.name }}` or `{{ jinjafx_input['age'] }}` - the variable name is the field name and the prompt text is the value. However, there might be some situations where you want a certain pattern to be followed or where an input is mandatory, and this is where the advanced syntax comes into play (you can mix and match syntax for different fields):

```yaml
---
jinjafx_input:
  prompt:
    name:
      text: "Name"
      required: True
    age:
      text: "Age"
      required: True
      pattern: "[1-9]+[0-9]*"
```

Under the field the `text` key is always mandatory, but the following optional keys are also valid:

- `required` - can be True or False (default is False)

- `pattern` - a regular expression that the input value must match

- `type` - if set to "password" then echo is turned off - used for inputting sensitive values

### Jinja2 Extensions

Jinja2 supports the ability to provide extended functionality through [extensions](https://jinja.palletsprojects.com/en/2.11.x/extensions/). To enable specific Jinja2 extensions in JinjaFx you can use the `jinja2_extensions` global variable, which you can set within one of your `vars.yml` files (it expects a list):

```yaml
---
jinja2_extensions:
  - 'jinja2.ext.i18n'
  - 'jinja2.ext.loopcontrols'
```

JinjaFx will then attempt to load and enable the extensions that will then be used when processing your Jinja2 templates. You also have the ability to check whether an extensions is loaded within your template by querying `jinja2_extensions` directly.

Unfortunately writing Jinja2 Extensions isn't that obvious - well, I didn't find it that obvious as it took me quite a while to work out how to write a custom filter. Let's assume we want to write a custom filter called `add` that simply adds a value to a number, for example:

```jinja2
{{ 10|add(1) }}
```

We start off by creating our Extension in a file called `jinjafx_extensions.py` (the name of the file is arbitrary) - this file basically defines a new class which extends Extension and a private `__add` method that is mapped to a new filter called `add`:

```python
from jinja2.ext import Extension

class AddExtension(Extension):
  def __init__(self, environment):
    Extension.__init__(self, environment)
    environment.filters['add'] = self.__add

  def __add(self, number, value):
    return number + value
```

We would then use the new Extension by adding the following YAML to our `vars.yml` file - based on the name it will automatically look in `jinjafx_extensions.py` for the `AddExtension` class and will then load and enable the `add` filter.

```yaml
---
jinja2_extensions:
  - 'jinjafx_extensions.AddExtension'
```

### JinjaFx DataTemplates

JinjaFx also supports the ability to combine the data, template and vars into a single YAML file (called a DataTemplate), which you can pass to JinjaFx using `-dt`. This is the same format used by the JinjaFx Server when you click on 'Export DataTemplate'. It uses headers with block indentation to separate out the different components - you must ensure the indentation is maintained on all lines as this is how YAML knows when one section ends and another starts.

```yaml
---
dt:
  data: |2
    ... DATA.CSV ...

  template: |2
    ... TEMPLATE.J2 ...

  vars: |2
    ... VARS.YML ...
```

### JinjaFx Built-Ins

Templates should be written using Jinja2 template syntax to make them compatible with Ansible and other tools which use Jinja2. However, there are a few JinjaFx specific extensions that have been added to make JinjaFx much more powerful when dealing with rows of data, as well as providing some much needed functionality which isn't currently present in Jinja2 (e.g. being able to store persistent variables across templates). These are used within a template like any other variable or function (e.g. `{{ jinjafx.version }}`).

- <b><code>jinjafx.version</code></b>

This variable will contain the current version of JinjaFx as a string (e.g. "1.0.0").

- <b><code>jinjafx.jinja2_version</code></b>

This variable will return the current version of the Jinja2 templating engine as a string (e.g. "2.10.3").

- <b><code>jinjafx.row</code></b>

This variable will contain the current row number being processed as an integer.

- <b><code>jinjafx.rows</code></b>

This variable will contain the total number of rows within the data as an integer.

- <b><code>jinjafx.data[][]</code></b>

This list of lists will contain all the row and column data that JinjaFx is currently traversing through. The first row will contain the header row with subsequent rows containing the row data - it is accessed using `jinjafx.data[row][col]`.

- <b><code>jinjafx.expand("string")</code></b>

This function is used to expand a string that contains static character classes (i.e. `[0-9]`), static groups (i.e. `(a|b)`) or active counters (i.e. `{ start-end:increment }`) into a list of all the different permutations. You are permitted to use as many classes, groups or counters within the same string - if it doesn't detect any classes, groups or counters within the string then the "string" will be returned as the only list element. Character classes support "A-Z", "a-z" and "0-9" characters, whereas static groups allow any string of characters (including static character classes). If you wish to include "[", "]", "(", ")", "{" or "}" literals within the string then they will need to be escaped.

- <b><code>jinjafx.counter(["key"], [increment=1], [start=1])</code></b>

This function is used to provide a persistent counter within a row or between rows. If you specify a `key` then it is a global counter that will persist between rows, but if you don't or you include `jinjafx.row` within the `key`, then the counter only persists within the template of the current row.

- <b><code>jinjafx.exception("message")</code></b>

This function is used to stop processing and raise an exception with a meaningful message - for example, if an expected header field doesn't exist you could use it as follows:

```jinja2
{% if name is not defined %}
  {% set null = jinjafx.exception("header field 'name' is not defined in data") %}
{% endif %}

```

- <b><code>jinjafx.warning("message", [repeat=False])</code></b>

Nearly identical to the previous function, except this won't stop processing of the template but will raise a warning message when the output is generated - this can be specified multiple times for multiple warnings, although repeated warnings are suppressed unless you set the second parameter to True.

- <b><code>jinjafx.first([fields[]], [{ "filter_field": "regex", ... }])</code></b>

This function is used to determine whether this is the first row where you have seen this particular field value or not - if you don't specify any fields then it will return `True` for the first row and `False` for the rest.

```
A, B, C    <- HEADER ROW
1, 2, 3    <- DATA ROW 1
2, 2, 3    <- DATA ROW 2
2, 3, 3    <- DATA ROW 3
```

If we take the above example, then `jinjafx.first(['A'])` would return `True` for rows 1 and 2, but `False` for row 3 as these rows are the first time we have seen this specific value for "A". We also have the option of specifying multiple fields, so `jinjafx.first(['A', 'B'])` would return `True` for all rows as the combination of "A" and "B" are different in all rows.

There is also an optional `filter_field` argument that allows you to filter the data using a regular expression to match certain rows before performing the check. For example, `jinjafx.first(['A'], { 'B': '3' })` would return `True` for row 3 only as it is the only row which matches the filter.

- <b><code>jinjafx.last([fields[]], [{ "filter_field": "regex", ... }])</code></b>

This function is used to determine whether this is the last row where you have seen this particular field value or not - if you don't specify any fields then it will return 'True' for the last row and 'False' for the rest.

- <b><code>jinjafx.fields("field", [{ "filter_field": "regex", ... }])</code></b>

This function is used to return a unique list of non-empty field values for a specific header field. It also allows the ability to limit what values are included in the list by specifying an optional `filter_field` argument that allows you to filter the data using a regular expression to match certain rows.

- <b><code>jinjafx.setg("key", "value")</code></b>

This function is used to set a global variable that will persist throughout the processing of all rows.

- <b><code>jinjafx.getg("key", ["default"])</code></b>

This function is used to get a global variable that has been set with `jinjafx.setg()` - optionally you can specify a default value that is returned if the `key` doesn't exist.
