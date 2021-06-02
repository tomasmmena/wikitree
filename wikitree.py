"""
Main module for the wikitree application.
"""

import argparse
import re
import string
from numpy.lib.function_base import copy

from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from transformers import pipeline

import pickle
import wikipedia
from copy import copy
from pathlib import Path
from pyvis.network import Network
from wikipedia.exceptions import DisambiguationError, PageError
from tabulate import tabulate

parser = argparse.ArgumentParser()
parser.add_argument('--query', '-q', type=str,
                    help='Query to retrieve as root from Wikipedia.')
parser.add_argument('--session', '-s', type=str,
                    help='Name of the session.')
parser.add_argument('--label', '-l', type=str, default='PER',
                    help='Label for the initial node.')
parser.add_argument('--depth', '-d', type=int, default=2,
                    help='Max tree depth.')
parser.add_argument('--width', '-w', type=int, default=2,
                    help='Neighbours to fetch for each node being expanded.')
parser.add_argument('--single-page', action='store_true',
                    help='Provide metrics for a single page rather than building a whole tree.')

ALLOWED_LABELS = ('PER', 'ORG', 'LOC')
NODE_COLORS = ('#f8ffe5', 
               '#06d6a0',
               '#1b9aaa',
               '#ef476f',
               '#ef476f')


class RelationshipGraph(object):
    """
    This class represents a relationship graph containing multiple nodes and the edges connecting them.
    """

    def __init__(self, query: str, depth: int = 2, width: int = 2, initial_label = 'PER') -> None:
        """
        Initialize an empty graph with an initial query.

        :param query: This is the value for the query to generate the initial node in the graph. The value 
            will be updated when the node is fetched if there is a disambiguation error or if the name of 
            the page is different.
        """
        self.initial_query = query
        self.initial_label = initial_label
        self.nodes = {}     # nodes indexed by key/name
        self.edges = set()  # set of tuples of three elements, the keys for the nodes at either end of the 
                            # edge and the label for the relationship
        self.depth = depth
        self.width = width

    def fetch(self):
        """
        Fetch nodes and their relationships from Wikipedia.
        """
        initial_node = GraphNode(self.initial_query, node_type=self.initial_label)
        initial_node.fetch(self, self.depth, self.width)

    def display(self, show: bool = False) -> Network:
        """
        Use pyvis to generate an interactive visualization of this instance of the relationship graph.

        :param show: If set to True the pyvis network will be exported to an HTML document and openned in 
            the browser.
        """
        color_theme = {k: v for k, v in zip(ALLOWED_LABELS, NODE_COLORS)}

        network = Network(
            height='100%',
            width='100%'
        )
        for k, v in self.nodes.items():
            network.add_node(
                k,
                label=k,
                title=v.label(),
                color=color_theme[v.node_type]
            )
        network.add_edges([t[:2] for t in self.edges])

        if show:
            network.toggle_physics(True)
            network.set_edge_smooth('dynamic')
            network.show('output.html')
        
        return network


