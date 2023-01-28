import os
import random
import subprocess
import socket

from datetime import datetime
from typing import List, Tuple
from multiprocessing import Process
from threading import Lock
from elosports.elo import Elo

from engine import Game, Player, STATUS
from config import *

# Tournament Config
TOURNAMENT_RESULT_PATH = 'tournament_results'
# BOTS = [('python_skeleton', './python_skeleton'),
#         ('cpp_skeleton', './cpp_skeleton'),
#         ('cpp_skeleton', './cpp_skeleton'),
#         ('cpp_skeleton', './cpp_skeleton')]

BOTS = [('A', './preflop_hand'),
        ('B', './week_3_bot')]
# Used to represent that a bot is out for a round
DUMMY_BOT_NAME = 'dummy_bot'
DUMMY_BOT_PATH = './'
DUMMY_BOT = (DUMMY_BOT_NAME, DUMMY_BOT_PATH)

NUM_CHAR_BOT_NAME = 25

class Tournament_Stats():
    WON = 'won_against'
    LOST = 'lost_against'

    # ELO parameters
    K_FACTOR = 16
    G_VALUE = 1
    HOMEFIELD = 0
    STARTING_RATING = 1200
    WINNER_HOME = False

    def __init__(self):
        # Initialize mutex to update stats during the tournament
        # as games will be spawned concurrently
        self.mutex = Lock()
        self.stats = None
        self.elo_league = None

    def init_stats(self, bots: List[Tuple]):
        '''
        Initializes the stats for each bots. It records the winning and losing
        frequencies between bots. Additionally, it initializes the ELO for all
        of the bots.
        '''
        self.stats = {}
        self.elo_league = Elo(k = self.K_FACTOR, g = self.G_VALUE, homefield = self.HOMEFIELD)
        for bot_name, _ in bots:
            self.stats[bot_name] = {'won_against': {}, 'lost_against': {}}
            # Add bot to the elo league object
            self.elo_league.addPlayer(bot_name, rating = self.STARTING_RATING)

    def acquire_stats(self):
        self.mutex.acquire()

    def release_stats(self):
        self.mutex.release()

    def _update_stats(self, winner: str, loser: str):
        # Update winner
        if loser not in self.stats[winner][self.WON]:
            self.stats[winner][self.WON][loser] = 0
        self.stats[winner][self.WON][loser] += 1

        # Update loser
        if winner not in self.stats[loser][self.LOST]:
            self.stats[loser][self.LOST][winner] = 0
        self.stats[loser][self.LOST][winner] += 1

    def _update_elo(self, winner: str, loser: str):
        self.elo_league.gameOver(winner, loser, self.WINNER_HOME)

    def update(self, winner: str, loser: str):
        self._update_stats(winner, loser)
        self._update_elo(winner, loser)

    def print_stats(self):
        # TODO: Print stats about the players

        print(str(self.stats) + "\n")

        # Print elo-related stats
        if self.elo_league:
            elo_str = "ELO Ranking\n"
            sorted_bots_elo = reversed(sorted(self.elo_league.ratingDict.items(),
                                        key = lambda elo: round(elo[1])))
            ranking_num = 1
            for bot in sorted_bots_elo:
                elo_str += "{}) {}: {}\n".format(ranking_num, bot[0], round(bot[1]))
                ranking_num += 1
            print(elo_str)
        else:
            print("ERROR: Did no print ELO ranking since it has not been initialized.")

class Tournament_Player(Player):
    def stop(self, output_dir: str):
        '''
        Closes the socket connection and stops the pokerbot.
        '''
        if self.socketfile is not None:
            try:
                self.socketfile.write('Q\n')
                self.socketfile.close()
            except socket.timeout:
                print('Timed out waiting for', self.name, 'to disconnect')
            except OSError:
                print('Could not close socket connection with', self.name)
        if self.bot_subprocess is not None:
            try:
                outs, _ = self.bot_subprocess.communicate(timeout=CONNECT_TIMEOUT)
                self.bytes_queue.put(outs)
            except subprocess.TimeoutExpired:
                print('Timed out waiting for', self.name, 'to quit')
                self.bot_subprocess.kill()
                outs, _ = self.bot_subprocess.communicate()
                self.bytes_queue.put(outs)
        with open(os.path.join(output_dir, self.name + '.txt'), 'wb') as log_file:
            bytes_written = 0
            for output in self.bytes_queue.queue:
                try:
                    bytes_written += log_file.write(output)
                    if bytes_written >= PLAYER_LOG_SIZE_LIMIT:
                        break
                except TypeError:
                    pass

class Tournament_Game(Game):
    def __init__(self, log_dir: str, stats_obj: Tournament_Stats):
        super().__init__()
        self.log_dir = log_dir
        self.stats_obj = stats_obj

    def get_winner_loser(self, players):
        winner = None
        loser = None
        if players[0].bankroll > players[1].bankroll:
            winner = players[0].name
            loser = players[1].name
        elif players[1].bankroll > players[0].bankroll:
            winner = players[1].name
            loser = players[0].name
        return winner, loser

    def run(self, players: List[Tournament_Player]):
        '''
        Runs one game between two pokerbots.
        '''
        # Terminate earlier if one of the players
        # is a dummy bot
        if players[0].name == DUMMY_BOT_NAME or\
                players[1].name == DUMMY_BOT_NAME:
            return

        # Initialize and activate bots
        for player in players:
            player.build()
            player.run()

        # Run the round of hands between two bots
        for round_num in range(1, NUM_ROUNDS + 1):
            self.log.append('')
            self.log.append('Round #' + str(round_num) + STATUS(players))
            self.run_round(players)
            players = players[::-1]
        self.log.append('')
        self.log.append('Final' + STATUS(players))
        for player in players:
            player.stop(self.log_dir)
        
        # Write the log from the game
        name = 'gamelog_' + players[0].name + '_' + players[1].name + '.txt'
        full_log_path = os.path.join(self.log_dir, name)
        with open(full_log_path, 'w') as log_file:
            log_file.write('\n'.join(self.log))

        # Get the winner of the game
        winner, loser = self.get_winner_loser(players)
        # Return early if there's a tie
        if winner == None:
            return

        # Update statistics
        self.stats_obj.acquire_stats()
        self.stats_obj.update(winner, loser)
        self.stats_obj.release_stats()

