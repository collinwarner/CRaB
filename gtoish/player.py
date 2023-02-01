'''
Simple example pokerbot, written in Python.
'''
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot

import pandas as pd
import math

#import sys, os
#sys.path.append('/home/collinw/pokerbots/CRaB/gtoish/deuces/deuces')
from deuces.deuces.card import Card
from deuces.deuces.evaluator import Evaluator
from deuces.deuces.deck import Deck

class Player(Bot):
    '''
    A pokerbot.
    '''

    ALL_PERCENT = .12
    CALL_PERCENT = .18
    
    def __init__(self):
        '''
        Called when a new game starts. Called exactly once.

        Arguments:
        Nothing.

        Returns:
        Nothing.
        '''
        self.oracle = Evaluator()
        df = pd.read_csv('hole_strengths.csv')
        # Sort by strength of the hole cards
        hole_cards = df['Holes']
        strengths = df['Strengths']
        hole_strengths = []

        for idx in range(len(df)):
            hole_strengths.append((hole_cards[idx], strengths[idx]))

        hole_strengths.sort(reverse=True, key=lambda item: item[1])

        self.pre_flop_cards_all = set()
        
        for idx in range(math.floor(len(df)*self.ALL_PERCENT)):
            self.pre_flop_cards_all.add(hole_strengths[idx][0])

        self.pre_flop_cards_call = set()
        for idx in range(math.floor(len(df)*self.ALL_PERCENT),
                math.floor(len(df)*self.CALL_PERCENT)):
            self.pre_flop_cards_call.add(hole_strengths[idx][0])
        self.hole_cards = [] 
        self.board = []
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
        my_cards = round_state.hands[active]  # your cards
        self.hole_cards = Card.hand_to_binary(my_cards) 
        Card.print_pretty_cards(self.hole_cards)
        #big_blind = bool(active)  # True if you are the big blind

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


        if street == 0:
            range_ending = ''

            is_suited = my_cards[0][1] == my_cards[1][1]

            if is_suited:
                range_ending += 's'
            else:
                range_ending += 'o'

            is_red = (my_cards[0][1] == 'd' or my_cards[0][1] == 'h') and\
                    (my_cards[1][1] == 'd' or my_cards[1][1] == 'h')
            is_black = (my_cards[0][1] == 'c' or my_cards[0][1] == 's') and\
                    (my_cards[1][1] == 'c' or my_cards[1][1] == 's')

            if is_red:
                range_ending += 'r'

            elif is_black:
                range_ending += 'b'
            else:
                range_ending += 'm'

            my_preflop_range = my_cards[0][0] + my_cards[1][0] + range_ending
            my_preflop_range_alt = my_cards[1][0] + my_cards[0][0] + range_ending
            if ((my_preflop_range in self.pre_flop_cards_all) or (my_preflop_range_alt in self.pre_flop_cards_all)) and RaiseAction in legal_actions:
                min_raise, max_raise = round_state.raise_bounds()
                max_cost = max_raise - my_pip

                if max_cost <= my_stack: #make sure the max_cost is something we can afford! Must have at least this much left after our other costs
                    my_action = RaiseAction(max_raise) #GO ALL IN!!!
                elif CallAction in legal_actions: # check-call
                    my_action = CallAction()
                else:
                    my_action = CheckAction()
                return my_action 
            elif (((my_preflop_range in self.pre_flop_cards_all) or (my_preflop_range_alt in self.pre_flop_cards_all)) or\
                    ((my_preflop_range in self.pre_flop_cards_call) or (my_preflop_range_alt in self.pre_flop_cards_call))):
                if CheckAction in legal_actions:
                    print("check")
                    return CheckAction()
                if CallAction in legal_actions:
                    print("call")
                    return CallAction();
            elif FoldAction in legal_actions:
                print("fold")
                return FoldAction()
            elif CheckAction in legal_actions:
                return CheckAction()
            else:
                print(f"street {street} legal actions {legal_actions}")
                raise Exception("Should not get here")
        board_cards = Card.hand_to_binary(round_state.deck[:street])  # the board cards
        hand_strength_percentage = 1 - self.oracle.get_five_card_rank_percentage(self.oracle._seven(self.hole_cards + board_cards))
        print("cards")
        Card.print_pretty_cards(board_cards)
        print(f"ranking {hand_strength_percentage}")

        if hand_strength_percentage > .9:
            return RaiseAction(my_stack)
        elif CheckAction in legal_actions:  # check-call
            # print("final check")
            return CheckAction()
        elif hand_strength_percentage > (continue_cost/(continue_cost + my_pip + opp_pip)):
            return CallAction()
        else:
            return FoldAction()

if __name__ == '__main__':
    run_bot(Player(), parse_args())
