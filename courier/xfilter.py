# courier.xfilter -- python module for modifying messages in the queue
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

import email
# Compatibility with email version 3:
# http://docs.python.org/lib/email-pkg-history.html
try:
    import email.Generator
    email.generator = email.Generator
except ImportError:
    import email.generator
import courier.control
import courier.config
from email.policy import EmailPolicy


class XFilterError(Exception):
    pass


class InitError(XFilterError):
    pass


class XFilter:
    """Modify messages in the Courier spool.

    This class will load a specified message from Courier's spool and
    allow you to modify it.  This is implemented by loading the
    message as an email.Message object which will be resubmitted to
    the spool.  If the new message is submitted, the original message
    will be marked completed.  If the new message is not submitted,
    no changes will be made to the original message.

    Arguments:
    filter_name -- a name identifying the filter calling this class
    body_path -- the same argument given to the doFilter function
    control_paths -- the same argument given to the doFilter function

    The class will raise xfilter.InitError when instantiated if it
    cannot open the body_path or any of the control files.

    After creating an instance of this class, use the get_message
    method to get the email.Message object created from the body_path.
    Make any modifications required using the normal python functions
    usable with that object.

    When modifications are complete, call the XFilter object's submit
    method to insert the new message into the spool.

    """
    def __init__(self, filter_name, body_path, control_paths):
        try:
            with open(body_path, 'rb') as body_file:
                self.message = email.message_from_binary_file(body_file, policy=EmailPolicy(refold_source="none"))
        except Exception as e:
            raise InitError('Internal failure parsing message data file: %s' % str(e))
        # Save the arguments
        self.filter_name = filter_name
        self.body_path = body_path
        self.control_paths = control_paths
        # Parse the control files and save their data
        self.control_data = courier.control.get_control_data(control_paths)

    def get_message(self):
        return self.message

    def set_message(self, message):
        self.message = message

    def get_control_data(self):
        return self.control_data

    def submit(self):
        bfo = open(self.body_path, 'r+b')
        bfo.truncate(0)
        g = email.generator.BytesGenerator(bfo, mangle_from_=False)
        g.flatten(self.message)
        # Make sure that the file ends with a newline, or courier
        # will choke on the new message file.
        bfo.seek(0, 2)
        bfo.seek(bfo.tell() - 1, 0)
        if bfo.read(1) != b'\n':
            bfo.seek(0, 2)
            bfo.write(b'\n')
        bfo.close()
        return ''

    # Deprecated names preserved for compatibility with older releases
    getMessage = get_message
    setMessage = set_message
    getControlData = get_control_data


class DummyXFilter(XFilter):
    def submit(self):
        return ''
