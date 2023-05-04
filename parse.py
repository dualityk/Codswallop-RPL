
# CODSWALLOP RPL (a zen garden)
# #####################################################
# Parser

# Or really parse coordinator.  The actual per-type parsing is done by
# functions for each type class, and coordinated by parse() and various
# helpers.

# Parse token.  This is handed back and forth between the parser and different
# registered object types to turn text into code.  It also contains the
# common methods whiteskip, nextobj, and the callback method validnext.

from trivia import *

class parsetoken:
  whitespace = ' \t\r\n'
  delimiters = ['}', '{', ':', ';']
  
  def __init__(self, runtime, text='', cursor=0):
    self.text = text		# The string to parse
    self.cursor = cursor	# Current position within string
    self.runtime = runtime	# Current runtime
    self.types = runtime.Types  # Current types object
    self.valid = False		# Flag: current object is valid
    self.stop = False   	# Flag: stop parsing, either error or done
    self.data = None    	# Current object
    self.error = ''		# Error message text on invalid stop
    self.whiteskip()
 
  # Skip all the whitespace under the cursor.
  def whiteskip(self):
    while self.cursor < len(self.text):
      if self.text[self.cursor] in self.whitespace:
        self.cursor += 1
      else:
        break
    # And if we reached the end, stop.
    if self.cursor >= len(self.text):
      self.stop = True
  
  # Click through one object.
  def nextobj(self):
    self.valid = False
    # Bounce through all the types, and if we get one, or one throws an
    # error, stop there.
    for i in self.types.parsetypes:
      i.parse(self)
      if self.valid:
        self.whiteskip()
        return
      elif self.stop:
        return
    # If no type claimed ownership, that too is an error.
    self.stop = True
    self.error = 'Whatever this is, it isn\'t'
      
  # Callback method: record valid data returned by an object's parser, 
  # and skip cursor ahead.
  def validnext(self, data, cursor):
    self.data = data
    self.valid = True
    self.cursor = cursor
      
# Parse helpers.

# Look only for numerals and return the final cursor position and whatever
# we got.
def getnumber(text, cursor):
  number = ''
  while cursor < len(text) and text[cursor] in '0123456789':
    number += text[cursor]
    cursor +=1
  return number, cursor

# Retrieve a text string up to a closing character or EOF, and do some
# rudimentary escape character things.
def getstring(text, cursor, delimiter):
  newstring = ''
  while cursor < len(text) and not text[cursor] in delimiter:
    if text[cursor] == '\\':
      cursor += 1
    if cursor < len(text):
      newstring += text[cursor]
      cursor += 1
  return newstring, cursor

# Build a list for a composite type.
def parsecomposite(runtime, text, cursor, delimiter):
  newlist = []
  
  # Build a local parse token.
  localp = parsetoken(runtime, text, cursor)
  while not localp.stop:
    # First check if we're at the end.
    if localp.cursor < len(localp.text) and \
       localp.text[localp.cursor] == delimiter:
      break
    
    # Then try to grab a new object.
    localp.nextobj()
    if localp.valid:
      newlist += [localp.data]
      localp.whiteskip()
    else:
      break
  return newlist, localp

# Check to see if text contains any symbolic naughties.
def validatename(text):
  for i in range(len(text)):
    if text[i] in parsetoken.delimiters or\
       text[i] in parsetoken.whitespace:
      return False
  return True

# Parse any text.
def parse(runtime, text):
  # First, cheekily hand the entire thing to parsecomposite.
  ourlist, token = parsecomposite(runtime, text, 0, None)
  
  # Did we receive something valid?
  if token.valid:
    # If the last thing was valid, everything is valid, and we return the list.
    return ourlist
  else:
    # If invalid, try to show the user roughly where things went sideways.
    print('\nYour words fail to become actions.\n')
    # Get our overall line number.
    linenum = token.text[:token.cursor].count('\n')+1
    # Look back from the cursor to find our last newline.
    newlinecursor = 0
    spotonline = 0
    for i in range(token.cursor-1, -1, -1):
      if token.text[i] == '\n':
        newlinecursor = i+1
        break
      else:
        spotonline += 1
    # Then just fetch this exact line and show cursor position.
    print('Stopped on line '+str(linenum)+', position '+str(spotonline+1)+':')
    print(token.text[newlinecursor:].split('\n')[0])
    print(' '*spotonline+ANSIBRITE+'↳✞'+ANSINORMAL)
    print('In particular:', token.error)    
    # And return nothing.
