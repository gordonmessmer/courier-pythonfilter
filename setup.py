#!/usr/bin/python

import glob
import os
import sys
from distutils.core import setup

setup(name="courier-pythonfilter",
      version="0.25",
      description="Python filtering architecture for the Courier MTA.",
      author="Gordon Messmer",
      author_email="gordon@dragonsdawn.net",
      url="http://www.dragonsdawn.net/~gordon/courier-patches/courier-pythonfilter/",
      license="GPL",
      scripts=['pythonfilter'],
      packages=['courier', 'pythonfilter'],
      package_dir = {'pythonfilter': 'filters'},
      data_files=[('/etc/', ['pythonfilter.conf', 
                             'pythonfilter-modules.conf'])]
     )
