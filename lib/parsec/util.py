#!/usr/bin/env python

# THIS FILE IS PART OF THE CYLC SUITE ENGINE.
# Copyright (C) 2008-2015 NIWA
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
from copy import copy
from parsec.OrderedDict import OrderedDictWithDefaults

"""
Utility functions for printing and manipulating PARSEC NESTED DICTS.
The copy and override functions below assume values are either dicts
(nesting) or shallow collections of simple types.
"""

def listjoin( lst, none_str='' ):
    if not lst:
        # empty list
        return none_str
    else:
        # return string from joined list, but quote all elements if any
        # of them contain comment or list-delimiter characters
        # (currently quoting must be consistent across all elements)
        nlst = []
        quote_me = False
        for item in lst:
            if isinstance( item, str ) and ( '#' in item or ',' in item ):
                quote_me = True
                break
        if quote_me:
            # TODO - this assumes no internal double-quotes
            return ', '.join( [ '"' + str(item) + '"' for item in lst ] )
        else:
            return ', '.join( [ str(item) for item in lst ] )

def printcfg(cfg, level=0, indent=0, prefix='', none_str='', handle=sys.stdout):
    """
    Recursively pretty-print a parsec config item or section (nested
    dict), as returned by parse.config.get().
    """
    spacer = '   '*indent
    if isinstance(cfg, list):
        # cfg is a single list value
        handle.write("%s%s%s\n" % (prefix, spacer, listjoin(cfg, none_str)))
    elif not isinstance(cfg,dict):
        # cfg is a single value
        if not cfg:
            cfg = none_str
        handle.write("%s%s%s\n" % (prefix, spacer, str(cfg)))
    else:
        # cfg is a possibly-nested section
        delayed=[]
        for key,val in cfg.items():
            if isinstance( val, dict ):
                # nested (val is a section)
                # delay output to print top level items before recursing
                delayed.append((key,val))
            else:
                # val is a single value
                if isinstance( val, list ):
                    v = listjoin( val, none_str )
                elif val is None:
                    v = none_str
                else:
                    v = str(val)
                # print "key = val"
                handle.write("%s%s%s = %s\n" % (prefix, spacer, str(key), v))

        for key,val in delayed:
            # print heading
            #if val != None:
            handle.write("%s%s%s%s%s\n" % (prefix, spacer, '['*(level+1), str(key), ']'*(level+1)))
            # recurse into section
            printcfg(val, level+1, indent+1, prefix, none_str, handle)

def replicate( target, source ):
    """
    Replicate source *into* target. Source elements need not exist in
    target already, so source overrides common elements in target and
    otherwise adds elements to it.
    """
    if not source:
        target = OrderedDictWithDefaults()
        return
    if hasattr(source, "defaults_"):
        target.defaults_ = pdeepcopy(source.defaults_)
    for key,val in source.items():
        if isinstance( val, dict ):
            if key not in target:
                target[key] = OrderedDictWithDefaults()
            if hasattr(val, 'defaults_'):
                target[key].defaults_ = pdeepcopy(val.defaults_)
            replicate( target[key], val )
        elif isinstance( val, list ):
            target[key] = val[:]
        else:
            target[key] = val

def pdeepcopy(source):
    """Make a deep copy of a pdict source"""
    target = OrderedDictWithDefaults()
    replicate( target, source )
    return target

def poverride( target, sparse ):
    """Override items in a target pdict, target sub-dicts must already exist."""
    if not sparse:
        target = OrderedDictWithDefaults()
        return
    for key,val in sparse.items():
        if isinstance( val, dict ):
            poverride( target[key], val )
        elif isinstance( val, list ):
            target[key] = val[:]
        else:
            target[key] = val

