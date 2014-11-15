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
        headers['Content-Type'] = 'application/json; charset=utf-8'
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
                           content_type="application/json; charset=utf-8",
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
        headers['Content-Type'] = 'application/json; charset=utf-8'
        headers['X-RateLimit-Remaining'] = 10
        headers['Link'] = (
            '<https://api.github.com/search/repositories?'
            'q=language%3Apython&sort=stars&page=1>; rel="last"')
        return 200, headers, next(body)

    # Register the index path.
    httpretty.register_uri(httpretty.GET,
                           "https://api.github.com/search/repositories",
                           body=request_callback)

    # Register the zip paths.
    httpretty.register_uri(httpretty.GET,
                           ghdwn.create_archive_url('eddieantonio', 'dev'),
                           body=mock_data.dev_zip,
                           content_type='application/zip')
    broken_url = ghdwn.create_archive_url('eddieantonio',
                                          'syntax-errors-up-the-ying-yang')
    httpretty.register_uri(httpretty.GET, broken_url,
                           body=mock_data.broken_zip,
                           content_type='application/zip')

    # Download that entire corpus.
    ghdwn.download_corpus('python', 'corpus')

    # Teardown httpretty.
    # Again, this function is not wrapped in @httpretty.activate,
    # so these two *must* be explicitly called.
    httpretty.disable()
    httpretty.reset()

    corpus_dir = tmpdir.join('corpus')

    assert corpus_dir.check(dir=True)

    assert corpus_dir.join('index.json').check(file=True)

    assert corpus_dir.join('eddieantonio', 'dev').check(dir=True)
    assert corpus_dir.join('eddieantonio', 'dev', 'dev.py').check(file=True)
    assert corpus_dir.join('eddieantonio', 'dev', 'setup.py').check(file=True)
    assert not corpus_dir.join('eddieantonio', 'dev', 'README.rst').check()

    # Assert that none of the files here exist (but the directory can exist!).
    # I may have gone overboard with the name here...
    repo = 'syntax-errors-up-the-ying-yang'
    assert corpus_dir.join('eddieantonio', repo).check(dir=True)
    assert len(corpus_dir.join('eddieantonio', repo).listdir()) == 0
