"""
Main module for the wikitree application.
"""

import argparse
import spacy
nlp = spacy.load('en_core_web_sm')

import wikipedia
from wikipedia.exceptions import DisambiguationError, PageError
from tabulate import tabulate

parser = argparse.ArgumentParser()
parser.add_argument('query', type=str, metavar='Q',
                    help='Query to retrieve as root from Wikipedia.')
parser.add_argument('--depth', '-d', type=int, default=2,
                    help='Max tree depth.')


class RelationshipGraph(object):
    """
    This class represents a relationship graph containing multiple nodes and the edges connecting them.
    """

    def __init__(self, query: str, depth: int = 2, width: int = 2) -> None:
        """
        Initialize an empty graph with an initial query.

        :param query: This is the value for the query to generate the initial node in the graph. The value 
            will be updated when the node is fetched if there is a disambiguation error or if the name of 
            the page is different.
        """
        self.initial_query = query
        self.nodes = {}  # nodes indexed by key/name
        self.edges = []  # set of tuples of three elements, the keys for the nodes at either end of the 
                         # edge and the label for the relationship
        self.depth = depth
        self.width = width

    def fetch(self):
        """
        Fetch nodes and their relationships from Wikipedia.
        """
        initial_node = GraphNode(self.initial_query)
        initial_node.fetch(self, self.depth, self.width)

    def display(self):
        print(tabulate(
            self.edges,
            headers=('From', 'To', 'Label')
        ))
        print('\n' + '\n'.join([_.name for _ in self.nodes.values()]))


class GraphNode(object):
    """
    This class represents a node in the concept graph.
    """

    def __init__(self, query):
        """
        Initialize graph node.

        :param query: Query for this node.
        """
        self.query = query
        self.page = None
        self.name = None

    def fetch(self, graph: RelationshipGraph, depth: int = 2, width: int = 2):
        """
        Retrive information for this node in the graph from Wikipedia. Determine candidates for adjacent 
        nodes and fetch for those as well with depth-1.

        :param depth: Depth of search.
        """
        print(f'Fetching: {self.query}')
        try:
            self.page = wikipedia.page(self.query, auto_suggest=False)
        except DisambiguationError as err:
            print(f'Disambiguating to {err.args[1][0]}')
            self.page = wikipedia.page(err.args[1][0], auto_suggest=False)
        self.name = self.page.title

        graph.nodes[self.name] = self
        
        if depth > 0:
            # Extract entities
            entities = nlp(self.page.content).ents  # Entities extracted from the text
            entity_counts = {}

            for e in entities:
                entity_counts[(e.text, e.label_)] = entity_counts.get((e.text, e.label_), 0) + 1

            # Select entities
            labels = ('PERSON', )
            candidate_entities = [k[0] for k, v in sorted(entity_counts.items(), key=lambda _: _[1]) if k[1] in labels]
            selected_entities = []
            while candidate_entities and len(selected_entities) < width:
                candidate = candidate_entities.pop()
                try:
                    page = wikipedia.page(candidate, auto_suggest=False)
                except DisambiguationError as err:
                    page = wikipedia.page(err.args[1][0], auto_suggest=False)
                except PageError:
                    continue
                print(f'{candidate} -> {page.title}')
                if page.title != self.page.title and page.title not in graph.nodes:
                    selected_entities.append(candidate)

            # Get selected entitites
            for query in selected_entities:
                if query in graph.nodes:
                    node = graph.nodes.get(query)
                else:
                    node = GraphNode(query)
                    node.fetch(graph, depth=depth - 1, width=width)
                
                graph.edges.append((self.name, node.name, 'UNK'))


if __name__ == '__main__':
    print('Welcome to Wikitree!')
    args = parser.parse_args()

    graph = RelationshipGraph(args.query)
    graph.fetch()

    graph.display()
