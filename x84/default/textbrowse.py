""" Bulletins / Gallery script for x/84 bbs, https://github.com/jquast/x84 """

# Variables for start position of lightbar etc can be found in def main()
# If you are running this on a -Windows- machine you will have to search
# and replace the '/' with '\' for the directory browsing to work correctly.

from x84.bbs import getsession, echo, getch, gosub, getterminal, showart, getch
import os
from os import walk

__author__ = 'Hellbeard'
__version__ = 1.1


# ---------------------------------------------------

def banner():
    term = getterminal()
    banner = ''
    artfile = os.path.join(os.path.dirname(__file__), 'art', 'bulletins.ans')
    for line in showart(artfile,'topaz'):
        banner = banner + line
    return banner

# ---------------------------------------------------

def helpscreen():
    term = getterminal()
    text = []
    text.append (u'x/84 bulletins v 1.1')
    text.append (u'')
    text.append (term.bold_white+term.underline+u'Key bindings for the navigator:'+term.normal)
    text.append (u'(Q/Escape) to quit.')
    text.append (u'(Up/Dn/Right/Left/Pgup/Pgdn/Enter) to navigate.')
    text.append ('')
    text.append (term.bold_white+term.underline+u'Key bindings for the file viewer:'+term.normal)
    text.append (u'(Q/Escape/Enter) to return.')
    text.append (u'(Up/Dn/Right/Left/Pgup/Pgdn) to navigate.')
    text.append ('')
    text.append (term.bold_white+term.underline+'General key bindings:'+term.normal)
    text.append (u'(Alt+f) change to a more appropiate font in Syncterm.')

    echo(term.clear()+banner()+term.move_y(8))
    for line in text:
        echo(term.move_x(8)+line+u'\r\n')

# ---------------------------------------------------

def displayfile(filename):
    term = getterminal()
    echo(term.clear+term.move(0,0)+term.normal)

    text = {}
    counter = 0
    offset = 0
    keypressed = ''

    for line in showart(filename):	# the string array named text will be zerobased
        text[counter] = line
        counter = counter + 1

    while 1:
        echo(term.move(0,0)+term.normal)
        for i in range (0, term.height-1): # -2 om man vill spara en rad i botten
            if len(text) > i+offset:
                echo(term.clear_eol+u'\r'+text[i+offset])

        keypressed = getch()
        echo(term.hide_cursor)
        if keypressed == 'q' or keypressed == 'Q' or keypressed == term.KEY_ESCAPE or keypressed == term.KEY_ENTER:
            break

        if keypressed == term.KEY_HOME:
            offset = 0

        if keypressed == term.KEY_END:
            if len(text) < term.height: # if the textline has fewer lines than the screen..
                offset = 0
            else:
                offset = len(text) - term.height+1

        if keypressed == term.KEY_DOWN:
            if len(text) > offset+term.height-1: #offset < len(text) + term.height:
                offset = offset + 1

        if keypressed == term.KEY_UP:
            if offset > 0:
                offset = offset -1

        if keypressed == term.KEY_LEFT or keypressed == term.KEY_PGUP:
            if offset > term.height:
                offset = offset - term.height+2
            else:
                offset = 0

        if keypressed == term.KEY_RIGHT or keypressed == term.KEY_PGDOWN:
            if (offset+term.height*2)-1 < len(text):
                offset = offset + term.height-2
            else:
                if len(text) < term.height: # if the textline has fewer lines than the screen..
                     offset = 0
                else:
                     offset = len(text) - term.height+1
         
# ---------------------------------------------------

def redrawlightbar(filer, lighty,lightx,lightbar,start,antalrader): # if the variable lightbar is negative the lightbar will be invisible
    term = getterminal()
    echo(term.move(lighty,lightx))

    for i in range (0, 10):
        echo(term.move(lighty+i-1,lightx)+'                                             ') # erases 45 char. dont want to use clreol. So filenames/directories can be 45 char.

    i2 = 0
    for i in range (start,start+antalrader):
        if i2 == lightbar:
            echo(term.move(lighty+i-start-1,lightx)+term.blue_reverse+filer[i]+term.normal)
        else:
            echo(term.move(lighty+i-start-1,lightx)+term.white+filer[i])
        i2 = i2 + 1

# ---------------------------------------------------

def getfilelist(katalog):
    filer = []
    kataloger = []
    for (dirpath, dirnames, filenames) in walk(katalog):
        filer.extend(sorted(filenames, key=str.lower))
        kataloger.extend(dirnames)
        break
    for i in range (0, len(kataloger)):
        filer.insert(0,kataloger[i]+'/')
    return filer

# ---------------------------------------------------

def main():
    """ Main procedure. """
    session = getsession()
    term = getterminal()
    session.activity = u'browsing textfiles'
    echo(term.clear+banner())

