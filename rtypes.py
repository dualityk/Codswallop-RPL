
# CODSWALLOP RPL (a zen garden)
# #####################################################
# Types

# This contains all the object type classes, and also includes the
# rpltypes class, which is what the runtime takes.  The runtime also
# requires this module, since it needs a few of these types for its
# own purposes, but more types can be added freely.

# Normally one would just call baseregistry(), which returns an
# rpltypes object prefabulated with all the types in this module.
# From there, more types can be added with the rpltypes.register method,
# with the rpltypes.updatestore method called afterward to keep the
# in-interpreter Types directory up to date.

from trivia import *
import parse

import copy

# Type registry.  This contains a dictionary matching human readable
# names with type numbers, a matching list to do the reverse, and a
# list of classes matching these types for parsing purposes.  Calling
# register(class) will add a new type, and updatestore() will record
# the registry into the Types directory within RPL.

class rpltypes:
  def __init__(self):
    # Our name to number dictionary.
    self.id = {'Any': 0}
    # Our number to name list.
    self.n = ['Any']
    # Our list of classes for the parser.
    self.parsetypes = []
    # Finally, reference to the object class itself.
    self.prototype = {}
  def register(self, obj):
    newnumber = len(self.n)
    # Put new objects at the beginning of the parse list.  This way,
    # unquoted symbols can be added first and always get last priority.
    self.parsetypes = [obj] + self.parsetypes
    self.id[obj.typename] = newnumber
    self.n += [obj.typename]
    self.prototype[obj.typename] = obj
    obj.typenum = newnumber
    
  def updatestore(self, runtime):
    # Create a new Types directory and populate it with type names
    # containing their matching type numbers, as well as a list 'n'
    # with all the names for given numbers.
    # We do have to reverse the reverse list since parsetypes is backwards.
    runtime.sto(['Types'], runtime.firstdir(runtime.lastobj))
    reverse = []
    runtime.sto(['Types','Any'],typeint(0))
    for i in self.parsetypes:
      runtime.sto(['Types',i.typename], typeint(i.typenum))
      reverse = [typestr(i.typename)]+reverse
    reverse = [typestr('Any')]+reverse
    runtime.sto(['Types','n'], typelst(reverse))
  
  
# Archetypal object.  An RPL typed object always contains a type number
# and the actual data.  It will also, at minimum, have these methods.
class objarchetype:
  # The human-readable name of our type.
  typename = 'Archetype'
  
  # And a number to be filled in when the type is registered.
  typenum = None
  
  # A hint about its function, for builtins.
  hint = None

  # A string parser, which receives a token, attempts to turn it into an
  # object, and returns some indication of why it can't, if it can't.
  # This is a function, not a method.
  def parse(token):
    pass

  # A constructor to initialize the data payload common to all objects.
  def __init__(self, x=None):
    if x != None:
      self.data = x

  # A string representation of the object which includes delimiters.
  def unparse(self, maxdepth=None):
    return str(self.data)
  
  # And a string representation suitable for displaying on the console.
  def disp(self):
    return self.unparse()
  
  # Return a duplicate object.  For immutable types, it returns itself.
  def dup(self):
    return self
    
  # A self-evaluation routine, which usually pushes the object to the stack.
  def eval(self, runtime):
    runtime.Stack.push(self)

  # A runtime evaluation routine, which is how the object will behave when
  # encountered in a program by the runtime.
  def rteval(self, runtime):
    runtime.Stack.push(self)
    
  # Self-documentation facility.
  def doc(self, runtime):
    if self.typenum:
      print('Fundamental data type',self.typenum,'('+self.typename+')')
    else:
      print('Unregistered data type '+self.typename)
    if self.hint:
      print(self.hint)


# Binary call, the barest wrapper around a Python function.
class typebinproc(objarchetype):
  typename = 'Internal'
  data = '(internal)'
  hint = 'A mystery; an enigma; a crash lying in wait...'
  def __init__(self, procedure, hint=None):
    self.eval = procedure
    self.rteval = procedure
    if hint:
      self.hint = hint
    

