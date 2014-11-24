""" Voting booth script for x/84 bbs, https://github.com/jquast/x84 """

from common import waitprompt
from x84.bbs import getsession, getterminal, echo, getch, LineEditor, DBProxy, showart
import os

databasename = 'votingbooth' # change this for alternate database file

__author__ = 'Hellbeard'
__version__ = 1.0

# -----------------------------------------------------------------------------------

def ynprompt():
    term = getterminal()
    echo (term.magenta+' (' + term.cyan + 'yes'+term.magenta+'/'+term.cyan+'no' + term.magenta+')'+ term.white)
    while 1:
        svar = getch()
        if (svar == 'y') or (svar == 'Y'):
            yn = True
            echo (u' yes!')
            break
        if (svar == 'n') or (svar == 'N') or (svar == 'q') or (svar == 'Q'):
            yn = False
            echo (u' no')
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
    counter = 0

    if not session.user.handle in db: # create database for user if the user hasn't made any votes
        db[session.user.handle] = {}
    uservotingdata = db[session.user.handle]

    echo(term.clear()+term.blue+'>>'+term.white+'questions availible\r\n'+term.blue+'---------------------\r\n\r\n'+term.white)
    for i in range (0, len(questions)):
        if (index[i], 0) in uservotingdata:
            echo(term.green+'*') # prints out a star to show that the user already voted on this question
        echo(term.magenta+'('+term.cyan+str(i)+term.magenta+') '+term.white+questions[i]+'\r\n')

        counter = counter + 1 # if the list of questions is longer than the screen height, display a press enter prompt
        if counter > term.height - 7:
            counter = 0
            waitprompt()
            echo (term.move_x(0)+term.clear_eol+term.move_up)

    echo(term.bold_black+'* = already voted\r\n\r\n'+term.normal)

    while 1:
        echo(term.magenta+'\rselect one of the questions above or press enter to return: ')
        le = LineEditor(30)
        le.colors['highlight'] = term.cyan
        inp = le.read()
        if inp.isnumeric() and int(inp) < len(questions):
            return int(inp)
        else:
            return 999    # 999 in this case means that no valid option was chosen.. break loop.
      
# -----------------------------------------------------------------------------------

