#!/usr/bin/python
# auto_whitelist -- Courier filter whitelisting recipients of "local" mail
# Copyright (C) 2006-2008  Gordon Messmer <gordon@dragonsdawn.net>
#
# This file is part of pythonfilter.
#
# pythonfilter is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pythonfilter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pythonfilter.  If not, see <http://www.gnu.org/licenses/>.

import hashlib
import sys
import time
import courier.config
import courier.control
from . import ttldb


# The good/bad senders lists will be scrubbed at the interval indicated
# in seconds.  All records older than the "whitelistTTL" number of seconds
# will be removed from the lists.
whitelist_ttl = 60 * 60 * 24 * 30
whitelist_purge_interval = 60 * 60 * 12


def init_filter():
    courier.config.apply_module_config('auto_whitelist.py', globals())
    # Keep a dictionary of sender/recipient pairs that we've seen before
    try:
        global _whitelist
        _whitelist = ttldb.TtlDb('auto_whitelist', whitelist_ttl, whitelist_purge_interval)
    except ttldb.OpenError as e:
        sys.stderr.write('Could not open auto_whitelist TtlDb: %s\n' % e)
        sys.exit(1)
    # Record in the system log that this filter was initialized.
    sys.stderr.write('Initialized the "auto_whitelist" python filter\n')


def whitelist_recipients(control_paths):
    sender = courier.control.get_sender(control_paths).lower()
    sender_md5 = hashlib.md5(sender.encode())
    _whitelist.lock()
    try:
        for recipient in courier.control.get_recipients(control_paths):
            recipient = recipient.lower()
            # Don't allow a whitelist between identical addresses.  Users
            # sometimes email themselves a note, which creates a path for
            # spam.
            if recipient == sender:
                continue
            correspondents = sender_md5.copy()
            correspondents.update(recipient.encode())
            cdigest = correspondents.hexdigest()
            _whitelist[cdigest] = time.time()
    finally:
        _whitelist.unlock()


def check_whitelist(control_paths):
    found_all = 1
    sender = courier.control.get_sender(control_paths).lower()
    _whitelist.lock()
    try:
        for recipient in courier.control.get_recipients(control_paths):
            correspondents = hashlib.md5(recipient.lower().encode())
            correspondents.update(sender.encode())
            cdigest = correspondents.hexdigest()
            if cdigest not in _whitelist:
                found_all = 0
                break
    finally:
        _whitelist.unlock()
    return found_all


def do_filter(body_path, control_paths):
    """Return a 200 code if the message looks like a reply to a message
    sent by an authenticated user.

    First, determine if the sender was authenticated.  If so, record the
    sender/recipient pair.  If not, then check to see if this
    sender/recipient pair was previously whitelisted.

    """

    _whitelist.purge()
    auth_user = courier.control.get_auth_user(control_paths, body_path)
    if auth_user:
        whitelist_recipients(control_paths)
        return ''
    if check_whitelist(control_paths):
        return '200 Ok'
    # Return no decision for everyone else.
    return ''


if __name__ == '__main__':
    # For debugging, you can create a file that contains one line,
    # beginning with an 's' character, followed by an email address
    # and more lines, beginning with an 'r' character, for each
    # recipient.  Run this script with the name of that file as an
    # argument, and it'll validate that email address.
    if len(sys.argv) != 3:
        print('Use:  auto_whitelist.py <body file> <control file>')
        sys.exit(1)
    init_filter()
    print(do_filter(sys.argv[1], sys.argv[2:]))
