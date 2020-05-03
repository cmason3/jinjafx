#!/usr/bin/env python

# JinjaFx Server - Jinja Templating Tool
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

from __future__ import print_function
from http.server import HTTPServer, BaseHTTPRequestHandler
import jinjafx, os, io, sys, socket, threading, yaml, json, base64, time, datetime, re, argparse, zipfile

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

      if self.command == 'POST':
        log('[' + src + '] [\033[1;' + ansi + 'm' + str(args[1]) + '\033[0m] \033[1;33m' + self.command + '\033[0m ' + path + ctype)

      elif self.command != None:
        log('[' + src + '] [\033[1;' + ansi + 'm' + str(args[1]) + '\033[0m] ' + self.command + ' ' + path)

        
  def do_GET(self):
    fpath = self.path.split('?', 1)[0]

    if fpath == '/':
      fpath = '/index.html'

    if fpath == '/ping':
      r = [ 'text/plain', 200, 'OK\r\n'.encode('utf-8') ]

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
        with open('www' + fpath, 'rb') as file:
          r = [ ctype, 200, file.read() ]

      except Exception:
        r = [ 'text/plain', 500, '500 Internal Server Error\r\n'.encode('utf-8') ]

    else:
      r = [ 'text/plain', 404, '404 Not Found\r\n'.encode('utf-8') ]

    self.send_response(r[1])
    self.send_header('Content-Type', r[0])
    self.send_header('Content-Length', str(len(r[2])))
    self.end_headers()
    self.wfile.write(r[2])


  def do_POST(self):
    if 'Content-Length' in self.headers:
      postdata = self.rfile.read(int(self.headers['Content-Length'])).decode('utf-8')

      if self.path == '/jinjafx':
        if self.headers['Content-Type'] == 'application/json':
          try:
            jsr = {}
            gvars = {}

            dt = json.loads(postdata)
            template = base64.b64decode(dt['template']) if 'template' in dt and len(dt['template'].strip()) > 0 else ''
            data = base64.b64decode(dt['data']) if 'data' in dt and len(dt['data'].strip()) > 0 else ''

            if 'vars' in dt and len(dt['vars'].strip()) > 0:
              gvars.update(yaml.load(base64.b64decode(dt['vars']), Loader=yaml.FullLoader))

            try:
              st = datetime.datetime.now()
              outputs = jinjafx.JinjaFx().jinjafx(template, data, gvars, 'Output')
              ocount = 0

              jsr = {
                'status': 'ok',
                'elapsed': (datetime.datetime.now().microsecond - st.microsecond) / 1000,
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
              exc_type, exc_obj, exc_tb = sys.exc_info()
              jsr = {
                'status': 'error',
                'error': 'error[' + str(exc_tb.tb_lineno) + ']: ' + str(e)
              }

            r = [ 'application/json', 200, json.dumps(jsr) ]

          except Exception as e:
            log('error: ' + str(e))
            r = [ 'text/plain', 400, '400 Bad Request\r\n' ]

        else:
          r = [ 'text/plain', 400, '400 Bad Request\r\n' ]

      elif self.path == '/download':
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

      else:
        r = [ 'text/plain', 404, '404 Not Found\r\n' ]

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
  try:
    print('JinjaFx Server v' + jinjafx.__version__ + ' - Jinja Templating Tool')
    print('Copyright (c) 2020 Chris Mason <chris@jinjafx.org>\n')

    parser = jinjafx.ArgumentParser(add_help=False)
    parser.add_argument('-s', action='store_true', required=True)
    parser.add_argument('-l', metavar='<address>', default='127.0.0.1', type=str)
    parser.add_argument('-p', metavar='<port>', default=8080, type=int)
    args = parser.parse_args()

    log('Starting JinjaFx Server on http://' + args.l + ':' + str(args.p) + '...')

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((args.l, args.p))
    s.listen(5)

    threads = []
    rflag = True

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
  print('[' + datetime.datetime.now().strftime('%b %d %H:%M:%S.%f')[:19] + '] {' + str(os.getpid()) + '} ' + t)


if __name__ == '__main__':
  main()
