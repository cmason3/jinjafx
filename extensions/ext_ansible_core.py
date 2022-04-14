# JinjaFx - Jinja2 Templating Tool
# Copyright (c) 2020-2022 Chris Mason <chris@netnix.org>
#
# Portions of this file are part of Ansible
# Copyright (c) 2012 Jeroen Hoekx <jeroen@hoekx.be>
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

from jinja2.ext import Extension
import re, base64, hashlib, yaml, json, datetime, time, math
 
class plugin(Extension):
  def __init__(self, environment):
    Extension.__init__(self, environment)
    environment.tests['regex'] = self.__regex
    environment.tests['match'] = self.__match
    environment.tests['search'] = self.__search
    environment.tests['contains'] = self.__contains
    environment.tests['any'] = any
    environment.tests['all'] = all
    environment.filters['to_yaml'] = self.__to_yaml
    environment.filters['to_nice_yaml'] = self.__to_nice_yaml
    environment.filters['from_yaml'] = self.__from_yaml
    environment.filters['to_json'] = self.__to_json
    environment.filters['to_nice_json'] = self.__to_nice_json
    environment.filters['from_json'] = json.loads
    environment.filters['to_bool'] = self.__to_bool
    environment.filters['to_datetime'] = self.__to_datetime
    environment.filters['strftime'] = self.__strftime
    environment.filters['b64decode'] = self.__b64decode
    environment.filters['b64encode'] = self.__b64encode
    environment.filters['regex_replace'] = self.__regex_replace
    environment.filters['regex_search'] = self.__regex_search
    environment.filters['regex_findall'] = self.__regex_findall
    environment.filters['hash'] = self.__hash
    environment.filters['log'] = self.__log
    environment.filters['pow'] = self.__pow
    environment.filters['root'] = self.__root

  def __to_yaml(self, a, *args, **kw):
    default_flow_style = kw.pop('default_flow_style', None)
    return yaml.dump(a, Dumper=yaml.SafeDumper, allow_unicode=True, default_flow_style=default_flow_style, **kw)

  def __to_nice_yaml(self, a, indent=4, *args, **kw):
    return yaml.dump(a, Dumper=yaml.SafeDumper, indent=indent, allow_unicode=True, default_flow_style=False, **kw)

  def __from_yaml(self, data):
    if isinstance(data, str):
      return yaml.load(data, Loader=yaml.SafeLoader)
    return data

  def __to_json(self, a, *args, **kw):
    return json.dumps(a, *args, **kw)

  def __to_nice_json(self, a, indent=4, sort_keys=True, *args, **kw):
    return self.__to_json(a, indent=indent, sort_keys=sort_keys, separators=(',', ': '), *args, **kw)

  def __to_bool(self, a):
    if a is None or isinstance(a, bool):
      return a

    if isinstance(a, str):
      a = a.lower()

    if a in ('yes', 'on', '1', 'true', 1):
      return True

    return False

  def __to_datetime(self, string, format="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.strptime(string, format)

  def __strftime(self, string_format, second=None):
    if second is not None:
      second = float(second)
    return time.strftime(string_format, time.localtime(second))

  def __b64decode(self, string, encoding='utf-8'):
    return base64.b64decode(string.encode(encoding)).decode(encoding)

  def __b64encode(self, string, encoding='utf-8'):
    return base64.b64encode(string.encode(encoding)).decode(encoding)

  def __regex(self, value='', pattern='', ignorecase=False, multiline=False, match_type='search', flags=0):
    if ignorecase:
      flags |= re.I

    if multiline:
      flags |= re.M

    _re = re.compile(pattern, flags=flags)
    return bool(getattr(_re, match_type, 'search')(value))

  def __match(self, value, pattern='', ignorecase=False, multiline=False):
    return self.__regex(value, pattern, ignorecase, multiline, 'match')

  def __search(self, value, pattern='', ignorecase=False, multiline=False):
    return self.__regex(value, pattern, ignorecase, multiline, 'search')

  def __contains(self, seq, value):
    return value in seq

  def __regex_replace(self, value='', pattern='', replacement='', ignorecase=False, multiline=False, flags=0):
    if ignorecase:
      flags |= re.I

    if multiline:
      flags |= re.M

    _re = re.compile(pattern, flags=flags)
    return _re.sub(replacement, value)

  def __regex_search(self, value, regex, *args, **kwargs):
    groups = list()
    flags = 0

    for arg in args:
      if arg.startswith('\\g'):
        match = re.match(r'\\g<(\S+)>', arg).group(1)
        groups.append(match)
      elif arg.startswith('\\'):
        match = int(re.match(r'\\(\d+)', arg).group(1))
        groups.append(match)
      else:
        raise Exception('Unknown argument')

    if kwargs.get('ignorecase'):
      flags |= re.I
    if kwargs.get('multiline'):
      flags |= re.M

    match = re.search(regex, value, flags)
    if match:
      if not groups:
        return match.group()
      else:
        items = list()
        for item in groups:
          items.append(match.group(item))
        return items

  def __regex_findall(self, value, pattern='', multiline=False, ignorecase=False):
    return self.__regex(value, pattern, ignorecase, multiline, 'findall')

  def __hash(self, data, hashtype='sha1'):
    h = hashlib.new(hashtype)
    h.update(data.encode('utf-8'))
    return h.hexdigest()

  def __log(self, x, base=math.e):
    return math.log10(x) if base == 10 else math.log(x, base)

  def __pow(self, x, y):
    return math.pow(x, y)

  def __root(self, x, base=2):
    return math.sqrt(x) if base == 2 else math.pow(x, 1.0 / float(base))

