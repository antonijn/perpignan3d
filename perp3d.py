#!/usr/bin/env python3
import sys
import os.path
import perpignan as p
from direct.showbase.ShowBase import ShowBase
from panda3d.core import AmbientLight, DirectionalLight, LightAttrib
from panda3d.core import LPoint3, LVector3, BitMask32
from panda3d.core import OrthographicLens
from panda3d.core import NodePath
from panda3d.core import loadPrcFileData
from direct.showbase import DirectObject
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

    return node

class MyApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.setBackgroundColor(0.392, 0.584, 0.929)
        tiles_path = os.path.join(os.path.dirname(__file__), 'tiles.gltf')
        self.scene = self.loader.loadModel(tiles_path)

        self.perp = p.Perpignan()
        self.tnode = None

        self.tile = -1
        self.nextTile()

        self.setupLights()

        lens = OrthographicLens()
        #lens.setFilmSize(2, 2)
        self.cam.node().setLens(lens)
        self.cam.setPos(8, -4, 12)
        self.cam.lookAt(LVector3(0, 0, 0))

        self.accept(self.win.getWindowEvent(), self.onWindowEvent)
        self.accept('escape', sys.exit)
        self.accept('k', self.nextTile)
        self.accept('j', self.prevTile)
        self.accept('wheel_up', self.rotCW)
        self.accept('wheel_down', self.rotCCW)

    def onWindowEvent(self, window):
        if window.isClosed():
            sys.exit()

        width = window.getProperties().getXSize()
        height = window.getProperties().getYSize()
        aspect = width / height
        fw, fh = 6, 6
        if width > height:
            fw *= aspect
        else:
            fh /= aspect
        lens = self.cam.node().getLens()
        lens.setFilmSize(fw, fh)

    def nextTile(self):
        self.tile = (self.tile + 1) % len(self.perp.deck)
        self.loadTile()

    def prevTile(self):
        self.tile = (self.tile + len(self.perp.deck) - 1) % len(self.perp.deck)
        self.loadTile()

    def loadTile(self):
        if self.tnode is not None:
            self.tnode.removeNode()

        tile = self.perp.deck[self.tile]

        self.tnode = tile_to_node(tile, self.scene)
        #self.tnode.setPos(-8, 4, -12)
        self.tnode.reparentTo(self.render)

    def rotCW(self):
        h = self.tnode.getH(self.tnode)
        self.tnode.setH(self.tnode, h - 90)

    def rotCCW(self):
        h = self.tnode.getH(self.tnode)
        self.tnode.setH(self.tnode, h + 90)

    def setupLights(self):  # This function sets up some default lighting
        ambientLight = AmbientLight("ambientLight")
        ambientLight.setColor((.7, .7, .7, 1))
        directionalLight = DirectionalLight("directionalLight")
        directionalLight.setDirection(LVector3(0, 45, -45))
        directionalLight.setColor((.3, .3, .3, 1))
        render.setLight(render.attachNewNode(directionalLight))
        render.setLight(render.attachNewNode(ambientLight))

app = MyApp()
app.run()
