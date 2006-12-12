#!/usr/bin/python
# comeagain -- Courier filter implementing a "greylisting" technique.
# Copyright (C) 2006  Gordon Messmer <gordon@dragonsdawn.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import md5
import sys
import string
import time
import courier.control
import TtlDb


# The good/bad senders lists will be scrubbed at the interval indicated
# in seconds.  All records older than the "_sendersTTL" number of seconds
# will be removed from the lists.
_sendersTTL = 60 * 60 * 24 * 30
_sendersPurgeInterval = 60 * 60 * 12

# Keep a dictionary of sender/recipient pairs that we've seen before
try:
    _senders = TtlDb.TtlDb('correspondents', _sendersTTL, _sendersPurgeInterval)
except TtlDb.OpenError, e:
    sys.stderr.write(e.message)
    sys.exit(1)

# Record in the system log that this filter was initialized.
sys.stderr.write('Initialized the "comeagain" python filter\n')


def doFilter(bodyFile, controlFileList):
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
        sender = courier.control.getSender(controlFileList)
    except:
        return '451 Internal failure locating control files'
    if sender == '':
        # Null sender is allowed as a non-fatal error
        return ''

    _senders.purge()

    # Create a new MD5 object.  The pairs of sender/recipient will
    # be stored in the db in the form of an MD5 digest.
    senderMd5 = md5.new(sender)

    # Create a digest for each recipient and look it up in the db.
    # Update the timestamp of each pair as we look them up.  If any
    # pair does not exist, we'll have to ask the sender to deliver
    # again.
    foundAll=1
    _senders.lock()
    for recipient in courier.control.getRecipients(controlFileList):
        correspondents = senderMd5.copy()
        correspondents.update(recipient)
        cdigest = correspondents.hexdigest()
        if not _senders.has_key(cdigest):
            foundAll = 0
        _senders[cdigest] = str(time.time())
    _senders.unlock()

    if foundAll:
        return ''
    else:
        return('421-Please send the message again.\n'
               '421-This is not an indication of a problem:  We require\n'
               '421-that any new sender retry their delivery as proof that\n'
               '421-they are not spamware or virusware.\n'
               '421 Thank you.')


if __name__ == '__main__':
    # For debugging, you can create a file that contains one line,
    # beginning with an 's' character, followed by an email address
    # and more lines, beginning with an 'r' character, for each
    # recipient.  Run this script with the name of that file as an
    # argument, and it'll validate that email address.
    if not sys.argv[1:]:
        print 'Use:  comeagain.py <control file>'
        sys.exit(1)
    print doFilter('', sys.argv[1:])
