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
import os
import requests
import re

from bs4 import BeautifulSoup
from http.cookiejar import LWPCookieJar, Cookie

from .internal import Album, Playlist, Station, Track

AMAZON_MUSIC_SUBSCRIPTION = 'MUSIC_SUBSCRIPTION'
AMAZON_PRIME_SUBSCRIPTION = 'PRIME'

AMAZON_MUSIC_URL = 'https://music.amazon.com'
AMAZON_SIGN_IN_PATH = '/ap/signin'
AMAZON_FORCE_SIGN_IN_PATH = '/gp/dmusic/cloudplayer/forceSignIn'
COOKIE_AMAZON_TARGET = '_AmazonMusic-targetUrl'
USER_AGENT = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0'

REGION_MAP = {'USAmazon': 'NA', 'EUAmazon': 'EU', 'FEAmazon': 'FE'}


class AmazonMusic:
    """
    Allows interaction with the Amazon Music service through a programmatic
    interface.

    Usage:

      >>> from amazon_music import AmazonMusic
      >>> from getpass import getpass
      >>> amzn = AmazonMusic(credentials = lambda: [input('Email: '), getpass('Amazon password: ')])
    """

    def __init__(self, email=None, password=None, cookie_cache_path=None, prime=True):
        """
        Constructs and returns an :class:`AmazonMusic <AmazonMusic>` class. This
        will use a cookie jar stored, by default, in the home directory.

        :param email: (required) Amazon account email used for the account.
        :param password: (required) Amazon account password used for the account (not stored on disk).
        :param cookie_cache_path: (optional) File path to be used for the cookie jar.
        :param prime: (optional) Whether or not the user is an Amazon Music Prime member
        """

        if prime:
            self._amazon_subscription = AMAZON_PRIME_SUBSCRIPTION
        else:
            self._amazon_subscription = AMAZON_MUSIC_SUBSCRIPTION

        # Compute cache path, or use current directory
        current_dir = os.path.dirname(os.path.realpath(__file__))
        _cookie_cache_path = cookie_cache_path or '{}/.amzn.cookies'.format(
            os.environ.get('HOME', os.environ.get('LOCALAPPDATA', current_dir)))

        # Create a request session (with cookies)
        self.session = requests.Session()
        self.session.cookies = LWPCookieJar(_cookie_cache_path)

        # Load cookies from disk
        if os.path.isfile(_cookie_cache_path):
            self.session.cookies.load()

        # Check if the Amazon region is already stored in the cache
        target_region_cookie = next((c for c in self.session.cookies if c.name == COOKIE_AMAZON_TARGET), None)

        # If the target is not available, create one (this will be filled with the proper region)
        if target_region_cookie is None:
            target_region_cookie = Cookie(1, COOKIE_AMAZON_TARGET, AMAZON_MUSIC_URL, '0', False, ':invalid', True, ':invalid', '',
                            False, True, 2147483647, False, None, None, {})

        # Fetch the homepage, authenticate if needed
        self._email = email
        self._password = password

        r = self.session.get(
            target_region_cookie.value, headers={'User-Agent': USER_AGENT})

        # Save cookies to disk (and ensure permissions are correct)
        self.session.cookies.save()
        os.chmod(_cookie_cache_path, 0o600)

        # Zero out the site configuration
        amzn_music_config = None
        while amzn_music_config is None:
            # If we keep getting bounced around, authenticate
            while r.history and any(h.status_code == 302
                                    and AMAZON_SIGN_IN_PATH in h.headers['Location']
                                    for h in r.history):
                r = self._authenticate(r)

            # Read the JSON object from the HTML page (XXX find a better solution)
            for line in r.iter_lines(decode_unicode=True):
                if 'amznMusic.appConfig = ' in line:
                    amzn_music_config = json.loads(
                        re.sub(r'^[^{]*', '', re.sub(r';$', '', line)))
                    break

            if amzn_music_config is None:
                raise Exception("Amazon Music `appConfig` could not be found (you may have triggered the captcha)")

            if amzn_music_config['isRecognizedCustomer'] == 0:
                r = self.session.get(
                    AMAZON_MUSIC_URL + AMAZON_FORCE_SIGN_IN_PATH,
                    headers={'User-Agent': USER_AGENT})

                amzn_music_config = None

        # Zero out the credentials so that they may not be accessed later
        self._email = None
        self._password = None

        self.device_id = amzn_music_config['deviceId']
        self.csrf_token = amzn_music_config['CSRFTokenConfig']['csrf_token']
        self.csrf_ts = amzn_music_config['CSRFTokenConfig']['csrf_ts']
        self.csrf_rnd = amzn_music_config['CSRFTokenConfig']['csrf_rnd']
        self.customer_id = amzn_music_config['customerId']
        self.device_type = amzn_music_config['deviceType']
        self.territory = amzn_music_config['musicTerritory']
        self.locale = amzn_music_config['i18n']['locale']
        self.region = REGION_MAP.get(amzn_music_config['realm'],
                                     amzn_music_config['realm'][:2])
        self.url = 'https://' + amzn_music_config['serverInfo']['returnUrlServer']

        target_region_cookie.value = self.url

        # Store the target region inside the cookie (and write it to disk)
        self.session.cookies.set_cookie(target_region_cookie)
        self.session.cookies.save()

    def _authenticate(self, r):
        """
        Handles the sign-in process with Amazon's login page.

        :param r: The response object pointing to the Amazon sign in page.
        """
        soup = BeautifulSoup(r.content, "html.parser")

        query = {"email": self._email, "password": self._password}

        # For each input
        for field in soup.form.find_all("input"):
            # If it is a hidden value (i.e.: CSRF data or temporary session variables)
            if field.get("type") == "hidden":
                # Set them in the query
                query[field.get("name")] = field.get("value")

        # Post the data using the `action` embedded inside the <form>
        r = self.session.post(
            soup.form.get("action"),
            headers={
                'User-Agent':
                    USER_AGENT,
                'Referer':
                    r.history[0].headers['Location'],
                'Upgrade-Insecure-Requests':
                    '1',
                'Accept':
                    'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language':
                    'en-US,en;q=0.9'
            },
            data=query)

        # Save cookies to disk
        self.session.cookies.save()

        return r

    def call(self, endpoint, target, query):
        """
        Make a call against an endpoint and return the JSON response.

        :param endpoint: The URL endpoint of the request.
        :param target: The (Java?) class of the API to invoke.
        :param query: The JSON request.
        """
        query_headers = {
            'User-Agent': USER_AGENT,
            'csrf-token': self.csrf_token,
            'csrf-rnd': self.csrf_rnd,
            'csrf-ts': self.csrf_ts,
            'X-Requested-With': 'XMLHttpRequest'
        }
        if target is None:  # Legacy cirrus API
            query_data = query
        else:
            query_headers['X-Amz-Target'] = target
            query_headers['Content-Type'] = 'application/json'
            query_headers['Content-Encoding'] = 'amz-1.0'
            query_data = json.dumps(query)

        r = self.session.post(
            '{}/{}/api/{}'.format(self.url, self.region, endpoint),
            headers=query_headers,
            data=query_data)
        self.session.cookies.save()
        return r.json()

    def station(self, id):
        """
        Create a station that can be played.

        :param id: Station ID, for example `A2UW0MECRAWILL`.
        """
        return Station(
            self, id,
            self.call(
                'mpqs/voiceenabled/createQueue',
                'com.amazon.musicplayqueueservice.model.client.external.voiceenabled.MusicPlayQueueServiceExternal'
                'VoiceEnabledClient.createQueue', {
                    'identifier': id,
                    'identifierType': 'STATION_KEY',
                    'customerInfo': {
                        'deviceId': self.device_id,
                        'deviceType': self.device_type,
                        'musicTerritory': self.territory,
                        'customerId': self.customer_id
                    }
                }))

    def album(self, id):
        """
        Get an album that can be played.

        param albumId: Album ID, for example `B00J9AEZ7G`.
        """
        return Album(
            self,
            self.call(
                'muse/legacy/lookup',
                'com.amazon.musicensembleservice.MusicEnsembleService.lookup',
                {
                    'asins': [id],
                    'features': [
                        'popularity', 'expandTracklist',
                        'trackLibraryAvailability',
                        'collectionLibraryAvailability'
                    ],
                    'requestedContent':
                        self._amazon_subscription,
                    'deviceId':
                        self.device_id,
                    'deviceType':
                        self.device_type,
                    'musicTerritory':
                        self.territory,
                    'customerId':
                        self.customer_id
                })['albumList'][0])

    def albums_in_library(self):
        """
        Return albums that are in the library. Amazon considers all albums,
        however this filters the list to albums with only four or more items.
        """
        query = {
            'Operation': 'searchLibrary',
            'ContentType': 'JSON',
            'searchReturnType': 'ALBUMS',
            'searchCriteria.member.1.attributeName': 'status',
            'searchCriteria.member.1.comparisonType': 'EQUALS',
            'searchCriteria.member.1.attributeValue': 'AVAILABLE',
            'searchCriteria.member.2.attributeName': 'trackStatus',
            'searchCriteria.member.2.comparisonType': 'IS_NULL',
            'searchCriteria.member.2.attributeValue': None,
            'albumArtUrlsSizeList.member.1': 'FULL',
            'selectedColumns.member.1': 'albumArtistName',
            'selectedColumns.member.2': 'albumName',
            'selectedColumns.member.3': 'artistName',
            'selectedColumns.member.4': 'objectId',
            'selectedColumns.member.5': 'primaryGenre',
            'selectedColumns.member.6': 'sortAlbumArtistName',
            'selectedColumns.member.7': 'sortAlbumName',
            'selectedColumns.member.8': 'sortArtistName',
            'selectedColumns.member.9': 'albumCoverImageFull',
            'selectedColumns.member.10': 'albumAsin',
            'selectedColumns.member.11': 'artistAsin',
            'selectedColumns.member.12': 'gracenoteId',
            'sortCriteriaList': None,
            'maxResults': 100,
            'nextResultsToken': None,
            'caller': 'getAllDataByMetaType',
            'sortCriteriaList.member.1.sortColumn': 'sortAlbumName',
            'sortCriteriaList.member.1.sortType': 'ASC',
            'customerInfo.customerId': self.customer_id,
            'customerInfo.deviceId': self.device_id,
            'customerInfo.deviceType': self.device_type,
        }

        data = self.call('cirrus/', None,
                         query)['searchLibraryResponse']['searchLibraryResult']
        results = []
        results.extend(data['searchReturnItemList'])
        while results:
            r = results.pop(0)
            if r['numTracks'] >= 4 and r['metadata'].get(
                    'primeStatus') == 'PRIME':
                yield Album(self, r)

            if not results and data['nextResultsToken']:
                query['nextResultsToken'] = data['nextResultsToken']
                data = self.call(
                    'cirrus/', None,
                    query)['searchLibraryResponse']['searchLibraryResult']
                results.extend(data['searchReturnItemList'])

    def playlist(self, id):
        """
        Get a playlist that can be played.

        :param id: Playlist ID, for example `B075QGZDZ3`.
        """
        return Playlist(
            self,
            self.call(
                'muse/legacy/lookup',
                'com.amazon.musicensembleservice.MusicEnsembleService.lookup',
                {
                    'asins': [id],
                    'features': [
                        'popularity', 'expandTracklist',
                        'trackLibraryAvailability',
                        'collectionLibraryAvailability'
                    ],
                    'requestedContent':
                        self._amazon_subscription,
                    'deviceId':
                        self.device_id,
                    'deviceType':
                        self.device_type,
                    'musicTerritory':
                        self.territory,
                    'customerId':
                        self.customer_id
                })['playlistList'][0])

    def search(self,
               query,
               library_only=False,
               tracks=True,
               albums=True,
               playlists=True,
               artists=True,
               stations=True):
        """
        Search Amazon Music for the given query, and return matching results
        (playlists, albums, tracks and artists).

        This is still a work-in-progress, and at the moment the raw Amazon Music
        native data structure is returned.

        :param query: Query.
        :param library_only (optional) Limit to the user's library only, rather than the library + Amazon Music.
               Defaults to false.
        :param tracks: (optional) Include tracks in the results, defaults to true.
        :param albums: (optional) Include albums in the results, defaults to true.
        :param playlists: (optional) Include playlists in the results, defaults to true.
        :param artists: (optional) Include artists in the results, defaults to true.
        :param stations: (optional) Include stations in the results, defaults to true - only makes sense if
               `library_only` is false.
        """
        query_obj = {
            'deviceId': self.device_id,
            'deviceType': self.device_type,
            'musicTerritory': self.territory,
            'customerId': self.customer_id,
            'languageLocale': self.locale,
            'requestContext': {
                'customerInitiated': True
            },
            'query': {},
            'resultSpecs': []
        }

        # -- Set up the search object...
        #
        if library_only:

            def _set_q(q):
                query_obj['query'] = q
        else:
            query_obj['query'] = {
                '__type':
                    'com.amazon.music.search.model#BooleanQuery',
                'must': [{}],
                'should': [{
                    '__type':
                        'com.amazon.music.search.model#TermQuery',
                    'fieldName':
                        'primeStatus',
                    'term':
                        'PRIME'
                }]
            }

            def _set_q(q):
                query_obj['query']['must'][0] = q

        # -- Set up the query...
        #
        if query is None:
            _set_q({
                '__type': 'com.amazon.music.search.model#ExistsQuery',
                'fieldName': 'asin'
            })
        else:
            _set_q({
                '__type': 'com.amazon.music.search.model#MatchQuery',
                'query': query
            })

        def _add_result_spec(**kwargs):
            for type_ in kwargs:
                if kwargs[type_]:

                    def result_spec(n):
                        return {
                            'label':
                                '{}s'.format(
                                    n),  # Before it was %ss, is {}s right?
                            'documentSpecs': [{
                                'type':
                                    n,
                                'fields': [
                                    '__DEFAULT', 'artFull', 'fileExtension',
                                    'isMusicSubscription', 'primeStatus'
                                ]
                            }],
                            'maxResults':
                                30
                        }

                    if type_ != 'station':
                        query_obj['resultSpecs'].append(
                            result_spec('library_{}'.format(type_)))
                    if not library_only:
                        query_obj['resultSpecs'].append(
                            result_spec('catalog_{}'.format(type_)))

        _add_result_spec(
            track=tracks,
            album=albums,
            playlist=playlists,
            artist=artists,
            station=stations)

        # TODO Convert into a better data structure
        # TODO There seems to be a paging token
        return list(
            [[r['label'], r] for r in self.call(
                'search/v1_1/',
                'com.amazon.tenzing.v1_1.TenzingServiceExternalV1_1.search',
                query_obj)['results']])