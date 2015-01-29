""" Voting booth script for x/84. """

from common import waitprompt, prompt_pager
from x84.bbs import getsession, getterminal, echo, LineEditor
from x84.bbs import DBProxy, showart, syncterm_setfont
import os

databasename = 'votingbooth'  # change this to use an alternative database file

__author__ = 'Hellbeard'
__version__ = 1.1

# -----------------------------------------------------------------------------------

def ynprompt():
    term = getterminal()
    echo(term.magenta + u' (' + term.cyan + u'yes' + term.magenta +
         u'/' + term.cyan + u'no' + term.magenta + u')' + term.white)
    while True:
        inp = term.inkey()
        if inp.lower() == u'y':
            yn = True
            echo(u' yes!')
            break
        if inp.lower() == u'n' or inp.lower() == u'q':
            yn = False
            echo(u' no')
            break
    return(yn)

# -----------------------------------------------------------------------------------

def query_question():
    term = getterminal()
    session = getsession()
    db = DBProxy(databasename)
    questions = []
    index = []
    uservotingdata = []
    questions = db['questions']
    index = db['index']

    # create a new database file if none exists
    if not session.user.handle in db:
        db[session.user.handle] = {}
    uservotingdata = db[session.user.handle]

    echo(term.clear() + term.blue(u'>>') + term.white(u'questions availible\r\n') +
         term.blue(u'-' * 21 + '\r\n\r\n'))

    text = ''
    for i in range(0, len(questions)):
        if (index[i], 0) in uservotingdata:
            text = text + term.green(u'*')
        text = text + u''.join(term.magenta + u'(' + term.cyan + str(i) + term.magenta + u') ' +
                              term.white + questions[i] + u'\r\n')
    text = text.splitlines()
    prompt_pager(content=text,
                 line_no=0,
                 colors={'highlight': term.cyan,
                         'lowlight': term.green,
                         },
                 width=term.width, breaker=None, end_prompt=False)
    echo(term.move_x(0) + term.bold_black(u'* = already voted\r\n\r\n'))

    while True:
        echo(term.move_x(
            0) + term.magenta(u'select one of the questions above or press enter to return: '))
        le = LineEditor(10)
        le.colors['highlight'] = term.cyan
        inp = le.read()
        if inp is not None and inp.isnumeric() and int(inp) < len(questions):
            return int(inp)
        else:
            # -1 in this case means that no valid option was chosen.. break
            # loop.
            return -1

# -----------------------------------------------------------------------------------


def list_results(questionnumber):
    term = getterminal()
    db = DBProxy(databasename)
    alternatives = {}
    questions = []
    results = []
    amount_of_alternatives = db['amount_of_alternatives']
    alternatives = db['alternatives']
    questions = db['questions']
    results = db['results']

    echo(term.clear())

    text = (term.white + questions[questionnumber] + u'\r\n' + term.blue +
            u'-' * len(questions[questionnumber]) + u'\r\n\r\n')

    # only display full statistics if the screen width is above 79 columns.
    if term.width > 79:
        text = text + (term.magenta + u'(alternatives)' + term.move_x(49) +
                       u'(votes)' + term.move_x(57) + u'(percentage)\r\n')
        totalvotes = 0.00
        for i in range(0, amount_of_alternatives[questionnumber]):
            totalvotes = totalvotes + results[(questionnumber, i)]
        for i in range(0, amount_of_alternatives[questionnumber]):
            if results[(questionnumber, i)] > 0:
                percentage = (results[(questionnumber, i)] / totalvotes) * 100
            else:
                percentage = 0
            staple = int(round(percentage / 5))
            text = text + u''.join(term.move_x(0) + term.white(alternatives[(questionnumber, i)]) + term.move_x(49) +
                                   term.cyan(str(results[(questionnumber, i)])) + u'  ' + term.cyan + str(int(percentage)) +
                                   term.cyan(u'%') + term.move_x(57) + term.cyan(u'[') +
                                   term.green('#' * staple) + term.move_x(78) + term.cyan(']'))
            if i != amount_of_alternatives[questionnumber]:
                text = text + u'\r\n'
    else:
        for i in range(0, amount_of_alternatives[questionnumber]):
            text = text + (term.white(str(alternatives[(questionnumber, i)])) + term.cyan(u' votes: ') +
                           term.magenta(str(results[(questionnumber, i)])) + u'\r\n')

    text = text.splitlines()
    prompt_pager(content=text,
                 line_no=0,
                 colors={'highlight': term.cyan,
                         'lowlight': term.green,
                         },
                 width=term.width, breaker=None, end_prompt=False)
    echo(term.move_x(0) + term.bold_black(u'* = already voted\r\n'))
    waitprompt(term)

