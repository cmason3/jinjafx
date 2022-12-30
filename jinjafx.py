#!/usr/bin/env python3

# JinjaFx - Jinja2 Templating Tool
# Copyright (c) 2020-2023 Chris Mason <chris@netnix.org>
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

import sys, os, io, importlib.util, argparse, re, getpass, datetime, traceback
import jinja2, jinja2.sandbox, yaml, pytz

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.hmac import HMAC
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.modes import CTR
from cryptography.exceptions import InvalidSignature

__version__ = '1.15.0'

def main():
  exc_source = None

  try:
    if not any(x in ['-q', '-encrypt', '-decrypt'] for x in sys.argv):
      print(f'JinjaFx v{__version__} - Jinja2 Templating Tool')
      print('Copyright (c) 2020-2023 Chris Mason <chris@netnix.org>\n')

    prog = os.path.basename(sys.argv[0])
    jinjafx_usage = '-t <template.j2> [-d <data.csv>] [-g <vars.yml>]\n'
    jinjafx_usage += (' ' * (len(prog) + 3)) + '-dt <dt.yml> [-ds <dataset>] [-g <vars.yml>]\n'
    jinjafx_usage += (' ' * (len(prog) + 3)) + '-encrypt/-decrypt [file1] [file2] [...]\n'
    jinjafx_usage += '''

    -t <template.j2>           - specify a Jinja2 template
    -d <data.csv>              - specify row/column based data (comma or tab separated)
    -dt <dt.yml>               - specify a JinjaFx DataTemplate (combines template, data and vars)
    -ds <dataset>              - specify a regex to match a DataSet within a JinjaFx DataTemplate
    -g <vars.yml> [-g ...]     - specify global variables in yaml (supports Ansible Vault)
    -var <x=value> [-var ...]  - specify global variables on the command line (overrides existing)
    -ed <exts dir> [-ed ...]   - specify where to look for extensions (default is "." and "~/.jinjafx")
    -o <output file>           - specify the output file (supports Jinja2 variables) (default is stdout)
    -od <output dir>           - set output dir for output files with a relative path (default is ".")
    -encrypt [file] [...]      - encrypt files or stdin (if file omitted) using Ansible Vault
    -decrypt [file] [...]      - decrypt files or stdin (if file omitted) using Ansible Vault
    -m                         - merge duplicate global variables (dicts and lists) instead of replacing
    -q                         - quiet mode - don't output version or usage information

Environment Variables:
  ANSIBLE_VAULT_PASSWORD       - specify an Ansible Vault password
  ANSIBLE_VAULT_PASSWORD_FILE  - specify an Ansible Vault password file'''

    parser = __ArgumentParser(add_help=False, usage=f'{prog} {jinjafx_usage}')
    group_ex = parser.add_mutually_exclusive_group(required=True)
    group_ex.add_argument('-t', type=argparse.FileType('r'))
    group_ex.add_argument('-dt', type=argparse.FileType('r'))
    group_ex.add_argument('-encrypt', type=str, nargs='*')
    group_ex.add_argument('-decrypt', type=str, nargs='*')
    parser.add_argument('-d', type=argparse.FileType('r'))
    parser.add_argument('-ds', type=str)
    parser.add_argument('-g', type=argparse.FileType('r'), action='append')
    parser.add_argument('-var', type=str, action='append')
    parser.add_argument('-ed', type=str, action='append', default=[])
    parser.add_argument('-o', type=str)
    parser.add_argument('-od', type=str)
    parser.add_argument('-m', action='store_true')
    parser.add_argument('-q', action='store_true')
    args = parser.parse_args()

    if args.dt is not None and args.d is not None:
      parser.error('argument -d: not allowed with argument -dt')

    if args.dt is None and args.ds is not None:
      parser.error('argument -ds: only allowed with argument -dt')

    if args.m and args.g is None:
      parser.error('argument -m: only allowed with argument -g')

    if args.od is not None and not os.access(args.od, os.W_OK):
      parser.error('argument -od: unable to write to output directory')

    gvars = {}
    data = None
    vpw = [ None ]

    if args.encrypt is not None:
      if not args.encrypt:
        b_string = sys.stdin.buffer.read().strip()
        if len(b_string.splitlines()) > 1:
          raise Exception('multiline stings not permitted')

        __get_vault_credentials(vpw, True)
        vtext = Vault().encrypt(b_string, vpw[0])
        print('!vault |\n' + re.sub(r'^', ' ' * 10, vtext, flags=re.MULTILINE))

      else:
        __get_vault_credentials(vpw, True)

        for f in args.encrypt:
          if os.path.isfile(f):
            print(f'Encrypting {f}... ', flush=True, end='')

            try:
              with open(f, 'rb') as fh:
                vtext = Vault().encrypt(fh.read(), vpw[0])

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
        print(Vault().decrypt(b_vtext, vpw[0]).decode('utf-8'))

      else:
        __get_vault_credentials(vpw)

        for f in args.decrypt:
          if os.path.isfile(f):
            print(f'Decrypting {f}... ', flush=True, end='')

            try:
              with open(f, 'rb') as fh:
                plaintext = Vault().decrypt(fh.read(), vpw[0])

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
      yaml.add_constructor('!vault', lambda x, y: __decrypt_vault(vpw, y.value).decode('utf-8'), yaml.SafeLoader)

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
  
          if gv:
            gyaml = __decrypt_vault(vpw, gv)
            if gyaml:
              try:
                gvars.update(yaml.load(gyaml, Loader=yaml.SafeLoader))

              except Exception as e:
                exc_source = 'dt:global'
                raise

          if 'vars' in dt:
            gyaml = __decrypt_vault(vpw, dt['vars'])
            if gyaml:
              try:
                gvars.update(yaml.load(gyaml, Loader=yaml.SafeLoader))

              except Exception as e:
                exc_source = 'dt:vars'
                raise
  
      elif args.d is not None:
        with open(args.d.name, 'rt') as f:
          data = f.read()
  
      if args.g is not None:
        for g in args.g:
          with open(g.name, 'rt') as f:
            gyaml = __decrypt_vault(vpw, f.read())
            try:
              if args.m == True:
                __merge(gvars, yaml.load(gyaml, Loader=yaml.SafeLoader))
              else:
                gvars.update(yaml.load(gyaml, Loader=yaml.SafeLoader))

            except Exception as e:
              exc_source = g.name
              raise

      if args.var is not None:
        for v in args.var:
          x, value = list(map(str.strip, v.split('=')))
          gvars[x] = value
  
      if args.o is None:
        args.o = '_stdout_'
  
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
  
      args.ed = [os.getcwd(), os.getenv('HOME') + '/.jinjafx'] + args.ed
      outputs = JinjaFx().jinjafx(args.t, data, gvars, args.o, args.ed)
      ocount = 0
  
      if args.od is not None:
        os.chdir(args.od)
  
      if outputs['_stderr_']:
        print('Warnings:', file=sys.stderr)
        for w in outputs['_stderr_']:
          print(f' - {w}', file=sys.stderr)
  
        print('', file=sys.stderr)
  
      for o in sorted(outputs.items(), key=lambda x: (x[0] == '_stdout_')):
        oname = o[0].rsplit(':', 1)[0]

        if oname != '_stderr_':
          output = '\n'.join(o[1]) + '\n'
          if output.strip():
            if oname == '_stdout_':
              if ocount:
                print('\n-\n')
              print(output)
    
            else:
              ofile = re.sub(r'_+', '_', re.sub(r'[^A-Za-z0-9_. -/]', '_', os.path.normpath(oname)))
    
              if os.path.dirname(ofile) != '':
                if not os.path.isdir(os.path.dirname(ofile)):
                  os.makedirs(os.path.dirname(ofile))
    
              with open(ofile, 'wt') as f:
                f.write(output)
    
              print(__format_bytes(len(output)) + ' > ' + ofile)
    
            ocount += 1
  
      if ocount:
        if '_stdout_' not in outputs:
          print()
  
      else:
        raise Exception('nothing to output')

  except KeyboardInterrupt:
    sys.exit(-1)

  except jinja2.TemplateError as e:
    m = re.search(r'File "(.+)", line ([0-9]+),', traceback.format_exc(-1), re.IGNORECASE | re.MULTILINE)
    print(f'error[{m.group(1)}:{m.group(2)}]: {type(e).__name__}: {e}', file=sys.stderr)
    sys.exit(-2)

  except Exception as e:
    print(f'error[{exc_source or sys.exc_info()[2].tb_lineno}]: {type(e).__name__}: {e}', file=sys.stderr)
    sys.exit(-2)


