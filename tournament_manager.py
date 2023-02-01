import os
import random
import subprocess
import socket

from datetime import datetime
from typing import List, Tuple
from multiprocessing import Process, Manager
from threading import Lock

from engine import Game, Player, STATUS
from config import *

# Tournament Config
TOURNAMENT_RESULT_PATH = 'tournament_results'
# BOTS = [('python_skeleton', './python_skeleton'),
#         ('cpp_skeleton', './cpp_skeleton'),
#         ('cpp_skeleton', './cpp_skeleton'),
#         ('cpp_skeleton', './cpp_skeleton')]

BOTS = [('A', './gtoish'),
        ('B', './week_3_bot')]
# Used to represent that a bot is out for a round
DUMMY_BOT_NAME = 'dummy_bot'
DUMMY_BOT_PATH = './'
DUMMY_BOT = (DUMMY_BOT_NAME, DUMMY_BOT_PATH)

NUM_CHAR_BOT_NAME = 25

class Elo:
    """
    Manages players' ELO rating.
    """
    def __init__(self, k, g, thread_manager):
        self.k 				= k
        self.g 				= g
        self.thread_manager = thread_manager
        self.rating_dict  	= self.thread_manager.dict()

    def get_ratings(self):
        return reversed(sorted(self.rating_dict.items(),
                                key = lambda elo: round(elo[1])))

    def add_player(self, name, rating):
        self.rating_dict[name] = rating

    def expect_result(self, player_1, player_2):
        exp = (player_2-player_1)/400.0
        return 1/((10.0**(exp))+1)

    def update(self, winner, loser):
        result = self.expect_result(self.rating_dict[winner], self.rating_dict[loser])
        self.rating_dict[winner] = self.rating_dict[winner] + (self.k*self.g)*(1 - result)  
        self.rating_dict[loser] = self.rating_dict[loser] + (self.k*self.g)*(0 - (1 -result))

class Tournament_Stats():
    WON = 'won_against'
    LOST = 'lost_against'

    NUM_WS = 'num_wins'
    NUM_LS = 'num_losses'

    # ELO parameters
    K_FACTOR = 16
    G_VALUE = 1
    STARTING_RATING = 1500

    def __init__(self, ):
        # Initialize mutex to update stats during the tournament
        # as games will be spawned concurrently
        self.mutex = Lock()
        self.thread_manager = None
        self.elo_league = None
        self.stats = None

    def init_stats(self, bots: List[Tuple]):
        '''
        Initializes the stats for each bots. It records the winning and losing
        frequencies between bots. Additionally, it initializes the ELO for all
        of the bots.
        '''
        self.thread_manager = Manager()
        self.elo_league = Elo(self.K_FACTOR, self.G_VALUE, self.thread_manager)
        self.stats = {}
        
        # Create a shared dicts for threads
        for bot_name, _ in bots:
            if bot_name == DUMMY_BOT_NAME:
                continue
            self.stats[bot_name] = self.thread_manager.dict()
            self.stats[bot_name][self.WON] = self.thread_manager.dict()
            self.stats[bot_name][self.LOST] = self.thread_manager.dict()
            self.stats[bot_name][self.NUM_WS] = 0
            self.stats[bot_name][self.NUM_LS] = 0
            # Add bot to the elo league object
            self.elo_league.add_player(bot_name, self.STARTING_RATING)

    def acquire_stats(self):
        self.mutex.acquire()

    def release_stats(self):
        self.mutex.release()

    def _update_stats(self, winner: str, loser: str):
        # Update winner
        if loser not in self.stats[winner][self.WON]:
            self.stats[winner][self.WON][loser] = 0
        self.stats[winner][self.WON][loser] += 1
        self.stats[winner][self.NUM_WS] += 1

        # Update loser
        if winner not in self.stats[loser][self.LOST]:
            self.stats[loser][self.LOST][winner] = 0
        self.stats[loser][self.LOST][winner] += 1
        self.stats[loser][self.NUM_LS] += 1

    def _update_elo(self, winner: str, loser: str):
        self.elo_league.update(winner, loser)

    def update(self, winner: str, loser: str):
        self._update_stats(winner, loser)
        self._update_elo(winner, loser)

    def get_stats_str(self):
        # TODO: Print more stats about the players

        # Print elo-related stats
        if not self.elo_league:
            return "ERROR: Did no print ELO ranking since it has not been initialized."
        
        elo_str = "\nELO Ranking\n"
        elo_str += f"{'Rank' : <8}{'Bot' : <20}{'ELO' : ^10}{'Wins' : ^10}{'Losses' : ^10}\n"
        bots_elo = self.elo_league.get_ratings()
        ranking_num = 1
        for bot_name, bot_elo in bots_elo:
            num_ws = self.stats[bot_name][self.NUM_WS]
            num_ls = self.stats[bot_name][self.NUM_LS]
            elo_str += f"{str(ranking_num) + ')'  : <8}{bot_name : <20}{round(bot_elo) : ^10}{num_ws : ^10}{num_ls : ^10}\n"
            ranking_num += 1
        return elo_str

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

        # Get the winner of the game
        winner, loser = self.get_winner_loser(players)
        
        # Write the log from the game
        name = 'gamelog_' + winner + '_' + loser + '.txt'
        full_log_path = os.path.join(self.log_dir, name)
        with open(full_log_path, 'w') as log_file:
            log_file.write('\n'.join(self.log))
        
        # Return early if there's a tie
        # That is, don't update the elo rating
        if winner == None:
            return

        # Update stats using a mutex
        self.stats_obj.acquire_stats()
        self.stats_obj.update(winner, loser)
        self.stats_obj.release_stats()