def list_results(questionnumber):
    term = getterminal()

    db = DBProxy(databasename)
    alternatives = {}
    questions = []
    results = []
    amount_of_alternatives = []
    amount_of_alternatives = db['amount_of_alternatives']
    alternatives = db['alternatives']
    alternatives = db['alternatives']
    questions = db['questions']
    results = db['results']
    index = db['index']
    counter = 0

    echo (term.clear())
    echo (term.white+questions[questionnumber]+term.move_x(term.width-10)+' index: '+str(index[questionnumber])+
          '\r\n'+term.blue+'-'*len(questions[questionnumber])+'\r\n\r\n')
    echo (term.magenta+'(alternatives)'+term.move_x(49)+'(votes)'+term.move_x(57)+'(percentage)\r\n')


    totalvotes = 0.00
    for i in range (0,amount_of_alternatives[questionnumber]):
        totalvotes = totalvotes + results[(questionnumber,i)]

    for i in range (0,amount_of_alternatives[questionnumber]):
        if results[(questionnumber,i)] > 0:
            percentage = (results[(questionnumber,i)]/totalvotes)*100
        else:
            percentage = 0
        staple = int(round(percentage / 5))

        echo (term.cyan+term.move_x(49)+str(results[(questionnumber,i)])+'  '+str(int(percentage))+
              '%'+term.move_x(57)+'[                    ]'+term.move_x(58)+term.green+'#'*staple+'\r')
        echo (term.white+alternatives[(questionnumber,i)]+'\r\n')

        counter = counter + 1 # if the list of questions is longer than the screen height, display a press enter prompt
        if counter > term.height - 7:
            counter = 0
            waitprompt()
            echo (term.move_x(0)+term.clear_eol+term.move_up)

    waitprompt()

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
    amount_of_alternatives =db['amount_of_alternatives']
    index = db['index']

    echo(term.clear()+term.white+questions[questionnumber]+'\r\n\r\n')
    for i in range (0,amount_of_alternatives[questionnumber]):
        echo(term.magenta+'('+term.cyan+str(i)+term.magenta+') '+term.white+alternatives[(questionnumber,i)]+'\r\n')
    echo(term.magenta+'('+term.cyan+str(amount_of_alternatives[questionnumber])+term.magenta+')'+term.bold_black+' Add your own answer..\r\n\r\n')

    while 1:
        echo(term.normal+term.magenta+'\rYour choice:: ')
        le = LineEditor(30)
        le.colors['highlight'] = term.cyan
        inp = le.read()
        if inp.isnumeric() and int(inp) <= amount_of_alternatives[questionnumber]:

            if not session.user.handle in db: # create database for user if the user hasn't made any votes
                db[session.user.handle] = {}

            uservotingdata = {}
            uservotingdata = db[session.user.handle]

            if int(inp) == amount_of_alternatives[questionnumber]: # if user wants to create an own alternative..
                echo(term.clear+term.red+'\r\nPress enter to abort.'+term.move(0,0)+term.white+' Your answer: ')
                le = LineEditor(48)
                new_alternative = le.read()
                if new_alternative == '':
                    return
                results[(questionnumber,int(inp))] = 0 # init..
                alternatives[(questionnumber,int(inp))] = new_alternative # init..
                amount_of_alternatives[questionnumber] = amount_of_alternatives[questionnumber] + 1
                db['alternatives'] = alternatives
                db['amount_of_alternatives'] = amount_of_alternatives 

            if (index[questionnumber], 0) in uservotingdata: # if the user has voted on this question before..
                temp2 = uservotingdata[(index[questionnumber],0)]
                results[(questionnumber,temp2)] = results[(questionnumber,temp2)] -1 # remove the old vote
                results[(questionnumber,int(inp))] = results[(questionnumber,int(inp))] +1
                uservotingdata[(index[questionnumber],0)] = int(inp)
            else:
                uservotingdata[(index[questionnumber],0)] = int(inp)
                results[(questionnumber,int(inp))] = results[(questionnumber,int(inp))] +1

            uservotingdata[(index[questionnumber],0)] = int(inp)

            echo(term.green+'\r\nyour vote has been noted, thanks..')
            getch(1)
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
    amount_of_alternatives =db['amount_of_alternatives']
    amount_of_questions = len(questions)

    echo(term.clear+term.white+'\r\nQuestion: ')
    le = LineEditor(65)
    new_question = le.read()
    if new_question == '':
        return

    echo(term.bold_black+'\r\n\r\nLeave a blank line when you are finished..')
    new_amount = 0
    while 1:
        echo(term.normal+term.white+'\r\nchoice '+term.red+str(new_amount)+term.white+': ')
        le = LineEditor(48)
        alternatives[(amount_of_questions, new_amount)] = le.read()
        if alternatives[(amount_of_questions, new_amount)] == '':
            break
        else:
            results[(amount_of_questions,new_amount)] = 0
            new_amount = new_amount + 1

    if new_amount > 0:
        echo(term.normal+term.white+'\r\n\r\nSave this voting question?')
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

            waitprompt()

# -----------------------------------------------------------------------------------