def __decrypt_vault(vpw, string):
  if string.lstrip().startswith('$ANSIBLE_VAULT;'):
    __get_vault_credentials(vpw)
    return Vault().decrypt(string.encode('utf-8'), vpw[0])
  return string


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
  def jinjafx(self, template, data, gvars, output, exts_dirs=[], sandbox=False):
    self.__g_datarows = []
    self.__g_dict = {}
    self.__g_row = 0 
    self.__g_vars = {}
    self.__g_warnings = []
    self.__g_xlimit = 5000 if sandbox else 0

    outputs = {}
    delim = None
    rowkey = 1
    int_indices = []
    float_indices = []

    if not isinstance(template, (str, io.IOBase)):
      raise TypeError('template must be of type str or type FileType')

    if data is not None:
      if not isinstance(data, str):
        raise TypeError('data must be of type str')

      if data.strip():
        jinjafx_filter = {}
        jinjafx_adjust_headers = str(gvars.get('jinjafx_adjust_headers', 'no')).strip().lower()
        recm = re.compile(r'(?<!\\){[ \t]*([0-9]+):([0-9]+)[ \t]*(?<!\\)}')

        for l in data.splitlines():
          if l.strip() and not re.match(r'^[ \t]*#', l):
            if not self.__g_datarows:
              if l.count(',') > l.count('\t'):
                delim = r'[ \t]*,[ \t]*'
                schars = ' \t'
              else:
                delim = r' *\t *'
                schars = ' '
  
              fields = re.split(delim, re.sub('(?:' + delim + ')+$', '', l.strip(schars)))
              fields = [re.sub(r'^(["\'])(.*)\1$', r'\2', f) for f in fields]

              for i, v in enumerate(fields):
                if v.lower().endswith(':int'):
                  int_indices.append(i + 1)
                  fields[i] = v[:-4]
                elif v.lower().endswith(':float'):
                  float_indices.append(i + 1)
                  fields[i] = v[:-6]
  
                if jinjafx_adjust_headers == 'yes':
                  fields[i] = re.sub(r'[^A-Z0-9_]', '', v, flags=re.UNICODE | re.IGNORECASE)
                elif jinjafx_adjust_headers == 'upper':
                  fields[i] = re.sub(r'[^A-Z0-9_]', '', v.upper(), flags=re.UNICODE | re.IGNORECASE)
                elif jinjafx_adjust_headers == 'lower':
                  fields[i] = re.sub(r'[^A-Z0-9_]', '', v.lower(), flags=re.UNICODE | re.IGNORECASE)
                elif jinjafx_adjust_headers != 'no':
                  raise Exception('invalid value specified for \'jinjafx_adjust_headers\' - must be \'yes\', \'no\', \'upper\' or \'lower\'')

                if fields[i] == '':
                  raise Exception(f'empty header field detected at column position {i + 1}')

                elif not re.match(r'^[A-Z_][A-Z0-9_]*$', fields[i], re.IGNORECASE):
                  raise Exception(f'header field at column position {i + 1} contains invalid characters')
  
              if len(set(fields)) != len(fields):
                raise Exception('duplicate header field detected in data')

              else:
                self.__g_datarows.append(fields)
  
              if 'jinjafx_filter' in gvars and gvars['jinjafx_filter']:
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
                        raise Exception(f'parenthesis in row {rowkey} at "{m.group(0)}" should be escaped or removed')
  
                      else:
                        f = f[:m.start() + delta] + '\\(' + m.group(1) + '\\)' + f[m.end() + delta:]
                        delta += 2
  
                  gcount += 1
  
                fields.append(re.sub(r'^(["\'])(.*)\1$', r'\2', f))
  
              n = len(self.__g_datarows[0])
              fields = [list(map(self.__jfx_expand, fields[:n] + [''] * (n - len(fields)), [True] * n))]

              row = 0
              while fields:
                if not isinstance(fields[0][0], int):
                  fields[0].insert(0, rowkey)
                  rowkey += 1
  
                if any(isinstance(col[0], list) for col in fields[0][1:]):
                  for col in range(1, len(fields[0])):
                    if isinstance(fields[0][col][0], list):
                      for i, v in enumerate(fields[0][col][0]):
                        nrow = [e[:] if isinstance(e, list) else e for e in fields[0]]
                        nrow[col] = [v, fields[0][col][1][i]]
                        fields.append(nrow)
  
                      fields.pop(0)
                      break
  
                else:
                  groups = []
  
                  for col in range(1, len(fields[0])):
                    fields[0][col][0] = recm.sub(lambda m: self.__jfx_data_counter(m, fields[0][0], col, row), fields[0][col][0])
  
                    for g in range(len(fields[0][col][1])):
                      fields[0][col][1][g] = recm.sub(lambda m: self.__jfx_data_counter(m, fields[0][0], col, row), fields[0][col][1][g])
  
                    groups.append(fields[0][col][1])
 
                  groups = dict(enumerate(sum(groups, ['\\0'])))
  
                  for col in range(1, len(fields[0])):
                    fields[0][col] = re.sub(r'\\([0-9]+)', lambda m: groups.get(int(m.group(1)), '\\' + m.group(1)), fields[0][col][0])
  
                    delta = 0
                    for m in re.finditer(r'([0-9]+)(?<!\\)\%([0-9]+)', fields[0][col]):
                      pvalue = str(int(m.group(1))).zfill(int(m.group(2)))
                      fields[0][col] = fields[0][col][:m.start() + delta] + pvalue + fields[0][col][m.end() + delta:]
  
                      if len(m.group(0)) > len(pvalue):
                        delta -= len(m.group(0)) - len(pvalue)
                      else:
                        delta += len(pvalue) - len(m.group(0))
  
                    fields[0][col] = re.sub(r'\\([}{%])', r'\1', fields[0][col])
  
                    if col in int_indices:
                      fields[0][col] = int(fields[0][col])

                    elif col in float_indices:
                      fields[0][col] = float(fields[0][col])

                  include_row = True
                  if jinjafx_filter:
                    for index in jinjafx_filter:
                      if not re.search(jinjafx_filter[index], fields[0][index]):
                        include_row = False
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

    sys.path += [os.path.abspath(os.path.dirname(__file__)) + '/extensions'] + exts_dirs

    if 'jinja2_extensions' not in gvars:
      gvars.update({ 'jinja2_extensions': [] })

    if importlib.util.find_spec('ext_jinjafx') is not None:
      gvars['jinja2_extensions'].insert(0, 'ext_jinjafx.plugin')

    if importlib.util.find_spec('ext_ansible_ipaddr') is not None:
      gvars['jinja2_extensions'].insert(0, 'ext_ansible_ipaddr.plugin')

    if importlib.util.find_spec('ext_ansible_core') is not None:
      gvars['jinja2_extensions'].insert(0, 'ext_ansible_core.plugin')

    jinja2_options = {
      'undefined': jinja2.StrictUndefined,
      'trim_blocks': True,
      'lstrip_blocks': True,
      'keep_trailing_newline': True
    }

    jinja2env = jinja2.sandbox.SandboxedEnvironment if sandbox else jinja2.Environment

    if isinstance(template, str):
      env = jinja2env(extensions=gvars['jinja2_extensions'], **jinja2_options)
      template = env.from_string(template)

    else:
      env = jinja2env(extensions=gvars['jinja2_extensions'], loader=jinja2.FileSystemLoader(os.path.dirname(template.name)), **jinja2_options)
      template = env.get_template(os.path.basename(template.name))

    if gvars:
      jinjafx_render_vars = str(gvars.get('jinjafx_render_vars', 'yes')).strip().lower()

      if jinjafx_render_vars != 'no':
        gyaml = env.from_string(yaml.dump(gvars, sort_keys=False)).render(gvars)
        gvars = yaml.load(gyaml, Loader=yaml.SafeLoader)

      env.globals.update(gvars)

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
      'data': self.__jfx_data,
      'setg': self.__jfx_setg,
      'getg': self.__jfx_getg,
      'now': self.__jfx_now,
      'rows': max([0, len(self.__g_datarows) - 1]),
    },
      'lookup': self.__jfx_lookup
    })

    output = env.from_string(output)

    for row in range(1, max(2, len(self.__g_datarows))):
      rowdata = {}

      if self.__g_datarows:
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
        if self.__g_warnings:
          outputs['0:_stderr_'] = self.__g_warnings

      except MemoryError:
        raise MemoryError('not enough memory to process template')

      except Exception as e:
        if e.args[0].startswith('[jfx_exception] '):
          e.args = (e.args[0][16:],)
        else:
          if len(e.args) >= 1 and self.__g_row:
            e.args = (e.args[0] + ' at data row ' + str(self.__g_datarows[row][0]) + ':\n - ' + str(rowdata),) + e.args[1:]
        raise

      stack = ['0:' + output.render(rowdata)]
      start_tag = re.compile(r'<output(:\S+)?[\t ]+["\']*(.+?)["\']*[\t ]*>(?:\[(-?\d+)\])?', re.IGNORECASE)
      end_tag = re.compile(r'</output[\t ]*>', re.IGNORECASE)
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

          if block_begin.group(3) is not None:
            index = int(block_begin.group(3))
          else:
            index = 0

          oformat = block_begin.group(1) if block_begin.group(1) is not None else ':text'
          stack.append(str(index) + ':' + block_begin.group(2).strip() + oformat.lower())

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

    for o in sorted(outputs.keys(), key=lambda x: int(x.split(':')[0])):
      nkey = o.split(':', 1)[1]

      if nkey not in outputs:
        outputs[nkey] = []
          
      outputs[nkey] += outputs[o]
      del outputs[o]

    return outputs


  def __find_re_match(self, o, v, default=0):
    for rx in o:
      if rx[0].match(v):
        return rx[1]

    return default


  def __jfx_lookup(self, method, variable, default=None):
    if method == 'vars' or method == 'ansible.builtin.vars':
      if variable in self.__g_vars:
        return self.__g_vars[variable]

      elif default is not None:
        return default
  
      else:
        raise jinja2.exceptions.UndefinedError(f'\'lookup\' variable \'{variable}\' is undefined')

    else:
      raise jinja2.exceptions.UndefinedError(f'\'lookup\' with method \'{method}\' is undefined')


  def __jfx_data_counter(self, m, orow, col, row):
    start = m.group(1)
    increment = m.group(2)
    key = '_datacnt_r_' + str(orow) + '_' + str(col) + '_' + m.group()

    if self.__g_dict.get(key + '_' + str(row), True):
      n = self.__g_dict.get(key, int(start) - int(increment))
      self.__g_dict[key] = n + int(increment)
      self.__g_dict[key + '_' + str(row)] = False
    return str(self.__g_dict[key])


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
        m = re.search(r'(?<!\\)\{[ \t]*([0-9]+-[0-9]+):([0-9]+)[ \t]*(?<!\\)\}', pofa[i])
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
            pofa.append(pofa[i][:m.start(1) - 1] + str(n) + pofa[i][m.end(m.lastindex) + 1:])
            self.__g_xlimit -= 1

            if not self.__g_xlimit:
              raise OverflowError("jinjafx.expand() - expansion limit reached")

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
        if f in self.__g_datarows[0]:
          fpos.append(self.__g_datarows[0].index(f) + 1)
        else:
          raise Exception(f'invalid field "{f}" passed to jinjafx.{forl}()')
    elif forl == 'first':
      return True if self.__g_row == 1 else False
    else:
      return True if self.__g_row == (len(self.__g_datarows) - 1) else False

    tv = ':'.join([str(self.__g_datarows[self.__g_row][i]) for i in fpos])

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
            raise Exception(f'invalid filter regex "{ffilter[f]}" for field "{f}" passed to jinjafx.{forl}()')
        else:
          raise Exception(f'invalid filter field "{f}" passed to jinjafx.{forl}()')

      if fmatch:
        if tv == ':'.join([str(self.__g_datarows[r][i]) for i in fpos]):
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
        raise Exception(f'invalid field "{field}" passed to jinjafx.fields()')
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
              raise Exception(f'invalid filter regex "{ffilter[f]}" for field "{f}" passed to jinjafx.fields()')
          else:
            raise Exception(f'invalid filter field "{f}" passed to jinjafx.fields()')

        if fmatch:
          field_values.append(field_value)

    return field_values

 
  def __jfx_data(self, row, col=None):
    if self.__g_datarows:
      if isinstance(col, str):
        if col in self.__g_datarows[0]:
          col = self.__g_datarows[0].index(col) 
        else:
          raise Exception(f'invalid column "{col}" passed to jinjafx.data()')

      if row and isinstance(col, int):
        col += 1

      if row is not None and col is not None:
        return self.__g_datarows[row][col]

      elif row is not None:
        return self.__g_datarows[row][1 if row else 0:]


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


  def __jfx_now(self, fmt=None, tz='UTC'):
    tz = pytz.timezone(tz)

    if fmt is not None:
      return datetime.datetime.now(tz=tz).strftime(fmt)

    else:
      return str(datetime.datetime.now(tz=tz))


class Vault():
  def __derive_key(self, b_password, b_salt=None):
    if b_salt is None:
      b_salt = os.urandom(32)

    b_key = PBKDF2HMAC(hashes.SHA256(), 80, b_salt, 10000).derive(b_password)
    return b_salt, b_key

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

  def decrypt(self, b_string, password):
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


if __name__ == '__main__':
  main()
