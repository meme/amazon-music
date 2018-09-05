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

from .track import Track


class Playlist:
    """
    Represents a streamable, playable playlist. This should be created with `AmazonMusic.getPlaylist`.

    Key properties are:

    * `id` - ID of the album (Amazon ASIN)
    * `name` - Album name.
    * `coverUrl` - URL containing cover art for the album.
    * `genre` - Genre of the album.
    * `rating` - Average review score (out of 5).
    * `trackCount` - Number of tracks.
    * `tracks` - Iterable generator for the `Tracks` that make up this station.
    """

    def __init__(self, amzn, data):
        """
        Internal use only.

        :param amzn: AmazonMusic object, used to make API calls.
        :param data: JSON data structure for the album, from Amazon Music.
        """
        self._amzn = amzn
        self.json = data
        self.id = data['asin']
        self.cover_url = data['image']
        self.name = data['title']
        self.genre = data['primaryGenre']
        self.rating = data['reviews']['average']
        self.track_count = data['trackCount']

    def tracks(self):
        """
        Provide the list for the `Tracks` that make up this album.
        """
        return list([Track(self._amzn, t) for t in self.json['tracks']])
