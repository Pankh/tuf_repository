# -*- coding: utf-8 -*-
### Automatically generated by repyhelper.py ### /home/pankhuri/projects/TUF+SEATTLE/softwareupdater/RUNNABLE/dylink.r2py

### THIS FILE WILL BE OVERWRITTEN!
### DO NOT MAKE CHANGES HERE, INSTEAD EDIT THE ORIGINAL SOURCE FILE
###
### If changes to the src aren't propagating here, try manually deleting this file. 
### Deleting this file forces regeneration of a repy translation


from repyportability import *
from repyportability import _context
import repyhelper
mycontext = repyhelper.get_shared_context()
callfunc = 'initialize'
callargs = []

"""
Author: Armon Dadgar
Description:
  This module is designed to help dynamically link against other modules,
  and to provide a import like functionality in Repy.

  Its main mechanisms are dy_import_module, dy_import_module_symbols, and 
  dy_dispatch_module.
  dy_import_module_symbols allows importing directly into the current 
  context (ala from X import *) and dy_import_module allows importing as 
  an encapsulated module (ala import X as Y).

  dy_dispatch_module is a convenience for programs that want to behavior 
  as "modules". These are behavior altering programs, that don't execute 
  any code, but provide new code or alter behavior of builtin calls. These 
  types of modules expect to be chained and to recursively call into the 
  next module in the chain. dy_dispatch_module will take the globally 
  defined CHILD_CONTEXT and evaluate the next module in that context. 
  Modules are free to alter CHILD_CONTEXT prior to calling dy_dispatch_module.

  Modules being imported are called with callfunc set to "import" to
  allow modules to have special behavior. If the module performs some
  action on import, it is possible that dy_* never returns, as with
  import in Python.
"""

# Initialize globals once
if callfunc == "initialize":
  # Copy our clean context for our child
  CHILD_CONTEXT = _context.copy()
  CHILD_CONTEXT["_context"] = CHILD_CONTEXT
  CHILD_CONTEXT["mycontext"] = {}


  # This holds the set of already imported modules.   The key is the module
  # name and the value is the module object.
  IMPORTED_MODULE_CACHE = {}

  # This cache maps a module name -> a VirtualNamespace object
  # JAC: This caches the "code" *only* for modules.   If the same file is
  # imported twice, this will not cause the references to be saved and reused
  # (See #1320 for why this is a problem.)   
  MODULE_CACHE = {}

  # This cache maps a module name to a VirtualNamespace object for 
  # binding attributes
  MODULE_BIND_CACHE = {}


  # These are the functions in the "stock" repy API,
  STOCK_API = set(['createlock', 'createthread', 'createvirtualnamespace', 
      'dy_dispatch_module', 'dy_import_module', 'dy_import_module_symbols', 
      'exitall', 'gethostbyname', 'getlasterror', 'getmyip', 'getresources', 
      'getruntime', 'getthreadname', 'listenforconnection', 
      'listenformessage', 'listfiles', 'log', 'openconnection', 'openfile', 
      'randombytes', 'removefile', 'sendmessage', 'sleep'])


  # This is the maximum number of bytes we will try to read in for a file.
  # Anything larger and we abort
  MAX_FILE_SIZE = 200000



#### Helper functions ####

# Constructs a "default" context from the given context
# Additional_globals can be an array of "extra" globals, which are
# copied in addition to the STOCK_API
def _default_context(import_context, additional_globals=[]):
  # Construct a new context based on the importer's context
  new_context = SafeDict()
  all_globals = set(additional_globals)
  all_globals.update(STOCK_API)
  for func in all_globals:
    if func in import_context:
      new_context[func] = import_context[func]

  # Add mycontext and _context
  new_context["_context"] = new_context
  new_context["mycontext"] = {}

  # Return the new context
  return new_context




# Constructs the VirtualNamespace that is used to bind the attributes
# Caches this namespace to speed up duplicate imports
def _dy_bind_code(module, context):
  # Check if this is cached
  if module in MODULE_BIND_CACHE:
    return MODULE_BIND_CACHE[module]

  # Construct the bind code
  else:
    # Start constructing the string to form the module
    mod_str = ""

    # Check each key, and bind those we should...
    for attr in context:
      # Skip attributes starting with _ or part of the stock API
      if attr.startswith("_") or attr in STOCK_API:
        continue

      # Bind now
      mod_str += "m." + attr + " = c['" + attr + "']\n"

    # Create the namespace to do the binding
    module_bind_space = createvirtualnamespace(mod_str, module+" bind-space")

    # Cache this
    MODULE_BIND_CACHE[module] = module_bind_space

    # Return the new namespace
    return module_bind_space


