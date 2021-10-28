#!/usr/bin/env python3

# Vaulty - Encrypt/Decrypt with ChaCha20-Poly1305
# Copyright (c) 2021 Chris Mason <chris@netnix.org>
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

import sys, os, base64, getpass
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.exceptions import InvalidTag

class Vaulty():
  def __init__(self):
    self.__version__ = '1.0.0'
    self.__prefix = b'$VAULTY;'
    self.__kcache = {}

  def __derive_key(self, password, salt=None):
    ckey = (password, salt)
  
    if ckey in self.__kcache:
      return self.__kcache[ckey]
  
    if salt is None:
      salt = os.urandom(16)
      
    key = Scrypt(salt, 32, 2**16, 8, 1).derive(password)
    self.__kcache[ckey] = [salt, key]
    return salt, key
  
  def encrypt(self, plaintext, password, cols=None):
    salt, key = self.__derive_key(password)
    nonce = os.urandom(12)
    ciphertext = ChaCha20Poly1305(key).encrypt(nonce, plaintext, None)
    r = self.__prefix + base64.b64encode(b'\x01' + salt + nonce + ciphertext)

    if cols is not None:
      r = b'\n'.join([r[i:i + cols] for i in range(0, len(r), cols)])

    return r + b'\n'
  
  def decrypt(self, ciphertext, password):
    try:
      ciphertext = ciphertext.strip()
      if ciphertext.startswith(self.__prefix):
        ciphertext = base64.b64decode(ciphertext[8:])
        if ciphertext.startswith(b'\x01') and len(ciphertext) > 29:
          key = self.__derive_key(password, ciphertext[1:17])[1]
          return ChaCha20Poly1305(key).decrypt(ciphertext[17:29], ciphertext[29:], None)

    except InvalidTag:
      pass

  def encrypt_file(self, filepath, password, cols=None):
    with open(filepath, 'rb') as fh:
      ciphertext = self.encrypt(fh.read(), password, cols)

    if ciphertext is not None:
      with open(filepath, 'wb') as fh:
        return fh.write(ciphertext)

  def decrypt_file(self, filepath, password):
    with open(filepath, 'rb') as fh:
      plaintext = self.decrypt(fh.read(), password)

    if plaintext is not None:
      with open(filepath, 'wb') as fh:
        return fh.write(plaintext)


def args():
  if len(sys.argv) >= 2:
    m = sys.argv[1].lower()
    if m == 'encrypt' or m == 'decrypt':
      if len(sys.argv) == 2 or all([os.path.isfile(f) for f in sys.argv[2:]]):
        return m

def main(m=args(), cols=80):
  if m is not None:
    if len(sys.argv) == 2:
      data = sys.stdin.read().encode('utf-8')

    password = getpass.getpass('enter password: ').encode('utf-8')
    if len(password) > 0:
      v = Vaulty()

      if m == 'encrypt':
        if password == getpass.getpass('verify password: ').encode('utf-8'):
          if len(sys.argv) == 2:
            print(v.encrypt(data, password, cols).decode('utf-8'), flush=True, end='')
      
          else:
            print()
            for f in sys.argv[2:]:
              print('encrypting ' + f + '... ', flush=True, end='')
              v.encrypt_file(f, password, cols)
              print('ok')
  
        else:
          print('error: password verification failed', file=sys.stderr)
  
      elif m == 'decrypt':
        if len(sys.argv) == 2:
          plaintext = v.decrypt(data, password)
          if plaintext is not None:
            print(plaintext.decode('utf-8'), flush=True, end='')
  
          else:
            print('error: invalid password or data not encrypted', file=sys.stderr)
  
        else:
          print()
          for f in sys.argv[2:]:
            print('decrypting ' + f + '... ', flush=True, end='')
            if v.decrypt_file(f, password) is None:
              print('failed\nerror: invalid password or file not encrypted', file=sys.stderr)

            else:
              print('ok')

    else:
      print('error: password is mandatory', file=sys.stderr)

  else:
    print('usage: vaulty encrypt|decrypt [file1[ file2[ ...]]]', file=sys.stderr)


if __name__ == '__main__':
  try:
    main()

  except KeyboardInterrupt:
    pass
