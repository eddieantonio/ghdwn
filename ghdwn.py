#!/usr/bin/env python

"""
This file is meant to replace the following two file:


    #### ghdwn.curl ####
    url = "https://api.github.com/search/repositories"
    -G
    data-urlencode = "q=language:python"
    data-urlencode = "sort=stars"
    data-urlencode = "per_page=100"
    header = "Accept: application/vnd.github.v3+json"



    #### download.sh ####
    download_index () {
            i=1
            while [ $i -le 10 ] ;
            do
                    curl -K ghdwn.curl --data-urlencode "page=$i" | \
                            tee json/$i.json | \
                            jq '.items | .[] | .clone_url' > urls/$i

                    i=$((i+1))
            done;

            cat urls/* > repos/index.txt
    }


    cd repos
    for url in `cat index.txt`
    do
            git clone $url
    done

"""

import json
import math
import urllib2
import re
import itertools

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
GITHUB_BASE = "https://github.com"

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
        link_header = response.info().getheader('Link')

        # Set the new buffer's contents.
        self.buffer = [tuple(repo['full_name'].split('/')) for repo in payload['items']]

        self.next_url = parse_link_header(link_header)['next']

    def next(self):
        if self.buffer:
            return self.buffer.pop(0)
        if not self.requests_left:
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

def create_search_url(language, page=1, quantity=100):
    """
    Creates a URL for search repositories based on the langauge.
    >>> create_search_url('python')
    'https://api.github.com/search/repositories?q=language:python&sort=stars&per_page=100&page=1'
    >>> create_search_url('coffeescript', 10)
    'https://api.github.com/search/repositories?q=language:coffeescript&sort=stars&per_page=100&page=10'
    """

    if type(page) is not int: raise TypeError('Need an int for page number')
    if page < 1: raise ValueError('Pages must be greater than 0')

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

# TODO: Create context manager that does RESTful stuff!

def rate_limit_permits(response):
    "Check if more requests can be made on the GitHub API."
    return response.info()['X-RateLimit-Remaining'] > 0

def create_github_request(url):
    request = urllib2.Request(url)
    request.add_header('Accept', 'application/vnd.github.v3+json')
    return request

def create_list_request(language, page_num):
    url = create_search_url(language, page_num)
    request = urllib2.Request(url)
    request.add_header('Accept', 'application/vnd.github.v3+json')
    return request

def legacy_github_list_thing():
    repos = []
    total_requests = int(math.ceil(quantity / 100.0))

    for page_num in xrange(1, total_requests + 1):
        response = urllib2.urlopen(create_list_request(language, page_num))
        payload = json.load(response)

        repos.extend([tuple(repo['full_name'].split('/')) for repo in payload['items']])

        # Downloaded the entire list...
        if len(repos) >= int(payload['total_count']):
            # Done downloading..
            break


    return repos


if __name__ == '__main__':
    index = get_github_list('python')
    # Apparently I used to clone them, but now I will carefully select Python
    # files from each index.

    "python -m py_compile {0}".format(script)

    pass
