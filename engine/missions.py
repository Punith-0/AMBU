"""Demo geography and mission lifecycle; names are illustrative, not real facilities."""
HOSPITALS=[
 {'id':'sanjeevani','name':'Sanjeevani Hospital','edge':'E3E4','x':525,'y':525,'specialty':'Trauma and emergency'},
 {'id':'aarogya','name':'Aarogya General Hospital','edge':'A0A1','x':75,'y':75,'specialty':'General emergency'},
 {'id':'jeevan','name':'Jeevan Heart Centre','edge':'E1E2','x':525,'y':225,'specialty':'Cardiac and critical care'}
]
STATION={'name':'Suraksha Ambulance Station','edge':'C0C1','x':375,'y':75}
PICKUPS=[{'edge':'A0A1','name':'Gandhi Nagar'}, {'edge':'B1B2','name':'Basavanagudi'}, {'edge':'C2D2','name':'MG Road Junction'}, {'edge':'D3E3','name':'Indiranagar'}, {'edge':'E0E1','name':'HSR Layout'}, {'edge':'A3B3','name':'Jayanagar'}, {'edge':'C4D4','name':'Hebbal'}]

def hospital(hid):
    return next((h for h in HOSPITALS if h['id']==hid),None)

def nearest(net,origin):
    candidates=[]
    for h in HOSPITALS:
        path,cost=net.getShortestPath(net.getEdge(origin),net.getEdge(h['edge']))
        if path:candidates.append((cost,h['id'],h))
    return min(candidates,key=lambda x:(x[0],x[1]))[2]
