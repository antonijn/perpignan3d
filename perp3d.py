#!/usr/bin/env python3
import math
import os.path
import perpignan as p
import sys
import threading
from direct.showbase.ShowBase import ShowBase
from panda3d.core import AmbientLight, DirectionalLight, LightAttrib
from panda3d.core import Point3, Vec2, Vec3, Plane
from panda3d.core import OrthographicLens
from panda3d.core import NodePath
from panda3d.core import loadPrcFileData
from direct.showbase import DirectObject
from direct.task import Task
from enum import Enum

loadPrcFileData('', 'framebuffer-srgb true')

def tile_to_node(tile, scene):
    edges = []
    features = {}
    for i in range(4):
        feat = tile.slots[i * 3 + 1].feature
        edges.append(type(feat))
        if feat not in features:
            features[feat] = []
        features[feat].append(i)

    has_crossroads = False
    rivers = 0
    middle_inst = None
    middle_rot = 0
    road_into_town = -1

    # determine base tile
    node = NodePath('Tile')
    tile_base = node.attachNewNode('Base')

    for feat in features:
        if feat is not None:
            continue

        slots = features[feat]
        rivers = len(slots)
        if rivers == 1:
            [slot] = slots
            tile_base_inst = scene.find('Base3')
            tile_base_inst.instanceTo(tile_base)
            tile_base.setH(tile_base, 90 * (2 - slot))
        elif rivers == 2:
            if slots == [0, 2] or slots == [1, 3]:
                tile_base_inst = scene.find('Base1')
                tile_base_inst.instanceTo(tile_base)
                tile_base.setH(tile_base, 0 if 0 in slots else 90)
            else:
                rots = { (0,1): 180, (1,2): 90, (2,3): 0, (0,3): 270 }
                tile_base_inst = scene.find('Base2')
                tile_base_inst.instanceTo(tile_base)
                tile_base.setH(tile_base, rots[(slots[0], slots[1])])

    if rivers == 0:
        tile_base_inst = scene.find('Base0')
        tile_base_inst.instanceTo(tile_base)

    for feat in features:
        if type(feat) is not p.Road:
            continue

        slots = features[feat]

        edge_path_inst = scene.find('Path')
        for slot in slots:
            edge_path = node.attachNewNode('Path')
            edge_path_inst.instanceTo(edge_path)
            edge_path.setH(edge_path, 90 * (1 - slot))

        add_straight_middle = False
        if slots == [0, 2] or slots == [1, 3]:
            add_straight_middle = True
        elif len(slots) == 1 and edges.count(p.Road) == 1 and \
             edges[(slots[0] + 2) % 4] is p.Town:

            towns = edges.count(p.Town)
            if towns == 1:
                road_into_town = (slots[0] + 2) % 4
                add_straight_middle = True
            elif towns == 3:
                road_into_town = slots[0]

        if add_straight_middle:
            if rivers == 0:
                middle_inst = scene.find('Straight')
            else:
                middle_inst = scene.find('Bridge')
            middle_rot = 0 if slot in (1,3) else 270
        elif len(slots) == 2:
            middle_inst = scene.find('BendAway')
            rots = { (0,1): 0, (1,2): 270, (2,3): 180, (0,3): 90 }
            middle_rot = rots[(slots[0], slots[1])]

    for feat in features:
        if type(feat) is not p.Town:
            continue

        slots = features[feat]
        if len(slots) == 1:
            [slot] = slots

            idx_ch = '3' if road_into_town == slot else '1'
            wall_inst = scene.find(f'Wall{idx_ch}')
            wall = node.attachNewNode('Wall')
            wall_inst.instanceTo(wall)
            wall.setH(wall, 90 * (3 - slot))

            floor_inst = scene.find(f'Floor{idx_ch}a')
            floor = node.attachNewNode('Floor')
            floor_inst.instanceTo(floor)
            floor.setH(floor, 90 * (3 - slot))
        elif len(slots) == 2:
            if slots == [0, 2] or slots == [1, 3]:
                rot = 90 if 1 in slots else 0
                wall_inst = scene.find('Wall1')
                wall1 = node.attachNewNode('Wall')
                wall_inst.instanceTo(wall1)
                wall1.setH(wall1, rot)

                wall2 = node.attachNewNode('Wall')
                wall_inst.instanceTo(wall2)
                wall2.setH(wall2, rot + 180)

                floor_inst = scene.find('Floor1c')
                floor = node.attachNewNode('Floor')
                floor_inst.instanceTo(floor)
                floor.setH(floor, rot)
            else:
                rots = { (0,1): 270, (1,2): 180, (2,3): 90, (0,3): 0 }
                wall_inst = scene.find('Wall2')
                wall = node.attachNewNode('Wall')
                wall_inst.instanceTo(wall)
                wall.setH(wall, rots[(slots[0], slots[1])])

                floor_inst = scene.find('Floor2')
                floor = node.attachNewNode('Floor')
                floor_inst.instanceTo(floor)
                floor.setH(floor, rots[(slots[0], slots[1])])
        elif len(slots) == 3:
            # so that no tree is placed
            has_crossroads = True

            [slot] = (i for i in range(4) if i not in slots)
            idx_ch = '3' if road_into_town == slot else '1'
            wall_inst = scene.find(f'Wall{idx_ch}')
            wall = node.attachNewNode('Wall')
            wall_inst.instanceTo(wall)
            wall.setH(wall, 90 * (3 - slot))

            floor_inst = scene.find(f'Floor{idx_ch}b')
            floor = node.attachNewNode('Floor')
            floor_inst.instanceTo(floor)
            floor.setH(floor, 90 * (3 - slot))
        else:
            floor_inst = scene.find('Floor4')
            floor = node.attachNewNode('Floor')
            floor_inst.instanceTo(floor)

    if tile.slots[12].feature is not None:
        middle_inst = scene.find('Mill')
        if None in edges:
            water_mill = scene.find('WaterMill')
            if not middle_inst.isEmpty():
                middle_inst = water_mill

        if p.Road in edges:
            middle_rot = 90 * (1 - edges.index(p.Road))

    elif middle_inst is None and p.Road in edges and not has_crossroads:
        middle_inst = scene.find('Tree')

    if middle_inst is not None:
        middle = node.attachNewNode('Middle')
        middle_inst.instanceTo(middle)
        middle.setH(middle, middle_rot)

    node.setScale(0.5, 0.5, 0.5)

    return node

