
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
    self.usrproto = {}

  def register(self, obj):
    newnumber = len(self.n)
    # Put new objects at the beginning of the parse list.  This way,
    # unquoted symbols can be added first and always get last priority.
    self.parsetypes = [obj] + self.parsetypes
    self.id[obj.typename] = newnumber
    self.n += [obj.typename]
    obj.typenum = newnumber
    self.prototype[obj.typename] = obj
       
  # Register a new user-created type.
  def registerusr(self, obj):
    newnumber = len(self.n)
    self.id[obj.typename] = newnumber
    self.n += [obj.typename]
    obj.typenum = newnumber
    self.prototype[obj.typename] = obj
    self.usrproto[obj.typename] = obj
      
  def updatestore(self, runtime):
    # Create a new Types directory and populate it with type names
    # containing their matching type numbers, as well as a list 'n'
    # with all the names for given numbers.
    # We do have to reverse the reverse list since parsetypes is backwards.
    runtime.sto(['Types'], runtime.firstdir())
    reverse = []
    runtime.sto(['Types','Any'],typeint(0))
    for i in self.parsetypes:
      runtime.sto(['Types',i.typename], typeint(i.typenum))
      reverse = [typestr(i.typename)]+reverse
    for i in self.usrproto.values():
      runtime.sto(['Types',i.typename], typeint(i.typenum))
      reverse += [typestr(i.typename)]
    reverse = [typestr('Any')]+reverse
    runtime.sto(['Types','n'], typelst(reverse))
    if len(self.usrproto):
      runtime.sto(['Types','Proto'], runtime.firstdir())
      for i in self.usrproto:
        runtime.sto(['Types','Proto',i], self.usrproto[i])


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

# Binary call, the barest wrapper around a Python function.
class typebinproc(objarchetype):
  typename = 'Internal'
  data = '(internal)'
  def __init__(self, procedure, hint=None):
    self.eval = procedure
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


# Generic quote type.  When evaluated, it returns its contents, useful for
# preventing the immediate evaluation of code and symbols.
class typequote(objarchetype):
  typename = 'Quote'
  def parse(token):
    #return
    cursor = token.cursor
    if cursor < len(token.text) and token.text[cursor] == "'":
      # But if they did, now increment and try to retrieve a valid object.
      cursor += 1
      newtoken = parse.parsetoken(token.runtime, token.text, cursor)

      # If we're already at the end of the text, that's an error.
      if newtoken.stop: 
        token.cursor = cursor
        token.error = "You should put something here"
        token.stop = True          
      else:
        newtoken.nextobj()
        
        # Did we get a thing?
        if newtoken.valid:
          # We did, so fashion a new tag.
          token.validnext(typequote(newtoken.data), newtoken.cursor)
        else:
          # We got an error, pass it along.
          token.cursor = newtoken.cursor
          token.error = newtoken.error
          token.stop = True

  def eval(self, runtime):
    runtime.Stack.push(self.data)
    
  def unparse(self, maxdepth=None):
    return "'"+self.data.unparse(maxdepth)

# Symbol type.  This evaluates whatever it's pointed to as soon as it's
# encountered.
class typesym(objarchetype):
  typename = 'Symbol'
  def __init__(self, x):
    self.data = x
  
  def parse(token):    
    cursor = token.cursor
    ourtext, cursor = parse.getstring(token.text, cursor, token.whitespace)
    
    # A little bit of preprocessing here.  If a symbol starts with a grave,
    # try to recall it.  This can be used to insert constants without excess
    # chicanery.
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
        if thing is not None:
          token.validnext(thing, cursor)
        else:
          token.error = "This symbol has to exist at parse time"
          token.stop = True
      else:
        token.validnext(typesym(ourtext), cursor)
    else:
      token.error = "Are you trying to break shit with delimiters in symbol names?"
      token.stop = True
  
  def disp(self):
    return symtostr(self.data)
  def unparse(self, maxdepth=None):
    return symtostr(self.data)

  # Evaluating a symbol attempts to retrieve it by name and evaluate that.
  def eval(self, runtime):
    x = runtime.rcl(self.data)
    if x is not None:
      return x.eval
    else:
      runtime.Caller = 'this symbol'
      oursym = symtostr(self.data)
      runtime.ded('We seek '+oursym+' but we cannot always find '+oursym)


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
    # Here so == can hopefully tell us apart by address.
    self.data = self

  def parse(token):
    cursor = token.cursor
    
    # Just to be a good sport, catch spurious closed brackets too.
    if token.text[cursor] == ']':
      token.error = 'Wherever this was supposed to go, it wasn\'t here'
      token.stop = True
    elif token.text[cursor:cursor+5] == '[dir:':
      # Set up our own token and start digging for tags.
      cursor += 5
      newtoken = parse.parsetoken(token.runtime, token.text, cursor)
      firstdir = token.runtime.firstdir()
      nextdir = firstdir
      running = True
      
      while running:
        # If we hit the end, that means we're missing a close bracket.
        if newtoken.stop:
          token.error = 'A directory has failed to ]'
          token.stop = True
          running = False
        # If we found a close bracket, we're done here.
        elif newtoken.text[newtoken.cursor] == ']':
          running = False
          token.validnext(firstdir, newtoken.cursor+1)
        # Otherwise it's tag time.
        else:
          # Only try to parse a tag.
          typetag.parse(newtoken)
          # We got one, so add it to the chain.
          if newtoken.valid:
            newtoken.valid = False
            nextdir.next = typedir(newtoken.data, nextdir.next)
            nextdir = nextdir.next
          # Or tag threw an error, in which case pass it along.  
          elif newtoken.stop:
            token.error = newtoken.error
            token.cursor = newtoken.cursor
            token.stop = True
            running = False
          # Or tag didn't throw an error, in which case it wasn't a tag.
          else:
            token.error = 'Directories can only contain tags'
            token.cursor = newtoken.cursor
            token.stop = True
            running = False
   
  # Duplicating a directory is trickier, because all entries and tags
  # need to be copied.  This was so hairy I had to take a shower to make it.
  def dup(self, depth=CPDEPTH):
    if depth:
      # We have to hang onto 'ourcopy' because that's what we're returning.
      # Rest is our new directory entry of interest, and current is the old
      # structure we're following.
      ourcopy = typedir(self.tag.dup(), self.next)
      rest = ourcopy
      current = self
      # Lastobjs point to themselves, so we only follow til we get to a self-ref.
      while current.next is not current.next.next:
        # Each new 'rest' initially points back to the original list, retaining
        # our global lastobj when we drop out of the loop.
        current = current.next
        rest.next = typedir(rest.next.tag.dup(), current.next)
        rest = rest.next
        # We have to recurse to catch subdirectories, but only to a point.
        if rest.tag.obj.typenum == self.typenum:
          rest.tag.obj = rest.tag.obj.dup(depth-1)
      return ourcopy
    else:
      # If we're out of recursion depth, silently return the original.
      return self
    
  def unparse(self, maxdepth=None):
    return "[directory]"


