=========================
ghdown ❧ download corpora
=========================

.. image:: https://travis-ci.org/eddieantonio/ghdwn.svg
    :target: https://travis-ci.org/eddieantonio/ghdwn

Downloads the most popular projects for a given language. For Python
files, it only writes files that compile as valid Python to the
file system.

-----
Usage
-----
::

    ghdwn {langauage} [directory [quantity]]

For example::

    ghdwn python corpus 1024

Downloads the top 1024 Python projects to `corpus/`.


-------------
Authorization
-------------

If you have a `GitHub Access Token`_, you can place it in a file called
`~/.ghtoken` and it will be automtically be used with requests. This
allows for greater freedom regarding rate-limiting.

.. _GitHub Access Token: https://help.github.com/articles/creating-an-access-token-for-command-line-use/


-------
License
-------

© 2014 Eddie Antonio Santos. MIT Licensed. 
