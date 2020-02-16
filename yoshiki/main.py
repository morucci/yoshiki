#!/usr/bin/env python3

# MIT License
# Copyright (c) 2019 Fabien Boucher

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
import requests
import logging
import logging.config
import json
from textwrap import dedent
from time import sleep
from datetime import datetime

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


Raw = Dict[str, Any]
Result = Dict[str, Any]
Results = List[Result]


class Query(ABC):
    @staticmethod
    @abstractmethod
    def sub_parser(parser: argparse._SubParsersAction) -> None:
        ...

    @abstractmethod
    def next_graph_query(self) -> Optional[str]:
        ...

    @abstractmethod
    def transform_result(self, raw: Raw) -> Results:
        ...

    def sort(self, results: Results) -> Results:
        return results


class GithubGraphQLQuery(object):

    log = logging.getLogger("yoshiki.GithubGraphQLQuery")

    def __init__(self, token: str, url: str = 'https://api.github.com/graphql') -> None:
        self.url = url
        self.headers = {'Authorization': 'token %s' % token}
        self.session = requests.session()
        # Will get every 25 requests
        self.get_rate_limit_rate = 25
        self.query_count = 0
        # Set an initial value
        self.quota_remain = 5000
        self.set_rate_limit()

    def set_rate_limit(self) -> None:
        try:
            ratelimit = self.getRateLimit()
        except requests.exceptions.ConnectionError:
            sleep(5)
            ratelimit = self.getRateLimit()
        self.quota_remain = ratelimit['remaining']
        self.resetat = datetime.strptime(
            ratelimit['resetAt'], '%Y-%m-%dT%H:%M:%SZ')
        self.log.info("Got rate limit data: remain %s resetat %s" % (
            self.quota_remain, self.resetat))

    def wait_for_call(self) -> None:
        if self.quota_remain <= 150:
            until_reset = self.resetat - datetime.utcnow()
            self.log.info(
                "Quota remain: %s/calls delay until "
                "reset: %s/secs waiting ..." % (
                    self.quota_remain, until_reset.seconds))
            sleep(until_reset.seconds + 60)
            self.set_rate_limit()

    def getRateLimit(self) -> Raw:
        qdata = '''{
          rateLimit {
            limit
            cost
            remaining
            resetAt
          }
        }'''
        data = self._query(qdata)
        rate_limit = data['data']['rateLimit']
        if not isinstance(rate_limit, dict):
            raise Exception("Rate limit it not a dict: %s" % rate_limit)
        return rate_limit

    def query(self, qdata: str, ignore_not_found: bool=False) -> Raw:
        if self.query_count % self.get_rate_limit_rate == 0:
            self.set_rate_limit()
        self.wait_for_call()
        return self._query(qdata, ignore_not_found)

    def _query(self, qdata: str, ignore_not_found: bool=False) -> Raw:
        data = {'query': qdata}
        r = self.session.post(
            url=self.url, json=data, headers=self.headers,
            timeout=30.3)
        self.query_count += 1
        if not r.status_code != "200":
            raise Exception("No ok response code see: %s" % r.text)
        ret = r.json()
        if 'errors' in ret:
            raise Exception("Errors in response see: %s" % r.text)
        if not isinstance(ret, dict):
            raise Exception("Graph result is not a dict: %s" % ret)
        return ret

    def run(self, query: Query) -> Results:
        results: Results = []
        while True:
            graph_query = query.next_graph_query()
            if not graph_query:
                break
            data = self.query(graph_query)
            results += query.transform_result(data)
        return query.sort(results)


class PaginatedQuery(Query):
    def __init__(self) -> None:
        self.after: Optional[str] = None
        self.count: Optional[int] = None

    def next_graph_query(self) -> Optional[str]:
        if self.count and not self.after:
            return None
        return self.graph_query()

    @abstractmethod
    def graph_query(self) -> str:
        ...


class SearchProjects(PaginatedQuery):
    log = logging.getLogger("yoshiki.SearchProjects")

    @staticmethod
    def sub_parser(parser: argparse._SubParsersAction) -> None:
        sub = parser.add_parser("search-projects")
        sub.set_defaults(query=SearchProjects)
        sub.add_argument(
            '--stars', help='Gather projects with stars > to',
            required=True)
        sub.add_argument(
            '--terms', help='Extra search term such as language:ocaml')

    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__()
        self.stars: int = int(args.stars)
        self.terms: str = args.terms

    def graph_query(self) -> str:
        return dedent(
        """
        {
          search(query: "stars:>%(stars)s%(terms)s is:public fork:false archived:false sort:stars-asc", type: REPOSITORY, first: 25%(after)s) {
            repositoryCount
            pageInfo {
                hasNextPage endCursor
            }
            edges {
              node {
                ... on Repository {
                  nameWithOwner
                  defaultBranchRef {
                      name
                  }
                  description
                  stargazers {
                    totalCount
                  }
                  forks {
                    totalCount
                  }
                  watchers {
                    totalCount
                  }
                  repositoryTopics(first: 100) {
                      edges {
                          node {
                            topic {
                              name
                          }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """ % dict(
            after=', after: "%s"' % self.after if self.after else '',
            stars=self.stars,
            terms=' ' + self.terms if self.terms else '',
        ))

    @staticmethod
    def strip(_repo: Result) -> Result:
        _repo = _repo['node']
        try:
            return {
                'name': _repo['nameWithOwner'],
                'owner': _repo['nameWithOwner'].split('/')[0],
                'default_branch': _repo['defaultBranchRef']['name'],
                'description': _repo['description'] or '',
                'stars': _repo['stargazers']['totalCount'],
                'stargazers': [
                    t['node']['login'] for t in
                    _repo['stargazers'].get('edges', [])
                ],
                'forks': _repo['forks']['totalCount'],
                'watchers': _repo['watchers']['totalCount'],
                'topics': [
                    t['node']['topic']['name'] for t in
                    _repo['repositoryTopics']['edges']]
            }
        except Exception:
            SearchProjects.log.exception("Error to parse repository data %s" % _repo)
            return {}

    def transform_result(self, ret: Raw) -> Results:
        if not self.count:
            self.count = int(ret['data']['search']['repositoryCount'])
            self.log.info(f"{self.count} repositories to fetch")
        pageInfo = ret['data']['search']['pageInfo']
        if pageInfo['hasNextPage']:
            self.after = pageInfo['endCursor']
        else:
            self.after = ''
        repos = [sr for sr in [SearchProjects.strip(r) for r in ret['data']['search']['edges']] if sr]
        self.log.info("%s repositories read" % len(repos))
        return repos

    def sort(self, results: Results) -> Results:
        return sorted(results, key=lambda x: x.get('stars', 0), reverse=True)


