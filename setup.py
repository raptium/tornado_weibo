#!/usr/bin/env python
import distutils.core
import sys
# Importing setuptools adds some features like "setup.py develop", but
# it's optional so swallow the error if it's not there.
try:
    import setuptools
except ImportError:
    pass

kwargs = {}

version = "0.1dev"
major, minor = sys.version_info[:2]
if major >= 3:
    import setuptools  # setuptools is required for use_2to3
    kwargs["use_2to3"] = True

distutils.core.setup(
    name="tornado_weibo",
    version=version,
    packages = ["tornado_weibo"],
    package_data = {
        "tornado_weibo": ["ca-certificates.crt"],
        },
    author="GUAN Hao",
    author_email="raptium@gmail.com",
    url="http://www.raptium.net/",
    license="http://www.apache.org/licenses/LICENSE-2.0",
    description="Weibo OAuth2 mixin for Tornado web framework",
    requires=["tornado (>=2.0)"],
    **kwargs
)