def m_override( target, sparse ):
    """Override items in a target pdict. Target keys must already exist
    unless there is a "__MANY__" placeholder in the right position."""
    if not sparse:
        target = OrderedDictWithDefaults()
        return
    stack = [(sparse, target, [], OrderedDictWithDefaults())]
    defaults_list = []
    while stack:
        source, dest, keylist, many_defaults = stack.pop(0)
        if many_defaults:
            defaults_list.append((dest, many_defaults))
        for key, val in source.items():
            if isinstance( val, dict ):
                if key in many_defaults:
                    child_many_defaults = many_defaults[key]
                else:
                    child_many_defaults = OrderedDictWithDefaults()
                if key not in dest:
                    if '__MANY__' in dest:
                        dest[key] = OrderedDictWithDefaults()
                        child_many_defaults = dest['__MANY__']
                    elif '__MANY__' in many_defaults:
                        # A 'sub-many' dict - would it ever exist in real life?
                        dest[key] = OrderedDictWithDefaults()
                        child_many_defaults = many_defaults['__MANY__']
                    elif key in many_defaults:
                        dest[key] = OrderedDictWithDefaults()
                    else:
                        # TODO - validation prevents this, but handle properly for completeness.
                        raise Exception(
                            "parsec dict override: no __MANY__ placeholder" +
                            "%s" % (keylist + [key])
                        )
                stack.append((val, dest[key], keylist + [key], child_many_defaults))
            else:
                if key not in dest:
                    if '__MANY__' in dest or key in many_defaults or '__MANY__' in many_defaults:
                        if isinstance( val, list ):
                            dest[key] = val[:]
                        else:
                            dest[key] = val

                    else:
                        # TODO - validation prevents this, but handle properly for completeness.
                        raise Exception(
                            "parsec dict override: no __MANY__ placeholder" +
                            "%s" % (keylist + [key])
                        )
                if isinstance( val, list ):
                    dest[key] = val[:]
                else:
                    dest[key] = val
    for dest_dict, defaults in defaults_list:
        dest_dict.defaults_ = defaults


def un_many( cfig ):
    """Remove any '__MANY__' items from a nested dict, in-place."""
    if not cfig:
        return
    for key,val in cfig.items():
        if key == '__MANY__':
            try:
                del cfig[key]
            except KeyError:
                if hasattr(cfig, 'defaults_') and key in cfig.defaults_:
                    del cfig.defaults_[key]
                else:
                    raise
        elif isinstance( val, dict ):
            un_many( cfig[key] )


def itemstr( parents=[], item=None, value=None ):
    """
    Pretty-print an item from list of sections, item name, and value
    E.g.: ([sec1, sec2], item, value) to '[sec1][sec2]item = value'.
    """
    keys = copy(parents)
    if keys and value and not item:
        # last parent is the item
        item = keys[-1]
        keys.remove(item)
    if parents:
        s = '[' + ']['.join(parents) + ']'
    else:
        s = ''
    if item:
        s += str(item)
        if value:
            s += " = " + str(value)
    if not s:
        s = str(value)

    return s


if __name__ == "__main__":
    print 'Item strings:'
    print '  ', itemstr( ['sec1','sec2'], 'item', 'value' )
    print '  ', itemstr( ['sec1','sec2'], 'item' )
    print '  ', itemstr( ['sec1','sec2'] )
    print '  ', itemstr( ['sec1'] )
    print '  ', itemstr( item='item', value='value' )
    print '  ', itemstr( item='item' )
    print '  ', itemstr( value='value' )
    print '  ', itemstr( parents=['sec1','sec2'], value='value' ) # error or useful?

    print 'Configs:'
    printcfg( 'foo', prefix=' > ' )
    printcfg( ['foo','bar'], prefix=' > ' )
    printcfg( {}, prefix=' > ' )
    printcfg( { 'foo' : 1 }, prefix=' > ' )
    printcfg( { 'foo' : None }, prefix=' > ' )
    printcfg( { 'foo' : None }, none_str='(none)', prefix=' > ' )
    printcfg( { 'foo' : { 'bar' : 1 } }, prefix=' > ' )
    printcfg( { 'foo' : { 'bar' : None } }, prefix=' > ' )
    printcfg( { 'foo' : { 'bar' : None } }, none_str='(none)', prefix=' > ' )
    printcfg( { 'foo' : { 'bar' : 1, 'baz' : 2, 'qux' : { 'boo' : None} } }, none_str='(none)', prefix=' > ' )
