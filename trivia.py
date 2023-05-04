
# CODSWALLOP RPL (a zen garden)
# #####################################################
# Trivia

# This contains constants and settings which might be of interest globally. 

# Version string, and our base directory.
VERSION = "Codswallop RPL"
BASDIR =  "./"

# Hard limit on the interpreter's call stack size.  Should be healthy, 
# but bounded.
CALLDEPTH = 2048

# Where to put the sysRPL functions in the named store.
INTERNALSDIR = 'I*'

# Boot program: read and execute 'boot.rpl' out of the base directory.
LAUNCHCODE = ':: BASDIR "boot.rpl" '+INTERNALSDIR+'.+str '+INTERNALSDIR+'.dsk> ;'

# Maximum number of bytes to read from a file into the parser.
MAXREAD = 256000

# ANSI codes for reverse and normal video.
ANSIINV = chr(27)+'[7m'
ANSIBRITE = chr(27)+'[1m'
ANSIDIM = chr(27)+'[2m'
ANSINORMAL = chr(27)+'[0m'

# Print recursion depth for composite objects (on the Python side.)
PRINTDEPTH = 1
BOOORING = ANSIDIM + '...' + ANSINORMAL + ' '

# Names for runtime Calls[] entries: instruction pointer, code object, context.
CALL_IP = 0
CALL_CODE = 1
CALL_CONTEXT = 2

