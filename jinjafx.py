#!/usr/bin/env python3

# JinjaFx - Jinja2 Templating Tool
# Copyright (c) 2020-2025 Chris Mason <chris@netnix.org>
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

import sys
if sys.version_info < (3, 9):
  sys.exit('Requires Python >= 3.9')

import os, io, importlib.util, importlib.metadata, argparse, re, getpass, datetime, copy
import jinja2, jinja2.sandbox, yaml, zoneinfo, base64, tempfile, shutil

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.hmac import HMAC
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.modes import CTR
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.exceptions import InvalidSignature
from cryptography.exceptions import InvalidTag

__version__ = '1.26.1'

__all__ = ['JinjaFx', 'AnsibleVault', 'Vaulty']

def main():
  exc_source = None

  try:
    if not any(x in ['-q', '-encrypt', '-decrypt'] for x in sys.argv):
      print(f'JinjaFx v{__version__} - Jinja2 Templating Tool')
      print('Copyright (c) 2020-2025 Chris Mason <chris@netnix.org>\n')

    prog = os.path.basename(sys.argv[0])
    jinjafx_usage = '-t <template.j2> [-d [<data.csv>]] [-g <vars.(yml|json)>]\n'
    jinjafx_usage += (' ' * (len(prog) + 3)) + '-dt <dt.yml> [-ds <dataset>] [-d [<data.csv>]] [-g <vars.(yml|json)>]\n'
    jinjafx_usage += (' ' * (len(prog) + 3)) + '-encrypt/-decrypt [<file1>] [<file2>] [..]\n'
    jinjafx_usage += '''

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
  ANSIBLE_VAULT_PASSWORD_FILE  - specify an Ansible Vault password file'''

    parser = __ArgumentParser(add_help=False, usage=f'{prog} {jinjafx_usage}')
    group_ex = parser.add_mutually_exclusive_group(required=True)
    group_ex.add_argument('-t', type=argparse.FileType('r'))
    group_ex.add_argument('-dt', type=argparse.FileType('r'))
    group_ex.add_argument('-encrypt', type=str, nargs='*')
    group_ex.add_argument('-decrypt', type=str, nargs='*')
    parser.add_argument('-d', type=argparse.FileType('r'), nargs='?', const='-')
    parser.add_argument('-ds', type=str)
    parser.add_argument('-g', type=argparse.FileType('r'), action='append')
    parser.add_argument('-var', type=str, action='append')
    parser.add_argument('-ed', type=str, action='append', default=[])
    parser.add_argument('-o', type=str)
    parser.add_argument('-od', type=str)
    parser.add_argument('-m', action='store_true')
    parser.add_argument('-q', action='store_true')
    args = parser.parse_args()

    if args.dt is None and args.ds is not None:
      parser.error('argument -ds: only allowed with argument -dt')

    if args.m and args.g is None:
      parser.error('argument -m: only allowed with argument -g')

    if args.od is not None and not os.access(args.od, os.W_OK):
      parser.error('argument -od: unable to write to output directory')

    gvars = {}
    data = None
    vpw = [None]

    if args.encrypt is not None:
      if not args.encrypt:
        b_string = sys.stdin.buffer.read().strip()
        if len(b_string.splitlines()) > 1:
          raise Exception('multiline stings not permitted')

        __get_vault_credentials(vpw, True)
        vtext = AnsibleVault().encrypt(b_string, vpw[0])
        print('!vault |\n' + re.sub(r'^', ' ' * 10, vtext, flags=re.MULTILINE))

      else:
        __get_vault_credentials(vpw, True)

        for f in args.encrypt:
          if os.path.isfile(f):
            print(f'Encrypting {f}... ', flush=True, end='')

            try:
              with open(f, 'rb') as fh:
                vtext = AnsibleVault().encrypt(fh.read(), vpw[0])

              with open(f, 'wb') as fh:
                fh.write(vtext.encode('utf-8'))
                print('ok')

            except Exception as e:
              print('failed')
              print(f'error: {e}', file=sys.stderr)

          elif not os.path.exists(f):
            print(f'Encrypting {f}... not found')

          else:
            print(f'Encrypting {f}... unsupported')

    elif args.decrypt is not None:
      if not args.decrypt:
        b_vtext = sys.stdin.buffer.read()
        __get_vault_credentials(vpw)
        print(AnsibleVault().decrypt(b_vtext, vpw[0]).decode('utf-8'))

      else:
        __get_vault_credentials(vpw)

        for f in args.decrypt:
          if os.path.isfile(f):
            print(f'Decrypting {f}... ', flush=True, end='')

            try:
              with open(f, 'rb') as fh:
                plaintext = AnsibleVault().decrypt(fh.read(), vpw[0])

              with open(f, 'wb') as fh:
                fh.write(plaintext)
                print('ok')

            except Exception as e:
              print('failed')
              print(f'error: {e}', file=sys.stderr)

          elif not os.path.exists(f):
            print(f'Decrypting {f}... not found')

          else:
            print(f'Decrypting {f}... unsupported')

    else:
      vault_undef = False

      def yaml_vault_tag(loader, node):
        x = __decrypt_vault(vpw, node.value, vault_undef)
        if x is not None:
          return x.decode('utf-8')

        else:
          return '_undef'

      if args.dt is not None:
        with open(args.dt.name, 'rt') as f:
          try:
            dt = yaml.load(f.read(), Loader=yaml.SafeLoader)['dt']

          except Exception as e:
            exc_source = args.dt.name
            raise

          args.t = dt['template']
          gv = ''

          if 'datasets' in dt:
            if args.ds is not None:
              try:
                args.ds = re.compile(args.ds, re.IGNORECASE)

              except Exception:
                parser.error('argument -ds: invalid regular expression')

              matches = list(filter(args.ds.search, list(dt['datasets'].keys())))
              if len(matches) == 1:
                if 'data' in dt['datasets'][matches[0]]:
                  dt['data'] = dt['datasets'][matches[0]]['data']

                if 'global' in dt:
                  gv = dt['global']

                if 'vars' in dt['datasets'][matches[0]]:
                  dt['vars'] = dt['datasets'][matches[0]]['vars']

              else:
                parser.error('argument -ds: must only match a single dataset')

            else:
              parser.error('argument -ds: required with datatemplates that use datasets')

          elif args.ds is not None:
            parser.error('argument -ds: not required with datatemplates without datasets')

          if 'data' in dt:
            data = dt['data']

          yaml.add_constructor('!vault', lambda x, y: None, yaml.SafeLoader)

          if gv:
            try:
              if 'jinjafx_vault_undefined' in gv:
                if y := yaml.load(gv, Loader=yaml.SafeLoader):
                  vault_undef = y.get('jinjafx_vault_undefined', vault_undef)

            except Exception as e:
              exc_source = 'dt:global'
              raise

          if 'vars' in dt:
            try:
              if 'jinjafx_vault_undefined' in dt['vars']:
                if y := yaml.load(dt['vars'], Loader=yaml.SafeLoader):
                  vault_undef = y.get('jinjafx_vault_undefined', vault_undef)

            except Exception as e:
              exc_source = 'dt:vars'
              raise

          yaml.add_constructor('!vault', yaml_vault_tag, yaml.SafeLoader)

          if gv:
            try:
              if y := yaml.load(gv, Loader=yaml.SafeLoader):
                if isinstance(y, list):
                  y = {'_': y}

                gvars.update(y)

            except Exception as e:
              exc_source = 'dt:global'
              raise

          if 'vars' in dt:
            try:
              if y := yaml.load(dt['vars'], Loader=yaml.SafeLoader):
                if isinstance(y, list):
                  y = {'_': y}

                gvars.update(y)

            except Exception as e:
              exc_source = 'dt:vars'
              raise

      if args.d is not None:
        if args.d.name == '<stdin>':
          if sys.stdin.isatty():
            print('Paste in Data (CTRL+D to End)...')

          if data is not None:
            data += args.d.read()
          else:
            data = args.d.read()

          if sys.stdin.isatty():
            print()

        else:
          with open(args.d.name, 'rt') as f:
            if data is not None:
              data += f.read()
            else:
              data = f.read()

      if args.g is not None:
        fcontents = {}

        yaml.add_constructor('!vault', lambda x, y: None, yaml.SafeLoader)

        for g in args.g:
          with open(g.name, 'rt') as f:
            fcontents[g.name] = __decrypt_vault(vpw, f.read())

          try:
            if b'jinjafx_vault_undefined' in fcontents[g.name]:
              if y := yaml.load(fcontents[g.name], Loader=yaml.SafeLoader):
                vault_undef = y.get('jinjafx_vault_undefined', vault_undef)

          except Exception as e:
            exc_source = g.name
            raise

        yaml.add_constructor('!vault', yaml_vault_tag, yaml.SafeLoader)

        for g in args.g:
          try:
            if y := yaml.load(fcontents[g.name], Loader=yaml.SafeLoader):
              if isinstance(y, list):
                y = {'_': y}

              if args.m == True:
                __merge(gvars, y)
              else:
                gvars.update(y)

          except Exception as e:
            exc_source = g.name
            raise

      if args.var is not None:
        for v in args.var:
          x, value = list(map(str.strip, v.split('=')))
          gvars[x] = value

      if args.o is None:
        args.o = '_stdout_'

      s = [gvars]

      while s:
        c = s.pop()
        for key in list(c.keys()):
          if c[key] == '_undef':
            del c[key]
          elif isinstance(c[key], dict):
            s.append(c[key])
          elif isinstance(c[key], list):
            for item in c[key]:
              if isinstance(item, dict):
                s.append(item)

      if 'jinjafx_input' in gvars:
        jinjafx_input = {}

        if 'prompt' in gvars['jinjafx_input'] and gvars['jinjafx_input']['prompt']:
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

                if not jinjafx_input[k]:
                  if v['required']:
                    print('error: input is required', file=sys.stderr)
                  else:
                    break
                else:
                  m = re.match(v['pattern'], jinjafx_input[k], re.IGNORECASE)
                  if not m or (m.span()[1] - m.span()[0]) != len(jinjafx_input[k]):
                    print('error: input doesn\'t match pattern "' + v['pattern'] + '"', file=sys.stderr)
                  else:
                    break

            else:
              jinjafx_input[k] = input(v + ': ').strip()

          print()

        gvars['jinjafx_input'] = jinjafx_input

      args.ed = [os.getcwd(), os.getenv('HOME', '') + '/.jinjafx'] + args.ed
      outputs = JinjaFx()._jinjafx(args.t, data, gvars, args.o, args.ed)
      ocount = 0

      if args.od is not None:
        os.chdir(args.od)

      if outputs['_stderr_']:
        print('Warnings:', file=sys.stderr)
        for w in outputs['_stderr_']:
          print(f' - {w}', file=sys.stderr)

        print('', file=sys.stderr)

      for o in sorted(sorted(outputs.items()), key=lambda x: (x[0] == '_stdout_')):
        if o[0] != '_stderr_':
          output = '\n'.join(o[1]) + '\n'
          if output.strip():
            if o[0] == '_stdout_':
              if ocount:
                print('\n-\n')
              print(output)

            else:
              ofile = re.sub(r'_+', '_', re.sub(r'[^A-Za-z0-9_. -/]', '_', os.path.normpath(o[0])))

              if os.path.dirname(ofile) != '':
                if not os.path.isdir(os.path.dirname(ofile)):
                  os.makedirs(os.path.dirname(ofile))

              with open(ofile, 'wt') as f:
                f.write(output)

              print(__format_bytes(len(output)) + ' > ' + os.path.abspath(ofile))

            ocount += 1

      if ocount:
        if '_stdout_' not in outputs:
          print()

      else:
        raise Exception('nothing to output')

  except KeyboardInterrupt:
    sys.exit(-1)

  except jinja2.TemplateError as e:
    if hasattr(e, 'name') and e.name and hasattr(e, 'lineno') and e.lineno:
      print(f'error[{e.name}:{e.lineno}]: {type(e).__name__}: {e}', file=sys.stderr)

    else:
      error = _format_error(e, 'template code')
      print(error.replace('__init__.py:', 'jinjafx.py:'), file=sys.stderr)

    sys.exit(-2)

  except Exception as e:
    error = _format_error(e, 'template code', '_jinjafx')
    print(error.replace('__init__.py:', 'jinjafx.py:'), file=sys.stderr)
    sys.exit(-2)


