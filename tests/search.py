#!/usr/bin/env python3

# MIT License
# Copyright (c) 2020 YoShiKi

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging
logging.basicConfig(level=getattr(logging, 'DEBUG'))

import argparse
import json
import unittest
from . utils import github_mock, timestamp
from typing import Any, Dict

import yoshiki.main


class TestSearch(unittest.TestCase):
    def setUp(self) -> None:
        def mock_search(name: str, hasNext: bool) -> Dict[str, Any]:
            return dict(data=dict(search=dict(
                repositoryCount=26, pageInfo=dict(hasNextPage=hasNext, endCursor='4242'), edges=[
                    dict(node=dict(nameWithOwner=name,
                                   defaultBranchRef=dict(name="master"),
                                   description="desc",
                                   stargazers=dict(totalCount=42),
                                   forks=dict(totalCount=42),
                                   watchers=dict(totalCount=48),
                                   repositoryTopics=dict(edges=[])))])))
        self.httpd, self.thread = github_mock(list(map(json.dumps, [
            dict(data=dict(rateLimit=dict(limit=5000, cost=1, remaining=5000, resetAt=timestamp(3600)))),
            mock_search('toto/tata', True), mock_search('titi/riri', False)])))

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.thread.join()

    def test_search(self) -> None:
        gql = yoshiki.main.GithubGraphQLQuery("fake-token", 'http://localhost:8080')
        reqc = yoshiki.main.SearchProjects(argparse.Namespace(stars=42, terms=''))
        repos = gql.run(reqc)
        print(repos)
        self.assertEqual(len(repos), 2)
