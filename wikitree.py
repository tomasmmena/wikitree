"""
Main module for the wikitree application.
"""

import argparse
import scrapy
import wikipedia

parser = argparse.ArgumentParser()
parser.add_argument('query', type=str, metavar='Q',
                    help='Query to retrieve as root from Wikipedia.')
parser.add_argument('--depth', '-d', type=int, default=2,
                    help='Max tree depth.')
                    

if __name__ == '__main__':
    print('Welcome to Wikitree!')
    args = parser.parse_args()

    root_page = wikipedia.page(args.query)
    print(root_page.content)