def _format_error(e, *args):
  tb = e.__traceback__
  stack = []
  msg = str(e)

  if isinstance(e, jinja2.TemplateNotFound):
    if ' in search path' in msg:
      msg = msg[:msg.index(' in search path')]

  while tb is not None:
    stack.append([tb.tb_frame.f_code.co_filename, tb.tb_frame.f_code.co_name, tb.tb_lineno])
    tb = tb.tb_next

  for a in args:
    for s in reversed(stack):
      if a in s[1]:
        return f'error[{os.path.basename(s[0])}:{s[2]}]: {type(e).__name__}: {msg}'

  return f'error[{os.path.basename(stack[0][0])}:{stack[0][2]}]: {type(e).__name__}: {msg}'


def __decrypt_vault(vpw, string, return_none=False):
  if string.lstrip().startswith('$ANSIBLE_VAULT;'):
    __get_vault_credentials(vpw)

    if vpw[0].strip():
      return_none = False

    return AnsibleVault().decrypt(string.encode('utf-8'), vpw[0], return_none)
  return string.encode('utf-8')


def __get_vault_credentials(vpw, verify=False):
  if vpw[0] is None:
    vpw[0] = os.getenv('ANSIBLE_VAULT_PASSWORD')

    if vpw[0] is None:
      vpwf = os.getenv('ANSIBLE_VAULT_PASSWORD_FILE')
      if vpwf is not None:
        with open(vpwf, 'rt') as f:
          vpw[0] = f.read().strip()

    if vpw[0] is None:
      vpw[0] = getpass.getpass('Vault Password: ')

      if verify:
        if vpw[0] != getpass.getpass('Password Verification: '):
          print()
          raise Exception('password verification failed')

      print()


