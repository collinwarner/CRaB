import eval7
import itertools
import pandas as pd
import time

import multiprocessing

DIAMONDS_VAL = eval7.Card('Ad').suit
HEARTS_VAL = eval7.Card('Ah').suit

def calculate_strength(hole, iterations):
    
        deck = eval7.Deck()
        hole_card = [eval7.Card(card) for card in hole]

        for card in hole_card:
            deck.cards.remove(card)

        score = 0

        for _ in range(iterations):
            deck.shuffle()

            _OPP = 2
            _COMM = 5

            draw = deck.peek(_COMM + _OPP)

            opp_hole = draw[:_OPP]
            community = draw[_OPP:]

            while community[-1].suit == DIAMONDS_VAL or\
                    community[-1].suit == HEARTS_VAL:
                # Draw one more card when playing river of blood
                _COMM += 1
                draw = deck.peek(_OPP + _COMM)
                community = draw[_OPP:]

            our_value = float('-inf')
            opp_value = float('-inf')

            for community_subset in itertools.combinations(community, 5):
                community_subset = list(community_subset)
                our_hand = hole_card +  community_subset
                opp_hand = opp_hole +  community_subset

                # Update our value if we have a better hand
                our_new_value = eval7.evaluate(our_hand)
                if our_new_value > our_value:
                    our_value = our_new_value

                # Update the opp value if they have a better hand
                opp_new_value = eval7.evaluate(opp_hand)
                if opp_new_value > opp_value:
                    opp_value = opp_new_value

            if our_value > opp_value:
                score += 2
            
            elif our_value == opp_value:
                score += 1

            else:
                score += 0

        hand_strength = score / (2 * iterations)

        return hand_strength

def compute_strengths(num_iter, holes, suits, dict_key, return_dict):
    strengths = []
    for hole in holes:
        strengths.append(calculate_strength([hole[0] + suits[0], hole[1] + suits[1]], _MONTE_CARLO_ITERS))
    return_dict[dict_key] = strengths

if __name__ == '__main__':

    start = time.time()

    _MONTE_CARLO_ITERS = 1000000
    _RANKS = 'AKQJT98765432'
    _SUITS = ['d', 'h', 'c', 's']

    off_rank_holes = list(itertools.combinations(_RANKS, 2)) #all holes we can have EXCEPT pocket pairs (e.g. [(A, K), (A, Q), (A, J)...])
    pocket_pair_holes = list(zip(_RANKS, _RANKS)) #all pocket pairs [(A, A), (K, K), (Q, Q)...]

    # Compute the strengths for the possible hole cards in parallel
    manager = multiprocessing.Manager()
    return_dict = manager.dict() # share dict across processes

    # Create processes
    processes = []
    #all red holes with the same suit
    processes.append(multiprocessing.Process(target=compute_strengths, args=(_MONTE_CARLO_ITERS, off_rank_holes, [_SUITS[0], _SUITS[0]], 'suited_red', return_dict)))

    #all black holes with the same suit
    processes.append(multiprocessing.Process(target=compute_strengths, args=(_MONTE_CARLO_ITERS, off_rank_holes, [_SUITS[2], _SUITS[2]], 'suited_black', return_dict)))

    #all red holes with off suits
    processes.append(multiprocessing.Process(target=compute_strengths, args=(_MONTE_CARLO_ITERS, off_rank_holes, [_SUITS[0], _SUITS[1]], 'off_suited_red', return_dict)))

    #all black holes with off suits
    processes.append(multiprocessing.Process(target=compute_strengths, args=(_MONTE_CARLO_ITERS, off_rank_holes, [_SUITS[2], _SUITS[3]], 'off_suited_black', return_dict)))

    #all holes with off suits with one black and one red
    processes.append(multiprocessing.Process(target=compute_strengths, args=(_MONTE_CARLO_ITERS, off_rank_holes, [_SUITS[0], _SUITS[2]], 'off_suited_mix', return_dict)))

    #all red pocket pairs
    processes.append(multiprocessing.Process(target=compute_strengths, args=(_MONTE_CARLO_ITERS, pocket_pair_holes, [_SUITS[0], _SUITS[1]], 'pocket_pairs_red', return_dict)))

    #all black pocket pairs
    processes.append(multiprocessing.Process(target=compute_strengths, args=(_MONTE_CARLO_ITERS, pocket_pair_holes, [_SUITS[2], _SUITS[3]], 'pocket_pairs_black', return_dict)))

    #all mixed pocket pairs
    processes.append(multiprocessing.Process(target=compute_strengths, args=(_MONTE_CARLO_ITERS, pocket_pair_holes, [_SUITS[0], _SUITS[2]], 'pocket_pairs_mix', return_dict)))

    # Launch processes
    for proc in processes:
        proc.start()

    # Sync processes
    for proc in processes:
        proc.join()

    # Convert cards to string/look-table
    
    #s == suited
    suited_red_holes = [hole[0] + hole[1] + 'sr' for hole in off_rank_holes]
    suited_black_holes = [hole[0] + hole[1] + 'sb' for hole in off_rank_holes]

    #o == off-suit
    off_suited_red_holes = [hole[0] + hole[1] + 'or' for hole in off_rank_holes]
    off_suited_black_holes = [hole[0] + hole[1] + 'ob' for hole in off_rank_holes]
    off_suited_mix_holes = [hole[0] + hole[1] + 'om' for hole in off_rank_holes]
    
    #pocket pairs are always off suit
    pocket_pairs_red = [hole[0] + hole[1] + 'or' for hole in pocket_pair_holes]
    pocket_pairs_black = [hole[0] + hole[1] + 'ob' for hole in pocket_pair_holes]
    pocket_pairs_mix = [hole[0] + hole[1] + 'om' for hole in pocket_pair_holes]

    #aggregate them all
    all_strengths = return_dict['suited_red'] + return_dict['suited_black'] +\
        return_dict['off_suited_red'] + return_dict['off_suited_black'] + return_dict['off_suited_mix'] +\
        return_dict['pocket_pairs_red'] + return_dict['pocket_pairs_black'] + return_dict['pocket_pairs_mix'] 
    all_holes = suited_red_holes + suited_black_holes +\
        off_suited_red_holes + off_suited_black_holes + off_suited_mix_holes +\
        pocket_pairs_red + pocket_pairs_black + pocket_pairs_mix

    hole_df = pd.DataFrame() #make our spreadsheet with a pandas data frame!
    hole_df['Holes'] = all_holes
    hole_df['Strengths'] = all_strengths

    hole_df.to_csv('hole_strengths.csv', index=False) #save it for later use, trade space for time!

    end = time.time()

    print("Computation took:", end-start)
