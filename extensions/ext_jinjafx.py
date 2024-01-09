# JinjaFx - Jinja2 Templating Tool
# Copyright (c) 2020-2024 Chris Mason <chris@netnix.org>
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

from jinja2 import Environment
from jinja2.ext import Extension
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.exceptions import InvalidTag
from jinjafx import JinjaFx

import os, base64, random, re, hashlib, ipaddress

try:
  from lxml import etree
  lxml = True

except:
  lxml = False

class plugin(Extension):
  def __init__(self, environment):
    Extension.__init__(self, environment)
    
    self.__vaulty = Vaulty()
    self.__std_b64chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    self.__mod_b64chars = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    self.__mod_b64table = str.maketrans(self.__std_b64chars, self.__mod_b64chars)
    
    environment.filters['cisco_snmpv3_key'] = self.__cisco_snmpv3_key
    environment.filters['junos_snmpv3_key'] = self.__junos_snmpv3_key
    environment.filters['cisco7encode'] = self.__cisco7encode
    environment.filters['junos9encode'] = self.__junos9encode
    environment.filters['cisco8hash'] = self.__cisco8hash
    environment.filters['cisco9hash'] = self.__cisco9hash
    environment.filters['cisco10hash'] = self.__cisco10hash
    environment.filters['junos6hash'] = self.__junos6hash
    environment.filters['ipsort'] = self.__ipsort
    environment.filters['summarize_address_range'] = self.__summarize_address_range
    environment.filters['xpath'] = self.__xpath
    environment.filters['vaulty_encrypt'] = self.__vaulty.encrypt
    environment.filters['vaulty_decrypt'] = self.__vaulty.decrypt

  def __expand_snmpv3_key(self, password, algorithm):
    h = hashlib.new(algorithm)
    h.update(((password * (1048576 // len(password))) + password[:1048576 % len(password)]).encode('utf-8'))
    return h.digest()

  def __cisco_snmpv3_key(self, password, engineid, algorithm='sha1'):
    ekey = self.__expand_snmpv3_key(password, algorithm)

    h = hashlib.new(algorithm)
    h.update(ekey + bytearray.fromhex(engineid) + ekey)
    hexdigest = h.hexdigest()
    return ':'.join([hexdigest[i:i + 2] for i in range(0, len(hexdigest), 2)])

  def __junos_snmpv3_key(self, password, engineid, algorithm='sha1', prefix='80000a4c'):
    ekey = self.__expand_snmpv3_key(password, algorithm)

    if re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', engineid):
      data = ''.join(f"{o:02x}" for o in map(int, engineid.split('.')))
      engineid = prefix + '01' + data

    elif re.match(r'^(?:[a-f0-9]{2}:){5}[a-f0-9]{2}$', engineid):
      engineid = prefix + '03' + engineid.replace(':', '')

    else:
      data = ''.join(f"{c:02x}" for c in map(ord, engineid))
      engineid = prefix + '04' + data

    h = hashlib.new(algorithm)
    h.update(ekey + bytearray.fromhex(engineid) + ekey)
    return h.hexdigest()

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
      raise JinjaFx.TemplateError('invalid salt provided to cisco8hash')

    h = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt.encode('utf-8'), iterations=20000).derive(string.encode('utf-8'))
    return '$8$' + salt + '$' + base64.b64encode(h).decode('utf-8').translate(self.__mod_b64table)[:-1]

  def __cisco9hash(self, string, salt=None):
    if salt is None:
      salt = self.__generate_salt(14)

    elif len(salt) != 14 or any(c not in self.__mod_b64chars for c in salt):
      raise JinjaFx.TemplateError('invalid salt provided to cisco9hash')

    h = Scrypt(salt.encode('utf-8'), 32, 16384, 1, 1).derive(string.encode('utf-8'))
    return '$9$' + salt + '$' + base64.b64encode(h).decode('utf-8').translate(self.__mod_b64table)[:-1]

  def __sha512_crypt(self, key, salt):
    def b64_from_24bit(b2, b1, b0, n):
      index = b2 << 16 | b1 << 8 | b0

      ret = []
      for i in range(n):
        ret.append(self.__mod_b64chars[index & 0x3f])
        index >>= 6
      
      return ''.join(ret)

    nkey = key.encode('utf-8')
    klen = len(nkey)

    h = hashlib.sha512()
    alt_h = hashlib.sha512()

    alt_h.update(nkey + salt.encode('utf-8') + nkey)
    alt_r = alt_h.digest()

    h.update(nkey + salt.encode('utf-8'))

    for i in range(klen // 64):
      h.update(alt_r)

    h.update(alt_r[:(klen % 64)])

    while klen > 0:
      if klen & 1 == 0:
        h.update(nkey)
      else:
        h.update(alt_r)

      klen >>= 1

    alt_r = h.digest()

    h = hashlib.sha512()
    alt_h = hashlib.sha512()

    for i in range(len(nkey)):
      h.update(nkey)

    t = h.digest()
    p_bytes = t * (len(nkey) // 64)
    p_bytes += t[:(len(nkey) % 64)]

    for i in range(16 + alt_r[0]):
      alt_h.update(salt.encode('utf-8'))

    t = alt_h.digest()
    s_bytes = t * (len(salt) // 64)
    s_bytes += t[:(len(salt) % 64)]

    for i in range(5000):
      h = hashlib.sha512()

      h.update(p_bytes if i & 1 else alt_r)

      if i % 3:
        h.update(s_bytes)

      if i % 7:
        h.update(p_bytes)

      h.update(alt_r if i & 1 else p_bytes)

      alt_r = h.digest()

    ret = []
    ret.append(b64_from_24bit(alt_r[0], alt_r[21], alt_r[42], 4))
    ret.append(b64_from_24bit(alt_r[22], alt_r[43], alt_r[1], 4))
    ret.append(b64_from_24bit(alt_r[44], alt_r[2], alt_r[23], 4))
    ret.append(b64_from_24bit(alt_r[3], alt_r[24], alt_r[45], 4))
    ret.append(b64_from_24bit(alt_r[25], alt_r[46], alt_r[4], 4))
    ret.append(b64_from_24bit(alt_r[47], alt_r[5], alt_r[26], 4))
    ret.append(b64_from_24bit(alt_r[6], alt_r[27], alt_r[48], 4))
    ret.append(b64_from_24bit(alt_r[28], alt_r[49], alt_r[7], 4))
    ret.append(b64_from_24bit(alt_r[50], alt_r[8], alt_r[29], 4))
    ret.append(b64_from_24bit(alt_r[9], alt_r[30], alt_r[51], 4))
    ret.append(b64_from_24bit(alt_r[31], alt_r[52], alt_r[10], 4))
    ret.append(b64_from_24bit(alt_r[53], alt_r[11], alt_r[32], 4))
    ret.append(b64_from_24bit(alt_r[12], alt_r[33], alt_r[54], 4))
    ret.append(b64_from_24bit(alt_r[34], alt_r[55], alt_r[13], 4))
    ret.append(b64_from_24bit(alt_r[56], alt_r[14], alt_r[35], 4))
    ret.append(b64_from_24bit(alt_r[15], alt_r[36], alt_r[57], 4))
    ret.append(b64_from_24bit(alt_r[37], alt_r[58], alt_r[16], 4))
    ret.append(b64_from_24bit(alt_r[59], alt_r[17], alt_r[38], 4))
    ret.append(b64_from_24bit(alt_r[18], alt_r[39], alt_r[60], 4))
    ret.append(b64_from_24bit(alt_r[40], alt_r[61], alt_r[19], 4))
    ret.append(b64_from_24bit(alt_r[62], alt_r[20], alt_r[41], 4))
    ret.append(b64_from_24bit(0, 0, alt_r[63], 2))
    return '$6$' + salt + '$' + ''.join(ret)

  def __cisco10hash(self, string, salt=None):
    if salt is None:
      salt = self.__generate_salt(16)

    elif len(salt) != 16 or any(c not in self.__mod_b64chars for c in salt):
      raise JinjaFx.TemplateError('invalid salt provided to cisco10hash')

    return self.__sha512_crypt(string, salt)

  def __junos6hash(self, string, salt=None):
    if salt is None:
      salt = self.__generate_salt(8)

    elif len(salt) != 8 or any(c not in self.__mod_b64chars for c in salt):
      raise JinjaFx.TemplateError('invalid salt provided to junos6hash')

    return self.__sha512_crypt(string, salt)

  def __ipsort(self, a):
    if isinstance(a, list):
      return sorted(a, key=lambda x: int(ipaddress.ip_address(x)))

    raise JinjaFx.TemplateError("'ipsort' filter requires a list")

  def __summarize_address_range(self, r):
    start, end = r.split('-', 2)
    clist = ipaddress.summarize_address_range(ipaddress.ip_address(start.strip()), ipaddress.ip_address(end.strip()))
    return list(map(str, clist))

  def __xpath(self, s_xml, s_path):
    if lxml:
      s_xml = re.sub(r'>\s+<', '><', s_xml.strip())
      p_xml = etree.fromstring(s_xml, parser=etree.XMLParser(remove_comments=True, remove_pis=True))
      nsmap = {}

      for k in p_xml.nsmap:
        if k is not None:
          nsmap[k] = p_xml.nsmap[k]
      
      xml = p_xml.xpath(s_path, namespaces=nsmap)

      r = []
      for x in xml:
        if isinstance(x, str):
          r.append(x.strip())
        else:
          r.append(etree.tostring(x, pretty_print=True).decode('utf-8').strip())
      return r

    else:
      raise JinjaFx.TemplateError("'xpath' filter requires the 'lxml' python module")

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