# Integer type.
class typeint(objarchetype):
  typename = 'Integer'
  
  def parse(token):
    # Common failure routine.
    def parseerror():
      token.error = 'This integer is barely even an integer at all'
      token.stop = True
      
    # All integers start with a pound sign.
    cursor = token.cursor   
    if token.text[cursor] == '#':
      cursor += 1
      prefix = ''
      if cursor >= len(token.text):
        parseerror()
        return
      # Check for optional sign.
      if token.text[cursor] == '+':
        cursor += 1
      elif token.text[cursor] == '-':
        prefix = '-'
        cursor += 1
        
      # Now rummage for numbers.
      text, cursor = parse.getnumber(token.text, cursor)
            
      # Now try to make whatever we got be a number.  Parsenumber must have
      # returned something, and that something must have been followed by
      # whitespace or EOF to be valid.
      if len(text) and\
         (cursor == len(token.text) or token.text[cursor] in token.whitespace):
        try:
          # If this works, advance the cursor and return our object.
          token.validnext(typeint(int(prefix+text)), cursor)
        except:
          parseerror()
      else:
        parseerror()      
    
  def __init__(self, x):
    self.data = int(x)
  def unparse(self, maxdepth=None):
    return '#'+str(self.data)
  def disp(self):
    return str(self.data)

# Float type.
class typefloat(objarchetype):
  typename = 'Float'
  
  def parse(token):
    # Common failure routine.
    def parseerror():
      token.error = 'This number is not much of a float'
      token.stop = True
              
    # First, check for a sign.
    cursor = token.cursor
    text = ''	
    if token.text[cursor] == '+':
      cursor += 1
    elif token.text[cursor] == '-':
      text += '-'
      cursor += 1      
    
    # Second, try to read an integer or decimal point, but fall through 
    # error-free otherwise.
    if cursor < len(token.text) and token.text[cursor] in '.0123456789':
      # This will be our integer portion, if there is one.
      value, cursor = parse.getnumber(token.text, cursor)
      text += value
                  
      # If we have a decimal point, add it and whatever integer may follow.
      if cursor < len(token.text) and token.text[cursor] == '.':
        cursor += 1
        value, cursor = parse.getnumber(token.text, cursor)
        text += '.' + value

      # If there's an exponent, add it and whatever integer may follow also.
      if cursor < len(token.text) and token.text[cursor] == 'e':
        cursor += 1
        value, cursor = parse.getnumber(token.text, cursor)
        # If there's an e but no exponent, fail.
        if len(value):
          text += 'e' + value
        else:
          parseerror()
        
      # If we're at whitespace or EOF, return an object.  If there's
      # trailing garbage, raise an error.
      if cursor >= len(token.text) or token.text[cursor] in token.whitespace:
        try:
          # If this works, advance the cursor and return our object.
          token.validnext(typefloat(float(text)), cursor)
        except:
          parseerror()      
      else:
        parseerror()

  def __init__(self, x):
    self.data = float(x)

# String type.
class typestr(objarchetype):
  typename = 'String'

  def parse(token):    
    # All strings begin and end with a quote.
    cursor = token.cursor
    if token.text[cursor] == '"':
      cursor += 1
      ourtext, cursor = parse.getstring(token.text, cursor, '"')
      if cursor < len(token.text) and token.text[cursor] == '"':
        token.validnext(typestr(ourtext), cursor+1)
      else:
        token.error = "Strings don't just start with quotes"
        token.stop = True
        
  def __init__(self, x):
    self.data = str(x)
  def unparse(self, maxdepth=None):
    return '"'+self.data+'"'
  def disp(self):
    return self.data

