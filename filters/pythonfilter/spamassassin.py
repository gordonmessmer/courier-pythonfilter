#!/usr/bin/python
# spamassassin -- Courier filter which scans messages with spamassassin
# Copyright (C) 2007-2008  Jerome Blion <jerome@hebergement-pro.org>
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
import os.path
import subprocess
import sys
import courier.config
import courier.xfilter
from email.policy import EmailPolicy


spamc_path = '/usr/bin/spamc'
# This is the maximum size of a message that we'll try to scan.
# 500 KiB is spamc's default.
max_msg_size = 512000
# If you want to scan messages as a user other than the one as
# which pythonfilter runs, specify the user's name in the modules
# configuration file.
username = None
# If reject_score is set to a number, then the score in the X-Spam-Status
# header will be used to determine whether or not to reject the message.
# Otherwise, messages will be rejected if they are spam.
reject_score = None


def init_filter():
    courier.config.apply_module_config('spamassassin.py', globals())
    # Record in the system log that this filter was initialized.
    sys.stderr.write('Initialized the "spamassasinfilter" python filter\n')


def check_reject_condition(status, result_header):
    if not result_header:
        result_header = ''
    else:
        result_header = result_header.replace('\n', '')
    if reject_score is None or result_header == '':
        # No reject_score is configured or spamassassin is configured not
        # to create new headers, so simply use the exit status of
        # spamc.  If the exit status is not 0, then the message is spam.
        if status != 0:
            return '554 Mail rejected - spam detected: ' + result_header
    elif result_header.startswith('Yes,'):
        # Attempt to load the score from the result_header.
        resultwords = result_header.split()
        for word in resultwords:
            if word.startswith('score='):
                score = float(word[6:])
                if score >= reject_score:
                    return '554 Mail rejected - spam detected: ' + result_header
    return None


def do_filter(body_path, control_paths):
    msg_size = os.path.getsize(body_path)
    if msg_size > max_msg_size:
        return ''

    cmd = [spamc_path, '-s', str(max_msg_size), '-E']
    if username:
        cmd.extend(['-u', username])
    try:
        with open(body_path, 'r') as body_file:
            spamc_proc = subprocess.Popen(cmd, stdin=body_file,
                                          stdout=subprocess.PIPE)
    except Exception as e:
        return "454 " + str(e)

    # Parse the output of spamc into an email.message object.
    result = email.message_from_binary_file(spamc_proc.stdout, policy=EmailPolicy(refold_source="none"))
    result_header = result['X-Spam-Status']

    reject_msg = check_reject_condition(spamc_proc.wait(), result_header)
    if reject_msg is not None:
        return reject_msg

    # If the message wasn't rejected, then replace the message with
    # the output of spamc.
    mfilter = courier.xfilter.XFilter('spamassassin', body_path,
                                      control_paths)
    mfilter.set_message(result)
    submit_val = mfilter.submit()
    return submit_val


if __name__ == '__main__':
    # we only work with 1 parameter
    if len(sys.argv) != 2:
        print("Usage: spamassassin.py <message body file>")
        sys.exit(0)
    init_filter()
    courier.xfilter.XFilter = courier.xfilter.DummyXFilter
    print(do_filter(sys.argv[1], []))
