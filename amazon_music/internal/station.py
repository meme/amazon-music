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


class Station:
    """
    Represents a streamable, unending station. This should be created with `AmazonMusic.createStation`.

    Key properties are:

    * `id` - ID of the station (Amazon ASIN)
    * `name` - Name of the station.
    * `coverUrl` - URL containing cover art for the station.
    * `tracks` - Iterable generator for the `Tracks` that make up this station.
    """

    def __init__(self, amzn, asin, data):
        """
        Internal use only.

        :param amzn: AmazonMusic object, used to make API calls.
        :param asin: Station ASIN.
        :param data: JSON data structure for the station, from Amazon Music.
        """
        self._amzn = amzn
        self.id = asin
        self.json = data
        self.cover_url = data['queue']['queueMetadata']['imageUrlMap']['FULL']
        self.name = data['queue']['queueMetadata']['title']
        self._page_token = data['queue']['pageToken']

    def tracks(self):
        """
        Provides an iterable generator for the `Tracks` that make up this station.
        """
        tracks = []
        tracks.extend(self.json['trackMetadataList'])
        while tracks:
            yield Track(self._amzn, tracks.pop(0))

            if not tracks:
                data = self._amzn.call(
                    'mpqs/voiceenabled/getNextTracks',
                    'com.amazon.musicplayqueueservice.model.client.external.voiceenabled.MusicPlayQueueService'
                    'ExternalVoiceEnabledClient.getNextTracks', {
                        'pageToken': self._page_token,
                        'numberOfTracks': 10,
                        'customerInfo': {
                            'deviceId': self._amzn.device_id,
                            'deviceType': self._amzn.device_type,
                            'musicTerritory': self._amzn.territory,
                            'customerId': self._amzn.customer_id
                        }
                    })
                self._page_token = data['nextPageToken']
                tracks.extend(data['trackMetadataList'])