# Gets the code object for a module
def _dy_module_code(module):
  # Check if this module is cached
  if module in MODULE_CACHE:
    # Get the cached virtual namespace
    return MODULE_CACHE[module]

  # The module is not cached
  else:
    # Try to get a file handle to the module
    fileh = None
    try:
      fileh = openfile(module, False)
    except FileNotFoundError, err:
      raise RepyImportError("Failed to locate the module! Module: '" + 
              module + "' " + str(err))
    except ResourceExhaustedError:
      raise


    # Read in the code
    code = fileh.readat(MAX_FILE_SIZE, 0)
    fileh.close()
    if len(code) == MAX_FILE_SIZE:
      log("Failed to read all of module (" + module + 
          ")! File size exceeds " + str(MAX_FILE_SIZE) + " characters!\n")


    # Create a new virtual namespace
    try:
      virt = DylinkNamespace(code,module)
    except Exception, e:
      raise Exception("Failed to initialize the module (" + module + 
          ")! Got the following exception: '" + repr(e) + "'")
    
    # Cache the module
    MODULE_CACHE[module] = virt

    # Return the new namespace
    return virt


# This class is used to simulate a module
class ImportedModule:
  """
  Emulates a module object. The instance field
  _context refers to the dictionary of the module,
  and _name is the name of the module.
  """
  # Initiaze the module from the context it was evaluated in
  def __init__(self, name, context):
    # Store the context and name
    self._name = name
    self._context = context

    # Get the binding namespace
    module_bind_space = _dy_bind_code(name, context)

    # Create the binding context
    module_bind_context = {"c": context, "m": self}

    # Perform the binding
    module_bind_space.evaluate(module_bind_context)

  def __str__(self):
    # Print the module name
    return "<Imported module '" + self._name + "'>"

  def __repr__(self):
    # Use the str method
    return self.__str__()


#### Main dylink Functions ####

# Main API call to link in new modules
def dylink_import_global(module, module_context,new_callfunc="import"):
  """
  <Purpose>
    This function performs the equivalent of "from X import *".   It first
    does an import, and then remaps symbols from the module object into the
    provided module_context.

  <Arguments>
    module:
      The filename of a module to import. This must include file extensions 
      (thus making "mylib.py" and "mylib.r2py" distinct modules).

    module_context: 
      The context to evaluate the module in. If you want to do a global import,
      you can evaluate in the current global context. For a bundled module,
      see dylink_import_module.

    new_callfunc:
      The value to use for callfunc during the import.
      Defaults to "import".

  <Exceptions>
    Raises RepyImportError if the module cannot be found, or if there 
    is a problem initializing a VirtualNamespace around the module. 
    See VirtualNamespace.
  
  <Side Effects>
    module_context will likely be modified.  
  """

  # let's do a normal import of this first.   Much like Python, even if one 
  # does "from X import *" multiple times, it only gets initialized once

  # JAC: Potential bug, I do not fully understand why we need 
  # "additional_globals", but I do not believe it was used by this module.   
  # I think it only matters for import.   I am setting to []
  module_object = dylink_import_module(module, module_context, new_callfunc, [])

  # Now remap the symbols.   Python overwrites symbols, so if a module X 
  # defines z=2, and Y looks like:
  # """
  # z=1
  # from X import *
  # log(str(z))
  # """
  # 
  # it will print 2.   I replicate this behavior.
  for symbolname in module_object._context:

    # It is critical to avoid overwriting things like _context, callfunc,
    # and dy_import_module because these are specific to the containing 
    # module
    if symbolname not in SYMBOLS_TO_IGNORE_WHEN_FROM_X_IMPORT:
      module_context[symbolname] = module_object._context[symbolname]


  # That should be all!





# This is a list of modules that are currently being imported.   It is used
# to prevent circular imports from causing an infinite loop (#1379).  
imports_in_progress = []

