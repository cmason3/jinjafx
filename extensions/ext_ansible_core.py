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

from jinja2.ext import Extension
import re
 
class plugin(Extension):
  def __init__(self, environment):
    Extension.__init__(self, environment)
    environment.tests['regex'] = self.__regex
    environment.tests['match'] = self.__match
    environment.tests['search'] = self.__search
    environment.filters['regex_replace'] = self.__regex_replace
    environment.filters['regex_search'] = self.__regex_search
    environment.filters['regex_findall'] = self.__regex_findall

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

