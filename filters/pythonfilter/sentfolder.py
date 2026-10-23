#!/usr/bin/python
# sentfolder -- Copies messages sent by local users back to the sender.
# Copyright (C) 2016  Gordon Messmer <gordon@dragonsdawn.net>
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

import email
import email.utils
import sys
import courier.config
import courier.control
import courier.sendmail
from email.policy import EmailPolicy


siteid = '69f7dc20-7aef-420b-a8d2-85ea229f97ba'


def init_filter():
    courier.config.apply_module_config('sentfolder.py', globals())
    # Record in the system log that this filter was initialized.
    sys.stderr.write('Initialized the "sentfolder" python filter\n')


def do_filter(body_path, control_paths):
    sender = courier.control.get_auth_user(control_paths, body_path)
    if not sender:
        return ''

    if '@' not in sender:
        sender = '%s@%s' % (sender, courier.config.me())
    courier.sendmail.sendmail('', sender, makemsg(body_path, control_paths))

    return ''


def makemsg(body_path, control_paths):
    yield ('X-Deliver-To-Sent-Folder: ' + siteid + '\r\n').encode()

    try:
        with open(body_path, 'rb') as body_file:
            msg = email.message_from_binary_file(body_file, policy=EmailPolicy(refold_source="none"))
    except Exception as e:
        raise SystemError('Internal failure parsing message data file: %s' % str(e))
    tos = msg.get_all('to', [])
    ccs = msg.get_all('cc', [])
    resent_tos = msg.get_all('resent-to', [])
    resent_ccs = msg.get_all('resent-cc', [])
    all_recipients = [x[1] for x in email.utils.getaddresses(tos + ccs + resent_tos + resent_ccs)]
    bccs = []
    for recipient in courier.control.get_recipients_data(control_paths):
        if recipient[1]:
            r = recipient[1]
        else:
            r = recipient[0]
        if (r not in all_recipients and
                r not in bccs):
            bccs.append(r)
    if bccs:
        yield ('Bcc: ' + ', '.join(bccs) + '\r\n').encode()

    body_file = open(body_path, 'rb')
    for line in body_file:
        yield line


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: sentfolder.py <body file>")
        sys.exit(1)
    init_filter()
    print(do_filter(sys.argv[1], []))