# IO type.  Used as handles for files and character devices, probably.
class typeio(objarchetype):
  typename = 'Handle'
  
  # Python's EOF handling is kind of garbage, but I feex.
  eof = False
  def __init__(self, data):
    self.data = data
  def __del__(self):
    try:
      self.data.close()
    except:
      print('By the way, a terrible fate has befallen a forgotten file handle')
  def unparse(self, maxdepth=-1):
    return '(I/O handle for '+self.data.name+')'


# Tag type.
# Also a specific purpose thing used for named storage:
# 'name' is a string, an unqualified name with no periods
# 'obj' is any old thing, but has to be an RPL type.
# Tags are expressly mutable and can be used to pass a reference
# when that's useful, such as for closures, or when the original
# name may be covered by a local variable.  It's also the basis
# of the user type scheme.
class typetag(objarchetype):
  typename = 'Tag'
  
  def __init__(self, data, obj):
    self.name = data
    self.obj = obj
    # This is so == can hopefully tell if we're equal by address.
    self.data = self

  def dup(self):
    # Make a copy of the tag, but not the object we contain.
    newtag = typetag(self.name, self.obj)
    # And save our type number, because it may have changed.
    newtag.typenum = self.typenum
    return newtag
    
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
          # If we're already at the end of the text, that's an error.
          if newtoken.stop: 
            token.cursor = cursor
            token.error = "You should put something here"
            token.stop = True          
          else:
            newtoken.nextobj()
            # Did we get a thing?
            if newtoken.valid:
              # We did, so fashion a new tag.
              token.validnext(typetag(ourtext, newtoken.data), newtoken.cursor)
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
    # For now, return a placeholder.
    return "{ … }"
  
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
    
  def unparse(self, maxdepth=PRINTDEPTH):
    # For now, skip the rest of this and print nothing useful.
    return ":: … ;"
  
    output = ":: "
    if maxdepth:
      for i in range(len(self.data)):
        output += self.data[i].unparse(maxdepth=maxdepth-1) + " "
    else:
      output += BOOORING
    output += ";"
    return output
    
# RPL built-in command type.  This does basic type and argument count
# checking.  It then hops along to dispatch where the command-specific work
# is done.

# For legibility purposes when printing code, data equals the name of the
# function.

class typebin(objarchetype):
  typename = 'Builtin'
  
  data = 'NOP'
  hint = 'A very lazy person has declined to document this built-in.'

  # A list of possible stack configurations.
  argck = []
  # A matching list of dispatch functions.
  dispatches = []
  # Number of expected arguments.
  argct = 0
  
  # Conceptually useful for saving a snapshot of a builtin before hooking it.
  def dup(self):
    newbin = typebin()
    newbin.data = self.data
    newbin.argck = self.argck[:]
    newbin.dispatches = self.dispatches[:]
    newbin.argct = self.argct
    newbin.hint = self.hint
    return newbin
    
  def eval(self, runtime):
    # Preemptively claim responsibility for errors.
    runtime.Caller = self.data
    
    # First check to see that we have enough arguments.
    if len(runtime.Stack)<self.argct:
      runtime.ded('How about '+str(self.argct)+' arguments instead of '+\
          str(len(runtime.Stack))+'?')
    else:
      # We do have enough args, so what are they?
      wegot = []
      for i in range(len(runtime.Stack.data)-self.argct, 
                     len(runtime.Stack.data)):
        wegot += [runtime.Stack.data[i].typenum]

      for i in range(len(self.argck)):
        # Check each argument to match type number.  0 will match any type.
        match = True
        for j in range(self.argct):
          if self.argck[i][j] and self.argck[i][j] != wegot[j]: match = False
        # Suggest the runtime call the first matching dispatch.
        if match: 
          return self.dispatches[i].eval
          
      runtime.ded('There are '+str(len(self.argck))+' ways to call and you tried #'+\
      str(len(self.argck)+1))
  


# Prepare an rpltypes object to hand to the runtime, containing our basic
# types.
def baseregistry():
  Types = rpltypes()
  for i in [typebinproc, typesym, typefloat, typestr, typerem,
            typebin, typedir, typetag, typelst, typecode, typeint, typeio,
            typequote]:
    Types.register(i)
  return Types

# Return an unparsed dot name from a symbol list.
def symtostr(sym):
  decimalname = sym[0]
  for i in range(1, len(sym)):
    decimalname += '.'+sym[i]
  return decimalname
