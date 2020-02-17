# Yoshiki crawler

## What is this ?

A simple Python library of GraphQL queries + a CLI to query the Github API version 4. Yoshiki provides the following facilities:

* search-projects: query the list of popular source repositories with at least N stars ordered by stars.
* list-followers: query the list of followers of a given user.
* list-following: query the list of users a given user is following.
* list-repositories: query the list of repositories a given user own.
* list-stargazers: query the list of stargazers of a given repository.
* list-watchers: query the list of watchers of a given repository.

## How to install

Simply run:

```
$ python3 setup.py install --user
```

# Usage

You first need to generate a Github API token without ant specific right then you can start to run Yoshiki.

```
$ python3 ~/.local/bin/yoshiki --token <token> search-projects --stars 50000
```

## How to help ?

Simply open PRs/Issues ! Contributions are welcome !