# -----------------------------------------------------------------------------------

def vote(questionnumber):
    term = getterminal()
    session = getsession()
    db = DBProxy(databasename)
    questions = []
    amount_of_alternatives = []
    alternatives = {}
    results = {}
    index = []
    questions = db['questions']
    alternatives = db['alternatives']
    results = db['results']
    amount_of_alternatives = db['amount_of_alternatives']
    index = db['index']

    echo(term.clear() + term.white + questions[questionnumber] + u'\r\n' +
         term.blue(u'-' * len(questions[questionnumber])) + u'\r\n\r\n')
    text = ''
    for i in range(0, amount_of_alternatives[questionnumber]):
        text = text + (term.magenta + u'(' + term.cyan + str(i) + term.magenta + u') ' +
                       term.white + alternatives[(questionnumber, i)] + u'\r\n')

    text = text.splitlines()
    prompt_pager(content=text,
                 line_no=0,
                 colors={'highlight': term.cyan,
                         'lowlight': term.green,
                         },
                 width=term.width, breaker=None, end_prompt=False)
    echo(term.move_x(0) + term.magenta(u'(') + term.cyan(str(amount_of_alternatives[questionnumber])) +
         term.magenta(u') ') + term.bold_black(u'Add your own answer..\r\n\r\n'))

    while True:
        echo(term.move_x(0) + term.magenta(u'Your choice: '))
        le = LineEditor(10)
        le.colors['highlight'] = term.cyan
        inp = le.read()
        if inp is not None and inp.isnumeric() and int(
                inp) <= amount_of_alternatives[questionnumber]:

            # create database for user if the user hasn't made any votes
            if session.user.handle not in db:
                db[session.user.handle] = {}

            uservotingdata = {}
            uservotingdata = db[session.user.handle]

            # if user wants to create an own alternative..
            if int(inp) == amount_of_alternatives[questionnumber]:
                echo(term.clear + term.red + u'\r\nPress enter to abort. ' +
                     term.move(0, 0) + term.white(u'Your answer: '))
                le = LineEditor(48)
                new_alternative = le.read()
                if new_alternative == '':
                    return
                results[(questionnumber, int(inp))] = 0  # init..
                # init..
                alternatives[(questionnumber, int(inp))] = new_alternative
                amount_of_alternatives[
                    questionnumber] = amount_of_alternatives[questionnumber] + 1
                db['alternatives'] = alternatives
                db['amount_of_alternatives'] = amount_of_alternatives

            # if the user has voted on this question before..
            if (index[questionnumber], 0) in uservotingdata:
                temp2 = uservotingdata[(index[questionnumber], 0)]
                results[(questionnumber, temp2)] = results[
                    (questionnumber, temp2)] - 1  # remove the old vote
                results[(questionnumber, int(inp))] = results[
                    (questionnumber, int(inp))] + 1
                uservotingdata[(index[questionnumber], 0)] = int(inp)
            else:
                uservotingdata[(index[questionnumber], 0)] = int(inp)
                results[(questionnumber, int(inp))] = results[
                    (questionnumber, int(inp))] + 1

            uservotingdata[(index[questionnumber], 0)] = int(inp)

            echo(term.green(u'\r\nyour vote has been noted, thanks..'))
            term.inkey(2)
            db['results'] = results
            db[session.user.handle] = uservotingdata
            list_results(questionnumber)
            return

