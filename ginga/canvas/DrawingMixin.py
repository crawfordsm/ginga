#
# DrawingMixin.py -- enable drawing capabilities.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time
import math

class DrawingMixin(object):
    """The DrawingMixin is a mixin class that adds drawing capability for
    some of the basic CanvasObject-derived types.  The setSurface method is
    used to associate a ImageViewCanvas object for layering on.
    """

    def __init__(self, drawDict):
        # For interactive drawing
        self.candraw = False
        self.drawDict = drawDict
        drawtypes = drawDict.keys()
        self.drawtypes = []
        for key in ['point', 'line', 'circle', 'ellipse', 'square',
                    'rectangle', 'box', 'polygon', 'path',
                    'triangle', 'righttriangle', 'equilateraltriangle',
                    'ruler', 'compass', 'text']:
            if key in drawtypes:
                self.drawtypes.append(key)
        self.t_drawtype = 'point'
        self.t_drawparams = {}
        self._drawtext = "EDIT ME"
        self._start_x = 0
        self._start_y = 0
        self._points = []
        self._drawrot_deg = 0.0

        self._cp_index = None

        self._processTime = 0.0
        # time delta threshold for deciding whether to update the image
        self._deltaTime = 0.020
        self.drawObj = None

        self.fitsobj = None
        self.drawbuttonmask = 0x4

        # NOTE: must be mixed in with a Callback.Callbacks
        for name in ('draw-event', 'draw-down', 'draw-move', 'draw-up',
                     'draw-scroll', 'drag-drop', 'edit-event'):
            self.enable_callback(name)

    def setSurface(self, viewer):
        self.viewer = viewer

        # register this canvas for events of interest
        self.set_callback('edit-down', self.edit_start)
        self.set_callback('edit-move', self.edit_motion)
        self.set_callback('edit-up', self.edit_stop)
        #self.set_callback('edit-scroll', self.edit_scale)
        self.set_callback('edit-scroll', self.edit_rotate)
        self.set_callback('draw-down', self.draw_start)
        self.set_callback('draw-move', self.draw_motion)
        self.set_callback('draw-up', self.draw_stop)
        self.set_callback('keydown-poly_add', self.draw_poly_add)
        self.set_callback('keydown-poly_del', self.draw_poly_delete)
        self.set_callback('keydown-edit_del', self.edit_delete)

        #self.ui_setActive(True)

    def getSurface(self):
        return self.viewer

    def draw(self):
        super(DrawingMixin, self).draw()
        if self.drawObj:
            self.drawObj.draw()

    def set_drawtext(self, text):
        self._drawtext = text
        
    def _draw_update(self, data_x, data_y):

        klass = self.drawDict[self.t_drawtype]
        obj = None
        
        if self.t_drawtype == 'point':
            radius = max(abs(self._start_x - data_x),
                         abs(self._start_y - data_y))
            obj = klass(self._start_x, self._start_y, radius,
                        **self.t_drawparams)

        elif self.t_drawtype == 'compass':
            radius = max(abs(self._start_x - data_x),
                         abs(self._start_y - data_y))
            obj = klass(self._start_x, self._start_y,
                        radius, **self.t_drawparams)

        elif self.t_drawtype == 'rectangle':
            obj = klass(self._start_x, self._start_y,
                        data_x, data_y, **self.t_drawparams)
                
        elif self.t_drawtype == 'square':
                len_x = self._start_x - data_x
                len_y = self._start_y - data_y
                length = max(abs(len_x), abs(len_y))
                len_x = cmp(len_x, 0) * length
                len_y = cmp(len_y, 0) * length
                obj = klass(self._start_x, self._start_y,
                            self._start_x-len_x, self._start_y-len_y,
                            **self.t_drawparams)

        elif self.t_drawtype == 'equilateraltriangle':
                len_x = self._start_x - data_x
                len_y = self._start_y - data_y
                length = max(abs(len_x), abs(len_y))
                obj = klass(self._start_x, self._start_y,
                            length, length, **self.t_drawparams)
            
        elif self.t_drawtype in ('box', 'ellipse', 'triangle'):
            xradius = abs(self._start_x - data_x)
            yradius = abs(self._start_y - data_y)
            self.t_drawparams['rot_deg'] = self._drawrot_deg
            obj = klass(self._start_x, self._start_y, xradius, yradius,
                        **self.t_drawparams)

        elif self.t_drawtype == 'circle':
            radius = math.sqrt(abs(self._start_x - data_x)**2 + 
                               abs(self._start_y - data_y)**2 )
            obj = klass(self._start_x, self._start_y, radius,
                        **self.t_drawparams)

        elif self.t_drawtype == 'line':
            obj = klass(self._start_x, self._start_y, data_x, data_y,
                        **self.t_drawparams)

        elif self.t_drawtype == 'righttriangle':
            obj = klass(self._start_x, self._start_y, data_x, data_y,
                        **self.t_drawparams)

        elif self.t_drawtype == 'polygon':
            points = list(self._points)
            points.append((data_x, data_y))
            obj = klass(points, **self.t_drawparams)

        elif self.t_drawtype == 'path':
            points = list(self._points)
            points.append((data_x, data_y))
            obj = klass(points, **self.t_drawparams)

        elif self.t_drawtype == 'text':
            obj = klass(self._start_x, self._start_y, self._drawtext,
                        **self.t_drawparams)

        elif self.t_drawtype == 'ruler':
            obj = klass(self._start_x, self._start_y, data_x, data_y,
                        **self.t_drawparams)

        if obj != None:
            obj.initialize(None, self.viewer, self.logger)
            #obj.initialize(None, self.viewer, self.viewer.logger)
            self.drawObj = obj
            if time.time() - self._processTime > self._deltaTime:
                self.processDrawing()
            
        return True
            
    def draw_start(self, canvas, action, data_x, data_y):
        if not self.candraw:
            return False

        # unselect an editing object if one was selected
        if (self.drawObj != None) and self.drawObj.is_editing():
            self.drawObj.set_edit(False)

        self.drawObj = None
        self._drawrot_deg = 0.0
        self._points = [(data_x, data_y)]
        self._start_x, self._start_y = data_x, data_y
        self._draw_update(data_x, data_y)

        self.processDrawing()
        return True

    def draw_stop(self, canvas, button, data_x, data_y):
        if not self.candraw:
            return False

        self._draw_update(data_x, data_y)
        obj, self.drawObj = self.drawObj, None
        self._points = []

        if obj:
            objtag = self.add(obj, redraw=True)
            self.make_callback('draw-event', objtag)
            return True
        else:
            self.processDrawing()

    def draw_motion(self, canvas, button, data_x, data_y):
        if not self.candraw:
            return False
        self._draw_update(data_x, data_y)
        return True

    def draw_poly_add(self, canvas, action, data_x, data_y):
        if self.candraw and (self.t_drawtype in ('polygon', 'path')):
            self._points.append((data_x, data_y))
        return True

    def draw_poly_delete(self, canvas, action, data_x, data_y):
        if self.candraw and (self.t_drawtype in ('polygon', 'path')):
            if len(self._points) > 0:
                self._points.pop()
        return True

    def processDrawing(self):
        self._processTime = time.time()
        self.viewer.redraw(whence=3)
    
    def _edit_update(self, data_x, data_y):
        if self._cp_index == None:
            return False

        if self._cp_index < 0:
            self.drawObj.move_to(data_x - self._start_x,
                                 data_y - self._start_y)
        else:
            self.drawObj.set_edit_point(self._cp_index, (data_x, data_y))

        if time.time() - self._processTime > self._deltaTime:
            self.processDrawing()
        return True

    def _is_editable(self, obj, x, y, is_inside):
        return is_inside and obj.editable
    
    def edit_start(self, canvas, action, data_x, data_y):

        # check for objects at this location
        print("getting items")
        objs = canvas.select_items_at(data_x, data_y,
                                      test=self._is_editable)
        print("items: %s" % (str(objs)))
        if self.drawObj == None:
            print("no editing: select/deselect")
            # <-- no current object being edited

            if len(objs) == 0:
                # no objects
                return False

            # pick top object
            obj = objs[-1]       

            if not obj.is_editing():
                obj.set_edit(True)
                self.drawObj = obj
            else:
                obj.set_edit(False)

        elif self.drawObj.is_editing():
            print("editing: checking for cp")
            edit_pts = self.drawObj.get_edit_points()
            i = self.drawObj.get_pt(edit_pts, data_x, data_y,
                                    self.drawObj.cap_radius)
            if i != None:
                print("editing cp #%d" % (i))
                # editing a control point from an existing object
                self._cp_index = i
                self._edit_update(data_x, data_y)
                return True

            elif self.drawObj.contains(data_x, data_y):
                # TODO: moving an existing object
                print("moving an object")
                self._cp_index = -1
                ref_x, ref_y = self.drawObj.get_reference_pt()
                self._start_x, self._start_y = data_x - ref_x, data_y - ref_y
                return True

            else:
                # <-- user clicked outside the object
                print("deselecting an object")
                if self.drawObj in objs:
                    objs.remove(self.drawObj)
                self.drawObj.set_edit(False)
                if len(objs) == 0:
                    self.drawObj = None
                else:
                    obj = objs[-1]       
                    obj.set_edit(True)
                    self.drawObj = obj
        else:
            if self.drawObj in objs:
                # reselect
                self.drawObj.set_edit(True)
            elif len(objs) > 0:
                obj = objs[-1]       
                obj.set_edit(True)
                self.drawObj = obj
            
        self.processDrawing()
        return True

    def edit_stop(self, canvas, button, data_x, data_y):
        if (self.drawObj == None) or (self._cp_index == None):
            return False

        self._edit_update(data_x, data_y)
        self._cp_index = None

        #objtag = self.lookup_object_tag(self.drawObj)
        #self.make_callback('edit-event', objtag)
        return True

    def edit_motion(self, canvas, button, data_x, data_y):
        if (self.drawObj != None) and (self._cp_index != None):
            self._edit_update(data_x, data_y)
            return True
        return False

    def edit_rotate(self, canvas, direction, amount, data_x, data_y,
                    msg=True):
        if self.drawObj == None:
            return False
        bd = self.viewer.get_bindings()
        if bd.get_direction(direction) == 'down':
            amount = - amount
        cur_rot = self._drawrot_deg
        new_rot = cur_rot + amount
        if hasattr(self.drawObj, 'rot_deg'):
            self.drawObj.rot_deg = new_rot
            self._drawrot_deg = new_rot
        else:
            self.drawObj.rotate_by(amount)
        self.processDrawing()
        return True

    def edit_scale(self, canvas, direction, amount, data_x, data_y,
                    msg=True):
        if self.drawObj == None:
            return False
        bd = self.viewer.get_bindings()
        if bd.get_direction(direction) == 'down':
            amount = 0.9
        else:
            amount = 1.1
        self.drawObj.scale_by(amount, amount)
        self.processDrawing()
        return True

    def edit_delete(self, canvas, action, data_x, data_y):
        if (self.drawObj != None) and self.drawObj.is_editing():
            obj, self.drawObj = self.drawObj, None
            self.deleteObject(obj)
        return True

    def isDrawing(self):
        return self.drawObj != None
    
    def enable_draw(self, tf):
        self.candraw = tf
        
    def set_drawcolor(self, colorname):
        self.t_drawparams['color'] = colorname
        
    def set_drawtype(self, drawtype, **drawparams):
        drawtype = drawtype.lower()
        assert drawtype in self.drawtypes, \
               ValueError("Bad drawing type '%s': must be one of %s" % (
            drawtype, self.drawtypes))
        self.t_drawtype = drawtype
        self.t_drawparams = drawparams.copy()

    def get_drawtypes(self):
        return self.drawtypes

    def get_drawtype(self):
        return self.t_drawtype

    def getDrawClass(self, drawtype):
        drawtype = drawtype.lower()
        klass = self.drawDict[drawtype]
        return klass
        
    def get_drawparams(self):
        return self.t_drawparams.copy()

#END