class GraphNode(object):
    """
    This class represents a node in the concept graph.
    """

    def __init__(self, query: str, node_type: str = None):
        """
        Initialize graph node.

        :param query: Query for this node.
        :param node_type: String identifier for the type of node. This admits entity types supported by the 
            base NER implementation on BERT. Accepted values are PER, ORG and LOC.
        """
        self.query = query
        self.page = None
        self.name = None
        self.node_type = node_type

        self.all_entities = None
        self.selected_entities = None

    def get_page(self, hint_text: str = None) -> wikipedia.WikipediaPage:
        """
        Returns the wikipedia page for a query. Optionally, it can take a hint text for disambiguation, 
        typically this would be the text content for the source node.

        :param hint_text: Optional text to be used as an aid for disambiguation.
        """
        print(f'Fetching: {self.query}')
        if self.page is None:
            try:
                self.page = wikipedia.page(self.query, auto_suggest=False)
            except DisambiguationError as err:
                regex = re.compile('^.* \((?P<hint>.+)\)$')
                sw = set(stopwords.words('english')) | {'born'} | set(string.punctuation)  # stopwords
                candidate = None
                max_count = 0
                if hint_text is not None and self.node_type == 'PER':
                    for alternative in err.args[1]:
                        if '(name)' in alternative or '(surname)' in alternative or '(given name)' in alternative or '(disambiguation)' in alternative:
                            print('not proper noun')
                            continue
                        if match := regex.match(alternative):
                            hint = match.groupdict()['hint']
                            occurrence_count = sum([hint_text.count(token) for token in word_tokenize(hint) if token not in sw])
                            print(f'{alternative} -> {occurrence_count}')
                            if occurrence_count > max_count:
                                max_count = occurrence_count
                                candidate = alternative

                print(f'Disambiguating to {candidate or err.args[1][0]}')
                for page in [candidate] + err.args[1]:
                    if page is not None:
                        try:
                            self.page = wikipedia.page(page, auto_suggest=False)
                            break
                        except Exception as err2:
                            print(f'{err2} fetching {page}.')
            
            self.name = self.page.title
        return self.page

    def fetch(self, graph: RelationshipGraph, depth: int = 2, width: int = 2, hint_text: str = None):
        """
        Retrive information for this node in the graph from Wikipedia. Determine candidates for adjacent 
        nodes and fetch for those as well with depth-1.

        :param depth: Depth of search.
        :param width: Number of nodes to expand from a single node.
        :param hint_text: Content text from the source node for assisting with disambiguation.
        """
        self.get_page(hint_text=hint_text)

        graph.nodes[self.name] = self
        
        processed = set()
        if depth > 0:
            # Extract entities
            entities = []
            content = copy(self.page.content)

            # Cut off references, external links and see also sections
            for section in ('== References ==', '== See also ==', '== External links =='):
                content = content.split(section)[0]

            while content:
                chunk, content = content[:2000], content[2000:]
                entities.extend(ner(chunk))  # Entities extracted from the text
            entity_counts = {}

            for e in entities:
                entity_counts[(e['word'], e['entity_group'])] = entity_counts.get((e['word'], e['entity_group']), 0) + 1

            self.entities = entity_counts

            # Select entities
            candidate_entities = [k for k, v in sorted(entity_counts.items(), key=lambda _: _[1]) if k[1] in ALLOWED_LABELS]
            person_entities = []
            location_entities = []
            org_entities = []
            linked_entities = []
            while depth > 0 and candidate_entities and len(person_entities) + len(linked_entities) < width:
                candidate, label = candidate_entities.pop()
                if '##' in candidate or len(candidate) < 2:  # Discard ner's partial tokens and single letter tokens
                    continue

                # Promotion logic: if there is a bigram, trigram or ngram further down the list that contains the value, we promote it
                # to be processed in place of the current candidate. We add it to a set of already processed candidates so as not to process it again.
                if label == 'PER':
                    if candidate in processed:
                        continue
                    for processed_candidate in processed:
                        if candidate.lower() in processed_candidate.lower():
                            continue
                    if len(candidate.split(' ')) == 1:
                        for other_candidate, label in reversed(candidate_entities):
                            if candidate.lower() in other_candidate.lower() and len(other_candidate.split(' ')) > 1:
                                print(f'Promoting {other_candidate} in place of {candidate}.')
                                candidate = other_candidate
                                break

                processed.add(candidate)
                
                try:
                    page = GraphNode(candidate).get_page(hint_text=self.page.content)
                except (PageError, KeyError):  # KeyError controls for an internal error in the wikipedia client.
                    continue
                print(f'{candidate} -> {page.title}')
                if '(name)' in page.title or '(surname)' in page.title or '(given name)' in page.title or '(disambiguation)' in page.title:
                    continue

                if page.title != self.page.title and page.title not in graph.nodes:
                    {
                        'PER': person_entities,
                        'ORG': org_entities,
                        'LOC': location_entities
                    }.get(label, []).append((candidate, label))
                elif page.title != self.page.title and label == 'PER':
                    linked_entities.append(candidate)
                    graph.edges.add((*sorted([self.name, page.title]), 'UNK'))

            selected_entities = location_entities[:2] + org_entities[:2] + person_entities
            self.selected_entities = selected_entities

            # Get selected entitites
            for query, label in selected_entities:
                if query in graph.nodes:
                    node = graph.nodes.get(query)
                else:
                    node = GraphNode(query, node_type=label)
                    node.fetch(graph, depth=depth - 1 if label == 'PER' else 0, width=width, hint_text=self.page.content)
                
                graph.edges.add((*sorted([self.name, node.name]), 'UNK'))

    def label(self, max_lenght: int = 100) -> str:
        """
        Get a set of labels for the entity represented with this node.

        :param max_lenght: Max lenght for the label.
        :return: A list of text labels.
        """
        first_sentence = sent_tokenize(self.page.summary)[0]
        regex = re.compile('^.*(is a |is an|was a |was an |was the |is the )(?P<summary>.*).$')
        if match := regex.match(first_sentence):
            label = match.groupdict()['summary']
            if len(label) > max_lenght:
                label = label[:max_lenght] + '...'
            return label

        return ''


    def summary(self):
        """
        Print a debug summary for the node.
        """
        print('\nEntities:\n')
        print(tabulate([(k[0], k[1], v) for k, v in sorted(self.entities.items(), key=lambda _: _[1], reverse=True) if k[1] in ALLOWED_LABELS]))


if __name__ == '__main__':
    print('Welcome to Wikitree!')
    args = parser.parse_args()
    Path('sessions').mkdir(exist_ok=True)

    if args.query is None and args.session is None:
        raise argparse.ArgumentError(None, 'A query or a session should be provided.')

    if args.query is not None:
        ner = pipeline('ner', grouped_entities=True)
        if args.single_page:
            # Just load a single node graph and show debugging information.
            graph = RelationshipGraph(args.query, depth=1, initial_label=args.label)
            graph.fetch()
            list(graph.nodes.values())[0].summary()
        elif args.session is not None:
            session_path = Path(f'sessions/{args.session}.session')
            if session_path.is_file():
                # Load session from file system
                with open(session_path.as_posix(), 'rb') as f:
                    graph = pickle.load(f)
                new_node = graph.nodes.get(args.query, None) or GraphNode(args.query, node_type=args.label)
                new_node.fetch(graph, args.depth, args.width)
            else:
                # Create new session
                graph = RelationshipGraph(args.query, depth=args.depth, width=args.width, initial_label=args.label)
                graph.fetch()

            graph.display(show=True)

            user_command = ''
            while user_command.lower() not in ('y', 'n'):
                user_command = input('Save (y/n):')
            if user_command.lower() == 'y':
                with open(session_path.as_posix(), 'wb') as f:
                    pickle.dump(graph, f)
            
        else:
            graph = RelationshipGraph(args.query, depth=args.depth, width=args.width, initial_label=args.label)
            graph.fetch()

            graph.display(show=True)

    else:
        # simply render the session
        session_path = Path(f'sessions/{args.session}.session')
        if session_path.is_file():
            with open(session_path.as_posix(), 'rb') as f:
                graph = pickle.load(f)
            graph.display(show=True)
        else:
            raise argparse.ArgumentError(None, f'Could not find session <{args.session}>!')

