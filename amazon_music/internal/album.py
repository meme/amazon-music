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


class Album:
    """
    Represents a streamable, playable album. This should be created with
    `AmazonMusic.getAlbum`.

    Key properties are:

    * `id` - ID of the album (Amazon ASIN)
    * `name` - Album name.
    * `artist` - Album artist name.
    * `coverUrl` - URL containing cover art for the album.
    * `genre` - Genre of the album.
    * `rating` - Average review score (out of 5).
    * `trackCount` - Number of tracks.
    * `releaseDate` - UNIX timestamp of the original release date.
    * `tracks` - Iterable generator for the `Tracks` that make up this station.
    """

    def __init__(self, amzn, data):
        """
        Internal use only.

        :param amzn: AmazonMusic object, used to make API calls.
        :param data: JSON data structure for the album, from Amazon Music. Supports both `muse` and `cirrus` formats.
        """
        self._amzn = amzn
        self.json = data

        if 'metadata' in data:
            self.track_count = data['numTracks']
            self.json = data['metadata']

            data = self.json

            self.id = data['albumAsin']
            self.cover_url = data.get('albumCoverImageFull',
                                      data.get('albumCoverImageMedium'))
            self.name = data['albumName']
            self.artist = data['albumArtistName']
            self.genre = data['primaryGenre']
            self.rating = None
            self.release_date = None
        else:
            self.id = data['asin']
            self.cover_url = data['image']
            self.name = data['title']
            self.artist = data['artist']['name']
            self.genre = data['productDetails'].get('primaryGenreName')
            self.rating = data['reviews']['average']
            self.track_count = data['trackCount']
            self.release_date = data['originalReleaseDate'] / 1000

    def tracks(self):
        """
        Provide the list for the `Tracks` that make up this album.
        """
        # If we've only got a summary, load the full data
        if 'tracks' not in self.json:
            a = self._amzn.album(self.id)
            self.__init__(self._amzn, a.json)

        return list([Track(self._amzn, t) for t in self.json['tracks']])