# TODO: Make the tuple representing a bot into a namedtuple for cleaner code
class Tournament_Manager():
    GENERATION_STR = 'gen_'
    ROUND_DIR_PREFIX = '_round_'

    # Tournament Parameters
    NUM_GAMES_PER_PAIR = 2

    def __init__(self, name: str, path: str, bots: List[Tuple]):
        self.name = name
        self.path = path
        self.bots = bots[:]

        # Ensure that the tournament has an even number of players to create the 
        # round robin schedules
        if len(self.bots)%2 != 0:
            self.bots.append(DUMMY_BOT)

        self.num_bots = len(self.bots)
        
        # Create player objects based on the info from the bots
        self.players = []
        for bot_name, bot_path in self.bots:
            self.players.append(Tournament_Player(bot_name, bot_path))
        
        self.stats = Tournament_Stats()
        self.stats.init_stats(self.bots)

    def get_name(self):
        return self.name

    def get_path(self):
        return self.path

    def print_starting_msg(self):
        bots_info = "\nBots in the tournament:\n"
        bots_info += "\tName" +\
            " "*(NUM_CHAR_BOT_NAME - len("Name")) +\
            "Path\n"
        for bot_name, bot_path in self.bots: 
            bots_info += "\t{}".format(bot_name) +\
                " "*(NUM_CHAR_BOT_NAME - len(bot_name)) +\
                "{}".format(bot_path) + "\n"
        print("Starting tournament '{}'...".format(self.get_name()))
        print(bots_info)

    def prepare_dir(self, path):
        if not os.path.exists(path):
            os.makedirs(path)

    def create_tournament_schedule(self):
        '''
        Implements the following scheduling algorithm for the tournament
        https://en.wikipedia.org/wiki/Round-robin_tournament#Scheduling_algorithm.
        A round schedule is generated by placing players into two rows. Then, the
        players are paired up across columns. When there is an odd number of players,
        there exists a dummy player that we can pair up to indicate a player will 
        not participate in the current round.

        Returns: a list of round schedules for Player objects participating in the 
        tournament.
        '''
        # Ensure that the number of players is even
        num_players = len(self.players)
        assert num_players%2 == 0

        tournament_schedule = []
        middle_idx = int(num_players/2)
        top_row = self.players[:middle_idx]
        bottom_row = self.players[middle_idx:]
        bottom_row.reverse()

        for round_num in range(1, num_players):
            round_schedule = []
            for game_idx in range(middle_idx):
                round_schedule.append((top_row[game_idx], bottom_row[game_idx]))
            tournament_schedule.append(round_schedule)

            # Move the players clockwise except for the top left player
            next_top_row = [top_row[0]] + [bottom_row[0]] + top_row[1:-1]
            next_bottom_row = bottom_row[1:] + [top_row[-1]]

            # Update the top row and bottom schedules for the next round
            top_row = next_top_row
            bottom_row = next_bottom_row
        return tournament_schedule

    def run(self):
        # Generate the tournament schedules
        print("Running tournament...\n")
        tournament_schedule = self.create_tournament_schedule()
        
        for generation_num in range(1, self.NUM_GAMES_PER_PAIR + 1):
            print("Round robin generation " + str(generation_num))
            # Shuffle the tournament schedule to add variation
            random.shuffle(tournament_schedule)
            for round_num, round_schedule in enumerate(tournament_schedule):
                print("Round num ", round_num + 1)
                round_name = self.GENERATION_STR + str(generation_num) + self.ROUND_DIR_PREFIX + str(round_num + 1)
                round_dir = os.path.join(self.get_path(), round_name)

                self.prepare_dir(round_dir)
                round_game_procs = [Process(target=Tournament_Game(round_dir, self.stats).run, args=([player_1, player_2],))\
                        for player_1, player_2 in round_schedule]
                # Launch the games in parallel
                for game_proc in round_game_procs:
                    game_proc.start()
                # Wait for the games to finish
                for game_proc in round_game_procs:
                    game_proc.join()
            print()

if __name__ == '__main__':
    # By default, the name of the tournament is the current time
    tournament_name = datetime.now().strftime("%y_%m_%d_%H_%M_%S")
    current_dir = os.getcwd()
    tournament_path = os.path.join(current_dir,
        TOURNAMENT_RESULT_PATH, tournament_name)

    # Prepare the directory to hold results
    # prepare_dir(tournament_path)
    
    tournament_manager = Tournament_Manager(tournament_name,
        tournament_path, BOTS)

    tournament_manager.run()
    # tournament_manager.print_starting_msg()

    # tournament_manager.stats.acquire_stats()

    # tournament_manager.stats.print_stats()

    # tournament_manager.stats.release_stats()
