import hashlib
import pickle
import re
import socket
import ssl
from .compat import get_charset
from .compat import HTTPError
from .compat import OrderedDict
from .compat import Request
from .compat import urlencode
from .compat import URLError
from .compat import urlopen
try:
    import simplejson as json
    try:
        InvalidJson = json.JSONDecodeError
    except AttributeError:
        InvalidJson = ValueError
except ImportError:
    import json
    InvalidJson = ValueError

from micawber.exceptions import InvalidResponseException
from micawber.exceptions import ProviderException
from micawber.exceptions import ProviderNotFoundException


# a dict of dicts.
# the keys are an API endpoint
# the values are a dict of matching regular expression patterns ('re')
# and domains the endpoint serves ('d')
providers_library = {
    # b
    'http://blip.tv/oembed': {
        're': ['http://blip.tv/\S+', ],
        'd': ['blip.tv', ]
    },

    # c
    'http://chirb.it/oembed.json': {
        're': ['http://chirb.it/\S+', ],
        'd': ['chirb.it', ],
    },
    'https://www.circuitlab.com/circuit/oembed': {
        're': ['https://www.circuitlab.com/circuit/\S+', ],
        'd': ['circuitlab.com', ],
    },
    'http://www.collegehumor.com/oembed.json': {
        're': ['http://www.collegehumor.com/video/\S+', ],
        'd': ['collegehumor.com', ],
    },

    # d
    'http://www.dailymotion.com/services/oembed': {
        're': ['https?://(www\.)?dailymotion\.com/\S+', ],
        'd': ['dailymotion.com', ],
    },

    # f
    'https://www.flickr.com/services/oembed/': {
        're': ['https?://\S*?flickr.com/\S+',
               'https?://flic\.kr/\S*',
               ],
        'd': ['flickr.com',
              'flic.kr',
              ],
    },
    'http://www.funnyordie.com/oembed': {
        're': ['https?://(www\.)?funnyordie\.com/videos/\S+', ],
        'd': ['funnyordie.com', ],
    },

    # g
    'https://github.com/api/oembed': {
        're': [r'https?://gist.github.com/\S*', ],
        'd': ['gist.github.com', ],
    },

    # h
    'http://www.hulu.com/api/oembed.json': {
        're': ['http://www.hulu.com/watch/\S+', ],
        'd': ['hulu.com', ],
    },

    # i
    'http://www.ifixit.com/Embed': {
        're': ['http://www.ifixit.com/Guide/View/\S+', ],
        'd': ['ifixit.com', ],
    },
    'http://api.imgur.com/oembed': {
        're': ['http://\S*imgur\.com/\S+', ],
        'd': ['imgur.com', ],
    },
    'http://api.instagram.com/oembed': {
        're': ['https?://(www\.)?instagr(\.am|am\.com)/p/\S+', ],
        'd': ['instagr.am',
              'instagram.com',
              ],
    },

    # j
    'http://www.jest.com/oembed.json': {
        're': ['http://www.jest.com/(video|embed)/\S+', ],
        'd': ['jest.com', ],
    },

    # m
    'http://api.mobypicture.com/oEmbed': {
        're': ['http://www.mobypicture.com/user/\S*?/view/\S*',
               'http://moby.to/\S*',
               ],
        'd': ['mobypicture.com',
              'moby.to',
              ],
    },

    # p
    'http://photobucket.com/oembed': {
        're': ['http://i\S*.photobucket.com/albums/\S+',
               'http://gi\S*.photobucket.com/groups/\S+',
               ],
        'd': ['photobucket.com', ],
    },
    'http://www.polleverywhere.com/services/oembed/': {
        're': ['http://www.polleverywhere.com/(polls|multiple_choice_polls|free_text_polls)/\S+', ],
        'd': ['polleverywhere.com', ],
    },
    'http://polldaddy.com/oembed/': {
        're': ['https?://(.+\.)?polldaddy\.com/\S*', ],
        'd': ['polldaddy.com', ],
    },

    # q
    'http://qik.com/api/oembed.json': {
        're': ['http://qik.com/video/\S+', ],
        'd': ['qik.com', ],
    },

    # r
    'http://revision3.com/api/oembed/': {
        're': ['http://\S*.revision3.com/\S+', ],
        'd': ['revision3.com', ],
    },

    # s
    'http://www.slideshare.net/api/oembed/2': {
        're': ['https?://www.slideshare.net/[^\/]+/\S+',
               'https?://slidesha\.re/\S*',
               ],
        'd': ['slideshare.net',
              'slidesha.re', ]
    },
    'http://api.smugmug.com/services/oembed/': {
        're': ['http://\S*.smugmug.com/\S*', ],
        'd': ['smugmug.com', ],
    },
    'http://soundcloud.com/oembed': {
        're': ['https://\S*?soundcloud.com/\S+', ],
        'd': ['soundcloud.com', ],
    },
    'https://speakerdeck.com/oembed.json': {
        're': ['https?://speakerdeck\.com/\S*', ],
        'd': ['speakerdeck.com', ],
    },
    'http://www.scribd.com/services/oembed': {
        're': ['https?://(www\.)?scribd\.com/\S*', ],
        'd': ['scribd.com', ],
    },

    # t
    'https://api.twitter.com/1/statuses/oembed.json': {
        're': ['https?://(www\.)?twitter.com/\S+/status(es)?/\S+', ],
        'd': ['twitter.com', ],
    },

    # v
    'http://vimeo.com/api/oembed.json': {
        're': ['http://vimeo.com/\S+',
               'https://vimeo.com/\S+',
               ],
        'd': ['vimeo.com', ],
    },
    'http://lab.viddler.com/services/oembed/': {
        're': ['http://\S*.viddler.com/\S*', ],
        'd': ['viddler.com', ],
    },

    # y
    'http://www.youtube.com/oembed': {
        're': ['http://(\S*.)?youtu(\.be/|be\.com/watch)\S+', ],
        'd': ['youtu.be', 'youtube.com', ],
    },
    'http://www.youtube.com/oembed?scheme=https&': {
        're': ['https://(\S*.)?youtu(\.be/|be\.com/watch)\S+', ],
        'd': ['youtu.be', 'youtube.com', ],
    },
    'http://www.yfrog.com/api/oembed': {
        're': ['http://(\S*\.)?yfrog\.com/\S*', ],
        'd': ['yfrog.com', ],
    },

    # w
    'http://public-api.wordpress.com/oembed/': {
        're': ['http://\S+.wordpress.com/\S+', ],
        'd': ['wordpress.com', ],
    },
    'http://wordpress.tv/oembed/': {
        're': ['https?://wordpress.tv/\S+', ],
        'd': ['wordpress.tv', ],
    },
}


