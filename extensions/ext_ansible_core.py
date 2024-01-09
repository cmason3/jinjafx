# JinjaFx - Jinja2 Templating Tool
# Copyright (c) 2020-2024 Chris Mason <chris@netnix.org>
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
from jinja2.filters import do_unique
from jinja2.utils import pass_environment
from collections.abc import Sequence, Hashable
from urllib.parse import urlsplit
from jinjafx import JinjaFx

import re, base64, hashlib, yaml, json, datetime, time, math, random, itertools

class plugin(Extension):
  def __init__(self, environment):
    Extension.__init__(self, environment)

    for p in ('', 'ansible.builtin.'):
      environment.tests[p + 'regex'] = self.__regex
      environment.tests[p + 'match'] = self.__match
      environment.tests[p + 'search'] = self.__search
      environment.tests[p + 'contains'] = self.__contains
      environment.tests[p + 'any'] = any
      environment.tests[p + 'all'] = all
      environment.filters[p + 'to_yaml'] = self.__to_yaml
      environment.filters[p + 'to_nice_yaml'] = self.__to_nice_yaml
      environment.filters[p + 'from_yaml'] = self.__from_yaml
      environment.filters[p + 'to_json'] = self.__to_json
      environment.filters[p + 'to_nice_json'] = self.__to_nice_json
      environment.filters[p + 'from_json'] = json.loads
      environment.filters[p + 'bool'] = self.__bool
      environment.filters[p + 'to_datetime'] = self.__to_datetime
      environment.filters[p + 'strftime'] = self.__strftime
      environment.filters[p + 'b64decode'] = self.__b64decode
      environment.filters[p + 'b64encode'] = self.__b64encode
      environment.filters[p + 'random'] = self.__random
      environment.filters[p + 'shuffle'] = self.__shuffle
      environment.filters[p + 'ternary'] = self.__ternary
      environment.filters[p + 'dict2items'] = self.__dict2items
      environment.filters[p + 'items2dict'] = self.__items2dict
      environment.filters[p + 'extract'] = self.__extract
      environment.filters[p + 'flatten'] = self.__flatten
      environment.filters[p + 'regex_replace'] = self.__regex_replace
      environment.filters[p + 'regex_escape'] = self.__regex_escape
      environment.filters[p + 'regex_search'] = self.__regex_search
      environment.filters[p + 'regex_findall'] = self.__regex_findall
      environment.filters[p + 'hash'] = self.__hash
      environment.filters[p + 'product'] = itertools.product
      environment.filters[p + 'permutations'] = itertools.permutations
      environment.filters[p + 'combinations'] = itertools.combinations
      environment.filters[p + 'zip'] = zip
      environment.filters[p + 'zip_longest'] = itertools.zip_longest
      environment.filters[p + 'log'] = self.__log
      environment.filters[p + 'pow'] = self.__pow
      environment.filters[p + 'root'] = self.__root
      environment.filters[p + 'unique'] = self.__unique
      environment.filters[p + 'intersect'] = self.__intersect
      environment.filters[p + 'difference'] = self.__difference
      environment.filters[p + 'symmetric_difference'] = self.__symmetric_difference
      environment.filters[p + 'union'] = self.__union
      environment.filters[p + 'urlsplit'] = self.__urlsplit

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

  def __bool(self, a):
    if a is None or isinstance(a, bool):
      return a

    if isinstance(a, str):
      a = a.lower()

    if a in ('yes', 'on', '1', 'true', 1):
      return True

    return False

  def __to_datetime(self, string, fmt="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.strptime(string, fmt)

  def __strftime(self, string_format, second=None):
    if second is not None:
      second = float(second)
    return time.strftime(string_format, time.localtime(second))

  def __b64decode(self, string, encoding='utf-8'):
    return base64.b64decode(string.encode(encoding)).decode(encoding)

  def __b64encode(self, string, encoding='utf-8'):
    return base64.b64encode(string.encode(encoding)).decode(encoding)

  def __random(self, end, start=None, step=None, seed=None):
    r = random.Random(seed)

    if isinstance(end, int):
      if not start:
        start = 0
      if not step:
        step = 1

      return r.randrange(start, end, step)

    elif hasattr(end, '__iter__'):
      if start or step:
        raise JinjaFx.TemplateError('start and step can only be used with integer values')

      return r.choice(end)

    raise JinjaFx.TemplateError('random can only be used on sequences and integers')

  def __shuffle(self, mylist, seed=None):
    try:
      mylist = list(mylist)
      if seed is None:
        random.shuffle(mylist)
      else:
        random.Random(seed).shuffle(mylist)

    except Exception:
      pass

    return mylist

  def __ternary(self, value, true_val, false_val, none_val=None):
    if value is None:
      return none_val
    elif bool(value):
      return true_val
    else:
      return false_val

  def __urlsplit(self, value, query=None):
    obj = urlsplit(value)
    results = dict((k, getattr(obj, k)) for k in dir(obj) if not k.startswith('_') and not callable(getattr(obj, k)))

    if query is not None:
      if query not in results:
        raise JinjaFx.TemplateError('urlsplit: unknown URL component: ' + query)
      return results[query]
    else:
      return results

  def __dict2items(self, mydict, key_name='key', value_name='value'):
    ret = []
    if not isinstance(mydict, dict):
      raise JinjaFx.TemplateError('dict2items requires a dictionary, got ' + str(type(mydict)) + ' instead')

    for key in mydict:
      ret.append({key_name: key, value_name: mydict[key]})
    return ret

  def __items2dict(self, mylist, key_name='key', value_name='value'):
    if not isinstance(mylist, list):
      raise JinjaFx.TemplateError('items2dict requires a list, got ' + str(type(mylist)) + ' instead')

    try:
      return dict((item[key_name], item[value_name]) for item in mylist)
    except KeyError:
      raise JinjaFx.TemplateError('items2dict requires each dictionary in the list to contain the keys "' + str(key_name) + '" and "' + str(value_name) + '", got ' + str(mylist) + ' instead') from None
    except TypeError:
      raise JinjaFx.TemplateError('items2dict requires a list of dictionaries, got ' + str(mylist) + ' instead') from None

  @pass_environment
  def __extract(self, environment, item, container, morekeys=None):
    if morekeys is None:
        keys = [item]
    elif isinstance(morekeys, list):
        keys = [item] + morekeys
    else:
        keys = [item, morekeys]

    value = container
    for key in keys:
        value = environment.getitem(value, key)
    return value

  def __flatten(self, mylist, levels=None, skip_nulls=True):
    ret = []
    for element in mylist:
      if skip_nulls and element in (None, 'None', 'null'):
        continue
      elif not isinstance(element, (str, bytes)) and isinstance(element, Sequence):
        if levels is None:
          ret.extend(self.__flatten(element, skip_nulls=skip_nulls))
        elif levels >= 1:
          ret.extend(self.__flatten(element, levels=(int(levels) - 1), skip_nulls=skip_nulls))
        else:
          ret.append(element)
      else:
        ret.append(element)
    return ret

  def __regex(self, value='', pattern='', ignorecase=False, multiline=False, match_type='search', flags=0):
    if ignorecase:
      flags |= re.I

    if multiline:
      flags |= re.M

    _re = re.compile(pattern, flags=flags)

    if match_type == 'match':
      return bool(_re.match(value))
    elif match_type == 'findall':
      return bool(_re.findall(value))
    else:
      return bool(_re.search(value))

    #return bool(getattr(_re, match_type, 'search')(value))

  def __match(self, value, pattern='', ignorecase=False, multiline=False):
    return self.__regex(value, pattern, ignorecase, multiline, 'match')

  def __search(self, value, pattern='', ignorecase=False, multiline=False):
    return self.__regex(value, pattern, ignorecase, multiline, 'search')

  def __regex_findall(self, value, pattern='', multiline=False, ignorecase=False):
    return self.__regex(value, pattern, ignorecase, multiline, 'findall')

  def __contains(self, seq, value):
    return value in seq

  def __regex_escape(self, string, re_type='python'):
    if re_type == 'python':
      return re.escape(string)

    elif re_type == 'posix_basic':
      return self.__regex_replace(string, r'([].[^$*\\])', r'\\\1')

    else:
      raise JinjaFx.TemplateError('Unknown regex type - ' + re_type)

  def __regex_replace(self, value='', pattern='', replacement='', ignorecase=False, multiline=False, flags=0):
    if ignorecase:
      flags |= re.I

    if multiline:
      flags |= re.M

    _re = re.compile(pattern, flags=flags)
    return _re.sub(replacement, value)

  def __regex_search(self, value, regex, *args, **kwargs):
    groups = []
    flags = 0

    for arg in args:
      if arg.startswith('\\g'):
        match1 = re.match(r'\\g<(\S+)>', arg)
        groups.append(match1.group(1))
      elif arg.startswith('\\'):
        match2 = re.match(r'\\(\d+)', arg)
        groups.append(int(match2.group(1)))
      else:
        raise JinjaFx.TemplateError('Unknown argument')

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

  @pass_environment
  def __unique(self, environment, a, case_sensitive=None, attribute=None):
    return list(do_unique(environment, a, case_sensitive=bool(case_sensitive), attribute=attribute))

  @pass_environment
  def __intersect(self, environment, a, b):
    #if isinstance(a, Hashable) and isinstance(b, Hashable):
    #  c = set(a) & set(b)
    #else:
    return self.__unique(environment, [x for x in a if x in b], True)
    #return c

  @pass_environment
  def __difference(self, environment, a, b):
    #if isinstance(a, Hashable) and isinstance(b, Hashable):
    #  c = set(a) - set(b)
    #else:
    return self.__unique(environment, [x for x in a if x not in b], True)
    #return c

  @pass_environment
  def __symmetric_difference(self, environment, a, b):
    #if isinstance(a, Hashable) and isinstance(b, Hashable):
    #  c = set(a) ^ set(b)
    #else:
    isect = self.__intersect(environment, a, b)
    return [x for x in self.__union(environment, a, b) if x not in isect]
    #return c

  @pass_environment
  def __union(self, environment, a, b):
    #if isinstance(a, Hashable) and isinstance(b, Hashable):
    #  c = set(a) | set(b)
    #else:
    return self.__unique(environment, a + b, True)
    #return c

