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
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
import base64, random, re, crypt

class plugin(Extension):
  def __init__(self, environment):
    Extension.__init__(self, environment)
    environment.filters['cisco_snmpv3_key'] = self.__cisco_snmpv3_key
    environment.filters['junos_snmpv3_key'] = self.__junos_snmpv3_key
    environment.filters['cisco7encode'] = self.__cisco7encode
    environment.filters['junos9encode'] = self.__junos9encode
    environment.filters['cisco8hash'] = self.__cisco8hash
    environment.filters['cisco9hash'] = self.__cisco9hash
    environment.filters['junos6hash'] = self.__junos6hash

    self.__std_b64chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    self.__mod_b64chars = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    self.__mod_b64table = str.maketrans(self.__std_b64chars, self.__mod_b64chars)

  def __expand_snmpv3_key(self, password, algorithm):
    h = hashes.Hash(getattr(hashes, algorithm.upper())())
    h.update(((password * (1048576 // len(password))) + password[:1048576 % len(password)]).encode('utf-8'))
    return h.finalize()

  def __cisco_snmpv3_key(self, password, engineid, algorithm='sha1'):
    ekey = self.__expand_snmpv3_key(password, algorithm)

    h = hashes.Hash(getattr(hashes, algorithm.upper())())
    h.update(ekey + bytearray.fromhex(engineid) + ekey)
    hexdigest = h.finalize().hex()
    return ':'.join([hexdigest[i:i + 2] for i in range(0, len(hexdigest), 2)])

  def __junos_snmpv3_key(self, password, engineid, algorithm='sha1', prefix='80000a4c'):
    ekey = self.__expand_snmpv3_key(password, algorithm)

    if re.match(r'^(?:[a-f0-9]{2}:){5}[a-f0-9]{2}$', engineid):
      engineid = prefix + '03' + ''.join(engineid.split(':'))

    elif re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', engineid):
      engineid = prefix + '01' + ''.join("{:02x}".format(int(o), 2) for o in engineid.split('.'))

    else:
      engineid = prefix + '04' + ''.join("{:02x}".format(ord(c)) for c in engineid)

    h = hashes.Hash(getattr(hashes, algorithm.upper())())
    h.update(ekey + bytearray.fromhex(engineid) + ekey)
    return h.finalize().hex()

  def __cisco7encode(self, string, seed=False):
    KEY = 'dsfd;kfoA,.iyewrkldJKDHSUBsgvca69834ncxv9873254k;fg87'

    if seed:
      random.seed(seed)

    result = format(random.randint(0, 15), '02d')
    
    for i in range(0, len(string)):
      result += format(ord(string[i]) ^ ord(KEY[(i + int(result[:2])) % len(KEY)]), '02X')

    return result

  def __junos9encode(self, string, seed=False):
    ENCODING = [[1, 4, 32], [1, 16, 32], [1, 8, 32], [1, 64], [1, 32], [1, 4, 16, 128], [1, 32, 64]]
    FAMILY = ['QzF3n6/9CAtpu0O', 'B1IREhcSyrleKvMW8LXx', '7N-dVbwsY2g4oaJZGUDj', 'iHkq.mPf5T']
    EXTRA = { char: 3-i for i, f in enumerate(FAMILY) for char in f }
    NUM_ALPHA = [char for char in ''.join(FAMILY)]
    ALPHA_NUM = { NUM_ALPHA[i]: i for i, c in enumerate(NUM_ALPHA) }
  
    def random_salt(length):
      salt = ''

      for i in range(length):
        salt += NUM_ALPHA[random.randrange(len(NUM_ALPHA))]

      return salt
  
    def gap_encode(char, prev, encode):
      gaps = []
      val = ord(char)
      for e in encode[::-1]:
        gaps.insert(0, val // e)
        val %= e
  
      result = ''
      for g in gaps:
        g += ALPHA_NUM[prev] + 1
        c = prev = NUM_ALPHA[g % len(NUM_ALPHA)]
        result += c
  
      return result
  
    if seed:
      random.seed(seed)
  
    salt = random_salt(1)
    rand = random_salt(EXTRA[salt])
  
    pos = 0
    prev = salt
    result = '$9$' + salt + rand
  
    for char in string:
      result += gap_encode(char, prev, ENCODING[pos % len(ENCODING)])
      prev = result[-1]
      pos += 1
  
    return result

  def __generate_salt(self, length=16):
    return ''.join(random.choice(self.__mod_b64chars) for _ in range(length))

  def __cisco8hash(self, string, salt=None):
    if salt is None:
      salt = self.__generate_salt(14)

    elif len(salt) != 14 or any(c not in self.__mod_b64chars for c in salt):
      raise Exception('invalid salt provided to cisco8hash')

    h = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt.encode('utf-8'), iterations=20000).derive(string.encode('utf-8'))
    return '$8$' + salt + '$' + base64.b64encode(h).decode('utf-8').translate(self.__mod_b64table)[:-1]

  def __cisco9hash(self, string, salt=None):
    if salt is None:
      salt = self.__generate_salt(14)

    elif len(salt) != 14 or any(c not in self.__mod_b64chars for c in salt):
      raise Exception('invalid salt provided to cisco9hash')

    h = Scrypt(salt.encode('utf-8'), 32, 16384, 1, 1, default_backend()).derive(string.encode('utf-8'))
    return '$9$' + salt + '$' + base64.b64encode(h).decode('utf-8').translate(self.__mod_b64table)[:-1]

  def __junos6hash(self, string, salt=None):
    if salt is None:
      salt = self.__generate_salt(8)

    elif len(salt) != 8 or any(c not in self.__mod_b64chars for c in salt):
      raise Exception('invalid salt provided to junos6hash')

    return crypt.crypt(string, '$6$' + salt)
