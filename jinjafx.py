#!/usr/bin/env python3

# JinjaFx - Jinja2 Templating Tool
# Copyright (c) 2020-2022 Chris Mason <chris@netnix.org>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import sys, os, jinja2, yaml, argparse, re, copy, getpass, traceback

__version__ = '1.8.1'
jinja2_filters = []

def import_filters(errc = 0):
  try:
    from ansible.plugins.filter import core
    jinja2_filters.append(core.FilterModule().filters())
  except Exception:
    print('warning: unable to import ansible \'core\' filters - requires ansible', file=sys.stderr)
    errc += 1
      
  try:
    import netaddr

    try:
      from ansible.plugins.filter import ipaddr
    except Exception:
      try:
        from ansible_collections.ansible.netcommon.plugins.filter import ipaddr
      except Exception:
        raise Exception()

    filters = {}
    for k, v in ipaddr.FilterModule().filters().items():
      filters[k] = v
      filters['ansible.netcommon.' + k] = v

    jinja2_filters.append(filters)

  except Exception:
    print('warning: unable to import ansible \'ipaddr\' filter - requires ansible and netaddr', file=sys.stderr)
    errc += 1

  return errc


def __format_bytes(b):
  for u in [ '', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y' ]:
    if b >= 1000:
      b /= 1000
    else:
      return '{:.2f}'.format(b).rstrip('0').rstrip('.') + u + 'B'


def main():
  try:
    if '-q' not in sys.argv:
      print('JinjaFx v' + __version__ + ' - Jinja2 Templating Tool')
      print('Copyright (c) 2020-2022 Chris Mason <chris@netnix.org>\n')

    jinjafx_usage = '(-t <template.j2> [-d <data.csv>] | -dt <dt.yml>) [-g <vars.yml>] [-o <output file>] [-od <output dir>] [-m] [-q]'

    parser = __ArgumentParser(add_help=False, usage='%(prog)s ' + jinjafx_usage)
    group_ex = parser.add_mutually_exclusive_group(required=True)
    group_ex.add_argument('-dt', metavar='<dt.yml>', type=argparse.FileType('r'))
    group_ex.add_argument('-t', metavar='<template.j2>', type=argparse.FileType('r'))
    parser.add_argument('-d', metavar='<data.csv>', type=argparse.FileType('r'))
    parser.add_argument('-g', metavar='<vars.yml>', type=argparse.FileType('r'), action='append')
    parser.add_argument('-o', metavar='<output file>', type=str)
    parser.add_argument('-od', metavar='<output dir>', type=str)
    parser.add_argument('-m', action='store_true')
    parser.add_argument('-q', action='store_true')
    args = parser.parse_args()

    if args.dt is not None and args.d is not None:
      parser.error("argument -d: not allowed with argument -dt")

    if args.m is True and args.g is None:
      parser.error("argument -m: only allowed with argument -g")

    if args.od is not None and not os.access(args.od, os.W_OK):
      parser.error("argument -od: unable to write to output directory")

    data = None
    vault = [ None ]
    gvars = {}
    dt = {}

    def decrypt_vault(string):
      if string.startswith('$ANSIBLE_VAULT;'):
        if vault[0] is None:
          from ansible.constants import DEFAULT_VAULT_ID_MATCH
          from ansible.parsing.vault import VaultLib
          from ansible.parsing.vault import VaultSecret

          vpw = os.getenv('ANSIBLE_VAULT_PASSWORD')

          if vpw == None:
            vpwf = os.getenv('ANSIBLE_VAULT_PASSWORD_FILE')
            if vpwf != None:
              with open(vpwf) as f:
                vpw = f.read().strip()

          if vpw == None:
            vpw = getpass.getpass('Vault Password: ')
            print()

          vault[0] = VaultLib([(DEFAULT_VAULT_ID_MATCH, VaultSecret(vpw.encode('utf-8')))])

        return vault[0].decrypt(string.encode('utf-8')).decode('utf-8')
      return string

    def yaml_vault_tag(loader, node):
      return decrypt_vault(node.value)

    def merge(dst, src):
      for key in src:
        if key in dst:
          if isinstance(dst[key], dict) and isinstance(src[key], dict):
            merge(dst[key], src[key])

          elif isinstance(dst[key], list) and isinstance(src[key], list):
            dst[key] += src[key]

          else:
            dst[key] = src[key]

        else:
          dst[key] = src[key]

      return dst

    yaml.add_constructor('!vault', yaml_vault_tag, yaml.SafeLoader)

    if args.dt is not None:
      with open(args.dt.name) as f:
        dt.update(yaml.load(f.read(), Loader=yaml.SafeLoader)['dt'])
        args.t = dt['template']

        if 'datasets' in dt:
          raise Exception('datasets aren\'t supported at present')

        else:
          if 'data' in dt:
            data = dt['data']

          if 'vars' in dt:
            gyaml = decrypt_vault(dt['vars'])
            if gyaml:
              gvars.update(yaml.load(gyaml, Loader=yaml.SafeLoader))

    if args.d is not None:
      with open(args.d.name) as f:
        data = f.read()

    if args.g is not None:
      for g in args.g:
        with open(g.name) as f:
          gyaml = decrypt_vault(f.read())
          if args.m == True:
            merge(gvars, yaml.load(gyaml, Loader=yaml.SafeLoader))
          else:
            gvars.update(yaml.load(gyaml, Loader=yaml.SafeLoader))

    if args.o is None:
      args.o = '_stdout_'

    if 'jinjafx_input' in gvars:
      jinjafx_input = {}

      if 'prompt' in gvars['jinjafx_input'] and len(gvars['jinjafx_input']['prompt']) > 0:
        for k in gvars['jinjafx_input']['prompt']:
          v = gvars['jinjafx_input']['prompt'][k]

          if isinstance(v, dict):
            if 'pattern' not in v:
              v['pattern'] = '.*'

            if 'required' not in v:
              v['required'] = False

            while True:
              if 'type' in v and v['type'].lower() == 'password':
                jinjafx_input[k] = getpass.getpass(v['text'] + ': ').strip()
              else:
                jinjafx_input[k] = input(v['text'] + ': ').strip()

              if len(jinjafx_input[k]) == 0:
                if v['required']:
                  print('error: input is required', file=sys.stderr)
                else:
                  break
              else:
                m = re.match(v['pattern'], jinjafx_input[k], re.I)
                if not m or (m.span()[1] - m.span()[0]) != len(jinjafx_input[k]):
                  print('error: input doesn\'t match pattern "' + v['pattern'] + '"', file=sys.stderr)
                else:
                  break

          else:
            jinjafx_input[k] = input(v + ': ').strip()

        print()

      gvars['jinjafx_input'] = jinjafx_input

    if import_filters() > 0:
      print()

    outputs = JinjaFx().jinjafx(args.t, data, gvars, args.o)
    ocount = 0

    if args.od is not None:
      os.chdir(args.od)

    if len(outputs['_stderr_']) > 0:
      print('Warnings:', file=sys.stderr)
      for w in outputs['_stderr_']:
        print(' - ' + w, file=sys.stderr)

      print('', file=sys.stderr)

    for o in sorted(outputs.items(), key=lambda x: (x[0] == '_stdout_')):
      if o[0] != '_stderr_':
        output = '\n'.join(o[1]) + '\n'
        if len(output.strip()) > 0:
          if o[0] == '_stdout_':
            if ocount > 0:
              print('\n-\n')
            print(output)
  
          else:
            ofile = re.sub(r'_+', '_', re.sub(r'[^A-Za-z0-9_. -/]', '_', os.path.normpath(o[0])))
  
            if os.path.dirname(ofile) != '':
              if not os.path.isdir(os.path.dirname(ofile)):
                os.makedirs(os.path.dirname(ofile))
  
            with open(ofile, 'w') as f:
              f.write(output)
  
            print(__format_bytes(len(output)) + ' > ' + ofile)
  
          ocount += 1

    if ocount > 0:
      if '_stdout_' not in outputs:
        print()

    else:
      raise Exception('nothing to output')

  except KeyboardInterrupt:
    sys.exit(-1)

  except Exception as e:
    tb = traceback.format_exc()
    match = re.search(r'[\s\S]*File "(.+)", line ([0-9]+), in.*template', tb, re.IGNORECASE)
    if match:
      print('error[' + match.group(1) + ':' + match.group(2) + ']: ' + type(e).__name__ + ': ' + str(e), file=sys.stderr)
    else:
      print('error[' + str(sys.exc_info()[2].tb_lineno) + ']: ' + type(e).__name__ + ': ' + str(e), file=sys.stderr)

    sys.exit(-2)


class __ArgumentParser(argparse.ArgumentParser):
  def error(self, message):
    if '-q' not in sys.argv:
      print('URL:\n  https://github.com/cmason3/jinjafx\n', file=sys.stderr)
      print('Usage:\n  ' + self.format_usage()[7:], file=sys.stderr)
    raise Exception(message)


class JinjaFx():
  def jinjafx(self, template, data, gvars, output):
    self.__g_datarows = []
    self.__g_dict = {}
    self.__g_row = 0 
    self.__g_vars = {}
    self.__g_warnings = []

    outputs = {}
    delim = None
    rowkey = 1
    int_indices = []
    
    if isinstance(data, bytes):
      data = data.decode('utf-8')

    if data is not None and len(data.strip()) > 0:
      jinjafx_filter = {}

      for l in data.splitlines():
        if len(l.strip()) > 0 and not re.match(r'^[ \t]*#', l):
          if len(self.__g_datarows) == 0:
            if l.count(',') > l.count('\t'):
              delim = r'[ \t]*,[ \t]*'
              schars = ' \t'
            else:
              delim = r' *\t *'
              schars = ' '

            fields = re.split(delim, re.sub('(?:' + delim + ')+$', '', l.strip(schars)))
            fields = [re.sub(r'^(["\'])(.*)\1$', r'\2', f) for f in fields]

            for i in range(len(fields)):
              if fields[i].lower().endswith(':int'):
                int_indices.append(i + 1)
                fields[i] = fields[i][:-4]

              if 'jinjafx_adjust_headers' in gvars:
                jinjafx_adjust_headers = str(gvars['jinjafx_adjust_headers']).strip().lower()

                if jinjafx_adjust_headers == 'yes':
                  fields[i] = re.sub(r'[^A-Z0-9_]', '', fields[i], flags=re.UNICODE | re.IGNORECASE)

                elif jinjafx_adjust_headers == 'upper':
                  fields[i] = re.sub(r'[^A-Z0-9_]', '', fields[i].upper(), flags=re.UNICODE | re.IGNORECASE)

                elif jinjafx_adjust_headers == 'lower':
                  fields[i] = re.sub(r'[^A-Z0-9_]', '', fields[i].lower(), flags=re.UNICODE | re.IGNORECASE)

                elif jinjafx_adjust_headers != 'no':
                  raise Exception('invalid value specified for \'jinjafx_adjust_headers\' - must be \'yes\', \'no\', \'upper\' or \'lower\'')
              
              if fields[i] == '':
                raise Exception('empty header field detected at column position ' + str(i + 1))

              elif not re.match(r'^[A-Z_][A-Z0-9_]*$', fields[i], re.IGNORECASE):
                raise Exception('header field at column position ' + str(i + 1) + ' contains invalid characters')

            if len(set(fields)) != len(fields):
              raise Exception('duplicate header field detected in data')

            else:
              self.__g_datarows.append(fields)

            if 'jinjafx_filter' in gvars and len(gvars['jinjafx_filter']) > 0:
              for field in gvars['jinjafx_filter']:
                jinjafx_filter[self.__g_datarows[0].index(field) + 1] = gvars['jinjafx_filter'][field]

          else:
            gcount = 1
            fields = []

            for f in re.split(delim, l.strip(schars)):
              delta = 0

              for m in re.finditer(r'(?<!\\)\((.+?)(?<!\\)\)', f):
                if not re.search(r'(?<!\\)\|', m.group(1)):
                  if not re.search(r'\\' + str(gcount), l):
                    if re.search(r'\\[0-9]+', l):
                      raise Exception('parenthesis in row ' + str(rowkey) + ' at \'' + str(m.group(0)) + '\' should be escaped or removed')

                    else:
                      f = f[:m.start() + delta] + '\\(' + m.group(1) + '\\)' + f[m.end() + delta:]
                      delta += 2

                gcount += 1

              fields.append(re.sub(r'^(["\'])(.*)\1$', r'\2', f))

            n = len(self.__g_datarows[0])
            fields = [list(map(self.__jfx_expand, fields[:n] + [''] * (n - len(fields)), [True] * n))]

            # recm = r'(?<!\\){[ \t]*([0-9]+):([0-9]+)[ \t]*(?<!\\)}' # TODO: REMOVE PAD
            recm = r'(?<!\\){[ \t]*([0-9]+):([0-9]+)(?::([0-9]+))?[ \t]*(?<!\\)}'

            row = 0
            while row < len(fields):
              if not isinstance(fields[row][0], int):
                fields[row].insert(0, rowkey)
                rowkey += 1

              if any(isinstance(col[0], list) for col in fields[row][1:]):
                for col in range(1, len(fields[row])):
                  if isinstance(fields[row][col][0], list):
                    for v in range(len(fields[row][col][0])):
                      nrow = copy.deepcopy(fields[row])
                      nrow[col] = [fields[row][col][0][v], fields[row][col][1][v]]
                      fields.append(nrow)

                    fields.pop(row)
                    break

              else:
                groups = []

                for col in range(1, len(fields[row])):
                  fields[row][col][0] = re.sub(recm, lambda m: self.__jfx_data_counter(m, fields[row][0], col, row), fields[row][col][0])

                  for g in range(len(fields[row][col][1])):
                    fields[row][col][1][g] = re.sub(recm, lambda m: self.__jfx_data_counter(m, fields[row][0], col, row), fields[row][col][1][g])

                  groups.append(fields[row][col][1])

                groups = dict(enumerate(sum(groups, ['\\0'])))

                for col in range(1, len(fields[row])):
                  fields[row][col] = re.sub(r'\\([0-9]+)', lambda m: groups.get(int(m.group(1)), '\\' + m.group(1)), fields[row][col][0])

                  delta = 0
                  for m in re.finditer(r'([0-9]+)(?<!\\)\%([0-9]+)', fields[row][col]):
                    pvalue = str(int(m.group(1))).zfill(int(m.group(2)))
                    fields[row][col] = fields[row][col][:m.start() + delta] + pvalue + fields[row][col][m.end() + delta:]

                    if len(m.group(0)) > len(pvalue):
                      delta -= len(m.group(0)) - len(pvalue)
                    else:
                      delta += len(pvalue) - len(m.group(0))

                  fields[row][col] = re.sub(r'\\([}{%])', r'\1', fields[row][col])

                  if col in int_indices:
                    fields[row][col] = int(fields[row][col])

                include_row = True
                if len(jinjafx_filter) > 0:
                  for index in jinjafx_filter:
                    if not re.search(jinjafx_filter[index], fields[row][index]):
                      include_row = False
                      break

                if include_row:
                  self.__g_datarows.append(fields[row])

                row += 1

      if len(self.__g_datarows) <= 1:
        raise Exception('not enough data rows - need at least two')

    if 'jinjafx_sort' in gvars and len(gvars['jinjafx_sort']) > 0:
      for field in reversed(gvars['jinjafx_sort']):
        if isinstance(field, dict):
          fn = next(iter(field))
          r = True if fn.startswith('-') else False
          mv = []

          for rx, v in field[fn].items():
            mv.append([re.compile(rx + '$'), v])

          self.__g_datarows[1:] = sorted(self.__g_datarows[1:], key=lambda n: (self.__find_re_match(mv, n[self.__g_datarows[0].index(fn.lstrip('+-')) + 1]), n[self.__g_datarows[0].index(fn.lstrip('+-')) + 1]), reverse=r)

        else:
          r = True if field.startswith('-') else False
          self.__g_datarows[1:] = sorted(self.__g_datarows[1:], key=lambda n: n[self.__g_datarows[0].index(field.lstrip('+-')) + 1], reverse=r)

    if 'jinja2_extensions' not in gvars:
      gvars.update({ 'jinja2_extensions': [] })

    else:
      sys.path.append(os.getcwd())

    jinja2_options = {
      'undefined': jinja2.StrictUndefined,
      'trim_blocks': True,
      'lstrip_blocks': True,
      'keep_trailing_newline': True
    }

    if isinstance(template, bytes) or isinstance(template, str):
      env = jinja2.Environment(extensions=gvars['jinja2_extensions'], **jinja2_options)
      [env.filters.update(f) for f in jinja2_filters]
      if isinstance(template, bytes):
        template = env.from_string(template.decode('utf-8'))
      else:
        template = env.from_string(template)
    else:
      env = jinja2.Environment(extensions=gvars['jinja2_extensions'], loader=jinja2.FileSystemLoader(os.path.dirname(template.name)), **jinja2_options)
      [env.filters.update(f) for f in jinja2_filters]
      template = env.get_template(os.path.basename(template.name))

    env.tests.update({
      'regex': self.__jfx_regex,
      'match': self.__jfx_match,
      'search': self.__jfx_search
    })

    env.globals.update({
      'lookup': self.__jfx_lookup
    })

    env.globals.update({ 'jinjafx': {
      'version': __version__,
      'jinja2_version': jinja2.__version__,
      'expand': self.__jfx_expand,
      'counter': self.__jfx_counter,
      'exception': self.__jfx_exception,
      'warning': self.__jfx_warning,
      'first': self.__jfx_first,
      'last': self.__jfx_last,
      'fields': self.__jfx_fields,
      'setg': self.__jfx_setg,
      'getg': self.__jfx_getg,
#      'nslookup': self.__jfx_nslookup,
      'rows': max([0, len(self.__g_datarows) - 1]),
      'data': [r[1:] if isinstance(r[0], int) else r for r in self.__g_datarows]
    }})

    if len(gvars) > 0:
      env.globals.update(gvars)

    for row in range(1, max(2, len(self.__g_datarows))):
      rowdata = {}

      if len(self.__g_datarows) > 0:
        for col in range(len(self.__g_datarows[0])):
          rowdata.update({ self.__g_datarows[0][col]: self.__g_datarows[row][col + 1] })

        env.globals['jinjafx'].update({ 'row': row })
        self.__g_row = row

      else:
        env.globals['jinjafx'].update({ 'row': 0 })
        self.__g_row = 0

      self.__g_vars = gvars
      self.__g_vars.update(rowdata)

      try:
        content = template.render(rowdata)

        outputs['0:_stderr_'] = []
        if len(self.__g_warnings) > 0:
          outputs['0:_stderr_'] = self.__g_warnings

      except Exception as e:
        if e.args[0].startswith('[jfx_exception] '):
          e.args = (e.args[0][16:],)
        else:
          if len(e.args) >= 1 and self.__g_row != 0:
            e.args = (e.args[0] + ' at data row ' + str(self.__g_datarows[row][0]) + ':\n - ' + str(rowdata),) + e.args[1:]
        raise

      stack = ['0:' + env.from_string(output).render(rowdata)]
      for l in iter(content.splitlines()):
        block_begin = re.search(r'<output[\t ]+["\']*(.+?)["\']*[\t ]*>(?:\[(-?\d+)\])?', l, re.IGNORECASE)
        if block_begin:
          if block_begin.group(2) != None:
            index = int(block_begin.group(2))
          else:
            index = 0

          stack.append(str(index) + ':' + block_begin.group(1).strip())
        else:
          block_end = re.search(r'</output[\t ]*>', l, re.IGNORECASE)
          if block_end:
            if len(stack) > 1:
              stack.pop()
            else:
              raise Exception('unbalanced output tags')
          else:
            if stack[-1] not in outputs:
              outputs[stack[-1]] = []
            outputs[stack[-1]].append(l)

      if len(stack) != 1:
        raise Exception('unbalanced output tags')

    for o in sorted(outputs.keys(), key=lambda x: int(x.split(':')[0])):
      nkey = o.split(':', 1)[1]

      if nkey not in outputs:
        outputs[nkey] = []
          
      outputs[nkey] += outputs[o]
      del outputs[o]

    return outputs


  def __jfx_lookup(self, method, variable, default=None):
    if method == 'vars':
      if variable in self.__g_vars:
        return self.__g_vars[variable]

      elif default is not None:
        return default
  
      else:
        raise jinja2.exceptions.UndefinedError('\'lookup\' variable \'' + variable + '\' is undefined')

    else:
      raise jinja2.exceptions.UndefinedError('\'lookup\' with method \'' + method + '\' is undefined')


  def __jfx_data_counter(self, m, orow, col, row):
    start = m.group(1)
    increment = m.group(2)
    pad = int(m.group(3)) if m.lastindex == 3 else 0 # TODO: REMOVE PAD

    if pad > 0:
      message = "padding on counters has been deprecated - please use the '%' pad operator instead"
      if message not in self.__g_warnings:
        self.__g_warnings.append(message)

    key = '_datacnt_r_' + str(orow) + '_' + str(col) + '_' + m.group()

    if self.__g_dict.get(key + '_' + str(row), True):
      n = self.__g_dict.get(key, int(start) - int(increment))
      self.__g_dict[key] = n + int(increment)
      self.__g_dict[key + '_' + str(row)] = False
    # return str(self.__g_dict[key]) # TODO: REMOVE PAD
    return str(self.__g_dict[key]).zfill(pad)


  def __jfx_expand(self, s, rg=False):
    pofa = [s]
    groups = [[s]]

    if re.search(r'(?<!\\)[\(\[\{]', pofa[0]):
      i = 0
      while i < len(pofa):
        m = re.search(r'(?<!\\)\((.+?)(?<!\\)\)', pofa[i])
        if m:
          for g in re.split(r'(?<!\\)\|', m.group(1)):
            pofa.append(pofa[i][:m.start(1) - 1] + g + pofa[i][m.end(1) + 1:])
            groups.append(groups[i] + [re.sub(r'\\([\|\(\[\)\]])', r'\1', g)])

          pofa.pop(i)
          groups.pop(i)

        else:
          i += 1

      i = 0
      while i < len(pofa):
        # m = re.search(r'(?<!\\)\{[ \t]*([0-9]+-[0-9]+):([0-9]+)[ \t]*(?<!\\)\}', pofa[i]) # TODO: REMOVE PAD
        m = re.search(r'(?<!\\)\{[ \t]*([0-9]+-[0-9]+):([0-9]+)(?::([0-9]+))?[ \t]*(?<!\\)\}', pofa[i])
        if m:
          mpos = groups[i][0].index(m.group())
          nob = len(re.findall(r'(?<!\\)\(', groups[i][0][:mpos]))
          ncb = len(re.findall(r'(?<!\\)\)', groups[i][0][:mpos]))
          groups[i][0] = groups[i][0].replace(m.group(), 'x', 1)
          group = max(0, (nob - ncb) * nob)

          e = list(map(int, m.group(1).split('-')))

          start = e[0]
          end = e[1] + 1 if e[1] >= e[0] else e[1] - 1
          step = int(m.group(2)) if end > start else 0 - int(m.group(2))

          for n in range(start, end, step):
            if m.lastindex == 3:
              message = "padding on counters has been deprecated - please use the '%' pad operator instead"
              if message not in self.__g_warnings:
                self.__g_warnings.append(message)

            n = str(n).zfill(int(m.group(3)) if m.lastindex == 3 else 0) # TODO: REMOVE PAD
            # pofa.append(pofa[i][:m.start(1) - 1] + str(n) + pofa[i][m.end(m.lastindex) + 1:]) # TODO: REMOVE PAD
            pofa.append(pofa[i][:m.start(1) - 1] + n + pofa[i][m.end(m.lastindex) + 1:])

            ngroups = list(groups[i])
            if group > 0 and group < len(ngroups):
              ngroups[group] = ngroups[group].replace(m.group(), n, 1)

            groups.append(ngroups)

          pofa.pop(i)
          groups.pop(i)

        else:
          m = re.search(r'(?<!\\)\[([A-Z0-9\-]+)(?<!\\)\]', pofa[i], re.IGNORECASE)
          if m and not re.match(r'(?:[A-Z]-[^A-Z]|[a-z]-[^a-z]|[0-9]-[^0-9]|[^A-Za-z0-9]-)', m.group(1)):
            clist = []
  
            mpos = groups[i][0].index(m.group())
            nob = len(re.findall(r'(?<!\\)\(', groups[i][0][:mpos]))
            ncb = len(re.findall(r'(?<!\\)\)', groups[i][0][:mpos]))
            groups[i][0] = groups[i][0].replace(m.group(), 'x', 1)
            group = max(0, (nob - ncb) * nob)
  
            for x in re.findall('([A-Z0-9](-[A-Z0-9])?)', m.group(1), re.IGNORECASE):
              if x[1] != '':
                e = x[0].split('-')

                start = ord(e[0])
                end = ord(e[1]) + 1 if ord(e[1]) >= ord(e[0]) else ord(e[1]) - 1
                step = 1 if end > start else -1

                for c in range(start, end, step):
                  clist.append(chr(c))
              else:
                clist.append(x[0])
  
            for c in clist:
              pofa.append(pofa[i][:m.start(1) - 1] + c + pofa[i][m.end(1) + 1:])
              ngroups = list(groups[i])
  
              if group > 0 and group < len(ngroups):
                ngroups[group] = ngroups[group].replace(m.group(), c, 1)
              
              groups.append(ngroups)
  
            pofa.pop(i)
            groups.pop(i)

          else:
            i += 1

    for g in groups:
      g.pop(0)

    pofa = [re.sub(r'\\([\|\(\[\)\]])', r'\1', i) for i in pofa]
    return [pofa, groups] if rg else pofa


  def __jfx_fandl(self, forl, fields, ffilter):
    fpos = []

    if self.__g_row == 0:
      return True

    if fields is not None:
      for f in fields:
        if f in self.__g_datarows[0]:
          fpos.append(self.__g_datarows[0].index(f) + 1)
        else:
          raise Exception('invalid field \'' + f + '\' passed to jinjafx.' + forl + '()')
    elif forl == 'first':
      return True if self.__g_row == 1 else False
    else:
      return True if self.__g_row == (len(self.__g_datarows) - 1) else False

    tv = ':'.join([self.__g_datarows[self.__g_row][i] for i in fpos])

    if forl == 'first':
      rows = range(1, len(self.__g_datarows))
    else:
      rows = range(len(self.__g_datarows) - 1, 0, -1)

    for r in rows:
      fmatch = True

      for f in ffilter:
        if f in self.__g_datarows[0]:
          try:
            if not re.match(ffilter[f], self.__g_datarows[r][self.__g_datarows[0].index(f) + 1]):
              fmatch = False
              break
          except Exception:
            raise Exception('invalid filter regex \'' + ffilter[f] + '\' for field \'' + f + '\' passed to jinjafx.' + forl + '()')
        else:
          raise Exception('invalid filter field \'' + f + '\' passed to jinjafx.' + forl + '()')

      if fmatch:
        if tv == ':'.join([self.__g_datarows[r][i] for i in fpos]):
          return True if self.__g_row == r else False

    return False


  def __jfx_exception(self, message):
    raise Exception('[jfx_exception] ' + message)


  def __jfx_warning(self, message, repeat=False):
    if repeat or message not in self.__g_warnings:
      self.__g_warnings.append(message)
    return ''


  def __jfx_first(self, fields=None, ffilter={}):
    return self.__jfx_fandl('first', fields, ffilter)


  def __jfx_last(self, fields=None, ffilter={}):
    return self.__jfx_fandl('last', fields, ffilter)

  
  def __jfx_fields(self, field=None, ffilter={}):
    if field is not None:
      if field in self.__g_datarows[0]:
        fpos = self.__g_datarows[0].index(field) + 1
      else:
        raise Exception('invalid field \'' + field + '\' passed to jinjafx.fields()')
    else:
      return None
    
    field_values = []
        
    for r in range(1, len(self.__g_datarows)):
      fmatch = True
      field_value = self.__g_datarows[r][fpos]

      if field_value not in field_values and len(field_value.strip()) > 0:
        for f in ffilter:
          if f in self.__g_datarows[0]:
            try:
              if not re.match(ffilter[f], self.__g_datarows[r][self.__g_datarows[0].index(f) + 1]):
                fmatch = False
                break
            except Exception:
              raise Exception('invalid filter regex \'' + ffilter[f] + '\' for field \'' + f + '\' passed to jinjafx.fields()')
          else:
            raise Exception('invalid filter field \'' + f + '\' passed to jinjafx.fields()')

        if fmatch:
          field_values.append(field_value)
    
    return field_values

 
  def __jfx_counter(self, key=None, increment=1, start=1):
    if key is None:
      key = '_cnt_r_' + str(self.__g_row)
    else:
      key = '_cnt_k_' + str(key)

    n = self.__g_dict.get(key, int(start) - int(increment))
    self.__g_dict[key] = n + int(increment)
    return self.__g_dict[key]


  def __jfx_setg(self, key, value):
    self.__g_dict['_val_' + str(key)] = value
    return ''


  def __jfx_getg(self, key, default=None):
    return self.__g_dict.get('_val_' + str(key), default)


#  def __jfx_nslookup(self, v, family=46):
#    try:
#      if re.match(r'^(?:[0-9a-f:]+:+)+[0-9a-f]+$', v, re.I): # IPv6
#        return [socket.getnameinfo((v, 0), socket.NI_NAMEREQD)[0]]
#
#      elif re.match(r'^(?:[0-9]+\.){3}[0-9]+$', v): # IPv4
#        return [socket.getnameinfo((v, 0), socket.NI_NAMEREQD)[0]]
#
#      else:
#        if int(family) == 46:
#          s = socket.getaddrinfo(v, 0, 0, socket.SOCK_STREAM)
#          return [e[4][0] for e in s]
#        elif int(family) == 4:
#          s = socket.getaddrinfo(v, 0, socket.AF_INET, socket.SOCK_STREAM)
#          return [e[4][0] for e in s]
#        elif int(family) == 6:
#          s = socket.getaddrinfo(v, 0, socket.AF_INET6, socket.SOCK_STREAM)
#          return [e[4][0] for e in s]
#
#    except:
#      pass
#
#    return None


  def __jfx_regex(self, value='', pattern='', ignorecase=False, multiline=False, match_type='search', flags=0):
    if ignorecase:
      flags |= re.I

    if multiline:
      flags |= re.M

    _re = re.compile(pattern, flags=flags)
    return bool(getattr(_re, match_type, 'search')(value))


  def __jfx_match(self, value, pattern='', ignorecase=False, multiline=False):
    return self.__jfx_regex(value, pattern, ignorecase, multiline, 'match')


  def __jfx_search(self, value, pattern='', ignorecase=False, multiline=False):
    return self.__jfx_regex(value, pattern, ignorecase, multiline, 'search')


  def __find_re_match(self, o, v, default=0):
    for rx in o:
      if rx[0].match(v):
        return rx[1]

    return default


if __name__ == '__main__':
  main()
