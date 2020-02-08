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
from time import sleep
from datetime import datetime


class GithubGraphQLQuery(object):

    log = logging.getLogger("fgp.GithubGraphQLQuery")

    def __init__(self, token):
        self.url = 'https://api.github.com/graphql'
        self.headers = {'Authorization': 'token %s' % token}
        self.session = requests.session()
        # Will get every 25 requests
        self.get_rate_limit_rate = 25
        self.query_count = 0
        # Set an initial value
        self.quota_remain = 5000
        self.get_rate_limit()

    def get_rate_limit(self):
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

    def wait_for_call(self):
        if self.quota_remain <= 150:
            until_reset = self.resetat - datetime.utcnow()
            self.log.info(
                "Quota remain: %s/calls delay until "
                "reset: %s/secs waiting ..." % (
                    self.quota_remain, until_reset.seconds))
            sleep(until_reset.seconds + 60)
            self.get_rate_limit()

    def getRateLimit(self):
        qdata = '''{
          rateLimit {
            limit
            cost
            remaining
            resetAt
          }
        }'''
        data = self.query(qdata, skip_get_rate_limit=True)
        return data['data']['rateLimit']

    def query(self, qdata, skip_get_rate_limit=False, ignore_not_found=False):
        if not skip_get_rate_limit:
            if self.query_count % self.get_rate_limit_rate == 0:
                self.get_rate_limit()
            self.wait_for_call()
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
        return ret


class GithubTopByStars():

    log = logging.getLogger("fgp.GithubTopByStars")

    def __init__(self, gql, terms):
        self.gql = gql
        self.terms = " " + terms if terms else ""

    def get_page(self, stars, after=''):
        body = """
        {
          search(query: "stars:>%(stars)s%(terms)s is:public fork:false archived:false sort:stars-asc", type: REPOSITORY, first: 25, %(after)s) {
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
        }"""
        if after:
            after = 'after: "%s"' % after
        qdata = body % {'after': after, 'stars': stars, 'terms': self.terms}
        return self.gql.query(qdata=qdata)

    def strip(self, _repo):
        _repo = _repo['node']
        try:
            return {
                'name': _repo['nameWithOwner'],
                'owner': _repo['nameWithOwner'].split('/')[0],
                'default_branch': _repo['defaultBranchRef']['name'],
                'description': _repo['description'] or '',
                'stars': _repo['stargazers']['totalCount'],
                'forks': _repo['forks']['totalCount'],
                'watchers': _repo['watchers']['totalCount'],
                'topics': [
                    t['node']['topic']['name'] for t in
                    _repo['repositoryTopics']['edges']]
            }
        except Exception:
            self.log.info("Error to parse repository data %s" % _repo)
            return None

    def get_repos(self, stars):
        repos = []
        repo_count = None
        while True:
            after = ''
            while True:
                ret = self.get_page(stars, after=after)
                if not repo_count:
                    repo_count = ret['data']['search']['repositoryCount']
                    self.log.info("%s repositories to fetch" % repo_count)
                pageInfo = ret['data']['search']['pageInfo']
                _repos = ret['data']['search']['edges']
                _repos = [sr for sr in [self.strip(r) for r in _repos] if sr]
                repos.extend(_repos)
                self.log.info("%s repositories read" % len(repos))
                if pageInfo['hasNextPage']:
                    after = pageInfo['endCursor']
                else:
                    break
            if len(repos) < repo_count and len(_repos) == 25:
                stars = repos[-1]['stars']
            else:
                break
        return sorted(repos, key=lambda x: x['stars'], reverse=True)epos


def main():

    parser = argparse.ArgumentParser(prog='fgp')
    parser.add_argument(
        '--loglevel', help='logging level', default='INFO')
    parser.add_argument(
        '--token', help='The token used to query github api',
        required=True)
    parser.add_argument(
        '--stars', help='Gather projects with stars > to',
        required=True)
    parser.add_argument(
        '--terms', help='Extra search term such as language:ocaml')
    parser.add_argument(
        '--json', help='Print a json list', action='store_true')

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.loglevel.upper()))

    gql = GithubGraphQLQuery(args.token)
    reqc = GithubTopByStars(gql, args.terms)
    repos = reqc.get_repos(args.stars)
    if args.json:
        print(json.dumps(repos))
    else:
        for repo in repos:
            print(repo)


if __name__ == "__main__":
    main()
