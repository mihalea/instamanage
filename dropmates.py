#!/usr/bin/env python3


import argparse
import atexit
import logging
import signal

from file_repository import read_json
from log import create_logger
from session_controller import SessionController
from user_service import UserService

logger = create_logger("stats")


class Application:
    def __init__(self, username, password, rebuild):
        self.session = SessionController()
        self.users = UserService()

        self.session.set_credentials(username, password)
        if rebuild or not self.users.read_cache():
            self.users.rebuild_cache(self.session)

        signal.signal(signal.SIGTERM, self.session.logout)
        atexit.register(self.session.logout)

    def __display_users(self, users):
        for u in users:
            print(u)

        print("Displayed %i users" % len(users))

    def display_followers(self, verified):
        self.__display_users(self.users.find_followers(verified))

    def display_following(self, verified):
        self.__display_users(self.users.find_following(verified))

    def display_shame(self, verified):
        self.__display_users(self.users.find_shame(verified))

    def auto_unfollow(self, verified, interactive):
        users = self.users.find_shame(verified)
        if interactive:
            users = [u for u in users if self.request_unfollow(u)]

        self.session.unfollow_all(users)

    def request_unfollow(self, user):
        def req_input():
            k = input("Do you want do unfollow %s (@%s)? [y/n] " % (user.full_name, user.username))
            return k.lower()

        key = req_input()
        while key not in ['y', 'n']:
            key = req_input()

        return key == 'y'

    def close(self):
        self.session.logout()


if __name__ == "__main__":
    example_text = '''example:

  # Show users who follow you and are not verified
  dropmates.py -c config.json -fx

  # Show users who don't follow you back, with debug messages
  dropmates.py -u username -p password -svv

  # Ignore local cache and automatically unfollow users, providing a UI for selecting which users
  dropmates.py -c config -ai'''

    parser = argparse.ArgumentParser(description='Analyze and process instagram followers',
                                     epilog=example_text,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("-u", "--username", help='Instagram username')
    parser.add_argument("-p", "--password", help='Instagram password')
    parser.add_argument("-c", "--config", help='Application config file')
    parser.add_argument("-r", "--rebuild", action="store_true", help='Rebuild the user cache from the web')
    parser.add_argument("-x", "--verified", action="store_true", help='Filter by hiding verified users')
    parser.add_argument("-v", "--verbose", action="count", help='Verbose logging')
    parser.add_argument("-i", "--interactive", action="store_true", help='Interactive unfollowing')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--followers", action="store_true", help="Show your followers")
    group.add_argument("-o", "--following", action="store_true", help="Show the user that you follow")
    group.add_argument("-s", "--shame", action="store_true", help="Show those users that don't follow you back")
    group.add_argument("-a", "--auto", action="store_true", help='Automatically unfollow those users '
                                                                 'that don\'t follow you back')

    args = parser.parse_args()

    if args.verbose == 2:
        logger.setLevel(logging.DEBUG)
    elif args.verbose == 1:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.CRITICAL)

    app = None
    un = args.username
    pw = args.password
    if not un and not pw and args.config:
        logger.debug("Reading username and password from config file")
        config = read_json(args.config)
        un = config['username']
        pw = config['password']

    if not un and not pw:
        logger.critical("No credentials found")
        exit()

    app = Application(un, pw, args.rebuild)

    if args.followers:
        app.display_followers(args.verified)
    elif args.following:
        app.display_following(args.verified)
    elif args.shame:
        app.display_shame(args.verified)
    elif args.auto:
        app.auto_unfollow(args.verified, args.interactive)

    app.close()