class MyPlayer(p.Player):
    def __init__(self, action_avail_cond):
        super().__init__('3d!')
        self.action_avail_cond = action_avail_cond
        self.action = None

    def poll_action(self):
        self.action_avail_cond.acquire()
        self.action_avail_cond.wait()
        return self.action

    def do_action(self, action):
        self.action_avail_cond.acquire()
        try:
            self.action = action
            self.action_avail_cond.notify()
        finally:
            self.action_avail_cond.release()

    def inform(self, msg):
        pass

class GhostTile(DirectObject.DirectObject):
    def __init__(self, app, player, cursor=(43, 42)):
        super().__init__()

        self.tile = app.perp.deck[-1]
        self.node = tile_to_node(self.tile, app.scene)
        x, y = cursor
        self.node.setPos(x, y, 0)
        self.node.reparentTo(app.render)

        self.app = app
        self.player = player

        self.hpr_lerp = None
        self.rotations = 0
        self.cursor = cursor

        self.update_task = taskMgr.add(self.update, 'update')

        # make these object-bound, so we create less garbage in the
        # update function
        self.mousePos3D = Point3()
        self.nearPoint = Point3()
        self.farPoint = Point3()
        self.groundPlane = Plane(Vec3(0, 0, 1), Vec3(0, 0, 0))
        self.lastMousePos = Vec2(0, 0)

        self.accept('wheel_up', self.rotCW)
        self.accept('wheel_down', self.rotCCW)
        self.accept('mouse1', self.place)

    def rotCW(self):
        self.rotations = (self.rotations + 1) % 4
        initial_h = self.node.getH()

        if self.hpr_lerp is not None and self.hpr_lerp.isPlaying():
            self.hpr_lerp.finish()

        h = self.node.getH() - 90
        self.hpr_lerp = self.node.hprInterval(0.15, Vec3(h, 0, 0), Vec3(initial_h, 0, 0))
        self.hpr_lerp.start()

    def rotCCW(self):
        self.rotations = (self.rotations + 3) % 4
        initial_h = self.node.getH()

        if self.hpr_lerp is not None and self.hpr_lerp.isPlaying():
            self.hpr_lerp.finish()

        h = self.node.getH() + 90
        self.hpr_lerp = self.node.hprInterval(0.15, Vec3(h, 0, 0), Vec3(initial_h, 0, 0))
        self.hpr_lerp.start()

    def commitTransforms(self):
        x, y = self.cursor
        self.app.perp.cursor = self.cursor
        for _ in range(self.rotations):
            self.app.perp.deck[-1].rotate_cw()
        self.rotations = 0

    def canPlace(self):
        return self.app.perp.can_place()

    def place(self):
        self.commitTransforms()

        if not self.canPlace():
            return

        self.app.perp.place()
        messenger.send('tile_placed')

    def update(self, task):
        mouseWatcher = base.mouseWatcherNode
        if mouseWatcher.hasMouse():
            mousePos = mouseWatcher.getMouse()
            self.lastMousePos = mousePos
        else:
            mousePos = self.lastMousePos

        base.camLens.extrude(mousePos, self.nearPoint, self.farPoint)
        self.groundPlane.intersectsLine(
            self.mousePos3D,
            base.render.getRelativePoint(base.cam, self.nearPoint),
            base.render.getRelativePoint(base.cam, self.farPoint)
        )

        cur_x, cur_y, _ = self.mousePos3D
        def dist(pos):
            x, y = pos
            x -= cur_x
            y -= cur_y
            return x*x + y*y

        nearest_spot = min(self.app.perp.available, key=dist)
        self.cursor = nearest_spot
        self.node.setPos(nearest_spot[0], nearest_spot[1], 0)

        return Task.cont

    def remove(self):
        #self.node.removeNode()
        self.ignoreAll()
        taskMgr.remove(self.update_task)

