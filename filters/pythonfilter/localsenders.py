#!/usr/bin/python
# localsenders -- Courier filter which validates sender addresses, if they are local
# Copyright (C) 2007-2008  Gordon Messmer <gordon@dragonsdawn.net>
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
import courier.authdaemon
import courier.config
import courier.control


require_auth = False


def init_filter():
    courier.config.apply_module_config('localsenders.py', globals())
    # Record in the system log that this filter was initialized.
    sys.stderr.write('Initialized the "localsenders" python filter\n')


def do_filter(body_path, control_paths):
    """Validate sender addresses, if their domain is locally hosted."""
    try:
        sender = courier.control.get_sender(control_paths)
    except:
        return '451 Internal failure locating control files'
    sparts = sender.split('@')
    if len(sparts) != 2:
        return ''

    if courier.config.is_local(sparts[1]):
        sender_info = courier.authdaemon.get_user_info('smtp', sparts[0])
    elif courier.config.is_hosteddomain(sparts[1]):
        sender_info = courier.authdaemon.get_user_info('smtp', sender)
    else:
        # Short circuit return for non-local senders
        return ''

    if sender_info is None:
        return '517 Sender does not exist: %s' % sender
    if (require_auth and
            courier.control.get_auth_user(control_paths, body_path) is None):
        return '517 Policy requires local senders to authenticate.'
    return ''


if __name__ == '__main__':
    # For debugging, you can create a file or set of files that
    # mimics the Courier control file set.
    if not sys.argv[1:]:
        print('Use:  localsenders.py <control file>')
        sys.exit(1)
    init_filter()
    print(do_filter('', sys.argv[1:]))
