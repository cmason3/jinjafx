#!/usr/bin/env python

# JinjaFx Server - Jinja Templating Tool
# Copyright (c) 2020-2021 Chris Mason <chris@jinjafx.org>
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

from __future__ import print_function
from http.server import HTTPServer, BaseHTTPRequestHandler
import jinjafx, os, io, sys, socket, threading, yaml, json, base64, time, datetime, re, argparse, zipfile, hashlib, traceback, glob

try:
  from ansible.constants import DEFAULT_VAULT_ID_MATCH
  from ansible.parsing.vault import VaultLib
  from ansible.parsing.vault import VaultSecret
except Exception:
  pass

lock = threading.RLock()
repository = None

class JinjaFxServer(HTTPServer):
  def handle_error(self, request, client_address):
    pass


class JinjaFxRequest(BaseHTTPRequestHandler):
  server_version = 'JinjaFx/' + jinjafx.__version__
  protocol_version = 'HTTP/1.1'

  def log_message(self, format, *args):
    path = self.path if hasattr(self, 'path') else ''

    if not isinstance(args[0], int) and path != '/ping':
      ansi = '32' if args[1] == '200' else '31'
      src = str(self.client_address[0])
      ctype = ''

      if hasattr(self, 'headers'):
        if 'X-Forwarded-For' in self.headers:
          src = self.headers['X-Forwarded-For']

        if 'Content-Type' in self.headers:
          ctype = ' (' + self.headers['Content-Type'] + ')'

      if str(args[1]) == 'ERR':
        log('[' + src + '] [\033[1;' + ansi + 'm' + str(args[1]) + '\033[0m] ' + str(args[2]))
          
      elif self.command == 'POST':
        log('[' + src + '] [\033[1;' + ansi + 'm' + str(args[1]) + '\033[0m] \033[1;33m' + self.command + '\033[0m ' + path + ctype)

      elif self.command != None:
        log('[' + src + '] [\033[1;' + ansi + 'm' + str(args[1]) + '\033[0m] ' + self.command + ' ' + path)

        
  def encode_link(self, bhash):
    alphabet = b'rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz'
    string = ''
    i = 0

    for offset, byte in enumerate(reversed(bytearray(bhash))):
      i += byte << (offset * 8)

    while i:
      i, idx = divmod(i, len(alphabet))
      string = alphabet[idx:idx + 1].decode('utf') + string

    return string


  def do_GET(self):
    fpath = self.path.split('?', 1)[0]
    ro = False

    if fpath == '/':
      fpath = '/index.html'

    if fpath == '/ping':
      r = [ 'text/plain', 200, 'OK\r\n'.encode('utf-8') ]

    elif re.search(r'^/dt/[A-Za-z0-9_-]{1,24}$', fpath):
      if repository != None:
        fpath = os.path.normpath(repository + '/jfx_' + fpath[4:] + '.yml')

        with lock:
          if os.path.isfile(fpath):
            try:
              with open(fpath, 'rb') as f:
                r = [ 'application/json', 200, f.read() ]

              if not os.access(fpath, os.W_OK):
                ro = True

              os.utime(fpath, None)

            except Exception:
              r = [ 'text/plain', 500, '500 Internal Server Error\r\n'.encode('utf-8') ]

          else:
            r = [ 'text/plain', 404, '404 Not Found\r\n'.encode('utf-8') ]

      else:
        r = [ 'text/plain', 503, '503 Service Unavailable\r\n'.encode('utf-8') ]

    elif not re.search(r'[^A-Za-z0-9_./-]', fpath) and not re.search(r'\.{2,}', fpath) and os.path.isfile('www' + fpath):
      if fpath.endswith('.js'):
        ctype = 'text/javascript'
      elif fpath.endswith('.css'):
        ctype = 'text/css'
      elif fpath.endswith('png'):
        ctype = 'image/png'
      else:
        ctype = 'text/html'

      try:
        with open('www' + fpath, 'rb') as f:
          r = [ ctype, 200, f.read() ]

          if fpath == '/index.html':
            r[2] = r[2].decode('utf-8').replace('{{ jinjafx.version }}', jinjafx.__version__).encode('utf-8')

      except Exception:
        r = [ 'text/plain', 500, '500 Internal Server Error\r\n'.encode('utf-8') ]

    else:
      r = [ 'text/plain', 404, '404 Not Found\r\n'.encode('utf-8') ]

    self.send_response(r[1])
    self.send_header('Content-Type', r[0])
    self.send_header('Content-Length', str(len(r[2])))
    if ro:
      self.send_header('X-Read-Only', 'yes');  
    self.end_headers()
    self.wfile.write(r[2])


  def do_POST(self):
    uc = self.path.split('?', 1)
    params = { x[0]: x[1] for x in [x.split('=') for x in uc[1].split('&') ] } if len(uc) > 1 else { }
    fpath = uc[0]

    if 'Content-Length' in self.headers:
      postdata = self.rfile.read(int(self.headers['Content-Length'])).decode('utf-8')

      if len(postdata) < (256 * 1024):
        if fpath == '/jinjafx':
          if self.headers['Content-Type'] == 'application/json':
            try:
              gvars = {}
  
              dt = json.loads(postdata)
              template = base64.b64decode(dt['template']) if 'template' in dt and len(dt['template'].strip()) > 0 else ''
              data = base64.b64decode(dt['data']) if 'data' in dt and len(dt['data'].strip()) > 0 else ''
  
              if 'vars' in dt and len(dt['vars'].strip()) > 0:
                gyaml = base64.b64decode(dt['vars'])

                if 'vault_password' in dt:
                  vault = VaultLib([(DEFAULT_VAULT_ID_MATCH, VaultSecret(base64.b64decode(dt['vault_password'])))])

                  if gyaml.decode('utf-8').startswith('$ANSIBLE_VAULT;'):
                    gyaml = vault.decrypt(gyaml).decode('utf-8')

                  def yaml_vault_tag(loader, node):
                    return vault.decrypt(node.value).decode('utf-8')

                  yaml.add_constructor('!vault', yaml_vault_tag, yaml.FullLoader)

                gvars.update(yaml.load(gyaml, Loader=yaml.FullLoader))
  
              st = round(time.time() * 1000)
              outputs = jinjafx.JinjaFx().jinjafx(template, data, gvars, 'Output')
              ocount = 0
  
              jsr = {
                'status': 'ok',
                'elapsed': round(time.time() * 1000) - st,
                'outputs': {}
              }
  
              for o in outputs:
                output = '\n'.join(outputs[o]) + '\n'
                if len(output.strip()) > 0:
                  jsr['outputs'].update({ o: base64.b64encode(output.encode('utf-8')).decode('utf-8') })
                  ocount += 1
  
              if ocount == 0:
                raise Exception('nothing to output')
  
            except Exception as e:
              tb = traceback.format_exc()
              match = re.search(r'[\s\S]*File "<(?:template|unknown)>", line ([0-9]+), in.*template', tb, re.IGNORECASE)
              if match:
                error = 'error[template.j2:' + match.group(1) + ']: ' + type(e).__name__ + ': ' + str(e)
              elif 'yaml.FullLoader' in tb:
                error = 'error[vars.yml]: ' + type(e).__name__ + ': ' + str(e)
              else:
                traceback.print_exc()
                error = 'error[' + str(sys.exc_info()[2].tb_lineno) + ']: ' + type(e).__name__ + ': ' + str(e)

              jsr = {
                'status': 'error',
                'error': '<pre>' + error + '</pre>'
              }
              self.log_request('ERR', error);
  
            r = [ 'application/json', 200, json.dumps(jsr) ]
  
          else:
            r = [ 'text/plain', 400, '400 Bad Request\r\n' ]
  
        elif fpath == '/download':
          if self.headers['Content-Type'] == 'application/json':
            lterminator = '\r\n' if 'User-Agent' in self.headers and 'windows' in self.headers['User-Agent'].lower() else '\n'
  
            try:
              outputs = json.loads(postdata)
  
              zfile = io.BytesIO()
              z = zipfile.ZipFile(zfile, 'w', zipfile.ZIP_DEFLATED)
  
              for o in outputs:
                ofile = re.sub(r'_+', '_', re.sub(r'[^A-Za-z0-9_. -/]', '_', os.path.normpath(o)))
                outputs[o] = re.sub(r'\r?\n', lterminator, base64.b64decode(outputs[o]).decode('utf-8'))
  
                if '.' not in ofile:
                  if re.search(r'<html.*?>[\s\S]+<\/html>', outputs[o], re.IGNORECASE):
                    ofile += '.html'
                  else:
                    ofile += '.txt'
  
                z.writestr(ofile, outputs[o])
  
              z.close()
  
              self.send_response(200)
              self.send_header('Content-Type', 'application/zip')
              self.send_header('Content-Length', str(len(zfile.getvalue())))
              self.send_header('X-Download-Filename', 'Outputs.' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '.zip')
              self.end_headers()
              self.wfile.write(zfile.getvalue())
              return
  
            except Exception as e:
              log('error: ' + str(e))
              r = [ 'text/plain', 400, '400 Bad Request\r\n' ]
  
          else:
            r = [ 'text/plain', 400, '400 Bad Request\r\n' ]

        elif fpath == '/get_link':
          if repository != None:
            if self.headers['Content-Type'] == 'application/json':
              try:
                dt = json.loads(postdata)

                vdt = {}
                vdt['data'] = base64.b64decode(dt['data']).decode('utf-8') if 'data' in dt and len(dt['data'].strip()) > 0 else ''
                vdt['template'] = base64.b64decode(dt['template']).decode('utf-8') if 'template' in dt and len(dt['template'].strip()) > 0 else ''
                vdt['vars'] = base64.b64decode(dt['vars']).decode('utf-8') if 'vars' in dt and len(dt['vars'].strip()) > 0 else ''

                dt_yml = '---\n'
                dt_yml += 'dt:\n'

                if vdt['data'] == '':
                  dt_yml += '  data: ""\n\n'
                else:
                  dt_yml += '  data: |2\n'
                  dt_yml += re.sub('^', ' ' * 4, vdt['data'].rstrip(), flags=re.MULTILINE) + '\n\n'

                if vdt['template'] == '':
                  dt_yml += '  template: ""\n\n'
                else:
                  dt_yml += '  template: |2\n'
                  dt_yml += re.sub('^', ' ' * 4, vdt['template'].rstrip(), flags=re.MULTILINE) + '\n\n'

                if vdt['vars'] == '':
                  dt_yml += '  vars: ""\n'
                else:
                  dt_yml += '  vars: |2\n'
                  dt_yml += re.sub('^', ' ' * 4, vdt['vars'].rstrip(), flags=re.MULTILINE) + '\n'

                dt_link = self.encode_link(hashlib.sha256(dt_yml.encode('utf-8')).digest()[:12])
                dt_sha256 = hashlib.sha256(dt_yml.encode('utf-8')).hexdigest()

                if 'id' in params:
                  dt_yml += '\nrev_id: 1\n'
                else:
                  dt_yml += '\nrev_id: 0\n'

                dt_yml += 'created: "' + datetime.datetime.now().strftime('%b %d, %Y at %H:%M:%S') + '"\n'
                dt_yml += 'sha256: "' + dt_sha256 + '"\n'

                if hasattr(self, 'headers'):
                  if 'User-Agent' in self.headers:
                    dt_yml += 'user-agent: "' + self.headers['User-Agent'] + '"\n'
                  if 'X-Forwarded-For' in self.headers:
                    dt_yml += 'remote-addr: "' + self.headers['X-Forwarded-For'] + '"\n'
                  else:
                    dt_yml += 'remote-addr: "' + str(self.client_address[0]) + '"\n'

                if os.access(repository, os.W_OK):
                  with lock:
                    maxiter = 10

                    if 'id' in params:
                      dt_id = params['id']
  
                      if re.search(r'^[A-Za-z0-9_-]{1,24}$', dt_id):
                        fpath = os.path.normpath(repository + '/jfx_' + dt_id + '.yml')
  
                        if os.path.exists(fpath):
                          if os.access(fpath, os.W_OK):
                            try:
                              with open(fpath, 'r') as f:
                                if '\nsha256: "' + dt_sha256 + '"' in f.read():
                                  fpath = None
                            except:
                              pass
  
                            if fpath != None:
                              os.rename(fpath, fpath + '.' + dt_link + '.bak')
  
                          else:
                            raise Exception("link is read only")
  
                        else:
                          raise Exception("link doesn't exist")
  
                      else:
                        raise Exception("invalid link format")
  
                    else:
                      while maxiter > 0:
                        dt_id = dt_link
                        fpath = os.path.normpath(repository + '/jfx_' + dt_id + '.yml')
  
                        if os.path.exists(fpath):
                          if not os.access(fpath, os.W_OK):
                            dt_link = self.encode_link(hashlib.sha256(dt_link.encode('utf-8')).digest()[:12])
                            maxiter -= 1
                            continue
  
                          try:
                            with open(fpath, 'r') as f:
                              if '\nrev_id: 1' in f.read():
                                dt_link = self.encode_link(hashlib.sha256(dt_link.encode('utf-8')).digest()[:12])
                                maxiter -= 1
                                continue
                          except:
                            pass
  
                          fpath = None
  
                        break

                    if maxiter == 0:
                      log('error: unable to generate unique link')
                      r = [ 'text/plain', 500, '500 Internal Server Error\r\n' ]

                    else:
                      try:
                        if fpath != None:
                          with open(fpath, 'w') as f:
                            f.write(dt_yml)
  
                        r = [ 'text/plain', 200, dt_id + '\r\n' ]
  
                      except Exception as e:
                        log('error: ' + str(e))
                        r = [ 'text/plain', 500, '500 Internal Server Error\r\n' ]

                else:
                  log('error: unable to write to repository')
                  r = [ 'text/plain', 500, '500 Internal Server Error\r\n' ]

              except Exception as e:
                log('error: ' + str(e))
                r = [ 'text/plain', 400, '400 Bad Request\r\n' ]

            else:
              r = [ 'text/plain', 400, '400 Bad Request\r\n' ]

          else:
            r = [ 'text/plain', 503, '503 Service Unavailable\r\n' ]

        else:
          r = [ 'text/plain', 404, '404 Not Found\r\n' ]

      else:
        r = [ 'text/plain', 413, '413 Request Entity Too Large\r\n' ]

    else:
      r = [ 'text/plain', 400, '400 Bad Request\r\n' ]

    self.send_response(r[1])
    self.send_header('Content-Type', r[0])
    self.send_header('Content-Length', str(len(r[2])))
    self.end_headers()
    self.wfile.write(r[2].encode('utf-8'))


