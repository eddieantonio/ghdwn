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

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
GITHUB_BASE = "https://github.com"

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

def rate_limit_permits(response):
    "Check if more requests can be made on the GitHub API."
    return response.info()['X-RateLimit-Remaining'] > 0

def create_list_request(language, page_num):
    url = create_search_url(language, page_num)
    request = urllib2.Request(url)
    request.add_header('Accept', 'application/vnd.github.v3+json')
    return request

def get_github_list(language, quantity=1024):
    """
    Returns a great big list of suitable owner/repository tuples for the given
    langauge.
    """

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
