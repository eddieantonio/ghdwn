#!/usr/bin/env py.test
# coding: utf-8

"""
Tests GitHub downloading thingymobber.
"""

import httpretty
from itertools import count

import ghdwn
import mock_data

@httpretty.activate
def test_download_java():

    # Sample request bodies:
    requests_remaining, body = count(9, -1), iter(mock_data.search_bodies)
    page_no = count(2)

    def request_callback(request, uri, headers):
        headers['Content-Type'] = 'application/json'
        headers['X-RateLimit-Remaining'] = next(requests_remaining)
        headers['Link'] = (
                '<https://api.github.com/search/repositories?'
                'q=language%3Apython&sort=stars&page={0}>; rel="next", '
                '<https://api.github.com/search/repositories?'
                'q=language%3Ajava&sort=stars&page=34>; rel="last"').format(
                        next(page_no))

        return 200, headers, next(body)

    httpretty.register_uri(httpretty.GET,
        "https://api.github.com/search/repositories",
        body=request_callback)
    index = ghdwn.get_github_list('python')

    assert len(index) == 8
    assert index == [
            ('jakubroztocil', 'httpie'),
            ('django', 'django'),
            ('kennethreitz', 'requests'),
            ('mitsuhiko', 'flask'),
            ('ansible', 'ansible'),
            ('tornadoweb', 'tornado'),
            ('numbbbbb', 'the-swift-programming-language-in-chinese'),
            ('reddit', 'reddit')
    ]



@httpretty.activate
def test_rate_limiting():
    # Come up with zero results.
    httpretty.register_uri(httpretty.GET,
            "https://api.github.com/search/repositories",
            status=403,
            content_type="application/json",
            adding_headers={
                'X-RateLimit-Remaining': '0'
            })

    # Should have gotten zero results...
    index = ghdwn.get_github_list('python')
    assert index == []


def test_download_corpus(monkeypatch, tmpdir):
    # Pretend we're in a temporary directory...
    monkeypatch.chdir(tmpdir)

    # Can't use @httpretty.activate because of monkeypatch and tmpdir
    httpretty.enable()
    body = iter(mock_data.abbrev_search_bodies)

    def request_callback(request, uri, headers):
        headers['Content-Type'] = 'application/json'
        headers['X-RateLimit-Remaining'] = 10
        headers['Link'] = (
                '<https://api.github.com/search/repositories?'
                'q=language%3Apython&sort=stars&page=1>; rel="last"')
        return 200, headers, next(body)

    httpretty.register_uri(httpretty.GET,
        "https://api.github.com/search/repositories",
        body=request_callback)
    index = ghdwn.get_github_list('python')

    # Download that entire corpus.
    ghdwn.download_corpus('python')

    # Assert that files exist...
    assert tmpdir.join('eddieantonio','dev').check(dir=True)
    assert tmpdir.join('eddieantonio', 'dev', 'dev.py').check(file=True)
    assert not tmpdir.join('eddieantonio', 'dev', 'README.rst').check()
    # TODO: More asserts for this...
    assert tmpdir.join('django', 'django').check(dir=True)

    # Again, this function is not wrapped in @httpretty.activate
    httpretty.disable()  
    httpretty.reset() 

def test_syntax_ok(monkeypatch, tmpdir):
    monkeypatch.chdir(tmpdir)

    valid_python = tmpdir.join('alright.py')
    valid_python.write('print "Hello, World!",')

    assert ghdwn.syntax_ok(str(valid_python))

    invalid_python = tmpdir.join('no_good.py')
    invalid_python.write('import java.util.*;')

    assert not ghdwn.syntax_ok(str(invalid_python))
