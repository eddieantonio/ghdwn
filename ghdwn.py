#!/usr/bin/env python

"""
Downloads a craptonne of code from GitHub. Uses only the Python standard
library, because... uh...
"""

import codecs
import collections
import io
import itertools
import json
import logging
import os
import re
import sys
import zipfile

# These are different in Python 3...
try:
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import urlopen, Request, HTTPError

__version__ = '0.1.0'

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
GITHUB_BASE = "https://github.com"

logger = logging.getLogger()
logging.basicConfig()

class GitHubSearchRequester(object):

    """
    Requests stuff from GitHub. You can tell it downloads GitHub stuff because
    of the way it is. Wow.
    """

    def __init__(self, language):
        self.requests_left = 1
        self.next_url = create_search_url(language, quantity=100)
        self.buffer = None

    def __iter__(self):
        return self

    def request_next_page(self):
        # Do that nasty request
        response = urlopen(create_github_request(self.next_url))

        assert 'charset=utf-8' in response.info().get('Content-Type')

        reader = codecs.getreader("utf-8")
        payload = json.load(reader(response))

        link_header = response.info().get('Link', '')

        # Set the new buffer's contents.
        self.buffer = [RepositoryInfo.from_json(repo)
                       for repo in payload['items']]

        self.next_url = parse_link_header(link_header).get('next', None)

    def next(self):
        if self.buffer:
            return self.buffer.pop(0)

        # Either no requests left or there are no more pages:
        if not self.requests_left or not self.next_url:
            raise StopIteration()

        try:
            self.request_next_page()
        # Some HTTP error occured. Return no results.
        except HTTPError:
            self.buffer = []

        if self.buffer:
            return self.buffer.pop(0)
        else:
            raise StopIteration()

    # For Python 3 compatibility:
    __next__ = next


class RepositoryInfo(object):
    STANDARD_ATTRS = ('owner', 'name', 'default_branch')

    def __init__(self, owner, repo, default_branch='master'):
        self.owner = owner
        self.name = repo
        self.default_branch = default_branch

    @property
    def archive_url(self):
        return "{base}/{owner}/{name}/archive/{default_branch}.zip".format(
            base=GITHUB_BASE, **vars(self))

    def __repr__(self):
        args = ', '.join(repr(getattr(self, name))
                         for name in self.STANDARD_ATTRS)
        return 'RepositoryInfo({0:s})'.format(args)

    def __str__(self):
        return "{owner}/{name}".format(**vars(self))

    def __eq__(self, other):
        if isinstance(other, tuple):
            return self.__tuple_eq__(other)
        return all(getattr(self, attr) == getattr(other, attr)
                   for attr in self.STANDARD_ATTRS)

    def __tuple_eq__(self, other):
        return self.owner == other[0] and self.name == other[1]

    def as_dict(self):
        return dict((attr, getattr(self, attr))
                    for attr in self.STANDARD_ATTRS)

    @classmethod
    def from_json(cls, json):
        """
        Creates a RepositoryInfo object from a single element of the JSON
        search body.

        >>> json = {'name': 'dev', 'owner': {'login': 'eddieantonio'}}
        >>> RepositoryInfo.from_json(json)
        RepositoryInfo('eddieantonio', 'dev', 'master')
        >>> json['default_branch'] = 'dev'
        >>> RepositoryInfo.from_json(json)
        RepositoryInfo('eddieantonio', 'dev', 'dev')

        """
        owner = json['owner']['login']
        name = json['name']
        default_branch = json.get('default_branch', 'master')

        return cls(owner, name, default_branch)


def get_github_list(language, quantity=1024):
    """
    Returns a great big list of suitable owner/repository tuples for the given
    language.
    """
    # GitHubSearchRequester does the bulk of the work. Using islice to emit at most
    # `quantity` results.
    urls = itertools.islice(GitHubSearchRequester(language), quantity)
    return list(urls)


def parse_link_header(header):
    """
    Parses the content of a Link: header.

    >>> header = '<https://example.com?page=6&q=language%3Apython>; rel="next", <https://example.com?page=36&q=language%3Apython>; rel="prev"'
    >>> links = parse_link_header(header)
    >>> links['next']
    'https://example.com?page=6&q=language%3Apython'
    >>> links['prev']
    'https://example.com?page=36&q=language%3Apython'
    >>> parse_link_header('')
    {}
    """
    raw_links = re.split(r',\s+', header) if header.strip() else []

    links = {}
    for text in raw_links:
        match = re.search(r'^<([^>]+)>;.*?rel="([^"]+)"', text)
        if not match:
            raise ValueError('Could not find links in header: %r' % (header,))
        url, rel = match.groups()
        links[rel] = url

    return links


