"""Use the OS certificate store for HTTPS on Windows.

The Microsoft Store Python build ships with certifi, but requests/urllib3
prefer that bundle over Windows trust roots. On machines behind SSL
inspection (or with incomplete certifi bundles), OAuth calls to Google
fail with CERTIFICATE_VERIFY_FAILED. truststore delegates verification
to the platform store instead.
"""

import sys

# Reconfigure stdout and stderr to UTF-8 to prevent UnicodeEncodeError when printing emojis on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

