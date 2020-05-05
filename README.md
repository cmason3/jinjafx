![Release](https://img.shields.io/github/v/release/cmason3/jinjafx)
![Size](https://img.shields.io/github/languages/code-size/cmason3/jinjafx?label=size)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
# JinjaFx / JinjaFx Server
## Jinja Templating Tool

JinjaFx is a Templating Tool that uses [Jinja2](https://jinja.palletsprojects.com/en/2.11.x/templates/) as the templating engine. It is written in Python and is extremely lightweight and hopefully simple - it doesn't require any Python modules that aren't in the base install, with the exception of [jinja2](https://pypi.org/project/Jinja2/) for obvious reasons, [ansible](https://pypi.org/project/ansible/) if you want to decrypt Ansible Vaulted files and [netaddr](https://pypi.org/project/netaddr/) with ansible if you want to use the [ipaddr](https://docs.ansible.com/ansible/latest/user_guide/playbooks_filters_ipaddr.html) filters. It should work using both Python 2.7 and Python 3 without modification.

JinjaFx Server is a lightweight web server that provides a web frontend to JinjaFx. It is a separate Python file which imports JinjaFx to generate outputs from a web interface.

JinjaFx Server running at https://jinjafx.io

### JinjaFx Usage

```
 jinjafx.py
   -t <template.j2>            - specify a Jinja2 template
   [-d <data.csv>]             - specify row based data (comma or tab separated)
   [-g <vars.yml>[, -g ...]]   - specify global variables in yaml (supports Ansible vaulted files)
   [-o <output file>]          - specify the output file (supports Jinja2 variables) (default is stdout)
   [--ask-vault-pass]          - prompt for vault password (use with -g) (or use ANSIBLE_VAULT_PASS env)
```

JinjaFx differs from the Ansible "template" module as it allows data to be specified in "csv" format as well as multiple yaml files. Providing data in "csv" format is easier if the data originates from a spreadsheet or is already in a tabular format. In networking it is common to find a list of physical connections within a patching schedule, which has each connection on a different row - this format isn't easily transposed into yaml, hence the need to be able to use "csv" as a data format in these scenarios.

This tool allows you to specify a text based "csv" file using the `-d` argument - it is composed of a header row and a series of data rows. It supports both comma and tab separated data and will automagically detect what you are using by analysing the header row - it counts the number of occurrences to determine what one is most prevalent.

```
A, B, C    <- HEADER ROW
1, 2, 3    <- DATA ROW 1
4, 5, 6    <- DATA ROW 2
7, 8, 9    <- DATA ROW 3
```

The case-sensitive header row determines the Jinja2 variables that you will use in your template and the data rows determine the value of that variable for a given row/template combination. Each data row within your data will be passed to the Jinja2 templating engine to construct an output. In addition or instead of the "csv" data, you also have the option to specify multiple yaml files (using the `-g` argument) to include additional variables that would be global to all rows - multiple `-g` arguments can be specified to combine variables from multiple files. If you do omit the data then the template will still be executed, but with a single empty row of data.

Apart from normal data you can also specify regex based static character classes or static groups as values within the data rows. These will be expanded using the `jinjafx.expand()` function to multiple rows, for example:

```
DEVICE, TYPE
us(ma|n[yh]|tx)-pe-1[ab], pe
```

The above would be expanded to the following, which JinjaFx would then loop through like normal rows (be careful as you can easily create huge data sets with no boundaries) - if you do wish to use literal brackets then they would need to be escaped (e.g. "\\["):

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

The `-o` argument is used to specify the output file, as by default the output is sent to `stdout`. This can be a static file, where all the row outputs will be appended, or you can use Jinja2 syntax (e.g. `-o "{{ DEVICE }}.txt"`) to specify a different output file per row. If you specify a directory path then all required directories will be automatically created - any existing files will be overwritten.

### JinjaFx Server Usage

Once JinjaFx Server has been started with the "-s" argument then point your web browser at http://localhost:8080 and you will be presented with a web page that allows you to specify "data.csv", "template.j2" and "vars.yml" and then generate outputs.

```
 jinjafx_server.py
   -s                          - start the JinjaFx Server
   [-l <address>]              - specify a listen address (default is '127.0.0.1')
   [-p <port>]                 - specify a listen port (default is 8080)
```

For health checking purposes, if you specify the URL "/ping" then you should get an "OK" response if the JinaFx Server is up and working (these requests are omitted from the logs).

### JinjaFx Templates

JinjaFx templates are Jinja2 templates with one exception - they support a JinjaFx specific syntax that allows you to specify a different output file within a Jinja2 template to override the value of `-o` (or output name if being used with the JinjaFx Server):

```
<output "output file">
...
</output>
```

The above syntax is transparent to Jinja2 and will be ignored, but JinjaFx will parse it and use a different output file for the contents of that specific block. Full Jinja2 syntax is supported within the block as well as supporting nested blocks.

By default the following Jinja2 templating options are enabled, but they can be overridden as required in the template:

```
trim_blocks = True
lstrip_blocks = True
keep_trailing_newline = True
```

### Jinja2 Extensions

Jinja2 supports the ability to provide extended functionality through [extensions](https://jinja.palletsprojects.com/en/2.11.x/extensions/). To enable specific Jinja2 extensions in JinjaFx you can use the `jinja_extensions` global variable, which you can set within one of your "vars.yml" files (it expects a list):

```yaml
---
jinja_extensions:
  - 'jinja2.ext.i18n'
```

JinjaFx will then attempt to load and enable the extensions that will then be used when processing your Jinja2 templates. You also have the ability to check whether an extensions is loaded within your template by querying `jinja_extensions` directly.

### JinjaFx Built-Ins

Templates should be written using Jinja2 template syntax to make them compatible with Ansible and other tools which use Jinja2. However, there are a few JinjaFx specific extensions that have been added to make JinjaFx much more powerful when dealing with rows of data, as well as providing some much needed functionality which isn't currently present in Jinja2 (e.g. being able to store persistent variables across templates). These are used within a template like any other variable or function (e.g. `{{ jinjafx.version }}`).

- <b><code>jinjafx.version</code></b>

This variable will contain the current version of JinjaFx as a string (e.g. "1.0.0").

- <b><code>jinjafx.jinja_version</code></b>

This variable will return the current version of the Jinja templating engine as a string (e.g. "2.10.3").

- <b><code>jinjafx.row</code></b>

This variable will contain the current row number being processed as an integer.

- <b><code>jinjafx.rows</code></b>

This variable will contain the total number of rows within the data as an integer.

- <b><code>jinjafx.data[][]</code></b>

This list of lists will contain all the row and column data that JinjaFx is currently traversing through. The first row will contain the header row with subsequent rows containing the row data - it is accessed using `jinjafx.data[row][col]`.

- <b><code>jinjafx.expand("string")</code></b>

This function is used to expand a string that contains static character classes (i.e. "[0-9]") or static groups (i.e. "(a|b)") into a list of all the different permutations. You are permitted to use as many classes or groups within the same string - if it doesn't detect any classes or groups within the string then the "string" will be returned as the only list element. Character classes support "A-Z", "a-z" and "0-9" characters, whereas static groups allow any string of characters (including static character classes). If you wish to include "[", "]", "(" or ")" literals within the string then they will need to be escaped.

- <b><code>jinjafx.counter(["key"], [increment], [start])</code></b>

This function is used to provide a persistent counter within a row or between rows. If you specify a `key` then it is a global counter that will persist between rows, but if you don't or you include `jinjafx.row` within the `key`, then the counter only persists within the template of the current row.

- <b><code>jinjafx.first([fields[]], [{ filter_field: "regex", ... }])</code></b>

This function is used to determine whether this is the first row where you have seen this particular field value or not - if you don't specify any fields then it will return `True` for the first row and `False` for the rest.

```
A, B, C    <- HEADER ROW
1, 2, 3    <- DATA ROW 1
2, 2, 3    <- DATA ROW 2
2, 3, 3    <- DATA ROW 3
```

If we take the above example, then `jinjafx.first(['A'])` would return `True` for rows 1 and 2, but `False` for row 3 as these rows are the first time we have seen this specific value for "A". We also have the option of specifying multiple fields, so `jinjafx.first(['A', 'B'])` would return `True` for all rows as the combination of "A" and "B" are different in all rows.

There is also an optional `filter_field` argument that allows you to filter the data using a regular expression to match certain rows before performing the check. For example, `jinjafx.first(['A'], { 'B': '3' })` would return `True` for row 3 only as it is the only row which matches the filter.

- <b><code>jinjafx.last([fields[]], [{ filter_field: "regex", ... }])</code></b>

This function is used to determine whether this is the last row where you have seen this particular field value or not - if you don't specify any fields then it will return 'True' for the last row and 'False' for the rest.

- <b><code>jinjafx.setg("key", value)</code></b>

This function is used to set a global variable that will persist throughout the processing of all rows.

- <b><code>jinjafx.getg("key", [default])</code></b>

This function is used to get a global variable that has been set with `jinjafx.setg()` - optionally you can specify a default value that is returned if the `key` doesn't exist.
