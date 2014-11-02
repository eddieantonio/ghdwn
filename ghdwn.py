#!/usr/bin/env python

import urllib
import urllib2
import urlparse

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
GITHUB_BASE = "https://github.com"

def create_search_url(language, quantity=100):
    """
    Creates a URL for search repositories based on the langauge.
    >>> create_search_url('python')
    'https://api.github.com/search/repositories?q=language%3Apython&sort=stars&per_page=100'
    >>> create_search_url('coffeescript', 10)
    'https://api.github.com/search/repositories?q=language%3Acoffeescript&sort=stars&per_page=10'
    """
    options = {
            'q': "language:%s" % language,
            'sort': 'stars',
            'per_page': quantity
    }
    query = urllib.urlencode(options)
    return "%s?%s" % (GITHUB_SEARCH_URL, query)


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

def get_github_list(language, quantity=100):
    url = create_search_url(langauge, quantity)
    request = urllib2.urlopen(url)