# -----------------------------------------------------------------------------------

def add_question():
    term = getterminal()
    db = DBProxy(databasename)
    questions = []
    amount_of_alternatives = []
    index = {}
    alternatives = {}
    results = {}
    index = db['index']
    questions = db['questions']
    alternatives = db['alternatives']
    results = db['results']
    amount_of_alternatives = db['amount_of_alternatives']
    amount_of_questions = len(questions)

    echo(term.clear + term.white + u'\r\nQuestion: ')
    le = LineEditor(65)
    new_question = le.read()
    if new_question == '':
        return

    echo(term.bold_black(u'\r\n\r\nLeave a blank line when you are finished..'))
    new_amount = 0
    while True:
        echo(term.normal + term.white + u'\r\nchoice ' +
             term.red + str(new_amount) + term.white + u': ')
        le = LineEditor(48)
        alternatives[(amount_of_questions, new_amount)] = le.read()
        if alternatives[(amount_of_questions, new_amount)] == '':
            break
        else:
            results[(amount_of_questions, new_amount)] = 0
            new_amount = new_amount + 1

    if new_amount > 0:
        echo(term.white(u'\r\n\r\nSave this voting question?'))
        answer = ynprompt()
        if answer == 1:
            questions.append(new_question)
            amount_of_alternatives.append(new_amount)

            indexcounter = db['indexcounter']
            indexcounter = indexcounter + 1
            index.append(str(indexcounter))

            db['indexcounter'] = indexcounter
            db['index'] = index
            db['questions'] = questions
            db['amount_of_alternatives'] = amount_of_alternatives
            db['results'] = results
            db['amount_of_questions'] = amount_of_questions
            db['alternatives'] = alternatives

            waitprompt(term)

# -----------------------------------------------------------------------------------

def delete_question(questionnumber):
    term = getterminal()
    db = DBProxy(databasename)
    alternatives = {}
    questions = []
    results = {}
    amount_of_alternatives = []
    questions = db['questions']
    results = db['results']
    amount_of_alternatives = db['amount_of_alternatives']
    alternatives = db['alternatives']
    index = db['index']

    echo(term.clear + term.white(u'Delete the ') + term.magenta(u'(') + term.cyan(u'e') + term.magenta(u')') +
         term.white(u'ntire question or delete single ') + term.magenta(u'(') + term.cyan(u'a') + term.magenta(u')') +
         term.white(u'lternatives?') + u'\r\n\r\n' + term.magenta(u'command: '))

    le = LineEditor(10)
    le.colors['highlight'] = term.cyan
    inp = le.read()
    # makes the input indifferent to wheter you used lower case when typing in
    # a command or not..
    inp = (inp or u'').lower()

    if inp == u'a':  # delete answer alternative..
        echo(term.clear)
        echo(term.white + questions[questionnumber] + term.move_x(max(0, term.width - 12)) +
             u' index: ' + str(index[questionnumber]) + u'\r\n\r\n')
        for i in range(0, amount_of_alternatives[questionnumber]):
            echo(term.cyan(str(i) + u'. ') +
                 term.white(alternatives[(questionnumber, i)]) + u'\r\n')

        echo(term.magenta(u'\r\nSelect a number. Enter to abort: '))

        le = LineEditor(10)
        le.colors['highlight'] = term.cyan
        inp2 = le.read()

        if inp2 is not None and inp2.isnumeric() and int(
                inp2) < amount_of_alternatives[questionnumber]:
            if int(inp2) + 1 < amount_of_alternatives[questionnumber]:
                for i in range(
                        int(inp2), amount_of_alternatives[questionnumber] - 1):
                    alternatives[(questionnumber, i)] = alternatives[
                        (questionnumber, i + 1)]
                    results[(questionnumber, i)] = results[
                        (questionnumber, i + 1)]
        else:
            return
        amount_of_alternatives[questionnumber] -= 1

    elif inp == u'e':  # delete entire question..
        if questionnumber + 1 < len(questions):
            for i in range(questionnumber, len(questions) - 1):
                questions[i] = questions[i + 1]
                amount_of_alternatives[i] = amount_of_alternatives[i + 1]
                index[(i)] = index[(i + 1)]
                for i2 in range(0, amount_of_alternatives[i + 1]):
                    alternatives[(i, i2)] = alternatives[(i + 1, i2)]
                    results[(i, i2)] = results[(i + 1, i2)]
        del questions[-1]
        del amount_of_alternatives[-1]
        del index[-1]
    else:
        return

    db['index'] = index
    db['questions'] = questions
    db['amount_of_alternatives'] = amount_of_alternatives
    db['results'] = results
    db['alternatives'] = alternatives
    return

