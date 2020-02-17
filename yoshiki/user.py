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


class User(PaginatedQuery):
    log = logging.getLogger("yoshiki.User")
    connection = ''

    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__()
        self.username: str = args.username

    def graph_query(self) -> str:
        return textwrap.dedent(
        """
        {
          user(login: "%(username)s") {
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
                   username=self.username,
                   connection=self.connection))

    @staticmethod
    def strip(edge: Result) -> Result:
        try:
            return dict(name=edge['node']['name'], login=edge['node']['login'])
        except Exception:
            User.log.exception(f"Failed to parse {edge}")
            return {}

    def transform_result(self, raw: Raw) -> Results:
        edges = raw['data']['user'][self.connection]['edges']
        if not self.count:
            self.count = len(edges)
            self.log.info(f"{self.count} {self.connection} to fetch")
        pageInfo = raw['data']['user'][self.connection]['pageInfo']
        if pageInfo['hasNextPage']:
            self.after = pageInfo['endCursor']
        else:
            self.after = ''
        self.log.info(f"{self.count} {self.connection} read")
        return [user for user in [Followers.strip(edge) for edge in edges] if edges]


class Followers(User):
    connection = 'followers'

    @staticmethod
    def sub_parser(parser: argparse._SubParsersAction) -> None:
        sub = parser.add_parser(f"list-followers")
        sub.set_defaults(query=Followers)
        sub.add_argument('--username', help='The user name', required=True)


class Following(User):
    connection = 'following'

    @staticmethod
    def sub_parser(parser: argparse._SubParsersAction) -> None:
        sub = parser.add_parser(f"list-following")
        sub.set_defaults(query=Following)
        sub.add_argument('--username', help='The user name', required=True)
