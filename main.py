import itertools
import random
import wordle
from math import log2
from matplotlib import pyplot as plt
from wordleAPI import WordleAPI
from multiprocessing import Pool
from dictionaries import words_and_frequencies
import re
from timeit import default_timer as timer
from numpy import std, mean, around
import seaborn as sns


def get_all_patterns():
    return list(itertools.product(['correct', 'present', 'absent'], repeat=5))


def get_matching_words(word, word_list, pattern):
    matching_words = word_list.copy()

    # correct
    if "correct" in pattern:
        pat = "^" + ''.join([word[i] if val == "correct" else "." for i, val in enumerate(pattern)]) + "$"
        p = re.compile(pat)
        matching_words = [s for s in matching_words if p.match(s)]

    # absent   ^ [ ^ <>] * $
    if "absent" in pattern:

        # completely absent (given letter is only grey in this pattern)
        completely_absent = []
        zipped = list(zip(word, pattern))

        for a, val in list(filter(lambda x: x[1] == 'absent', zipped)):
            if len(list(filter(lambda x: x[0] == a and x[1] in ['present', 'correct'], zipped))) == 0:
                if a not in completely_absent: completely_absent.append(a)

        if len(completely_absent) > 0:
            pat = "^[^" + ''.join(completely_absent) + "]+$"
            matching_words = [s for s in matching_words if re.compile(pat).match(s)]

        # absent only on exact position (is green on other position)
        pat = "^" + ''.join(["[^" + word[i] + "]" if val == "absent" else "." for i, val in enumerate(pattern)]) + "$"
        matching_words = [s for s in matching_words if re.compile(pat).match(s)]

    # present somewhere in a word ^(?=.*F)(?=.*O)(?=.*G).*
    if "present" in pattern:
        pat = "^" + ''.join(["(?=.*" + word[i] + ")" if val == "present" else "" for i, val in enumerate(pattern)]) + ".+$"
        matching_words = [s for s in matching_words if re.compile(pat).match(s)]

        # but not present on given position
        pat = "^" + ''.join(["[^" + word[i] + "]" if val == "present" else "." for i, val in enumerate(pattern)]) + "$"
        matching_words = [s for s in matching_words if re.compile(pat).match(s)]

    return matching_words


def get_word_entropy(word, word_list):
    entropy = 0
    for pattern in get_all_patterns():
        matching_words_count = len(get_matching_words(word, word_list, pattern))
        probability = max(matching_words_count / len(word_list), 0.000000001)
        entropy += probability * log2(1 / probability)
    return [word, entropy]


def get_words_entropies(word_list):

    if len(word_list) > 250:
        with Pool() as pool:
            return pool.starmap(get_word_entropy, [[word, word_list] for word in word_list])
    else:
        return [get_word_entropy(word, word_list) for word in word_list]


"""
Translating responses from wordle-pythonic format to correct/present/absent
"""


def translate_response(response):
    res = []
    for x in response[0].split("   ")[:-1]:
        if "*" in x:
            res.append('correct')
        elif x.isupper():
            res.append('present')
        else:
            res.append('absent')
    return res


"""

Selecting word according to current policy

"""


def get_word(avail_words, state , print_selections = False):

    if state.count('correct') == 4 or len(avail_words) > 250 :
        curr_word, score = avail_words[0], get_word_frequency_score(avail_words[0])

        if print_selections:
            print(f"Selected word is {curr_word.upper()} with score {round(score,2)} (char frequency), choosen out of {len(avail_words)} words")

    else:
        curr_word, score = max(get_words_entropies(avail_words), key=lambda x: x[1])

        if print_selections:
            print(f"Selected word is {curr_word.upper()} with score {round(score,2)} (entropy), choosen out of {len(avail_words)} words")

    return curr_word, score


def get_word_frequency_score(word):
    return words_and_frequencies[word]


def run_online_game(website="unlimited"):
    wordSel = WordleAPI(website)

    while wordSel.last_ans_row < 6:

        if wordSel.last_ans_row == -1:
            avail_words = [a[0] for a in sorted(words_and_frequencies.items(), key=lambda x: x[1], reverse=True)]
            curr_word = random.choice(avail_words[:50])
            print(f"First word will be: {curr_word.upper()}")
        else:
            avail_words = get_matching_words(curr_word, avail_words, state)
            curr_word, _ = get_word(avail_words, state)

        wordSel.send_answer(curr_word)
        state = wordSel.get_state()
        avail_words.remove(curr_word)

        # handle ,,invalid word" case
        if "letter selected" in state:
            wordSel.erase_word()
            wordSel.last_ans_row -= 1
            print(f"Word {curr_word.upper()} was invalid!")

        elif set(state) == {'correct'}:
            print(f"Online game ended in {wordSel.last_ans_row + 1} guesses. The final word was: {curr_word.upper()}")
            return wordSel.last_ans_row + 1

    return "Game over!"


def run_local_game():

    final_word = random.choice(list(words_and_frequencies.keys()))
    # print(f"The final word will be: {final_word}")
    game = wordle.Wordle(word=final_word.lower(), real_words = False)

    i = 0
    while True:

        if i == 0:
            avail_words = [a[0] for a in sorted(words_and_frequencies.items(), key=lambda x: x[1], reverse=True)]
            curr_word = random.choice(avail_words[:50])
            print(f"First word will be: {curr_word.upper()}")
        else:
            avail_words = get_matching_words(curr_word, avail_words, translate_response(state))
            curr_word, _ = get_word(avail_words, translate_response(state))


        state = game.send_guess(curr_word, log_guess=False)
        i+=1
        avail_words.remove(curr_word)

        # handle ,,invalid word" case
        if state == 'That\'s not a real word.':
            i -= 1
            print(f"Word {curr_word.upper()} was invalid!")

        elif state[1]:
            print(f"Local game ended in {i} guesses. The final word was: {curr_word.upper()}")
            return i



NUM_OF_ITERATIONS = 1000
def test_efficiency():
    x, guesses, game_times, wins = list(range(1, NUM_OF_ITERATIONS+1)),[], [], 0

    for i in range(NUM_OF_ITERATIONS):
        print(f"{i+1}/{NUM_OF_ITERATIONS}")
        start = timer()
        guesses.append(int(run_local_game()))

        if 0 <= guesses[-1] <= 6:
            wins += 1

        game_times.append(round(timer() - start, 2))

    # num of guesses and time scatter plots
    for vals, name in zip([guesses, game_times], ['guesses', 'game_time']):
        plt.cla()
        plt.scatter(x, vals, s=10, c="green")
        print(x, vals)
        plt.xlabel("game no.")
        plt.ylabel(name)
        plt.title(f"AVG {name}={around(mean(vals),2)}, STD={around(std(vals),2)}, WINS={round(100*wins/NUM_OF_ITERATIONS,2)}%")
        print(f"AVG {name}={around(mean(vals),2)}, STD={around(std(vals),2)}, WINS={round(100*wins/NUM_OF_ITERATIONS,2)}%")
        plt.savefig(name+'.png')

    # num of guesses distribution plot
    plt.cla()
    sns.set_theme()
    sns.displot(guesses)
    plt.savefig("guesses_dist.png")

    # time distribution plot
    plt.cla()
    sns.set_theme()
    plt.hist(game_times, bins=25)
    plt.savefig("game_time_dist.png")

    return


if __name__ == '__main__':
    test_efficiency()
    # run_local_game()
    # run_online_game()
