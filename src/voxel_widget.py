# glwidget.py
# A 3D OpenGL QT Widget
# Copyright (c) 2013, Graham R King
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

import random
import math
import array
from PySide import QtCore, QtGui, QtOpenGL
from OpenGL.GL import *
from OpenGL.GLU import gluUnProject
import voxel
from euclid import LineSegment3, Plane, Point3

class GLWidget(QtOpenGL.QGLWidget):

    @property
    def floor_grid(self):
        return self._display_floor_grid
    @floor_grid.setter
    def floor_grid(self, value):
        self._display_floor_grid = value
        self.updateGL()

    def __init__(self, parent=None):
        glformat = QtOpenGL.QGLFormat()
        glformat.setVersion(1,1);
        glformat.setProfile(QtOpenGL.QGLFormat.CoreProfile);
        QtOpenGL.QGLWidget.__init__(self, glformat, parent)
        # Test we have a valid context
        ver = QtOpenGL.QGLFormat.openGLVersionFlags()
        if not ver & QtOpenGL.QGLFormat.OpenGL_Version_1_1:
            raise Exception("Requires OpenGL Version 1.1 or above.")
        # Default values
        self._background_colour = QtGui.QColor("silver")
        # Mouse position
        self._mouse = QtCore.QPoint()
        # Rotation
        self._rotate_x = 0
        self._rotate_y = 0
        self._rotate_z = 0
        # Translation
        self._translate_x = 0
        self._translate_y = 0
        self._translate_z = -60
        # zoom
        self._zoom_speed = 0.1
        # Render floor grid?
        self._display_floor_grid = True
        # Our voxel scene
        self.voxels = voxel.VoxelData()
        # Generate some test data XXX
        self.build_world()
    
    # Initialise OpenGL            
    def initializeGL(self):
        # Set background colour        
        self.qglClearColor(self._background_colour)
        # Our polygon winding order is clockwise
        glFrontFace(GL_CW);
        # Enable depth testing
        glEnable(GL_DEPTH_TEST)
        # Enable backface culling
        glCullFace(GL_BACK)
        glEnable(GL_CULL_FACE)
        # Shade model
        glShadeModel(GL_SMOOTH)
        # Build our mesh
        self.build_mesh()
        # Setup our lighting
        self.setup_lights()
                
    # Render our scene
    def paintGL(self):        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(self._translate_x,self._translate_y, self._translate_z)
        glRotated(self._rotate_x, 1.0, 0.0, 0.0)
        glRotated(self._rotate_y, 0.0, 1.0, 0.0)
        glRotated(self._rotate_z, 0.0, 0.0, 1.0)
        
        # Enable vertex buffers
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        # Describe our buffers
        glVertexPointer( 3, GL_FLOAT, 0, self._vertices);
        glColorPointer(3, GL_UNSIGNED_BYTE, 0, self._colours);
        glNormalPointer(GL_FLOAT, 0, self._normals);
        
        # Render the buffers
        glDrawArrays(GL_TRIANGLES, 0, self._num_vertices)

        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)
        
        # Floor grid
        if self.floor_grid:
            self.paintGrid()
        
    # Window is resizing
    def resizeGL(self, width, height):
        self._width = width
        self._height = height 
        glViewport(0,0,width,height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        self.perspective(45.0, float(width) / height, 4, 300)
        glMatrixMode(GL_MODELVIEW)

    # Render scene as colour ID's
    def paintID(self):
        glDisable(GL_LIGHTING)

        # Render with white background
        self.qglClearColor(QtGui.QColor.fromRgb(0xff, 0xff, 0xff))
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(self._translate_x,self._translate_y, self._translate_z)
        glRotated(self._rotate_x, 1.0, 0.0, 0.0)
        glRotated(self._rotate_y, 0.0, 1.0, 0.0)
        glRotated(self._rotate_z, 0.0, 0.0, 1.0)
        
        # Enable vertex buffers
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        # Describe our buffers
        glVertexPointer( 3, GL_FLOAT, 0, self._vertices);
        glColorPointer(3, GL_UNSIGNED_BYTE, 0, self._colour_ids);
        glNormalPointer(GL_FLOAT, 0, self._normals);
        
        # Render the buffers
        glDrawArrays(GL_TRIANGLES, 0, self._num_vertices)

        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)
                
        # Set background colour back to original
        self.qglClearColor(self._background_colour)
        
        # Re-enable lighting        
        glEnable(GL_LIGHTING)

    # Render a grid
    def paintGrid(self):
        # Disable lighting
        glDisable(GL_LIGHTING)
        
        # Enable vertex buffers
        glEnableClientState(GL_VERTEX_ARRAY)

        # Describe our buffers
        glVertexPointer( 3, GL_FLOAT, 0, self._grid);
        
        # Render the buffers
        glDrawArrays(GL_LINES, 0, self._num_grid_vertices)

        # Disable vertex buffers
        glDisableClientState(GL_VERTEX_ARRAY)

        # Enable lighting
        glEnable(GL_LIGHTING)

    def perspective(self, fovY, aspect, zNear, zFar ):
        fH = math.tan( fovY / 360.0 * math.pi ) * zNear;
        fW = fH * aspect
        glFrustum( -fW, fW, -fH, fH, zNear, zFar )

    def setup_lights(self):
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
    
    # Build a mesh from our current voxel data
    def build_mesh(self):
        # Grab the voxel vertices
        (self._vertices, self._colours, self._normals,
         self._colour_ids) = self.voxels.get_vertices()
        self._num_vertices = len(self._vertices)//3
        self._vertices = array.array("f", self._vertices).tostring()
        self._colours = array.array("B", self._colours).tostring()
        self._colour_ids = array.array("B", self._colour_ids).tostring()
        self._normals = array.array("f", self._normals).tostring()

    # This is just a hack to put some demo data in the voxel world
    def build_world(self):
        world = self.voxels

        # Build a grid
        grid = world.get_grid_vertices()
        self._grid = array.array("f", grid).tostring()
        self._num_grid_vertices = len(grid)//3
        
        # Add some random voxels
        for i in range(250):
            x = random.randint(0,world.width-1)
            y = random.randint(0,world.height-1)
            z = random.randint(0,world.depth-1)
            world.set(x, y, z, voxel.FULL)

    def mousePressEvent(self, event):
        self._mouse = QtCore.QPoint(event.pos())
        if event.buttons() & QtCore.Qt.LeftButton:
            x, y, z, face = self.window_to_voxel(event.x(), event.y())
            # If we actually clicked on a voxel
            if face is not None:
                self.voxels.set(x, y, z, voxel.EMPTY)
                self.build_mesh()
                self.updateGL()
            elif x is not None:
                # We clicked on the background
                self.voxels.set(x, y, z, voxel.FULL)                
                self.build_mesh()
                self.updateGL()

    def mouseMoveEvent(self, event):
        dx = event.x() - self._mouse.x()
        dy = event.y() - self._mouse.y()

        # Right mouse button held down - rotate
        if event.buttons() & QtCore.Qt.RightButton:
            self._rotate_x = self._rotate_x + dy
            self._rotate_y = self._rotate_y + dx
            self.updateGL()
            
        # Middle mouse button held down - translate
        if event.buttons() & QtCore.Qt.MiddleButton:
            self._translate_x = self._translate_x + (dx / 10.0)
            self._translate_y = self._translate_y - (dy / 10.0) 
            self.updateGL()
            
        self._mouse = QtCore.QPoint(event.pos())

    def wheelEvent(self, event):
        if event.delta() > 0:
            self._translate_z *= 1+self._zoom_speed
        else:
            self._translate_z *= 1-self._zoom_speed
        self.updateGL()

    # Return voxel space x,y,z coordinates given x, y window coordinates
    # Also return an identifier which indicates which face was clicked on.
    # If the background was click on rather than a voxel, calculate and return
    # the location on the floor grid.
    def window_to_voxel(self, x, y):
        # We must invert y coordinates
        y = self._height - y
        # Render our scene (to the back buffer) using colour IDs
        self.paintID()
        # Grab the colour / ID at the coordinates
        c = glReadPixels( x, y, 1, 1, GL_RGB, GL_UNSIGNED_BYTE)
        # Grab the colour (ID) which was clicked on
        voxelid = ord(c[0])<<16 | ord(c[1])<<8 | ord(c[2])
        # Perhaps we clicked on the background?
        if voxelid == 0xffffff:
            x, y, z = self.floor_intersection(x, y)
            if x is None:
                return None, None, None, None
            return x, y, z, None
        # Decode the colour ID into x,y,z,face
        x = (voxelid & 0xfe0000)>>17
        y = (voxelid & 0x1fc00)>>10
        z = (voxelid & 0x3f8)>>3
        face = voxelid & 0x07
        # Return what we learned
        return x,y,z,face

    # Calculate the intersection between mouse coordinates and floor grid
    def floor_intersection(self, x, y):
        # Unproject coordinates into object space
        nx,ny,nz = gluUnProject(x, y, 0.0)
        fx,fy,fz = gluUnProject(x, y, 1.0)
        # Calculate the ray
        near = Point3(nx, ny, nz)
        far = Point3(fx, fy, fz)
        ray = LineSegment3(near, far)
        # Define ground plane
        _x, gridy, _z = self.voxels.voxel_to_world(0, 0, 0)
        point1 = Point3(0,gridy,0)
        point2 = Point3(10,gridy,10)
        point3 = Point3(-2,gridy,-8)
        plane = Plane(point1, point2, point3)
        # Get intersection point
        intersect = plane.intersect(ray)
        if not intersect:
            return None, None, None
        # Adjust to voxel space coordinates
        x, y, z = self.voxels.world_to_voxel(intersect.x, intersect.y, intersect.z)
        return int(x), int(y), int(z)