# Quoted symbol type.
class typesym(objarchetype):
  typename = 'Symbol'

  def parse(token):    
    # If it starts with a tic, it's a quoted symbol.
    cursor = token.cursor
    if token.text[cursor] == "'":
      cursor += 1
      ourtext, cursor = parse.getstring(token.text, cursor, "'")
      
      # It might be valid if the quote is closed.
      if cursor < len(token.text) and token.text[cursor] == "'":
        if parse.validatename(ourtext):
          # Make a list out of our symbol.
          ourtext = ourtext.split('.')
          token.validnext(typesym(ourtext), cursor+1)
        else:
          token.error = "Are you trying to break shit with delimiters in symbol names?"
          token.stop = True
      else:
        token.error = "Quoted symbol never unquoted"
        token.stop = True
  
  def __init__(self, x):
    #self.data = str(x)
    self.data = x
  def unparse(self, maxdepth=None):
    return "'"+symtostr(self.data)+"'"
  # Evaluating a symbol attempts to retrieve it by name and evaluate that.
  def eval(self, runtime):
    x = runtime.rcl(self.data)
    if x != None:
      x.eval(runtime)
    else:
      runtime.Caller = 'this symbol'
      oursym = symtostr(self.data)
      runtime.ded('We seek '+oursym+' but we cannot always find '+oursym)

# Unquoted symbol type (will not normally exist on stack, only in lists and
# programs). This is probably just an immediate command, though recalling a
# builtin can leave one on the stack.
class typeunq(typesym):
  typename = 'Function'
  def __init__(self, x):
    #self.data = str(x)
    self.data = x
    self.rteval = self.eval
  
  def parse(token):    
    cursor = token.cursor
    ourtext, cursor = parse.getstring(token.text, cursor, token.whitespace)
    
    # A little bit of preprocessing here.  If a symbol starts with a grave,
    # try to recall it.  This can be used to insert constants without excess
    # chicanery.  If the name doesn't exist at the moment, we just return
    # the symbol sans grave.
    if len(ourtext)>1 and ourtext[0] == '`':
      ourtext = ourtext[1:]
      recallattempt = True
    else:
      recallattempt = False
    if parse.validatename(ourtext):
      # Split up our directory tree here.
      ourtext = ourtext.split('.')
      if recallattempt:
        thing = token.runtime.rcl(ourtext)
        if thing != None:
          token.validnext(thing, cursor)
        else:
          token.validnext(typeunq(ourtext), cursor)
      else:
        token.validnext(typeunq(ourtext), cursor)
    else:
      token.error = "Are you trying to break shit with delimiters in symbol names?"
      token.stop = True
  
  def disp(self):
    return symtostr(self.data)
  def unparse(self, maxdepth=None):
    return symtostr(self.data)

# Comment string.  A special case string that's retained in programs and lists
# but vanishes when evaluated.
class typerem(typestr):
  typename = 'Comment'

  def parse(token):    
    # Comments begin with ( and end with ).
    cursor = token.cursor
    if token.text[cursor] == ')':
      token.error = "This looks like a shut and open case"
      token.stop = True
    elif token.text[cursor] == '(':
      cursor += 1
      ourtext, cursor = parse.getstring(token.text, cursor, ')')
      if cursor < len(token.text) and token.text[cursor] == ')':
        token.validnext(typerem(ourtext), cursor+1)
      else:
        token.error = "These remarks have gone on far too long"
        token.stop = True
  
  def eval(self, runtime):
    pass
  
  def rteval(self, runtime):
    pass
    
  def unparse(self, maxdepth=None):
    return '('+self.data+')'

# Directory type.  
# A specific purpose, singly linked list used for named storage:
# 'tag' is a Tag,
# 'next' is the next Directory.
class typedir(objarchetype):
  typename = 'Directory'
  
  def __init__(self, name, nextobj):
    self.tag = name
    if nextobj is None:
      self.next = self
    else:
      self.next = nextobj
  def unparse(self, maxdepth=None):
    return "[directory]"

