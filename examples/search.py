# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import json

from amazon_music import AmazonMusic
from getpass import getpass

am = AmazonMusic()

if len(sys.argv) < 2:
    raise Exception("search term was not provided")

amzn = AmazonMusic(email=input("Email: "), password=getpass("Password: "))

results = amzn.search(' '.join(sys.argv[1:]))
print(json.dumps(results, sort_keys=True, indent=2))
