'''
Simple example pokerbot, written in Python.
'''
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot


class Player(Bot):
    '''
    A pokerbot.
    '''

    def __init__(self):
        '''
        Called when a new game starts. Called exactly once.

        Arguments:
        Nothing.

        Returns:
        Nothing.
        '''
        pass

    def handle_new_round(self, game_state, round_state, active):
        '''
        Called when a new round starts. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        #my_bankroll = game_state.bankroll  # the total number of chips you've gained or lost from the beginning of the game to the start of this round
        #game_clock = game_state.game_clock  # the total number of seconds your bot has left to play this game
        #round_num = game_state.round_num  # the round number from 1 to NUM_ROUNDS
        #my_cards = round_state.hands[active]  # your cards
        #big_blind = bool(active)  # True if you are the big blind
        pass

    def handle_round_over(self, game_state, terminal_state, active):
        '''
        Called when a round ends. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        terminal_state: the TerminalState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        #my_delta = terminal_state.deltas[active]  # your bankroll change from this round
        #previous_state = terminal_state.previous_state  # RoundState before payoffs
        #street = previous_state.street  # int of street representing when this round ended
        #my_cards = previous_state.hands[active]  # your cards
        #opp_cards = previous_state.hands[1-active]  # opponent's cards or [] if not revealed
        pass

    def get_action(self, game_state, round_state, active):
        '''
        Where the magic happens - your code should implement this function.
        Called any time the engine needs an action from your bot.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Your action.
        '''
        legal_actions = round_state.legal_actions()  # the actions you are allowed to take
        street = round_state.street  # int representing pre-flop, flop, turn, or river respectively
        my_cards = round_state.hands[active]  # your cards
        board_cards = round_state.deck[:street]  # the board cards
        my_pip = round_state.pips[active]  # the number of chips you have contributed to the pot this round of betting
        opp_pip = round_state.pips[1-active]  # the number of chips your opponent has contributed to the pot this round of betting
        my_stack = round_state.stacks[active]  # the number of chips you have remaining
        opp_stack = round_state.stacks[1-active]  # the number of chips your opponent has remaining
        continue_cost = opp_pip - my_pip  # the number of chips needed to stay in the pot
        my_contribution = STARTING_STACK - my_stack  # the number of chips you have contributed to the pot
        opp_contribution = STARTING_STACK - opp_stack  # the number of chips your opponent has contributed to the pot
        if RaiseAction in legal_actions:
           min_raise, max_raise = round_state.raise_bounds()  # the smallest and largest numbers of chips for a legal bet/raise
           min_cost = min_raise - my_pip  # the cost of a minimum bet/raise
           max_cost = max_raise - my_pip  # the cost of a maximum bet/raise


        ranks = ('2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A')
        suits = ('c', 'd', 'h', 's')


        range_hash = {'AA': 4, 'AKs': 4, 'AQs': 4, 'AJs': 4, 'ATs': 4, 'A9s': 3, 'A8s': 3, 'A7s': 3, 'A6s': 3, 'A5s': 3, 'A4s': 3, 'A3s': 3, 'A2s': 3,
                      'AKo': 4, 'KK': 4, 'KQs': 4, 'KJs': 4, 'KTs': 4, 'T9s': 3, 'K8s': 3, 'K7s': 3, 'K6s': 2, 'K5s': 2, 'K4s': 2, 'K3s': 2, 'K2s': 2,
                      'AQo': 4, 'KQo': 3, 'QQ': 4, 'QJs': 4, 'QTs': 4, 'Q9s': 3, 'Q8s': 3, 'Q7s': 2, 'Q6s': 2, 'Q5s': 2, 'Q4s': 2, 'Q3s': 2, 'Q2s': 2,
                      'AJo': 3, 'KJo': 3, 'QJo': 3, 'JJ': 4, 'JTs': 4, 'J9s': 3, 'J8s': 3, 'J7s': 2, 'J6s': 1, 'J5s': 1, 'J4s': 1, 'J3s': 1, 'J2s': 1,
                      'ATo': 3, 'KTo': 3, 'QTo': 3, 'JTo': 3, 'TT': 4, 'T9s': 3, 'T8s': 3, 'T7s': 2, 'T6s': 2, 'T5s': 1, 'T4s': 1, 'T3s': 1, 'T2s': 1,
                      'A9o': 2, 'K9o': 2, 'Q9o': 2, 'J9o': 2, 'T9o': 2, '99': 4, '98s': 3, '97s': 3, '96s': 2, '95s': 1, '94s': 1, '93s': 1, '92s': 1,
                      'A8o': 2, 'K8o': 1, 'Q8o': 1, 'J8o': 1, 'T8o': 1, '98o': 1, '88': 4, '87s': 3, '86s': 3, '85s': 2, '84s': 1, '83s': 1, '82s': 1,
                      'A7o': 2, 'K7o': 1, 'Q7o': 1, 'J7o': 1, 'T7o': 1, '97o': 1, '87o': 1, '77': 4, '76s': 3, '75s': 3, '74s': 2, '73s': 1, '72s': 1,
                      'A6o': 2, 'K6o': 1, 'Q6o': 1, 'J6o': 1, 'T6o': 1, '96o': 1, '86o': 1, '76o': 1, '66': 4, '65s': 3, '64s': 3, '63s': 2, '62s': 1,
                      'A5o': 2, 'K5o': 1, 'Q5o': 1, 'J5o': 1, 'T5o': 1, '95o': 1, '85o': 1, '75o': 1, '65o': 1, '55': 4, '54s': 3, '53s': 3, '52s': 2,
                      'A4o': 2, 'K4o': 1, 'Q4o': 1, 'J4o': 1, 'T4o': 1, '94o': 1, '84o': 1, '74o': 1, '64o': 1, '54o': 1, '44': 3, '43s': 3, '42s': 2,
                      'A3o': 2, 'K3o': 1, 'Q3o': 1, 'J3o': 1, 'T3o': 1, '93o': 1, '83o': 1, '73o': 1, '63o': 1, '53o': 1, '43o': 1, '33': 3, '32s': 2,
                      'A2o': 2, 'K2o': 1, 'Q2o': 1, 'J2o': 1, 'T2o': 1, '92o': 1, '82o': 1, '72o': 1, '62o': 1, '52o': 1, '42o': 1, '32o': 1, '22': 3,}



        if street == 0:
            suited =  my_cards[0].suit == my_cards[1].suit

            if my_cards[0].rank == my_cards[1].rank:
                range_ending = ''
            elif suited:
                range_ending = 's'
            else:
                range_ending = 'o'


            if my_cards[0].rank < my_cards[1].rank:
                range_beginning = ranks[my_cards[1].rank] + ranks[my_cards[0].rank]
            else:
                range_beginning = ranks[my_cards[0].rank] + ranks[my_cards[1].rank]

            my_preflop_range = range_beginning + range_ending


            preflop_confidence = range_hash[my_preflop_range]
            
            if preflop_confidence > 2 and RaiseAction in legal_actions:
                return RaiseAction(max_cost)
            elif preflop_confidence > 1 and CheckAction in legal_actions:
                return CheckAction()
            else:
                return FoldAction()




        if CheckAction in legal_actions:  # check-call
            return CheckAction()
        return CallAction


if __name__ == '__main__':
    run_bot(Player(), parse_args())