class MyApp(ShowBase):
    def __init__(self, perp):
        ShowBase.__init__(self)
        self.perp = perp

        self.setBackgroundColor(0.392, 0.584, 0.929)
        tiles_path = os.path.join(os.path.dirname(__file__), 'tiles.gltf')
        self.scene = self.loader.loadModel(tiles_path)

        start_tile = tile_to_node(self.perp.grid[42][42], self.scene)
        start_tile.setPos(42, 42, 0)
        start_tile.reparentTo(self.render)

        self.setupLights()

        self.disableMouse()
        self.camLens = OrthographicLens()
        self.cam.node().setLens(self.camLens)
        self.focus = Vec3(42, 42, 0)
        self.tiles_placed = 1
        # this initial setting is meaningless; see next_player()
        self.focus_radius = 1

        self.accept(self.win.getWindowEvent(), self.onWindowEvent)
        self.accept('escape', sys.exit)
        self.accept('tile_placed', self.next_player)
        self.ghost = None
        self.next_player()

    def next_player(self):
        self.perp.next_player()
        if self.ghost is not None:
            self.ghost.remove()
            x, y = self.ghost.cursor
            self.focus = (self.focus * self.tiles_placed + Vec3(x, y, 0)) / (self.tiles_placed + 1)
            self.tiles_placed += 1

        far_tile_dist_sqr = max(
            (Vec3(t.x, t.y, 0) - self.focus).length_squared()
            for col in self.perp.grid
            for t in col
            if t is not None
        )
        self.focus_radius = math.sqrt(far_tile_dist_sqr)

        self.ghost = GhostTile(self, self.perp.active_player)

        self.reset_camera()

    def onWindowEvent(self, window):
        if window.isClosed():
            sys.exit()

        self.reset_camera()

    def reset_camera(self):
        width = self.win.getProperties().getXSize()
        height = self.win.getProperties().getYSize()
        aspect = width / height
        fw = (self.focus_radius + 3) * 1.4
        fh = fw
        if width > height:
            fw *= aspect
        else:
            fh /= aspect
        self.camLens.setFilmSize(fw, fh)
        self.cam.setPos(self.focus + Vec3(8, -4, 12))
        self.cam.lookAt(self.focus)

    def setupLights(self):  # This function sets up some default lighting
        ambientLight = AmbientLight("ambientLight")
        ambientLight.setColor((.7, .7, .7, 1))
        directionalLight = DirectionalLight("directionalLight")
        directionalLight.setDirection(Vec3(0, 45, -45))
        directionalLight.setColor((.3, .3, .3, 1))
        render.setLight(render.attachNewNode(directionalLight))
        render.setLight(render.attachNewNode(ambientLight))

perp = p.Perpignan()
action_avail_cond = threading.Condition()
perp.players = [MyPlayer(action_avail_cond)]

app = MyApp(perp)

#perp_thread = threading.Thread(target=perp.run)
#perp_thread.start()

app.run()