# -----------------------------------------------------------------------------------

def generate_database():  # generates a database file with a generic question.
    db = DBProxy(databasename)

    index = []
    index.append(0)
    indexcounter = 0

    questions = []
    questions.append('Which is your prefered BBS software?')

    alternatives = {}
    alternatives[(0, 0)] = 'X/84'
    alternatives[(0, 1)] = 'Daydream'
    alternatives[(0, 2)] = 'Mystic'
    alternatives[(0, 3)] = 'Synchronet'

    results = {}
    results[(0, 0)] = 0
    results[(0, 1)] = 0
    results[(0, 2)] = 0
    results[(0, 3)] = 0

    amount_of_alternatives = []
    # this is the only list/dict that is not zerobased..
    amount_of_alternatives.append(4)

    db['indexcounter'] = indexcounter
    db['index'] = index
    db['amount_of_alternatives'] = amount_of_alternatives
    db['alternatives'] = alternatives
    db['results'] = results
    db['questions'] = questions

# -----------------------------------------------------------------------------------

def main():
    session = getsession()
    session.activity = u'hanging out in voting script'
    term = getterminal()
    echo(syncterm_setfont('topaz'))

    db = DBProxy(databasename)
    if 'questions' not in db:
        generate_database()

    while True:
        # clears the screen and displays the vote art header
        echo(term.clear())
        for line in showart(
                os.path.join(os.path.dirname(__file__), 'art', 'vote.ans'), 'cp437'):
            echo(term.cyan + term.move_x(max(0, (term.width / 2) - 40)) + line)

        if 'sysop' in session.user.groups:
            spacing = 1
        else:
            spacing = 7
            echo(' ')
        echo(term.magenta(u'\n (') + term.cyan(u'r') + term.magenta(u')') +
             term.white(u'esults') + ' ' * spacing +
             term.magenta(u'(') + term.cyan(u'v') + term.magenta(u')') +
             term.white(u'ote on a question') + u' ' * spacing +
             term.magenta(u'(') + term.cyan(u'a') + term.magenta(u')') +
             term.white(u'dd a new question') + u' ' * spacing)
        if 'sysop' in session.user.groups:
            echo(term.magenta(u'(') + term.cyan(u'd') + term.magenta(u')') +
                 term.white(u'elete a question') + u' ' * spacing)
        echo(term.magenta(u'(') + term.cyan(u'q') + term.magenta(u')') + term.white(u'uit') +
             term.magenta(u'\r\n\r\nx/84 voting booth command: '))
        le = LineEditor(10)
        le.colors['highlight'] = term.cyan
        inp = le.read()
        # makes the input indifferent to wheter you used lower case when typing
        # in a command or not..
        inp = (inp or u'').lower()

        if 'sysop' in session.user.groups and inp == u'd':
            while True:
                questionnumber = query_question()
                if questionnumber == -1:
                    break
                delete_question(questionnumber)
        elif inp == u'r':
            while True:
                questionnumber = query_question()
                if questionnumber == -1:
                    break
                list_results(questionnumber)
        elif inp == u'v':
            while True:
                questionnumber = query_question()
                if questionnumber == -1:
                    break
                vote(questionnumber)
        elif inp == u'a':
            add_question()
        elif inp == u'q':
            return
        else:
            # if no valid key is pressed then do some ami/x esthetics.
            echo(term.red(u'\r\nNo such command. Try again.\r\n'))
            waitprompt(term)