# Tag type.
# Also a specific purpose thing used for named storage:
# 'name' is a string, an unqualified name with no periods
# 'obj' is any old thing, but has to be an RPL type.
# Tags are expressly mutable and can be used to pass a reference
# when that's useful, such as for closures, or when the original
# name may be covered by a local variable.
class typetag(objarchetype):
  typename = 'Tag'
  
  def __init__(self, data, obj):
    self.name = data
    self.obj = obj

  def dup(self):
    return copy.copy(self)
    
  def parse(token):    
    # Tags will look like :name:thing, so we have to make sure we're
    # not actually looking at the beginning of a :: code block.
    cursor = token.cursor
    if token.text[cursor] == ":" and token.text[cursor:cursor+2] != "::":
      # Increment our cursor and see what we got for a name.
      cursor += 1
      ourtext, cursor = parse.getstring(token.text, cursor, ":")

      # It's possible a chucklefuck could end a sentence with a colon,
      # or fail to close the name section.
      if cursor < len(token.text) and token.text[cursor] == ":":
        # And it's also possible they didn't give us a valid name.
        if parse.validatename(ourtext) and not '.' in ourtext:
          # But if they did, now increment and try to retrieve a valid object.
          cursor += 1
          newtoken = parse.parsetoken(token.runtime, token.text, cursor)
          newtoken.nextobj()
          # Did we get a thing?
          if not newtoken.stop:
            # We did, so fashion a new tag.
            token.validnext(typetag(ourtext, newtoken.data), newtoken.cursor)
          elif newtoken.valid:
            # We didn't get anything, that's a paddlin'.
            token.cursor = cursor
            token.error = "You should put something here"
            token.stop = True
          else:
            # We got an error, pass it along.
            token.cursor = newtoken.cursor
            token.error = newtoken.error
            token.stop = True
        else:
          token.cursor += 1
          token.error = "This must be a kind-hearted, pure, and dotless symbol"
          token.stop = True
      else:
        token.error = "Colon what, dear"
        token.stop = True

  def unparse(self, maxdepth=None):
    return ":"+self.name+": "+self.obj.unparse()

# List type.
class typelst(objarchetype):
  typename = 'List'
  
  def parse(token):
    cursor = token.cursor
    
    # Just to be a good sport, catch spurious closed brackets too.
    if token.text[cursor] == '}':
      token.error = 'Wherever this was supposed to go, it wasn\'t here'
      token.stop = True
    elif token.text[cursor] == '{':
      cursor += 1
      newlist, newtoken = parse.parsecomposite(token.runtime, token.text, cursor, '}')
      
      # If parsecomposite wasn't stopped, there was no error or EOF.
      if not newtoken.stop:
        token.validnext(typelst(newlist), newtoken.cursor+1)
      elif newtoken.valid:
        # If there wasn't an error, we got to EOF, which is an error,
        # and we'll set the cursor to the beginning of the offending list.
        token.error = 'Somewhere, a list is missing its }'
        token.stop = True
      else:
        # If there was an error, something in the list was invalid, and
        # we'll set the cursor and message to the offending entry.
        token.error = newtoken.error
        token.cursor = newtoken.cursor
        token.stop = True
  
  def __init__(self, x=None):
    if x:
      self.data = x
    else:
      self.data = []

  def __len__(self):
    return len(self.data)
    
  # Duplicating a list makes a new list, but points to old objects.
  def dup(self):
    newme = copy.copy(self)
    newme.data = newme.data[:]
    return newme

  # Helpers for stack use.
  def push(self, value):
    self.data.append(value)
  def pop(self):
    if len(self.data):
      return self.data.pop()
    else:
      return None

  # Lists print all their contents recursively (to a point).
  def unparse(self, maxdepth=PRINTDEPTH):
    output = "{ "
    if maxdepth:
      for i in self.data:
        output += i.unparse(maxdepth=maxdepth-1) + " "
    else:
      output += BOOORING
    output += "}"
    return output

  # Explicitly displaying lists will recurse fully.
  def disp(self):
    return self.unparse(maxdepth=-1)
 