def create_search_url(language, page=1, quantity=100):
    """
    Creates a URL for search repositories based on the language.
    >>> create_search_url('python')
    'https://api.github.com/search/repositories?q=language:python&sort=stars&per_page=100&page=1'
    >>> create_search_url('coffeescript', 10)
    'https://api.github.com/search/repositories?q=language:coffeescript&sort=stars&per_page=100&page=10'
    """

    if type(page) is not int:
        raise TypeError('Need an int for page number')
    if page < 1:
        raise ValueError('Pages must be greater than 0')

    base = GITHUB_SEARCH_URL
    template = ("{base}?q=language:{language}&sort=stars"
                "&per_page={quantity}&page={page}")
    return template.format(**locals())


def create_archive_url(owner, repository, release="master"):
    """
    >>> create_archive_url('eddieantonio', 'perfection')
    'https://github.com/eddieantonio/perfection/archive/master.zip'
    >>> create_archive_url('gabebw', 'mean_girls', 'v0.0.1')
    'https://github.com/gabebw/mean_girls/archive/v0.0.1.zip'
    >>> create_archive_url('gabebw', 'mean_girls', 'v0.0.1')
    'https://github.com/gabebw/mean_girls/archive/v0.0.1.zip'
    """
    return RepositoryInfo(owner, repository, release).archive_url


def create_github_request(url):
    request = Request(url)
    request.add_header('Accept', 'application/vnd.github.v3+json')

    # Add authorization header...
    auth_token_path = os.path.expanduser('~/.ghtoken')
    if os.path.exists(auth_token_path):
        with open(auth_token_path) as f:
            token = f.read().rstrip()
        request.add_header('Authorization', 'token {}'.format(token))

    return request


def syntax_ok(contents):
    r"""
    Given a source file, returns True if the file compiles.

    >>> syntax_ok('print("Hello, World!")')
    True
    >>> syntax_ok('import java.util.*;')
    False
    >>> syntax_ok('\x89PNG\x0D\x0A\x1A\x0A\x00\x00\x00\x0D')
    False
    """
    try:
        compile(contents, '<unknown>', 'exec')
    except (SyntaxError, TypeError):
        return False
    return True


def mkdirp(*dirs):
    """
    Creates a deep directory hierarchy, unless it doesn't exist.
    """
    fullpath = os.path.join(*dirs)
    try:
        os.makedirs(fullpath)
    except OSError as e:
        # XXX: Oh gosh, Eddie...
        # Ignore the error if it's "File exists"
        if e.strerror != 'File exists':
            raise e
    return fullpath


def download_repo_zip(repo):
    url = repo.archive_url
    logger.info("Downloading %s...", url)
    request = create_github_request(url)
    try:
        response = urlopen(request)
    except HTTPError:
        logger.exception("Download failed: %s", url)
        return None

    assert response.info()['Content-Type'] == 'application/zip'

    # Need to create a "real" file-like object for ZipFile...
    file_like = io.BytesIO(response.read())

    return zipfile.ZipFile(file_like, allowZip64=True)


def maybe_write_file(directory, file_path, file_content):
    if not file_content or not syntax_ok(file_content):
        return False

    zip_path = file_path.split(os.sep)

    assert len(zip_path) >= 2

    filename = zip_path[-1]
    file_directory = zip_path[1:-1]

    file_dir_name = mkdirp(directory, *file_directory)
    file_path = os.path.join(file_dir_name, filename)

    logger.debug('Writing %s...', file_path)
    logger.debug('Its zip path %s...', zip_path)
    with open(file_path, 'wb') as f:
        f.write(file_content)

    return True


def download_repo(repo, directory, language="python"):
    """
    Downloads a repository and keeps only the files that validly compile.
    """
    base_dir = mkdirp(directory, repo.owner, repo.name)

    archive = download_repo_zip(repo)

    if not archive:
        logger.error('Could not download archive for %s', repo)
        return

    for filename in archive.namelist():
        content = archive.open(filename).read()
        maybe_write_file(base_dir, filename, content)


def download_corpus(language, directory, quantity=1024):
    """
    Downloads a corpus to the the given directory.
    """

    # Create the directory if it doesn't exist first!
    if not os.path.exists(directory):
        os.mkdir(directory)

    j = lambda *args: os.path.join(directory, *args)

    index = get_github_list(language, quantity)
    logger.info('Found %d/%d results for %s', len(index), quantity, language)

    # Persist the index to a file.
    with open(j('index.json'), 'w') as f:
        json.dump([repo.as_dict() for repo in index], f)

    for repo in index:
        download_repo(repo, directory, language)


def usage():
    message = ("Usage:\n"
               "\t{0} language [directory [quantity]]\n\n")
    sys.stderr.write(message.format(sys.argv[0]))


def main(argv=sys.argv):
    if len(argv) <= 1:
        usage()
        exit(-1)

    language = argv[1]
    directory = argv[2] if len(argv) >= 3 else './corpus'
    quantity = int(argv[3]) if len(argv) >= 4 else 1024
    download_corpus(language, directory, quantity)

if __name__ == '__main__':
    exit(main())
