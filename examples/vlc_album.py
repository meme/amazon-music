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

from amazon_music import AmazonMusic
from getpass import getpass
import os, sys

if len(sys.argv) <= 1:
    raise Exception("ASIN was not provided (e.g.: B00LXI93RO)")

amzn = AmazonMusic(email=input("Email: "), password=getpass("Password: "))

album = amzn.album(sys.argv[1])

print("'{}', ({} of 5 rating)".format(album.name, album.rating))
print("(Cover URL can be found at {})".format(album.cover_url))

for t in album.tracks():
    print("{} - {}".format(t.name, t.artist))
    # print("\t{}".format(t.url()))
    os.system("cvlc --play-and-exit {}".format(t.url()))