# Packages the module being imported into a module like object
def dylink_import_module(module, import_context, new_callfunc="import", additional_globals=[]):
  """
  <Purpose>
    Imports modules dynamically into a bundles module like object.   This is
    much like "import" in python, except it actually returns the module
    itself.   Use it like: 
       time = dylink_import_module('time.r2py',callercontext)

  <Arguments>
    module:
      The filename of a module to import. This must include file extensions 
      (thus making "mylib.py" and "mylib.r2py" distinct modules).

    import_context:
      The context of the caller, e.g. the context of who is importing.
      JAC: I believe this is needed to map in the appropriate calls
      like readat, randombytes, etc.

    new_callfunc:
      The value to use for callfunc during the import.
      Defaults to "import".

    additional_globals:
      An array of string globals which will be provided to the imported 
      module. E.g. if the current context defines "foo" and this should 
      be made available in addition to the Stock repy API, this can be 
      provided as ["foo"]

  <Exceptions>
    Raises RepyImportError if the module cannot be found, or if there is 
    a problem initializing a VirtualNamespace around the module. 
    See VirtualNamespace. See dylink_import_global. 

  <Returns>
    A module like object.
  """
  # Need to prevent circular imports from causing an infinite loop (#1379).  
  # To do this, Python associates an empty namespace with any module that is
  # being imported.   We will do the same.
  if module in imports_in_progress:
    return ImportedModule(module, {})

  imports_in_progress.append(module)
  # always clean up this entry from imports_in_progress...
  try:

    # I need to remap the context's items like readat, etc. correctly...
    # The rationale is that a security layer may use a module, like time. 
    # If untrusted code imports time, it should not get the security layer's 
    # call for sendmessage, writeat, etc.
    # I will clear the IMPORTED_MODULE_CACHE upon dispatch

    # We will keep a cache of imported modules so that we only import each
    # module once (see #1320).   This mimics Python's behavior
    if module in IMPORTED_MODULE_CACHE:
      return IMPORTED_MODULE_CACHE[module]

    # Okay, we'll need to load it in.  Construct a new context.   By testing
    # python this is what it seems to do in all cases (even "from X import *")
    new_context = _default_context(import_context, additional_globals)

    # Get the code for the module
    virt = _dy_module_code(module)

    # Set callfunc
    new_context["callfunc"] = new_callfunc

    # Try to evaluate the module.   This is where things like code safety checks
    # and syntax errors will fail.
    try:
      virt.evaluate(new_context)
    except Exception, e:
      debug_str = getlasterror()
      # JAC: BUG?   Not sure why we are not just raising the true error...
      raise Exception("Caught exception while initializing module (" + 
          module + ")! Debug String: " + debug_str)

    # Place the item in the cache so we do not import it more than once (#1320)
    IMPORTED_MODULE_CACHE[module] = ImportedModule(module, new_context)

    return IMPORTED_MODULE_CACHE[module]

  finally:
    # there must always be exactly one or this is an internal error (and
    # merits an exception)
    imports_in_progress.remove(module)


#### Support for recursive modules ####

# This allows modules to recursively evaluate
def dylink_dispatch(eval_context, caller_context):
  """
  <Purpose>
    Allows a module to recursively evaluate another context.
    When the user specifies a chain of modules and programs to
    evaluate, this call steps to the next module.

  <Arguments>
    eval_context:
        The context to pass to the next module that is being evaluated.

    caller_context:
        The context of the caller.

  <Exceptions>
    As with the module being evaluated. An exception will be raised
    if the module to be evaluated cannot be initialized in a VirtualNamespace
    due to safety or syntax problems, or if the module does not exist

  <Side Effects>
    Execution will switch to the next module.

  <Returns>
    True if a recursive evaluation was performed, false otherwise.
  """
  # Check that there is a next module
  if not "callargs" in caller_context or len(caller_context["callargs"]) == 0:
    return False

  # Get the specified module
  module = caller_context["callargs"][0]

  # I need to remap the context's items like readat, etc. correctly...
  # The rationale is that a security layer may use a module, like time.
  # If untrusted code imports time, it should not get the security layer's 
  # call for sendmessage, writeat, etc.
  # A sane way to do this may be to simply clear the IMPORTED_MODULE_CACHE
  # upon dispatch
  IMPORTED_MODULE_CACHE = {}

  # Get the code for the module
  virt = _dy_module_code(module)

  # Store the callfunc
  eval_context["callfunc"] = caller_context["callfunc"]
 
  # If the module's callargs is the same as the callers, shift the args by one
  if "callargs" in eval_context and eval_context["callargs"] is caller_context["callargs"]:
    eval_context["callargs"] = caller_context["callargs"][1:]
  
  # Evaluate recursively
  virt.evaluate(eval_context)

  # Return success
  return True
  

