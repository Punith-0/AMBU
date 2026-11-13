"""Reproducible SUMO network and sensor configuration."""
from pathlib import Path
import os, sys, shutil, subprocess, random, json, math
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SUMO = Path(shutil.which('sumo') or os.environ.get('SUMO_HOME', '') + '/bin/sumo.exe')
sys.path.append(str(SUMO.parent.parent / 'tools'))
import traci
import sumolib

def prepare():
    dest = ROOT / 'sumo'
    netfile = dest / 'nightwatch.net.xml'
    if not netfile.exists():
        subprocess.run([str(SUMO.parent/'netgenerate'),'--grid','--grid.number','6','--grid.length','150','--default.lanenumber','2','--default.speed','13.89','--tls.guess','true','--tls.guess.threshold','0','--tls.default-type','static','--tls.green.time','30','--tls.yellow.time','3','--tls.allred.time','2','--no-turnarounds','true','-o',str(netfile)],check=True,capture_output=True)
    net = sumolib.net.readNet(str(netfile), withInternal=True)
    add = ET.Element('additional')
    for edge in net.getEdges():
        if edge.getFunction() == 'internal': continue
        for lane in edge.getLanes():
            length = lane.getLength()
            ET.SubElement(add, 'laneAreaDetector', id='e2_' + lane.getID(), lane=lane.getID(), pos=str(max(0, length-65)), length=str(min(60, length-1)), period='60', file='NUL' if os.name == 'nt' else '/dev/null')
            ET.SubElement(add, 'inductionLoop', id='e1_' + lane.getID(), lane=lane.getID(), pos='-5', period='60', file='NUL' if os.name == 'nt' else '/dev/null')
    sensor_path=dest/'sensors.add.xml'
    sensor_bytes=ET.tostring(add)
    if not sensor_path.exists() or sensor_path.read_bytes()!=sensor_bytes:
        temporary=dest/f'sensors.{os.getpid()}.tmp'
        temporary.write_bytes(sensor_bytes)
        temporary.replace(sensor_path)
    return net

def geometry(net):
    edges = [e for e in net.getEdges() if e.getFunction() != 'internal']
    return {'roads': [{'id': e.getID(), 'shape': e.getShape(), 'lanes': [{'id': l.getID(), 'shape': l.getShape()} for l in e.getLanes()]} for e in edges], 'junctions': [{'id': n.getID(), 'position': n.getCoord(), 'shape': n.getShape(), 'signal': n.getType() == 'traffic_light'} for n in net.getNodes() if not n.getID().startswith(':')]}

def demand(net, seed, density, folder):
    rng = random.Random(seed)
    edges = [e for e in net.getEdges() if e.getFunction() != 'internal']
    routes = ET.Element('routes')
    ET.SubElement(routes, 'vType', id='car', accel='2.6', decel='4.5', sigma='0.4', length='4.5', minGap='2.5', maxSpeed='13.89')
    ET.SubElement(routes, 'vType', id='ambulance', vClass='passenger', guiShape='emergency', accel='3', decel='5', length='5.5', minGap='2.5', maxSpeed='16.67', color='1,1,1')
    for i in range(int(900*density)):
        a, b = rng.sample(edges, 2)
        path, cost = net.getShortestPath(a, b)
        if path and len(path) > 2:
            vehicle = ET.SubElement(routes, 'vehicle', id=f'car_{i}', type='car', depart=f'{i/density:.2f}', departLane='best', departSpeed='max')
            ET.SubElement(vehicle, 'route', edges=' '.join(e.getID() for e in path))
    path = folder / 'demand.rou.xml'
    ET.ElementTree(routes).write(path)
    return path