class Followers(PaginatedQuery):
    log = logging.getLogger("yoshiki.Followers")
    connection = 'followers'

    @staticmethod
    def sub_parser(parser: argparse._SubParsersAction) -> None:
        sub = parser.add_parser(f"list-followers")
        sub.set_defaults(query=Followers)
        sub.add_argument('--username', help='The user name', required=True)

    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__()
        self.username: str = args.username

    def graph_query(self) -> str:
        return dedent(
        """
        {
          user(login: "%(username)s") {
            %(connection)s(first: 100%(after)s) {
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
            Followers.log.exception(f"Failed to parse {edge}")
            return {}

    def transform_result(self, raw: Raw) -> Results:
        followers = raw['data']['user'][self.connection]['edges']
        if not self.count:
            self.count = len(followers)
        self.log.info(f"{self.count} {self.connection} read")
        return [user for user in [Followers.strip(edge) for edge in followers] if followers]


class Following(Followers):
    log = logging.getLogger("yoshiki.Following")
    connection = 'following'

    @staticmethod
    def sub_parser(parser: argparse._SubParsersAction) -> None:
        sub = parser.add_parser(f"list-following")
        sub.set_defaults(query=Following)
        sub.add_argument('--username', help='The user name', required=True)


class Repositories(PaginatedQuery):
    log = logging.getLogger("yoshiki.Repositories")

    @staticmethod
    def sub_parser(parser: argparse._SubParsersAction) -> None:
        sub = parser.add_parser(f"list-repositories")
        sub.set_defaults(query=Repositories)
        sub.add_argument('--username', help='The user name', required=True)

    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__()
        self.username: str = args.username

    def graph_query(self) -> str:
        return dedent(
        """
        {
          user(login: "%(username)s") {
            repositories(isFork: false first: 100 orderBy: {direction: DESC field: STARGAZERS}%(after)s) {
              totalCount
              pageInfo {
                hasNextPage endCursor
              }
              edges {
                node {
                  nameWithOwner
                  defaultBranchRef {
                      name
                  }
                  description
                  stargazers(first: 100) {
                    totalCount
                    edges {
                      node {
                        login
                      }
                    }
                  }
                  forks {
                    totalCount
                  }
                  watchers {
                    totalCount
                  }
                  repositoryTopics(first: 100) {
                    edges {
                      node {
                        topic {
                          name
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """ % dict(after=', after: "%s"' % self.after if self.after else '',
                   username=self.username))

    def transform_result(self, ret: Raw) -> Results:
        if not self.count:
            self.count = int(ret['data']['user']['repositories']['totalCount'])
            self.log.info(f"{self.count} repositories to fetch")
        pageInfo = ret['data']['user']['repositories']['pageInfo']
        if pageInfo['hasNextPage']:
            self.after = pageInfo['endCursor']
        else:
            self.after = ''
        repos = [sr for sr in [SearchProjects.strip(r) for r in ret['data']['user']['repositories']['edges']] if sr]
        self.log.info("%s repositories read" % len(repos))
        return repos

queries = [SearchProjects, Followers, Following, Repositories]

def main() -> None:

    parser = argparse.ArgumentParser(prog='yoshiki')
    parser.add_argument(
        '--loglevel', help='logging level', default='INFO')
    parser.add_argument(
        '--token', help='The token used to query github api',
        required=True)
    parser.add_argument(
        '--json', help='Print a json list', action='store_true')
    sub_parser = parser.add_subparsers()
    [query.sub_parser(sub_parser) for query in queries]

    args = parser.parse_args()
    if not getattr(args, 'query', None):
        parser.print_help()
        return

    logging.basicConfig(
        level=getattr(logging, args.loglevel.upper()))

    gql = GithubGraphQLQuery(args.token)
    query = args.query(args)
    results = gql.run(query)
    if args.json:
        print(json.dumps(results))
    else:
        for result in results:
            print(result)


if __name__ == "__main__":
    main()