#### Dylink initializers ####

# Defines dylink as a per-context thing, and makes it available
def init_dylink(import_context, child_context):
  """
  <Purpose>
    Initializes dylink to operate in the given namespace/context.

  <Arguments>
    import_context:
      The context to initialize in.
    
    child_context:
      A copy of the import_context that is used for dy_dispatch_module
      to pass to the child namespace.

  <Side Effects>
    dy_* will be defined in the context.
  """

  # Define closures around dy_* functions
  def _dy_import_module(module,new_callfunc="import",additional_globals=[]):
    return dylink_import_module(module,import_context,new_callfunc,additional_globals)

  def _dy_import_global(module,new_callfunc="import"):
    return dylink_import_global(module,import_context,new_callfunc)

  def _dylink_dispatch(eval_context=None):
    # Get the copied context if none is specified
    if eval_context is None:
      eval_context = child_context

    # Call dylink_dispatch with the proper eval context
    return dylink_dispatch(eval_context,import_context)


  # Make these available
  import_context["dy_import_module"] = _dy_import_module
  import_context["dy_import_module_symbols"] = _dy_import_global
  import_context["dy_dispatch_module"] = _dylink_dispatch

  # NOTE: Any context items must be added below or they will overwrite
  # the caller's items!


# It is critical to avoid replacing the caller's version of some symbols,
# such as the below.   These are setup by dylink and should not be remapped
# or else the caller will effective be stuck with some parts of the callee's 
# state.   
# 
# This is placed here because it needs to be updated when the functions
# above and below this change.
SYMBOLS_TO_IGNORE_WHEN_FROM_X_IMPORT = ['CHILD_CONTEXT', '_context', 
    'callfunc', 'dy_dispatch_module', 'dy_import_module', 
    'dy_import_module_symbols', "HAS_DYLINK", 'mycontext']


# Wrap around VirtualNamespace
class DylinkNamespace(object):
  """
  Wraps a normal namespace object to automatically update the context
  so that dylink_* operates correctly.
  """
  # Take any arguments, pass it down
  def __init__(self,*args,**kwargs):
    # Construct the underlying virtual namespace
    self._virt = createvirtualnamespace(*args,**kwargs)

    # Set the last eval context to None
    self._eval_context = None

  # Handle evaluate
  def evaluate(self,context,enable_dylink=True):
    # Convert context to a SafeDict if it isn't one
    if type(context) is dict:
      context = SafeDict(context)
    
    # Explicitly remove dylink_* calls if disabled
    if not enable_dylink:
      calls = ["dy_import_module", "dy_import_module_symbols", "dy_dispatch_module"]
      for call in calls:
        if call in context:
          del context[call]

    # Copy the context if this is the first evaluate of this context
    if enable_dylink and context is not self._eval_context:
      # Copy the context before evaluation
      child_context = context.copy()
      child_context["_context"] = child_context
      child_context["mycontext"] = {}

      # Let the module see this copy
      context["CHILD_CONTEXT"] = child_context

      # Initialize the context to use dylink
      init_dylink(context,child_context)

    # Inform the module if dylink is available
    context["HAS_DYLINK"] = enable_dylink

    # NOTE: Any context items must be added above or they will overwrite
    # the caller's items!

    # Set this as the last evaluated context
    self._eval_context = context

    # Evaluate
    self._virt.evaluate(context)

    # Return the context
    return context
    


class RepyImportError(Exception):
  """
  Define a new error for when we are able to import
  a module properly.
  """
  pass



# Functional wrapper around DylinkNamespace
def get_DylinkNamespace(*args,**kwargs):
  return DylinkNamespace(*args,**kwargs)

#### Call into the next module ####

# Update the child context
CHILD_CONTEXT["createvirtualnamespace"] = get_DylinkNamespace

# Evaluate the next module
dylink_dispatch(CHILD_CONTEXT, _context)


### Automatically generated by repyhelper.py ### /home/pankhuri/projects/TUF+SEATTLE/softwareupdater/RUNNABLE/dylink.r2py
