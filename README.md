[![PyPI](https://img.shields.io/pypi/v/jinjafx.svg)](https://pypi.python.org/pypi/jinjafx/)
![Python](https://img.shields.io/badge/python-≥&nbsp;3.9-brightgreen)
[<img src="https://img.shields.io/badge/url-https%3A%2F%2Fjinjafx.io-blue" align="right">](https://jinjafx.io)
&nbsp;
<h1 align="center">JinjaFx - Jinja2 Templating Tool</h1>

<p align="center"><a href="#jinjafx-usage">JinjaFx Usage</a> || <a href="#jinjafx-templates">JinjaFx Templates</a> || <a href="#ansible-filters">Ansible Filters</a> || <a href="#jinjafx-variables">JinjaFx Variables</a><br /><a href="#jinjafx-input">JinjaFx Input</a> || <a href="#jinjafx-datatemplates">JinjaFx DataTemplates</a> || <a href="#jinja2-extensions">Jinja2 Extensions</a> || <a href="#jinjafx-built-ins">JinjaFx Built-Ins</a> || <a href="#jinjafx-filters">JinjaFx Filters</a></p>

JinjaFx is a Templating Tool that uses [Jinja2](https://jinja.palletsprojects.com/en/3.1.x/templates/) as the templating engine. It is written in Python and is extremely lightweight and hopefully simple - it only requires a couple of Python modules that aren't in the base install - [jinja2](https://pypi.org/project/Jinja2/) for obvious reasons and [cryptography](https://pypi.org/project/cryptography/) for Ansible Vault.

JinjaFx differs from the Ansible "template" module as it allows data to be specified in a dynamic "csv" format as well as multiple YAML or JSON files. Providing data in "csv" format is easier if the data originates from a spreadsheet or is already in a tabular format. In networking it is common to find a list of physical connections within a patching schedule, which has each connection on a different row - this format isn't easily transposed into YAML or JSON, hence the need to be able to use "csv" as a data format in these scenarios.

In most cases the use of YAML can be substituted for JSON, except you can't use JSON as a DataTemplate as JSON doesn't support multiline strings.

![GIF](https://github.com/cmason3/jinjafx/raw/main/contrib/jinjafx.gif)
 
### Installation

```
python3 -m pip install --upgrade --user jinjafx
```

### JinjaFx Usage

```
 jinjafx -t <template.j2> [-d [<data.csv>]] [-g <vars.(yml|json)>]
         -dt <dt.yml> [-ds <dataset>] [-g <vars.(yml|json)>]
         -encrypt/-decrypt [<file1>] [<file2>] [..]

    -t <template.j2>          - specify a Jinja2 template
    -d [<data.csv>]           - specify row/column based data (comma or tab separated) - omit for <stdin>
    -dt <dt.yml>              - specify a JinjaFx DataTemplate (combines template, data and vars)
    -ds <dataset>             - specify a regex to match a DataSet within a JinjaFx DataTemplate
    -g <vars.yml> [-g ..]     - specify global variables in yaml (supports Ansible Vaulted variables and files)
    -g <vars.json> [-g ..]    - specify global variables in json (doesn't support Ansible Vaulted variables)
    -var <x=value> [-var ..]  - specify global variables on the command line (overrides existing)
    -ed <exts dir> [-ed ..]   - specify where to look for extensions (default is "." and "~/.jinjafx")
    -o <output file>          - specify the output file (supports Jinja2 variables) (default is stdout)
    -od <output dir>          - set output dir for output files with a relative path (default is ".")
    -encrypt [<file>] [..]    - encrypt files or stdin (if file omitted) using Ansible Vault
    -decrypt [<file>] [..]    - decrypt files or stdin (if file omitted) using Ansible Vault
    -m                        - merge duplicate global variables (dicts and lists) instead of replacing
    -q                        - quiet mode - don't output version or usage information

 Environment Variables:
   ANSIBLE_VAULT_PASSWORD       - specify an Ansible Vault password
   ANSIBLE_VAULT_PASSWORD_FILE  - specify an Ansible Vault password file
```

JinjaFx allows you to specify a text based "csv" file using the `-d` argument - it is composed of a header row and a series of data rows. It supports both comma and tab separated data and will automagically detect what you are using by analysing the header row - it counts the number of occurrences to determine what one is most prevalent. If it detects a "#" at the beginning of a row then that row is ignored as it is treated as a comment.

```
A, B, C    <- HEADER ROW
1, 2, 3    <- DATA ROW 1
4, 5, 6    <- DATA ROW 2
7, 8, 9    <- DATA ROW 3
```

The case-sensitive header row (see `jinjafx_adjust_headers` in [JinjaFx Variables](#jinjafx-variables)) determines the Jinja2 variables that you will use in your template (which means they can only contain `A-Z`, `a-z`, `0-9` or `_` in their value) and the data rows determine the value of that variable for a given row/template combination. Each data row within your data will be passed to the Jinja2 templating engine to construct an output. In addition or instead of the "csv" data, you also have the option to specify multiple yaml or json files (using the `-g` argument) to include additional variables that would be global to all rows - multiple `-g` arguments can be specified to combine variables from multiple files. If you define the same key in different files then the last file specified will overwrite the key value, unless you specify `-m` which tells JinjaFx to merge keys, although this only works for keys of the same type that are mergable (i.e. dicts and lists). If you do omit the data then the template will still be executed, but with a single empty row of data.

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

We also support the ability to use active and passive counters during data expansion with the `{ start[-end]:step[:repeat] }` syntax (step must be positive and repeat specifies the number of times the same number is repeated) - counters are row specific (i.e. they don't persist between different rows). Active counters are easier to explain as they are used to expand rows based on a start and end number (they are bounded) as per the example below. In this instance as we have specified a start (0) and an end (9) it will expand the row to 10 rows using the values from 0 to 9 (i.e. 'et-0/0/0' to 'et-0/0/9').

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

Another type of passive counter is a looping counter, which is used to loop through a set of predefined numerical values via the syntax `{n1|n2|n3|..[:repeat]}`. For example, if we were to use `{1|3|5:1}` then it would output 1, 1, 3, 3, 5, 5, 1, 1, 3, 3, etc - it will only keep going based on the number of rows it is being expanded into.

#### Field Values

By default all field values are treated as strings which means you need to use the `int` filter (e.g. `{{ NUMBER|int }}`) if you wish to perform mathematical functions on them (e.g. `{{ NUMBER|int + 1 }}`). If you have a field where all the values are numbers and you wish them to be treated as numerical values without having to use the `int` filter, then you can suffix `:int` onto the field name (if it detects a non-numerical value in the data then an error will occur), e.g:

```
NUMBER:int, NAME
1, one
10, ten
2, two
20, twenty
```

Like `:int` you can also use `:float` to treat all values as a float.


#### Pad Operator

JinjaFx supports the ability to add or remove leading zeros from numbers using the `%` pad operator. The pad operator is used by suffixing a `%` to a number followed by the number of zeros to pad the number to (e.g. `100%4` would result in `0100` and `003%0` would result in `3`). Using the following example, we might want to have no padding on the `INTERFACE` field but leave the leading zero on the `HOST` field, e.g:

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

Jinja2 is commonly used with Ansible which has a wide variety of [custom filters](https://docs.ansible.com/ansible/latest/user_guide/playbooks_filters.html) that can be used in your Jinja2 templates. However, these filters aren't included in Jinja2 as they are part of Ansible. JinjaFx contains some of them that have been ported from Ansible - please raise an Issue if there is one that is missing that people commonly use and I will get it added.

This contains the following Ansible filters:

- `to_yaml`
- `to_nice_yaml`
- `from_yaml`
- `to_json`
- `to_nice_json`
- `from_json`
- `bool`
- `to_datetime`
- `strftime`
- `b64encode`
- `b64decode`
- `hash`
- `regex_escape`
- `regex_replace`
- `regex_search`
- `regex_findall`
- `dict2items`
- `items2dict`
- `random`
- `shuffle`
- `ternary`
- `extract`
- `flatten`
- `product`
- `permutations`
- `combinations`
- `unique`
- `intersect`
- `difference`
- `symmetric_difference`
- `union`
- `zip`
- `zip_longest`
- `log`
- `pow`
- `root`
- `urlsplit`
- `vlan_expander`
- `vlan_parser`

This also contains the following "[ipaddr](https://docs.ansible.com/ansible/latest/user_guide/playbooks_filters_ipaddr.html)" Ansible filters:

- `cidr_merge`
- `ipaddr`
- `ipmath`
- `ipwrap`
- `ip4_hex`
- `ipv4`
- `ipv6`
- `ipsubnet`
- `next_nth_usable`
- `network_in_network`
- `network_in_usable`
- `reduce_on_network`
- `nthhost`
- `previous_nth_usable`
- `slaac`
- `hwaddr`
- `macaddr` 

### Ansible Tests

In additional to Ansible Filters, Ansible also introduces [tests](https://docs.ansible.com/ansible/latest/user_guide/playbooks_tests.html) that can be performed with various filters (e.g. `select` and `select_attr`) - the following Ansible tests have been included in JinjaFx:

- `regex`
- `match`
- `search`
- `contains`
- `any`
- `all`

### Ansible Lookups

JinjaFx supports the following Ansible lookups:

- <code><b>lookup("vars", variable</b>: String<b>, default</b>: Optional[String]<b>)</b> -> String</code><br />
  or <code><b>vars(variable</b>: String<b>, default</b>: Optional[String]<b>)</b> -> String</code>

The [vars lookup](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/vars_lookup.html) builtin is used to dynamically access variables based on the content of other variables, e.g:

```jinja2
{{ lookup("vars", "my" ~ "variable") }}
```

- <code><b>lookup("varnames", regex</b>: String<b>, ...)</b> -> List[String]</code><br />
  or <code><b>varnames(regex</b>: String<b>, ...)</b> -> List[String]</code>

The [varnames lookup](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/varnames_lookup.html) builtin is used to list variables that are accessible within the scope of the Jinja2 template, e.g:

```jinja2
{{ lookup("varnames", ".+") }} {# return all variables #}

{{ lookup("varnames", "^a", "^b") }} {# return all variables which begin with "a" or "b" #}
```

### JinjaFx Variables

The following variables, if defined within `vars.yml` control how JinjaFx works:

- <code><b>jinjafx_adjust_headers</b></code>

There might be some situations where you can't control the format of the header fields that are provided in `data.csv` - it might come from a spreadsheet where someone hasn't been consistent with the header row and has used uppercase in some situations and lowercase in others or they might have used non-standard characters. The header fields are used by Jinja2 as case-sensitive variables and can't contain spaces or punctuation characters - they can only contain alphanumerical characters and the underscore. To help in these situations, the variable `jinjafx_adjust_headers` can be set in `vars.yml` to either "yes", "no" (the default), "upper" or "lower", which will remove any non-standard characters and change the case depending on the value (i.e. "Assigned / Unassigned" would become `ASSIGNEDUNASSIGNED` if the value was "upper" and `AssignedUnassigned` if the value was "yes").

```yaml
---
jinjafx_adjust_headers: "yes" | "no" | "upper" | "lower"
```

- <code><b>jinjafx_render_vars</b></code>

JinjaFx by default will attempt to render your `vars.yml` file using Jinja2, which means the following syntax is valid:

```yaml
---
fullname: "Firstname Surname"
firstname: "{{ fullname.split()[0] }}"
surname: "{{ fullname.split()[1] }}"
```

However, the rendering will happen after `vars.yml` has been processed by YAML, which means it must be valid YAML to start with - the following isn't valid YAML:


```yaml
---
{% if x != y %}
x: "{{ y }}"
{% endif %}
```

If you wish to use literal braces within your YAML (i.e. `{{`) then you need to ensure they are escaped, or you can disable this functionality by specifying the following variable in `vars.yml`:

```yaml
---
jinjafx_render_vars: "no"
```

- <code><b>jinjafx_filter</b></code> and <code><b>jinjafx_sort</b></code>

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

The above syntax allows you to specify an order key for individual field values - by default all fields have an order key of 0, which means the field name is used as the sort key. If you specify an order key < 0 then the field value will appear before the rest and if you specify an order key > 0 then the values will appear at the end. If multiple field values have the same order key then they are sorted based on actual field value. In the above example, "r740-036" will appear first, "r740-035" will appear second and everything else afterwards, with "r740-039" appearing last.

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

### Keyless YAML ###

There might be some scenarios where you want to define YAML without a root key, e.g:

```yaml
- name: "Alice"
  age: 27
- name: "Bob"
  age: 37
- name: "Eve"
  age: 29
```

While this is valid in YAML, it isn't valid to have a list when Jinja2 expects a dict. In this scenario, JinjaFx will create a parent key of `_` to allow you to iterate over it within a Jinja2 template (the same applies for JSON):

```jinja2
{% for k in _ %}
  {{ k.name }} is {{ k.age }}
{% endfor %}
```

### JinjaFx DataTemplates ###

JinjaFx also supports the ability to combine the data, template and vars into a single YAML file called a DataTemplate (no support for JSON as JSON doesn't support multiline strings, although you can specify the `vars` section using JSON), which you can pass to JinjaFx using `-dt`. This is the same format used by the JinjaFx Server when you click on 'Export DataTemplate'. It uses headers with block indentation to separate out the different components - you must ensure the indentation is maintained on all lines as this is how YAML knows when one section ends and another starts.

```yaml
---
dt:
  data: |2
    ... DATA.CSV ...

  template: |2
    ... TEMPLATE.J2 ...

  vars: |2
    ... VARS.(YML|JSON) ...
```

You also have the option to specify different DataSets within a DataTemplate - this is where the template is common, but the data and vars can be specified multiple times for different scenarios (e.g. "Test" and "Live"). When you use the DataSet format you will also need to specify which DataSet to generate the outputs for with `-ds`, which takes a case insensitive regular expression to match against.

```yaml
---
dt:
  global: |2
    ... GLOBAL.(YML|JSON) ...

  datasets:
    "Test":
      data: |2
        ... DATA.CSV ...

      vars: |2
        ... VARS.(YML|JSON) ...

    "Live":
      data: |2
        ... DATA.CSV ...

      vars: |2
        ... VARS.(YML|JSON) ...

  template: |2
    ... TEMPLATE.J2 ...
```

### Jinja2 Extensions

Jinja2 supports the ability to provide extended functionality through [extensions](https://jinja.palletsprojects.com/en/3.0.x/extensions/). To enable specific Jinja2 extensions in JinjaFx you can use the `jinja2_extensions` global variable, which you can set within one of your `vars.yml` files (it expects a list):

```yaml
---
jinja2_extensions:
  - 'jinja2.ext.i18n'
  - 'jinja2.ext.loopcontrols'
  - 'jinja2.ext.do'
  - 'jinja2.ext.debug'  
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

### JinjaFx Built-Ins

Templates should be written using Jinja2 template syntax to make them compatible with Ansible and other tools which use Jinja2. However, there are a few JinjaFx specific extensions that have been added to make JinjaFx much more powerful when dealing with rows of data, as well as providing some much needed functionality which isn't currently present in Jinja2 (e.g. being able to store persistent variables across templates). These are used within a template like any other variable or function (e.g. `{{ jinjafx.version }}`).

- <code><b>jinjafx.version</b> -> String</code>

This variable will contain the current version of JinjaFx (e.g. "1.0.0").

- <code><b>jinjafx.jinja2_version</b> -> String</code>

This variable will return the current version of the Jinja2 templating engine (e.g. "2.10.3").

- <code><b>jinjafx.row</b> -> Integer</code>

This variable will contain the current row number being processed.

- <code><b>jinjafx.rows</b> -> Integer</code>

This variable will contain the total number of rows within the data.

- <code><b>jinjafx.data(row</b>: Integer<b>, col</b>: Optional[Integer | String]<b>)</b> -> List[String] | String</code>

This function is used to access all the row and column data that JinjaFx is currently traversing through. The first row (0) will contain the header row with subsequent rows containing the row data - it is accessed using `jinjafx.data(row, col)`. If you wish to access the columns via their case-sensitive name then you can also use `jinjafx.data(row, 'FIELD')`. The `row` argument is mandatory, but if you omit the `col` argument then it will return the whole row as a list.

- <code><b>jinjafx.tabulate(datarows</b>: Optional[List[List[String]]]<b>, *, cols</b>: Optional[List[String]]<b>, colons</b>: Optional[Boolean]<b>=False)</b> -> String</code>

This function will produce a GitHub Markdown styled table using either the provided `datarows` variable, or (if omitted) using the data from `data.csv`, e.g:

```jinja2
{{ jinjafx.tabulate([["A", "B", "C"], ["1", "2", "3"], ["4", "5", "6"]]) }}
```

This will produce the following table:

```
| A | B | C |
| - | - | - |
| 1 | 2 | 3 |
| 4 | 5 | 6 |
```

The first row will always be used as the header row, which matches the behaviour of JinjaFx with respect to `data.csv`. You can also change the order of the columns or decide to only include some of the columns using the `cols` argument, e.g:


```jinja2
{{ jinjafx.tabulate([["A", "B", "C"], ["1", "2", "3"], ["4", "5", "6"]], cols=["C", "A"]) }}
```

This will produce the following table:

```
| C | A |
| - | - |
| 3 | 1 |
| 6 | 4 |
```

All columns are left aligned, except if the column value is of type `int` or `float` (`data.csv` uses `:int` and `:float` syntax to force this) and then they are right aligned. At this point you can't change this, but if you wish to include the `:` as used by GitHub Markdown to force the alignment, you can set `colons` to `True`.

- <code><b>jinjafx.expand(value</b>: String<b>)</b> -> List[String]</code>

This function is used to expand a string that contains static character classes (i.e. `[0-9]`), static groups (i.e. `(a|b)`) or active counters (i.e. `{ start-end:increment }`) into a list of all the different permutations. You are permitted to use as many classes, groups or counters within the same string - if it doesn't detect any classes, groups or counters within the string then the "string" will be returned as the only list element. Character classes support "A-Z", "a-z" and "0-9" characters, whereas static groups allow any string of characters (including static character classes). If you wish to include "[", "]", "(", ")", "{" or "}" literals within the string then they will need to be escaped.

- <code><b>jinjafx.counter(key</b>: Optional[String]<b>, increment</b>: Optional[Integer]<b>=1, start</b>: Optional[Integer]<b>=1, row</b>: Optional[Integer]<b>)</b> -> Integer | String</code>

This function is used to provide a persistent counter within a row or between rows. If you specify a case insensitive `key` then it is a global counter that will persist between rows, but if you don't or you include `jinjafx.row` within the `key`, then the counter only persists within the template of the current row. You can also manipulate the counter by specifying a custom row, which overrides the current row.

This function also supports a hierarchical counter which can be used for numbering of headings, e.g:

```
1.
1.1.
1.1.1.
1.1.2.
2.
```

This is achieved by using a special syntax for the `key` value:

```jinja2
{{ jinjafx.counter('A.') }}
{{ jinjafx.counter('A.A.') }}
{{ jinjafx.counter('A.A.A.') }}
{{ jinjafx.counter('A.A.A.') }}
{{ jinjafx.counter('A.') }}
```

When this function detects a `key` which consists of single letters preceded by a dot, then it will act as a hierarchical counter and will produce the above output. Using different letters will reset the counter value back to 1 (or a different number if you have specified `start`). You aren't able to skip levels (i.e. 'A.A.A.' isn't valid if 'A.A.' and 'A.' haven't been used previously, etc).

- <code><b>jinjafx.now(format</b>: Optional[String]<b>, tz</b>: Optional[String]<b>="UTC")</b> -> String</code>

This function is used to output the current date and time. If you don't specify the optional `format` argument then it will output using the default ISO 8601 format - if you wish to specify a custom format then it needs to be as per [strftime](https://strftime.org/). The `tz` argument is also optional and allows you to specify a timezone as opposed to `UTC` which is used by default.

- <code><b>jinjafx.exception(message</b>: String<b>)</b> -> NoReturn</code>

This function is used to stop processing and raise an exception with a meaningful message - for example, if an expected header field doesn't exist you could use it as follows:

```jinja2
{% if name is not defined %}
  {% set null = jinjafx.exception("header field 'name' is not defined in data") %}
{% endif %}

```

- <code><b>jinjafx.warning(message</b>: String<b>, repeat</b>: Optional[Boolean]<b>=False)</b> -> NoReturn</code>

Nearly identical to the previous function, except this won't stop processing of the template but will raise a warning message when the output is generated - this can be specified multiple times for multiple warnings, although repeated warnings are suppressed unless you set the second parameter to True.

- <code><b>jinjafx.first(field</b>: Optional[List[String]]<b>, filter_fields</b>: Optional[Dict[<b>field</b>: String<b>, regex</b>: String]]<b>)</b> -> Boolean</code>

This function is used to determine whether this is the first row where you have seen this particular field value or not - if you don't specify any fields then it will return `True` for the first row and `False` for the rest.

```
A, B, C    <- HEADER ROW
1, 2, 3    <- DATA ROW 1
2, 2, 3    <- DATA ROW 2
2, 3, 3    <- DATA ROW 3
```

If we take the above example, then `jinjafx.first(['A'])` would return `True` for rows 1 and 2, but `False` for row 3 as these rows are the first time we have seen this specific value for "A". We also have the option of specifying multiple fields, so `jinjafx.first(['A', 'B'])` would return `True` for all rows as the combination of "A" and "B" are different in all rows.

There is also an optional `filter_fields` argument that allows you to filter the data using a regular expression to match certain rows before performing the check. For example, `jinjafx.first(['A'], { 'B': '3' })` would return `True` for row 3 only as it is the only row which matches the filter, where 'B' contains a '3'.

There might be some scenarios where you don't want to match the entire value, but part of it - to support this, there is an optional split operator using the following syntax `FIELD:<CHAR><POS>`, e.g:

```
DEVICE
LEAF-01
LEAF-02
LEAF-03
```

By using the split operator we can specify `jinjafx.first(['DEVICE:-0'])`, which uses `-` as the split character and `0` as the numeric position - this will use the value 'LEAF' when deciding if it is the first value or not. Like Python syntax we also support negative positions, so `DEVICE:--1` would represent the last value.

- <code><b>jinjafx.last(field</b>: Optional[List[String]]<b>, filter_fields</b>: Optional[Dict[<b>field</b>: String<b>, regex</b>: String]]<b>)</b> -> Boolean</code>

This function is used to determine whether this is the last row where you have seen this particular field value or not - if you don't specify any fields then it will return 'True' for the last row and 'False' for the rest. Similar to `jinjafx.first()` it supports the same syntax.

- <code><b>jinjafx.fields(field</b>: String<b>, filter_fields</b>: Optional[Dict[<b>field</b>: String<b>, regex</b>: String]]<b>)</b> -> List[String]</code>

This function is used to return a unique list of non-empty field values for a specific header field. It also allows the ability to limit what values are included in the list by specifying an optional `filter_fields` argument that allows you to filter the data using a regular expression to match certain rows.

- <code><b>jinjafx.setg(key</b>: String<b>, value</b>: String | Integer | Boolean]<b>)</b> -> NoReturn</code>

This function is used to set a global variable that will persist throughout the processing of all rows.

- <code><b>jinjafx.getg(key</b>: String<b>, default</b>: Optional[String | Integer | Boolean])</b> -> String | Integer | Boolean</code>

This function is used to get a global variable that has been set with `jinjafx.setg()` - optionally you can specify a default value that is returned if the `key` doesn't exist.

### JinjaFx Filters

JinjaFx comes with a custom Jinja2 Extension (`extensions/ext_jinjafx.py`) that is enabled by default which provides the following custom filters:

- <code><b>cisco_snmpv3_key(engineid</b>: String<b>, algorithm</b>: Optional[String]<b>="sha1")</b> -> String</code>

This filter is used to generate localised SNMPv3 authentication and privacy keys (section A.2 of [RFC3414](https://datatracker.ietf.org/doc/html/rfc3414#appendix-A.2)) for use by Cisco devices, e.g:

```jinja2
snmp-server engineID local {{ engineID }}
snmp-server user {{ snmpUser }} {{ snmpGroup }} v3 encrypted auth sha {{ authPassword|cisco_snmpv3_key(engineID) }} priv aes 128 {{ privPassword|cisco_snmpv3_key(engineID) }}
```

- <code><b>junos_snmpv3_key(engineid</b>: String<b>, algorithm</b>: Optional[String]<b>="sha1")</b> -> String</code>

This filter is used to generate localised SNMPv3 authentication and privacy keys (section A.2 of [RFC3414](https://datatracker.ietf.org/doc/html/rfc3414#appendix-A.2)) for use by Juniper devices, e.g:

```jinja2
set snmp engine-id local {{ engineID }}
set snmp v3 usm local-engine user {{ snmpUser }} authentication-sha authentication-key {{ authPassword|junos_snmpv3_key(engineID) }}
set snmp v3 usm local-engine user {{ snmpUser }} privacy-aes128 privacy-key {{ privPassword|junos_snmpv3_key(engineID) }}
```

- <code><b>cisco7encode(value</b>: String<b>, seed</b>: Optional[String]<b>)</b> -> String</code>

This filter will encode a string using Cisco's Type 7 encoding scheme. An optional "seed" can be provided which makes the encoded string deterministic for idempotent operations.

- <code><b>junos9encode(value</b>: String<b>, seed</b>: Optional[String]<b>)</b> -> String</code>

This filter will encode a string using Juniper's Type 9 encoding scheme. An optional "seed" can be provided which makes the encoded string deterministic for idempotent operations.

- <code><b>cisco8hash(value</b>: String<b>, salt</b>: Optional[String]<b>)</b> -> String</code>

This filter will hash a string using Cisco's Type 8 hashing scheme (SHA256 with PBKDF2). An optional "salt" (length must be 14 characters) can be provided which makes the hashed string deterministic for idempotent operations.

- <code><b>cisco9hash(value</b>: String<b>, salt</b>: Optional[String]<b>)</b> -> String</code>

This filter will hash a string using Cisco's Type 9 hashing scheme (SCrypt). An optional "salt" (length must be 14 characters) can be provided which makes the hashed string deterministic for idempotent operations.

- <code><b>cisco10hash(value</b>: String<b>, salt</b>: Optional[String]<b>)</b> -> String</code>

This filter will hash a string using Cisco's Type 10 hashing scheme (Unix Crypt based SHA512). An optional "salt" (length must be 16 characters) can be provided which makes the hashed string deterministic for idempotent operations.

- <code><b>junos6hash(value</b>: String<b>, salt</b>: Optional[String]<b>)</b> -> String</code>

This filter will hash a string using Juniper's Type 6 hashing scheme (Unix Crypt based SHA512). An optional "salt" (length must be 8 characters) can be provided which makes the hashed string deterministic for idempotent operations.

- <code><b>ipsort(query</b>: List[String]<b>)</b> -> List[String]</code>

This filter will sort a list of IPv4 and/or IPv6 addresses into numerical order.
This custom filter will be removed if and when the standard Ansible `ipaddr` filter provides support.

- <code><b>summarize_address_range(range</b>: String<b>)</b> -> List[String]</code>

This filter will summarise an IPv4 or IPv6 range into a list of CIDR networks, e.g:

```jinja2
{{ "192.0.2.0-192.0.2.255"|summarize_address_range }}
```

This will result in the following output:

```
['192.0.2.0/24']
```

This custom filter will be removed if and when the standard Ansible `ipaddr` filter provides support.

- <code><b>xpath(query</b>: String<b>)</b> -> String</code> (requires `lxml` python module)

This filter is used to perform an xpath query on an XML based output and return the matching sections as a list (if you use namespaces you need to ensure you define them using the `xmlns:` syntax), e.g:

```yaml
---
xml: |2
  <interfaces xmlns:junos="http://xml.juniper.net/junos/*/junos">
      <interface>
          <name>et-0/1/0</name>
          <description junos:changed='changed'>## [DCI] 100GE Circuit to ROUTER-01 (et-0/1/0) ##</description>
      </interface>
      <interface>
          <name>et-0/1/1</name>
          <description>## 100GE Link to SPINE-01 (et-0/0/0) ##</description>
      </interface>
      <interface>
          <name>et-0/1/2</name>
          <description>## 100GE Link to SPINE-02 (et-0/0/0) ##</description>
      </interface>
  </interfaces>
```

The following xpath query can be used to find all the "et" interfaces which have the attribute "junos:changed" applied to them and then output the interface's description:

```jinja2
{% for description in xml|xpath("//interfaces/interface[starts-with(name, 'et')]/description[@junos:changed]/text()") %}
{{ description }}
{% endfor %}
```

- <code><b>vaulty_encrypt(plaintext</b>: String<b>, password</b>: String<b>, cols</b>: Optional[Integer]<b>)</b> -> String</code>

This filter will encrypt a string using [Vaulty](https://github.com/cmason3/vaulty) which is an alternative to Ansible Vault. Vaulty provides 256-bit authenticated symmetric encryption (AEAD) using ChaCha20-Poly1305 and Scrypt as the password based key derivation function. Ansible Vault is very inefficient when it comes to output size - for example, a 256 byte string encrypted using Ansible Vault will take up 1,390 bytes (a 443% increase) compared to Vaulty where the same string will only take up 412 bytes (a 61% increase). The optional "cols" argument will split the output into rows of "cols" width similar to Ansible Vault output.

- <code><b>vaulty_decrypt(ciphertext</b>: String<b>, password</b>: String<b>)</b> -> String</code>

This filter will perform the opposite of `vaulty_encrypt` and takes a Vaulty encrypted string and the password, e.g:

```jinja2
{{ "$VAULTY;..."|vaulty_decrypt("password") }}
```