#********** default variables for you to change ! ************* 

    startfolder = os.path.join(os.path.dirname(__file__), 'art', 'bulletins/') # the folder where you store your textfiles..
    lightx = 8                                      # xpos for the lightbar
    lighty = 10                                     # ypos for the lightbar
    max_amount_rows = 10

    currentfolder = startfolder                     # dont change these three lines..
    filer = []
    filer = getfilelist(currentfolder)

    if len(filer) > max_amount_rows:
        antalrader = max_amount_rows
    else:
        antalrader = len(filer)
# antalrader = amount of rows to be displayed. By default it will display up to 14 lines. More wont fit because of the artwork.
# as for colours and stuff.. just search and replace.
#****************************************************************

    offset = 0
    lightbarpos = 0
    keypressed = ''

    redrawlightbar(filer, lighty,lightx,lightbarpos,offset,offset+antalrader)
    echo(term.hide_cursor)

    while 1:

        keypressed = getch()

        if keypressed == 'q' or keypressed == 'Q' or keypressed == term.KEY_ESCAPE:
            echo(term.normal_cursor)
            return

        if keypressed == term.KEY_LEFT or keypressed == term.KEY_PGUP:
            offset = offset - antalrader
            if offset < 0:
                offset = 0
                lightbarpos = 0
            redrawlightbar(filer, lighty,lightx,lightbarpos,offset,antalrader)

        if keypressed == term.KEY_RIGHT or keypressed == term.KEY_PGDOWN:
            offset = offset + antalrader
            if offset+antalrader > len(filer)-1:
                offset = len(filer) - antalrader
                lightbarpos = antalrader-1
            redrawlightbar(filer, lighty,lightx,lightbarpos,offset,antalrader)

        if keypressed == term.KEY_UP and lightbarpos+offset > -1:
            echo(term.white+term.move(lighty+lightbarpos-1,lightx)+filer[lightbarpos+offset]) # restore colour on the old coordinate
            lightbarpos = lightbarpos - 1 
            if lightbarpos < 0:
               if offset > 0:
                   offset = offset - 1
               lightbarpos = lightbarpos + 1
               redrawlightbar(filer, lighty,lightx,-1,offset,antalrader)

            echo(term.blue_reverse+term.move(lighty+lightbarpos-1,lightx)+filer[lightbarpos+offset]+term.normal)

        if keypressed == term.KEY_DOWN and lightbarpos+offset < len(filer)-1:
            echo(term.white+term.move(lighty+lightbarpos-1,lightx)+filer[lightbarpos+offset]) # restore colour on the old coordnate 
            lightbarpos = lightbarpos + 1
            if lightbarpos > antalrader-1:
               offset = offset + 1
               lightbarpos = lightbarpos- 1
               redrawlightbar(filer, lighty,lightx,-1,offset,antalrader)

            echo(term.blue_reverse+term.move(lighty+lightbarpos-1,lightx)+filer[lightbarpos+offset]+term.normal)

        if keypressed == 'h':
            helpscreen()            
            getch()
            echo(term.clear+banner()+term.normal)
            redrawlightbar(filer, lighty,lightx,lightbarpos,offset,antalrader)


        if keypressed == term.KEY_ENTER:

            if filer[lightbarpos+offset][-1:] == '/':
                currentfolder = currentfolder + filer[lightbarpos+offset]
                filer = getfilelist(currentfolder)
#                oldlightbarpos = lightbarpos # saves the location of the lightbar in previous directory
                filer.insert(0,'(..) GO BACK')
                offset = 0  
                lightbarpos = 0


                if len(filer) > max_amount_rows:
                    antalrader = max_amount_rows
                else:
                    antalrader = len(filer)    # stops the script from printing none-existing rows

                redrawlightbar(filer, lighty,lightx,lightbarpos,offset,antalrader)

            elif filer[lightbarpos+offset] == '(..) GO BACK':
                for i in range (2,50): # support folders up to 50 characters..
                    if currentfolder[len(currentfolder)-i] == '/':
                        currentfolder = currentfolder[:-i+1]
                        offset = 0
                        lightbarpos = 0
#                        lightbarpos = oldlightbarpos # restores the lightbarpos previously used in the old directory
                        filer = getfilelist(currentfolder)
                        if currentfolder != startfolder:
                            filer.insert(0,'(..) GO BACK')
                        if len(filer) > max_amount_rows:
                            antalrader = max_amount_rows
                        else:
                            antalrader = len(filer)
                        redrawlightbar(filer, lighty,lightx,lightbarpos,offset,antalrader)
                        break
            else:
                displayfile(currentfolder+filer[lightbarpos+offset])
                echo(term.clear+banner()+term.normal)
                redrawlightbar(filer, lighty,lightx,lightbarpos,offset,antalrader)
