#!/usr/bin/python
# attachments -- Courier filter which blocks specified attachment types
# Copyright (C) 2005-2008  Robert Penz <robert@penz.name>
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

import os
import sys
import re
import email.header
import tempfile
import courier.config
try:
    import libarchive
    HAVE_LIBARCHIVE = True
except ImportError:
    HAVE_LIBARCHIVE = False


blocked_pattern = re.compile(r'^.*\.(scr|exe|com|bat|pif|lnk|sys|mid|vb|js|ws|shs|ceo|cmd|cpl|hta|vbs)$', re.I)


def init_filter():
    config = courier.config.get_module_config('attachments.py')
    if 'blocked_pattern' in config:
        # blocked_pattern in configuration file should be only the
        # regular expression.  We recompile it here.
        global blocked_pattern
        blocked_pattern = re.compile(config['blocked_pattern'], re.I)
    # Record in the system log that this filter was initialized.
    sys.stderr.write('Initialized the "attachments" python filter\n')


def check_archive(filename, part):
    if not HAVE_LIBARCHIVE:
        return False
    tmp_d = tempfile.mkdtemp()
    tmp_path = '%s/scan-archive' % (tmp_d,)
    tmp_file = open(tmp_path, 'wb')
    tmp_file.write(part.get_payload(decode=True))
    tmp_file.close()
    found = False
    try:
        with libarchive.file_reader(tmp_path) as archive:
            for entry in archive:
                if blocked_pattern.match(entry.pathname):
                    found = True
    except libarchive.exception.ArchiveError:
        pass
    os.unlink(tmp_path)
    os.rmdir(tmp_d)
    return found


def do_filter(body_path, control_paths):
    try:
        with open(body_path, 'rb') as body_file:
            msg = email.message_from_binary_file(body_file)
    except Exception as e:
        return "554 " + str(e)

    for part in msg.walk():
        # multipart/* are just containers
        if part.get_content_maintype() == 'multipart':
            continue

        filename = part.get_filename()
        if not filename:
            continue
        if isinstance(filename, str):
            filename = str(email.header.make_header(email.header.decode_header(filename)))

        if check_archive(filename, part):
            return "554 The extension of the attached file is blacklisted"

        if blocked_pattern.match(filename):
            return "554 The extension of the attached file is blacklisted"

    return ''


if __name__ == '__main__':
    # For debugging, you can create a file that contains a message
    # body, possibly including attachments.
    # Run this script with the name of that file as an argument,
    # and it'll print either a permanent failure code to indicate
    # that the message would be rejected, or print nothing to
    # indicate that the remaining filters would be run.
    if len(sys.argv) != 2:
        print("Usage: attachments.py <message_body_path>")
        sys.exit(0)
    init_filter()
    print(do_filter(sys.argv[1], []))