class Provider(object):
    def __init__(self, endpoint, timeout=3.0, user_agent=None, **kwargs):
        self.endpoint = endpoint
        self.socket_timeout = timeout
        self.user_agent = user_agent or 'python-micawber'
        self.base_params = {'format': 'json'}
        self.base_params.update(kwargs)

    def fetch(self, url):
        req = Request(url, headers={'User-Agent': self.user_agent})
        try:
            resp = fetch(req, self.socket_timeout)
        except URLError:
            return False
        except HTTPError:
            return False
        except socket.timeout:
            return False
        except ssl.SSLError:
            return False
        return resp

    def encode_params(self, url, **extra_params):
        params = dict(self.base_params)
        params.update(extra_params)
        params['url'] = url
        return urlencode(sorted(params.items()))

    def request(self, url, **extra_params):
        encoded_params = self.encode_params(url, **extra_params)

        endpoint_url = self.endpoint
        if '?' in endpoint_url:
            endpoint_url = '%s&%s' % (endpoint_url.rstrip('&'), encoded_params)
        else:
            endpoint_url = '%s?%s' % (endpoint_url, encoded_params)

        response = self.fetch(endpoint_url)
        if response:
            return self.handle_response(response, url)
        else:
            raise ProviderException('Error fetching "%s"' % endpoint_url)

    def handle_response(self, response, url):
        try:
            json_data = json.loads(response)
        except InvalidJson as exc:
            try:
                msg = exc.message
            except AttributeError:
                msg = exc.args[0]
            raise InvalidResponseException(msg)

        if 'url' not in json_data:
            json_data['url'] = url
        if 'title' not in json_data:
            json_data['title'] = json_data['url']

        return json_data


