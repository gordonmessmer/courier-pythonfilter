#!/usr/bin/python3

from setuptools import setup


long_description = """pythonfilter is a collection of useful filters for the Courier MTA,
and a framework for developing new filters in Python.

pythonfilter can be used to filter spam and viruses, as well as
implement other local mail policies.
"""

setup(name="courier-pythonfilter",
      version="3.0.6",
      description="Python filtering architecture for the Courier MTA.",
      long_description=long_description,
      author="Gordon Messmer",
      author_email="gordon@dragonsdawn.net",
      url="https://github.com/gordonmessmer/courier-pythonfilter",
      license="GPL",
      scripts=['pythonfilter', 'pythonfilter-quarantine', 'dropmsg'],
      packages=['courier', 'pythonfilter'],
      package_dir={'pythonfilter': 'filters/pythonfilter'},
      data_files=[('/etc/', ['pythonfilter.conf',
                             'pythonfilter-modules.conf'])]
      )