def __format_bytes(b):
  for u in [ '', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y' ]:
    if b >= 1000:
      b /= 1000
    else:
      break

  return f'{b:.2f}'.rstrip('0').rstrip('.') + u + 'B'


def __merge(dst, src):
  for key in src:
    if key in dst:
      if isinstance(dst[key], dict) and isinstance(src[key], dict):
        __merge(dst[key], src[key])

      elif isinstance(dst[key], list) and isinstance(src[key], list):
        dst[key] += src[key]

      else:
        dst[key] = src[key]

    else:
      dst[key] = src[key]

  return dst


class __ArgumentParser(argparse.ArgumentParser):
  def error(self, message):
    if '-q' not in sys.argv:
      print('URL:\n  https://github.com/cmason3/jinjafx\n', file=sys.stderr)
      print(f'Usage:\n  {self.format_usage()[7:]}', file=sys.stderr)
    raise Exception(message)


class JinjaFx():
  def _jinjafx(self, template, data, gvars, output, exts_dirs=None, sandbox=False, use_oformat=False):
    self.__g_datarows = []
    self.__g_dict = {}
    self.__g_row = 0
    self.__g_vars = {}
    self.__g_filters = {}
    self.__g_warnings = []
    self.__g_xlimit = 5000 if sandbox else 0
    self.__g_hcounter = re.compile(r'(?:[A-Z]\.)+$', re.IGNORECASE)

    outputs = {}
    delim = None
    rowkey = 1
    int_indices = []
    float_indices = []
    list_indices = []
    tempdir = None

    if not isinstance(template, (str, io.TextIOWrapper, dict)):
      raise TypeError('template must be of type str, dict or type FileType')

    if isinstance(template, dict) and ('Default' not in template):
      raise TypeError('dict based templates must contain a "Default" key')

    if data is not None:
      if not isinstance(data, str):
        raise TypeError('data must be of type str')

      if data.strip():
        jinjafx_filter = {}
        jinjafx_adjust_headers = str(gvars.get('jinjafx_adjust_headers', 'no')).strip().lower()
        recm = re.compile(r'(?<!\\){[ \t]*([0-9]+):([0-9]+)(:[0-9]+)?[ \t]*(?<!\\)}')
        rotm = re.compile(r'(?<!\\){[ \t]*((?:[0-9]+\|)+[0-9]+)(:[0-9]+)?[ \t]*(?<!\\)}')

        for l in data.splitlines():
          if l.strip() and not re.match(r'^[ \t]*#', l):
            if not self.__g_datarows:
              if l.count(',') > l.count('\t'):
                delim = r'[ \t]*(?<!\\),[ \t]*'
                schars = ' \t'
              else:
                delim = r' *\t *'
                schars = ' '

              hfields = re.split(delim, re.sub('(?:' + delim + ')+$', '', l.strip(schars)))
              hfields = [re.sub(r'^(["\'])(.*)\1$', r'\2', f) for f in hfields]

              for i, v in enumerate(hfields):
                hfields[i] = re.sub(r'^\[[ \t]*(\S+)[ \t]*\]$', r'\1', v)
                if hfields[i] != v:
                  list_indices.append(i + 1)
                  v = hfields[i]

                if v.lower().endswith(':int'):
                  int_indices.append(i + 1)
                  hfields[i] = v[:-4]
                elif v.lower().endswith(':float'):
                  float_indices.append(i + 1)
                  hfields[i] = v[:-6]

                if jinjafx_adjust_headers == 'yes':
                  hfields[i] = re.sub(r'[^A-Z0-9_]', '', v, flags=re.UNICODE | re.IGNORECASE)
                elif jinjafx_adjust_headers == 'upper':
                  hfields[i] = re.sub(r'[^A-Z0-9_]', '', v.upper(), flags=re.UNICODE | re.IGNORECASE)
                elif jinjafx_adjust_headers == 'lower':
                  hfields[i] = re.sub(r'[^A-Z0-9_]', '', v.lower(), flags=re.UNICODE | re.IGNORECASE)
                elif jinjafx_adjust_headers != 'no':
                  raise Exception('invalid value specified for \'jinjafx_adjust_headers\' - must be \'yes\', \'no\', \'upper\' or \'lower\'')

                if hfields[i] == '':
                  raise Exception(f'empty header field detected at column position {i + 1}')

                elif not re.match(r'^[A-Z_][A-Z0-9_]*$', hfields[i], re.IGNORECASE):
                  raise Exception(f'header field at column position {i + 1} contains invalid characters')

              if len(set(hfields)) != len(hfields):
                raise Exception('duplicate header field detected in data')

              else:
                self.__g_datarows.append(hfields)

              if 'jinjafx_filter' in gvars and gvars['jinjafx_filter']:
                for field in gvars['jinjafx_filter']:
                  jinjafx_filter[self.__g_datarows[0].index(field) + 1] = gvars['jinjafx_filter'][field]

            else:
              gcount = 1
              ufields = []

              for f in re.split(delim, l.strip(schars)):
                delta = 0

                for m in re.finditer(r'(?<!\\)\((.+?)(?<!\\)\)', f):
                  if not re.search(r'(?<!\\)\|', m.group(1)):
                    if not re.search(r'\\' + str(gcount), l):
                      if re.search(r'\\[0-9]+', l):
                        raise Exception(f'parenthesis in row {rowkey} at "{m.group(0)}" should be escaped or removed')

                      else:
                        f = f[:m.start() + delta] + '\\(' + m.group(1) + '\\)' + f[m.end() + delta:]
                        delta += 2

                  gcount += 1

                ufields.append(re.sub(r'^(["\'])(.*)\1$', r'\2', f))

              n = len(self.__g_datarows[0])
              fields = [list(map(self.__jfx_expand, ufields[:n] + [''] * (n - len(ufields)), [True] * n))]

              row = 0
              while fields:
                if not isinstance(fields[0][0], int):
                  fields[0].insert(0, rowkey)
                  rowkey += 1

                if any(isinstance(colx[0], list) for colx in fields[0][1:]):
                  for col in range(1, len(fields[0])):
                    if isinstance(fields[0][col][0], list):
                      for i, v in enumerate(fields[0][col][0]):
                        nrow = [e[:] if isinstance(e, list) else e for e in fields[0]]
                        nrow[col] = [v, fields[0][col][1][i]]
                        fields.append(nrow)

                      fields.pop(0)
                      break

                else:
                  xgroups = []

                  for col in range(1, len(fields[0])):
                    fields[0][col][0] = recm.sub(lambda m: self.__jfx_data_counter(m, fields[0][0], col, row), fields[0][col][0])
                    fields[0][col][0] = rotm.sub(lambda m: self.__jfx_data_loop(m, fields[0][0], col, row), fields[0][col][0])

                    for g in range(len(fields[0][col][1])):
                      fields[0][col][1][g] = recm.sub(lambda m: self.__jfx_data_counter(m, fields[0][0], col, row), fields[0][col][1][g])
                      fields[0][col][1][g] = rotm.sub(lambda m: self.__jfx_data_loop(m, fields[0][0], col, row), fields[0][col][1][g])

                    xgroups.append(fields[0][col][1])

                  groups = dict(enumerate(sum(xgroups, ['\\0'])))

                  for col in range(1, len(fields[0])):
                    fields[0][col] = re.sub(r'\\([0-9]+)', lambda m: groups.get(int(m.group(1)), '\\' + str(m.group(1))), fields[0][col][0])

                    delta = 0
                    for m in re.finditer(r'([0-9]+)(?<!\\)\%([0-9]+)', fields[0][col]):
                      pvalue = str(int(m.group(1))).zfill(int(m.group(2)))
                      fields[0][col] = fields[0][col][:m.start() + delta] + pvalue + fields[0][col][m.end() + delta:]

                      if len(m.group(0)) > len(pvalue):
                        delta -= len(m.group(0)) - len(pvalue)
                      else:
                        delta += len(pvalue) - len(m.group(0))

                    fields[0][col] = re.sub(r'\\([}{%,])', r'\1', fields[0][col])

                    if col in list_indices:
                      fields[0][col] = re.split(r'[ \t]*;[ \t]*', fields[0][col])

                      if col in int_indices:
                        fields[0][col] = list(map(int, fields[0][col]))

                      elif col in float_indices:
                        fields[0][col] = list(map(float, fields[0][col]))

                    elif col in int_indices:
                      fields[0][col] = int(fields[0][col])

                    elif col in float_indices:
                      fields[0][col] = float(fields[0][col])

                  include_row = True
                  if jinjafx_filter:
                    for index in jinjafx_filter:
                      if isinstance(fields[0][index], list):
                        field_match = False
                        for v in fields[0][index]:
                          if re.search(jinjafx_filter[index], v):
                            field_match = True
                            break

                        if not field_match:
                          include_row = False

                      else:
                        if not re.search(jinjafx_filter[index], fields[0][index]):
                          include_row = False

                      if not include_row:
                        break

                  if include_row:
                    self.__g_datarows.append(fields[0])

                  fields.pop(0)
                  row += 1

        if len(self.__g_datarows) <= 1:
          raise Exception('not enough data rows - need at least two')

    if 'jinjafx_sort' in gvars and gvars['jinjafx_sort']:
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

    if exts_dirs is not None:
      sys.path += [os.path.abspath(os.path.dirname(__file__)) + '/extensions'] + exts_dirs
    else:
      sys.path += [os.path.abspath(os.path.dirname(__file__)) + '/extensions']

    if 'jinja2_extensions' not in gvars:
      gvars.update({ 'jinja2_extensions': [ 'jinja2.ext.do', 'jinja2.ext.loopcontrols' ] })

    if importlib.util.find_spec('ext_jinjafx') is not None:
      gvars['jinja2_extensions'].insert(0, 'ext_jinjafx.plugin')

    if importlib.util.find_spec('ext_ansible_netcommon') is not None:
      gvars['jinja2_extensions'].insert(0, 'ext_ansible_netcommon.plugin')

    if importlib.util.find_spec('ext_ansible_core') is not None:
      gvars['jinja2_extensions'].insert(0, 'ext_ansible_core.plugin')

    jinja2_options = {
      'undefined': jinja2.StrictUndefined,
      'trim_blocks': True,
      'lstrip_blocks': True,
      'keep_trailing_newline': True
    }

    if 'jinja2_options' in gvars and gvars['jinja2_options']:
      for o in ('trim_blocks', 'lstrip_blocks', 'keep_trailing_newline'):
        if o in gvars['jinja2_options']:
          jinja2_options[o] = gvars['jinja2_options'][o]

    jinja2env = jinja2.sandbox.SandboxedEnvironment if sandbox else jinja2.Environment
    template_name = 'Default'

    if isinstance(template, str):
      template = { 'template.j2': template }
      template_name = 'template.j2'

    try:
      if isinstance(template, dict):
        tempdir = tempfile.mkdtemp(prefix='jinjafx_')

        for f, v in template.items():
          f = tempdir + '/' + os.path.normpath(f).strip('./')
          os.makedirs(os.path.dirname(f), exist_ok=True)

          with open(f, 'wt') as fh:
            fh.write(v)

        template = open(tempdir + '/' + template_name, 'rt')

      env = jinja2env(extensions=gvars['jinja2_extensions'], loader=jinja2.FileSystemLoader(os.path.dirname(template.name)), **jinja2_options)
      rtemplate = env.get_template(os.path.basename(template.name))

      if gvars:
        jinjafx_disable_dataloop = gvars.get('jinjafx_disable_dataloop', False)
        gyaml = env.from_string(yaml.dump(gvars, sort_keys=False)).render(gvars)
        gvars = yaml.load(gyaml, Loader=yaml.SafeLoader)

      else:
        jinjafx_disable_dataloop = False

      env.globals.update({ 'jinjafx': {
        'version': __version__,
        'jinja2_version': importlib.metadata.version('jinja2'),
        'eval': self.__jfx_eval,
        'expand': self.__jfx_expand,
        'counter': self.__jfx_counter,
        'exception': self.__jfx_exception,
        'warning': self.__jfx_warning,
        'first': self.__jfx_first,
        'last': self.__jfx_last,
        'fields': self.__jfx_fields,
        'tabulate': self.__jfx_tabulate,
        'data': self.__jfx_data,
        'setg': self.__jfx_setg,
        'getg': self.__jfx_getg,
        'now': self.__jfx_now,
        'rows': max([0, len(self.__g_datarows) - 1]),
      },
        'lookup': self.__jfx_lookup,
        'vars': self.__jfx_lookup_vars,
        'varnames': self.__jfx_lookup_varnames
      })

      self.__g_filters = env.filters

      routput = env.from_string(output)
      blanks = {}

      for row in range(1, max(2, len(self.__g_datarows))):
        rowdata = {}

        if self.__g_datarows and not jinjafx_disable_dataloop:
          for col in range(len(self.__g_datarows[0])):
            rowdata.update({ self.__g_datarows[0][col]: self.__g_datarows[row][col + 1] })

          env.globals['jinjafx'].update({ 'row': row })
          self.__g_row = row

        else:
          env.globals['jinjafx'].update({ 'row': 0 })
          self.__g_row = 0

        self.__g_vars = copy.deepcopy(gvars)
        self.__g_vars.update(rowdata)

        try:
          content = rtemplate.render(self.__g_vars)

          outputs['0:_stderr_'] = []
          if self.__g_warnings:
            outputs['0:_stderr_'] = self.__g_warnings

        except MemoryError:
          raise MemoryError('not enough memory to process template')

        except JinjaFx.TemplateException:
          raise

        except Exception as e:
          if len(e.args) >= 1 and self.__g_row:
            e.args = (e.args[0] + ' at data row ' + str(self.__g_datarows[row][0]) + ':\n - ' + str(rowdata),) + e.args[1:]
          raise

        stack = ['0:' + routput.render(rowdata)]
        start_tag = re.compile(r'<output(' + (r':\S+' if use_oformat else '') + r')?[\t ]+(.+?)[\t ]*>(?:\[(-?\d+)\])?', re.IGNORECASE)
        end_tag = re.compile(r'</output[\t ]*(\\n[\t ]*)?>', re.IGNORECASE)
        clines = content.splitlines()

        i = 0
        while i < len(clines):
          l = clines[i]

          block_begin = start_tag.search(l.strip())
          if block_begin:
            if block_begin.start() != 0:
              clines[i] = l[:block_begin.start()]
              clines.insert(i + 1, l[block_begin.start():])
              continue

            if block_begin.end() != len(l.strip()):
              clines[i] = l[:block_begin.end()]
              clines.insert(i + 1, l[block_begin.end():])
              continue

            oname = block_begin.group(2)
            if oname.startswith(('"', "'")) or oname.endswith(('"', "'")):
              if (len(oname.replace(' ', '')) > 2) and (oname[0] == oname[-1]) and not (oname[0] in oname[1:-1]):
                oname = oname[1:-1].strip()

              else:
                raise Exception('invalid output tag')

            elif len(oname.strip()) == 0:
              raise Exception('invalid output tag')

            if block_begin.group(3) is not None:
              index = int(block_begin.group(3))
            else:
              index = 0

            oformat = block_begin.group(1) if block_begin.group(1) else (':text' if use_oformat else '')
            stack.append(str(index) + ':' + oname.strip() + oformat.lower())

          else:
            block_end = end_tag.search(l.strip())
            if block_end:
              if block_end.start() != 0:
                clines[i] = l[:block_end.start()]
                clines.insert(i + 1, l[block_end.start():])
                continue

              if block_end.end() != len(l.strip()):
                clines[i] = l[:block_end.end()]
                clines.insert(i + 1, l[block_end.end():])
                continue

              if block_end.group(1):
                blanks[stack[-1]] = True

              if len(stack) > 1:
                stack.pop()
              else:
                raise Exception('unbalanced output tags')
            else:
              if stack[-1] not in outputs:
                outputs[stack[-1]] = []
              outputs[stack[-1]].append(l)

          i += 1

        if len(stack) != 1:
          raise Exception('unbalanced output tags')

        if jinjafx_disable_dataloop:
          break

      for o in sorted(outputs.keys(), key=lambda x: int(x.split(':')[0])):
        nkey = o.split(':', 1)[1]
        if nkey not in outputs:
          outputs[nkey] = []

        outputs[nkey] += outputs[o]
        if o in blanks:
          outputs[nkey] += ' '
        del outputs[o]

      outputs = {k: v for k, v in outputs.items() if (k == '_stderr_') or len(''.join(v).strip())}
      return outputs

    finally:
      if tempdir is not None:
        shutil.rmtree(tempdir)


  class TemplateError(jinja2.TemplateError):
    pass


  class TemplateException(jinja2.TemplateError):
    pass


  def __find_re_match(self, o, v, default=0):
    for rx in o:
      if rx[0].match(v):
        return rx[1]
    return default


  @jinja2.pass_context
  def __jfx_eval(self, context, value, **kwargs):
    if isinstance(value, jinja2.Undefined):
      return value

    template = context.eval_ctx.environment.from_string(value)
    return template.render(context, **kwargs)


  def __jfx_lookup(self, method, *args):
    if method == 'vars' or method == 'ansible.builtin.vars':
      if args:
        default = args[1] if len(args) > 1 else None

        if args[0] in self.__g_vars:
          return self.__g_vars[args[0]]

        elif default is not None:
          return default

        else:
          raise JinjaFx.TemplateError(f'\'lookup\' variable \'{args[0]}\' is undefined')

      else:
        raise JinjaFx.TemplateError(f'\'lookup\' method doesn\'t have enough arguments')

    elif method == 'varnames' or method == 'ansible.builtin.varnames':
      if args:
        ret = []

        for term in args:
          try:
            tre = re.compile(term)

          except Exception:
            tre = None

          if tre is None:
            raise JinjaFx.TemplateError(f'\'lookup\' method doesn\'t have a valid search regex')

          for varname in self.__g_vars:
            if tre.search(varname):
              ret.append(varname)

        return ret

      else:
        raise JinjaFx.TemplateError(f'\'lookup\' method doesn\'t have enough arguments')

    elif method == 'filters':
      if args:
        if args[0] in self.__g_filters:
          return self.__g_filters[args[0]]

        else:
          raise JinjaFx.TemplateError(f'\'lookup\' filter \'{args[0]}\' is undefined')

      else:
        raise JinjaFx.TemplateError(f'\'lookup\' method doesn\'t have enough arguments')

    else:
      raise JinjaFx.TemplateError(f'\'lookup\' method \'{method}\' is undefined')


  def __jfx_lookup_vars(self, *args):
    return self.__jfx_lookup('vars', *args)


  def __jfx_lookup_varnames(self, *args):
    return self.__jfx_lookup('varnames', *args)


  def __jfx_data_counter(self, m, orow, col, row):
    start = int(m.group(1))
    increment = int(m.group(2))
    repeat = int((m.group(3) or ':0')[1:])
    key = '_datacnt_r_' + str(orow) + '_' + str(col) + '_' + m.group()

    if self.__g_dict.get(key + '_' + str(row), True):
      n = self.__g_dict.get(key, start - increment)
      r = repeat

      if r:
        r = self.__g_dict.get(key + '_repeat', repeat + 1)
        self.__g_dict[key + '_repeat'] = r - 1 if r > 1 else repeat + 1

      if r > repeat or not r:
        self.__g_dict[key] = n + increment

      self.__g_dict[key + '_' + str(row)] = False
    return str(self.__g_dict[key])


  def __jfx_data_loop(self, m, orow, col, row):
    group = m.group(1).split('|')
    repeat = int((m.group(2) or ':0')[1:])
    key = '_dataloop_r_' + str(orow) + '_' + str(col) + '_' + m.group()

    if self.__g_dict.get(key + '_' + str(row), True):
      n = self.__g_dict.get(key, -1)
      r = repeat

      if r:
        r = self.__g_dict.get(key + '_repeat', repeat + 1)
        self.__g_dict[key + '_repeat'] = r - 1 if r > 1 else repeat + 1

      if r > repeat or not r:
        self.__g_dict[key] = n + 1

      self.__g_dict[key + '_' + str(row)] = False
    return str(group[self.__g_dict[key] % len(group)])


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
            self.__g_xlimit -= 1

            if not self.__g_xlimit:
              raise OverflowError("jinjafx.expand() - expansion limit reached")

          pofa.pop(i)
          groups.pop(i)

        else:
          i += 1

      i = 0
      while i < len(pofa):
        m = re.search(r'(?<!\\)\{[ \t]*([0-9]+-[0-9]+):([0-9]+)(:[0-9]+)?[ \t]*(?<!\\)\}', pofa[i])
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
          repeat = int((m.group(3) or ':0')[1:])

          for n in range(start, end, step):
            for r in range(repeat + 1):
              pofa.append(pofa[i][:m.start(1) - 1] + str(n) + pofa[i][m.end(m.lastindex) + 1:])
              self.__g_xlimit -= 1

              if not self.__g_xlimit:
                raise OverflowError("jinjafx.expand() - expansion limit reached")

              ngroups = list(groups[i])
              if group > 0 and group < len(ngroups):
                ngroups[group] = ngroups[group].replace(m.group(), str(n), 1)

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

            for x in re.findall(r'([A-Z0-9](-[A-Z0-9])?)', m.group(1), re.IGNORECASE):
              if x[1] != '':
                ee = x[0].split('-')

                start = ord(ee[0])
                end = ord(ee[1]) + 1 if ord(ee[1]) >= ord(ee[0]) else ord(ee[1]) - 1
                step = 1 if end > start else -1

                for j in range(start, end, step):
                  clist.append(chr(j))

              else:
                clist.append(x[0])

            for c in clist:
              pofa.append(pofa[i][:m.start(1) - 1] + c + pofa[i][m.end(1) + 1:])
              ngroups = list(groups[i])
              self.__g_xlimit -= 1

              if not self.__g_xlimit:
                raise OverflowError("jinjafx.expand() - expansion limit reached")

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

    if not self.__g_row:
      return True

    if fields is not None:
      for f in fields:
        if ':' in f:
          try:
            f, s = f.split(':', 1)
            s = [s[0], int(s[1:])]

          except Exception:
            raise JinjaFx.TemplateError(f'invalid split operator for field "{f}" passed to jinjafx.{forl}()')

        else:
          s = ['_this_should_never_match_anything_', 0]

        if f in self.__g_datarows[0]:
          fpos.append([self.__g_datarows[0].index(f) + 1, s])

        else:
          raise JinjaFx.TemplateError(f'invalid field "{f}" passed to jinjafx.{forl}()')

    elif forl == 'first':
      return True if self.__g_row == 1 else False

    else:
      return True if self.__g_row == (len(self.__g_datarows) - 1) else False

    try:
      tv = ':'.join([str(self.__g_datarows[self.__g_row][i[0]]).split(i[1][0])[i[1][1]] for i in fpos])

    except IndexError:
      raise JinjaFx.TemplateError(f'invalid split operator for field "{f}" passed to jinjafx.{forl}()')

    if forl == 'first':
      rows = range(1, len(self.__g_datarows))
    else:
      rows = range(len(self.__g_datarows) - 1, 0, -1)

    for r in rows:
      fmatch = True

      for f in ffilter:
        if f in self.__g_datarows[0]:
          try:
            if not re.match(ffilter[f], str(self.__g_datarows[r][self.__g_datarows[0].index(f) + 1])):
              fmatch = False
              break
          except Exception:
            raise JinjaFx.TemplateError(f'invalid filter regex "{ffilter[f]}" for field "{f}" passed to jinjafx.{forl}()')
        else:
          raise JinjaFx.TemplateError(f'invalid filter field "{f}" passed to jinjafx.{forl}()')

      if fmatch:
        if tv == ':'.join([str(self.__g_datarows[r][i[0]]).split(i[1][0])[i[1][1]] for i in fpos]):
          return True if self.__g_row == r else False

    return False


  def __jfx_exception(self, message):
    raise JinjaFx.TemplateException(message)


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
        raise JinjaFx.TemplateError(f'invalid field "{field}" passed to jinjafx.fields()')
    else:
      return None

    field_values = []

    for r in range(1, len(self.__g_datarows)):
      fmatch = True
      field_value = self.__g_datarows[r][fpos]

      if field_value not in field_values and str(field_value).strip():
        for f in ffilter:
          if f in self.__g_datarows[0]:
            try:
              if not re.match(ffilter[f], str(self.__g_datarows[r][self.__g_datarows[0].index(f) + 1])):
                fmatch = False
                break
            except Exception:
              raise JinjaFx.TemplateError(f'invalid filter regex "{ffilter[f]}" for field "{f}" passed to jinjafx.fields()')
          else:
            raise JinjaFx.TemplateError(f'invalid filter field "{f}" passed to jinjafx.fields()')

        if fmatch:
          field_values.append(field_value)

    return field_values


  def __jfx_tabulate(self, datarows=None, *, cols=None, style='default'):
    colwidth = []
    colmap = []
    offset = 0
    o = ''

    ansi = re.compile(r'\033\[(?:[01];[0-9][0-9]|0)m')

    style = style.lower()
    if style not in ('default', 'github', 'simple'):
      raise JinjaFx.TemplateError(f'invalid style "{style}" passed to jinjafx.tabulate()')

    if datarows is None:
      datarows = self.__g_datarows
      offset = 1

    if len(datarows) > 1:
      if not cols:
        colmap = list(range(len(datarows[0])))

      else:
        for c in cols:
          try:
            colmap.append(datarows[0].index(c))

          except Exception:
            raise JinjaFx.TemplateError(f'invalid column "{c}" passed to jinjafx.tabulate()')

      colalign = [["<", ":", " "]] * len(datarows[0])
      coltype = [0] * len(datarows[0])

      for c in range(len(datarows[0])):
        colwidth.append(len(datarows[0][c]))

      for r in range(1, len(datarows)):
        for c in range(offset, len(datarows[r])):
          coltype[c - offset] |= (1<<(isinstance(datarows[r][c], (int, float))))
          lendr = len(ansi.sub('', str(datarows[r][c])))
          if colwidth[c - offset] < lendr:
            colwidth[c - offset] = lendr

      for c, t in enumerate(coltype):
        if t == 2:
          colalign[c] = [">", " ", ":"]

      if style == 'simple':
        o = "  ".join([f"{datarows[0][c]:{colalign[c][0]}{colwidth[c]}}" for c in colmap]) + "\n"
        o += "  ".join([f"{'-' * colwidth[c]}" for c in colmap]) + "\n"
      else:
        o = "| " + " | ".join([f"{datarows[0][c]:{colalign[c][0]}{colwidth[c]}}" for c in colmap]) + " |\n"
        o += "|" + "|".join([f"{colalign[c][1] if style == 'github' else ' '}{'-' * colwidth[c]}{colalign[c][2] if style == 'github' else ' '}" for c in colmap]) + "|\n"

      for r in range(1, len(datarows)):
        delta = [len(str(datarows[r][c + offset])) - len(ansi.sub('', str(datarows[r][c + offset]))) for c in colmap]

        if style == "simple":
          o += "  ".join([f"{datarows[r][c + offset]:{colalign[c][0]}{colwidth[c] + delta[c]}}" for c in colmap]) + "\n"
        else:
          o += "| " + " | ".join([f"{datarows[r][c + offset]:{colalign[c][0]}{colwidth[c] + delta[c]}}" for c in colmap]) + " |\n"

    return o.strip()


  def __jfx_data(self, row, col=None):
    if self.__g_datarows:
      if isinstance(col, str):
        if col in self.__g_datarows[0]:
          col = self.__g_datarows[0].index(col)
        else:
          raise JinjaFx.TemplateError(f'invalid column "{col}" passed to jinjafx.data()')

      if row and isinstance(col, int):
        col += 1

      if row is not None and col is not None:
        if len(self.__g_datarows) > row:
          if len(self.__g_datarows[row]) > col:
            return self.__g_datarows[row][col]

          else:
            raise JinjaFx.TemplateError(f'invalid column "{col}" passed to jinjafx.data()')

        else:
          raise JinjaFx.TemplateError(f'invalid row "{row}" passed to jinjafx.data()')

      elif row is not None:
        if len(self.__g_datarows) > row:
          return self.__g_datarows[row][1 if row else 0:]

        else:
          raise JinjaFx.TemplateError(f'invalid row "{row}" passed to jinjafx.data()')

    return None


  def __jfx_counter(self, key=None, increment=1, start=1, row=None):
    if row is None:
      row = self.__g_row

    if key is None:
      key = '_cnt_r_' + str(row)

    elif str(key).endswith('.') and self.__g_hcounter.match(key):
      nkey = '_cnt_hk' + str(row)
      kelements = key[:-1].lower().split('.')

      for i, v in enumerate(kelements[:-1]):
        nkey += '_' + v

        if nkey in self.__g_dict:
          nkey = '_'.join(nkey.split('_')[:-1]) + '_' + str(self.__g_dict[nkey])

        else:
          return None

      nkey += '_' + kelements[-1]
      n = self.__g_dict.get(nkey, int(start) - int(increment))
      self.__g_dict[nkey] = int(n) + int(increment)
      rv = nkey.split('_')[3:-1] + [str(self.__g_dict[nkey])]
      return '.'.join(rv) + '.'

    else:
      key = '_cnt_k_' + str(key).lower()

    n = self.__g_dict.get(key, int(start) - int(increment))
    self.__g_dict[key] = int(n) + int(increment)
    return int(self.__g_dict[key])


  def __jfx_setg(self, key, value):
    self.__g_dict['_val_' + str(key)] = value
    return ''


  def __jfx_getg(self, key, default=None):
    return self.__g_dict.get('_val_' + str(key), default)


  def __jfx_now(self, fmt=None, tz='UTC'):
    if fmt is not None:
      return datetime.datetime.now(tz=zoneinfo.ZoneInfo(tz)).strftime(fmt)

    else:
      return str(datetime.datetime.now(tz=zoneinfo.ZoneInfo(tz)))


class AnsibleVault():
  def __derive_key(self, b_password, b_salt=None):
    if b_salt is None:
      b_salt = os.urandom(32)

    b_key = PBKDF2HMAC(hashes.SHA256(), 80, b_salt, 10000).derive(b_password)
    return [b_salt, b_key]

  def encrypt(self, b_string, password):
    if b_string.lstrip().startswith(b'$ANSIBLE_VAULT;'):
      raise Exception('data is already encrypted with ansible vault')

    b_salt, b_derivedkey = self.__derive_key(password.encode('utf-8'))

    p = PKCS7(128).padder()
    e = Cipher(AES(b_derivedkey[:32]), CTR(b_derivedkey[64:80])).encryptor()
    b_ciphertext = e.update(p.update(b_string) + p.finalize()) + e.finalize()

    hmac = HMAC(b_derivedkey[32:64], hashes.SHA256())
    hmac.update(b_ciphertext)
    b_hmac = hmac.finalize()

    vtext = '\n'.join([b_salt.hex(), b_hmac.hex(), b_ciphertext.hex()]).encode('utf-8').hex()
    return '$ANSIBLE_VAULT;1.1;AES256\n'  + '\n'.join([vtext[i:i + 80] for i in range(0, len(vtext), 80)]) + '\n'

  def decrypt(self, b_string, password, return_none=False):
    slines = b_string.strip().splitlines()
    hdr = list(map(bytes.strip, slines[0].split(b';')))

    if hdr[0] == b'$ANSIBLE_VAULT' and len(slines) > 1:
      if hdr[1] == b'1.1' or hdr[1] == b'1.2':
        if hdr[2] == b'AES256':
          vaulttext = bytes.fromhex(b''.join(slines[1:]).decode('utf-8'))
          b_salt, b_hmac, b_ciphertext = vaulttext.split(b'\n', 2)
          b_hmac = bytes.fromhex(b_hmac.decode('utf-8'))
          b_ciphertext = bytes.fromhex(b_ciphertext.decode('utf-8'))
          b_derivedkey = self.__derive_key(password.encode('utf-8'), bytes.fromhex(b_salt.decode('utf-8')))[1]

          hmac = HMAC(b_derivedkey[32:64], hashes.SHA256())
          hmac.update(b_ciphertext)

          try:
            hmac.verify(b_hmac)

          except InvalidSignature:
            if return_none:
              return None

            else:
              raise Exception('invalid ansible vault password')

          u = PKCS7(128).unpadder()
          d = Cipher(AES(b_derivedkey[:32]), CTR(b_derivedkey[64:80])).decryptor()
          b_plaintext = u.update(d.update(b_ciphertext) + d.finalize()) + u.finalize()
          return b_plaintext

        else:
          raise Exception('unknown ansible vault cipher')

      else:
        raise Exception('unknown ansible vault version')

    else:
      raise Exception('data isn\'t ansible vault encrypted')


class Vaulty():
  def __init__(self):
    self.__prefix = '$VAULTY;'
    self.__kcache = {}

  def __derive_key(self, password, salt=None):
    if (ckey := (password, salt)) in self.__kcache:
      e = self.__kcache[ckey]
      self.__kcache[ckey] = e[0], e[1], e[2] + 1
      return self.__kcache[ckey]

    if salt is None:
      salt = os.urandom(16)

    key = Scrypt(salt, 32, 2**16, 8, 1).derive(password.encode('utf-8'))
    self.__kcache[ckey] = [salt, key, 0]
    return [salt, key, 0]

  def encrypt(self, plaintext, password, cols=None):
    version = b'\x01'
    salt, key, uc = self.__derive_key(password)
    nonce = os.urandom(12)[:-4] + uc.to_bytes(4, 'big')
    ciphertext = ChaCha20Poly1305(key).encrypt(nonce, plaintext.encode('utf-8'), None)

    r = self.__prefix + base64.b64encode(version + salt + nonce + ciphertext).decode('utf-8')

    if cols is not None:
      r = '\n'.join([r[i:i + cols] for i in range(0, len(r), cols)])

    return r

  def decrypt(self, ciphertext, password):
    if ciphertext.lstrip().startswith(self.__prefix):
      try:
        nciphertext = base64.b64decode(ciphertext.strip()[len(self.__prefix):])

        if len(nciphertext) > 29 and nciphertext.startswith(b'\x01'):
          key = self.__derive_key(password, nciphertext[1:17])[1]
          return ChaCha20Poly1305(key).decrypt(nciphertext[17:29], nciphertext[29:], None).decode('utf-8')

      except Exception:
        pass

      raise JinjaFx.TemplateError('invalid vaulty password or ciphertext malformed')

    raise JinjaFx.TemplateError('data not encrypted with vaulty')


if __name__ == '__main__':
  main()
