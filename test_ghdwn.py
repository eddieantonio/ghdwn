#!/usr/bin/env py.test

"""
Tests GitHub downloading thingymobber.
"""

import httpretty
from itertools import count

import ghdwn

@httpretty.activate
def test_download_java():

    # Sample request bodies:
    java_bodies = [
        '{"total_count": 2, "items":[{"full_name": "herp/derp"}]}',
        '{"total_count": 2, "items":[{"full_name": "foo/bar"}]}'
    ]
    requests_remaining, body = count(59, -1), iter(java_bodies)
    
    def request_callback(request, uri, headers):
        headers['Content-Type'] = 'application/json'
        headers['X-RateLimit-Remaining'] = next(requests_remaining)
        return 200, headers, next(body)

    httpretty.register_uri(httpretty.GET,
        "https://api.github.com/search/repositories",
        body=request_callback)
    index = ghdwn.get_github_list('java')

    assert index[0] == ('herp', 'derp')
    assert len(index) == 2

@httpretty.activate
def test_rate_limiting():
    httpretty.register_uri(httpretty.GET, "https://api.github.com/search/repositories",
            body='[{"title": "Test Deal"}]',
            content_type="application/json",
            adding_headers={
                'X-RateLimit-Remaining': '0'
            })
    assert True


"""
    # For first request:
    httpretty.Response(
        body='[{"title": "Test Deal"}]',
        content_type="application/json",
        adding_headers={'X-RateLimit-Remaining': '59'})
    # For second request:
    httpretty.Response(
        body='[{"title": "Test Deal"}]',
        content_type="application/json",
        adding_headers={})
])
"""
