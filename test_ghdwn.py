#!/usr/bin/env py.test

"""
Tests GitHub downloading thingymobber. 
"""

import httpretty

@httpretty.activate
def test_download_python():
    httpretty.register_uri(httpretty.GET, "https://api.github.com/search/repositories",
            body='[{"title": "Test Deal"}]',
            content_type="application/json",
            adding_headers={
                'X-RateLimit-Remaining': '59'
            })

    assert True


@httpretty.activate
def test_rate_limiting():
    httpretty.register_uri(httpretty.GET, "https://api.github.com/search/repositories",
            body='[{"title": "Test Deal"}]',
            content_type="application/json",
            adding_headers={
                'X-RateLimit-Remaining': '0'
            })
    assert True