def delete_question(questionnumber):
    term = getterminal()
    db = DBProxy(databasename)

    alternatives = {}
    questions = []
    results = {}
    amount_of_alternatives = []
    questions=db['questions']
    results=db['results']
    amount_of_alternatives=db['amount_of_alternatives']
    alternatives=db['alternatives']
    index = db['index']
    
    echo(term.clear+term.white+'Delete the '+term.magenta+'('+term.cyan+'e'+term.magenta+')'+term.white+
         'ntire question or delete single '+term.magenta+'('+term.cyan+'a'+term.magenta+')'+term.white+'lternatives?'+
         '\r\n\r\n'+term.magenta+'command:: ')

    le = LineEditor(30)
    le.colors['highlight'] = term.cyan
    inp = le.read()
    inp = inp.lower() # makes the input indifferent to wheter you used lower case when typing in a command or not..

    if inp == 'a': # delete answer alternative..
        echo (term.clear)
        echo (term.white+questions[questionnumber]+term.move_x(term.width-12)+' index: '+str(index[questionnumber])+'\r\n\r\n')
        for i in range (0,amount_of_alternatives[questionnumber]):
            echo (term.cyan+str(i)+'. '+term.white+alternatives[(questionnumber,i)]+'\r\n')

        echo(term.magenta+'\r\nSelect a number. Enter to abort: ')

        le = LineEditor(30)
        le.colors['highlight'] = term.cyan
        inp2 = le.read()

        if inp2.isnumeric() and int(inp2) < amount_of_alternatives[questionnumber]:
            if int(inp2)+1 < amount_of_alternatives[questionnumber]:
                for i in range (int(inp2),amount_of_alternatives[questionnumber]-1):
                    alternatives[(questionnumber,i)] = alternatives[(questionnumber,i+1)]
                    results[(questionnumber,i)] = results[(questionnumber,i+1)]
        else:
            return
        amount_of_alternatives[questionnumber] -= 1

    elif inp == 'e': # delete entire question..
        if questionnumber+1 < len(questions):
            for i in range (questionnumber, len(questions)-1):
                questions[i] = questions[i+1]
                amount_of_alternatives[i] = amount_of_alternatives[i+1]
                index[(i)] = index[(i+1)]
                for i2 in range(0,amount_of_alternatives[i+1]):
                    alternatives[(i,i2)] = alternatives[(i+1,i2)]
                    results[(i,i2)] = results[(i+1,i2)]
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

def generate_database(): # generates a database file with a generic question.
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
    amount_of_alternatives.append(4) # this is the only list/dict that is not zerobased..

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
    echo(term.clear())

    db = DBProxy(databasename)  
    if not 'questions' in db:
        generate_database()

    while True: 
        echo(term.clear()) # clears the screen and displays the vote art header
        for line in showart(os.path.join(os.path.dirname(__file__),'art','vote.ans'),'topaz'):
            echo(term.cyan+term.move_x((term.width/2)-40)+line)

        if 'sysop' in session.user.groups:
            spacing = 1
        else:
            spacing = 7
            echo(' ')
        echo(term.magenta+'\n ('+term.cyan+'r'+term.magenta+')'+term.white+'esults'+' '*spacing)
        echo(term.magenta+'('+term.cyan+'v'+term.magenta+')'+term.white+'ote on a question'+' '*spacing)
        echo(term.magenta+'('+term.cyan+'a'+term.magenta+')'+term.white+'dd a new question'+' '*spacing)
        if 'sysop' in session.user.groups:
            echo(term.magenta+'('+term.cyan+'d'+term.magenta+')'+term.white+'elete a question'+' '*spacing)
        echo(term.magenta+'('+term.cyan+'q'+term.magenta+')'+term.white+'uit')
        echo(term.magenta+'\r\n\r\n\r\nx/84 voting booth command: ')  
        le = LineEditor(30)
        le.colors['highlight'] = term.cyan
        inp = le.read()
        inp = inp.lower() # makes the input indifferent to wheter you used lower case when typing in a command or not..

        if 'sysop' in session.user.groups and inp == 'd':
            while 1:
                questionnumber = query_question()
                if questionnumber == 999:
                    break
                delete_question(questionnumber)
        elif inp == 'r':
            while 1:
                questionnumber = query_question()
                if questionnumber == 999:
                    break
                list_results(questionnumber)
        elif inp == 'v':
            while 1:
                questionnumber = query_question()
                if questionnumber == 999:
                    break
                vote(questionnumber)
        elif inp == 'a':
            add_question()
        elif inp == 'q':
            return
        else:
            echo(term.red+'\r\nNo such command. Try again.\r\n') # if no valid key is pressed then do some ami/x esthetics.
            waitprompt()