# TODO: Make the tuple representing a bot into a namedtuple for cleaner code
class Tournament_Manager():
    GENERATION_STR = 'gen_'
    ROUND_DIR_PREFIX = '_round_'

    # Tournament Parameters
    NUM_GAMES_PER_PAIR = 100

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

    def get_stats_str(self):
        return self.stats.get_stats_str()

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
        self.print_starting_msg()

        # Generate the tournament schedules
        tournament_schedule = self.create_tournament_schedule()
        
        for generation_num in range(1, self.NUM_GAMES_PER_PAIR + 1):
            print(25*'*' + "Round robin generation " + str(generation_num) + 25*'*')
            # Shuffle the tournament schedule to add variation
            random.shuffle(tournament_schedule)
            for round_num, round_schedule in enumerate(tournament_schedule):
                print(25*'-' + "Round num ", str(round_num + 1) + 25*'-')
                round_name = self.GENERATION_STR + str(generation_num) + self.ROUND_DIR_PREFIX + str(round_num + 1)
                round_dir = os.path.join(self.get_path(), round_name)

                self.prepare_dir(round_dir)
                round_game_procs = [Process(target=Tournament_Game(round_dir, self.stats).run, args=([player_1, player_2],))\
                        for player_1, player_2 in round_schedule]
                # Launch the games from one round in parallel
                for game_proc in round_game_procs:
                    game_proc.start()
                # Wait for the games to finish
                for game_proc in round_game_procs:
                    game_proc.join()

                # Print stats at the end of the round
                print(self.get_stats_str())
            print()

        # Save final elo as a txt file
        final_results_path = os.path.join(self.path, 'results.txt')
        with open(final_results_path, 'w') as final_results:
            final_results.write(self.get_stats_str())
        
if __name__ == '__main__':
    # By default, the name of the tournament is the current time
    tournament_name = datetime.now().strftime("%y_%m_%d_%H_%M_%S")
    current_dir = os.getcwd()
    tournament_path = os.path.join(current_dir,
        TOURNAMENT_RESULT_PATH, tournament_name)
    
    tournament_manager = Tournament_Manager(tournament_name,
        tournament_path, BOTS)

    tournament_manager.run()
