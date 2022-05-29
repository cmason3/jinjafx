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

import netutils.bandwidth, netutils.interface
 
class plugin(Extension):
  def __init__(self, environment):
    Extension.__init__(self, environment)

    environment.filters['name_to_bits'] = netutils.bandwidth.name_to_bits
    environment.filters['name_to_bytes'] = netutils.bandwidth.name_to_bytes
    environment.filters['bits_to_name'] = netutils.bandwidth.bits_to_name
    environment.filters['bytes_to_name'] = netutils.bandwidth.bytes_to_name
    environment.filters['name_to_name'] = netutils.bandwidth.name_to_name
    environment.filters['interface_range_expansion'] = netutils.interface.interface_range_expansion
    environment.filters['interface_range_compress'] = netutils.interface.interface_range_compress
    environment.filters['split_interface'] = netutils.interface.split_interface
    environment.filters['canonical_interface_name'] = netutils.interface.canonical_interface_name
    environment.filters['canonical_interface_name_list'] = netutils.interface.canonical_interface_name_list
    environment.filters['abbreviated_interface_name'] = netutils.interface.abbreviated_interface_name
    environment.filters['abbreviated_interface_name_list'] = netutils.interface.abbreviated_interface_name_list
    environment.filters['sort_interface_list'] = netutils.interface.sort_interface_list