class JinjaFxThread(threading.Thread):
  def __init__(self, s, addr):
    threading.Thread.__init__(self)
    self.s = s
    self.addr = addr
    self.daemon = True
    self.start()


  def run(self):
    httpd = JinjaFxServer(self.addr, JinjaFxRequest, False)
    httpd.socket = self.s
    httpd.server_bind = self.server_close = lambda self: None
    httpd.serve_forever()


def main(rflag=False):
  global repository

  try:
    print('JinjaFx Server v' + jinjafx.__version__ + ' - Jinja Templating Tool')
    print('Copyright (c) 2020-' + datetime.datetime.now().strftime('%Y') + ' Chris Mason <chris@jinjafx.org>\n')

    parser = jinjafx.ArgumentParser(add_help=False)
    parser.add_argument('-s', action='store_true', required=True)
    parser.add_argument('-l', metavar='<address>', default='127.0.0.1', type=str)
    parser.add_argument('-p', metavar='<port>', default=8080, type=int)
    parser.add_argument('-r', metavar='<repository>', type=w_directory)
    args = parser.parse_args()

    jinjafx.import_filters()

    log('Starting JinjaFx Server on http://' + args.l + ':' + str(args.p) + '...')

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((args.l, args.p))
    s.listen(5)

    threads = []
    rflag = True
    repository = args.r

    for i in range(64):
      threads.append(JinjaFxThread(s, (args.l, args.p)))

    while True:
      time.sleep(0.1)

  except KeyboardInterrupt:
    sys.exit(-1)

  except Exception as e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    print('error[' + str(exc_tb.tb_lineno) + ']: ' + str(e), file=sys.stderr)
    sys.exit(-2)

  finally:
    if rflag is True:
      log('Terminating JinjaFx Server...')
      s.shutdown(1)
      s.close()


def log(t):
  with lock:
    print('[' + datetime.datetime.now().strftime('%b %d %H:%M:%S.%f')[:19] + '] {' + str(os.getpid()) + '} ' + t)


def w_directory(d):
  if not os.path.isdir(d):
    raise argparse.ArgumentTypeError("repository directory '" + d + "' must exist")
  elif not os.access(d, os.W_OK):
    raise argparse.ArgumentTypeError("repository directory '" + d + "' must be writable")
  return d


if __name__ == '__main__':
  main()
