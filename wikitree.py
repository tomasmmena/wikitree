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
                    

class TreeNode(object):
    """
    This class represents a node in the concept tree.
    """

    def __init__(self, query):
        """
        Initialize tree node.

        :param query: Query for this node.
        """
        self.query = query
        self.page = None
        self.name = None
        self.neighbours = []  # type: list[TreeNode]

    def fetch(self, depth: int = 2, width: int = 2):
        """
        Retrive information for this node in the tree from Wikipedia. Determine candidates for adjacent 
        nodes and fetch for those as well with depth-1.

        :param depth: Depth of search.
        """
        print(f'Fetching: {self.query}')
        try:
            self.page = wikipedia.page(self.query)
        except DisambiguationError as err:
            print(f'Disambiguating to {err.args[1][0]}')
            self.page = wikipedia.page(err.args[1][0])
        self.name = self.page.title
        
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
                    page = wikipedia.page(candidate)
                except DisambiguationError as err:
                    page = wikipedia.page(err.args[1][0])
                except PageError:
                    continue
                print(f'{candidate} -> {page.title}')
                if page.title != self.page.title:
                    selected_entities.append(candidate)

            # Get selected entitites
            for query in selected_entities:
                node = TreeNode(query)
                node.fetch(depth=depth - 1)
                self.neighbours.append(node)

    def display(self, indent=0):
        print(' ' * 4 * indent + self.name)
        for n in self.neighbours:
            n.display(indent + 1)


if __name__ == '__main__':
    print('Welcome to Wikitree!')
    args = parser.parse_args()

    root_node = TreeNode(args.query)
    root_node.fetch()

    root_node.display()

    # root_page = wikipedia.page(args.query)
    # entities = nlp(root_page.content).ents  # Entities extracted from the text
    # entity_counts = {}
    # for e in entities:
    #     entity_counts[(e.text, e.label_)] = entity_counts.get((e.text, e.label_), 0) + 1
    
    # print(
    #     tabulate(
    #         [(k[0], k[1], v) for k, v in sorted(entity_counts.items(), key=lambda _: _[1], reverse=True)]
    #     )
    # )