def make_key(*args, **kwargs):
    return hashlib.md5(pickle.dumps((args, kwargs))).hexdigest()


def url_cache(fn):
    def inner(self, url, **params):
        if self.cache:
            key = make_key(url, params)
            data = self.cache.get(key)
            if not data:
                data = fn(self, url, **params)
                self.cache.set(key, data)
            return data
        return fn(self, url, **params)
    return inner


def fetch(request, timeout=None):
    urlopen_params = {}
    if timeout:
        urlopen_params['timeout'] = timeout
    resp = urlopen(request, **urlopen_params)
    if resp.code < 200 or resp.code >= 300:
        return False

    # by RFC, default HTTP charset is ISO-8859-1
    charset = get_charset(resp) or 'iso-8859-1'

    content = resp.read().decode(charset)
    resp.close()
    return content


class ProviderRegistry(object):
    def __init__(self, cache=None):
        self._registry = OrderedDict()
        self.cache = cache

    def register(self, regex, provider):
        self._registry[regex] = provider

    def unregister(self, regex):
        del self._registry[regex]

    def __iter__(self):
        return iter(reversed(list(self._registry.items())))

    def provider_for_url(self, url):
        for regex, provider in self:
            if re.match(regex, url):
                return provider

    @url_cache
    def request(self, url, **params):
        provider = self.provider_for_url(url)
        if provider:
            return provider.request(url, **params)
        raise ProviderNotFoundException('Provider not found for "%s"' % url)


def bootstrap_basic(cache=None, registry=None):
    # complements of oembed.com#section7
    pr = registry or ProviderRegistry(cache)
    for _endpoint in providers_library.keys():
        _provider = Provider(_endpoint)
        for _regex in providers_library[_endpoint]['re']:
            pr.register(_regex, _provider)
    return pr


def bootstrap_embedly(cache=None, registry=None, **params):
    endpoint = 'http://api.embed.ly/1/oembed'
    schema_url = 'http://api.embed.ly/1/services/python'

    pr = registry or ProviderRegistry(cache)

    # fetch the schema
    contents = fetch(schema_url)
    json_data = json.loads(contents)

    for provider_meta in json_data:
        for regex in provider_meta['regex']:
            pr.register(regex, Provider(endpoint, **params))
    return pr


def bootstrap_noembed(cache=None, registry=None, **params):
    endpoint = 'http://noembed.com/embed'
    schema_url = 'http://noembed.com/providers'

    pr = registry or ProviderRegistry(cache)

    # fetch the schema
    contents = fetch(schema_url)
    json_data = json.loads(contents)

    for provider_meta in json_data:
        for regex in provider_meta['patterns']:
            pr.register(regex, Provider(endpoint, **params))
    return pr


def bootstrap_oembedio(cache=None, registry=None, **params):
    endpoint = 'http://oembed.io/api'
    schema_url = 'http://oembed.io/providers'

    pr = registry or ProviderRegistry(cache)

    # fetch the schema
    contents = fetch(schema_url)
    json_data = json.loads(contents)

    for provider_meta in json_data:
        regex = provider_meta['s']
        if not regex.startswith('http'):
            regex = 'https?://(?:www\.)?' + regex
        pr.register(regex, Provider(endpoint, **params))
    return pr
