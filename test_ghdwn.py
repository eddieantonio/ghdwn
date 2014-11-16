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
    requests_remaining = iter(xrange(9, -1, -1))
    body = iter(mock_data.search_bodies)
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


def test_authentication(monkeypatch):
    import os.path
    import io
    import __builtin__

    auth_token = 'fhqwhgads\n'

    # Monkey-Patch open() to return specific file content.
    original_open = open

    def intercept_open(path, *args, **kwargs):
        if path == os.path.expanduser('~/.ghtoken'):
            return io.BytesIO(auth_token)
        return original_open(file, *args, **kwargs)
    monkeypatch.setattr(__builtin__, 'open', intercept_open)

    # Enable HTTPretty and register the index path.
    httpretty.enable()

    body = iter(mock_data.abbrev_search_bodies)

    def request_callback(request, uri, headers):
        headers['Content-Type'] = 'application/json; charset=utf-8'
        headers['X-RateLimit-Remaining'] = 10
        headers['Link'] = (
            '<https://api.github.com/search/repositories?'
            'q=language%3Apython&sort=stars&page=1>; rel="last"')
        return 200, headers, next(body)

    httpretty.register_uri(httpretty.GET,
                           "https://api.github.com/search/repositories",
                           body=request_callback)

    # Simply issue the request...
    ghdwn.get_github_list('java')
    assert httpretty.last_request().headers[
        'Authorization'] == 'token fhqwhgads'

    original_exists = os.path.exists

    def intercept_exists(path, *args, **kwargs):
        if path == os.path.expanduser('~/.ghtoken'):
            return False
        return original_exists(path, *args, **kwargs)
    monkeypatch.setattr(os.path, 'exists', intercept_exists)

    # Now pretend that file DOES NOT exist!
    def intercept_open_failure(path, *args, **kwargs):
        assert False
        if path == os.path.expanduser('~/.ghtoken'):
            raise IOError('Could not find file!')
        return original_open(file, *args, **kwargs)
    monkeypatch.setattr(__builtin__, 'open', intercept_open_failure)

    # Issue the same request again:
    ghdwn.get_github_list('java')
    assert 'Authorization' not in httpretty.last_request().headers

    # Disable HTTPretty
    httpretty.disable()
    httpretty.reset()


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
    # This one is purposefully not found. Because.
    httpretty.register_uri(httpretty.GET,
                           ghdwn.create_archive_url('django', 'reinhardt'),
                           status=404)

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

    # Assert that none of the files in the root directory exist (but the
    # directory can exist!).  I may have gone overboard with the name here...
    repo = 'syntax-errors-up-the-ying-yang'
    assert corpus_dir.join('eddieantonio', repo).check(dir=True)
    assert len(corpus_dir.join('eddieantonio', repo).listdir()) == 1
    # This file is nested, but it compiles just fine!
    assert corpus_dir.join('eddieantonio', repo, 'working',
                           '__init__.py').check(file=True)
