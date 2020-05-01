#!/usr/bin/env python

# JinjaFx - Jinja Templating Tool
# Copyright (c) 2020 Chris Mason <chris@jinjafx.org>
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

from __future__ import print_function, division
import sys, os, jinja2, yaml, argparse, re

__version__ = '1.0.2'

class ArgumentParser(argparse.ArgumentParser):
  def error(self, message):
    print('URL:\n  https://github.com/cmason3/jinjafx\n', file=sys.stderr)
    print('Usage:\n  ' + self.format_usage()[7:], file=sys.stderr)
    raise Exception(message)


def main():
  try:
    print('JinjaFx v' + __version__ + ' - Jinja Templating Tool')
    print('Copyright (c) 2020 Chris Mason <chris@jinjafx.org>\n')

    parser = ArgumentParser(add_help=False)
    parser.add_argument('-t', metavar='<template.j2>', type=argparse.FileType('r'), required=True)
    parser.add_argument('-d', metavar='<data.csv>', type=argparse.FileType('r'))
    parser.add_argument('-g', metavar='<vars.yml>', type=argparse.FileType('r'), action='append')
    parser.add_argument('-o', metavar='<output file>', type=str)
    parser.add_argument('--ask-vault-pass', action='store_true')
    args = parser.parse_args()

    data = None
    vault = None
    gvars = {}

    if args.d is not None:
      with open(args.d.name) as file:
        data = file.read()

    if args.g is not None:
      for g in args.g:
        with open(g.name) as file:
          gyaml = file.read()

          if gyaml.startswith('$ANSIBLE_VAULT'):
            if vault is None:
              from ansible.constants import DEFAULT_VAULT_ID_MATCH
              from ansible.parsing.vault import VaultLib
              from ansible.parsing.vault import VaultSecret
              from getpass import getpass

              if args.ask_vault_pass:
                vpw = getpass('Vault Password: ')
                print()
              else:
                vpw = os.getenv('ANSIBLE_VAULT_PASS', '')

              vault = VaultLib([(DEFAULT_VAULT_ID_MATCH, VaultSecret(vpw.encode('utf-8')))])

            gyaml = vault.decrypt(gyaml.encode('utf8'))

          gvars.update(yaml.load(gyaml, Loader=yaml.FullLoader))

    if args.o is None:
      args.o = '_stdout_'

    outputs = JinjaFx().jinjafx(args.t, data, gvars, args.o)
    ocount = 0

    for o in sorted(outputs.items(), key=lambda x: (x[0] == '_stdout_')):
      output = '\n'.join(o[1]) + '\n'
      if len(output.strip()) > 0:
        if o[0] != '_stdout_':
          ofile = re.sub(r'_+', '_', re.sub(r'[^A-Za-z0-9_. -/]', '_', os.path.normpath(o[0])))

          if os.path.dirname(ofile) != '':
            if not os.path.isdir(os.path.dirname(ofile)):
              os.makedirs(os.path.dirname(ofile))

          with open(ofile, 'w') as file:
            file.write(output)

          print(format_bytes(len(output)) + ' > ' + ofile)

        else:
          if ocount > 0:
            print('\n-\n')
          print(output)

        ocount += 1

    if ocount > 0:
      if '_stdout_' not in outputs:
        print()
    else:
      raise Exception('nothing to output')

  except KeyboardInterrupt:
    sys.exit(-1)

  except jinja2.exceptions.UndefinedError as e:
    print('error: template variable ' + str(e), file=sys.stderr)
    sys.exit(-3)

  except Exception as e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    print('error[' + str(exc_tb.tb_lineno) + ']: ' + str(e), file=sys.stderr)
    sys.exit(-2)


