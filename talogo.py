# -*- coding: utf-8 -*-
#Copyright (c) 2007-8, Playful Invention Company.
#Copyright (c) 2008-10, Walter Bender
#Copyright (c) 2008-10, Raúl Gutiérrez Segalés

#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import gtk
import gobject
from time import clock
from math import sqrt
from random import uniform
from operator import isNumberType
import audioop
import subprocess
from UserDict import UserDict
try:
    from sugar.datastore import datastore
except:
    pass

from constants import *
from tagplay import play_audio, play_movie_from_file, stop_media
from tajail import myfunc, myfunc_import
from tautils import get_pixbuf_from_journal, movie_media_type,\
                    audio_media_type, round_int
from gettext import gettext as _

procstop = False

class noKeyError(UserDict):
    __missing__=lambda x,y: 0

class symbol:
    def __init__(self, name):
        self.name = name
        self.nargs = None
        self.fcn = None

    def __str__(self):
        return self.name
    def __repr__(self):
        return '#'+self.name

class logoerror(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

"""
Utility functions
"""

def careful_divide(x,y):
    try:
        if y==0:
            return 0
        return x/y
    except:
        return 0

def taequal(x,y):
    try:
        return float(x)==float(y)
    except:
        if type(x) == str or type(x) == unicode:
            xx = ord(x[0])
        else:
            xx = x
        if type(y) == str or type(y) == unicode:
            yy = ord(y[0])
        else:
            yy = y
        return xx==yy
    
def taless(x, y):
    try:
        return float(x)<float(y)
    except:
        if type(x) == str or type(x) == unicode:
            xx = ord(x[0])
        else:
            xx = x
        if type(y) == str or type(y) == unicode:
            yy = ord(y[0])
        else:
            yy = y
        return xx<yy
    
def tamore(x, y):
    return taless(y, x)

def taplus(x, y):
    if (type(x) == int or type(x) == float) and \
        (type(y) == int or type(y) == float):
        return(x+y)
    else:
        return(str(x) + str(y))
    
def taminus(x, y):
    try:
        return(x-y)
    except:
        raise logoerror("#syntaxerror")
    
def taproduct(x, y):
    try:
        return(x*y)
    except:
        raise logoerror("#syntaxerror")
    
def tamod(x, y):
    try:
        return(x%y)
    except:
        raise logoerror("#syntaxerror")
    
def tasqrt(x):
    try:
        return sqrt(x)
    except:
        raise logoerror("#syntaxerror")
    
def identity(x):
    return(x)

def start_stack(tw):
    if tw.running_sugar:
        tw.activity.recenter()

def calc_position(tw, t):
    w,h,x,y,dx,dy = TEMPLATES[t]
    x *= tw.canvas.width
    y *= tw.canvas.height
    w *= (tw.canvas.width-x)
    h *= (tw.canvas.height-y)
    dx *= w
    dy *= h
    return(w,h,x,y,dx,dy)
    
def stop_logo(tw):
    tw.step_time = 0
    tw.lc.step = just_stop()
    
def just_stop():
    yield False

def millis():
    return int(clock()*1000)

"""
A class for parsing Logo Code
"""
class LogoCode:
    def __init__(self, tw):

        self.tw = tw
        self.oblist = {}

        DEFPRIM = {
        '(':[1, lambda self, x: self.prim_opar(x)],
        '/':[None, lambda self,x,y: careful_divide(x,y)],
        '-':[None, lambda self,x,y: x-y],
        '*':[None, lambda self,x,y: x*y],
        '%':[None, lambda self,x,y: x%y],
        '+':[None, lambda self,x,y: x+y],
        'and':[2, lambda self,x,y: x&y],
        'arc':[2, lambda self, x, y: self.tw.canvas.arc(x, y)],
        'back':[1, lambda self,x: self.tw.canvas.forward(-x)],
        'blue':[0, lambda self: 70],
        'bpos':[0, lambda self: -self.tw.canvas.height/(self.tw.coord_scale*2)],
        'box1':[0, lambda self: self.boxes['box1']],
        'box':[1, lambda self,x: self.box(x)],
        'box2':[0, lambda self: self.boxes['box2']],
        'bullet':[2, self.prim_bullet, True],
        'clean':[0, lambda self: self.clear()],
        'color':[0, lambda self: self.tw.canvas.color],
        'container':[1, lambda self,x: x],
        'cyan':[0, lambda self: 50],
        'define':[2, self.prim_define],
        'division':[2, lambda self,x,y: careful_divide(x,y)],
        'emptyheap':[0, lambda self: self.empty_heap()],
        'equal?':[2, lambda self,x,y: taequal(x,y)],
        'fillscreen':[2, lambda self, x, y: self.tw.canvas.fillscreen(x, y)],
        'forever':[1, self.prim_forever, True],
        'forward':[1, lambda self, x: self.tw.canvas.forward(x)],
        'greater?':[2, lambda self,x,y: tamore(x,y)],
        'green':[0, lambda self: 30],
        'heading':[0, lambda self: self.tw.canvas.heading],
        'heap':[0, lambda self: self.heap_print()],
        'hideblocks':[0, lambda self: self.tw.hideblocks()],
        'hres':[0, lambda self: self.tw.canvas.width/self.tw.coord_scale],
        'id':[1, lambda self,x: identity(x)],
        'if':[2, self.prim_if, True],
        'ifelse':[3, self.prim_ifelse, True],
        'insertimage':[1, lambda self,x: self.insert_image(x, False)],
        'kbinput':[0, lambda self: self.kbinput()],
        'keyboard':[0, lambda self: self.keyboard],
        'left':[1, lambda self,x: self.tw.canvas.right(-x)],
        'lpos':[0, lambda self: -self.tw.canvas.width/(self.tw.coord_scale*2)],
        'less?':[2, lambda self,x,y: taless(x,y)],
        'minus':[2, lambda self,x,y: taminus(x,y)],
        'mod':[2, lambda self,x,y: tamod(x,y)],
        'myfunc':[2, lambda self,f,x: self.callmyfunc(f, x)],
        'nop':[0, lambda self: None],
        'nop1':[0, lambda self: None],
        'nop2':[0, lambda self: None],
        'nop3':[1, lambda self,x: None],
        'not':[1, lambda self,x:not x],
        'orange':[0, lambda self: 10],
        'or':[2, lambda self,x,y: x|y],
        'pendown':[0, lambda self: self.tw.canvas.setpen(True)],
        'pensize':[0, lambda self: self.tw.canvas.pensize],
        'penup':[0, lambda self: self.tw.canvas.setpen(False)],
        'plus':[2, lambda self,x,y: taplus(x,y)],
        'pop':[0, lambda self: self.pop_heap()],
        'print':[1, lambda self,x: self.status_print(x)],
        'product':[2, lambda self,x,y: taproduct(x,y)],
        'purple':[0, lambda self: 90],
        'push':[1, lambda self,x: self.push_heap(x)],
        'random':[2, lambda self,x,y: int(uniform(x,y))],
        'red':[0, lambda self: 0],
        'repeat':[2, self.prim_repeat, True],
        'right':[1, lambda self, x: self.tw.canvas.right(x)],
        'rpos':[0, lambda self: self.tw.canvas.width/(self.tw.coord_scale*2)],
        'scale':[0, lambda self: self.scale],
        'setcolor':[1, lambda self, x: self.tw.canvas.setcolor(x)],
        'seth':[1, lambda self, x: self.tw.canvas.seth(x)],
        'setpensize':[1, lambda self, x: self.tw.canvas.setpensize(x)],
        'setscale':[1, lambda self,x: self.set_scale(x)],
        'setshade':[1, lambda self, x: self.tw.canvas.setshade(x)],
        'settextcolor':[1, lambda self, x: self.tw.canvas.settextcolor(x)],
        'settextsize':[1, lambda self, x: self.tw.canvas.settextsize(x)],
        'setxy':[2, lambda self, x, y: self.tw.canvas.setxy(x, y)],
        'shade':[0, lambda self: self.tw.canvas.shade],
        'show':[1,lambda self, x: self.show(x, True)],
        'showblocks':[0, lambda self: self.tw.showblocks()],
        'sound':[1, lambda self,x: self.play_sound(x)],
        'sqrt':[1, lambda self,x: sqrt(x)],
        'stack1':[0, self.prim_stack1, True],
        'stack':[1, self.prim_stack, True],
        'stack2':[0, self.prim_stack2, True],
        'start':[0, lambda self: start_stack(self.tw)],
        'stopstack':[0, self.prim_stopstack],
        'storeinbox1':[1, lambda self,x: self.setbox('box1',x)],
        'storeinbox2':[1, lambda self,x: self.setbox('box2',x)],
        'storeinbox':[2, lambda self,x,y: self.setbox('box3'+str(x),y)],
        't1x1':[2, lambda self,x,y: self.show_template1x1(x, y)],
        't1x1a':[2, lambda self,x,y: self.show_template1x1a(x, y)],
        't1x2':[3, lambda self,x,y,z: self.show_template1x2(x, y, z)],
        't2x1':[3, lambda self,x,y,z: self.show_template2x1(x, y, z)],
        't2x2':[5, lambda self,x,y,z,a,b: self.show_template2x2(x, y, z, a, b)],
        'textcolor':[0, lambda self: self.tw.canvas.textcolor],
        'textsize':[0, lambda self: self.tw.textsize],
        'tpos':[0, lambda self: self.tw.canvas.height/(self.tw.coord_scale*2)],
        'turtle':[1, lambda self, x: self.tw.canvas.set_turtle(int(x-1))],
        'userdefined':[1, lambda self,x: self.loadmyblock(x)],
        'video':[1, lambda self,x: self.play_movie(x)],
        'vres':[0, lambda self: self.tw.canvas.height/self.tw.coord_scale],
        'wait':[1, self.prim_wait, True],
        'write':[2, lambda self, x,y: self.write(self, x,y)],
        'xcor':[0, lambda self: self.tw.canvas.xcor/self.tw.coord_scale],
        'ycor':[0, lambda self: self.tw.canvas.ycor/self.tw.coord_scale],
        'yellow':[0, lambda self: 20]}

        for p in iter(DEFPRIM):
            if len(DEFPRIM[p]) == 2:
                self.defprim(p, DEFPRIM[p][0], DEFPRIM[p][1])
            else:
                self.defprim(p, DEFPRIM[p][0], DEFPRIM[p][1], DEFPRIM[p][2])
    
        self.symtype = type(self.intern('print'))
        self.listtype = type([])
        self.symnothing = self.intern('%nothing%')
        self.symopar = self.intern('(')
        self.iline = None
        self.cfun = None
        self.arglist = None
        self.ufun = None
    
        self.istack = []
        self.stacks = {}
        self.boxes = {'box1': 0, 'box2': 0}
        self.heap = []

        self.keyboard = 0
        self.trace = 0
        self.gplay = None
        self.ag = None
        self.nobox = ""
        self.title_height = int((self.tw.canvas.height/20)*self.tw.scale)
        self.body_height = int((self.tw.canvas.height/40)*self.tw.scale)
        self.bullet_height = int((self.tw.canvas.height/30)*self.tw.scale)
    
        self.scale = 33

    """
    Given a block to run...
    """
    def run_blocks(self, blk, blocks, run_flag):
        for k in self.stacks.keys():
            self.stacks[k] = None
        self.stacks['stack1'] = None
        self.stacks['stack2'] = None
        for b in blocks:
            if b.name == 'hat1':
                self.stacks['stack1'] = self.readline(self.blocks_to_code(b))
            if b.name=='hat2':
                self.stacks['stack2'] = self.readline(self.blocks_to_code(b))
            if b.name == 'hat':
                if b.connections[1] is not None:
                    self.stacks['stack3'+b.connections[1].values[0]] =\
                        self.readline(self.blocks_to_code(b))
        code = self.blocks_to_code(blk)
        if run_flag is True:
            print "running code: %s" % (code)
            self.setup_cmd(code)
        else:
            return code

    """
    Convert a stack of blocks to pseudocode.
    """
    def blocks_to_code(self, blk):
        if blk is None:
            return ['%nothing%']
        code = []
        dock = blk.docks[0]
        if len(dock)>4:
            code.append(dock[4]) # There could be a '(' or '['.
        if blk.primitive is not None:
            code.append(blk.primitive)
        elif len(blk.values)>0:  # Extract the value from content blocks.
            if blk.name=='number':
                try:
                    code.append(float(blk.values[0]))
                except ValueError:
                    code.append(float(ord(blk.values[0][0])))
            elif blk.name=='string' or blk.name=='title':
                if type(blk.values[0]) == float or type(blk.values[0]) == int:
                    if int(blk.values[0]) == blk.values[0]:
                        blk.values[0] = int(blk.values[0])
                    code.append('#s'+str(blk.values[0]))
                else:
                    code.append('#s'+blk.values[0])
            elif blk.name=='journal':
                if blk.values[0] is not None:
                    code.append('#smedia_'+str(blk.values[0]))
                else:
                    code.append('#smedia_None')
            elif blk.name=='description':
                if blk.values[0] is not None:
                    code.append('#sdescr_'+str(blk.values[0]))
                else:
                    code.append('#sdescr_None')
            elif blk.name=='audio':
                if blk.values[0] is not None:
                    code.append('#saudio_'+str(blk.values[0]))
                else:
                    code.append('#saudio_None')
            else:
                print "%s had no primitive." % (blk.name)
                return ['%nothing%']
        else:
            print "%s had no value." % (blk.name)
            return ['%nothing%']
        for i in range(1, len(blk.connections)):
            b = blk.connections[i]        
            dock = blk.docks[i]
            if len(dock)>4:
                for c in dock[4]:
                    code.append(c)
            if b is not None:
                code.extend(self.blocks_to_code(b))
            elif blk.docks[i][0] not in ['flow', 'unavailable']:
                code.append('%nothing%')
        return code
    
    """
    Execute the psuedocode.
    """
    def setup_cmd(self, str):
        self.tw.active_turtle.hide() # Hide the turtle while we are running.
        self.procstop = False
        list = self.readline(str)
        # print list
        self.step = self.start_eval(list)

    """
    Convert the pseudocode into a list of commands.
    """
    def readline(self, line):
        res = []
        while line:
            token = line.pop(0)
            if isNumberType(token):
                res.append(token)
            elif token.isdigit():
                res.append(float(token))
            elif token[0]=='-' and token[1:].isdigit():
                res.append(-float(token[1:]))
            elif token[0] == '"':
                res.append(token[1:])
            elif token[0:2] == "#s":
                res.append(token[2:])
            elif token == '[':
                res.append(self.readline(line))
            elif token == ']':
                return res
            else:
                res.append(self.intern(token))
        return res

    """
    Add the object to the object list.
    """
    def intern(self, str):
        if str in self.oblist:
            return self.oblist[str]
        sym = symbol(str)
        self.oblist[str] = sym
        return sym
    
    """
    Step through the list.
    """
    def start_eval(self, list):
        self.icall(self.evline, list)
        yield True
        if self.tw.running_sugar:
            self.tw.activity.stop_button.set_icon("stopitoff")
        yield False

    """
    Add a function to the program stack.
    """
    def icall(self, fcn, *args):
        self.istack.append(self.step)
        self.step = fcn(*(args))

    """
    Evaluate a line of code from the list.
    """
    def evline(self, list):
        oldiline = self.iline
        self.iline = list[:]
        self.arglist = None
        # print "evline: %s" % (self.iline)
        while self.iline:
            if self.tw.step_time > 0: # show the turtle during idle time
                self.tw.active_turtle.show()
                endtime = millis()+self.an_int(self.tw.step_time)*100
                while millis()<endtime:
                    yield True
                self.tw.active_turtle.hide()
            token = self.iline[0]
            if token == self.symopar:
                token = self.iline[1]
            self.icall(self.eval)
            yield True
            if self.procstop:
                break
            if self.iresult == None:
                continue
            raise logoerror(str(self.iresult))
        self.iline = oldiline
        self.ireturn()
        self.tw.display_coordinates()
        yield True
    
    """
    Evaluate the next token on the line.
    """
    def eval(self, infixarg=False):
        token = self.iline.pop(0)
        # print "eval: %s" % (str(token))
        if type(token) == self.symtype:
            self.icall(self.evalsym, token)
            yield True
            res = self.iresult
        else:
            res = token
        if not infixarg:
            while self.infixnext():
                self.icall(self.evalinfix, res)
                yield True
                res = self.iresult
        self.ireturn(res)
        yield True

    """
    Process symbols.
    """
    def evalsym(self, token):
        self.debug_trace(token)
        self.undefined_check(token)
        oldcfun, oldarglist = self.cfun, self.arglist
        self.cfun, self.arglist = token, []
        # print "   evalsym: %s %s" % (str(self.cfun), str(self.arglist))
        if token.nargs == None:
            raise logoerror("#noinput")
        for i in range(token.nargs):
            self.no_args_check()
            self.icall(self.eval)
            yield True
            self.arglist.append(self.iresult)
        if self.cfun.rprim:
            if type(self.cfun.fcn) == self.listtype:
                self.icall(self.ufuncall, self.cfun.fcn)
                yield True
            else:
                self.icall(self.cfun.fcn, *self.arglist)
                yield True
            result = None
        else:
            # TODO: find out why stopstack args are mismatched
            if token.name == 'stopstack':
                print "%s: %d" % (token.name, len(self.arglist))
                result = self.cfun.fcn()
            else:
                result = self.cfun.fcn(self, *self.arglist)
        self.cfun, self.arglist = oldcfun, oldarglist
        if self.arglist is not None and result == None:
            raise logoerror("%s didn't output to %s (arglist %s, result %s)" % \
                (oldcfun.name, self.cfun.name, str(self.arglist), str(result)))
        self.ireturn(result)
        yield True

    def evalinfix(self, firstarg):
        token = self.iline.pop(0)
        oldcfun, oldarglist = self.cfun, self.arglist
        self.cfun, self.arglist = token, [firstarg]
        no_args_check(self)
        self.icall(self.eval, True); yield True
        self.arglist.append(self.iresult)
        result = self.cfun.fcn(self, *self.arglist)
        self.cfun, self.arglist = oldcfun, oldarglist
        self.ireturn(result)
        yield True
    
    def infixnext(self):
        if len(self.iline)==0:
            return False
        if type(self.iline[0]) is not self.symtype:
            return False
        return self.iline[0].name in ['+', '-', '*', '/','%','and','or']

    def ufuncall(self, body):
        ijmp(self.evline, body)
        yield True
    
    def doevalstep(self):
        starttime = millis()
        try:
            while (millis()-starttime)<120:
                try:
                    if self.step is not None:
                        self.step.next()
                    else: # TODO: where is doevalstep getting called with None?
                        print "step is None"
                        return False
                except StopIteration:
                    self.tw.active_turtle.show()
                    return False
        except logoerror, e:
            self.showlabel(str(e)[1:-1])
            self.tw.active_turtle.show()
            return False
        return True

    def ireturn(self, res=None):
        self.step = self.istack.pop()
        self.iresult = res

    def ijmp(self, fcn, *args):
        self.step = fcn(*(args))

    def debug_trace(self, token):
        if self.trace:
            if token.name in PALETTES[PALETTE_NAMES.index('turtle')]:
                my_string = "%s\n%s=%d\n%s=%d\n%s=%d\n%s=%d" %\
                    (token.name, _('xcor'), int(self.tw.canvas.xcor),
                     _('ycor'), int(self.tw.canvas.ycor), _('heading'),
                     int(self.tw.canvas.heading), _('scale'), int(self.scale))
            elif token.name in PALETTES[PALETTE_NAMES.index('pen')]:
                if self.tw.canvas.pendown:
                    penstatus = _('pen down')
                else:
                    penstatus = _('pen up')
                my_string = "%s\n%s\n%s=%d\n%s=%d\n%s=%.1f" %\
                    (token.name, penstatus, _('color'),
                     int(self.tw.canvas.color), _('shade'),
                     int(self.tw.canvas.shade), _('pen size'),
                     self.tw.canvas.pensize)
            else:
                my_string = "%s\n%s:\n" % (token.name, _('box'))
                for k, v in self.boxes.iteritems():
                    tmp = k +":" + str(v) + "\n"
                    my_string += tmp
            shp = 'info'
            self.tw.status_spr.set_shape(self.tw.status_shapes[shp])
            self.tw.status_spr.set_label(_(my_string))
            self.tw.status_spr.set_layer(STATUS_LAYER)
        return
    
    def undefined_check(self, token):
        if token.fcn is not None:
            return False
        raise logoerror("%s %s" % (_("I don't know how to"), token.name))
    
    def no_args_check(self):
        if self.iline and self.iline[0] is not self.symnothing:
            return
        raise logoerror("#noinput")
    
    def prim_wait(self, time):
        self.tw.active_turtle.show()
        endtime = millis()+self.an_int(time*1000)
        while millis()<endtime:
            yield True
        self.tw.active_turtle.hide()
        self.ireturn()
        yield True
    
    def prim_repeat(self, num, list):
        num = self.an_int(num)
        for i in range(num):
            self.icall(self.evline, list[:])
            yield True
            if self.procstop:
                break
        self.ireturn()
        yield True

    def prim_bullet(self, title, list):
        self.show_bullets(title, list)
        self.ireturn()
        yield True

    def prim_forever(self, list):
        while True:
            self.icall(self.evline, list[:])
            yield True
            if self.procstop:
                break
        self.ireturn()
        yield True

    def prim_if(self, bool, list):
        if bool:
            self.icall(self.evline, list[:])
            yield True
        self.ireturn()
        yield True

    def prim_ifelse(self, bool, list1, list2):
        if bool:
            self.ijmp(self.evline, list1[:])
            yield True
        else:
            self.ijmp(self.evline, list2[:])
            yield True

    def prim_opar(self, val):
        self.iline.pop(0)
        return val

    def prim_define(self, name, body):
        if type(name) is not symtype:
            name = self.intern(name)
        name.nargs, name.fcn = 0, body
        name.rprim = True
    
    def prim_stack(self, str):
        if (not self.stacks.has_key('stack3'+str)) or\
           self.stacks['stack3'+str] is None:
            raise logoerror("#nostack")
        self.icall(self.evline, self.stacks['stack3'+str][:])
        yield True
        self.procstop = False
        self.ireturn()
        yield True

    def prim_stack1(self):
        if self.stacks['stack1'] is None:
            raise logoerror("#nostack")
        self.icall(self.evline, self.stacks['stack1'][:])
        yield True
        self.procstop = False
        self.ireturn()
        yield True
    
    def prim_stack2(self):
        if self.stacks['stack2'] is None:
            raise logoerror("#nostack")
        self.icall(self.evline, self.stacks['stack2'][:])
        yield True
        self.procstop = False
        self.ireturn()
        yield True

    def prim_stopstack(self):
        self.procstop = True
    
    def heap_print(self):
        self.showlabel(self.heap)

    def an_int(self, n):
        if type(n) == int:
            return n
        elif type(n) == float:
            return int(n)
        elif type(n) == str:
            return int(ord(n[0]))
        else:
            raise logoerror("%s doesn't like %s as input" \
                % (self.cfun.name, str(n)))

    def defprim(self, name, args, fcn, rprim=False):
        sym = self.intern(name)
        sym.nargs, sym.fcn = args, fcn
        sym.rprim = rprim    

    def box(self, x):
        try:
            return self.boxes['box3'+str(x)]
        except:
            self.nobox = str(x)
            raise logoerror("#emptybox")
    
    def loadmyblock(self, x):
        # Execute code imported from the Journal
        if self.tw.myblock is not None:
            y = myfunc_import(self, self.tw.myblock, x)
        else:
            raise logoerror("#nocode")
        return
    
    def callmyfunc(self, f, x):
        y = myfunc(self, f, x)
        if y == None:
            raise logoerror("#syntaxerror")
            stop_logo(self.tw)
        else:
            return y
    
    def status_print(self, n):
        if type(n) == str or type(n) == unicode:
            # show title for Journal entries
            if n[0:6] == 'media_':
                try:
                    dsobject = datastore.get(n[6:])
                    self.showlabel(dsobject.metadata['title'])
                    dsobject.destroy()
                except:
                    self.showlabel(n)
            else:
                self.showlabel(n)
        elif type(n) == int:
            self.showlabel(n)
        else:
            self.showlabel(round_int(n))
    
    def kbinput(self):
        if len(self.tw.keypress) == 1:
            self.keyboard = ord(self.tw.keypress[0])
        else:
            try:
                self.keyboard = {'Escape': 27, 'space': 32, ' ': 32,
                                 'Return': 13, \
                                 'KP_Up': 2, 'KP_Down': 4, 'KP_Left': 1, \
                                 'KP_Right': 3,}[self.tw.keypress]
            except:
                self.keyboard = 0
        self.tw.keypress = ""
    
    def showlabel(self, label):
        if label=='#nostack':
            shp = 'nostack'
            label=''
        elif label=='#noinput':
            shp = 'noinput'
            label=''
        elif label=='#emptyheap':
            shp = 'emptyheap'
            label=''
        elif label=='#emptybox':
            shp = 'emptybox'
            label='                    '+self.nobox
        elif label=='#nomedia':
            shp = 'nomedia'
            label=''
        elif label=='#nocode':
            shp = 'nocode'
            label=''
        elif label=='#syntaxerror':
            shp = 'syntaxerror'
            label=''
        elif label=='#overflowerror':
            shp = 'overflowerror'
            label=''
        elif label=='#notanumber':
            shp = 'overflowerror'
            label=''
        else:
            shp = 'status'
        self.tw.status_spr.set_shape(self.tw.status_shapes[shp])
        self.tw.status_spr.set_label(label)
        self.tw.status_spr.set_layer(STATUS_LAYER)

    def setbox(self, name,val):
        self.boxes[name]=val
    
    def push_heap(self, val):
        self.heap.append(val)

    def pop_heap(self):
        try:
            return self.heap.pop(-1)
        except:
            raise logoerror ("#emptyheap")

    def empty_heap(self):
        self.heap = []

    """
    Everything below is related to multimedia commands
    """

    def show_picture(self, media, x, y, w, h):
        if media == "" or media[6:] == "":
            pass
        elif media[6:] is not "None":
            pixbuf = None
            if self.tw.running_sugar:
                try:
                    dsobject = datastore.get(media[6:])
                except:
                    print "Couldn't open Journal object %s" % (media[6:])
                if movie_media_type(dsobject.file_path[-4:]):
                    play_movie_from_file(self,
                        dsobject.file_path, int(x), int(y), int(w), int(h))
                else:
                    pixbuf = get_pixbuf_from_journal(dsobject, int(w), int(h))
                dsobject.destroy()
            else:
                try:
                    if movie_media_type(media[-4:]):
                        play_movie_from_file(self, media[6:], int(x), int(y),
                                                              int(w), int(h))
                    else:
                        pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(
                                     media[6:], int(w), int(h))
                except:
                    print "Couldn't open media object %s" % (media[6:])
            if pixbuf is not None:
                self.tw.canvas.draw_pixbuf(pixbuf, 0, 0, int(x), int(y),
                                                         int(w), int(h))

    def show_description(self, media, x, y, w, h):
        if media == "" or media[6:] == "":
            pass
        elif media[6:] is not "None":
            text = None
            if self.tw.running_sugar:
                try:
                    dsobject = datastore.get(media[6:])
                    text = str(dsobject.metadata['description'])
                    dsobject.destroy()
                except:
                    print "no description in %s" % (media[6:])
            else:
                try:
                    f = open(media[6:], 'r')
                    text = f.read()
                    f.close()
                except:
                    print "no text in %s?" % (media[6:])
            if text is not None:
                print "text: %s" % (text)
                self.tw.canvas.draw_text(text, int(x), int(y),
                                         self.body_height, int(w))
    
    def draw_title(self, title, x, y):
        self.tw.canvas.draw_text(title,int(x),int(y),self.title_height,
                                                     self.tw.canvas.width-x)

    # title, one image, and description
    def show_template1x1(self, title, media):
        w,h,xo,yo,dx,dy = calc_position(self.tw, 't1x1')
        x = -(self.tw.canvas.width/2)+xo
        y = self.tw.canvas.height/2
        self.tw.canvas.setxy(x, y)
        # save the text size so we can restore it later
        save_text_size = self.tw.textsize
        # set title text
        self.tw.canvas.settextsize(self.title_height)
        self.show(title)
        # calculate and set scale for media blocks
        myscale = 45 * (self.tw.canvas.height - self.title_height*2) \
                      / self.tw.canvas.height
        self.set_scale(myscale)
        # set body text size
        self.tw.canvas.settextsize(self.body_height)
        # render media object
        # leave some space below the title
        y -= int(self.title_height*2*self.tw.lead)
        self.tw.canvas.setxy(x, y)
        self.show(media)
        if self.tw.running_sugar:
            x = 0
            self.tw.canvas.setxy(x, y)
            self.show(media.replace("media_","descr_"))
        # restore text size
        self.tw.canvas.settextsize(save_text_size)
    
    # title, two images (horizontal), two descriptions
    def show_template2x1(self, title, media1, media2):
        w,h,xo,yo,dx,dy = calc_position(self.tw, 't2x1')
        x = -(self.tw.canvas.width/2)+xo
        y = self.tw.canvas.height/2
        self.tw.canvas.setxy(x, y)
        # save the text size so we can restore it later
        save_text_size = self.tw.textsize
        # set title text
        self.tw.canvas.settextsize(self.title_height)
        self.show(title)
        # calculate and set scale for media blocks
        myscale = 45 * (self.tw.canvas.height - self.title_height*2)/\
                  self.tw.canvas.height
        self.set_scale(myscale)
        # set body text size
        self.tw.canvas.settextsize(self.body_height)
        # render four quadrents
        # leave some space below the title
        y -= int(self.title_height*2*self.tw.lead)
        self.tw.canvas.setxy(x, y)
        self.show(media1)
        x = 0
        self.tw.canvas.setxy(x, y)
        self.show(media2)
        y = -self.title_height
        if self.tw.running_sugar:
            self.tw.canvas.setxy(x, y)
            self.show(media2.replace("media_","descr_"))
            x = -(self.tw.canvas.width/2)+xo
            self.tw.canvas.setxy(x, y)
            self.show(media1.replace("media_","descr_"))
        # restore text size
        self.tw.canvas.settextsize(save_text_size)

    # title and varible number of  bullets
    def show_bullets(self, title, sarray):
        w,h,xo,yo,dx,dy = calc_position(self.tw, 'bullet')
        x = -(self.tw.canvas.width/2)+xo
        y = self.tw.canvas.height/2
        self.tw.canvas.setxy(x, y)
        # save the text size so we can restore it later
        save_text_size = self.tw.textsize
        # set title text
        self.tw.canvas.settextsize(self.title_height)
        self.show(title)
        # set body text size
        self.tw.canvas.settextsize(self.bullet_height)
        # leave some space below the title
        y -= int(self.title_height*2*self.tw.lead)
        for s in sarray:
            self.tw.canvas.setxy(x, y)
            self.show(s)
            y -= int(self.bullet_height*2*self.tw.lead)
        # restore text size
        self.tw.canvas.settextsize(save_text_size)
    
    # title, two images (vertical), two desciptions
    def show_template1x2(self, title, media1, media2):
        w,h,xo,yo,dx,dy = calc_position(self.tw, 't1x2')
        x = -(self.tw.canvas.width/2)+xo
        y = self.tw.canvas.height/2
        self.tw.canvas.setxy(x, y)
        # save the text size so we can restore it later
        save_text_size = self.tw.textsize
        # set title text
        self.tw.canvas.settextsize(self.title_height)
        self.show(title)
        # calculate and set scale for media blocks
        myscale = 45 * (self.tw.canvas.height - self.title_height*2)/\
                 self.tw.canvas.height
        self.set_scale(myscale)
        # set body text size
        self.tw.canvas.settextsize(self.body_height)
        # render four quadrents
        # leave some space below the title
        y -= int(self.title_height*2*self.tw.lead)
        self.tw.canvas.setxy(x, y)
        self.show(media1)
        if self.tw.running_sugar:
            x = 0
            self.tw.canvas.setxy(x, y)
            self.show(media1.replace("media_","descr_"))
            y = -self.title_height
            self.tw.canvas.setxy(x, y)
            self.show(media2.replace("media_","descr_"))
            x = -(self.tw.canvas.width/2)+xo
            self.tw.canvas.setxy(x, y)
            self.show(media2)
        # restore text size
        self.tw.canvas.settextsize(save_text_size)

    # title and four images
    def show_template2x2(self, title, media1, media2, media3, media4):
        w,h,xo,yo,dx,dy = calc_position(self.tw, 't2x2')
        x = -(self.tw.canvas.width/2)+xo
        y = self.tw.canvas.height/2
        self.tw.canvas.setxy(x, y)
        # save the text size so we can restore it later
        save_text_size = self.tw.textsize
        # set title text
        self.tw.canvas.settextsize(self.title_height)
        self.show(title)
        # calculate and set scale for media blocks
        myscale = 45 * (self.tw.canvas.height - self.title_height*2)/\
                  self.tw.canvas.height
        self.set_scale(myscale)
        # set body text size
        self.tw.canvas.settextsize(self.body_height)
        # render four quadrents
        # leave some space below the title
        y -= int(self.title_height*2*self.tw.lead)
        self.tw.canvas.setxy(x, y)
        self.show(media1)
        x = 0
        self.tw.canvas.setxy(x, y)
        self.show(media2)
        y = -self.title_height
        self.tw.canvas.setxy(x, y)
        self.show(media4)
        x = -(self.tw.canvas.width/2)+xo
        self.tw.canvas.setxy(x, y)
        self.show(media3)
        # restore text size
        self.tw.canvas.settextsize(save_text_size)

    # title, one media object
    def show_template1x1a(self, title, media1):
        w,h,xo,yo,dx,dy = calc_position(self.tw, 't1x1a')
        x = -(self.tw.canvas.width/2)+xo
        y = self.tw.canvas.height/2
        self.tw.canvas.setxy(x, y)
        # save the text size so we can restore it later
        save_text_size = self.tw.textsize
        # set title text
        self.tw.canvas.settextsize(self.title_height)
        self.show(title)
        # calculate and set scale for media blocks
        myscale = 90 * (self.tw.canvas.height - self.title_height*2) /\
                       self.tw.canvas.height
        self.set_scale(myscale)
        # set body text size
        self.tw.canvas.settextsize(self.body_height)
        # render media object
        # leave some space below the title
        y -= int(self.title_height*2*self.tw.lead)
        self.tw.canvas.setxy(x, y)
        self.show(media1)
        # restore text size
        self.tw.canvas.settextsize(save_text_size)

    # image only (at current x,y)
    def insert_image(self, media, center):
        w = (self.tw.canvas.width * self.scale)/100
        h = (self.tw.canvas.height * self.scale)/100
        # convert from Turtle coordinates to screen coordinates
        x = self.tw.canvas.width/2+int(self.tw.canvas.xcor)
        y = self.tw.canvas.height/2-int(self.tw.canvas.ycor)
        if center is True:
            x -= w/2
            y -= h/2
        if media[0:5] == 'media':
            self.show_picture(media, x, y, w, h)
    
    # description text only (at current x,y)
    def insert_desc(self, media):
        w = (self.tw.canvas.width * self.scale)/100
        h = (self.tw.canvas.height * self.scale)/100
        # convert from Turtle coordinates to screen coordinates
        x = self.tw.canvas.width/2+int(self.tw.canvas.xcor)
        y = self.tw.canvas.height/2-int(self.tw.canvas.ycor)
        if media[0:5] == 'descr':
            self.show_description(media, x, y, w, h)
    
    def set_scale(self, x):
        self.scale = x

    # need to fix export logo to map show to write
    def show(self, string, center=False):
        # convert from Turtle coordinates to screen coordinates
        x = self.tw.canvas.width/2+int(self.tw.canvas.xcor)
        y = self.tw.canvas.height/2-int(self.tw.canvas.ycor)
        if type(string) == str or type(string) == unicode:
            if string == "media_None":
                pass
            elif string[0:6] == 'media_':
                self.insert_image(string, center)
            elif string[0:6] == 'descr_':
                self.insert_desc(string)
            elif string[0:6] == 'audio_':
                self.play_sound(string)
            else:
                if center is True:
                    y -= self.tw.textsize
                self.tw.canvas.draw_text(string,x,y,self.tw.textsize,
                          self.tw.canvas.width-x)
        elif type(string) == float or type(string) == int:
            string = round_int(string)
            if center is True:
                y -= self.tw.textsize
            self.tw.canvas.draw_text(string, x, y, self.tw.textsize,
                                     self.tw.canvas.width-x)
    
    def play_sound(self, audio):
        if audio == "" or audio[6:] == "":
            raise logoerror("#nomedia")
        if self.tw.running_sugar:
            if audio[6:] != "None":
                try:
                    dsobject = datastore.get(audio[6:])
                    play_audio(self, dsobject.file_path)
                except:
                    print "Couldn't open id: " + str(audio[6:])
        else:
            play_audio(self, audio[6:])

    def clear(self):
        stop_media(self)
        self.tw.canvas.clearscreen()

    def write(self, string, fsize):
        # convert from Turtle coordinates to screen coordinates
        x = self.tw.canvas.width/2+int(self.tw.canvas.xcor)
        y = self.tw.canvas.height/2-int(self.tw.canvas.ycor)
        self.tw.canvas.draw_text(string,x,y-15,int(fsize),self.tw.canvas.width)

