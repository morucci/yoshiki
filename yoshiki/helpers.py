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
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

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
