#!/usr/bin/python
# comeagain -- Courier filter implementing a "greylisting" technique.
# Copyright (C) 2003-2008  Gordon Messmer <gordon@dragonsdawn.net>
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
# in seconds.  All records older than the "senders_ttl" number of seconds
# will be removed from the lists.
senders_ttl = 60 * 60 * 24 * 30
senders_purge_interval = 60 * 60 * 12


def init_filter():
    courier.config.apply_module_config('comeagain.py', globals())
    # Keep a dictionary of sender/recipient pairs that we've seen before
    try:
        global _senders
        _senders = ttldb.TtlDb('correspondents', senders_ttl, senders_purge_interval)
    except ttldb.OpenError as e:
        sys.stderr.write('Could not open comeagain TtlDb: %s\n' % e)
        sys.exit(1)
    # Record in the system log that this filter was initialized.
    sys.stderr.write('Initialized the "comeagain" python filter\n')


def do_filter(body_path, control_paths):
    """Return a temporary failure message if this sender hasn't tried to
    deliver mail previously.

    Search through the control files and discover the envelope sender
    and message recipients.  If the sender has written to these
    recipients before, allow the message.  Otherwise, throw a
    temporary failure, and expect the remote MTA to try again.  Many
    spamware sites and viruses will not, preventing these messages
    from getting into the users' mailbox.

    """

    # Grab the sender from the control files.
    try:
        sender = courier.control.get_sender(control_paths)
    except Exception:
        return '451 Internal failure locating control files'
    if sender == '':
        # Null sender is allowed as a non-fatal error
        return ''

    _senders.purge()

    # Create a new MD5 object.  The pairs of sender/recipient will
    # be stored in the db in the form of an MD5 digest.
    sender_md5 = hashlib.md5(sender.encode())

    # Create a digest for each recipient and look it up in the db.
    # Update the timestamp of each pair as we look them up.  If any
    # pair does not exist, we'll have to ask the sender to deliver
    # again.
    found_all = 1
    _senders.lock()
    try:
        for recipient in courier.control.get_recipients(control_paths):
            correspondents = sender_md5.copy()
            correspondents.update(recipient.encode())
            cdigest = correspondents.hexdigest()
            if cdigest not in _senders:
                found_all = 0
            _senders[cdigest] = time.time()
    finally:
        _senders.unlock()

    if found_all:
        return ''
    return '421 Please send the message again to prove you are not spamware or virusware.'


if __name__ == '__main__':
    # For debugging, you can create a file that contains one line,
    # beginning with an 's' character, followed by an email address
    # and more lines, beginning with an 'r' character, for each
    # recipient.  Run this script with the name of that file as an
    # argument, and it'll validate that email address.
    if not sys.argv[1:]:
        print('Use: comeagain.py <control file>')
        sys.exit(1)
    init_filter()
    print(do_filter('', sys.argv[1:]))