def format_bytes(b):
  for u in [ '', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y' ]:
    if b >= 1000:
      b /= 1000
    else:
      return '{:.2f}'.format(b).rstrip('0').rstrip('.') + u + 'B'


class JinjaFx():
  def jinjafx(self, template, data, gvars, output):
    self.g_datarows = []
    self.g_dict = {}
    self.g_row = 0 

    outputs = {}
    delim = None
    
    if isinstance(data, bytes):
      data = data.decode('utf-8')

    if data is not None and len(data.strip()) > 0:
      for l in data.strip().splitlines():
        if len(l.strip()) > 0:
          if len(self.g_datarows) == 0:
            delim = r'[ \t]*,[ \t]*' if l.count(',') > l.count('\t') else r' *\t *'
            fields = re.split(delim, re.sub('(?:' + delim + ')+$', '', l))
            fields = [re.sub(r'^(["\'])(.*)\1$', r'\2', f) for f in fields]

            if '' in fields:
              raise Exception('empty column header detected in data')
            elif len(set(fields)) != len(fields):
              raise Exception('duplicate column header detected in data')
            else:
              self.g_datarows.append(fields)

          else:
            n = len(self.g_datarows[0])
            fields = [re.sub(r'^(["\'])(.*)\1$', r'\2', f) for f in re.split(delim, l)]
            fields = [list(map(self.jfx_expand, fields[:n] + [''] * (n - len(fields))))]

            row = 0
            while row < len(fields):
              if any(isinstance(col, list) for col in fields[row]):
                for col in range(len(fields[row])):
                  if isinstance(fields[row][col], list):
                    for val in fields[row][col]:
                      nrow = list(fields[row])
                      nrow[col] = val
                      fields.append(nrow)

                    fields.pop(row)
                    break

              else:
                self.g_datarows.append(fields[row])
                row += 1

      if len(self.g_datarows) <= 1:
        raise Exception('not enough data rows - need at least two')

    if 'jinja_extensions' not in gvars:
      gvars.update({ 'jinja_extensions': [] })

    if isinstance(template, str) or isinstance(template, bytes):
      env = jinja2.Environment(extensions=gvars['jinja_extensions'], undefined=jinja2.StrictUndefined)
      template = env.from_string(str(template))
    else:
      env = jinja2.Environment(extensions=gvars['jinja_extensions'], loader=jinja2.FileSystemLoader(os.path.dirname(template.name)), undefined=jinja2.StrictUndefined)
      template = env.get_template(os.path.basename(template.name))

    env.trim_blocks = True
    env.lstrip_blocks = True
    env.keep_trailing_newline = True

    env.globals.update({ 'jinjafx': {
      'version': __version__,
      'jinja_version': jinja2.__version__,
      'expand': self.jfx_expand,
      'counter': self.jfx_counter,
      'first': self.jfx_first,
      'last': self.jfx_last,
      'setg': self.jfx_setg,
      'getg': self.jfx_getg,
      'rows': max([0, len(self.g_datarows) - 1]),
      'data': self.g_datarows
    }})

    if len(gvars) > 0:
      env.globals.update(gvars)

    for row in range(1, max(2, len(self.g_datarows))):
      rowdata = {}

      if len(self.g_datarows) > 0:
        for col in range(len(self.g_datarows[0])):
          rowdata.update({ self.g_datarows[0][col]: self.g_datarows[row][col] })

        env.globals['jinjafx'].update({ 'row': row })
        self.g_row = row

      else:
        env.globals['jinjafx'].update({ 'row': 0 })
        self.g_row = 0

      content = template.render(rowdata)

      stack = [ env.from_string(output).render(rowdata) ]
      for l in iter(content.splitlines()):
        block_begin = re.search(r'<output[\t ]+["\']*(.+?)["\']*[\t ]*>', l, re.IGNORECASE)
        if block_begin:
          stack.append(block_begin.group(1).strip())
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

    return outputs


  def jfx_expand(self, s):
    pofa = [s]

    if re.search(r'(?<!\\)[\(\[]', pofa[0]):
      i = 0
      while i < len(pofa):
        m = re.search(r'(?<!\\)\((.+?)(?<!\\)\)', pofa[i])
        if m:
          for g in m.group(1).split('|'):
            pofa.append(pofa[i][:m.start(1) - 1] + g + pofa[i][m.end(1) + 1:])
      
          pofa.pop(i)

        else:
          i += 1

      i = 0
      while i < len(pofa):
        m = re.search(r'(?<!\\)\[([A-Z0-9\-]+)(?<!\\)\]', pofa[i], re.IGNORECASE)
        if m and not re.match(r'(?:[A-Z]-[^A-Z]|[a-z]-[^a-z]|[0-9]-[^0-9]|[^A-Za-z0-9]-)', m.group(1)):
          clist = []

          for x in re.findall('([A-Z0-9](-[A-Z0-9])?)', m.group(1), re.IGNORECASE):
            if x[1] != '':
              e = sorted(x[0].split('-'))
              for c in range(ord(e[0]), ord(e[1]) + 1):
                clist.append(chr(c))
            else:
              clist.append(x[0])

          for c in clist:
            pofa.append(pofa[i][:m.start(1) - 1] + c + pofa[i][m.end(1) + 1:])

          pofa.pop(i)

        else:
          i += 1

    pofa = [re.sub(r'\\([\(\[\)\]])', r'\1', i) for i in pofa]
    return pofa


  def jfx_fandl(self, forl, fields, ffilter):
    fpos = []

    if self.g_row == 0:
      return True

    if fields is not None:
      for f in fields:
        if f in self.g_datarows[0]:
          fpos.append(self.g_datarows[0].index(f))
        else:
          raise Exception('invalid field \'' + f + '\' passed to jinjafx.' + forl + '()')
    elif forl == 'first':
      return True if self.g_row == 1 else False
    else:
      return True if self.g_row == (len(self.g_datarows) - 1) else False

    tv = ':'.join([self.g_datarows[self.g_row][i] for i in fpos])

    if forl == 'first':
      rows = range(1, len(self.g_datarows))
    else:
      rows = range(len(self.g_datarows) - 1, 0, -1)

    for r in rows:
      fmatch = True

      for f in ffilter:
        if f in self.g_datarows[0]:
          try:
            if not re.match(ffilter[f], self.g_datarows[r][self.g_datarows[0].index(f)]):
              fmatch = False
              break
          except Exception:
            raise Exception('invalid filter regex \'' + ffilter[f] + '\' for field \'' + f + '\' passed to jinjafx.' + forl + '()')
        else:
          raise Exception('invalid filter field \'' + f + '\' passed to jinjafx.' + forl + '()')

      if fmatch:
        if tv == ':'.join([self.g_datarows[r][i] for i in fpos]):
          return True if self.g_row == r else False

    return False


  def jfx_first(self, fields=None, ffilter={}):
    return self.jfx_fandl('first', fields, ffilter)


  def jfx_last(self, fields=None, ffilter={}):
    return self.jfx_fandl('last', fields, ffilter)


  def jfx_counter(self, key=None, increment=1, start=1):
    if key is None:
      key = '_cnt_r_' + str(self.g_row)
    else:
      key = '_cnt_k_' + str(key)

    n = self.g_dict.get(key, int(start) - int(increment))
    self.g_dict[key] = n + int(increment)
    return self.g_dict[key]


  def jfx_setg(self, key, value):
    self.g_dict['_val_' + str(key)] = value
    return ''


  def jfx_getg(self, key, default=None):
    return self.g_dict.get('_val_' + str(key), default)


if __name__ == '__main__':
  main()
