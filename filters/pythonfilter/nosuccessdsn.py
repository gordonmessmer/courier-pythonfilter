#!/usr/bin/python
# nosuccessdsn -- Courier filter which removes DSNs for success
# Copyright (C) 2004-2008  Gordon Messmer <gordon@dragonsdawn.net>
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

import sys
import courier.control


def init_filter():
    # Record in the system log that this filter was initialized.
    sys.stderr.write('Initialized the "nosuccessdsn" python filter\n')


def do_filter(body_path, control_paths):
    """Remove success DSNs from the control_paths

    Success DSNs are requested by some spammers with invalid return
    addresses.  Why?  I don't know.

    To prevent mail queue backlog as well as guard the privacy of your
    domain, it may be desirable not to send DSNs for successful
    deliveries.  If so, enable this filter.

    """
    rcpts = courier.control.get_recipients_data(control_paths)
    for x in rcpts:
        if 'S' in x[2]:
            newrcpt = x[:]
            newrcpt[2] = ''
            courier.control.add_recipient_data(control_paths, newrcpt)
            courier.control.del_recipient_data(control_paths, x)
    # Return no decision.
    return ''


if __name__ == '__main__':
    # For debugging, you can create a file or set of files that
    # mimics the Courier control file set.
    # Run this script with the name of those files as arguments,
    # and it'll rewrite them with no success DSNs.
    if not sys.argv[1:]:
        print('Use:  nosuccessdsn.py <control file>')
        sys.exit(1)
    init_filter()
    print(do_filter('', sys.argv[1:]))
