#!/usr/bin/env python

"""
Downloads a craptonne of code from GitHub. Uses only the Python standard
library, because... uh...
"""

import itertools
import json
import math
import os
import py_compile
import re
import urllib2

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
        response = urllib2.urlopen(create_github_request(self.next_url))

        payload = json.load(response)
        link_header = response.info()['Link']

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
        except urllib2.HTTPError:
            self.buffer = []

        if self.buffer:
            return self.buffer.pop(0)
        else:
            raise StopIteration()


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
    """
    raw_links = re.split(r',\s+', header)

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
    return "{base}/{owner}/{repository}/archive/{release}.zip".format(
        base=GITHUB_BASE, owner=owner, repository=repository,
        release=release)


def create_github_request(url):
    request = urllib2.Request(url)
    request.add_header('Accept', 'application/vnd.github.v3+json')
    return request


def syntax_ok(contents):
    """
    Given a source file, returns True if the file compiles.

    >>> syntax_ok('print "Hello, World!",')
    True
    >>> syntax_ok('import java.util.*;')
    False
    """
    try:
        compile(contents, '<unknown>', 'exec')
    except SyntaxError:
        return False
    return True


def post_process(repo_path, langauge):
    if language != 'python':
        return

    # For python files, will delete everything EXCEPT
    # the python files that compile.


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


def download_repo(owner, repo, directory, language="python"):
    """
    Downloads a repository. Does post-processing on the repo.
    """
    mkdirp(directory, owner, repo)


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

if __name__ == '__main__':
    raise NotImplemented()