# Code type.  This is very much a list.
class typecode(typelst):
  typename = 'Code'
  
  def parse(token):
    cursor = token.cursor
    
    # And catch semicolons here too; if they got this far, they're spurious.
    if token.text[cursor] == ';':
      token.error = 'Perhaps this semicolon should be somewhere else'
      token.stop = True
    elif token.text[cursor:cursor+2] == '::':
      cursor += 2
      newlist, newtoken = parse.parsecomposite(token.runtime, token.text, cursor, ';')
      
      # If parsecomposite wasn't stopped, there was no error or EOF.
      if not newtoken.stop:
        token.validnext(typecode(newlist), newtoken.cursor+1)
      elif newtoken.valid:
        # If there wasn't an error, we got to EOF, which is an error,
        # and we'll set the cursor to the beginning of the offending list.
        token.error = 'Semicolons are cool, you should try one more'
        token.stop = True
      else:
        # If there was an error, something in the list was invalid, and
        # we'll set the cursor and message to the offending entry.
        token.error = newtoken.error
        token.cursor = newtoken.cursor
        token.stop = True
  
  # Evaluating code pushes it to the call stack rather than the data stack.
  def eval(self, runtime):
    runtime.newcall(self)

  # Print routine has a highlighting helper for tracebacks.
  def unparse(self, highlight=-1, maxdepth=PRINTDEPTH):
    output = ":: "
    if maxdepth:
      for i in range(len(self.data)):
        if i == highlight: output += ANSIINV+" "
        output += self.data[i].unparse(maxdepth=maxdepth-1) + " "
        if i == highlight: output += ANSINORMAL+" "
    else:
      output += BOOORING
    output += ";"
    return output
    
# RPL built-in command type.  This does basic type and argument count
# checking.  It then hops along to dispatch where the command-specific work
# is done.

# For legibility purposes when printing code, data equals the name of the
# function.  This is also used to populate the global store without having
# to name the function twice.

class typebin(objarchetype):
  typename = 'Builtin'
  
  data = 'NOP'
  hint = 'A very lazy person has declined to document this built-in.'

  # A list of possible stack configurations (default, any).
  argck = []
  # Number of expected arguments.
  argct = 0
  
  # On construction, build a dispatch table based upon argck and our
  # list of hooks.
  def __init__(self, data=None):
    if data:
      self.data = data
    self.dispatches = [self.dispatch]
    self.rteval = self.eval
    
  # More comprehensive documentation provided for built-ins based on the
  # standard argument checking and dispatch.
  def doc(self, runtime):
    if self.hint: print(self.hint+'\n')
    print(self.data,'is looking for',self.argct,'arguments.',\
    ' For example:'*(len(self.argck)>0))
    for i in range(len(self.argck)):
      print('Stack configuration '+str(i)+':')
      for j in range(self.argct):
        if self.argck[i][j] < len(runtime.Types.n):
          name = runtime.Types.n[self.argck[i][j]]
        else:
          name = 'Unregistered, imaginary type #'+str(self.argck[i][j])
        print('  Line '+str(self.argct-j)+': '+name)
  
  def eval(self, runtime):
    # Preemptively claim responsibility for errors.
    runtime.Caller = self.data
    
    # First check to see that we have enough arguments.
    if len(runtime.Stack)<self.argct:
      runtime.ded('How about '+str(self.argct)+' arguments instead of '+\
          str(len(runtime.Stack))+'?')
    else:
      # There's enough arguments, so, do we care what they are?
      if len(self.argck):
        # Yes: then check each line of 'argck' and dispatch if args match 
        # what we have.
        wegot = []
        for i in range(len(runtime.Stack.data)-self.argct, 
                       len(runtime.Stack.data)):
          wegot += [runtime.Stack.data[i].typenum]

        for i in range(len(self.argck)):
          match = True
          for j in range(self.argct):
            if self.argck[i][j] and self.argck[i][j] != wegot[j]: match = False
          # Call the first matching line of the dispatch table.
          if match: 
            self.dispatches[i].eval(runtime)
            return
        runtime.ded('There are '+str(len(self.argck))+' ways to call and you tried #'+\
        str(len(self.argck)+1))
      else:
        # No: hit it.
        self.dispatches[0].eval(runtime)
  
  # Default dispatch does nothing.
  def dispatch(self):
    pass

# Prepare an rpltypes object to hand to the runtime, containing our basic
# types.
def baseregistry():
  Types = rpltypes()
  for i in [typebinproc, typeunq, typefloat, typesym, typestr, typerem, 
            typebin, typedir, typetag, typelst, typecode, typeint]:
    Types.register(i)
  return Types

# Return an unparsed dot name from a symbol list.
def symtostr(sym):
  decimalname = sym[0]
  for i in range(1, len(sym)):
    decimalname += '.'+sym[i]
  return decimalname
