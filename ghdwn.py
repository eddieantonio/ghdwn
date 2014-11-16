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
import os
import re
import sys
import zipfile
import logging

# These are different in Python 3...
try:
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import urlopen, Request, HTTPError

__version__ = '0.1.0'

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
GITHUB_BASE = "https://github.com"


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
        self.buffer = [tuple(repo['full_name'].split('/'))
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

    def __init__(self, owner, repo, default_branch='master'):
        self.owner = owner
        self.repository = repo
        self.default_branch = default_branch

    @property
    def archive_url(self):
        return "{base}/{owner}/{repository}/archive/{release}.zip".format(
            base=GITHUB_BASE, owner=self.owner, repository=self.repository,
            release=self.default_branch)

    def __repr__(self):
        args = ', '.join(repr(vars(self)[name]) for name in (
            'owner', 'repository', 'default_branch'))
        return 'RepositoryInfo({0:s})'.format(args)

    def __str__(self):
        return "{owner}/{repository}".format(**vars(self))

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
    langauge.
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
    Creates a URL for search repositories based on the langauge.
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


def download_repo_zip(owner, repo):
    request = create_github_request(create_archive_url(owner, repo, 'master'))
    try:
        response = urlopen(request)
    except HTTPError:
        return None

    assert response.info()['Content-Type'] == 'application/zip'

    # Need to create a "real" file-like object for ZipFile...
    file_like = io.BytesIO(response.read())

    return zipfile.ZipFile(file_like, allowZip64=True)


def maybe_write_file(directory, file_path, file_content):
    if not file_content or not syntax_ok(file_content):
        return False

    zip_path = os.path.split(file_path)

    assert len(zip_path) >= 2

    filename = zip_path[-1]
    file_directory = zip_path[1:-1]

    file_dir_name = mkdirp(directory, *file_directory)
    file_path = os.path.join(file_dir_name, filename)

    with open(file_path, 'wb') as f:
        f.write(file_content)

    return True


def download_repo(owner, repo, directory, language="python"):
    """
    Downloads a repository and keeps only the files that validly compile.
    """
    base_dir = mkdirp(directory, owner, repo)

    archive = download_repo_zip(owner, repo)

    if not archive:
        logging.warning('Could not download archive for %s', repo)
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

    # Persist the index to a file.
    with open(j('index.json'), 'w') as f:
        json.dump(index, f)

    for owner, repo in index:
        download_repo(owner, repo, directory, language)


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
