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

import json


class Track:
    """
    Represents an individual track on Amazon Music. This will be returned from
    one of the other calls and cannot be created directly.

    Key properties are:

    * `name` - Track name
    * `artist` - Track artist
    * `album` - Album containing the track
    * `albumArtist` - Primary artist for the album
    * `coverUrl` - URL containing cover art for the track/album.
    * `streamUrl` - URL of M3U playlist allowing the track to be streamed.
    """

    def __init__(self, amzn, data):
        """
        Internal use only.

        :param amzn: AmazonMusic object, used to make API calls.
        :param data: JSON data structure for the track, from Amazon Music.
                     Supported data structures are from `mpqs` and `muse`.
        """
        try:
            self._amzn = amzn
            self._url = None

            self.json = data
            self.name = data.get('name') or data['title']
            self.artist = data.get('artistName') or data['artist']['name']
            self.album = data['album'].get('name') or data['album'].get(
                'title')
            self.album_artist = data['album'].get(
                'artistName') or data['album'].get('albumArtistName',
                                                   self.artist)

            self.cover_url = None
            if 'artUrlMap' in data:
                self.cover_url = data['artUrlMap'].get(
                    'FULL', data['artUrlMap'].get('LARGE'))
            elif 'image' in data['album']:
                self.cover_url = data['album']['image']

            if 'identifierType' in data:
                self.identifier_type = data['identifierType']
                self.identifier = data['identifier']
            else:
                self.identifier_type = 'ASIN'
                self.identifier = data['asin']

            self.duration = data.get('durationInSeconds', data.get('duration'))

        except KeyError as e:
            e.args = ('{} not found in {}'.format(
                e.args[0], json.dumps(data, sort_keys=True)),)
            raise

    def url(self):
        """
        Return the URL for an M3U playlist for the track, allowing it to be streamed.
        The playlist seems to consist of individual chunks of the song, in ~10s segments,
        so a player capable of playing playlists seamless is required, such as VLC.
        """
        if self._url is None:
            stream_json = self._amzn.call(
                'dmls/',
                'com.amazon.digitalmusiclocator.DigitalMusicLocatorServiceExternal.getRestrictedStreamingURL',
                {
                    'customerId': self._amzn.customer_id,
                    'deviceToken': {
                        'deviceTypeId': self._amzn.device_type,
                        'deviceId': self._amzn.device_id,
                    },
                    'appMetadata': {
                        'https': 'true'
                    },
                    'clientMetadata': {
                        'clientId': 'WebCP',
                    },
                    'contentId': {
                        'identifier': self.identifier,
                        'identifierType': self.identifier_type,
                        'bitRate': 'HIGH',
                        'contentDuration': self.duration
                    }
                })

            if 'statusCode' in stream_json and stream_json['statusCode'] == 'MAX_CONCURRENCY_REACHED':
                raise Exception(stream_json['statusCode'])

            try:
                self._url = stream_json['contentResponse']['urlList'][0]
            except KeyError as e:
                e.args = ('{} not found in {}'.format(
                    e.args[0], json.dumps(stream_json, sort_keys=True)),)
                raise

        return self._url
