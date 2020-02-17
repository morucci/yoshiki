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

import argparse
import logging
import textwrap

from . helpers import PaginatedQuery, Raw, Result, Results
from . user import User


class Repository(PaginatedQuery):
    log = logging.getLogger("yoshiki.Repository")
    connection = ''

    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__()
        self.repository: str = args.repository

    def graph_query(self) -> str:
        return textwrap.dedent(
        """
        {
          repository(name: "%(name)s", owner: "%(owner)s") {
            %(connection)s(first: 100%(after)s) {
              pageInfo {
                hasNextPage endCursor
              }
              edges {
                node {
                  name
                  login
                }
              }
            }
          }
        }
        """ % dict(after=', after: "%s"' % self.after if self.after else '',
                   owner=self.repository.split('/')[0],
                   name=self.repository.split('/')[1],
                   connection=self.connection))

    def transform_result(self, raw: Raw) -> Results:
        edges = raw['data']['repository'][self.connection]['edges']
        if not self.count:
            self.count = len(edges)
        pageInfo = raw['data']['repository'][self.connection]['pageInfo']
        if pageInfo['hasNextPage']:
            self.after = pageInfo['endCursor']
        else:
            self.after = ''
        self.log.info(f"{self.count} {self.connection} read")
        return [user for user in [User.strip(edge) for edge in edges] if edges]


class Stargazers(Repository):
    connection = 'stargazers'

    @staticmethod
    def sub_parser(parser: argparse._SubParsersAction) -> None:
        sub = parser.add_parser(f"list-stargazers")
        sub.set_defaults(query=Stargazers)
        sub.add_argument('--repository', help='The repository name', required=True)


class Watchers(Repository):
    connection = 'watchers'

    @staticmethod
    def sub_parser(parser: argparse._SubParsersAction) -> None:
        sub = parser.add_parser(f"list-watchers")
        sub.set_defaults(query=Watchers)
        sub.add_argument('--repository', help='The repository name', required=True)
